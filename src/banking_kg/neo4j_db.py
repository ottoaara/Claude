from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
import os
import re
from datetime import datetime

# Corporate suffix pattern for peer name canonicalization
_CORP_SUFFIX_RE = re.compile(
    r"\b(inc\.?|corp\.?|co\.?|llc\.?|ltd\.?|plc\.?|corporation|company|group|"
    r"holdings?|automotive|motors?|technologies|technology|systems?|solutions?|"
    r"international|enterprises?|industries?)\b",
    re.IGNORECASE,
)

def _normalize_name(name: str) -> str:
    """Strip corporate suffixes and whitespace for fuzzy matching."""
    s = _CORP_SUFFIX_RE.sub("", name.lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _dedup_peers_list(peers: list) -> list:
    """Deduplicate a list of peer dicts by ticker (primary) then normalized name.
    Keeps the entry with a ticker over one without; on tie keeps first seen.
    Handles variants like 'General Motors' / 'General Motors Co.' and
    'Lucid Group' / 'Lucid Group Inc.'
    """
    seen_tickers: dict = {}
    seen_names: dict = {}
    out: list = []
    for peer in peers:
        ticker = (peer.get("ticker") or "").strip().upper() or None
        norm = _normalize_name(peer.get("company_name") or peer.get("name") or "")
        if ticker and ticker in seen_tickers:
            idx = seen_tickers[ticker]
            if len(peer.get("company_name", "") or peer.get("name", "")) > len(
                out[idx].get("company_name", "") or out[idx].get("name", "")
            ):
                out[idx] = peer
            continue
        if norm and norm in seen_names:
            idx = seen_names[norm]
            if ticker and not (out[idx].get("ticker") or "").strip():
                out[idx] = peer
                if ticker:
                    seen_tickers[ticker] = idx
            continue
        if ticker:
            seen_tickers[ticker] = len(out)
        if norm:
            seen_names[norm] = len(out)
        out.append(peer)
    return out


def _normalize_officer_name(name: str) -> str:
    """Normalize a person name for dedup: lowercase, strip middle initials/names.
    'Elon E. Musk', 'Elon E Musk', 'Elon Musk' → 'elon musk'
    Keeps first + last token only when 3+ tokens and middle token is 1-2 chars.
    """
    parts = re.sub(r"[^a-zA-Z\s]", "", name).lower().split()
    if len(parts) >= 3 and len(parts[1]) <= 2:
        # strip middle initial/name
        parts = [parts[0]] + parts[2:]
    return " ".join(parts)

# ── Universal cache TTL policy ───────────────────────────────────────────────
# All financial data (main company and peers, 10-K and 10-Q) uses the same TTL.
# Change this one constant to adjust the policy globally.
FINANCIAL_CACHE_TTL_DAYS   = 30   # re-fetch if filing node is older than this
NAICS_CACHE_TTL_DAYS       = 180  # NAICS classification changes rarely
PEER_LIST_CACHE_TTL_DAYS   = 180  # Peer company list (not financials)
COMPANY_INFO_CACHE_TTL_DAYS = 7   # Website-scraped company overview
NEWS_CACHE_TTL_DAYS         = 7   # News is refreshed frequently
# ─────────────────────────────────────────────────────────────────────────────


def _neo4j_to_python(value):
    """Recursively convert Neo4j temporal/spatial types to plain Python types."""
    # Neo4j Date → "YYYY-MM-DD"
    type_name = type(value).__name__
    if type_name in ("Date", "neo4j.time.Date"):
        try:
            return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
        except Exception:
            return str(value)
    # Neo4j DateTime / LocalDateTime → ISO string
    if type_name in ("DateTime", "LocalDateTime", "neo4j.time.DateTime"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    # Neo4j Time / Duration
    if type_name in ("Time", "Duration"):
        return str(value)
    # Nested dict (e.g. already-converted compound)
    if isinstance(value, dict):
        return {k: _neo4j_to_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_neo4j_to_python(v) for v in value]
    return value


def _node_to_dict(node) -> dict:
    """Convert a Neo4j Node to a plain dict with all types serialised."""
    if node is None:
        return {}
    return {k: _neo4j_to_python(v) for k, v in dict(node).items()}


class BankingKnowledgeGraph:
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def init_schema(self):
        """Initialize graph schema with constraints and indexes"""
        with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
                "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT news_id IF NOT EXISTS FOR (n:News) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT financial_id IF NOT EXISTS FOR (f:Financial) REQUIRE f.id IS UNIQUE",
                "CREATE CONSTRAINT industry_code IF NOT EXISTS FOR (i:Industry) REQUIRE i.naics_code IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Constraint creation skipped: {e}")

            # Create indexes for performance
            indexes = [
                "CREATE INDEX company_ticker IF NOT EXISTS FOR (c:Company) ON (c.ticker)",
                "CREATE INDEX news_date IF NOT EXISTS FOR (n:News) ON (n.date)",
                "CREATE INDEX financial_period IF NOT EXISTS FOR (f:Financial) ON (f.period)",
                "CREATE INDEX company_sector IF NOT EXISTS FOR (c:Company) ON (c.sector)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"Index creation skipped: {e}")

    def create_company(self, name: str, ticker: str = None, website: str = None,
                      sector: str = None, naics: str = None, **attributes) -> Dict:
        """Create a company node"""
        with self.driver.session() as session:
            result = session.run("""
                MERGE (c:Company {name: $name})
                SET c.ticker = $ticker,
                    c.website = $website,
                    c.sector = $sector,
                    c.naics = $naics,
                    c.updated_at = datetime(),
                    c += $attributes
                RETURN c
            """, name=name, ticker=ticker, website=website, sector=sector,
               naics=naics, attributes=attributes)
            return result.single()["c"]

    def get_company_info_cache(self, company_name: str, max_age_days: int = 7) -> dict:
        """Return cached company_info if saved within max_age_days, else {}."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $name})
                WHERE c.info_json IS NOT NULL
                  AND (c.info_saved_at IS NULL
                       OR duration.between(c.info_saved_at, datetime()).days <= $max_age)
                RETURN c.info_json AS info_json
            """, name=company_name, max_age=max_age_days)
            row = result.single()
            if row and row["info_json"]:
                import json as _json
                try:
                    return _json.loads(row["info_json"])
                except Exception:
                    pass
        return {}

    def save_company_info_cache(self, company_name: str, info: dict) -> None:
        """Persist company_info JSON on the Company node."""
        import json as _json
        with self.driver.session() as session:
            session.run("""
                MERGE (c:Company {name: $name})
                SET c.info_json    = $info_json,
                    c.info_saved_at = datetime()
            """, name=company_name, info_json=_json.dumps(info))

    def get_peers_for_company(self, company_name: str, max_age_days: int = 180) -> list:
        """Return cached peer list stored on the Industry node or via IS_PEER_OF edges.
        Returns [] if nothing cached or older than max_age_days."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $name})-[:BELONGS_TO]->(i:Industry)
                WHERE i.peers_json IS NOT NULL
                  AND (i.peers_saved_at IS NULL
                       OR duration.between(i.peers_saved_at, datetime()).days <= $max_age)
                RETURN i.peers_json AS peers_json
                LIMIT 1
            """, name=company_name, max_age=max_age_days)
            row = result.single()
            if row and row["peers_json"]:
                import json as _json
                try:
                    return _dedup_peers_list(_json.loads(row["peers_json"]))
                except Exception:
                    pass
        return []

    def save_peers_for_company(self, company_name: str, peers: list) -> None:
        """Persist peer list JSON on the Industry node linked to this company."""
        import json as _json
        peers = _dedup_peers_list(peers)  # strip duplicates before persisting
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $name})-[:BELONGS_TO]->(i:Industry)
                SET i.peers_json      = $peers_json,
                    i.peers_saved_at  = datetime()
            """, name=company_name, peers_json=_json.dumps(peers))

    def list_companies(self) -> list:
        """Return all Company nodes as a list of {name, ticker, industry, headquarters}."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company)
                OPTIONAL MATCH (c)-[:BELONGS_TO]->(i:Industry)
                RETURN c.name AS name,
                       c.ticker AS ticker,
                       c.industry AS industry,
                       c.headquarters AS headquarters,
                       i.name AS industry_name
                ORDER BY c.name
            """)
            seen = set()
            companies = []
            for r in result:
                name = r["name"]
                if not name or name in seen:
                    continue
                seen.add(name)
                companies.append({
                    "name": name,
                    "ticker": r["ticker"] or "",
                    "industry": r["industry_name"] or r["industry"] or "",
                    "headquarters": r["headquarters"] or "",
                })
            return companies

    def add_financial_data(self, company_name: str, filing_type: str, period: str,
                          data: Dict[str, Any], source: str = "EDGAR") -> Dict:
        """Add financial filing data (10-K, 10-Q)"""
        import json
        with self.driver.session() as session:
            financial_id = f"{company_name}_{filing_type}_{period}"
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (f:Financial {id: $financial_id})
                SET f.filing_type              = $filing_type,
                    f.period                   = $period,
                    f.filing_period            = $period,
                    f.source                   = $source,
                    f.filing_date              = $filing_date,
                    f.updated_at               = datetime(),
                    f.revenue                  = $revenue,
                    f.gross_profit             = $gross_profit,
                    f.operating_income         = $operating_income,
                    f.ebitda                   = $ebitda,
                    f.net_income               = $net_income,
                    f.eps_basic                = $eps_basic,
                    f.eps_diluted              = $eps_diluted,
                    f.cash_and_equivalents     = $cash_and_equivalents,
                    f.cash                     = $cash_and_equivalents,
                    f.short_term_investments   = $short_term_investments,
                    f.total_current_assets     = $total_current_assets,
                    f.total_assets             = $total_assets,
                    f.total_current_liabilities= $total_current_liabilities,
                    f.long_term_debt           = $long_term_debt,
                    f.total_liabilities        = $total_liabilities,
                    f.stockholders_equity      = $stockholders_equity,
                    f.shares_outstanding       = $shares_outstanding,
                    f.operating_cash_flow      = $operating_cash_flow,
                    f.capital_expenditures     = $capital_expenditures,
                    f.free_cash_flow           = $free_cash_flow,
                    f.investing_cash_flow      = $investing_cash_flow,
                    f.financing_cash_flow      = $financing_cash_flow,
                    f.dividends_paid           = $dividends_paid,
                    f.share_repurchases        = $share_repurchases,
                    f.relevance_score          = $relevance_score,
                    f.data_json                = $data_json
                MERGE (c)-[:HAS_FILING]->(f)
                RETURN f
            """,
                company_name=company_name,
                financial_id=financial_id,
                filing_type=filing_type,
                period=period,
                source=source,
                filing_date=data.get("filing_date", ""),
                revenue=data.get("revenue"),
                gross_profit=data.get("gross_profit"),
                operating_income=data.get("operating_income"),
                ebitda=data.get("ebitda"),
                net_income=data.get("net_income"),
                eps_basic=data.get("eps_basic"),
                eps_diluted=data.get("eps_diluted"),
                cash_and_equivalents=data.get("cash_and_equivalents"),
                short_term_investments=data.get("short_term_investments"),
                total_current_assets=data.get("total_current_assets"),
                total_assets=data.get("total_assets"),
                total_current_liabilities=data.get("total_current_liabilities"),
                long_term_debt=data.get("long_term_debt"),
                total_liabilities=data.get("total_liabilities"),
                stockholders_equity=data.get("stockholders_equity"),
                shares_outstanding=data.get("shares_outstanding"),
                operating_cash_flow=data.get("operating_cash_flow"),
                capital_expenditures=data.get("capital_expenditures"),
                free_cash_flow=data.get("free_cash_flow"),
                investing_cash_flow=data.get("investing_cash_flow"),
                financing_cash_flow=data.get("financing_cash_flow"),
                dividends_paid=data.get("dividends_paid"),
                share_repurchases=data.get("share_repurchases"),
                relevance_score=data.get("relevance_score", 0.5),
                data_json=json.dumps(data),
            )
            rec = result.single()
            return dict(rec["f"]) if rec else None

    def add_news(self, company_name: str, title: str, summary: str, url: str,
                date: str, sentiment: str = "neutral", source: str = "web",
                severity: str = "low", event_types: list = None,
                is_material: bool = False, key_facts: list = None,
                relevance_score: float = 0.5) -> Dict:
        """Add negative/relevant news with classifier fields"""
        import json, re
        # Sanitise date — Cypher date() requires strict YYYY-MM-DD
        safe_date = date if date and re.match(r'^\d{4}-\d{2}-\d{2}$', str(date)) \
                    else __import__('datetime').datetime.now().strftime('%Y-%m-%d')
        with self.driver.session() as session:
            news_id = f"{company_name}_{hash(url)}"
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (n:News {id: $news_id})
                SET n.title = $title,
                    n.summary = $summary,
                    n.url = $url,
                    n.date = date($date),
                    n.sentiment = $sentiment,
                    n.severity = $severity,
                    n.event_types = $event_types,
                    n.is_material = $is_material,
                    n.key_facts = $key_facts,
                    n.source = $source,
                    n.relevance_score = $relevance_score,
                    n.timestamp = datetime()
                MERGE (c)-[:MENTIONED_IN]->(n)
                RETURN n
            """, company_name=company_name, news_id=news_id, title=title,
               summary=summary, url=url, date=safe_date, sentiment=sentiment, source=source,
               severity=severity,
               event_types=json.dumps(event_types or []),
               is_material=is_material,
               key_facts=json.dumps(key_facts or []),
               relevance_score=relevance_score)
            rec = result.single()
            return dict(rec["n"]) if rec else None

    def save_news_analysis(self, company_name: str, analysis: Dict) -> None:
        """Store the aggregate news_analysis on the Company node"""
        import json
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                SET c.news_analysis = $analysis_json
            """, company_name=company_name, analysis_json=json.dumps(analysis))

    def save_temporal_summary(self, company_name: str, summary: Dict) -> None:
        """Store the temporal/freshness summary on the Company node"""
        import json
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                SET c.temporal_summary = $summary_json,
                    c.freshness_updated_at = datetime()
            """, company_name=company_name, summary_json=json.dumps(summary))

    def add_product(self, company_name: str, product_name: str, category: str,
                   description: str, features: List[str] = None,
                   relevance_score: float = 0.5, **attributes) -> Dict:
        """Add product information"""
        with self.driver.session() as session:
            product_id = f"{company_name}_{product_name.replace(' ', '_')}"
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (p:Product {id: $product_id})
                SET p.name = $product_name,
                    p.category = $category,
                    p.description = $description,
                    p.features = $features,
                    p.relevance_score = $relevance_score,
                    p.timestamp = datetime(),
                    p += $attributes
                MERGE (c)-[:OFFERS]->(p)
                RETURN p
            """, company_name=company_name, product_id=product_id,
               product_name=product_name, category=category, description=description,
               features=features or [], relevance_score=relevance_score,
               attributes=attributes)
            rec = result.single()
            return dict(rec["p"]) if rec else None

    def link_to_industry(self, company_name: str, naics_code: str,
                        industry_name: str, sector: str,
                        naics_classification: Dict = None) -> None:
        """Link company to industry/sector, storing full NAICS classification."""
        extra = naics_classification or {}
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (i:Industry {naics_code: $naics_code})
                SET i.name           = $industry_name,
                    i.sector         = $sector,
                    i.naics_sector   = $naics_sector,
                    i.naics_subsector = $naics_subsector,
                    i.confidence     = $confidence,
                    i.reasoning      = $reasoning,
                    i.saved_at       = datetime(),
                    i.updated_at     = datetime()
                MERGE (c)-[:BELONGS_TO]->(i)
                SET c.naics_code     = $naics_code,
                    c.naics_sector   = $naics_sector,
                    c.naics_saved_at = datetime()
            """, company_name=company_name, naics_code=naics_code,
               industry_name=industry_name, sector=sector,
               naics_sector=extra.get("naics_sector", ""),
               naics_subsector=extra.get("industry_subsector", ""),
               confidence=extra.get("confidence", ""),
               reasoning=extra.get("reasoning", ""))

    def get_naics_for_company(self, company_name: str, max_age_days: int = 180) -> Dict:
        """Return the stored NAICS classification for a company if recent enough.
        Returns {} if not found or older than max_age_days.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $name})-[:BELONGS_TO]->(i:Industry)
                WHERE i.naics_code IS NOT NULL
                  AND i.naics_code <> ''
                  AND (i.saved_at IS NULL
                       OR duration.between(i.saved_at, datetime()).days <= $max_age)
                RETURN i
                ORDER BY i.saved_at DESC
                LIMIT 1
            """, name=company_name, max_age=max_age_days)
            record = result.single()
            if not record or not record["i"]:
                return {}
            return _node_to_dict(record["i"])

    def _resolve_canonical_peer_name(self, peer_name: str) -> str:
        """Return the existing canonical Company.name for this peer if one exists
        (matched case-insensitively or by normalized suffix-stripped form).
        If no match is found, return peer_name unchanged."""
        norm = _normalize_name(peer_name)
        with self.driver.session() as s:
            # 1. Exact case-insensitive match
            row = s.run(
                "MATCH (c:Company) WHERE toLower(c.name) = toLower($name) "
                "RETURN c.name LIMIT 1",
                name=peer_name,
            ).single()
            if row:
                return row["c.name"]
            # 2. Suffix-stripped match — load all Company names and compare
            if norm:
                rows = s.run("MATCH (c:Company) RETURN c.name").data()
                for r in rows:
                    if _normalize_name(r["c.name"]) == norm:
                        return r["c.name"]
        return peer_name

    def add_peer_relationship(self, company_name: str, peer_name: str,
                             similarity_score: float = None) -> None:
        """Add peer/competitor relationship"""
        peer_name = self._resolve_canonical_peer_name(peer_name)
        with self.driver.session() as session:
            session.run("""
                MATCH (c1:Company {name: $company_name})
                MERGE (c2:Company {name: $peer_name})
                MERGE (c1)-[r:PEER_OF]-(c2)
                SET r.similarity_score = $similarity_score,
                    r.updated_at = datetime()
            """, company_name=company_name, peer_name=peer_name,
               similarity_score=similarity_score)

    def add_officer(self, company_name: str, officer: Dict) -> None:
        """Store an officer profile linked to a company.
        Resolves duplicate name variants (e.g. 'Elon E Musk' → existing 'Elon Musk' node)
        by checking normalized name before creating a new node.
        """
        import json as _json
        raw_name = officer.get("name", "").strip()
        norm = _normalize_officer_name(raw_name)

        # Look for an existing officer node for this company with same normalized name
        with self.driver.session() as _s:
            existing = _s.run(
                "MATCH (c:Company)-[:HAS_OFFICER]->(o:Officer) "
                "WHERE toLower(c.name) = toLower($company_name) "
                "RETURN o.id AS oid, o.name AS oname ",
                company_name=company_name,
            ).data()
            resolved_id = None
            for row in existing:
                if _normalize_officer_name(row.get("oname") or "") == norm:
                    resolved_id = row["oid"]
                    break

        officer_id = resolved_id or f"{company_name}_{raw_name.replace(' ', '_')}"

        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (o:Officer {id: $officer_id})
                SET o.name                 = $name,
                    o.role                 = $role,
                    o.role_short           = $role_short,
                    o.company              = $company_name,
                    o.profiled             = $profiled,
                    o.background_summary   = $background_summary,
                    o.education            = $education,
                    o.previous_roles       = $previous_roles,
                    o.tenure_years         = $tenure_years,
                    o.linkedin_url         = $linkedin_url,
                    o.key_achievements     = $key_achievements,
                    o.recent_news          = $recent_news,
                    o.publications_speaking= $publications,
                    o.board_memberships    = $boards,
                    o.risk_flags           = $risk_flags,
                    o.banking_relevance    = $banking_relevance,
                    o.confidence           = $confidence,
                    o.researched_at        = $researched_at,
                    o.updated_at           = datetime()
                MERGE (c)-[:HAS_OFFICER]->(o)
            """,
            company_name=company_name,
            officer_id=officer_id,
            name=raw_name,
            role=officer.get("role", ""),
            role_short=officer.get("role_short", officer.get("role", "")[:6]),
            profiled=bool(officer.get("profiled", False)),
            background_summary=officer.get("background_summary", ""),
            education=_json.dumps(officer.get("education", [])),
            previous_roles=_json.dumps(officer.get("previous_roles", [])),
            tenure_years=officer.get("tenure_years"),
            linkedin_url=officer.get("linkedin_url"),
            key_achievements=_json.dumps(officer.get("key_achievements", [])),
            recent_news=_json.dumps(officer.get("recent_news", [])),
            publications=_json.dumps(officer.get("publications_speaking", [])),
            boards=_json.dumps(officer.get("board_memberships", [])),
            risk_flags=_json.dumps(officer.get("risk_flags", [])),
            banking_relevance=officer.get("banking_relevance", ""),
            confidence=officer.get("confidence", "low"),
            researched_at=officer.get("researched_at", ""),
            )

    def get_officers(self, company_name: str) -> List[Dict]:
        """Retrieve all officer profiles for a company.
        Uses case-insensitive name matching and merges officers from all
        name variants (e.g. 'Apple', 'APPLE', 'Apple Inc') to handle
        duplicate nodes created by inconsistent research runs.
        """
        import json as _json
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company)-[:HAS_OFFICER]->(o:Officer)
                WHERE toLower(c.name) = toLower($company_name)
                   OR toLower(c.name) CONTAINS toLower($company_name)
                   OR toLower($company_name) CONTAINS toLower(c.name)
                RETURN o
                ORDER BY o.role
            """, company_name=company_name)

            officers = []
            seen_names: set = set()
            for record in result:
                if record["o"]:
                    o = _node_to_dict(record["o"])
                    for field in ("education", "previous_roles", "key_achievements",
                                  "recent_news", "publications_speaking",
                                  "board_memberships", "risk_flags"):
                        raw = o.get(field)
                        if isinstance(raw, str):
                            try:
                                o[field] = _json.loads(raw)
                            except Exception:
                                o[field] = []
                    # Infer profiled from stored flag or data completeness
                    if "profiled" not in o or o["profiled"] is None:
                        bs = o.get("background_summary") or ""
                        o["profiled"] = bool(bs and bs != "Profile unavailable.")

                    # Deduplicate across name variants (handles 'Elon E Musk' vs 'Elon Musk')
                    key = _normalize_officer_name(o.get("name") or "")
                    if key and key not in seen_names:
                        seen_names.add(key)
                        officers.append(o)
                    elif key in seen_names:
                        # Keep the richer record: prefer profiled, then most board data
                        idx = next((i for i, x in enumerate(officers)
                                    if _normalize_officer_name(x.get("name") or "") == key), None)
                        if idx is not None:
                            existing = officers[idx]
                            challenger_score = (
                                int(bool(o.get("profiled"))) * 100
                                + len(o.get("board_memberships") or [])
                                + len(o.get("previous_roles") or [])
                            )
                            existing_score = (
                                int(bool(existing.get("profiled"))) * 100
                                + len(existing.get("board_memberships") or [])
                                + len(existing.get("previous_roles") or [])
                            )
                            if challenger_score > existing_score:
                                officers[idx] = o
            return officers

    def add_peer_financial_data(self, target_company: str, peer_name: str,
                                ticker: str, metrics: Dict) -> None:
        """Store EDGAR financial metrics for a peer company.

        Uses the same Company→HAS_FILING→Financial pattern as the main company
        so all cached filings are multi-period and share a universal TTL policy.
        A lightweight PeerCompany identity node is also kept for relationship
        traversal queries.
        """
        import json as _json
        # Normalise peer_name: resolve to canonical DB name (handles suffix variants)
        peer_name = self._resolve_canonical_peer_name(peer_name)
        filing_type   = metrics.get("filing_type", "10-K")
        filing_period = metrics.get("filing_period", "") or metrics.get("period", "")
        financial_id  = f"{peer_name}_{filing_type}_{filing_period}"

        with self.driver.session() as session:
            # 1. Upsert a Company node for the peer (lightweight — no full research)
            session.run("""
                MERGE (c:Company {name: $peer_name})
                ON CREATE SET c.ticker     = $ticker,
                              c.is_peer    = true,
                              c.created_at = datetime()
                ON MATCH  SET c.ticker     = $ticker,
                              c.is_peer    = true
            """, peer_name=peer_name, ticker=ticker)

            # 2. Write the financial filing node — same schema as add_financial_data
            session.run("""
                MATCH (c:Company {name: $peer_name})
                MERGE (f:Financial {id: $financial_id})
                SET f.filing_type              = $filing_type,
                    f.period                   = $filing_period,
                    f.filing_period            = $filing_period,
                    f.source                   = 'EDGAR_peer',
                    f.filing_date              = $filing_date,
                    f.updated_at               = datetime(),
                    f.revenue                  = $revenue,
                    f.gross_profit             = $gross_profit,
                    f.operating_income         = $operating_income,
                    f.ebitda                   = $ebitda,
                    f.net_income               = $net_income,
                    f.eps_basic                = $eps_basic,
                    f.eps_diluted              = $eps_diluted,
                    f.cash_and_equivalents     = $cash,
                    f.short_term_investments   = $short_term_investments,
                    f.total_current_assets     = $total_current_assets,
                    f.total_assets             = $total_assets,
                    f.total_current_liabilities= $total_current_liabilities,
                    f.long_term_debt           = $long_term_debt,
                    f.total_liabilities        = $total_liabilities,
                    f.stockholders_equity      = $equity,
                    f.shares_outstanding       = $shares_outstanding,
                    f.operating_cash_flow      = $ocf,
                    f.capital_expenditures     = $capex,
                    f.free_cash_flow           = $fcf,
                    f.investing_cash_flow      = $investing_cf,
                    f.financing_cash_flow      = $financing_cf
                MERGE (c)-[:HAS_FILING]->(f)
            """,
                peer_name=peer_name,
                financial_id=financial_id,
                filing_type=filing_type,
                filing_period=filing_period,
                filing_date=metrics.get("filing_date", ""),
                revenue=metrics.get("revenue"),
                gross_profit=metrics.get("gross_profit"),
                operating_income=metrics.get("operating_income"),
                ebitda=metrics.get("ebitda"),
                net_income=metrics.get("net_income"),
                eps_basic=metrics.get("eps_basic"),
                eps_diluted=metrics.get("eps_diluted"),
                cash=metrics.get("cash_and_equivalents"),
                short_term_investments=metrics.get("short_term_investments"),
                total_current_assets=metrics.get("total_current_assets"),
                total_assets=metrics.get("total_assets"),
                total_current_liabilities=metrics.get("total_current_liabilities"),
                long_term_debt=metrics.get("long_term_debt"),
                total_liabilities=metrics.get("total_liabilities"),
                equity=metrics.get("stockholders_equity"),
                shares_outstanding=metrics.get("shares_outstanding"),
                ocf=metrics.get("operating_cash_flow"),
                capex=metrics.get("capital_expenditures"),
                fcf=metrics.get("free_cash_flow"),
                investing_cf=metrics.get("investing_cash_flow"),
                financing_cf=metrics.get("financing_cash_flow"),
            )

            # 3. Keep a lightweight PeerCompany identity node for HAS_PEER traversals
            session.run("""
                MATCH (target:Company {name: $target})
                MERGE (peer:PeerCompany {name: $peer_name})
                SET peer.ticker         = $ticker,
                    peer.relationship   = $relationship,
                    peer.estimated_size = $estimated_size,
                    peer.updated_at     = datetime()
                MERGE (target)-[r:HAS_PEER]->(peer)
                SET r.updated_at = datetime()
            """,
                target=target_company,
                peer_name=peer_name,
                ticker=ticker,
                relationship=metrics.get("relationship", "industry_peer"),
                estimated_size=metrics.get("estimated_size", "unknown"),
            )

    def get_peer_comparison(self, company_name: str) -> Dict:
        """Return target company metrics alongside all peer EDGAR metrics."""
        with self.driver.session() as session:
            # Get target company financials (most recent filing)
            target_result = session.run("""
                MATCH (c:Company {name: $name})
                OPTIONAL MATCH (c)-[:HAS_FILING]->(f:Financial)
                WITH c, f
                ORDER BY f.filing_date DESC
                WITH c, collect(f)[0] AS latest_filing
                RETURN c, latest_filing
            """, name=company_name)
            target_record = target_result.single()

            if not target_record:
                return None

            company_node = _node_to_dict(target_record["c"]) if target_record["c"] else {}
            latest_f = _node_to_dict(target_record["latest_filing"]) if target_record["latest_filing"] else {}

            # Get all peer companies with their most-recent filing.
            # PeerCompany nodes may have financials stored directly on them (legacy)
            # or via a Company {ticker} → HAS_FILING → Financial chain (new schema).
            peers_result = session.run("""
                MATCH (c:Company {name: $name})-[:HAS_PEER]->(pci:PeerCompany)
                OPTIONAL MATCH (pc:Company)-[:HAS_FILING]->(f:Financial)
                WHERE pc.ticker = pci.ticker
                WITH pci, pc, f
                ORDER BY f.filing_date DESC
                WITH pci, pc, collect(f)[0] AS latest
                RETURN pci, pc, latest
                ORDER BY coalesce(latest.revenue, pci.revenue, 0) DESC
            """, name=company_name)

            peers = []
            for record in peers_result:
                pci  = _node_to_dict(record["pci"])  if record["pci"]   else {}
                pc   = _node_to_dict(record["pc"])   if record["pc"]    else {}
                f    = _node_to_dict(record["latest"]) if record["latest"] else {}
                # Fall back to financials stored directly on the PeerCompany node
                # (legacy schema wrote them there)
                entry = {
                    "name":               pci.get("name", pc.get("name", pci.get("ticker", ""))),
                    "ticker":             pci.get("ticker", pc.get("ticker")),
                    "relationship":       pci.get("relationship", "industry_peer"),
                    "estimated_size":     pci.get("estimated_size", "unknown"),
                    "revenue":            f.get("revenue") or pci.get("revenue"),
                    "net_income":         f.get("net_income") or pci.get("net_income"),
                    "operating_income":   f.get("operating_income") or pci.get("operating_income"),
                    "total_assets":       f.get("total_assets") or pci.get("total_assets"),
                    "stockholders_equity":f.get("stockholders_equity") or pci.get("stockholders_equity"),
                    "operating_cash_flow":f.get("operating_cash_flow") or pci.get("operating_cash_flow"),
                    "filing_period":      f.get("filing_period") or f.get("period") or pci.get("filing_period") or pci.get("period", ""),
                    "filing_type":        f.get("filing_type") or pci.get("filing_type", ""),
                }
                peers.append(entry)

            # Also include legacy PEER_OF linked Company nodes that have financials
            legacy_result = session.run("""
                MATCH (c:Company {name: $name})-[:PEER_OF]-(peer:Company)
                OPTIONAL MATCH (peer)-[:HAS_FILING]->(f:Financial)
                WITH peer, f
                ORDER BY f.filing_date DESC
                WITH peer, collect(f)[0] AS filing
                RETURN peer, filing
            """, name=company_name)

            legacy_peers = []
            for record in legacy_result:
                if record["peer"]:
                    p = _node_to_dict(record["peer"])
                    f = _node_to_dict(record["filing"]) if record["filing"] else {}
                    if f:
                        p.update({
                            "revenue": f.get("revenue"),
                            "net_income": f.get("net_income"),
                            "total_assets": f.get("total_assets"),
                            "operating_income": f.get("operating_income"),
                            "filing_period": f.get("period", ""),
                            "filing_type": f.get("filing_type", ""),
                        })
                    legacy_peers.append(p)

            # Merge HAS_PEER and legacy PEER_OF results, dedup by normalized name
            all_peers = peers + [p for p in legacy_peers if not any(
                ep["name"] == p["name"] for ep in peers
            )]
            seen: dict = {}
            deduped_peers = []
            for p in all_peers:
                key = _normalize_name(p.get("name") or p.get("ticker") or "")
                if not key:
                    continue
                if key not in seen:
                    seen[key] = len(deduped_peers)
                    deduped_peers.append(p)
                else:
                    # Keep entry with more financial data
                    idx = seen[key]
                    if p.get("revenue") and not deduped_peers[idx].get("revenue"):
                        deduped_peers[idx] = p

            return {
                "target": {
                    "name": company_name,
                    "ticker": company_node.get("ticker"),
                    "revenue": latest_f.get("revenue"),
                    "net_income": latest_f.get("net_income"),
                    "operating_income": latest_f.get("operating_income"),
                    "total_assets": latest_f.get("total_assets"),
                    "stockholders_equity": latest_f.get("stockholders_equity"),
                    "filing_period": latest_f.get("period", ""),
                    "filing_type": latest_f.get("filing_type", ""),
                },
                "peers": deduped_peers,
            }

    def get_financials_by_ticker(self, ticker: str, max_age_days: int = FINANCIAL_CACHE_TTL_DAYS) -> List[Dict]:
        """Return cached financial filings for a ticker from the graph.

        Searches Company→HAS_FILING→Financial for both full-research companies
        and peer companies (which now use the same storage pattern).
        The legacy flat PeerCompany fallback is kept for backwards compatibility.
        Returns [] if nothing found or all records are stale.
        """
        with self.driver.session() as session:
            # Company→HAS_FILING→Financial — covers both main companies and peers
            result = session.run("""
                MATCH (c:Company)
                WHERE toUpper(c.ticker) = toUpper($ticker)
                MATCH (c)-[:HAS_FILING]->(f:Financial)
                WHERE f.updated_at IS NULL
                   OR duration.between(f.updated_at, datetime()).days <= $max_age
                RETURN f
                ORDER BY f.filing_date DESC
                LIMIT 4
            """, ticker=ticker, max_age=max_age_days)
            rows = [_node_to_dict(r["f"]) for r in result if r["f"]]

            # Legacy fallback: flat PeerCompany nodes written by the old schema
            if not rows:
                result2 = session.run("""
                    MATCH (p:PeerCompany)
                    WHERE toUpper(p.ticker) = toUpper($ticker)
                      AND (p.updated_at IS NULL
                           OR duration.between(p.updated_at, datetime()).days <= $max_age)
                    RETURN p
                    LIMIT 1
                """, ticker=ticker, max_age=max_age_days)
                for r in result2:
                    if r["p"]:
                        node = _node_to_dict(r["p"])
                        rows.append({
                            "filing_period":      node.get("filing_period", ""),
                            "filing_type":        node.get("filing_type", "10-K"),
                            "revenue":            node.get("revenue"),
                            "net_income":         node.get("net_income"),
                            "operating_income":   node.get("operating_income"),
                            "total_assets":       node.get("total_assets"),
                            "total_liabilities":  node.get("total_liabilities"),
                            "stockholders_equity":node.get("stockholders_equity"),
                            "operating_cash_flow":node.get("operating_cash_flow"),
                            "_source": "legacy_peer_cache",
                        })
        return rows

    def get_financials_by_naics(self, naics_code: str, max_age_days: int = 90) -> List[Dict]:
        """Return all peer financial records for companies in a NAICS sector.
        Useful for skipping EDGAR calls when we already have data for the same sector.
        Returns a list of dicts: {name, ticker, filing_period, revenue, ...}
        """
        with self.driver.session() as session:
            # Companies with a matching NAICS industry node
            result = session.run("""
                MATCH (c:Company)-[:BELONGS_TO]->(i:Industry)
                WHERE i.naics_code STARTS WITH $prefix
                  OR  i.naics_sector = $prefix
                MATCH (c)-[:HAS_FILING]->(f:Financial)
                WHERE f.updated_at IS NULL
                   OR duration.between(f.updated_at, datetime()).days <= $max_age
                WITH c, f
                ORDER BY f.filing_date DESC
                WITH c, collect(f)[0] AS latest
                RETURN c.name AS name, c.ticker AS ticker, latest AS f
            """, prefix=naics_code[:2], max_age=max_age_days)

            companies = []
            for r in result:
                if r["f"]:
                    f = _node_to_dict(r["f"])
                    companies.append({
                        "name":    r["name"],
                        "ticker":  r["ticker"],
                        "filing_period": f.get("period", f.get("filing_period", "")),
                        "filing_type":   f.get("filing_type", ""),
                        "revenue":       f.get("revenue"),
                        "net_income":    f.get("net_income"),
                        "operating_income": f.get("operating_income"),
                        "total_assets":  f.get("total_assets"),
                        "stockholders_equity": f.get("stockholders_equity"),
                        "operating_cash_flow": f.get("operating_cash_flow"),
                    })

            # Also check PeerCompany nodes tagged with same NAICS via target company
            result2 = session.run("""
                MATCH (target:Company)-[:BELONGS_TO]->(i:Industry)
                WHERE i.naics_code STARTS WITH $prefix
                   OR i.naics_sector = $prefix
                MATCH (target)-[:HAS_PEER]->(p:PeerCompany)
                WHERE p.revenue IS NOT NULL
                  AND (p.updated_at IS NULL
                       OR duration.between(p.updated_at, datetime()).days <= $max_age)
                RETURN DISTINCT p.name AS name, p.ticker AS ticker,
                       p.filing_period AS filing_period, p.filing_type AS filing_type,
                       p.revenue AS revenue, p.net_income AS net_income,
                       p.operating_income AS operating_income,
                       p.total_assets AS total_assets,
                       p.stockholders_equity AS stockholders_equity,
                       p.operating_cash_flow AS operating_cash_flow
            """, prefix=naics_code[:2], max_age=max_age_days)

            seen = {c["name"] for c in companies}
            for r in result2:
                if r["name"] and r["name"] not in seen:
                    companies.append(dict(r))
                    seen.add(r["name"])

        return companies

    def get_company_graph(self, company_name: str, max_depth: int = 2) -> Dict:
        """Get complete company graph with all dimensions"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                OPTIONAL MATCH (c)-[r1:HAS_FILING]->(f:Financial)
                OPTIONAL MATCH (c)-[r2:MENTIONED_IN]->(n:News)
                OPTIONAL MATCH (c)-[r3:OFFERS]->(p:Product)
                OPTIONAL MATCH (c)-[r4:BELONGS_TO]->(i:Industry)
                OPTIONAL MATCH (c)-[r5:PEER_OF]-(peer:Company)
                RETURN c,
                       collect(DISTINCT f) as financials,
                       collect(DISTINCT n) as news,
                       collect(DISTINCT p) as products,
                       collect(DISTINCT i) as industries,
                       collect(DISTINCT peer) as peers
            """, company_name=company_name)

            record = result.single()
            if not record:
                return None

            import json
            # Parse news items — deserialise JSON-stored list fields
            news_items = []
            for n in record["news"]:
                if not n:
                    continue
                item = _node_to_dict(n)
                for field in ("event_types", "key_facts"):
                    raw = item.get(field)
                    if isinstance(raw, str):
                        try:
                            item[field] = json.loads(raw)
                        except Exception:
                            item[field] = []
                news_items.append(item)

            # Parse news_analysis stored on Company node
            company_data = _node_to_dict(record["c"])
            news_analysis = None
            raw_analysis = company_data.pop("news_analysis", None)
            if raw_analysis:
                try:
                    news_analysis = json.loads(raw_analysis)
                except Exception:
                    pass

            temporal_summary = None
            raw_temporal = company_data.pop("temporal_summary", None)
            if raw_temporal:
                try:
                    temporal_summary = json.loads(raw_temporal)
                except Exception:
                    pass

            # Unpack data_json for each financial node and normalise field names
            def _unpack_financial(node) -> dict:
                import json as _json
                item = _node_to_dict(node)
                try:
                    inner = _json.loads(item.get("data_json", "{}") or "{}")
                    # handle double-nested data_json
                    inner2 = _json.loads(inner.get("data_json", "{}") or "{}")
                    merged = {**inner2, **inner, **item}
                except Exception:
                    merged = item
                merged.pop("data_json", None)
                # Normalise field name aliases so FinancialMetrics always finds them
                aliases = {
                    "assets":     ["total_assets"],
                    "liabilities":["total_liabilities"],
                    "equity":     ["stockholders_equity", "shareholders_equity"],
                    "operating_income": ["operating_income"],
                }
                for target, sources in aliases.items():
                    if merged.get(target) is None:
                        for src in sources:
                            if merged.get(src) is not None:
                                merged[target] = merged[src]
                                break
                return merged

            unpacked = [_unpack_financial(f) for f in record["financials"] if f]

            # Count how many key metric fields are populated — used for dedup below
            _KEY_FIELDS = (
                "operating_income", "total_liabilities", "stockholders_equity",
                "operating_cash_flow", "long_term_debt", "gross_profit",
            )
            def _richness(f: dict) -> int:
                return sum(1 for k in _KEY_FIELDS if f.get(k) is not None)

            # Normalise period string so "2026-Q1" and "Q1 2026" collapse to the
            # same key, keeping only the richest record per period.
            import re as _re
            def _norm_period(p: str) -> str:
                p = (p or "").upper().strip()
                # "Q1 2026" / "2026-Q1" / "2026Q1" → "Q12026"
                m = _re.search(r"Q(\d)\s*[-]?\s*(\d{4})|(\d{4})\s*[-]?\s*Q(\d)", p)
                if m:
                    q, yr = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
                    return f"Q{q}{yr}"
                # "FY2024" / "2024" / "2025" → "FY2024"
                m2 = _re.search(r"(\d{4})", p)
                if m2:
                    return f"FY{m2.group(1)}"
                return p

            seen_periods: dict = {}  # norm_period → index in deduped list
            deduped: list = []
            for f in unpacked:
                period_str = f.get("filing_period") or f.get("period") or ""
                norm = _norm_period(period_str)
                if norm in seen_periods:
                    existing_idx = seen_periods[norm]
                    if _richness(f) > _richness(deduped[existing_idx]):
                        deduped[existing_idx] = f  # replace with richer record
                else:
                    seen_periods[norm] = len(deduped)
                    deduped.append(f)

            # Sort richest + most recent first
            deduped.sort(key=lambda f: (
                -_richness(f),
                -(int(str(f.get("filing_date", "") or "").replace("-", "")[:8] or 0)),
            ))

            return {
                "company": company_data,
                "financials": deduped,
                "news": news_items,
                "news_analysis": news_analysis,
                "temporal_summary": temporal_summary,
                "products": [_node_to_dict(p) for p in record["products"] if p],
                "industries": [_node_to_dict(i) for i in record["industries"] if i],
                "peers": [_node_to_dict(p) for p in record["peers"] if p]
            }

    def prune_old_data(self, company_name: str, days_threshold: int = 90) -> int:
        """Temporal dimension: Remove outdated news and data"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $company_name})-[:MENTIONED_IN]->(n:News)
                WHERE n.date < date() - duration({days: $days_threshold})
                DETACH DELETE n
                RETURN count(n) as deleted
            """, company_name=company_name, days_threshold=days_threshold)
            return result.single()["deleted"]

    def get_visualization_data(self, company_name: str) -> Dict[str, List]:
        """Get graph data formatted for visualization"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                OPTIONAL MATCH (c)-[r]-(other)
                RETURN c, collect(DISTINCT r) as relationships, collect(DISTINCT other) as nodes
            """, company_name=company_name)

            record = result.single()
            if not record:
                return {"nodes": [], "edges": []}

            def _node_id(n) -> str:
                """Pick the best display ID for any node type."""
                return n.get("name") or n.get("title") or n.get("id") or "unknown"

            def _clean_data(d: dict) -> dict:
                """Strip large blobs; parse JSON-string list fields."""
                import json as _json
                skip = {"data_json", "news_analysis", "temporal_summary"}
                out = {}
                for k, v in d.items():
                    if k in skip:
                        continue
                    # Try to parse JSON-encoded lists back to lists
                    if isinstance(v, str) and v.startswith("["):
                        try:
                            out[k] = _json.loads(v)
                            continue
                        except Exception:
                            pass
                    out[k] = v
                return out

            nodes = [{"id": company_name, "label": company_name, "type": "Company",
                      "data": _clean_data(_node_to_dict(record["c"]))}]
            edges = []
            seen_ids = {company_name}

            for rel in record["relationships"]:
                if rel:
                    src = _node_id(rel.start_node)
                    tgt = _node_id(rel.end_node)
                    edges.append({
                        "source": src,
                        "target": tgt,
                        "type": rel.type,
                    })

            for node in record["nodes"]:
                if node:
                    node_labels = list(node.labels)
                    node_type = node_labels[0] if node_labels else "Unknown"
                    node_id = _node_id(node)
                    if node_id in seen_ids:
                        continue
                    seen_ids.add(node_id)
                    raw = _node_to_dict(node)
                    nodes.append({
                        "id": node_id,
                        "label": node_id,
                        "type": node_type,
                        "data": _clean_data(raw),
                    })

            return {"nodes": nodes, "edges": edges}

    def clear_company_data(self, company_name: str) -> None:
        """Clear all data for a company"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                OPTIONAL MATCH (c)-[r]->(n)
                WHERE NOT n:Industry AND NOT n:Company
                DETACH DELETE n
                DELETE r
            """, company_name=company_name)

    # ── RM Activity Log ───────────────────────────────────────────────────────

    def add_activity(self, company_name: str, activity: Dict) -> str:
        """Log an RM activity (call, email, meeting) against a company."""
        import json as _json, uuid as _uuid
        activity_id = activity.get("id") or str(_uuid.uuid4())
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company)
                WHERE toLower(c.name) = toLower($company_name)
                   OR toLower(c.name) CONTAINS toLower($company_name)
                   OR toLower($company_name) CONTAINS toLower(c.name)
                WITH c LIMIT 1
                MERGE (a:Activity {id: $activity_id})
                SET a.type          = $type,
                    a.date          = $date,
                    a.contact_name  = $contact_name,
                    a.contact_role  = $contact_role,
                    a.notes         = $notes,
                    a.next_action   = $next_action,
                    a.created_at    = datetime()
                MERGE (c)-[:HAS_ACTIVITY]->(a)
            """,
            company_name=company_name,
            activity_id=activity_id,
            type=activity.get("type", "call"),
            date=activity.get("date", ""),
            contact_name=activity.get("contact_name", ""),
            contact_role=activity.get("contact_role", ""),
            notes=activity.get("notes", ""),
            next_action=activity.get("next_action", ""),
            )
        return activity_id

    def get_activities(self, company_name: str) -> List[Dict]:
        """Get all RM activities for a company, newest first."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company)-[:HAS_ACTIVITY]->(a:Activity)
                WHERE toLower(c.name) = toLower($company_name)
                   OR toLower(c.name) CONTAINS toLower($company_name)
                   OR toLower($company_name) CONTAINS toLower(c.name)
                RETURN a ORDER BY a.date DESC
            """, company_name=company_name)
            return [_node_to_dict(r["a"]) for r in result if r["a"]]

    def delete_activity(self, activity_id: str) -> None:
        with self.driver.session() as session:
            session.run("MATCH (a:Activity {id: $id}) DETACH DELETE a",
                        id=activity_id)

    # ── Prior Deals / Existing Products ──────────────────────────────────────

    def add_deal(self, company_name: str, deal: Dict) -> str:
        """Record an existing or past WF deal / product relationship."""
        import uuid as _uuid
        deal_id = deal.get("id") or str(_uuid.uuid4())
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company)
                WHERE toLower(c.name) = toLower($company_name)
                   OR toLower(c.name) CONTAINS toLower($company_name)
                   OR toLower($company_name) CONTAINS toLower(c.name)
                WITH c LIMIT 1
                MERGE (d:Deal {id: $deal_id})
                SET d.product       = $product,
                    d.category      = $category,
                    d.status        = $status,
                    d.amount        = $amount,
                    d.start_date    = $start_date,
                    d.notes         = $notes,
                    d.created_at    = datetime()
                MERGE (c)-[:HAS_DEAL]->(d)
            """,
            company_name=company_name,
            deal_id=deal_id,
            product=deal.get("product", ""),
            category=deal.get("category", ""),
            status=deal.get("status", "active"),
            amount=deal.get("amount", ""),
            start_date=deal.get("start_date", ""),
            notes=deal.get("notes", ""),
            )
        return deal_id

    def get_deals(self, company_name: str) -> List[Dict]:
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company)-[:HAS_DEAL]->(d:Deal)
                WHERE toLower(c.name) = toLower($company_name)
                   OR toLower(c.name) CONTAINS toLower($company_name)
                   OR toLower($company_name) CONTAINS toLower(c.name)
                RETURN d ORDER BY d.start_date DESC
            """, company_name=company_name)
            return [_node_to_dict(r["d"]) for r in result if r["d"]]

    def delete_deal(self, deal_id: str) -> None:
        with self.driver.session() as session:
            session.run("MATCH (d:Deal {id: $id}) DETACH DELETE d", id=deal_id)

    # ── Portfolio View ────────────────────────────────────────────────────────

    def get_portfolio_summary(self) -> List[Dict]:
        """Return all companies with summary stats for the RM portfolio view."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company)
                WHERE c.name <> 'Wells Fargo'
                OPTIONAL MATCH (c)-[:HAS_FILING]->(f:Financial)
                OPTIONAL MATCH (c)-[:HAS_ACTIVITY]->(a:Activity)
                OPTIONAL MATCH (c)-[:HAS_DEAL]->(d:Deal)
                OPTIONAL MATCH (c)-[:MENTIONED_IN]->(n:News)
                RETURN c,
                       count(DISTINCT f) as fin_count,
                       count(DISTINCT a) as activity_count,
                       count(DISTINCT d) as deal_count,
                       count(DISTINCT n) as news_count,
                       max(a.date) as last_contact
                ORDER BY c.name
            """)
            rows = []
            for r in result:
                company = _node_to_dict(r["c"])
                # Skip duplicate/garbage names
                name = company.get("name", "").strip()
                if not name:
                    continue
                rows.append({
                    "name": name,
                    "ticker": company.get("ticker", ""),
                    "industry": company.get("industry", ""),
                    "headquarters": company.get("headquarters", ""),
                    "fin_count": r["fin_count"],
                    "activity_count": r["activity_count"],
                    "deal_count": r["deal_count"],
                    "news_count": r["news_count"],
                    "last_contact": r["last_contact"],
                    "naics_code": company.get("naics_code", ""),
                    "naics_sector": company.get("naics_sector", ""),
                })
            # Deduplicate by lowercase name
            seen = set()
            deduped = []
            for row in rows:
                key = row["name"].lower().strip()
                if key not in seen:
                    seen.add(key)
                    deduped.append(row)
            return deduped

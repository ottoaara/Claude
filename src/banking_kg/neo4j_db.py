from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
import os
from datetime import datetime


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

    def add_financial_data(self, company_name: str, filing_type: str, period: str,
                          data: Dict[str, Any], source: str = "EDGAR") -> Dict:
        """Add financial filing data (10-K, 10-Q)"""
        import json
        with self.driver.session() as session:
            financial_id = f"{company_name}_{filing_type}_{period}"
            flat_data = {
                "revenue": data.get("revenue"),
                "net_income": data.get("net_income"),
                "total_assets": data.get("total_assets"),
                "cash": data.get("cash_and_equivalents"),
                "data_json": json.dumps(data),
                "relevance_score": data.get("relevance_score", 0.5),
                "filing_date": data.get("filing_date", ""),
            }
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (f:Financial {id: $financial_id})
                SET f.filing_type = $filing_type,
                    f.period = $period,
                    f.source = $source,
                    f.revenue = $revenue,
                    f.net_income = $net_income,
                    f.total_assets = $total_assets,
                    f.cash = $cash,
                    f.data_json = $data_json,
                    f.relevance_score = $relevance_score,
                    f.filing_date = $filing_date,
                    f.timestamp = datetime()
                MERGE (c)-[:HAS_FILING]->(f)
                RETURN f
            """, company_name=company_name, financial_id=financial_id,
               filing_type=filing_type, period=period, source=source, **flat_data)
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
                        industry_name: str, sector: str) -> None:
        """Link company to industry/sector"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (i:Industry {naics_code: $naics_code})
                SET i.name = $industry_name,
                    i.sector = $sector,
                    i.updated_at = datetime()
                MERGE (c)-[:BELONGS_TO]->(i)
            """, company_name=company_name, naics_code=naics_code,
               industry_name=industry_name, sector=sector)

    def add_peer_relationship(self, company_name: str, peer_name: str,
                             similarity_score: float = None) -> None:
        """Add peer/competitor relationship"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c1:Company {name: $company_name})
                MERGE (c2:Company {name: $peer_name})
                MERGE (c1)-[r:PEER_OF]-(c2)
                SET r.similarity_score = $similarity_score,
                    r.updated_at = datetime()
            """, company_name=company_name, peer_name=peer_name,
               similarity_score=similarity_score)

    def add_peer_financial_data(self, target_company: str, peer_name: str,
                                ticker: str, metrics: Dict) -> None:
        """Store EDGAR financial metrics on a PeerCompany node linked to the target."""
        import json as _json
        with self.driver.session() as session:
            session.run("""
                MATCH (target:Company {name: $target})
                MERGE (peer:PeerCompany {name: $peer_name})
                SET peer.ticker            = $ticker,
                    peer.relationship      = $relationship,
                    peer.estimated_size    = $estimated_size,
                    peer.filing_type       = $filing_type,
                    peer.filing_period     = $filing_period,
                    peer.revenue           = $revenue,
                    peer.net_income        = $net_income,
                    peer.operating_income  = $operating_income,
                    peer.total_assets      = $total_assets,
                    peer.total_liabilities = $total_liabilities,
                    peer.stockholders_equity = $equity,
                    peer.operating_cash_flow = $ocf,
                    peer.updated_at        = datetime()
                MERGE (target)-[r:HAS_PEER]->(peer)
                SET r.updated_at = datetime()
            """,
            target=target_company,
            peer_name=peer_name,
            ticker=ticker,
            relationship=metrics.get("relationship", "industry_peer"),
            estimated_size=metrics.get("estimated_size", "unknown"),
            filing_type=metrics.get("filing_type", "10-K"),
            filing_period=metrics.get("filing_period", ""),
            revenue=metrics.get("revenue"),
            net_income=metrics.get("net_income"),
            operating_income=metrics.get("operating_income"),
            total_assets=metrics.get("total_assets"),
            total_liabilities=metrics.get("total_liabilities"),
            equity=metrics.get("stockholders_equity"),
            ocf=metrics.get("operating_cash_flow"),
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

            # Get all peer companies with their financials
            peers_result = session.run("""
                MATCH (c:Company {name: $name})-[:HAS_PEER]->(peer:PeerCompany)
                RETURN peer
                ORDER BY peer.revenue DESC
            """, name=company_name)

            peers = []
            for record in peers_result:
                if record["peer"]:
                    peers.append(_node_to_dict(record["peer"]))

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
                "peers": peers + [p for p in legacy_peers if not any(
                    ep["name"] == p["name"] for ep in peers
                )],
            }

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

            return {
                "company": company_data,
                "financials": [_node_to_dict(f) for f in record["financials"] if f],
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

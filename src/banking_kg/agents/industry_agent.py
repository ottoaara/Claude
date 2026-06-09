from typing import Dict, List
from ..llm_factory import robust_parse_json
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ddgs import DDGS
import json
import re
import datetime


NAICS_SECTORS = {
    "11": "Agriculture, Forestry, Fishing and Hunting",
    "21": "Mining, Quarrying, and Oil and Gas Extraction",
    "22": "Utilities",
    "23": "Construction",
    "31-33": "Manufacturing",
    "42": "Wholesale Trade",
    "44-45": "Retail Trade",
    "48-49": "Transportation and Warehousing",
    "51": "Information",
    "52": "Finance and Insurance",
    "53": "Real Estate and Rental and Leasing",
    "54": "Professional, Scientific, and Technical Services",
    "55": "Management of Companies and Enterprises",
    "56": "Administrative and Support Services",
    "61": "Educational Services",
    "62": "Health Care and Social Assistance",
    "71": "Arts, Entertainment, and Recreation",
    "72": "Accommodation and Food Services",
    "81": "Other Services",
    "92": "Public Administration",
}

_NAICS_LIST = "\n".join(f"{k}: {v}" for k, v in NAICS_SECTORS.items())


def _ddg_search(query: str, max_results: int = 6) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        return "\n".join(
            f"[{i+1}] {r.get('title', '')}: {r.get('body', '')[:200]}"
            for i, r in enumerate(results)
        )
    except Exception as e:
        return f"Search error: {e}"


# ---------------------------------------------------------------------------
# Tools — pure data retrieval, no internal LLM calls
# ---------------------------------------------------------------------------

@tool
def search_competitors(company_name: str, industry: str) -> str:
    """Search for direct competitors and peer companies of a given company.
    Returns raw web search results about competitors."""
    q1 = f"{company_name} top direct competitors publicly traded stock ticker"
    q2 = f"{company_name} {industry} rival companies peer comparison"
    r1 = _ddg_search(q1, max_results=6)
    r2 = _ddg_search(q2, max_results=5)
    return f"=== Competitor search: {q1} ===\n{r1}\n\n=== Peer search: {q2} ===\n{r2}"


@tool
def search_industry_trends(industry: str) -> str:
    """Search for current industry trends, growth outlook, and market dynamics.
    Returns raw web search results about the industry."""
    query = f"{industry} industry trends outlook 2025 2026 growth challenges banking"
    return _ddg_search(query, max_results=6)


@tool
def get_naics_reference() -> str:
    """Returns the NAICS sector classification table for reference."""
    return f"NAICS Sectors:\n{_NAICS_LIST}"


# ---------------------------------------------------------------------------
# Peer deduplication
# ---------------------------------------------------------------------------

_CORP_SUFFIXES = re.compile(
    r"\b(inc\.?|corp\.?|co\.?|llc\.?|ltd\.?|plc\.?|corporation|company|group|holdings?|"
    r"automotive|motors?|technologies|technology|systems?|solutions?|international|"
    r"enterprises?|industries?)\b",
    re.IGNORECASE,
)

def _normalize_peer_name(name: str) -> str:
    """Strip corporate suffixes and punctuation for fuzzy matching."""
    s = _CORP_SUFFIXES.sub("", name.lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _dedup_peers(peers: List[Dict]) -> List[Dict]:
    """
    Remove duplicate peer entries produced by the LLM (e.g. 'General Motors'
    and 'General Motors Co' both in the same list).
    Priority: keep the entry with a valid ticker; on tie, keep first seen.
    Deduplication keys (in order):
      1. Exact ticker match (non-null)
      2. Normalized name match (stripped of corporate suffixes)
    """
    seen_tickers: dict = {}   # ticker -> index in output list
    seen_names: dict = {}     # normalized name -> index in output list
    output: List[Dict] = []

    for peer in peers:
        ticker = (peer.get("ticker") or "").strip().upper() or None
        norm = _normalize_peer_name(peer.get("company_name") or "")

        # 1. Ticker dedup
        if ticker:
            if ticker in seen_tickers:
                # Keep the one with more data (longer company_name wins)
                existing_idx = seen_tickers[ticker]
                existing = output[existing_idx]
                if len(peer.get("company_name", "")) > len(existing.get("company_name", "")):
                    output[existing_idx] = peer
                continue
            seen_tickers[ticker] = len(output)

        # 2. Normalized-name dedup
        if norm:
            if norm in seen_names:
                existing_idx = seen_names[norm]
                existing = output[existing_idx]
                # Prefer entry that has a ticker
                if ticker and not (existing.get("ticker") or "").strip():
                    output[existing_idx] = peer
                    if ticker:
                        seen_tickers[ticker] = existing_idx
                continue
            seen_names[norm] = len(output)

        output.append(peer)

    return output


# ---------------------------------------------------------------------------
# NAICS sector filter — hard rule: peers must be in the same sector
# ---------------------------------------------------------------------------

# Well-known companies and their NAICS 2-digit sector codes.
# Used to reject cross-sector hallucinations (e.g. Apple/Amazon as auto peers).
_KNOWN_SECTORS: Dict[str, str] = {
    # Information / Tech (51)
    "AAPL": "51", "MSFT": "51", "GOOGL": "51", "GOOG": "51",
    "META": "51", "NFLX": "51", "SNAP": "51", "TWTR": "51",
    "UBER": "51", "LYFT": "51", "ABNB": "51", "SPOT": "51",
    "CRM": "51", "ORCL": "51", "SAP": "51", "ADBE": "51",
    "INTC": "51", "AMD": "51", "NVDA": "51", "QCOM": "51",
    "IBM": "51", "HPE": "51", "HPQ": "51", "DELL": "51",
    # Retail / E-commerce (44-45)
    "AMZN": "44", "WMT": "44", "TGT": "44", "COST": "44",
    "HD": "44", "LOW": "44", "EBAY": "44", "ETSY": "44",
    # Finance / Insurance (52)
    "JPM": "52", "BAC": "52", "WFC": "52", "C": "52",
    "GS": "52", "MS": "52", "AXP": "52", "V": "52", "MA": "52",
    "BRK.B": "52", "BRK.A": "52",
    # Health Care (62)
    "JNJ": "62", "PFE": "62", "MRK": "62", "ABBV": "62",
    "UNH": "62", "CVS": "62", "MCK": "62",
    # Energy (21)
    "XOM": "21", "CVX": "21", "COP": "21", "SLB": "21",
    # Utilities (22)
    "NEE": "22", "DUK": "22", "SO": "22", "AEP": "22",
    # Food / Beverages — Manufacturing (31-33) subset but often confused
    "KO": "31", "PEP": "31", "MCD": "72", "SBUX": "72",
}

_MFG_SECTOR_CODES = {"31", "32", "33", "31-33"}


def _naics_matches(sector_a: str, sector_b: str) -> bool:
    """Return True if two NAICS 2-digit sector codes are in the same bucket.
    Manufacturing is split 31/32/33 but treated as one sector (31-33)."""
    def _bucket(s: str) -> str:
        s = str(s).strip().split("-")[0]  # "31-33" → "31"
        if s in ("31", "32", "33"):
            return "31"
        return s
    return _bucket(sector_a) == _bucket(sector_b)


def _filter_peers_by_naics(peers: List[Dict], company_naics_sector: str) -> List[Dict]:
    """Remove peers that belong to a clearly different NAICS sector.
    Only applied when we have a confident sector classification.
    """
    if not company_naics_sector or company_naics_sector in ("", "99", "unknown"):
        return peers

    filtered = []
    for peer in peers:
        ticker = (peer.get("ticker") or "").upper().strip()
        peer_sector = _KNOWN_SECTORS.get(ticker)
        if peer_sector and not _naics_matches(peer_sector, company_naics_sector):
            print(f"   ⚠️  Dropping peer {peer.get('company_name')} ({ticker}) "
                  f"— sector {peer_sector} ≠ company sector {company_naics_sector}")
            continue
        filtered.append(peer)
    return filtered


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

INDUSTRY_TOOLS = [search_competitors, search_industry_trends, get_naics_reference]

SYSTEM_PROMPT = f"""You are an expert commercial banking industry analyst. Produce a comprehensive industry analysis by calling the available tools, then synthesise everything into a single JSON response.

NAICS sectors for reference:
{_NAICS_LIST}

Steps:
1. Call search_competitors to find direct peers/rivals with their tickers
2. Call search_industry_trends to get current industry outlook
3. Optionally call get_naics_reference if needed

After gathering data, respond with ONLY this JSON (no prose):
{{{{
  "naics_classification": {{{{
    "naics_sector": "2-digit code",
    "naics_sector_name": "sector name",
    "naics_code": "4-6 digit code",
    "industry_subsector": "specific subsector",
    "confidence": "high|medium|low"
  }}}},
  "peer_companies": [
    {{{{
      "company_name": "name",
      "ticker": "US ticker or null",
      "relationship": "direct_competitor|industry_peer|market_adjacent",
      "estimated_size": "larger|similar|smaller",
      "key_difference": "one sentence"
    }}}}
  ],
  "industry_trends": {{{{
    "growth_outlook": "strong|moderate|weak|declining",
    "key_trends": ["trend1", "trend2"],
    "opportunities": ["opp1"],
    "challenges": ["challenge1"],
    "risk_factors": ["risk1"],
    "summary": "2-3 sentences"
  }}}},
  "industry_comparison": null
}}}}

HARD RULE — Peer sector constraint: ALL peer companies MUST operate in the SAME NAICS sector as the subject company.
Do NOT list companies from other sectors — for example, do NOT include Apple, Amazon, Google, Microsoft, or any tech/retail/finance company as a peer for a manufacturer.
If a competitor search returns off-sector companies, ignore them.

Peer rules: 4-6 peers, US-listed tickers only, prioritise direct competitors in the same NAICS sector, no invented tickers."""


class IndustryAgent:
    """ReAct tool-calling agent for industry analysis.
    Tools are pure search functions — all synthesis done by Claude in one pass.
    Public interface identical to the old pipeline.
    """

    def __init__(self):
        import os
        from ..llm_factory import get_llm
        self.llm = get_llm(temperature=0)
        self._use_react = os.getenv("LLM_PROVIDER", "anthropic").lower() != "ollama"
        if self._use_react:
            self.agent = create_react_agent(
                self.llm,
                INDUSTRY_TOOLS,
                prompt=SYSTEM_PROMPT,
            )
        else:
            self.agent = None

    def get_comprehensive_industry_analysis(
        self,
        company_name: str,
        industry: str,
        company_description: str = None,
        financials: Dict = None,
    ) -> Dict:
        fin_note = ""
        if financials:
            fin_note = f"\n\nFinancials summary: revenue={financials.get('revenue')}, net_income={financials.get('net_income')}, total_assets={financials.get('total_assets')}"

        user_message = (
            f"Analyse: {company_name}\n"
            f"Industry: {industry}\n"
            f"Description: {company_description or 'Not provided'}"
            f"{fin_note}"
        )

        _TIMEOUT_SECONDS = 60

        parsed = {}

        if not self._use_react:
            # ── Ollama fallback: gather search data manually, then one LLM call ──
            try:
                competitors_raw = _ddg_search(
                    f"{company_name} top direct competitors publicly traded stock ticker", max_results=6
                )
                trends_raw = _ddg_search(
                    f"{industry or company_name} industry trends outlook 2025 2026", max_results=5
                )
                from langchain_core.messages import SystemMessage, HumanMessage as _HM
                system_content = (
                    "You are a commercial banking industry analyst.\n"
                    "Based on the search results below, return ONLY a JSON object with these exact fields:\n"
                    '{\n'
                    '  "naics_classification": {\n'
                    '    "naics_sector": "2-digit code",\n'
                    '    "naics_sector_name": "sector name",\n'
                    '    "naics_code": "4-6 digit code",\n'
                    '    "industry_subsector": "specific subsector",\n'
                    '    "confidence": "high"\n'
                    '  },\n'
                    '  "peer_companies": [\n'
                    '    {\n'
                    '      "company_name": "name",\n'
                    '      "ticker": "US ticker symbol or null",\n'
                    '      "relationship": "direct_competitor",\n'
                    '      "estimated_size": "larger|similar|smaller",\n'
                    '      "key_difference": "one sentence"\n'
                    '    }\n'
                    '  ],\n'
                    '  "industry_trends": {\n'
                    '    "growth_outlook": "strong|moderate|weak|declining",\n'
                    '    "key_trends": ["trend1", "trend2"],\n'
                    '    "opportunities": ["opp1"],\n'
                    '    "challenges": ["challenge1"],\n'
                    '    "risk_factors": ["risk1"],\n'
                    '    "summary": "2-3 sentences"\n'
                    '  },\n'
                    '  "industry_comparison": null\n'
                    '}\n'
                    "HARD RULE: ALL peers MUST be in the SAME NAICS sector as the subject company.\n"
                    "Do NOT include Apple, Amazon, Google, Microsoft, or any company from a different industry.\n"
                    "For an auto/EV manufacturer, only include other auto or EV companies.\n"
                    "Return 4-6 real publicly traded US peers with correct tickers. No invented tickers.\n"
                    f"NAICS reference:\n{_NAICS_LIST}"
                )
                user_content = (
                    f"Company: {company_name}\n"
                    f"Industry: {industry or 'Unknown'}\n"
                    f"Description: {company_description or 'Not provided'}\n\n"
                    f"Competitor search results:\n{competitors_raw[:3000]}\n\n"
                    f"Industry trend results:\n{trends_raw[:2000]}"
                )
                raw = self.llm.invoke([
                    SystemMessage(content=system_content),
                    HumanMessage(content=user_content),
                ]).content
                parsed = robust_parse_json(raw, {})
            except Exception as e:
                print(f"❌ IndustryAgent (Ollama fallback) error: {e}")
        else:
            # ── ReAct agent path (Anthropic/Claude) ──
            def _invoke():
                return self.agent.invoke(
                    {"messages": [HumanMessage(content=user_message)]},
                    config={"recursion_limit": 5},
                )

            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
                with ThreadPoolExecutor(max_workers=1) as _pool:
                    future = _pool.submit(_invoke)
                    try:
                        result = future.result(timeout=_TIMEOUT_SECONDS)
                    except FuturesTimeout:
                        future.cancel()
                        raise TimeoutError(f"IndustryAgent timed out after {_TIMEOUT_SECONDS}s")
                messages = result.get("messages", [])
                output = ""
                for msg in reversed(messages):
                    content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                    if content and not getattr(msg, "tool_calls", None):
                        output = content
                        break
                parsed = robust_parse_json(output, {})
            except Exception as e:
                print(f"❌ IndustryAgent error: {e}")
                parsed = {}

        return {
            "company_name": company_name,
            "naics_classification": parsed.get("naics_classification", {
                "naics_sector": "99", "naics_sector_name": "Unknown", "naics_code": ""
            }),
            "peer_companies": _filter_peers_by_naics(
                _dedup_peers(parsed.get("peer_companies", [])),
                (parsed.get("naics_classification") or {}).get("naics_sector", ""),
            ),
            "industry_trends": parsed.get("industry_trends", {
                "growth_outlook": "unknown", "key_trends": []
            }),
            "industry_comparison": parsed.get("industry_comparison"),
            "analyzed_at": datetime.datetime.now().isoformat(),
        }

    # Legacy shims
    def classify_naics(self, company_name: str, industry: str, description: str = None) -> Dict:
        r = self.get_comprehensive_industry_analysis(company_name, industry, description)
        return r.get("naics_classification", {})

    def find_peer_companies(self, company_name: str, naics_code: str, industry: str) -> List[Dict]:
        r = self.get_comprehensive_industry_analysis(company_name, industry)
        return r.get("peer_companies", [])

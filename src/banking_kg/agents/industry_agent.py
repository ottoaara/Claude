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

Peer rules: 4-6 peers, US-listed tickers only, prioritise direct competitors, no invented tickers."""


class IndustryAgent:
    """ReAct tool-calling agent for industry analysis.
    Tools are pure search functions — all synthesis done by Claude in one pass.
    Public interface identical to the old pipeline.
    """

    def __init__(self):
        from ..llm_factory import get_llm
        self.llm = get_llm(temperature=0)
        self.agent = create_react_agent(
            self.llm,
            INDUSTRY_TOOLS,
            prompt=SYSTEM_PROMPT,
        )

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

        _TIMEOUT_SECONDS = 60  # hard wall-clock limit — prevents infinite DDG hangs

        def _invoke():
            return self.agent.invoke(
                {"messages": [HumanMessage(content=user_message)]},
                config={"recursion_limit": 8},
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
            import traceback; traceback.print_exc()
            parsed = {}

        return {
            "company_name": company_name,
            "naics_classification": parsed.get("naics_classification", {
                "naics_sector": "99", "naics_sector_name": "Unknown", "naics_code": ""
            }),
            "peer_companies": _dedup_peers(parsed.get("peer_companies", [])),
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

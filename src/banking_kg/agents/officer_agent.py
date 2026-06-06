"""
OfficerAgent — PRD Dimension: Officer Intelligence

Responsibilities:
  - Discover C-suite and board members at a company from multiple sources:
      • DuckDuckGo web search (general leadership queries)
      • Company website leadership/management/about/team pages
      • SEC DEF 14A proxy statement (named executive officers + directors)
      • Wikipedia (company page often lists current leadership)
      • Press releases (appointments, promotions)
      • Forbes / Bloomberg / Crunchbase profiles
  - Build a deep professional profile per officer via web search
  - Support manual lookup: given any name + company, build a profile
  - Surface risk flags, board seats, publications, banking relevance
  - Return source attribution for discovered individuals
"""

from typing import Dict, List, Optional
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from ddgs import DDGS
import os
import json
import re
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
    _SCRAPE_AVAILABLE = True
except ImportError:
    _SCRAPE_AVAILABLE = False


class OfficerAgent:
    """Researches key executives and officers at a target company."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            temperature=0,
            max_tokens=4096,
        )

    # ── Search / scrape helpers ──────────────────────────────────────────────

    def _search(self, query: str, max_results: int = 8) -> List[Dict]:
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            print(f"   Officer search error for '{query}': {e}")
            return []

    def _slim(self, hits: List[Dict], max_items: int = 15) -> List[Dict]:
        return [
            {
                "title": h.get("title", "")[:120],
                "snippet": h.get("body", h.get("snippet", ""))[:250],
                "url": h.get("href", h.get("url", "")),
            }
            for h in hits[:max_items]
        ]

    def _fetch_page_text(self, url: str, max_chars: int = 4000) -> str:
        """Fetch a URL and return cleaned visible text."""
        if not _SCRAPE_AVAILABLE:
            return ""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
            r = requests.get(url, headers=headers, timeout=8)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = " ".join(soup.get_text(separator=" ").split())
            return text[:max_chars]
        except Exception:
            return ""

    def _parse_json(self, text: str):
        text = text.strip()
        if "```" in text:
            for part in text.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("[") or part.startswith("{"):
                    text = part
                    break
        return json.loads(text)

    # ── Multi-source officer discovery ───────────────────────────────────────

    def _search_leadership_page(self, company_name: str) -> List[Dict]:
        """Find the company's leadership/team/about page and scrape it."""
        hits = self._search(
            f'site:{company_name.lower().replace(" ", "")}.com leadership OR management OR executives OR "board of directors"',
            max_results=3,
        )
        if not hits:
            hits = self._search(
                f'"{company_name}" company website leadership team executives page',
                max_results=4,
            )
        results = []
        for h in hits[:2]:
            url = h.get("href") or h.get("url", "")
            text = self._fetch_page_text(url, max_chars=3000)
            if text:
                results.append({"source": "company_website", "url": url, "text": text})
        return results

    def _search_sec_proxy(self, company_name: str, ticker: str = "") -> List[Dict]:
        """Search for SEC DEF 14A proxy statement which lists named executives."""
        query = f'"{company_name}" SEC DEF 14A proxy named executive officers directors 2024 OR 2025 OR 2026'
        if ticker:
            query = f'{ticker} SEC DEF 14A proxy statement named executive officers'
        hits = self._search(query, max_results=5)
        return self._slim(hits, 5)

    def _search_wikipedia(self, company_name: str) -> str:
        """Fetch Wikipedia company page for leadership section."""
        hits = self._search(f'Wikipedia "{company_name}" executives CEO leadership', max_results=3)
        for h in hits:
            url = h.get("href") or h.get("url", "")
            if "wikipedia.org" in url:
                text = self._fetch_page_text(url, max_chars=3000)
                if text:
                    return text
        return ""

    def _search_press_releases(self, company_name: str) -> List[Dict]:
        """Find press releases announcing executive appointments."""
        hits = self._search(
            f'"{company_name}" appoints OR announces OR "named" CEO OR CFO OR COO OR president OR chief 2023 OR 2024 OR 2025 OR 2026',
            max_results=6,
        )
        return self._slim(hits, 6)

    def _search_investor_relations(self, company_name: str) -> List[Dict]:
        """Investor relations pages often list governance / leadership."""
        hits = self._search(
            f'"{company_name}" investor relations corporate governance leadership team',
            max_results=4,
        )
        return self._slim(hits, 4)

    def find_officers(self, company_name: str, ticker: str = "") -> List[Dict]:
        """
        Return a deduplicated list of named executives and board members
        aggregated from multiple public sources.
        """
        print(f"      Discovering officers from multiple sources...")

        # Source 1: general web search
        general_hits = self._search(
            f'"{company_name}" CEO CFO COO president "chief" officer board directors leadership',
            max_results=10,
        )

        # Source 2: press releases
        pr_hits = self._search_press_releases(company_name)

        # Source 3: SEC proxy
        sec_hits = self._search_sec_proxy(company_name, ticker)

        # Source 4: Wikipedia
        wiki_text = self._search_wikipedia(company_name)

        # Source 5: Investor relations / governance
        ir_hits = self._search_investor_relations(company_name)

        # Aggregate all text evidence
        all_snippets = self._slim(general_hits + pr_hits + sec_hits + ir_hits, 25)
        extra_text = wiki_text[:1500] if wiki_text else ""

        if not all_snippets and not extra_text:
            return []

        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract key executives and board members from the provided search results and supplementary text.
Return a JSON array where each element has:
- name: Full name (string) — REQUIRED, skip unnamed mentions
- role: Full title (e.g. "Chief Executive Officer", "Chief Financial Officer", "Lead Independent Director")
- role_short: Abbreviation (e.g. "CEO", "CFO", "COO", "CTO", "CMO", "CLO", "GC", "Board Chair", "Director")
- tenure_since: Year they took the role (integer) or null
- is_board: true if primarily a board/director role, false if executive
- source_hint: one of ["website", "sec_proxy", "press_release", "wikipedia", "news", "search"]

Include up to 12 most senior or recently announced named individuals.
Deduplicate by name — if same person appears in multiple sources, keep one entry.
Return ONLY valid JSON array, no markdown."""),
            ("user", (
                f"Company: {company_name}\n\n"
                f"Search snippets:\n{json.dumps(all_snippets, indent=2)}\n\n"
                + (f"Additional text (Wikipedia/website):\n{extra_text}\n" if extra_text else "")
            )),
        ])

        try:
            chain = prompt | self.llm
            result = self._parse_json(chain.invoke({}).content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"   Error finding officers for {company_name}: {e}")
            return []

    # ── Individual officer deep-dive ─────────────────────────────────────────

    def research_officer(self, name: str, company: str, role: str = "") -> Dict:
        """Build a comprehensive profile for a named individual."""
        queries = [
            f'"{name}" {company} {role} biography career background education',
            f'"{name}" LinkedIn profile executive',
            f'"{name}" news 2024 OR 2025 OR 2026',
            f'"{name}" interview speech publication OR article OR keynote OR Forbes OR Bloomberg',
            f'"{name}" {company} SEC filing compensation proxy',
        ]

        all_hits: List[Dict] = []
        for q in queries:
            all_hits.extend(self._search(q, max_results=5))

        if not all_hits:
            return self._empty_profile(name, company, role, "No search results found")

        slim = self._slim(all_hits, max_items=25)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a commercial banking relationship intelligence analyst.
Build a professional profile from search results. Return a JSON object with:
- name: Full name
- role: Current title
- company: Company name
- background_summary: 3-4 sentence professional background (focus on banking/lending-relevant facts)
- education: List of known credentials (strings), [] if unknown
- previous_roles: List of prior roles (strings, e.g. "CFO at Goldman Sachs 2018–2022"), up to 5
- tenure_years: Estimated years in current role (number) or null
- linkedin_url: LinkedIn URL if found in results, else null
- key_achievements: List of 2-3 notable achievements relevant to the company or banking
- recent_news: List of up to 3 recent news items as strings (headline + brief context)
- publications_speaking: Known articles, books, or speaking engagements (strings), [] if none
- board_memberships: Other board seats held (strings), [] if none
- risk_flags: Concerning items a banker should know — litigation, regulatory, controversies (strings), [] if none
- banking_relevance: 2-sentence note on why this person matters to a commercial banking relationship
- confidence: "high" | "medium" | "low" — how confident you are in the profile accuracy

Return ONLY valid JSON object, no markdown."""),
            ("user", f"Person: {name}\nRole: {role}\nCompany: {company}\n\nSearch results:\n{json.dumps(slim, indent=2)}"),
        ])

        try:
            chain = prompt | self.llm
            result = self._parse_json(chain.invoke({}).content)
            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")
            result.setdefault("name", name)
            result.setdefault("role", role)
            result.setdefault("company", company)
            result["researched_at"] = datetime.now().isoformat()
            return result
        except Exception as e:
            print(f"   Error researching officer {name}: {e}")
            return self._empty_profile(name, company, role, str(e))

    # ── Batch research ───────────────────────────────────────────────────────

    def get_comprehensive_officer_intelligence(self, company_name: str, ticker: str = "") -> Dict:
        """
        Discover ALL officers from multiple public sources, then deep-profile the top 6.
        Returns all discovered officers (with profiled flag) so the UI can show the full list.
        """
        print(f"   Finding officers for {company_name} via multiple sources...")
        all_officers = self.find_officers(company_name, ticker)
        print(f"   Found {len(all_officers)} officers total")

        profiles = []
        # Profile top 6 executives (non-board first, then board members)
        executives = [o for o in all_officers if not o.get("is_board")]
        board      = [o for o in all_officers if o.get("is_board")]
        to_profile = (executives + board)[:6]

        for officer in to_profile:
            name = officer.get("name", "").strip()
            role = officer.get("role", officer.get("role_short", ""))
            if not name:
                continue
            print(f"   Profiling {name} ({role})...")
            profile = self.research_officer(name, company_name, role)
            merged  = {**officer, **profile, "profiled": True}
            profiles.append(merged)

        # Add remaining discovered-but-not-profiled officers
        profiled_names = {p["name"].lower() for p in profiles}
        for officer in all_officers:
            if officer.get("name", "").lower() not in profiled_names:
                profiles.append({**officer, "profiled": False})

        return {
            "company_name": company_name,
            "officers": profiles,
            "total_found": len(all_officers),
            "total_profiled": len(to_profile),
            "researched_at": datetime.now().isoformat(),
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_profile(name: str, company: str, role: str, error: str) -> Dict:
        return {
            "name": name,
            "role": role,
            "company": company,
            "background_summary": "Profile unavailable.",
            "education": [],
            "previous_roles": [],
            "tenure_years": None,
            "linkedin_url": None,
            "key_achievements": [],
            "recent_news": [],
            "publications_speaking": [],
            "board_memberships": [],
            "risk_flags": [],
            "banking_relevance": "",
            "confidence": "low",
            "error": error,
            "researched_at": datetime.now().isoformat(),
        }



class OfficerAgent:
    """Researches key executives and officers at a target company."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            temperature=0,
            max_tokens=4096,
        )

    # ── Search helper ────────────────────────────────────────────────────────

    def _search(self, query: str, max_results: int = 8) -> List[Dict]:
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            print(f"   Officer search error for '{query}': {e}")
            return []

    def _slim(self, hits: List[Dict], max_items: int = 15) -> List[Dict]:
        return [
            {
                "title": h.get("title", "")[:120],
                "snippet": h.get("body", h.get("snippet", ""))[:250],
                "url": h.get("href", h.get("url", "")),
            }
            for h in hits[:max_items]
        ]

    def _parse_json(self, text: str):
        text = text.strip()
        if "```" in text:
            for part in text.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("[") or part.startswith("{"):
                    text = part
                    break
        return json.loads(text)

    # ── Officer discovery ────────────────────────────────────────────────────

    def find_officers(self, company_name: str) -> List[Dict]:
        """Return a list of named executives and board members."""
        hits = self._search(
            f'"{company_name}" CEO CFO COO president "chief" officer board directors leadership team',
            max_results=10,
        )
        if not hits:
            return []

        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract key executives and board members from search results.
Return a JSON array where each element has:
- name: Full name (string) — REQUIRED, skip unnamed mentions
- role: Full title (e.g. "Chief Executive Officer", "Chief Financial Officer")
- role_short: Abbreviation (e.g. "CEO", "CFO", "COO", "CTO", "CMO", "CLO", "Board Chair", "Director")
- tenure_since: Year they took the role (integer) or null
- is_board: true if primarily a board/director role, false if executive

Include 4-8 most senior named individuals. Return ONLY valid JSON array."""),
            ("user", f"Company: {company_name}\n\nSearch results:\n{json.dumps(self._slim(hits), indent=2)}"),
        ])

        try:
            chain = prompt | self.llm
            result = self._parse_json(chain.invoke({}).content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"   Error finding officers for {company_name}: {e}")
            return []

    # ── Individual officer deep-dive ─────────────────────────────────────────

    def research_officer(self, name: str, company: str, role: str = "") -> Dict:
        """Build a comprehensive profile for a named individual."""
        queries = [
            f'"{name}" {company} {role} biography career background',
            f'"{name}" LinkedIn executive profile',
            f'"{name}" news 2024 OR 2025 OR 2026',
            f'"{name}" interview speech publication OR article OR keynote',
        ]

        all_hits: List[Dict] = []
        for q in queries:
            all_hits.extend(self._search(q, max_results=5))

        if not all_hits:
            return self._empty_profile(name, company, role, "No search results found")

        slim = self._slim(all_hits, max_items=20)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a commercial banking relationship intelligence analyst.
Build a professional profile from search results. Return a JSON object with:
- name: Full name
- role: Current title
- company: Company name
- background_summary: 3-4 sentence professional background (focus on banking/lending-relevant facts)
- education: List of known credentials (strings), [] if unknown
- previous_roles: List of prior roles (strings, e.g. "CFO at Goldman Sachs 2018–2022"), up to 5
- tenure_years: Estimated years in current role (number) or null
- linkedin_url: LinkedIn URL if found in results, else null
- key_achievements: List of 2-3 notable achievements
- recent_news: List of up to 3 recent news items as strings (headline + brief context)
- publications_speaking: Known articles, books, or speaking engagements (strings), [] if none
- board_memberships: Other board seats held (strings), [] if none
- risk_flags: Concerning items a banker should know — litigation, regulatory, controversies (strings), [] if none
- banking_relevance: 2-sentence note on why this person matters to a commercial banking relationship
- confidence: "high" | "medium" | "low" — how confident you are in the profile accuracy

Return ONLY valid JSON object, no markdown."""),
            ("user", f"Person: {name}\nRole: {role}\nCompany: {company}\n\nSearch results:\n{json.dumps(slim, indent=2)}"),
        ])

        try:
            chain = prompt | self.llm
            result = self._parse_json(chain.invoke({}).content)
            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")
            result.setdefault("name", name)
            result.setdefault("role", role)
            result.setdefault("company", company)
            result["researched_at"] = datetime.now().isoformat()
            return result
        except Exception as e:
            print(f"   Error researching officer {name}: {e}")
            return self._empty_profile(name, company, role, str(e))

    # ── Batch research ───────────────────────────────────────────────────────

    def get_comprehensive_officer_intelligence(self, company_name: str) -> Dict:
        """Discover officers and build profiles for the top 4."""
        print(f"   Finding officers for {company_name}...")
        officers = self.find_officers(company_name)
        print(f"   Found {len(officers)} officers")

        profiles = []
        for officer in officers[:4]:   # cap at 4 to control cost/time
            name = officer.get("name", "").strip()
            role = officer.get("role", officer.get("role_short", ""))
            if not name:
                continue
            print(f"   Profiling {name} ({role})...")
            profile = self.research_officer(name, company_name, role)
            # Merge discovery fields into profile (profile overrides)
            merged = {**officer, **profile}
            profiles.append(merged)

        return {
            "company_name": company_name,
            "officers": profiles,
            "total_found": len(officers),
            "researched_at": datetime.now().isoformat(),
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_profile(name: str, company: str, role: str, error: str) -> Dict:
        return {
            "name": name,
            "role": role,
            "company": company,
            "background_summary": "Profile unavailable.",
            "education": [],
            "previous_roles": [],
            "tenure_years": None,
            "linkedin_url": None,
            "key_achievements": [],
            "recent_news": [],
            "publications_speaking": [],
            "board_memberships": [],
            "risk_flags": [],
            "banking_relevance": "",
            "confidence": "low",
            "error": error,
            "researched_at": datetime.now().isoformat(),
        }

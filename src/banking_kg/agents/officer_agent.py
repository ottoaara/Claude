"""
OfficerAgent — PRD Dimension: Officer Intelligence

Responsibilities:
  - Discover C-suite and board members at a company
  - Build a deep professional profile per officer via web search
  - Support manual lookup: given any name + company, build a profile
  - Surface risk flags, board seats, publications, banking relevance
"""

from typing import Dict, List
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from ddgs import DDGS
import os
import json
from datetime import datetime


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

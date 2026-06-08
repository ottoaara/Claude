from typing import Dict, List
from ..llm_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
from ddgs import DDGS
import os
import json
from datetime import datetime, timedelta

from .news_classifier import NewsClassifier


class NewsAgent:
    """Agent for finding and analyzing negative/relevant news about companies"""

    def __init__(self):
        self.llm = get_llm(temperature=0)
        self.classifier = NewsClassifier()

    def _search(self, query: str, max_results: int = 10, timelimit: str = None) -> List[Dict]:
        """Run a DuckDuckGo text search and return raw result dicts."""
        try:
            with DDGS() as ddgs:
                kwargs = {"max_results": max_results}
                if timelimit:
                    kwargs["timelimit"] = timelimit
                return list(ddgs.text(query, **kwargs))
        except Exception as e:
            print(f"Search error for '{query}': {e}")
            return []

    def search_negative_news(self, company_name: str, days_back: int = 120) -> List[Dict]:
        """Search for negative news about a company within the last `days_back` days."""
        from datetime import datetime, timedelta

        # DDG timelimit: "d"=day, "w"=week, "m"=month, "y"=year
        # Map days_back to the nearest supported bucket
        if days_back <= 7:
            timelimit = "w"
        elif days_back <= 31:
            timelimit = "m"
        else:
            timelimit = "y"  # DDG max; we post-filter below to exact cutoff

        cutoff = datetime.utcnow() - timedelta(days=days_back)

        search_queries = [
            f'"{company_name}" lawsuit OR scandal OR investigation OR fraud',
            f'"{company_name}" layoffs OR restructuring OR bankruptcy',
            f'"{company_name}" recall OR violation OR fine OR penalty',
            f'"{company_name}" controversy OR complaint OR misconduct',
        ]

        all_results = []
        for query in search_queries:
            hits = self._search(query, max_results=5, timelimit=timelimit)
            # Post-filter: drop articles whose parsed date is older than cutoff
            fresh = []
            for h in hits:
                raw_date = h.get("date") or h.get("published") or ""
                if raw_date:
                    try:
                        from dateutil import parser as _dp
                        article_dt = _dp.parse(raw_date, ignoretz=True)
                        if article_dt < cutoff:
                            continue
                    except Exception:
                        pass  # can't parse date — keep the article
                fresh.append(h)
            if fresh:
                all_results.append({"query": query, "results": fresh})

        return self._process_search_results(company_name, all_results)

    def _process_search_results(self, company_name: str, search_results: List[Dict]) -> List[Dict]:
        """Process and filter search results using Claude"""

        # Slim down the payload — only send title + body snippet per result
        slim = []
        for group in search_results:
            for hit in group.get("results", []):
                if isinstance(hit, dict):
                    slim.append({
                        "title": hit.get("title", "")[:120],
                        "snippet": hit.get("body", hit.get("snippet", ""))[:300],
                        "url": hit.get("href", hit.get("url", "")),
                    })

        if not slim:
            return []

        # Cap at 15 items to keep response size predictable
        slim = slim[:15]

        processing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are analyzing news search results for negative/concerning news about a company.

Return a JSON array of relevant news items with these fields ONLY:
- title: News headline (string)
- summary: 2-3 sentence summary (string)
- url: Source URL (string)
- date: Publication date estimate YYYY-MM-DD (string)
- severity: "high" | "medium" | "low"
- category: "legal" | "financial" | "regulatory" | "operational" | "reputational"

Rules:
- Only include news genuinely about THIS company
- Only include negative/concerning news (lawsuits, fines, scandals, layoffs, etc.)
- Return [] if nothing qualifies
- Return ONLY the JSON array, no other text"""),
            ("user", "Company: {company_name}\n\nArticles to evaluate:\n{results}")
        ])

        try:
            chain = processing_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "results": json.dumps(slim, indent=2, ensure_ascii=True)
            })

            response_text = response.content.strip()
            # Strip any markdown fences
            if "```" in response_text:
                parts = response_text.split("```")
                for part in parts:
                    part = part.strip().lstrip("json").strip()
                    if part.startswith("["):
                        response_text = part
                        break

            news_items = json.loads(response_text)

            for item in news_items:
                item["company_name"] = company_name
                item["discovered_at"] = datetime.now().isoformat()

            return news_items

        except Exception as e:
            print(f"Error processing search results: {e}")
            return []

    def search_general_news(self, company_name: str) -> List[Dict]:
        """Search for general recent news (not just negative)"""

        try:
            hits = self._search(f'"{company_name}" news 2025 OR 2026', max_results=10)
            if not hits:
                return []

            processing_prompt = ChatPromptTemplate.from_messages([
                ("system", """Extract news items from search results.
Return JSON array with:
- title: News headline
- summary: 1-2 sentence summary
- url: Source URL
- date: Publication date estimate (YYYY-MM-DD)
- sentiment: "positive" | "neutral" | "negative"
- relevance: "high" | "medium" | "low"

Include only recent, relevant news items."""),
                ("user", "Company: {company_name}\n\nSearch results:\n{results}")
            ])

            chain = processing_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "results": json.dumps(hits, indent=2)
            })

            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Error searching general news: {e}")
            return []

    def analyze_news_sentiment(self, news_items: List[Dict]) -> Dict:
        """Analyze overall news sentiment and risk level"""

        if not news_items:
            return {
                "overall_sentiment": "neutral",
                "risk_level": "low",
                "summary": "No significant news found"
            }

        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a commercial banking risk analyst reviewing recent news about a company.
Based on the news items, provide:
- overall_sentiment: "positive" | "neutral" | "negative"
- risk_level: "low" | "medium" | "high"
- key_concerns: List of top 2-3 concerns for a commercial lender
- positive_signals: List of any positive signals (if any)
- summary: 2-3 sentence overall assessment

Return valid JSON."""),
            ("user", "Analyze these news items:\n{news}")
        ])

        try:
            chain = analysis_prompt | self.llm
            response = chain.invoke({"news": json.dumps(news_items, indent=2)})

            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {
                "error": str(e),
                "overall_sentiment": "unknown",
                "risk_level": "unknown"
            }

    def get_comprehensive_news_analysis(self, company_name: str) -> Dict:
        """Get comprehensive news analysis for a company"""

        # Search for both negative and general news
        negative_news = self.search_negative_news(company_name)
        general_news = self.search_general_news(company_name)

        # Combine and deduplicate
        all_news = negative_news + general_news
        unique_news = list({item.get("title", ""): item for item in all_news}.values())

        # Classify each item (sentiment, severity, event types, material flag)
        classified = self.classifier.classify_batch(company_name, unique_news)

        # Remove noise / promotional content
        classified = self.classifier.filter_noise(classified)

        # Aggregate into overall risk profile
        analysis = self.classifier.aggregate(company_name, classified)

        return {
            "company_name": company_name,
            "news_items": classified,
            "analysis": analysis,
            "total_items": len(classified),
            "negative_count": sum(1 for n in classified if n.get("sentiment") == "negative"),
            "material_event_count": sum(1 for n in classified if n.get("is_material")),
            "analyzed_at": datetime.now().isoformat()
        }

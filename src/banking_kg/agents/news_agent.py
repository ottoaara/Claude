from typing import Dict, List
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults
import os
import json
from datetime import datetime, timedelta


class NewsAgent:
    """Agent for finding and analyzing negative/relevant news about companies"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            temperature=0
        )
        self.search_tool = DuckDuckGoSearchResults(num_results=10)

    def search_negative_news(self, company_name: str, days_back: int = 90) -> List[Dict]:
        """Search for negative news about a company"""

        # Search queries focused on negative news
        search_queries = [
            f'"{company_name}" lawsuit OR scandal OR investigation OR fraud',
            f'"{company_name}" layoffs OR restructuring OR bankruptcy',
            f'"{company_name}" recall OR violation OR fine OR penalty',
            f'"{company_name}" controversy OR complaint OR misconduct'
        ]

        all_results = []
        for query in search_queries:
            try:
                results = self.search_tool.run(query)
                all_results.append({"query": query, "results": results})
            except Exception as e:
                print(f"Error searching for '{query}': {e}")
                continue

        return self._process_search_results(company_name, all_results)

    def _process_search_results(self, company_name: str, search_results: List[Dict]) -> List[Dict]:
        """Process and filter search results using Claude"""

        processing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are analyzing news search results for negative/concerning news about a company.
For each search result, determine:
1. Is it actually about this company? (avoid false positives)
2. Is it negative/concerning news? (lawsuits, scandals, financial trouble, regulatory issues, etc.)
3. Is it recent and relevant?

Return a JSON array of relevant news items with:
- title: News headline
- summary: 2-3 sentence summary of the issue
- url: Source URL (extract from snippet if available)
- date: Publication date (estimate if not exact)
- severity: "high" | "medium" | "low"
- category: Type of issue (e.g., "legal", "financial", "regulatory", "operational")

Only include genuinely negative/concerning news. Return empty array [] if no relevant news found."""),
            ("user", "Company: {company_name}\n\nSearch results:\n{results}")
        ])

        try:
            chain = processing_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "results": json.dumps(search_results, indent=2)
            })

            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            news_items = json.loads(response_text)

            # Add metadata
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
            query = f'"{company_name}" news'
            results = self.search_tool.run(query)

            processing_prompt = ChatPromptTemplate.from_messages([
                ("system", """Extract news items from search results.
Return JSON array with:
- title: News headline
- summary: 1-2 sentence summary
- url: Source URL
- date: Publication date estimate
- sentiment: "positive" | "neutral" | "negative"
- relevance: "high" | "medium" | "low" (relevance to commercial banking assessment)

Include only recent, relevant news items."""),
                ("user", "Company: {company_name}\n\nSearch results:\n{results}")
            ])

            chain = processing_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "results": results
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
        unique_news = {item.get("title", ""): item for item in all_news}.values()
        unique_news = list(unique_news)

        # Analyze sentiment
        sentiment_analysis = self.analyze_news_sentiment(unique_news)

        return {
            "company_name": company_name,
            "news_items": unique_news,
            "analysis": sentiment_analysis,
            "total_items": len(unique_news),
            "negative_count": sum(1 for n in unique_news if n.get("sentiment") == "negative"),
            "analyzed_at": datetime.now().isoformat()
        }

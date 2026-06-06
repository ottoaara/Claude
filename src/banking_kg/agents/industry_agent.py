from typing import Dict, List
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from ddgs import DDGS
import os
import json


# NAICS sector mapping
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
    "92": "Public Administration"
}


class IndustryAgent:
    """Agent for industry analysis and NAICS classification"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            temperature=0,
            max_tokens=4096,
        )

    def _search(self, query: str, max_results: int = 5) -> str:
        """Search the web with DuckDuckGo and return a formatted string of results."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No results found."
            return "\n".join(
                f"[{i+1}] {r.get('title', '')}\n{r.get('body', '')}"
                for i, r in enumerate(results)
            )
        except Exception as e:
            return f"Search error: {e}"

    def classify_naics(self, company_name: str, industry: str,
                      description: str = None) -> Dict:
        """Classify company into NAICS sector and code"""

        sectors_list = "\n".join([f"{code}: {name}" for code, name in NAICS_SECTORS.items()])

        classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are classifying a company into the NAICS (North American Industry Classification System).

Available NAICS sectors:
11: Agriculture, Forestry, Fishing and Hunting
21: Mining, Quarrying, and Oil and Gas Extraction
22: Utilities
23: Construction
31-33: Manufacturing
42: Wholesale Trade
44-45: Retail Trade
48-49: Transportation and Warehousing
51: Information
52: Finance and Insurance
53: Real Estate and Rental and Leasing
54: Professional, Scientific, and Technical Services
55: Management of Companies and Enterprises
56: Administrative and Support Services
61: Educational Services
62: Health Care and Social Assistance
71: Arts, Entertainment, and Recreation
72: Accommodation and Food Services
81: Other Services
92: Public Administration

Return JSON with:
- naics_sector: The 2-digit sector code (e.g., "52")
- naics_sector_name: Full sector name
- naics_code: More specific 4-6 digit NAICS code (make best estimate)
- industry_subsector: More specific industry classification
- confidence: "high" | "medium" | "low"
- reasoning: Brief explanation of classification"""),
            ("user", """Company: {company_name}
Industry: {industry}
Description: {description}

Classify this company into NAICS sectors.""")
        ])

        try:
            chain = classification_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "industry": industry or "Unknown",
                "description": description or "No description"
            })

            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Error classifying NAICS: {e}")
            return {
                "naics_sector": "99",
                "naics_sector_name": "Unknown",
                "error": str(e)
            }

    def find_peer_companies(self, company_name: str, naics_code: str,
                           industry: str) -> List[Dict]:
        """Find peer/competitor companies in the same industry"""

        try:
            # Search for competitors
            query = f"{industry} companies competitors peers NAICS {naics_code}"
            search_results = self._search(query, max_results=8)

            peer_prompt = ChatPromptTemplate.from_messages([
                ("system", """Extract peer/competitor companies from search results.
Return a JSON array of objects, each with:
- company_name: Competitor name (string)
- ticker: Stock ticker symbol if publicly traded, or null (e.g. "AAPL", "MSFT")
- relationship: "direct_competitor" | "industry_peer" | "market_adjacent"
- estimated_size: "larger" | "similar" | "smaller"
- key_difference: Brief note on main difference

Include 3-5 most relevant peers. Exclude the original company.
Return ONLY valid JSON array, no prose."""),
                ("user", "Original company: {company_name}\nIndustry: {industry}\n\nSearch results:\n{results}")
            ])

            chain = peer_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "industry": industry,
                "results": search_results
            })

            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Error finding peers: {e}")
            return []

    def get_industry_trends(self, industry: str, naics_sector: str) -> Dict:
        """Get industry trends and outlook"""

        try:
            query = f"{industry} industry trends outlook 2024 2025 {naics_sector}"
            search_results = self._search(query, max_results=6)

            trends_prompt = ChatPromptTemplate.from_messages([
                ("system", """Analyze industry trends from search results.
Return JSON with:
- growth_outlook: "strong" | "moderate" | "weak" | "declining"
- key_trends: List of 3-5 major trends
- opportunities: List of 2-3 opportunities
- challenges: List of 2-3 challenges
- risk_factors: List of 2-3 risk factors for companies in this industry
- summary: 2-3 sentence summary

Focus on information relevant to commercial banking and lending decisions."""),
                ("user", "Industry: {industry}\nNAICS Sector: {naics_sector}\n\nSearch results:\n{results}")
            ])

            chain = trends_prompt | self.llm
            response = chain.invoke({
                "industry": industry,
                "naics_sector": naics_sector,
                "results": search_results
            })

            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Error getting industry trends: {e}")
            return {
                "error": str(e),
                "growth_outlook": "unknown"
            }

    def compare_to_industry(self, company_financials: Dict,
                           industry_avg: Dict = None) -> Dict:
        """Compare company metrics to industry averages"""

        # Generate mock industry averages if not provided
        if not industry_avg:
            industry_avg = self._generate_industry_benchmarks(company_financials)

        comparison_prompt = ChatPromptTemplate.from_messages([
            ("system", """Compare company performance to industry benchmarks.
Return JSON with:
- relative_performance: "above_average" | "average" | "below_average"
- strengths: List of 2-3 areas where company exceeds industry
- weaknesses: List of 2-3 areas where company lags
- competitive_position: "leader" | "strong" | "moderate" | "weak"
- assessment: 2-3 sentence comparison summary

Focus on metrics relevant to creditworthiness."""),
            ("user", "Company data:\n{company}\n\nIndustry benchmarks:\n{industry}")
        ])

        try:
            chain = comparison_prompt | self.llm
            response = chain.invoke({
                "company": json.dumps(company_financials, indent=2),
                "industry": json.dumps(industry_avg, indent=2)
            })

            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Error comparing to industry: {e}")
            return {
                "error": str(e),
                "relative_performance": "unknown"
            }

    def _generate_industry_benchmarks(self, company_data: Dict) -> Dict:
        """Generate realistic industry benchmark data"""
        # This is a simplified mock - in production, you'd pull from industry databases
        return {
            "avg_revenue_growth": "8-12%",
            "avg_profit_margin": "10-15%",
            "avg_debt_to_equity": "0.5-1.0",
            "avg_current_ratio": "1.5-2.0",
            "avg_roa": "5-10%",
            "data_source": "mock_benchmarks"
        }

    def get_comprehensive_industry_analysis(self, company_name: str, industry: str,
                                           company_description: str = None,
                                           financials: Dict = None) -> Dict:
        """Get comprehensive industry analysis"""

        # Classify into NAICS
        naics_classification = self.classify_naics(company_name, industry, company_description)

        # Find peers
        peers = self.find_peer_companies(
            company_name,
            naics_classification.get("naics_code", ""),
            industry
        )

        # Get industry trends
        trends = self.get_industry_trends(
            industry,
            naics_classification.get("naics_sector_name", "")
        )

        # Compare to industry if financials provided
        comparison = None
        if financials:
            comparison = self.compare_to_industry(financials)

        return {
            "company_name": company_name,
            "naics_classification": naics_classification,
            "peer_companies": peers,
            "industry_trends": trends,
            "industry_comparison": comparison,
            "analyzed_at": __import__('datetime').datetime.now().isoformat()
        }

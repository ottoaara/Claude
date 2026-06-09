from typing import Dict, List
from ..llm_factory import get_llm, robust_parse_json
from langchain_core.prompts import ChatPromptTemplate
import os
import json
import random


class ProductAgent:
    """Agent for generating mock product data (for demo purposes)"""

    def __init__(self):
        self.llm = get_llm(temperature=0.7, json_mode=True)

    def generate_products(self, company_name: str, industry: str,
                         company_description: str = None) -> List[Dict]:
        """Generate realistic mock products for a company"""

        generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are generating realistic product/service offerings for a company.
Based on the company name, industry, and description, create 3-5 products or services
that this company would likely offer.

For each product, return:
- name: Product/service name
- category: Product category (e.g., "Software", "Financial Service", "Hardware")
- description: 2-3 sentence description
- features: List of 3-5 key features
- target_market: Who this product is for
- pricing_tier: "enterprise" | "mid-market" | "small-business" | "consumer"
- revenue_impact: "high" | "medium" | "low" (estimated contribution to revenue)

Return a JSON array of products. Make them realistic and aligned with the company's industry."""),
            ("user", """Company: {company_name}
Industry: {industry}
Description: {description}

Generate realistic products/services for this company.""")
        ])

        try:
            chain = generation_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "industry": industry or "General",
                "description": company_description or "No description available"
            })

            response_text = response.content
            products = robust_parse_json(response_text, [])
            if not isinstance(products, list):
                products = []

            # Add mock revenue data
            for i, product in enumerate(products):
                product["id"] = f"{company_name.replace(' ', '_')}_{i+1}"
                product["annual_revenue_millions"] = self._generate_revenue(
                    product.get("revenue_impact", "medium"),
                    product.get("pricing_tier", "mid-market")
                )
                product["market_share_percent"] = round(random.uniform(5, 35), 1)
                product["growth_rate_percent"] = round(random.uniform(-5, 25), 1)

            return products

        except Exception as e:
            print(f"Error generating products: {e}")
            return self._fallback_products(company_name, industry)

    def _generate_revenue(self, impact: str, tier: str) -> float:
        """Generate realistic revenue numbers based on impact and tier"""
        base_ranges = {
            "high": (50, 500),
            "medium": (10, 100),
            "low": (1, 20)
        }

        tier_multipliers = {
            "enterprise": 2.0,
            "mid-market": 1.0,
            "small-business": 0.5,
            "consumer": 0.3
        }

        base_range = base_ranges.get(impact, (10, 100))
        multiplier = tier_multipliers.get(tier, 1.0)

        revenue = random.uniform(base_range[0], base_range[1]) * multiplier
        return round(revenue, 2)

    def _fallback_products(self, company_name: str, industry: str) -> List[Dict]:
        """Fallback products if generation fails"""
        return [
            {
                "id": f"{company_name.replace(' ', '_')}_1",
                "name": f"{industry} Core Solution",
                "category": "Primary Service",
                "description": f"Main {industry.lower()} solution offered by {company_name}",
                "features": ["Feature A", "Feature B", "Feature C"],
                "target_market": "Enterprise",
                "pricing_tier": "enterprise",
                "revenue_impact": "high",
                "annual_revenue_millions": 100.0,
                "market_share_percent": 15.0,
                "growth_rate_percent": 10.0
            }
        ]

    def analyze_product_portfolio(self, products: List[Dict]) -> Dict:
        """Analyze product portfolio for banking assessment"""

        if not products:
            return {
                "diversification": "unknown",
                "revenue_concentration": "unknown",
                "assessment": "No product data available"
            }

        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are analyzing a company's product portfolio from a commercial banking perspective.
Assess:
- diversification: "high" | "medium" | "low" (how diversified is the portfolio)
- revenue_concentration: "concentrated" | "balanced" | "distributed"
- key_strengths: List 2-3 strengths of the product portfolio
- key_risks: List 2-3 risks or concerns
- growth_potential: "high" | "medium" | "low"
- assessment: 2-3 sentence overall assessment for lending purposes

Return valid JSON."""),
            ("user", "Analyze this product portfolio:\n{products}")
        ])

        try:
            chain = analysis_prompt | self.llm
            response = chain.invoke({"products": json.dumps(products, indent=2)})

            response_text = response.content
            analysis = robust_parse_json(response_text, {})
            if not isinstance(analysis, dict):
                analysis = {}

            # Add calculated metrics
            total_revenue = sum(p.get("annual_revenue_millions", 0) for p in products)
            analysis["total_portfolio_revenue_millions"] = round(total_revenue, 2)
            analysis["product_count"] = len(products)

            return analysis

        except Exception as e:
            print(f"Error analyzing product portfolio: {e}")
            return {
                "error": str(e),
                "diversification": "unknown",
                "product_count": len(products)
            }

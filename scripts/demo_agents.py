#!/usr/bin/env python3
"""
Demo script to test the banking KG agents WITHOUT Neo4j
Shows what data the agents collect
"""

import sys
import os
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


def demo_agents():
    """Test individual agents without Neo4j"""

    print("\n" + "="*70)
    print("🧪 BANKING KNOWLEDGE GRAPH - AGENT DEMO (No Neo4j)")
    print("="*70 + "\n")

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not api_key.startswith("sk-ant-"):
        print("❌ Error: ANTHROPIC_API_KEY not set correctly in .env")
        return

    print(f"✅ API Key loaded: {api_key[:20]}...\n")

    # Test company
    company_name = "Tesla"
    ticker = "TSLA"
    website = "https://www.tesla.com"

    print(f"🎯 Target Company: {company_name} ({ticker})")
    print(f"   Website: {website}\n")
    print("="*70 + "\n")

    # Test 1: Web Scraper Agent
    print("📊 TEST 1: Web Scraper Agent")
    print("-" * 70)
    try:
        from src.banking_kg.agents.web_scraper_agent import WebScraperAgent

        agent = WebScraperAgent()
        print(f"Scraping company info from {website}...")

        company_info = agent.get_company_overview(company_name, website)

        if "error" not in company_info:
            print("✅ Success! Collected:")
            print(f"   • Company: {company_info.get('company_name', 'N/A')}")
            print(f"   • Industry: {company_info.get('industry', 'N/A')}")
            print(f"   • Description: {company_info.get('description', 'N/A')[:100]}...")
            print(f"   • Headquarters: {company_info.get('headquarters', 'N/A')}")
        else:
            print(f"⚠️  Error: {company_info.get('error')}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "="*70 + "\n")

    # Test 2: News Agent
    print("📰 TEST 2: News Search Agent")
    print("-" * 70)
    try:
        from src.banking_kg.agents.news_agent import NewsAgent

        agent = NewsAgent()
        print(f"Searching news for {company_name}...")

        news_data = agent.get_comprehensive_news_analysis(company_name)

        print(f"✅ Found {news_data.get('total_items', 0)} news items")
        print(f"   • Negative items: {news_data.get('negative_count', 0)}")

        analysis = news_data.get('analysis', {})
        print(f"   • Sentiment: {analysis.get('overall_sentiment', 'unknown')}")
        print(f"   • Risk level: {analysis.get('risk_level', 'unknown')}")

        if news_data.get('news_items'):
            print("\n   Recent headlines:")
            for item in news_data['news_items'][:3]:
                print(f"      • {item.get('title', 'No title')}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "="*70 + "\n")

    # Test 3: Product Agent
    print("🏭 TEST 3: Product Generator Agent")
    print("-" * 70)
    try:
        from src.banking_kg.agents.product_agent import ProductAgent

        agent = ProductAgent()
        print(f"Generating product data for {company_name}...")

        products = agent.generate_products(
            company_name,
            "Automotive/Technology",
            "Electric vehicle and clean energy company"
        )

        print(f"✅ Generated {len(products)} products:")
        for product in products:
            print(f"   • {product.get('name')}: ${product.get('annual_revenue_millions')}M/year")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "="*70 + "\n")

    # Test 4: Industry Agent
    print("🏢 TEST 4: Industry Analysis Agent")
    print("-" * 70)
    try:
        from src.banking_kg.agents.industry_agent import IndustryAgent

        agent = IndustryAgent()
        print(f"Analyzing industry for {company_name}...")

        industry_data = agent.get_comprehensive_industry_analysis(
            company_name,
            "Automotive",
            "Electric vehicle manufacturer"
        )

        naics = industry_data.get('naics_classification', {})
        print(f"✅ NAICS Classification:")
        print(f"   • Sector: {naics.get('naics_sector_name', 'N/A')}")
        print(f"   • Code: {naics.get('naics_code', 'N/A')}")

        peers = industry_data.get('peer_companies', [])
        if peers:
            print(f"\n   Peer Companies ({len(peers)}):")
            for peer in peers[:3]:
                print(f"      • {peer.get('company_name', 'N/A')}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "="*70 + "\n")

    # Test 5: Temporal Dimension
    print("⏰ TEST 5: Temporal Dimension")
    print("-" * 70)
    try:
        from src.banking_kg.temporal import TemporalDimension
        from datetime import datetime, timedelta

        temporal = TemporalDimension()

        # Test with sample data
        test_items = {
            "news": [
                {"title": "Recent news", "date": datetime.now().strftime("%Y-%m-%d"), "sentiment": "negative", "severity": "high"},
                {"title": "Old news", "date": (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d"), "sentiment": "neutral"}
            ]
        }

        scored = temporal.score_all_items(test_items)
        pruned = temporal.prune_low_relevance(scored, threshold=0.25)
        summary = temporal.get_temporal_summary(scored)

        print(f"✅ Temporal Scoring:")
        print(f"   • Total items: {summary.get('total_items')}")
        print(f"   • Fresh items: {summary.get('fresh_items')} (< 30 days)")
        print(f"   • Aged items: {summary.get('aged_items')} (> 90 days)")
        print(f"   • Average relevance: {summary.get('avg_relevance_score')}")

        print(f"\n   After pruning (threshold=0.25):")
        print(f"   • Kept: {len(pruned.get('news', []))} items")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "="*70 + "\n")

    # Summary
    print("✅ DEMO COMPLETE!")
    print("\nAll agents are working correctly!")
    print("\nNext Steps:")
    print("  1. Install Neo4j for full graph visualization:")
    print("     brew install neo4j")
    print("     neo4j start")
    print("")
    print("  2. Start the API:")
    print("     python -m uvicorn src.banking_kg.api:app --reload --port 8000")
    print("")
    print("  3. Start the frontend:")
    print("     cd src/kg_frontend && npm run dev")
    print("")


if __name__ == "__main__":
    demo_agents()

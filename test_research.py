#!/usr/bin/env python3
"""Quick test script to verify research is working"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from src.banking_kg.research_orchestrator import BankingResearchOrchestrator

def test_research():
    """Test research with a simple company"""

    print("=" * 60)
    print("TESTING RESEARCH SYSTEM")
    print("=" * 60)

    # Initialize orchestrator
    orchestrator = BankingResearchOrchestrator(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
        user_email=os.getenv("USER_EMAIL", "test@example.com")
    )

    # Test with Apple
    print("\n🧪 Testing with Apple (AAPL)...")
    result = orchestrator.research_company(
        company_name="Apple Inc.",
        ticker="AAPL",
        website="https://www.apple.com"
    )

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)

    print(f"\n✅ Completed steps: {result.get('completed_steps', [])}")
    print(f"❌ Errors: {result.get('errors', [])}")

    # Check financials
    financials = result.get('dimensions', {}).get('financials', [])
    print(f"\n💰 Financial filings found: {len(financials)}")
    if financials:
        for filing in financials:
            print(f"   - {filing.get('filing_type')} {filing.get('period')}: Revenue=${filing.get('revenue')}M")

    # Check industry
    industry = result.get('dimensions', {}).get('industry', {})
    print(f"\n🏢 Industry: {industry.get('naics_sector_name', 'N/A')}")
    print(f"   NAICS Code: {industry.get('naics_code', 'N/A')}")

    # Check news
    news = result.get('dimensions', {}).get('news', [])
    print(f"\n📰 News items: {len(news)}")

    # Check summary
    print(f"\n📋 Summary:")
    print(result.get('summary', 'No summary'))

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    orchestrator.close()

if __name__ == "__main__":
    test_research()

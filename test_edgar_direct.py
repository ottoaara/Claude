#!/usr/bin/env python3
"""Test Edgar agent directly"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from src.banking_kg.agents.edgar_agent import EdgarFinancialAgent

def test_edgar():
    print("=" * 60)
    print("TESTING EDGAR AGENT DIRECTLY")
    print("=" * 60)

    # Initialize Edgar agent
    email = os.getenv("USER_EMAIL", "test@example.com")
    print(f"\nUsing email: {email}")

    agent = EdgarFinancialAgent(company_email=email)

    # Test with AAPL (should always work)
    ticker = "AAPL"
    print(f"\n🧪 Testing with {ticker}...")

    result = agent.get_company_financials(ticker, filing_types=["10-K"])

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)

    print(f"\nTicker: {result.get('ticker')}")
    print(f"Total filings: {len(result.get('filings', []))}")

    for filing in result.get('filings', []):
        print(f"\n📄 Filing:")
        print(f"   Type: {filing.get('filing_type')}")
        print(f"   Period: {filing.get('filing_period')}")
        print(f"   Revenue: ${filing.get('revenue')}M")
        print(f"   Net Income: ${filing.get('net_income')}M")
        print(f"   Assets: ${filing.get('total_assets')}M")

        if 'error' in filing:
            print(f"   ❌ ERROR: {filing['error']}")

    print("\n" + "=" * 60)

    # Check if files were downloaded
    download_path = Path("./data/edgar_downloads/sec-edgar-filings") / ticker / "10-K"
    if download_path.exists():
        print(f"\n✅ Files downloaded to: {download_path}")
        print(f"   Number of filing folders: {len(list(download_path.iterdir()))}")
    else:
        print(f"\n❌ No files at: {download_path}")

if __name__ == "__main__":
    test_edgar()

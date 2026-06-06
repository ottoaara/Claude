#!/usr/bin/env python3
"""
Quick test of the Banking Knowledge Graph system
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.banking_kg.research_orchestrator import BankingResearchOrchestrator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_basic_research():
    """Test basic research workflow with a simple company"""

    print("\n" + "=" * 60)
    print("🧪 Testing Banking Knowledge Graph System")
    print("=" * 60 + "\n")

    # Initialize orchestrator
    print("1️⃣ Initializing orchestrator...")
    orchestrator = BankingResearchOrchestrator()

    # Initialize Neo4j schema
    print("2️⃣ Setting up Neo4j schema...")
    orchestrator.kg.init_schema()

    # Test company (using a well-known company with a ticker)
    test_company = "Tesla"
    test_ticker = "TSLA"
    test_website = "https://www.tesla.com"

    print(f"\n3️⃣ Starting research for: {test_company} ({test_ticker})")
    print(f"   Website: {test_website}\n")

    # Run research
    try:
        result = orchestrator.research_company(
            company_name=test_company,
            ticker=test_ticker,
            website=test_website
        )

        print("\n" + "=" * 60)
        print("📊 RESEARCH SUMMARY")
        print("=" * 60)
        print(f"\nCompleted Steps: {len(result.get('completed_steps', []))}")
        for step in result.get('completed_steps', []):
            print(f"  ✅ {step}")

        print(f"\nErrors: {len(result.get('errors', []))}")
        for error in result.get('errors', []):
            print(f"  ❌ {error}")

        print(f"\nGraph Populated: {result.get('graph_populated', False)}")

        # Get visualization data
        print("\n4️⃣ Fetching graph visualization data...")
        viz_data = orchestrator.get_graph_visualization(test_company)
        print(f"   Nodes: {len(viz_data.get('nodes', []))}")
        print(f"   Edges: {len(viz_data.get('edges', []))}")

        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60 + "\n")

        print("🌐 Next steps:")
        print("   1. Start the API: python -m uvicorn src.banking_kg.api:app --reload")
        print("   2. Start the frontend: cd src/kg_frontend && npm run dev")
        print("   3. Visit: http://localhost:3000/banking")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        orchestrator.close()


if __name__ == "__main__":
    # Check environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY not set in environment")
        print("   Create a .env file with your API key")
        sys.exit(1)

    if not os.getenv("NEO4J_URI"):
        print("⚠️  Warning: NEO4J_URI not set, using default: bolt://localhost:7687")

    test_basic_research()

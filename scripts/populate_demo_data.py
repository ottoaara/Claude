#!/usr/bin/env python3
"""
Populate Neo4j with demo data to show the 5-dimensional graph visualization
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from src.banking_kg.neo4j_db import BankingKnowledgeGraph


def populate_demo_company():
    """Populate a demo company with all 5 dimensions visible"""

    print("\n" + "="*70)
    print("🎨 POPULATING DEMO DATA FOR VISUALIZATION")
    print("="*70 + "\n")

    kg = BankingKnowledgeGraph()

    company_name = "Demo Corp"

    # Clear any existing data
    print("🧹 Clearing existing demo data...")
    kg.clear_company_data(company_name)

    # DIMENSION 1: Company Info
    print("\n📊 DIMENSION 1: Company Information")
    print("-" * 70)
    kg.create_company(
        name=company_name,
        ticker="DEMO",
        website="https://democorp.com",
        sector="Technology",
        naics="51",
        description="Leading technology company in enterprise software",
        headquarters="San Francisco, CA",
        founded="2010"
    )
    print(f"✅ Created company: {company_name}")

    # DIMENSION 2: Financial Data (3 filings)
    print("\n💰 DIMENSION 2: Financial Data")
    print("-" * 70)

    # Recent 10-K
    kg.add_financial_data(
        company_name=company_name,
        filing_type="10-K",
        period="2024-FY",
        data={
            "revenue": 5000.0,
            "net_income": 800.0,
            "total_assets": 12000.0,
            "total_liabilities": 4000.0,
            "cash_and_equivalents": 2500.0,
            "operating_cash_flow": 1200.0,
            "key_risks": [
                "Market competition",
                "Regulatory changes",
                "Cybersecurity threats"
            ]
        },
        source="EDGAR"
    )
    print("✅ Added 10-K filing (2024-FY)")

    # Recent 10-Q
    kg.add_financial_data(
        company_name=company_name,
        filing_type="10-Q",
        period="2024-Q1",
        data={
            "revenue": 1300.0,
            "net_income": 210.0,
            "cash_and_equivalents": 2600.0,
            "operating_cash_flow": 320.0
        },
        source="EDGAR"
    )
    print("✅ Added 10-Q filing (2024-Q1)")

    # DIMENSION 3: News (5 items with different sentiments)
    print("\n📰 DIMENSION 3: News & Sentiment")
    print("-" * 70)

    news_items = [
        {
            "title": "Demo Corp Launches AI-Powered Platform",
            "summary": "Company unveils new artificial intelligence platform for enterprise customers.",
            "url": "https://news.example.com/democorp-ai-launch",
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "sentiment": "positive"
        },
        {
            "title": "Demo Corp Faces SEC Investigation",
            "summary": "Securities and Exchange Commission opens investigation into accounting practices.",
            "url": "https://news.example.com/democorp-sec-investigation",
            "date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "sentiment": "negative"
        },
        {
            "title": "Demo Corp Q1 Earnings Beat Expectations",
            "summary": "Company reports stronger than expected quarterly earnings, stock rises 8%.",
            "url": "https://news.example.com/democorp-earnings-beat",
            "date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "sentiment": "positive"
        },
        {
            "title": "Demo Corp Announces Layoffs",
            "summary": "Company to cut 10% of workforce in restructuring effort.",
            "url": "https://news.example.com/democorp-layoffs",
            "date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
            "sentiment": "negative"
        },
        {
            "title": "Demo Corp Partners with Major Cloud Provider",
            "summary": "Strategic partnership announced to expand cloud infrastructure offerings.",
            "url": "https://news.example.com/democorp-partnership",
            "date": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
            "sentiment": "positive"
        }
    ]

    for news in news_items:
        kg.add_news(
            company_name=company_name,
            title=news["title"],
            summary=news["summary"],
            url=news["url"],
            date=news["date"],
            sentiment=news["sentiment"]
        )
        print(f"✅ Added news: {news['title'][:50]}...")

    # DIMENSION 4: Products (5 products)
    print("\n🏭 DIMENSION 4: Product Portfolio")
    print("-" * 70)

    products = [
        {
            "name": "Enterprise Cloud Platform",
            "category": "Software",
            "description": "Comprehensive cloud platform for enterprise data management and analytics.",
            "features": ["Real-time analytics", "Auto-scaling", "99.99% uptime SLA", "Multi-region deployment"],
            "pricing_tier": "enterprise",
            "revenue_impact": "high"
        },
        {
            "name": "AI Assistant Suite",
            "category": "Software",
            "description": "AI-powered assistant tools for business productivity and automation.",
            "features": ["Natural language processing", "Workflow automation", "Integration APIs", "Custom training"],
            "pricing_tier": "mid-market",
            "revenue_impact": "high"
        },
        {
            "name": "Security Monitor Pro",
            "category": "Security",
            "description": "Advanced cybersecurity monitoring and threat detection system.",
            "features": ["24/7 monitoring", "Threat intelligence", "Automated response", "Compliance reporting"],
            "pricing_tier": "enterprise",
            "revenue_impact": "medium"
        },
        {
            "name": "Mobile Workforce App",
            "category": "Mobile",
            "description": "Mobile application for remote workforce management and collaboration.",
            "features": ["Cross-platform", "Offline mode", "Video conferencing", "Task management"],
            "pricing_tier": "small-business",
            "revenue_impact": "medium"
        },
        {
            "name": "Developer Tools SDK",
            "category": "Developer Tools",
            "description": "Software development kit for building custom integrations.",
            "features": ["REST APIs", "SDKs for Python/Java/Node", "Documentation", "Community support"],
            "pricing_tier": "developer",
            "revenue_impact": "low"
        }
    ]

    for product in products:
        kg.add_product(
            company_name=company_name,
            product_name=product["name"],
            category=product["category"],
            description=product["description"],
            features=product["features"],
            pricing_tier=product["pricing_tier"],
            revenue_impact=product["revenue_impact"]
        )
        print(f"✅ Added product: {product['name']}")

    # DIMENSION 5: Industry & Peers
    print("\n🏢 DIMENSION 5: Industry & Competitors")
    print("-" * 70)

    # Link to industry
    kg.link_to_industry(
        company_name=company_name,
        naics_code="51",
        industry_name="Information Technology",
        sector="Technology"
    )
    print("✅ Linked to industry: Information Technology (NAICS 51)")

    # Add peer companies
    peers = [
        "Tech Giant Inc",
        "Software Solutions Corp",
        "Cloud Innovations LLC",
        "Enterprise Systems Ltd"
    ]

    for peer in peers:
        kg.add_peer_relationship(
            company_name=company_name,
            peer_name=peer,
            similarity_score=0.8
        )
        print(f"✅ Added peer: {peer}")

    # Get final graph stats
    print("\n" + "="*70)
    print("📊 FINAL GRAPH STATISTICS")
    print("="*70)

    graph_data = kg.get_company_graph(company_name)
    viz_data = kg.get_visualization_data(company_name)

    print(f"\n✅ Company: {company_name}")
    print(f"   • Financials: {len(graph_data['financials'])} filings")
    print(f"   • News: {len(graph_data['news'])} articles")
    print(f"   • Products: {len(graph_data['products'])} products")
    print(f"   • Industries: {len(graph_data['industries'])} classifications")
    print(f"   • Peers: {len(graph_data['peers'])} competitors")
    print(f"\n   Total nodes in graph: {len(viz_data['nodes'])}")
    print(f"   Total relationships: {len(viz_data['edges'])}")

    kg.close()

    print("\n" + "="*70)
    print("✅ DEMO DATA POPULATED SUCCESSFULLY!")
    print("="*70)
    print("\nView in browser:")
    print("  • Dashboard: http://localhost:3000/banking")
    print("  • Neo4j Browser: http://localhost:7474")
    print("  • API: http://localhost:8000/company/Demo%20Corp/visualization")
    print("\nThe graph now shows all 5 dimensions!")
    print()


if __name__ == "__main__":
    populate_demo_company()

from typing import TypedDict, Dict, List, Annotated
from langgraph.graph import StateGraph, END
import operator
from datetime import datetime

from .agents.edgar_agent import EdgarFinancialAgent
from .agents.web_scraper_agent import WebScraperAgent
from .agents.news_agent import NewsAgent
from .agents.product_agent import ProductAgent
from .agents.industry_agent import IndustryAgent
from .temporal import TemporalDimension
from .neo4j_db import BankingKnowledgeGraph


class ResearchState(TypedDict):
    """State for the research workflow"""
    company_name: str
    ticker: str
    website: str

    # Collected data from each dimension
    company_info: Dict
    financial_data: Dict
    news_data: Dict
    product_data: Dict
    industry_data: Dict

    # Processing status
    errors: Annotated[List[str], operator.add]
    completed_steps: Annotated[List[str], operator.add]

    # Final output
    graph_populated: bool
    summary: Dict


class BankingResearchOrchestrator:
    """LangGraph orchestrator for coordinating all research agents"""

    def __init__(self, neo4j_uri: str = None, neo4j_user: str = None,
                 neo4j_password: str = None, user_email: str = None):

        # Initialize agents
        self.edgar_agent = EdgarFinancialAgent(company_email=user_email)
        self.web_agent = WebScraperAgent()
        self.news_agent = NewsAgent()
        self.product_agent = ProductAgent()
        self.industry_agent = IndustryAgent()
        self.temporal = TemporalDimension()

        # Initialize Neo4j
        self.kg = BankingKnowledgeGraph(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

        # Live progress callback — set per-run by the API
        self._progress_callback = None

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""

        workflow = StateGraph(ResearchState)

        # Add nodes for each research dimension
        workflow.add_node("scrape_company_info", self._scrape_company_info)
        workflow.add_node("fetch_financials", self._fetch_financials)
        workflow.add_node("search_news", self._search_news)
        workflow.add_node("generate_products", self._generate_products)
        workflow.add_node("analyze_industry", self._analyze_industry)
        workflow.add_node("apply_temporal_scoring", self._apply_temporal_scoring)
        workflow.add_node("populate_graph", self._populate_graph)
        workflow.add_node("generate_summary", self._generate_summary)

        # Define the flow - sequential execution to avoid state conflicts
        workflow.set_entry_point("scrape_company_info")

        # Sequential flow through all research steps
        workflow.add_edge("scrape_company_info", "fetch_financials")
        workflow.add_edge("fetch_financials", "search_news")
        workflow.add_edge("search_news", "generate_products")
        workflow.add_edge("generate_products", "analyze_industry")
        workflow.add_edge("analyze_industry", "apply_temporal_scoring")
        workflow.add_edge("apply_temporal_scoring", "populate_graph")
        workflow.add_edge("populate_graph", "generate_summary")
        workflow.add_edge("generate_summary", END)

        return workflow.compile()

    def _emit_progress(self, completed_steps: list) -> None:
        """Fire the live progress callback if one is registered."""
        if self._progress_callback:
            try:
                self._progress_callback(list(completed_steps))
            except Exception:
                pass

    def _scrape_company_info(self, state: ResearchState) -> ResearchState:
        """Node: Scrape company information from website"""
        print(f"📊 Scraping company info for {state['company_name']}...")

        try:
            company_info = self.web_agent.get_company_overview(
                state["company_name"],
                state.get("website")
            )
            state["company_info"] = company_info
            state["completed_steps"].append("company_info")

        except Exception as e:
            error_msg = f"Company scraping error: {str(e)}"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
            state["company_info"] = {"error": str(e)}

        self._emit_progress(state["completed_steps"])
        return state

    def _fetch_financials(self, state: ResearchState) -> ResearchState:
        """Node: Fetch financial data from Edgar"""
        ticker = state.get('ticker', '').strip()

        print(f"💰 Fetching financials for ticker: '{ticker}'")
        print(f"   Company: {state.get('company_name')}")

        if not ticker:
            error_msg = "No ticker provided, skipping financial data"
            print(f"⚠️  {error_msg}")
            state["errors"].append(error_msg)
            state["financial_data"] = {"error": "No ticker", "filings": []}
            return state

        try:
            print(f"   Calling Edgar agent with ticker: {ticker}")
            financial_data = self.edgar_agent.get_company_financials(
                ticker,
                filing_types=["10-K", "10-Q"]
            )

            print(f"   ✅ Edgar returned {len(financial_data.get('filings', []))} filings")

            # Analyze financial health
            if financial_data.get("filings"):
                analysis = self.edgar_agent.analyze_financial_health(financial_data)
                financial_data["health_analysis"] = analysis

            state["financial_data"] = financial_data
            state["completed_steps"].append("financials")

        except Exception as e:
            error_msg = f"Financial data error: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            state["errors"].append(error_msg)
            state["financial_data"] = {"error": str(e), "filings": []}

        self._emit_progress(state["completed_steps"])
        return state

    def _search_news(self, state: ResearchState) -> ResearchState:
        """Node: Search for news (especially negative)"""
        print(f"📰 Searching news for {state['company_name']}...")

        try:
            news_data = self.news_agent.get_comprehensive_news_analysis(
                state["company_name"]
            )
            state["news_data"] = news_data
            state["completed_steps"].append("news")

        except Exception as e:
            error_msg = f"News search error: {str(e)}"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
            state["news_data"] = {"error": str(e)}

        self._emit_progress(state["completed_steps"])
        return state

    def _generate_products(self, state: ResearchState) -> ResearchState:
        """Node: Generate mock product data"""
        print(f"🏭 Generating product data for {state['company_name']}...")

        try:
            # Extract industry from company info
            industry = state.get("company_info", {}).get("industry", "General")
            description = state.get("company_info", {}).get("description", "")

            products = self.product_agent.generate_products(
                state["company_name"],
                industry,
                description
            )

            portfolio_analysis = self.product_agent.analyze_product_portfolio(products)

            state["product_data"] = {
                "products": products,
                "portfolio_analysis": portfolio_analysis
            }
            state["completed_steps"].append("products")

        except Exception as e:
            error_msg = f"Product generation error: {str(e)}"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
            state["product_data"] = {"error": str(e)}

        self._emit_progress(state["completed_steps"])
        return state

    def _analyze_industry(self, state: ResearchState) -> ResearchState:
        """Node: Analyze industry and find peers"""
        print(f"🏢 Analyzing industry for {state['company_name']}...")

        try:
            industry = state.get("company_info", {}).get("industry", "Unknown")
            description = state.get("company_info", {}).get("description", "")
            financials = state.get("financial_data", {})

            print(f"   Industry from company_info: {industry}")
            print(f"   Description available: {len(description)} chars")

            industry_analysis = self.industry_agent.get_comprehensive_industry_analysis(
                state["company_name"],
                industry,
                description,
                financials
            )

            print(f"   ✅ Industry analysis completed:")
            print(f"      NAICS: {industry_analysis.get('naics_code', 'N/A')}")
            print(f"      Sector: {industry_analysis.get('naics_sector_name', 'N/A')}")
            print(f"      Peers: {len(industry_analysis.get('peer_companies', []))}")

            state["industry_data"] = industry_analysis
            state["completed_steps"].append("industry")

        except Exception as e:
            error_msg = f"Industry analysis error: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            state["errors"].append(error_msg)
            state["industry_data"] = {"error": str(e)}

        self._emit_progress(state["completed_steps"])
        return state

    def _apply_temporal_scoring(self, state: ResearchState) -> ResearchState:
        """Node: Apply temporal dimension scoring"""
        print(f"⏰ Applying temporal relevance scoring...")

        try:
            # Combine all data
            combined_data = {
                "financials": state.get("financial_data", {}).get("filings", []),
                "news": state.get("news_data", {}).get("news_items", []),
                "products": state.get("product_data", {}).get("products", [])
            }

            # Score and prune
            scored_data = self.temporal.score_all_items(combined_data)
            pruned_data = self.temporal.prune_low_relevance(scored_data, threshold=0.25)
            temporal_summary = self.temporal.get_temporal_summary(scored_data)

            # Update state with scored data
            if "financial_data" in state and state["financial_data"]:
                state["financial_data"]["filings"] = scored_data.get("financials", [])

            if "news_data" in state and state["news_data"]:
                state["news_data"]["news_items"] = scored_data.get("news", [])

            if "product_data" in state and state["product_data"]:
                state["product_data"]["products"] = scored_data.get("products", [])

            state["temporal_summary"] = temporal_summary
            state["completed_steps"].append("temporal_scoring")

        except Exception as e:
            error_msg = f"Temporal scoring error: {str(e)}"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)

        self._emit_progress(state["completed_steps"])
        return state

    def _populate_graph(self, state: ResearchState) -> ResearchState:
        """Node: Populate Neo4j knowledge graph"""
        print(f"🔗 Populating knowledge graph...")

        try:
            # Create company node
            company_info = state.get("company_info", {})
            industry_data = state.get("industry_data", {})
            naics = industry_data.get("naics_classification", {})

            self.kg.create_company(
                name=state["company_name"],
                ticker=state.get("ticker"),
                website=company_info.get("source_url"),
                sector=naics.get("naics_sector_name"),
                naics=naics.get("naics_code"),
                description=company_info.get("description"),
                headquarters=company_info.get("headquarters"),
                founded=company_info.get("founded")
            )

            # Add financial data
            for filing in state.get("financial_data", {}).get("filings", []):
                if "error" not in filing:
                    self.kg.add_financial_data(
                        state["company_name"],
                        filing.get("filing_type", "10-K"),
                        filing.get("filing_period", "Unknown"),
                        filing
                    )

            # Add news (with all classifier fields)
            news_data = state.get("news_data", {})
            for news_item in news_data.get("news_items", []):
                self.kg.add_news(
                    state["company_name"],
                    news_item.get("title", ""),
                    news_item.get("summary", ""),
                    news_item.get("url", ""),
                    news_item.get("date", datetime.now().strftime("%Y-%m-%d")),
                    sentiment=news_item.get("sentiment", "neutral"),
                    severity=news_item.get("severity", "low"),
                    event_types=news_item.get("event_types", []),
                    is_material=news_item.get("is_material", False),
                    key_facts=news_item.get("key_facts", []),
                )

            # Save aggregate news analysis on Company node
            if news_data.get("analysis"):
                self.kg.save_news_analysis(state["company_name"], news_data["analysis"])

            # Add products
            for product in state.get("product_data", {}).get("products", []):
                self.kg.add_product(
                    state["company_name"],
                    product.get("name", ""),
                    product.get("category", ""),
                    product.get("description", ""),
                    features=product.get("features", []),
                    pricing_tier=product.get("pricing_tier"),
                    revenue_impact=product.get("revenue_impact")
                )

            # Link to industry
            if naics.get("naics_code"):
                self.kg.link_to_industry(
                    state["company_name"],
                    naics.get("naics_code", "99"),
                    naics.get("naics_sector_name", "Unknown"),
                    naics.get("naics_sector_name", "Unknown")
                )

            # Add peer relationships
            for peer in industry_data.get("peer_companies", []):
                self.kg.add_peer_relationship(
                    state["company_name"],
                    peer.get("company_name", "")
                )

            state["graph_populated"] = True
            state["completed_steps"].append("graph_populated")

        except Exception as e:
            error_msg = f"Graph population error: {str(e)}"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
            state["graph_populated"] = False

        self._emit_progress(state["completed_steps"])
        return state

    def _generate_summary(self, state: ResearchState) -> ResearchState:
        """Node: Generate executive summary"""
        print(f"📝 Generating summary...")

        summary = {
            "company_name": state["company_name"],
            "research_completed_at": datetime.now().isoformat(),
            "dimensions_completed": state.get("completed_steps", []),
            "errors": state.get("errors", []),
            "data_quality": {
                "company_info": "error" not in state.get("company_info", {}),
                "financials": "error" not in state.get("financial_data", {}),
                "news": "error" not in state.get("news_data", {}),
                "products": "error" not in state.get("product_data", {}),
                "industry": "error" not in state.get("industry_data", {})
            },
            "temporal_summary": state.get("temporal_summary", {}),
            "graph_populated": state.get("graph_populated", False)
        }

        state["summary"] = summary
        print(f"✅ Research complete for {state['company_name']}")

        return state

    def research_company(self, company_name: str, ticker: str = None,
                        website: str = None, progress_callback=None) -> Dict:
        """Execute the full research workflow for a company"""

        print(f"\n{'='*60}")
        print(f"🚀 Starting research for: {company_name}")
        print(f"{'='*60}\n")

        self._progress_callback = progress_callback

        initial_state = {
            "company_name": company_name,
            "ticker": ticker or "",
            "website": website or "",
            "company_info": {},
            "financial_data": {},
            "news_data": {},
            "product_data": {},
            "industry_data": {},
            "errors": [],
            "completed_steps": [],
            "graph_populated": False,
            "summary": {}
        }

        # Run the workflow
        final_state = self.workflow.invoke(initial_state)

        # Transform state into frontend-friendly format
        formatted_financials = self._format_financials(final_state.get("financial_data", {}))

        result = {
            "summary": self._generate_text_summary(final_state),
            "completed_steps": final_state.get("completed_steps", []),
            "temporal_summary": final_state.get("temporal_summary", {}),
            "dimensions": {
                "company_info": final_state.get("company_info", {}),
                "financials": formatted_financials,
                "news": final_state.get("news_data", {}).get("news_items", []),
                "products": final_state.get("product_data", {}).get("products", []),
                "industry": final_state.get("industry_data", {}),
            },
            "errors": final_state.get("errors", [])
        }

        print(f"\n✅ Research result structure:")
        print(f"   - Summary: {len(result['summary'])} chars")
        print(f"   - Financials: {len(formatted_financials)} filings")
        print(f"   - News: {len(result['dimensions']['news'])} items")
        print(f"   - Products: {len(result['dimensions']['products'])} items")
        print(f"   - Industry: {result['dimensions']['industry'].get('naics_sector_name', 'N/A')}")
        print(f"   - Errors: {len(result['errors'])}\n")

        return result

    def _generate_text_summary(self, state: Dict) -> str:
        """Generate a text summary from the research state"""
        company = state.get("company_name", "Company")
        completed = len(state.get("completed_steps", []))

        summary_parts = [
            f"Research completed for {company} across {completed} dimensions.",
            ""
        ]

        # Add company info
        if state.get("company_info", {}).get("description"):
            summary_parts.append(state["company_info"]["description"][:200] + "...")
            summary_parts.append("")

        # Add financial summary
        financials = state.get("financial_data", {}).get("filings", [])
        if financials and len(financials) > 0:
            latest = financials[0]
            if "revenue" in latest:
                summary_parts.append(f"Latest revenue: ${latest.get('revenue', 0):.1f}M")

        # Add news summary
        news = state.get("news_data", {}).get("news_items", [])
        if news:
            summary_parts.append(f"{len(news)} news articles analyzed with sentiment scoring.")

        # Add industry
        industry = state.get("industry_data", {})
        if industry.get("naics_sector_name"):
            summary_parts.append(f"Industry: {industry['naics_sector_name']}")

        return "\n".join(summary_parts)

    def _format_financials(self, financial_data: Dict) -> list:
        """Format financial data for the frontend"""
        filings = financial_data.get("filings", [])
        formatted = []

        print(f"DEBUG: Formatting {len(filings)} financial filings")

        for filing in filings:
            if "error" not in filing:
                formatted_filing = {
                    "period": filing.get("filing_period", "Unknown"),
                    "filing_type": filing.get("filing_type", "10-K"),
                    "filing_date": filing.get("filing_date", ""),
                    "revenue": filing.get("revenue"),
                    "net_income": filing.get("net_income"),
                    "operating_income": filing.get("operating_income"),
                    "assets": filing.get("total_assets"),
                    "liabilities": filing.get("total_liabilities"),
                    "equity": filing.get("stockholders_equity"),
                    "operating_cash_flow": filing.get("operating_cash_flow"),
                    "investing_cash_flow": filing.get("investing_cash_flow"),
                    "financing_cash_flow": filing.get("financing_cash_flow"),
                }
                print(f"DEBUG: Formatted filing - {formatted_filing['filing_type']} {formatted_filing['period']}, Revenue: {formatted_filing['revenue']}")
                formatted.append(formatted_filing)

        return formatted

    def get_graph_visualization(self, company_name: str) -> Dict:
        """Get graph data for visualization"""
        return self.kg.get_visualization_data(company_name)

    def close(self):
        """Clean up resources"""
        self.kg.close()

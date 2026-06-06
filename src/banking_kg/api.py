from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from .research_orchestrator import BankingResearchOrchestrator
from .neo4j_db import BankingKnowledgeGraph

app = FastAPI(
    title="Banking Knowledge Graph API",
    description="Commercial banking knowledge graph for sales meeting preparation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator (in production, use dependency injection)
orchestrator = None
kg = None

# Track research jobs
research_jobs = {}


class CompanyResearchRequest(BaseModel):
    company_name: str
    ticker: Optional[str] = None
    website: Optional[str] = None


class ResearchStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    company_name: str
    started_at: str
    completed_at: Optional[str] = None
    progress: Dict = {}
    result: Optional[Dict] = None
    error: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator and database connection"""
    global orchestrator, kg

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    user_email = os.getenv("USER_EMAIL", "ottoaara@gmail.com")

    try:
        orchestrator = BankingResearchOrchestrator(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            user_email=user_email
        )

        kg = BankingKnowledgeGraph(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )

        # Initialize schema
        kg.init_schema()
        print("✅ Banking KG API initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        print("⚠️  Make sure Neo4j is running at", neo4j_uri)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources"""
    global orchestrator, kg
    if orchestrator:
        orchestrator.close()
    if kg:
        kg.close()


@app.get("/")
def root():
    return {
        "name": "Banking Knowledge Graph API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "neo4j_connected": kg is not None,
        "orchestrator_ready": orchestrator is not None
    }


def run_research_sync(job_id: str, company_name: str, ticker: str = None, website: str = None):
    """Run research in background"""
    global research_jobs, orchestrator

    research_jobs[job_id]["status"] = "running"

    try:
        def on_step_complete(completed_steps: list):
            research_jobs[job_id]["progress"] = {
                "completed_steps": completed_steps,
                "total_steps": 7
            }

        result = orchestrator.research_company(company_name, ticker, website,
                                               progress_callback=on_step_complete)

        research_jobs[job_id]["status"] = "completed"
        research_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        research_jobs[job_id]["result"] = result
        research_jobs[job_id]["progress"] = {
            "completed_steps": result.get("completed_steps", []),
            "total_steps": 7
        }

        print(f"✅ Research completed for {company_name}")
        print(f"   API storing result with:")
        print(f"   - Financials: {len(result.get('dimensions', {}).get('financials', []))} filings")
        print(f"   - Industry: {result.get('dimensions', {}).get('industry', {}).get('naics_sector_name', 'N/A')}")
        print(f"   - News: {len(result.get('dimensions', {}).get('news', []))} items")

    except Exception as e:
        print(f"❌ Research failed for {company_name}: {e}")
        research_jobs[job_id]["status"] = "failed"
        research_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        research_jobs[job_id]["error"] = str(e)


@app.post("/research/start", response_model=ResearchStatus)
async def start_research(request: CompanyResearchRequest, background_tasks: BackgroundTasks):
    """Start company research process"""
    import uuid

    job_id = str(uuid.uuid4())

    research_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "company_name": request.company_name,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "progress": {},
        "result": None,
        "error": None
    }

    # Run research in background
    background_tasks.add_task(
        run_research_sync,
        job_id,
        request.company_name,
        request.ticker,
        request.website
    )

    return ResearchStatus(**research_jobs[job_id])


@app.get("/research/status/{job_id}", response_model=ResearchStatus)
def get_research_status(job_id: str):
    """Get status of a research job"""
    if job_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return ResearchStatus(**research_jobs[job_id])


@app.get("/research/jobs")
def list_research_jobs():
    """List all research jobs"""
    return {
        "jobs": list(research_jobs.values()),
        "total": len(research_jobs)
    }


@app.get("/company/{company_name}/graph")
def get_company_graph(company_name: str):
    """Get complete company graph data"""
    global kg

    graph_data = kg.get_company_graph(company_name)

    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    return graph_data


@app.get("/company/{company_name}/visualization")
def get_graph_visualization(company_name: str):
    """Get graph data formatted for visualization"""
    global kg

    viz_data = kg.get_visualization_data(company_name)

    if not viz_data or not viz_data.get("nodes"):
        raise HTTPException(status_code=404, detail=f"No graph data for '{company_name}'")

    return viz_data


@app.delete("/company/{company_name}")
def delete_company(company_name: str):
    """Delete company data from graph"""
    global kg

    kg.clear_company_data(company_name)

    return {"message": f"Company '{company_name}' data cleared"}


@app.get("/companies")
def list_companies():
    """List all companies in the graph"""
    global kg

    with kg.driver.session() as session:
        result = session.run("MATCH (c:Company) RETURN c.name as name, c.ticker as ticker")
        companies = [{"name": record["name"], "ticker": record["ticker"]} for record in result]

    return {
        "companies": companies,
        "total": len(companies)
    }


@app.get("/company/{company_name}/peer-comparison")
def get_peer_comparison(company_name: str):
    """
    Return financial metrics for the target company alongside its EDGAR-sourced
    peer companies for head-to-head comparison charts.
    """
    global kg
    data = kg.get_peer_comparison(company_name)
    if not data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    # Compute net margin where possible
    def net_margin(revenue, net_income):
        try:
            if revenue and net_income and float(revenue) != 0:
                return round(float(net_income) / float(revenue) * 100, 2)
        except Exception:
            pass
        return None

    def enrich(record: dict) -> dict:
        record["net_margin"] = net_margin(record.get("revenue"), record.get("net_income"))
        return record

    data["target"] = enrich(data["target"])
    data["peers"] = [enrich(p) for p in data.get("peers", [])]

    return data


@app.get("/company/{company_name}/freshness")
def get_company_freshness(company_name: str):
    """
    Return per-dimension data freshness scores for a company.
    Uses stored relevance_scores and temporal_summary from Neo4j,
    and re-computes live freshness for each item.
    """
    from .temporal import TemporalDimension
    from datetime import datetime

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    temporal = TemporalDimension()

    def item_age_days(item: dict) -> int | None:
        for field in ("filing_date", "date", "timestamp", "scraped_at", "discovered_at"):
            val = item.get(field)
            if val:
                try:
                    if isinstance(val, str):
                        dt = datetime.fromisoformat(val.replace("Z", "+00:00")) if "T" in val \
                             else datetime.strptime(val[:10], "%Y-%m-%d")
                    else:
                        dt = val
                    return max(0, (datetime.now() - dt.replace(tzinfo=None)).days)
                except Exception:
                    continue
        return None

    def freshness_label(score: float) -> str:
        if score >= 0.8: return "fresh"
        if score >= 0.5: return "recent"
        if score >= 0.3: return "aged"
        return "stale"

    dimensions = {}

    # Financials
    fin_items = []
    for f in graph_data.get("financials", []):
        age = item_age_days(f)
        score = f.get("relevance_score") or temporal.calculate_recency_score(
            f.get("filing_date", f.get("date", "")), "financial")
        fin_items.append({
            "label": f"{f.get('filing_type','?')} {f.get('period','')}",
            "age_days": age,
            "score": round(float(score), 3),
            "freshness": freshness_label(float(score)),
            "source": f.get("source", "EDGAR"),
        })
    dimensions["financials"] = {
        "items": fin_items,
        "avg_score": round(sum(i["score"] for i in fin_items) / len(fin_items), 3) if fin_items else 0,
        "window_days": temporal.relevance_windows["financial"],
        "needs_refresh": any(i["freshness"] in ("aged", "stale") for i in fin_items),
    }

    # News
    news_items = []
    for n in graph_data.get("news", []):
        age = item_age_days(n)
        score = n.get("relevance_score") or temporal.calculate_recency_score(
            str(n.get("date", "")), "news")
        news_items.append({
            "label": n.get("title", "")[:60],
            "age_days": age,
            "score": round(float(score), 3),
            "freshness": freshness_label(float(score)),
            "sentiment": n.get("sentiment"),
        })
    dimensions["news"] = {
        "items": news_items,
        "avg_score": round(sum(i["score"] for i in news_items) / len(news_items), 3) if news_items else 0,
        "window_days": temporal.relevance_windows["news"],
        "needs_refresh": any(i["freshness"] in ("aged", "stale") for i in news_items),
    }

    # Products
    prod_items = []
    for p in graph_data.get("products", []):
        age = item_age_days(p)
        score = p.get("relevance_score") or temporal.calculate_recency_score(
            str(p.get("timestamp", "")), "products")
        prod_items.append({
            "label": p.get("name", "")[:60],
            "age_days": age,
            "score": round(float(score), 3),
            "freshness": freshness_label(float(score)),
        })
    dimensions["products"] = {
        "items": prod_items,
        "avg_score": round(sum(i["score"] for i in prod_items) / len(prod_items), 3) if prod_items else 0,
        "window_days": temporal.relevance_windows["products"],
        "needs_refresh": any(i["freshness"] in ("aged", "stale") for i in prod_items),
    }

    # Overall score
    all_scores = [i["score"] for dim in dimensions.values() for i in dim["items"]]
    overall = round(sum(all_scores) / len(all_scores), 3) if all_scores else 0

    return {
        "company_name": company_name,
        "overall_score": overall,
        "overall_freshness": freshness_label(overall),
        "dimensions": dimensions,
        "temporal_summary": graph_data.get("temporal_summary"),
        "freshness_updated_at": graph_data.get("company", {}).get("freshness_updated_at"),
    }


@app.get("/stock/{ticker}/around-dates")
def get_stock_around_dates(ticker: str, dates: str):
    """
    Fetch closing prices for the day before and day after each date.
    dates: comma-separated list of ISO date strings (e.g. 2025-01-10,2025-03-05)
    Returns a dict keyed by date with {before, on, after, change_pct, color}
    """
    try:
        import yfinance as yf
        from datetime import date, timedelta

        date_list = [d.strip() for d in dates.split(",") if d.strip()]
        if not date_list:
            return {}

        # Determine the full window we need to download (min - 5 days, max + 5 days)
        parsed = sorted(date.fromisoformat(d) for d in date_list)
        start = parsed[0] - timedelta(days=7)
        end   = parsed[-1] + timedelta(days=7)

        hist = yf.Ticker(ticker.upper()).history(start=start.isoformat(), end=end.isoformat())
        if hist.empty:
            return {}

        # Build a lookup: trading-date string -> close price
        prices = {str(ts.date()): round(float(close), 2)
                  for ts, close in hist["Close"].items()}
        trading_days = sorted(prices.keys())

        def nearest_trading_day(target_str: str, offset: int) -> str | None:
            """Return the trading day 'offset' days away from target (±1 means prev/next session)."""
            try:
                idx = trading_days.index(target_str)
                ni = idx + offset
                if 0 <= ni < len(trading_days):
                    return trading_days[ni]
            except ValueError:
                # target not a trading day — find nearest
                for i, td in enumerate(trading_days):
                    if td >= target_str:
                        idx = i
                        ni = idx + offset
                        if 0 <= ni < len(trading_days):
                            return trading_days[ni]
            return None

        result = {}
        for d in date_list:
            before_key = nearest_trading_day(d, -1)
            on_key     = nearest_trading_day(d,  0)
            after_key  = nearest_trading_day(d,  1)

            before_price = prices.get(before_key) if before_key else None
            on_price     = prices.get(on_key)     if on_key     else None
            after_price  = prices.get(after_key)  if after_key  else None

            # Color rule: compare close on article day vs close day after
            change_pct = None
            color = "gray"
            ref = on_price or before_price
            if ref and after_price:
                change_pct = round((after_price - ref) / ref * 100, 2)
                if change_pct <= -2.0:
                    color = "red"
                elif change_pct >= 2.0:
                    color = "green"
                else:
                    color = "black"

            result[d] = {
                "before":     {"date": before_key, "close": before_price},
                "on":         {"date": on_key,     "close": on_price},
                "after":      {"date": after_key,  "close": after_price},
                "change_pct": change_pct,
                "color":      color,
            }

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

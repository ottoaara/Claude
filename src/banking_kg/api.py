from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict, List
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

# ─── Optional API key auth ────────────────────────────────────────────────────
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def _require_api_key(api_key: Optional[str] = Security(_API_KEY_HEADER)):
    """If BANKING_API_KEY is set in env, enforce it; otherwise allow all requests."""
    expected = os.getenv("BANKING_API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


app = FastAPI(
    title="Banking Knowledge Graph API",
    description=(
        "Context Fabric — Pre-Meeting Intelligence Platform\n\n"
        "## Service API\n"
        "1. `POST /research/start` — kick off research for a company (returns `job_id`)\n"
        "2. `GET /research/status/{job_id}` — poll until `status == completed`\n"
        "3. `GET /company/{name}/report` — fetch full JSON intelligence report\n"
        "4. `GET /company/{name}/report/pdf` — download formatted PDF brief\n\n"
        "Set the `X-API-Key` request header (matching `BANKING_API_KEY` env var) "
        "to authenticate service-to-service calls."
    ),
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("BANKING_CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(","),
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


class OfficerSearchRequest(BaseModel):
    name: str
    company: str
    role: Optional[str] = None


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
    import os
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "llama3:latest")
        llm_label = f"Ollama · {model}"
    else:
        model = "claude-sonnet-4-6"
        llm_label = "Claude Sonnet 4.6"
    return {
        "status": "healthy",
        "neo4j_connected": kg is not None,
        "orchestrator_ready": orchestrator is not None,
        "llm_provider": provider,
        "llm_model": model,
        "llm_label": llm_label,
    }


@app.get("/companies")
def list_companies():
    """Return all companies that have been researched and stored in the graph."""
    global kg
    companies = kg.list_companies()
    return {"companies": companies}


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


@app.get("/company/{company_name}/report",
         dependencies=[Depends(_require_api_key)])
def get_company_report(company_name: str):
    """
    **Service endpoint** — returns a complete structured JSON intelligence report
    for a company.  Suitable for machine-to-machine consumption.

    Requires `X-API-Key` header if `BANKING_API_KEY` env var is set.
    """
    global kg

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    peer_data = kg.get_peer_comparison(company_name)
    officers  = kg.get_officers(company_name)

    return {
        "company_name": company_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "company":     graph_data.get("company", {}),
        "financials":  graph_data.get("financials", []),
        "industry":    graph_data.get("industries", []),
        "news":        graph_data.get("news", []),
        "products":    graph_data.get("products", []),
        "peer_comparison": peer_data or {},
        "officers":    officers,
        "temporal_summary": graph_data.get("temporal_summary"),
        "news_analysis":    graph_data.get("news_analysis"),
    }


@app.get("/company/{company_name}/report/pdf",
         response_class=Response,
         dependencies=[Depends(_require_api_key)])
def get_company_report_pdf(company_name: str):
    """
    **Service endpoint** — generates and streams a professional PDF intelligence
    brief for the specified company.

    Returns `application/pdf` — save with `Content-Disposition: attachment`.
    Requires `X-API-Key` header if `BANKING_API_KEY` env var is set.
    """
    from .report_generator import generate_pdf
    global kg

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    peer_data = None
    officers  = []
    try:
        peer_data = kg.get_peer_comparison(company_name)
    except Exception:
        pass
    try:
        officers = kg.get_officers(company_name)
    except Exception:
        pass

    pdf_bytes = generate_pdf(
        company_name=company_name,
        graph_data=graph_data,
        peer_data=peer_data,
        officers=officers,
    )

    safe_name = company_name.replace(" ", "_").replace("/", "-")
    date_str  = datetime.utcnow().strftime("%Y%m%d")
    filename  = f"{safe_name}_intelligence_brief_{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/company/{company_name}/officers")
def get_company_officers(company_name: str):
    """Return stored officer profiles for a company."""
    global kg
    officers = kg.get_officers(company_name)
    return {"company_name": company_name, "officers": officers, "total": len(officers)}


@app.get("/company/{company_name}/board-interlocks")
def get_board_interlocks(company_name: str):
    """Return a board interlock map: for each officer, list their external board seats.
    Each interlock includes a wf_officers list — any WF board members / executives
    who also sit on that same external board.
    """
    from .bank_officers import BANK_OFFICERS, boards_match
    global kg
    officers = kg.get_officers(company_name)

    # Build a lookup: normalised board name → list of WF officer dicts
    wf_board_index: dict = {}
    for wf in BANK_OFFICERS:
        for seat in (wf.get("board_seats") or []):
            seat = seat.strip()
            if not seat:
                continue
            # Index under the canonical (first-seen) name for that board
            matched = next((k for k in wf_board_index if boards_match(k, seat)), None)
            if matched:
                wf_board_index[matched].append(wf)
            else:
                wf_board_index[seat] = [wf]

    interlocks = []
    for o in officers:
        boards = o.get("board_memberships") or []
        for board_entry in boards:
            if isinstance(board_entry, str) and board_entry.strip():
                board_name = board_entry.strip()
                # Find any WF officers who also sit on this board
                wf_matches = next(
                    (v for k, v in wf_board_index.items() if boards_match(k, board_name)),
                    []
                )
                interlocks.append({
                    "officer_name":       o.get("name", ""),
                    "officer_role":       o.get("role", ""),
                    "officer_role_short": o.get("role_short", ""),
                    "board_company":      board_name,
                    "is_board_member":    o.get("is_board", False),
                    "wf_officers": [
                        {"name": wf["name"], "role_short": wf["role_short"]}
                        for wf in wf_matches
                    ],
                })

    # Group by officer for easy rendering
    by_officer: dict = {}
    for entry in interlocks:
        key = entry["officer_name"]
        if key not in by_officer:
            by_officer[key] = {
                "officer_name":       entry["officer_name"],
                "officer_role":       entry["officer_role"],
                "officer_role_short": entry["officer_role_short"],
                "board_seats": [],
            }
        by_officer[key]["board_seats"].append({
            "company":     entry["board_company"],
            "wf_officers": entry["wf_officers"],
        })

    # Summary: all boards where at least one WF officer also sits
    shared_boards = [
        e["board_company"] for e in interlocks if e["wf_officers"]
    ]
    unique_shared = list(dict.fromkeys(shared_boards))  # dedup, preserve order

    return {
        "company_name":         company_name,
        "total_officers":       len(officers),
        "officers_with_boards": len(by_officer),
        "shared_with_wf_count": len(unique_shared),
        "shared_with_wf":       unique_shared,
        "interlocks":           list(by_officer.values()),
    }


@app.get("/company/{company_name}/relationship-map")
def get_relationship_map(company_name: str):
    """
    Cross-reference company officers against the bank's own board/leadership.
    Returns:
      - board_connections: officers who share external board seats with bank officers
      - alumni_connections: officers who attended the same school as bank officers
    Each connection includes profile_freshness metadata so the UI can flag stale data.
    """
    from .bank_officers import find_relationship_connections, BANK_NAME
    from .temporal import TemporalDimension

    global kg
    officers = kg.get_officers(company_name)
    temporal = TemporalDimension()

    # Build a name → officer lookup for freshness scoring
    officer_by_name = {(o.get("name") or "").strip().lower(): o for o in officers}

    connections = find_relationship_connections(officers, kg=kg)

    # Annotate every board connection with the source officer's profile freshness
    for conn in connections.get("board_connections", []):
        officer_key = (conn.get("company_officer") or "").strip().lower()
        officer = officer_by_name.get(officer_key, {})
        conn["profile_freshness"] = temporal.score_officer_freshness(officer)

    # Same for alumni connections
    for conn in connections.get("alumni_connections", []):
        officer_key = (conn.get("company_officer") or "").strip().lower()
        officer = officer_by_name.get(officer_key, {})
        conn["profile_freshness"] = temporal.score_officer_freshness(officer)

    # Overall staleness flag: True if any connection has a stale profile
    any_stale = any(
        c.get("profile_freshness", {}).get("needs_refresh", False)
        for group in ("board_connections", "alumni_connections")
        for c in connections.get(group, [])
    )

    return {
        "company_name": company_name,
        "bank_name": BANK_NAME,
        "has_stale_profiles": any_stale,
        **connections,
    }


@app.post("/officer/search")
def search_officer(request: OfficerSearchRequest):
    """
    Research a specific individual by name and company.
    Useful when the RM's contact is not in the automatically discovered officer list.
    Saves the profile to Neo4j so it appears in the Officers tab.
    """
    from .agents.officer_agent import OfficerAgent
    global kg

    agent = OfficerAgent()
    profile = agent.research_officer(
        request.name, request.company, request.role or ""
    )

    # Persist to Neo4j (best-effort — company may not exist yet)
    try:
        kg.add_officer(request.company, profile)
    except Exception:
        pass

    return profile


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

    PEER_KEEP = {"name", "ticker", "revenue", "net_income", "operating_income",
                 "total_assets", "stockholders_equity", "filing_period",
                 "filing_type", "relationship", "estimated_size", "net_margin"}

    def net_margin(revenue, net_income):
        try:
            if revenue and net_income and float(revenue) != 0:
                return round(float(net_income) / float(revenue) * 100, 2)
        except Exception:
            pass
        return None

    def clean(record: dict, keep_keys: set = None) -> dict:
        out = {}
        for k, v in record.items():
            if keep_keys and k not in keep_keys:
                continue
            # Strip Neo4j DateTime objects and other non-serialisable types
            if isinstance(v, (str, int, float, bool, type(None))):
                out[k] = v
            elif isinstance(v, list):
                out[k] = [x for x in v if isinstance(x, (str, int, float, bool))]
            # Skip anything else (Neo4j DateTime, Point, etc.)
        out["net_margin"] = net_margin(out.get("revenue"), out.get("net_income"))
        return out

    data["target"] = clean(data["target"])
    data["peers"] = [clean(p, PEER_KEEP | {"name"}) for p in data.get("peers", [])]

    return data


@app.get("/company/{company_name}/freshness")
def get_company_freshness(
    company_name: str,
    fin_window: Optional[int] = None,
    news_window: Optional[int] = None,
    prod_window: Optional[int] = None,
):
    """
    Return per-dimension data freshness scores for a company.
    Accepts optional window overrides (in days) per dimension:
      fin_window, news_window, prod_window
    """
    from .temporal import TemporalDimension
    from datetime import datetime

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    temporal = TemporalDimension()
    # Apply per-request window overrides
    if fin_window  is not None: temporal.relevance_windows["financial"]  = max(1, fin_window)
    if news_window is not None: temporal.relevance_windows["news"]       = max(1, news_window)
    if prod_window is not None: temporal.relevance_windows["products"]   = max(1, prod_window)

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
        cached = f.get("relevance_score") if fin_window is None else None
        score = cached or temporal.calculate_recency_score(
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
        cached = n.get("relevance_score") if news_window is None else None
        score = cached or temporal.calculate_recency_score(
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
        cached = p.get("relevance_score") if prod_window is None else None
        score = cached or temporal.calculate_recency_score(
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


@app.get("/company/{company_name}/recommendations")
def get_recommendations(company_name: str):
    """
    Synthesise all research data into a structured sales recommendation:
    customer profile, identified needs, suggested WF wholesale products,
    sales approach, and risk considerations.
    Uses Claude Sonnet for synthesis.
    """
    global kg

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    try:
        peer_data = kg.get_peer_comparison(company_name)
    except Exception:
        peer_data = {}
    try:
        officers = kg.get_officers(company_name)
    except Exception:
        officers = []

    # Relationship map: shared boards + alumni with WF officers
    try:
        from .bank_officers import find_relationship_connections
        rel_map = find_relationship_connections(officers, kg=kg)
        board_connections = rel_map.get("board_connections", [])
        alumni_connections = rel_map.get("alumni_connections", [])
    except Exception:
        board_connections = []
        alumni_connections = []

    # Incumbent bank data (cached or fetched)
    try:
        incumbent_raw = kg.get_company_graph(company_name) or {}
        # Check if we have cached incumbent data as a property on the company node
        incumbent_cached = (incumbent_raw.get("company") or {}).get("incumbent_bank_json")
        if incumbent_cached:
            import json as _ijson
            incumbent_data = _ijson.loads(incumbent_cached) if isinstance(incumbent_cached, str) else incumbent_cached
        else:
            incumbent_data = {}
    except Exception:
        incumbent_data = {}

    # Build compact context for Claude
    company       = graph_data.get("company", {})
    fins          = graph_data.get("financials", [])
    news          = graph_data.get("news", [])
    products      = graph_data.get("products", [])
    industry_list = graph_data.get("industries", [])
    industry      = industry_list[0] if industry_list else {}
    news_analysis = graph_data.get("news_analysis", {})

    latest_fin    = fins[0] if fins else {}
    material_news = [n for n in news if n.get("is_material") or n.get("severity") == "high"][:5]
    key_officers  = [{"name": o.get("name"), "title": o.get("title")} for o in officers[:5]]
    peers         = (peer_data.get("peers") or [])[:4]

    context = {
        "company": {
            "name": company_name,
            "description": company.get("description", ""),
            "industry": company.get("industry", ""),
            "headquarters": company.get("headquarters", ""),
            "website": company.get("website", ""),
        },
        "financials": {
            "revenue_millions": latest_fin.get("revenue"),
            "net_income_millions": latest_fin.get("net_income"),
            "total_assets_millions": latest_fin.get("total_assets"),
            "long_term_debt_millions": latest_fin.get("long_term_debt"),
            "operating_cash_flow_millions": latest_fin.get("operating_cash_flow"),
            "free_cash_flow_millions": latest_fin.get("free_cash_flow"),
            "filing_period": latest_fin.get("filing_period"),
        },
        "industry": {
            "naics_sector": industry.get("naics_sector_name", ""),
            "growth_outlook": industry.get("growth_outlook", ""),
            "key_trends": (industry.get("key_trends") or [])[:3],
        },
        "peers": [{"name": p.get("name"), "revenue": p.get("revenue")} for p in peers],
        "news_risk": {
            "overall_risk_level": news_analysis.get("risk_level", "unknown"),
            "key_concerns": (news_analysis.get("key_concerns") or [])[:3],
            "material_events": [n.get("title", "")[:80] for n in material_news],
        },
        "products": [p.get("name", "") for p in products[:5]],
        "key_officers": key_officers,
        "relationship_map": {
            "board_connections": [
                {
                    "company_officer": c["company_officer"],
                    "company_role": c["company_role"],
                    "shared_board": c["shared_board"],
                    "bank_officer": c["bank_officer"],
                    "bank_role": c["bank_role"],
                }
                for c in board_connections
            ],
            "alumni_connections": [
                {
                    "company_officer": c["company_officer"],
                    "company_role": c["company_role"],
                    "shared_school": c["shared_school"],
                    "bank_officer": c["bank_officer"],
                    "bank_role": c["bank_role"],
                }
                for c in alumni_connections
            ],
        },
        "incumbent_bank": {
            "primary_bank": incumbent_data.get("primary_bank"),
            "facility_type": incumbent_data.get("facility_type"),
            "facility_size": incumbent_data.get("facility_size"),
            "maturity_date": incumbent_data.get("maturity_date"),
            "maturity_status": incumbent_data.get("maturity_status"),
            "maturity_note": incumbent_data.get("maturity_note"),
            "wells_fargo_involved": incumbent_data.get("wells_fargo_involved"),
            "wf_advantages": incumbent_data.get("wf_advantages", []),
            "displacement_strategy": incumbent_data.get("displacement_strategy"),
            "urgency_rating": incumbent_data.get("urgency_rating"),
        } if incumbent_data.get("primary_bank") else None,
    }

    import json as _json
    from langchain_core.prompts import ChatPromptTemplate as _CPT
    from .llm_factory import robust_parse_json, get_llm

    llm = get_llm(temperature=0.3, json_mode=True)

    prompt = _CPT.from_messages([
        ("system", """You are a senior Wells Fargo Commercial Banking relationship manager preparing for a client meeting.
Using the provided company intelligence, generate a structured sales recommendation brief.

IMPORTANT: The context includes a `relationship_map` with two types of warm entry points:
- `board_connections`: company officers who sit on the same external board as a WF board member/executive
- `alumni_connections`: company officers who attended the same school as a WF board member/executive
These are REAL, actionable warm introduction paths — reference them specifically in your response.

INCUMBENT BANK: If `incumbent_bank` data is present, use it directly to sharpen the pitch:
- Name the specific incumbent bank and facility in your competitive_considerations
- Where WF advantages are listed, incorporate them into recommended_products pitches
- Reference the maturity date as a conversation trigger if within 24 months
- If wells_fargo_involved is false, frame this as a full displacement opportunity
- If wells_fargo_involved is true, frame this as a wallet-share expansion opportunity

Return ONLY a valid JSON object with these exact fields:

{{
  "customer_profile": "2-3 sentence summary of who this company is and their financial standing",
  "relationship_tier": "Tier 1 (>$1B revenue)" or "Tier 2 ($250M-$1B)" or "Tier 3 ($50M-$250M)" or "Tier 4 (<$50M)",
  "credit_assessment": "1-2 sentence credit quality assessment based on financials and news",
  "identified_needs": [
    {{ "need": "short need title", "rationale": "1 sentence why based on data" }}
  ],
  "recommended_products": [
    {{
      "product": "product name",
      "category": "Treasury Management" or "Credit & Lending" or "Capital Markets" or "Trade Finance" or "Risk Management" or "Deposits",
      "fit_score": 1-10,
      "pitch": "1-2 sentence tailored pitch for this specific company — reference incumbent bank by name if known",
      "estimated_deal_size": "e.g. $5M-$25M credit facility",
      "vs_incumbent": "1 sentence on how this WF product is better than what the incumbent offers, or null if not relevant"
    }}
  ],
  "sales_approach": {{
    "primary_entry_point": "which officer to target first and why — if relationship_map has connections, lead with those",
    "key_talking_points": ["3-5 talking points tailored to their situation — include incumbent displacement angle if applicable"],
    "meeting_agenda_suggestion": "suggested agenda for first meeting",
    "competitive_considerations": "specific note on the incumbent bank, their facility, what WF can do differently — be specific"
  }},
  "relationship_entry_points": [
    {{
      "type": "board_interlock" or "alumni",
      "company_officer": "name and role at target company",
      "connection": "shared board name or shared school",
      "bank_contact": "WF officer name and role",
      "action": "1 sentence on how to use this connection to get a warm intro"
    }}
  ],
  "risk_considerations": ["2-4 risks the banker should be aware of"],
  "next_steps": ["3-4 concrete action items — include incumbent bank refi timeline if maturity is within 24 months"]
}}

Recommend 4-6 specific Wells Fargo wholesale products. Be specific and data-driven — reference actual numbers where possible."""),
        ("user", "Company intelligence:\n\n{context}")
    ])

    chain = prompt | llm
    response = chain.invoke({"context": _json.dumps(context, indent=2)})

    result = robust_parse_json(response.content, {})
    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

    result["generated_at"] = datetime.utcnow().isoformat() + "Z"
    result["company_name"] = company_name
    return result


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




# ── Pydantic models for new features ─────────────────────────────────────────

class ActivityRequest(BaseModel):
    type: str  # "call" | "email" | "meeting" | "note"
    date: str  # ISO date string
    contact_name: Optional[str] = ""
    contact_role: Optional[str] = ""
    notes: Optional[str] = ""
    next_action: Optional[str] = ""

class DealRequest(BaseModel):
    product: str
    category: str  # "Treasury Management" | "Credit & Lending" | etc
    status: str = "active"  # "active" | "pipeline" | "closed" | "lost"
    amount: Optional[str] = ""
    start_date: Optional[str] = ""
    notes: Optional[str] = ""


# ── Deal Triggers ─────────────────────────────────────────────────────────────

@app.get("/company/{company_name}/triggers")
def get_deal_triggers(company_name: str):
    """
    Analyse existing news + financial data to surface deal triggers:
    M&A activity, capital raises, debt maturities, leadership transitions,
    covenant stress, regulatory events.
    Returns a list of triggers with type, evidence, urgency, and recommended action.
    """
    global kg
    from langchain_core.prompts import ChatPromptTemplate as _CPT
    from .llm_factory import robust_parse_json, get_llm
    import json as _json

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    fins = graph_data.get("financials", [])
    news = graph_data.get("news", [])
    news_analysis = graph_data.get("news_analysis", {}) or {}
    company = graph_data.get("company", {})

    # Unpack data_json for financials
    unpacked_fins = []
    for f in fins[:3]:
        try:
            inner = _json.loads(f.get("data_json", "{}") or "{}")
            inner2 = _json.loads(inner.get("data_json", "{}") or "{}")
            merged = {**inner2, **inner, **f, "data_json": None}
            unpacked_fins.append(merged)
        except Exception:
            unpacked_fins.append(f)

    context = {
        "company": company_name,
        "industry": company.get("industry", ""),
        "recent_news": [{"title": n.get("title",""), "date": n.get("date",""),
                         "sentiment": n.get("sentiment",""), "is_material": n.get("is_material",False),
                         "event_types": n.get("event_types",[]), "summary": n.get("summary","")} for n in news[:15]],
        "news_risk_level": news_analysis.get("risk_level",""),
        "material_events": news_analysis.get("material_events",[]),
        "key_concerns": news_analysis.get("key_concerns",[]),
        "financials": [{"period": f.get("filing_period") or f.get("period",""),
                        "revenue": f.get("revenue"), "net_income": f.get("net_income"),
                        "total_assets": f.get("total_assets"), "long_term_debt": f.get("long_term_debt"),
                        "operating_cash_flow": f.get("operating_cash_flow")} for f in unpacked_fins],
    }

    llm = get_llm(temperature=0, json_mode=True)
    prompt = _CPT.from_messages([
        ("system", """You are a commercial banking deal origination specialist.
Analyse the company's news and financial data to identify DEAL TRIGGERS — signals that the company
will likely need banking products or services soon.

Return a JSON array of trigger objects. Each trigger:
{{
  "type": one of ["M&A", "Capital Raise", "Debt Refinancing", "Leadership Transition",
                  "Expansion", "Distress", "Regulatory", "IPO/Exit", "Supply Chain"],
  "title": "Short descriptive title (max 10 words)",
  "evidence": "1-2 sentence summary of what signals this trigger",
  "urgency": "high" | "medium" | "low",
  "recommended_product": "The most relevant WF product for this trigger",
  "action": "1 sentence — what should the RM do in the next 2 weeks"
}}

Return 0–6 triggers. Only include real signals from the data — do not hallucinate triggers.
Return ONLY valid JSON array."""),
        ("user", "Company data:\n{context}")
    ])
    result = robust_parse_json(
        (prompt | llm).invoke({"context": _json.dumps(context, indent=2)}).content, []
    )
    if not isinstance(result, list):
        result = []

    # ── Temporal: apply contact-recency urgency boost ─────────────────────
    from .temporal import TemporalDimension
    activities = kg.get_activities(company_name)
    temporal = TemporalDimension()
    recency = temporal.contact_urgency_boost(activities)

    if recency["boost_factor"] >= 2.0:
        # Extended silence — escalate all triggers
        for t in result:
            if t.get("urgency") in ("medium", "low"):
                t["urgency"] = "high"
                t["urgency_boosted"] = True
    elif recency["boost_factor"] >= 1.5:
        # Contact gap — escalate medium triggers
        for t in result:
            if t.get("urgency") == "medium":
                t["urgency"] = "high"
                t["urgency_boosted"] = True

    return {
        "company_name": company_name,
        "triggers": result,
        "contact_recency": recency,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ── Covenant Watch ────────────────────────────────────────────────────────────

@app.get("/company/{company_name}/covenant-watch")
def get_covenant_watch(company_name: str):
    """
    Compute financial health ratios from stored EDGAR data and flag
    any that approach standard loan covenant thresholds.
    """
    global kg
    import json as _json

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    fins = graph_data.get("financials", [])
    periods = []
    for f in fins:
        try:
            inner = _json.loads(f.get("data_json","{}") or "{}")
            inner2 = _json.loads(inner.get("data_json","{}") or "{}")
            merged = {**inner2, **inner, **f}
        except Exception:
            merged = f
        period = merged.get("filing_period") or merged.get("period","Unknown")
        rev = merged.get("revenue")
        ni = merged.get("net_income")
        assets = merged.get("total_assets")
        liab = merged.get("total_liabilities")
        equity = merged.get("stockholders_equity")
        ocf = merged.get("operating_cash_flow")
        op_inc = merged.get("operating_income")
        interest = merged.get("interest_expense")
        lt_debt = merged.get("long_term_debt")

        def ratio(n, d):
            try:
                if n is None or d is None or float(d) == 0: return None
                return round(float(n) / float(d), 2)
            except Exception:
                return None

        ratios = {}

        # Debt/EBITDA — covenant typically <4.0x
        ebitda = None
        if op_inc is not None:
            da = merged.get("depreciation_amortization")
            ebitda = float(op_inc) + (float(da) if da else 0)
        if lt_debt and ebitda and ebitda > 0:
            ratios["debt_ebitda"] = {"value": round(float(lt_debt)/ebitda,2), "threshold": 4.0, "label": "Debt/EBITDA", "higher_is_worse": True}

        # Interest Coverage (EBIT/Interest) — covenant typically >2.5x
        if op_inc and interest and float(interest) > 0:
            ratios["interest_coverage"] = {"value": round(float(op_inc)/float(interest),2), "threshold": 2.5, "label": "Interest Coverage", "higher_is_worse": False}

        # Current ratio — from assets/liabilities proxy
        # Net margin
        if rev and ni and float(rev) > 0:
            ratios["net_margin"] = {"value": round(float(ni)/float(rev)*100,1), "threshold": 0, "label": "Net Margin (%)", "higher_is_worse": False}

        # Leverage: Debt/Equity
        if lt_debt and equity and float(equity) > 0:
            ratios["debt_equity"] = {"value": round(float(lt_debt)/float(equity),2), "threshold": 3.0, "label": "Debt/Equity", "higher_is_worse": True}

        # Return on Assets
        if ni and assets and float(assets) > 0:
            ratios["roa"] = {"value": round(float(ni)/float(assets)*100,1), "threshold": 2.0, "label": "Return on Assets (%)", "higher_is_worse": False}

        # Flag each ratio
        for key, r in ratios.items():
            v, t = r["value"], r["threshold"]
            if v is None:
                r["status"] = "unknown"
            elif r["higher_is_worse"]:
                r["status"] = "red" if v > t else ("yellow" if v > t * 0.8 else "green")
            else:
                r["status"] = "red" if v < t else ("yellow" if v < t * 1.25 else "green")

        if ratios:
            periods.append({"period": period, "filing_type": merged.get("filing_type",""), "ratios": ratios})

    any_red = any(r["status"] == "red" for p in periods for r in p["ratios"].values())
    any_yellow = any(r["status"] == "yellow" for p in periods for r in p["ratios"].values())
    overall = "red" if any_red else ("yellow" if any_yellow else "green")

    return {"company_name": company_name, "overall_status": overall,
            "periods": periods, "generated_at": datetime.utcnow().isoformat() + "Z"}


# ── Incumbent Bank Detection ──────────────────────────────────────────────────

@app.get("/company/{company_name}/incumbent-bank")
def get_incumbent_bank(company_name: str, ticker: Optional[str] = None):
    """
    Search SEC EDGAR and web for credit agreement language to identify
    the company's current banking relationships.
    """
    from ddgs import DDGS
    from langchain_core.prompts import ChatPromptTemplate as _CPT
    from .llm_factory import robust_parse_json, get_llm
    import json as _json

    # Also check stored ticker
    global kg
    graph_data = kg.get_company_graph(company_name)
    stored_ticker = ticker or (graph_data or {}).get("company", {}).get("ticker", "")

    queries = [
        f'"{company_name}" "credit agreement" "administrative agent" bank 2023 OR 2024 OR 2025 OR 2026',
        f'"{company_name}" "revolving credit facility" "lead arranger" lender',
        f'{stored_ticker or company_name} SEC 10-K "credit facility" "administrative agent" bank',
        f'"{company_name}" "term loan" "syndicated" bank agent lender',
    ]

    all_hits = []
    with DDGS() as ddgs:
        for q in queries:
            try:
                hits = list(ddgs.text(q, max_results=5))
                all_hits.extend(hits)
            except Exception:
                pass

    snippets = [{"title": h.get("title","")[:120], "snippet": h.get("body",h.get("snippet",""))[:300],
                 "url": h.get("href",h.get("url",""))} for h in all_hits[:20]]

    if not snippets:
        return {"company_name": company_name, "banks_identified": [],
                "confidence": "low", "note": "No credit agreement data found"}

    llm = get_llm(temperature=0, json_mode=True)
    prompt = _CPT.from_messages([
        ("system", """Extract banking relationships from credit agreement search results.
Return a JSON object with these fields:
primary_bank (string or null), other_lenders (array of strings),
facility_type (string), facility_size (string or null),
maturity_date (string year or null), confidence (high/medium/low),
sources (array of urls), wells_fargo_involved (boolean),
opportunity (1 sentence string).
Return ONLY valid JSON, no markdown."""),
        ("user", "Company: {company_name}\nTicker: {ticker}\n\nSearch results:\n{search_results}")
    ])
    result = robust_parse_json((prompt | llm).invoke({
        "company_name": company_name,
        "ticker": stored_ticker or "",
        "search_results": _json.dumps(snippets, indent=2),
    }).content, {})
    if not result:
        result = {"primary_bank": None, "confidence": "low", "other_lenders": []}
    result["company_name"] = company_name
    result["generated_at"] = datetime.utcnow().isoformat() + "Z"

    # ── Temporal: maturity date opportunity scoring ────────────────────────
    import re as _re
    maturity_raw = result.get("maturity_date")
    maturity_status = None
    maturity_note = None
    reliability_score = {"high": 0.9, "medium": 0.6, "low": 0.3}.get(
        result.get("confidence", "low"), 0.3
    )

    if maturity_raw:
        year_match = _re.search(r'\b(20\d{2})\b', str(maturity_raw))
        if year_match:
            maturity_year = int(year_match.group(1))
            current_year = datetime.utcnow().year
            years_to_maturity = maturity_year - current_year

            if years_to_maturity < 0:
                maturity_status = "past_due"
                maturity_note = (
                    f"Facility matured in {maturity_year} — likely already refinanced. "
                    "Verify current lender before the meeting."
                )
                reliability_score = max(0.15, reliability_score - 0.35)
            elif years_to_maturity == 0:
                maturity_status = "maturing_this_year"
                maturity_note = (
                    f"Facility matures in {maturity_year} — active refinancing window NOW. "
                    "Prioritise outreach immediately."
                )
            elif years_to_maturity == 1:
                maturity_status = "within_12_months"
                maturity_note = (
                    f"Facility matures within 12 months ({maturity_year}) — "
                    "refinancing conversations should begin now."
                )
            elif years_to_maturity <= 2:
                maturity_status = "within_24_months"
                maturity_note = (
                    f"Facility matures within 24 months ({maturity_year}) — "
                    "begin relationship-building ahead of the refi window."
                )
            else:
                maturity_status = "current"
                maturity_note = (
                    f"Facility matures in {maturity_year} — "
                    "monitor for early refinancing signals or covenant stress."
                )

    result["maturity_status"] = maturity_status
    result["maturity_note"] = maturity_note
    result["reliability_score"] = round(reliability_score, 2)

    # ── WF Competitive Product Analysis ──────────────────────────────────
    # Compare incumbent bank offering vs Wells Fargo product suite
    company_info = (graph_data or {}).get("company", {})
    fins = (graph_data or {}).get("financials", [])
    latest_fin = fins[0] if fins else {}

    competitive_prompt = _CPT.from_messages([
        ("system", """You are a senior Wells Fargo Commercial Banking product specialist.
Compare the detected incumbent bank relationship with Wells Fargo's product suite.
Return ONLY a valid JSON object with these exact fields:
wf_advantages (array of objects), displacement_strategy (string), urgency_rating (high/medium/low).
Each wf_advantages object must have: product (string), category (string), advantage (string), incumbent_gap (string), estimated_size (string).
Be specific to this company's situation and the incumbent's known offerings."""),
        ("user", """Company: {company_name}
Revenue: {revenue}
Long-term debt: {lt_debt}
Incumbent bank: {primary_bank}
Facility type: {facility_type}
Facility size: {facility_size}
Maturity: {maturity_date} ({maturity_status})
Wells Fargo involved: {wf_involved}

Identify 3-5 specific Wells Fargo products or services where WF would offer a better fit, lower cost, or stronger capability than the incumbent. Focus on realistic displacement opportunities given this company's size and the existing facility structure.""")
    ])

    try:
        comp_result = robust_parse_json(
            (competitive_prompt | llm).invoke({
                "company_name": company_name,
                "revenue": latest_fin.get("revenue") or "unknown",
                "lt_debt": latest_fin.get("long_term_debt") or "unknown",
                "primary_bank": result.get("primary_bank") or "unknown",
                "facility_type": result.get("facility_type") or "unknown",
                "facility_size": result.get("facility_size") or "unknown",
                "maturity_date": result.get("maturity_date") or "unknown",
                "maturity_status": maturity_status or "unknown",
                "wf_involved": str(result.get("wells_fargo_involved", False)),
            }).content,
            {}
        )
        result["wf_advantages"] = comp_result.get("wf_advantages", [])
        result["displacement_strategy"] = comp_result.get("displacement_strategy", "")
        result["urgency_rating"] = comp_result.get("urgency_rating", "medium")
    except Exception:
        result["wf_advantages"] = []
        result["displacement_strategy"] = ""
        result["urgency_rating"] = "medium"

    return result


# ── Meeting Brief ─────────────────────────────────────────────────────────────

@app.get("/company/{company_name}/meeting-brief")
def get_meeting_brief(company_name: str,
                      contact_name: Optional[str] = None,
                      contact_role: Optional[str] = None):
    """
    Generate a concise pre-meeting intelligence brief synthesising all
    available company data. Optionally personalised to a specific contact.
    """
    global kg
    from langchain_core.prompts import ChatPromptTemplate as _CPT
    from .llm_factory import robust_parse_json, get_llm
    from .bank_officers import find_relationship_connections
    import json as _json

    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    fins = graph_data.get("financials", [])
    news = graph_data.get("news", [])
    news_analysis = graph_data.get("news_analysis", {}) or {}
    company = graph_data.get("company", {})
    industries = graph_data.get("industries", [])
    officers = kg.get_officers(company_name)
    rel_map = find_relationship_connections(officers, kg=kg)
    activities = kg.get_activities(company_name)
    deals = kg.get_deals(company_name)

    # Unpack latest financials
    latest_fin = {}
    if fins:
        f = fins[0]
        try:
            inner = _json.loads(f.get("data_json","{}") or "{}")
            inner2 = _json.loads(inner.get("data_json","{}") or "{}")
            latest_fin = {**inner2, **inner, **f, "data_json": None}
        except Exception:
            latest_fin = f

    context = {
        "company": company_name,
        "description": company.get("description",""),
        "industry": (industries[0].get("name","") if industries else company.get("industry","")),
        "contact": f"{contact_name or 'Unknown'} ({contact_role or 'Unknown role'})",
        "financials": {
            "revenue": latest_fin.get("revenue"), "net_income": latest_fin.get("net_income"),
            "period": latest_fin.get("filing_period") or latest_fin.get("period",""),
            "operating_cash_flow": latest_fin.get("operating_cash_flow"),
        },
        "key_concerns": (news_analysis.get("key_concerns") or [])[:4],
        "positive_signals": (news_analysis.get("positive_signals") or [])[:3],
        "risk_level": news_analysis.get("risk_level",""),
        "recent_material_news": [n.get("title","") for n in news if n.get("is_material")][:3],
        "top_officers": [{"name": o.get("name",""), "role": o.get("role","")} for o in officers[:5]],
        "board_connections": rel_map.get("board_connections",[]),
        "alumni_connections": rel_map.get("alumni_connections",[]),
        "existing_deals": [{"product": d.get("product",""), "status": d.get("status","")} for d in deals],
        "last_contact": activities[0].get("date","") if activities else "No contact on record",
        "last_activity_notes": activities[0].get("notes","") if activities else "",
    }

    llm = get_llm(temperature=0.2, json_mode=True)
    prompt = _CPT.from_messages([
        ("system", """You are a senior Wells Fargo commercial banker generating a pre-meeting brief.
Be concise, actionable, and specific. Reference actual numbers and names from the data.

Return ONLY a JSON object with these fields:
{{
  "headline": "One sentence framing why this meeting matters right now",
  "company_snapshot": "2-3 sentences on company health and momentum",
  "three_things_going_well": ["3 specific positives with data points"],
  "three_risks": ["3 specific risks the banker should be aware of"],
  "likely_ask": "What this company probably needs from a bank right now",
  "entry_points": ["Up to 3 warm intro angles — shared boards, alumni, existing deals, referrals"],
  "smart_questions": ["5 questions that will impress the contact and surface needs"],
  "dont_mention": ["1-2 sensitive topics to avoid based on news/risk data"],
  "one_slide_summary": "3-sentence executive summary suitable for a pre-call email"
}}"""),
        ("user", "Meeting context:\n{context}")
    ])
    result = robust_parse_json((prompt | llm).invoke({"context": _json.dumps(context, indent=2)}).content, {})
    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate meeting brief")
    result["company_name"] = company_name
    result["contact_name"] = contact_name
    result["contact_role"] = contact_role
    result["generated_at"] = datetime.utcnow().isoformat() + "Z"
    return result


# ── Activity Log ──────────────────────────────────────────────────────────────

@app.get("/company/{company_name}/activity")
def get_activities(company_name: str):
    global kg
    activities = kg.get_activities(company_name)
    last = activities[0] if activities else None
    return {"company_name": company_name, "activities": activities,
            "total": len(activities), "last_contact": last}

@app.post("/company/{company_name}/activity")
def add_activity(company_name: str, request: ActivityRequest):
    global kg
    activity_id = kg.add_activity(company_name, request.dict())
    return {"activity_id": activity_id, "status": "created"}

@app.delete("/activity/{activity_id}")
def delete_activity(activity_id: str):
    global kg
    kg.delete_activity(activity_id)
    return {"status": "deleted"}


# ── Deals / Prior Products ────────────────────────────────────────────────────

@app.get("/company/{company_name}/deals")
def get_deals(company_name: str):
    global kg
    deals = kg.get_deals(company_name)
    return {"company_name": company_name, "deals": deals, "total": len(deals)}

@app.post("/company/{company_name}/deals")
def add_deal(company_name: str, request: DealRequest):
    global kg
    deal_id = kg.add_deal(company_name, request.dict())
    return {"deal_id": deal_id, "status": "created"}

@app.delete("/deal/{deal_id}")
def delete_deal(deal_id: str):
    global kg
    kg.delete_deal(deal_id)
    return {"status": "deleted"}


# ── RM Portfolio Dashboard ────────────────────────────────────────────────────

# ── Pitch Opportunity Score ───────────────────────────────────────────────────

def _compute_pitch_score(company_name: str, kg_instance, graph_data: dict = None) -> dict:
    """
    Deterministic, no-LLM scoring of a company's pitch opportunity.
    Reads stored Neo4j data only — safe to call in bulk.

    Component weights (100 pts total):
      Timing          25 pts  — incumbent bank maturity proximity
      Covenant Stress 20 pts  — red/yellow financial ratios
      Deal Triggers   24 pts  — cached high/medium urgency triggers
      Relationship    16 pts  — fresh board/alumni connections
      Contact Gap     15 pts  — days since last RM activity

    Grade:  A ≥ 80  |  B 60–79  |  C 40–59  |  D 20–39  |  F < 20
    """
    import json as _json
    from .temporal import TemporalDimension
    from .bank_officers import find_relationship_connections

    temporal = TemporalDimension()
    gd = graph_data or (kg_instance.get_company_graph(company_name) or {})
    activities = kg_instance.get_activities(company_name)
    officers   = kg_instance.get_officers(company_name)

    breakdown = {}

    # ── 1. TIMING (25 pts) ────────────────────────────────────────────────
    # Source: latest financial filing period as proxy for maturity proximity
    # (Full incumbent-bank search is expensive; use stored financial dates instead)
    timing_score = 0
    fins = gd.get("financials", [])
    if fins:
        f = fins[0]
        try:
            inner  = _json.loads(f.get("data_json","{}") or "{}")
            inner2 = _json.loads(inner.get("data_json","{}") or "{}")
            merged = {**inner2, **inner, **f}
        except Exception:
            merged = f
        period = merged.get("filing_period") or merged.get("period","")
        lt_debt = merged.get("long_term_debt")
        # If company has material long-term debt and recent filing: higher timing score
        if lt_debt:
            try:
                debt_val = float(lt_debt)
                if debt_val > 0:
                    # Score by debt magnitude (larger = more refinancing opportunity)
                    # Cap at 20 pts; base timing 5 pts for any debt presence
                    timing_score = min(20, 5 + int(debt_val / 1e8))  # +1 pt per $100M
                    timing_score = max(5, timing_score)
            except Exception:
                timing_score = 5
        # Recency bonus: if filing is within 120 days, company is active
        filing_recency = temporal.calculate_recency_score(period, "financial") if period else 0.5
        timing_score = min(25, int(timing_score * (0.7 + 0.5 * filing_recency)))
    breakdown["timing"] = {"score": timing_score, "max": 25}

    # ── 2. COVENANT STRESS (20 pts) ───────────────────────────────────────
    covenant_score = 0
    if fins:
        red_count = 0
        yellow_count = 0
        for f in fins[:2]:
            try:
                inner  = _json.loads(f.get("data_json","{}") or "{}")
                inner2 = _json.loads(inner.get("data_json","{}") or "{}")
                merged = {**inner2, **inner, **f}
            except Exception:
                merged = f
            op_inc   = merged.get("operating_income")
            interest = merged.get("interest_expense")
            lt_debt  = merged.get("long_term_debt")
            ni       = merged.get("net_income")
            rev      = merged.get("revenue")
            assets   = merged.get("total_assets")
            # Interest coverage < 2.5 = red, < 3.5 = yellow
            if op_inc and interest:
                try:
                    cov = float(op_inc) / float(interest)
                    if cov < 2.5: red_count += 1
                    elif cov < 3.5: yellow_count += 1
                except Exception: pass
            # Net margin < 0 = red, < 3% = yellow
            if ni and rev:
                try:
                    margin = float(ni) / float(rev) * 100
                    if margin < 0: red_count += 1
                    elif margin < 3: yellow_count += 1
                except Exception: pass
            # ROA < 2% = yellow
            if ni and assets:
                try:
                    roa = float(ni) / float(assets) * 100
                    if roa < 0: red_count += 1
                    elif roa < 2: yellow_count += 1
                except Exception: pass
        covenant_score = min(20, red_count * 7 + yellow_count * 3)
    breakdown["covenant_stress"] = {"score": covenant_score, "max": 20}

    # ── 3. DEAL TRIGGERS (24 pts) ─────────────────────────────────────────
    # Use news analysis as a fast proxy (no LLM call)
    trigger_score = 0
    news_analysis = gd.get("news_analysis") or {}
    material_news = gd.get("news", [])
    material_count = sum(1 for n in material_news if n.get("is_material") or n.get("severity") == "high")
    key_concerns   = len(news_analysis.get("key_concerns") or [])
    risk_level     = news_analysis.get("risk_level","")
    if risk_level == "high":       trigger_score += 12
    elif risk_level == "medium":   trigger_score += 6
    trigger_score += min(8, material_count * 2)
    trigger_score += min(4, key_concerns)
    # Contact gap boost — if RM hasn't called in 90+ days, elevate signal
    recency = temporal.contact_urgency_boost(activities)
    if recency["boost_factor"] >= 2.0:
        trigger_score = min(24, int(trigger_score * 1.3))
    elif recency["boost_factor"] >= 1.5:
        trigger_score = min(24, int(trigger_score * 1.15))
    trigger_score = min(24, trigger_score)
    breakdown["deal_triggers"] = {"score": trigger_score, "max": 24}

    # ── 4. RELATIONSHIP WARMTH (16 pts) ───────────────────────────────────
    rel_score = 0
    if officers:
        try:
            connections = find_relationship_connections(officers, kg=kg_instance)
            board_conns = connections.get("board_connections", [])
            alumni_conns = connections.get("alumni_connections", [])
            # Fresh connections worth more
            for conn in board_conns + alumni_conns:
                freshness = temporal.score_officer_freshness(
                    {k: v for k, v in conn.items() if k == "researched_at"}
                )
                if freshness["label"] in ("fresh", "recent"):
                    rel_score += 4
                elif freshness["label"] == "aged":
                    rel_score += 2
                else:  # stale
                    rel_score += 1
            rel_score = min(16, rel_score)
        except Exception:
            rel_score = 0
    breakdown["relationship_warmth"] = {"score": rel_score, "max": 16}

    # ── 5. CONTACT GAP (15 pts) ───────────────────────────────────────────
    days = recency.get("days_since_contact")
    if days is None:
        contact_score = 15   # No contact = maximum urgency
    elif days > 180:
        contact_score = 15
    elif days > 90:
        contact_score = 11
    elif days > 60:
        contact_score = 7
    elif days > 30:
        contact_score = 3
    else:
        contact_score = 0
    breakdown["contact_gap"] = {
        "score": contact_score,
        "max": 15,
        "days_since_contact": days,
    }

    total = timing_score + covenant_score + trigger_score + rel_score + contact_score

    if total >= 80: grade = "A"
    elif total >= 60: grade = "B"
    elif total >= 40: grade = "C"
    elif total >= 20: grade = "D"
    else: grade = "F"

    return {
        "score": total,
        "grade": grade,
        "breakdown": breakdown,
        "contact_urgency": recency,
    }


@app.get("/company/{company_name}/pitch-score")
def get_pitch_score(company_name: str):
    """
    Return the deterministic Pitch Opportunity Score (0–100) for a company.
    No LLM call — reads stored Neo4j data only.
    Components: Timing (25), Covenant Stress (20), Deal Triggers (24),
    Relationship Warmth (16), Contact Gap (15).
    """
    global kg
    graph_data = kg.get_company_graph(company_name)
    if not graph_data:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")

    result = _compute_pitch_score(company_name, kg, graph_data)
    return {
        "company_name": company_name,
        **result,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/rm/portfolio")
def get_rm_portfolio():
    """
    Return all companies with summary stats, last contact date, deal count,
    and news risk level for the RM portfolio view.
    """
    global kg
    import json as _json

    companies = kg.get_portfolio_summary()
    enriched = []
    for c in companies:
        name = c["name"]
        # Get news risk from graph
        try:
            gd = kg.get_company_graph(name)
            na = gd.get("news_analysis") if gd else None
            risk = (na or {}).get("risk_level","unknown") if na else "unknown"
            # Latest financial period
            fins = gd.get("financials",[]) if gd else []
            latest_rev = None
            latest_period = ""
            if fins:
                f = fins[0]
                try:
                    inner = _json.loads(f.get("data_json","{}") or "{}")
                    inner2 = _json.loads(inner.get("data_json","{}") or "{}")
                    merged = {**inner2, **inner, **f}
                    latest_rev = merged.get("revenue")
                    latest_period = merged.get("filing_period") or merged.get("period","")
                except Exception:
                    latest_rev = f.get("revenue")
                    latest_period = f.get("period","")
        except Exception:
            risk = "unknown"
            latest_rev = None
            latest_period = ""
            gd = None
        c["news_risk"] = risk
        c["latest_revenue"] = latest_rev
        c["latest_period"] = latest_period
        # Pitch Opportunity Score — computed inline (no LLM, no extra N+1 graph fetch)
        try:
            pitch = _compute_pitch_score(name, kg, gd)
            c["pitch_score"] = pitch["score"]
            c["pitch_grade"] = pitch["grade"]
            c["pitch_breakdown"] = pitch["breakdown"]
        except Exception:
            c["pitch_score"] = 0
            c["pitch_grade"] = "—"
            c["pitch_breakdown"] = {}
        enriched.append(c)

    return {"companies": enriched, "total": len(enriched),
            "generated_at": datetime.utcnow().isoformat() + "Z"}


@app.get("/rm/industry-heatmap")
def get_industry_heatmap():
    """
    Aggregate companies by NAICS sector with sentiment, risk, and deal pipeline signals.
    """
    global kg
    companies = kg.get_portfolio_summary()
    sectors: dict = {}
    for c in companies:
        sector = c.get("naics_sector") or c.get("industry") or "Unknown"
        if not sector:
            sector = "Unknown"
        if sector not in sectors:
            sectors[sector] = {"sector": sector, "companies": [], "risk_counts": {"high":0,"medium":0,"low":0,"unknown":0}}
        sectors[sector]["companies"].append(c["name"])

    # Enrich with risk data
    for name, data in sectors.items():
        company_names = data["companies"]
        for cn in company_names:
            try:
                gd = kg.get_company_graph(cn)
                na = (gd or {}).get("news_analysis") or {}
                risk = na.get("risk_level","unknown") if na else "unknown"
                data["risk_counts"][risk if risk in data["risk_counts"] else "unknown"] += 1
            except Exception:
                data["risk_counts"]["unknown"] += 1
        data["company_count"] = len(company_names)
        total = sum(data["risk_counts"].values())
        data["risk_score"] = round((data["risk_counts"]["high"]*3 + data["risk_counts"]["medium"]) / max(total,1), 2)

    result = sorted(sectors.values(), key=lambda x: x["risk_score"], reverse=True)
    return {"sectors": result, "total_companies": len(companies),
            "generated_at": datetime.utcnow().isoformat() + "Z"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

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
        result = orchestrator.research_company(company_name, ticker, website)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

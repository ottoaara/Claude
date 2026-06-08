# Claude Project — Context Fabric

## Overview
AI-powered Commercial Banking Knowledge Graph for pre-meeting intelligence.  
Stack: FastAPI + LangGraph + Neo4j + Next.js + Claude Sonnet 4.6 (or Ollama local LLM).

## Project Rules
- Be concise
- Run tests before done

## Project Structure
```
Claude/
├── CLAUDE.md
├── README.md
├── PRD.md
├── requirements.txt
├── .env                              # Secrets — gitignored
├── docs/
│   ├── architecture.md               # System architecture (Mermaid)
│   └── agent_flow.md                 # LangGraph workflow (Mermaid)
├── src/
│   ├── banking_kg/                   # Backend
│   │   ├── api.py                    # FastAPI (26 endpoints)
│   │   ├── research_orchestrator.py  # LangGraph 9-node workflow
│   │   ├── neo4j_db.py               # Neo4j CRUD + graph queries
│   │   ├── llm_factory.py            # get_llm() — Anthropic or Ollama
│   │   ├── report_generator.py       # reportlab PDF export
│   │   ├── temporal.py               # Freshness scoring + decay curves
│   │   ├── bank_officers.py          # WF officer registry + relationship matching
│   │   └── agents/
│   │       ├── edgar_agent.py        # SEC EDGAR 10-K/10-Q (disk cache first)
│   │       ├── industry_agent.py     # NAICS + peer discovery (ReAct + DDG)
│   │       ├── officer_agent.py      # Executive profiling (DDG + scraping)
│   │       ├── news_agent.py         # DuckDuckGo news search
│   │       ├── news_classifier.py    # Batch LLM sentiment classification
│   │       ├── product_agent.py      # Product portfolio generation
│   │       └── web_scraper_agent.py  # Company website scraper
│   └── kg_frontend/                  # Next.js 16 frontend (port 3000)
│       ├── app/banking/page.tsx      # Main dashboard (8 tabs)
│       ├── app/rm/page.tsx           # RM Portfolio dashboard
│       ├── lib/api.ts                # API client
│       └── components/
│           ├── InsightsOverview.tsx  # Company snapshot
│           ├── FinancialMetrics.tsx  # Self-fetching financials
│           ├── PeerComparison.tsx    # SVG bar charts
│           ├── CovenantWatch.tsx     # Ratio monitoring
│           ├── TriggerAlerts.tsx     # Deal triggers
│           ├── OfficerResearch.tsx   # Officers + Board Interlock Map
│           ├── WFCommonality.tsx     # WF affinity signals
│           ├── ScoreTooltip.tsx      # Shared tooltip system
│           ├── Recommendations.tsx   # Pitch + products
│           ├── IncumbentBank.tsx     # Incumbent bank detection
│           ├── MeetingBrief.tsx      # Pre-meeting modal
│           └── ...
├── sec-edgar-filings/                # Cached SEC filing downloads (55+ tickers)
├── tests/
│   └── test_knowledge_graph.py
└── scripts/
    └── kg_query.py
```

## Setup
```bash
# Activate virtual environment
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables
```
ANTHROPIC_API_KEY=your_api_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
USER_EMAIL=your_email@example.com

# LLM Provider (default: anthropic; set to ollama to use local model)
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3:latest
```

## Running
```bash
# Backend (port 8000)
python -m uvicorn src.banking_kg.api:app --port 8000

# Frontend (port 3000)
cd src/kg_frontend && npm run dev
```

## Commands
- Run tests: `pytest tests/`
- Health check: `curl http://localhost:8000/health`


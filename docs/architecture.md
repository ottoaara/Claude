# Context Fabric — System Architecture

## Full Stack Architecture

```mermaid
graph TB
    subgraph Browser["Browser"]
        direction TB
        UI["Next.js 16 / React 19 / TailwindCSS"]
        subgraph Tabs["8-Tab Research Dashboard  (localhost:3000/banking)"]
            T1["① Executive Summary + Deal Trigger Alerts"]
            T2["② Financial Metrics + Covenant Watch"]
            T3["③ Industry Analysis + Peer Benchmarking"]
            T4["④ News & Sentiment Sparklines"]
            T5["⑤ Knowledge Graph (force-directed)"]
            T6["⑥ Officer Intelligence + Board Interlock Map"]
            T7["⑦ Pitch + Incumbent Bank + Entry Points"]
            T8["⑧ Activity Log + Deals History"]
        end
        RM["RM Portfolio Dashboard\n(localhost:3000/rm)\nSortable table + Industry Heat Map"]
        MB["Meeting Brief Modal\n(header button — always visible)"]
        UI --> Tabs
        UI --> RM
        UI --> MB
    end

    subgraph API["FastAPI Backend  (localhost:8000)"]
        direction TB
        EP["26 REST Endpoints"]
        AUTH["X-API-Key Auth header"]
        BG["Async Background Jobs\n(per-job orchestrator — supports concurrent demos)"]
        EP --> AUTH
        EP --> BG
    end

    subgraph Pipeline["LangGraph Research Pipeline"]
        WF["8-Node Sequential Workflow\nEmits progress events per step\nFrontend polls /research/status/{job_id}"]
    end

    subgraph Agents["Research Agents"]
        A1["WebScraperAgent\nBeautifulSoup + Claude profile extraction"]
        A2["EdgarAgent\nSEC 10-K/10-Q — disk cache first\nOllama: 12k char cap; Anthropic: 150k"]
        A3["NewsAgent + NewsClassifier\nDuckDuckGo + LLM batch sentiment (5/call)"]
        A4["ProductAgent\nClaude maps sector+size → banking products"]
        A5["IndustryAgent\nNAICS classification + peer discovery\nOllama: DDG+direct LLM (no ReAct)\nHard rule: peers must match NAICS sector"]
        A6["OfficerAgent\nDDG + proxy/LinkedIn scrape\nBuilds full profile per exec"]
        A7["TemporalDimension\nDecay curves + recency scoring\nHandles Q1 2026 / FY2024 / ISO dates"]
    end

    subgraph DataLayer["Data Layer — Neo4j (bolt://localhost:7687)"]
        C["Company node"]
        FIN["FinancialData nodes"]
        NEWS["NewsItem nodes"]
        PROD["Product nodes"]
        IND["Industry nodes (NAICS)"]
        OFF["Officer nodes\n(normalized names, profiled flag)"]
        PEER["Company nodes (peers)\ndeduped by ticker + normalized name"]
        ACT["Activity + Deal nodes"]
        C -->|HAS_FINANCIAL| FIN
        C -->|HAS_NEWS| NEWS
        C -->|OFFERS| PROD
        C -->|IN_INDUSTRY| IND
        C -->|HAS_OFFICER| OFF
        C -->|HAS_PEER / PEER_OF| PEER
        C -->|HAS_ACTIVITY / HAS_DEAL| ACT
    end

    subgraph LLMFactory["LLM Factory  (llm_factory.py)"]
        direction LR
        LLMF["get_llm(json_mode, temperature)\nrobust_parse_json() — handles Ollama quirks\n(empty responses, dict wrappers, trailing commas)"]
        LLMF -->|"LLM_PROVIDER=anthropic"| ANT["Anthropic API\nClaude Sonnet 4.6"]
        LLMF -->|"LLM_PROVIDER=ollama"| OLL["Ollama (local)\nllama3:latest"]
    end

    subgraph OnDemand["On-Demand API Features (per-request, no pipeline)"]
        OD1["Deal Trigger Alerts\nClaude classifies news + financials → urgency + product"]
        OD2["Covenant Watch\nD/EBITDA · interest coverage · ROA vs thresholds"]
        OD3["Incumbent Bank Detection\nDDG + SEC credit agreement search"]
        OD4["Meeting Brief\nClaude synthesises all dimensions → headline + questions + email"]
        OD5["Pitch Score\n5-dimension weighted score (NAICS, recency, officers, triggers, financials)"]
        OD6["Board Interlock + Alumni Network\nCross-ref officers vs 17 WF banker roster"]
        OD7["RM Portfolio + Industry Heatmap\nAggregated stats across all tracked companies"]
    end

    subgraph FileCache["Local File Cache"]
        SEC["sec-edgar-filings/\nTicker/10-K|10-Q/accession/\n55+ tickers cached"]
    end

    subgraph External["External Services"]
        EDGAR["SEC EDGAR API"]
        DDG["DuckDuckGo (ddgs)"]
        YF["yfinance"]
    end

    Browser -->|"HTTP fetch"| API
    API --> Pipeline
    Pipeline --> Agents
    Agents --> DataLayer
    Agents --> LLMFactory
    Agents --> External
    A2 -->|"cache hit"| SEC
    A2 -->|"cache miss"| EDGAR
    API --> OnDemand
    OnDemand --> DataLayer
    OnDemand --> LLMFactory
    OnDemand -->|"incumbent bank"| DDG

    style Browser fill:#e3f2fd,stroke:#1565c0
    style API fill:#fff3e0,stroke:#e65100
    style Pipeline fill:#f3e5f5,stroke:#6a1b9a
    style Agents fill:#e8f5e9,stroke:#2e7d32
    style DataLayer fill:#fce4ec,stroke:#880e4f
    style LLMFactory fill:#fff8e1,stroke:#f9a825
    style OnDemand fill:#e0f7fa,stroke:#006064
    style FileCache fill:#f5f5f5,stroke:#9e9e9e
    style External fill:#f5f5f5,stroke:#9e9e9e
```

## Neo4j Node Types

| Node Label | Key Properties |
|---|---|
| `Company` | name, ticker, website, sector, employees, description |
| `FinancialData` | filing_type, period, revenue, net_income, total_assets, cash, ebitda |
| `NewsItem` | title, date, sentiment, severity, is_material, event_types |
| `Product` | name, category, description |
| `Industry` | naics_code, naics_sector, sector_name, subsector |
| `Officer` | name, role, background_summary, risk_flags, board_memberships, profiled |
| `Company` (peer) | same as Company — deduped by ticker then normalized name |
| `Activity` | type, date, notes, contact_name |
| `Deal` | product, category, amount, status, date |

## Environment Variables

```
ANTHROPIC_API_KEY=     # used when LLM_PROVIDER=anthropic
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
USER_EMAIL=            # SEC EDGAR courtesy header
LLM_PROVIDER=ollama    # or: anthropic
OLLAMA_MODEL=llama3:latest
```

            T1["1 Executive Summary\n+ Deal Trigger Alerts"]
            T2["2 Financial Metrics\n+ Covenant Watch"]
            T3["3 Industry Analysis\nPeer Benchmarking"]
            T4["4 News & Sentiment\nSparklines"]
            T5["5 Knowledge Graph\nForce-directed viz"]
            T6["6 Officer Intelligence\nBoard Interlock + Alumni"]
            T7["7 Pitch\nIncumbent Bank + Entry Points"]
            T8["8 Activity\nLog + Deals History"]
        end
        RM["RM Portfolio Dashboard\n(localhost:3000/rm)\nSortable table + Industry Heat Map"]
        MB["Meeting Brief Modal\nHeader button — always visible"]
        UI --> Tabs
        UI --> RM
        UI --> MB
    end

    subgraph API["FastAPI Backend  (localhost:8000)"]
        direction TB
        EP["REST Endpoints (26 total)"]
        AUTH["X-API-Key Auth"]
        BG["Async Background Jobs\n(research pipeline)"]
        EP --> AUTH
        EP --> BG
    end

    subgraph Pipeline["LangGraph Research Pipeline"]
        WF["9-Node Sequential Workflow\nEmits progress events every step"]
    end

    subgraph Agents["Research Agents"]
        A1["WebScraperAgent\nCompany website"]
        A2["EdgarAgent\nSEC 10-K / 10-Q\n(disk cache first)"]
        A3["NewsAgent + Classifier\nDDG + LLM sentiment"]
        A4["ProductAgent\nPortfolio generation"]
        A5["IndustryAgent\nNAICS + peer discovery"]
        A6["OfficerAgent\nExec profiling"]
        A7["TemporalDimension\nDecay curves + pruning"]
    end

    subgraph LLMFactory["LLM Factory (llm_factory.py)"]
        direction LR
        LLMF["get_llm(json_mode=True/False)"]
        LLMF -->|"LLM_PROVIDER=anthropic"| ANT
        LLMF -->|"LLM_PROVIDER=ollama"| OLL
    end

    subgraph OnDemand["On-Demand AI Features"]
        OD1["Deal Trigger Alerts\nClaude classifies news + financials"]
        OD2["Covenant Watch\nD/EBITDA, coverage, ROA vs thresholds"]
        OD3["Incumbent Bank Detection\nDDG + SEC credit agreement search"]
        OD4["Meeting Brief\nClaude synthesis across all dimensions"]
        OD5["Relationship Intelligence\nBoard Interlock + Alumni Network"]
        OD6["Portfolio + Heatmap\nAggregated RM stats by company/sector"]
    end

    subgraph Storage["Data Layer"]
        NEO["Neo4j Graph DB\nbolt://localhost:7687\n9 node types"]
        CACHE["Local File Cache\nsec-edgar-filings/"]
    end

    subgraph External["External Services"]
        ANT["Anthropic API\nClaude Sonnet 4.6"]
        OLL["Ollama (local)\nllama3:latest"]
        EDGAR["SEC EDGAR"]
        DDG["DuckDuckGo (ddgs)"]
        YF["yfinance"]
    end

    Browser -->|"HTTP fetch"| API
    API --> Pipeline
    Pipeline --> Agents
    API --> OnDemand
    OnDemand --> LLMFactory
    Agents --> LLMFactory
    OLL --> A1
    ANT --> A1
    OLL --> A3
    ANT --> A3
    OLL --> A4
    ANT --> A4
    OLL --> A5
    ANT --> A5
    OLL --> A6
    ANT --> A6
    A2 --> CACHE
    EDGAR --> A2
    DDG --> A3
    DDG --> A6
    OnDemand --> DDG
    OnDemand --> Storage
    Agents --> Storage
    YF --> API
    Storage --> API

    style Browser fill:#fff3f3,stroke:#D71E28,stroke-width:2px
    style API fill:#fff8e1,stroke:#C8A951,stroke-width:2px
    style Pipeline fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style Agents fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style LLMFactory fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style OnDemand fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style Storage fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style External fill:#e0f7fa,stroke:#006064,stroke-width:2px
```

## Component Breakdown

| Layer | Technology | Purpose |
|-------|-----------|----------|
| Frontend | Next.js 16, React 19, TypeScript, TailwindCSS | 8-tab research dashboard + /rm portfolio page |
| API | FastAPI, Python 3.10+, uvicorn | 26 REST endpoints, async job management, PDF streaming |
| Orchestration | LangGraph + LangChain | Sequential 9-node research pipeline |
| LLM | Claude Sonnet 4.6 (Anthropic) or Ollama llama3 | Research synthesis, triggers, covenants, meeting brief, officer profiling — switchable via `LLM_PROVIDER` env |
| Graph DB | Neo4j 4.x (Docker) | Knowledge graph — 9 node types, activity + deal tracking |
| PDF | reportlab 4.x | A4 branded intelligence brief |
| SEC Data | sec-edgar-downloader | 10-K / 10-Q filing downloads — disk-cached 55+ tickers |
| Search | ddgs (DuckDuckGo) | News, officer discovery, incumbent bank detection |
| Stock Data | yfinance | Price sparklines around news event dates |

## Neo4j Graph Schema

```mermaid
graph LR
    C(["Company"])
    F(["Financial"])
    N(["News"])
    P(["Product"])
    I(["Industry"])
    PC(["PeerCompany"])
    O(["Officer"])
    AC(["Activity"])
    D(["Deal"])

    C -->|HAS_FILING| F
    C -->|MENTIONED_IN| N
    C -->|OFFERS| P
    C -->|BELONGS_TO| I
    C -->|HAS_PEER| PC
    C -->|HAS_OFFICER| O
    C -->|PEER_OF| C
    C -->|HAS_ACTIVITY| AC
    C -->|HAS_DEAL| D

    style C fill:#D71E28,color:#fff
    style F fill:#1565c0,color:#fff
    style N fill:#e65100,color:#fff
    style P fill:#2e7d32,color:#fff
    style I fill:#6a1b9a,color:#fff
    style PC fill:#00838f,color:#fff
    style O fill:#4e342e,color:#fff
    style AC fill:#1a5276,color:#fff
    style D fill:#784212,color:#fff
```

**Relationship Intelligence cross-reference:**
`(:Company {name:"Wells Fargo"})-[:HAS_OFFICER]->(:Officer)` is cross-referenced against every researched company's officers to surface board interlocks and alumni ties.

## API Endpoints Reference

```
POST /research/start                     Start async research job
GET  /research/status/{job_id}           Poll progress
GET  /research/jobs                      List all jobs

GET  /companies                          All companies in graph
GET  /company/{name}/graph               Full graph data (all dimensions)
GET  /company/{name}/visualization       Force-graph visualization data
GET  /company/{name}/freshness           Temporal freshness scores
GET  /company/{name}/peer-comparison     Target + peer EDGAR financials
GET  /company/{name}/officers            Stored officer profiles
GET  /company/{name}/triggers            Deal trigger analysis (Claude)
GET  /company/{name}/covenant-watch      Financial ratio monitoring
GET  /company/{name}/incumbent-bank      Incumbent bank detection
GET  /company/{name}/meeting-brief       Pre-meeting synthesis brief
GET  /company/{name}/activity            RM activity log
POST /company/{name}/activity            Log call / email / meeting
DELETE /activity/{activity_id}           Remove activity entry
GET  /company/{name}/deals               Prior WF products / deals
POST /company/{name}/deals               Add deal record
DELETE /deal/{deal_id}                   Remove deal record
GET  /company/{name}/relationship-map    Board interlock + alumni connections
GET  /rm/portfolio                       All companies with RM stats
GET  /rm/industry-heatmap                Sector risk scores
GET  /company/{name}/report              JSON intelligence report  [API key]
GET  /company/{name}/report/pdf          PDF intelligence brief    [API key]

POST /officer/search                     Research a named individual
GET  /stock/{ticker}/around-dates        Stock prices around event dates

DELETE /company/{name}                   Clear company from graph
GET  /health                             System health check
```

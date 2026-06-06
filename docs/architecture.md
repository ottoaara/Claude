# Context Fabric — System Architecture

## Full Stack Architecture

```mermaid
graph TB
    subgraph Browser["Browser (localhost:3000)"]
        UI["Next.js 16 / React 19<br/>TailwindCSS"]
        subgraph Tabs["7 Dashboard Tabs"]
            T1["Executive Summary"]
            T2["Financial Metrics"]
            T3["Industry Analysis"]
            T4["News & Sentiment"]
            T5["Data Freshness"]
            T6["Knowledge Graph"]
            T7["Officer Intelligence"]
        end
        UI --> Tabs
    end

    subgraph API["FastAPI Backend (localhost:8000)"]
        direction TB
        EP["REST Endpoints"]
        AUTH["X-API-Key Auth<br/>(optional)"]
        BG["Background Tasks<br/>(research jobs)"]
        EP --> AUTH
        EP --> BG
    end

    subgraph Orchestration["LangGraph Orchestrator"]
        WF["9-Node Sequential Workflow"]
    end

    subgraph Agents["Research Agents"]
        A1["WebScraperAgent<br/>Company website"]
        A2["EdgarAgent<br/>SEC 10-K / 10-Q"]
        A3["NewsAgent<br/>DuckDuckGo search"]
        A4["NewsClassifier<br/>Batch sentiment + severity"]
        A5["ProductAgent<br/>Portfolio generation"]
        A6["IndustryAgent<br/>NAICS + peer discovery"]
        A7["OfficerAgent<br/>Executive profiling"]
    end

    subgraph Storage["Data Layer"]
        NEO["Neo4j Graph DB<br/>bolt://localhost:7687"]
        CACHE["Local File Cache<br/>sec-edgar-filings/"]
    end

    subgraph Output["Output Layer"]
        RPT["ReportGenerator<br/>(reportlab A4 PDF)"]
        VIZ["Graph Visualization<br/>(react-force-graph-2d)"]
    end

    subgraph External["External Services"]
        ANT["Anthropic API<br/>Claude Sonnet 4.6"]
        EDGAR["SEC EDGAR<br/>sec-edgar-downloader"]
        DDG["DuckDuckGo<br/>ddgs"]
        YF["Yahoo Finance<br/>yfinance"]
    end

    Browser -->|"HTTP / fetch"| API
    API --> Orchestration
    Orchestration --> Agents
    A2 -->|"download + parse"| CACHE
    EDGAR --> A2
    DDG --> A3
    DDG --> A7
    ANT -->|"LLM calls"| A1
    ANT -->|"LLM calls"| A3
    ANT -->|"LLM calls"| A4
    ANT -->|"LLM calls"| A5
    ANT -->|"LLM calls"| A6
    ANT -->|"LLM calls"| A7
    Agents --> Storage
    YF -->|"stock prices"| API
    API --> RPT
    RPT -->|"PDF bytes"| Browser
    API -->|"graph data"| VIZ
    Storage --> API

    style Browser fill:#fff3f3,stroke:#D71E28,stroke-width:2px
    style API fill:#fff8e1,stroke:#C8A951,stroke-width:2px
    style Orchestration fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style Agents fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style Storage fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style External fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style Output fill:#e0f7fa,stroke:#006064,stroke-width:2px
```

## Component Breakdown

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16, React 19, TypeScript, TailwindCSS | Interactive dashboard, 7-tab UI |
| API | FastAPI, Python 3.10+, uvicorn | REST endpoints, job management, PDF streaming |
| Orchestration | LangGraph + LangChain | Sequential 9-node research workflow |
| LLM | Claude Sonnet 4.6 (Anthropic) | Company analysis, news classification, officer profiling |
| Graph DB | Neo4j 4.x (Docker) | Knowledge graph storage + Cypher queries |
| PDF | reportlab 4.x | A4 intelligence brief generation |
| SEC Data | sec-edgar-downloader | 10-K / 10-Q filing downloads |
| Search | ddgs (DuckDuckGo) | News search, officer background research |
| Stock Data | yfinance | Price sparklines around news event dates |

## Neo4j Graph Schema

```mermaid
graph LR
    C(["Company"])
    F(["Financial<br/>HAS_FILING"])
    N(["News<br/>MENTIONED_IN"])
    P(["Product<br/>OFFERS"])
    I(["Industry<br/>BELONGS_TO"])
    PC(["PeerCompany<br/>HAS_PEER"])
    O(["Officer<br/>HAS_OFFICER"])

    C -->|HAS_FILING| F
    C -->|MENTIONED_IN| N
    C -->|OFFERS| P
    C -->|BELONGS_TO| I
    C -->|HAS_PEER| PC
    C -->|HAS_OFFICER| O
    C -->|PEER_OF| C

    style C fill:#D71E28,color:#fff
    style F fill:#1565c0,color:#fff
    style N fill:#e65100,color:#fff
    style P fill:#2e7d32,color:#fff
    style I fill:#6a1b9a,color:#fff
    style PC fill:#00838f,color:#fff
    style O fill:#4e342e,color:#fff
```

## API Endpoints Reference

```
POST /research/start                     Start company research job
GET  /research/status/{job_id}           Poll research progress
GET  /research/jobs                      List all jobs

GET  /companies                          List all companies in graph
GET  /company/{name}/graph               Full graph data (all dimensions)
GET  /company/{name}/visualization       Force-graph visualization data
GET  /company/{name}/freshness           Temporal freshness scores
GET  /company/{name}/peer-comparison     Target + peer EDGAR financials
GET  /company/{name}/officers            Stored officer profiles
GET  /company/{name}/report             ★ JSON intelligence report  [API key]
GET  /company/{name}/report/pdf         ★ PDF intelligence brief    [API key]

POST /officer/search                     Research a named individual
GET  /stock/{ticker}/around-dates        Stock prices around event dates

DELETE /company/{name}                   Clear company from graph
GET  /health                             System health check
```

`★` = protected by `X-API-Key` header when `BANKING_API_KEY` env var is set.

# Context Fabric — Agent Flow

## LangGraph Research Pipeline

The orchestrator runs a **9-node sequential LangGraph workflow**. Each node is a method on `BankingResearchOrchestrator`. Nodes emit progress events; the frontend polls `/research/status/{job_id}` every 2 seconds.

```mermaid
flowchart TD
    START(["research_company\nname · ticker · website"])

    subgraph PIPELINE["LangGraph Sequential Workflow  —  runs once per research job"]
        N1["1  scrape_company_info\nWebScraperAgent\nBeautifulSoup scrape + Claude profile extraction"]
        N2["2  fetch_financials\nEdgarAgent\nSEC EDGAR 10-K + 10-Q · ticker normalisation · XBRL parse"]
        N3["3  search_news\nNewsAgent + NewsClassifier\nDuckDuckGo queries · Claude batch classification (5/call)"]
        N4["4  generate_products\nProductAgent\nClaude maps sector + size to likely banking product portfolio"]
        N5["5  analyze_industry\nIndustryAgent\nNAICS via Claude · DuckDuckGo peer discovery with tickers"]
        N6["6  fetch_peer_financials\nEdgarAgent (per peer)\nSEC 10-K / 10-Q per peer · foreign ticker skip"]
        N7["7  fetch_officers\nOfficerAgent  —  always Claude Sonnet 4.6\nDDG discovery + 4 deep-profile searches per officer\nbackground · risk_flags · board_memberships · education"]
        N8["8  apply_temporal_scoring\nTemporalDimension\nDecay curves per dimension · prune below 0.3 · boost material events"]
        N9["9  populate_graph\nNeo4j  +  Claude Sonnet 4.6\nMERGE all nodes + relationships · generate AI executive summary"]
    end

    DONE(["Result returned to API\ndimensions · summary · errors"])

    START --> N1 --> N2 --> N3 --> N4 --> N5 --> N6 --> N7 --> N8 --> N9 --> DONE

    style START fill:#D71E28,color:#fff,stroke:#D71E28
    style DONE  fill:#2e7d32,color:#fff,stroke:#2e7d32
    style PIPELINE fill:#f9f9f9,stroke:#cccccc
    style N1 fill:#e3f2fd,stroke:#1565c0
    style N2 fill:#e3f2fd,stroke:#1565c0
    style N3 fill:#fff3e0,stroke:#e65100
    style N4 fill:#e8f5e9,stroke:#2e7d32
    style N5 fill:#f3e5f5,stroke:#6a1b9a
    style N6 fill:#e3f2fd,stroke:#1565c0
    style N7 fill:#fce4ec,stroke:#880e4f
    style N8 fill:#fff8e1,stroke:#f9a825
    style N9 fill:#e0f2f1,stroke:#00695c
```

## On-Demand AI Features

These run independently of the research pipeline — called per-request from the dashboard or API.

```mermaid
flowchart LR
    NEO[("Neo4j")]
    ANT["Claude Sonnet 4.6"]
    DDG["DuckDuckGo"]
    EDGAR["SEC EDGAR"]

    subgraph RM["RM Workflow Features  —  on-demand endpoints"]
        F1["Deal Trigger Alerts\nGET /company/name/triggers\nClaude reads news + financials\nOutputs: type · urgency · product · action"]
        F2["Covenant Watch\nGET /company/name/covenant-watch\nComputes D/EBITDA · interest coverage\nnet margin · ROA vs thresholds"]
        F3["Incumbent Bank Detection\nGET /company/name/incumbent-bank\nDDG + SEC credit agreement search\nOutputs: primary bank · lenders · facility · opportunity"]
        F4["Meeting Brief\nGET /company/name/meeting-brief\nClaude synthesises all dimensions\nheadline · 3+3 · questions · entry points · email"]
        F5["Relationship Intelligence\nGET /company/name/relationship-map\nCross-ref company officers vs 17 WF officers\nBoard Interlock Map + Alumni Network"]
        F6["Activity Log\nGET POST /company/name/activity\nPersist calls · emails · meetings · notes\nLast contact age tracking"]
        F7["Deals History\nGET POST /company/name/deals\nTrack WF products by category · status · amount"]
        F8["Portfolio + Heatmap\nGET /rm/portfolio\nGET /rm/industry-heatmap\nAggregated stats · sector risk scores"]
    end

    NEO --> F1
    NEO --> F2
    NEO --> F5
    NEO --> F6
    NEO --> F7
    NEO --> F8
    ANT --> F1
    ANT --> F4
    DDG --> F3
    EDGAR --> F3

    style RM fill:#fff3f3,stroke:#D71E28
    style F1 fill:#fce4ec,stroke:#880e4f
    style F2 fill:#e3f2fd,stroke:#1565c0
    style F3 fill:#fff8e1,stroke:#C8A951
    style F4 fill:#e8f5e9,stroke:#2e7d32
    style F5 fill:#f3e5f5,stroke:#6a1b9a
    style F6 fill:#e0f7fa,stroke:#006064
    style F7 fill:#e0f7fa,stroke:#006064
    style F8 fill:#fce4ec,stroke:#D71E28
```

## ResearchState — Data Flow

```mermaid
flowchart LR
    RS["ResearchState\nTypedDict"]

    RS --> company_info
    RS --> financial_data
    RS --> news_data
    RS --> product_data
    RS --> industry_data
    RS --> tickered_peers
    RS --> peer_financial_data
    RS --> officer_data
    RS --> temporal_scores
    RS --> temporal_summary
    RS --> graph_populated
    RS --> summary
    RS --> errors
    RS --> completed_steps

    company_info["company_info: Dict\nname · ticker · website · sector\nemployees · description · HQ"]
    financial_data["financial_data: List\nfiling_type · period · revenue\nnet_income · total_assets · cash"]
    news_data["news_data: Dict\nnews_items: List\ntitle · date · sentiment · severity\nis_material · event_types · source"]
    product_data["product_data: Dict\nproducts: List\nname · category · description"]
    industry_data["industry_data: Dict\nnaics_code · sector · trends\npeers: List · key_drivers"]
    tickered_peers["tickered_peers: List\nname · ticker"]
    peer_financial_data["peer_financial_data: List\npeer_name · ticker · metrics\nfiling_type · filing_period"]
    officer_data["officer_data: Dict\nofficers: List\nname · role · background_summary\nrisk_flags · banking_relevance\neducation · board_memberships · confidence"]
    temporal_scores["temporal_scores: Dict\nper-item relevance 0-1"]
    temporal_summary["temporal_summary: Dict\nfresh / recent / aged / stale counts"]
    graph_populated["graph_populated: bool"]
    summary["summary: Dict\nexecutive_summary · key_bullets"]
    errors["errors: List[str]"]
    completed_steps["completed_steps: List[str]\nprogress bar keys"]
```

## Temporal Decay Curves

```mermaid
flowchart LR
    TD["TemporalDimension"]
    TD --> D1["News\n90-day window\nfast decay"]
    TD --> D2["Quarterly Filings\n120-day window"]
    TD --> D3["Industry Trends\n180-day window"]
    TD --> D4["Annual Filings\n365-day window"]
    TD --> D5["Products\n730-day window\nslow decay"]
    TD --> B1["Boost\nHigh-severity news\n10-K filings"]
    TD --> P1["Prune\nrelevance < 0.3\nremoved from graph"]

    style TD fill:#fff8e1,stroke:#f9a825
    style B1 fill:#e8f5e9,stroke:#2e7d32
    style P1 fill:#fce4ec,stroke:#880e4f
```

## Individual Agent Details

### WebScraperAgent
```
Input:  company_name, website URL
Tools:  requests + BeautifulSoup (HTML scrape)
LLM:    Claude — structured company profile extraction
Output: { name, ticker, description, employees, headquarters, sector, founded }
```

### EdgarAgent
```
Input:  company_name, ticker
Tools:  sec-edgar-downloader -> local sec-edgar-filings/
        _normalise_ticker() alias map (e.g. "3M" -> "MMM")
        Foreign ticker skip (.KS, .HK, .L, .DE ...)
LLM:    none — regex/text extraction from filing text
Output: { revenue, net_income, total_assets, cash, filing_date, filing_type, period }
```

### NewsAgent + NewsClassifier
```
Input:  company_name
Tools:  DuckDuckGo (ddgs) — 2 queries: negative news + general news, 15 items cap
LLM:    Claude — classify in batches of 5
Output: { sentiment, severity, is_material, event_types, key_facts, summary }
```

### ProductAgent
```
Input:  company_name, company_info
LLM:    Claude — generate plausible banking product portfolio
Output: List[{ name, category, description, revenue_impact }]
```

### IndustryAgent
```
Input:  company_name, company_info
Tools:  DuckDuckGo — industry background search
LLM:    Claude — NAICS classification, peer discovery (with tickers), trend analysis
Output: { naics_code, sector, peers: [{name, ticker}], trends, key_drivers }
```

### OfficerAgent  (always Claude Sonnet 4.6 — ignores LLM_PROVIDER env)
```
Input:  company_name
Tools:  DuckDuckGo — 1 discovery query + 4 deep-profile queries per officer
LLM:    Claude Sonnet 4.6 — extract officer list; build deep profile per person
Output: { officers: [{ name, role, background_summary, education, previous_roles,
           tenure_years, linkedin_url, key_achievements, recent_news,
           publications_speaking, board_memberships, risk_flags,
           banking_relevance, confidence }] }
```

### TemporalDimension
```
Input:  All dimension data from ResearchState
Logic:  Dimension-specific decay curves (see diagram above)
        Boost: high-severity news, 10-K filings
        Prune: items with relevance_score < 0.3
Output: { relevance_scores, temporal_summary: { fresh, recent, aged, stale } }
```


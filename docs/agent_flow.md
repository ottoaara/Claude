# Context Fabric — Agent Flow

## LangGraph Research Workflow

The orchestrator runs a **9-node sequential LangGraph workflow**. Each node is a method on `BankingResearchOrchestrator`. Nodes emit progress events; the frontend polls `/research/status/{job_id}` every 2 seconds to update the progress bar.

```mermaid
flowchart TD
    START(["▶ research_company(name, ticker, website)"])

    subgraph WF["LangGraph Sequential Workflow"]
        N1["1 · scrape_company_info\nWebScraperAgent\n• BeautifulSoup website scrape\n• Claude extracts structured profile\n• company_info → ResearchState"]

        N2["2 · fetch_financials\nEdgarAgent\n• _normalise_ticker() alias map\n• sec-edgar-downloader 10-K + 10-Q\n• Parse XBRL / text for key metrics\n• financial_data → ResearchState"]

        N3["3 · search_news\nNewsAgent + NewsClassifier\n• DuckDuckGo: negative + general queries\n• Claude classifies in chunks of 5\n• sentiment / severity / is_material / event_types\n• news_data → ResearchState"]

        N4["4 · generate_products\nProductAgent\n• Claude generates likely product portfolio\n• Based on sector + company size\n• product_data → ResearchState"]

        N5["5 · analyze_industry\nIndustryAgent\n• NAICS classification via Claude\n• DuckDuckGo peer discovery\n• Peers with tickers → tickered_peers\n• industry_data → ResearchState"]

        N6["6 · fetch_peer_financials\nEdgarAgent (per peer)\n• _normalise_ticker() + foreign skip\n• 10-K / 10-Q for each peer\n• peer_financial_data → ResearchState"]

        N7["7 · fetch_officers\nOfficerAgent\n• DuckDuckGo: find company officers\n• Claude extracts name / role / board\n• 4 deep-profile searches per officer\n• background / risk_flags / banking_relevance\n• officer_data → ResearchState"]

        N8["8 · apply_temporal_scoring\nTemporalDimension\n• Decay curves per dimension\n  News: 90d, Quarterly: 120d\n  Industry: 180d, Annual: 365d\n• Relevance scores 0–1\n• Prune items below 0.3\n• temporal_summary → ResearchState"]

        N9["9 · populate_graph\nBankingKnowledgeGraph (Neo4j)\n• MERGE Company node\n• Store Financial, News, Product, Industry\n• Store PeerCompany + HAS_PEER\n• Store Officer + HAS_OFFICER\n• graph_populated = True"]

        N10["10 · generate_summary\nClaude Sonnet 4.6\n• Full research context prompt\n• AI executive summary + key bullets\n• Stored on Company node\n• summary → ResearchState"]
    end

    DONE(["✅ Result returned to API\n{ dimensions, summary, errors }"])

    START --> N1
    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
    N5 --> N6
    N6 --> N7
    N7 --> N8
    N8 --> N9
    N9 --> N10
    N10 --> DONE

    style START fill:#D71E28,color:#fff,stroke:#D71E28
    style DONE  fill:#2e7d32,color:#fff,stroke:#2e7d32
    style N1 fill:#e3f2fd,stroke:#1565c0
    style N2 fill:#e3f2fd,stroke:#1565c0
    style N3 fill:#fff3e0,stroke:#e65100
    style N4 fill:#e8f5e9,stroke:#2e7d32
    style N5 fill:#f3e5f5,stroke:#6a1b9a
    style N6 fill:#e3f2fd,stroke:#1565c0
    style N7 fill:#fce4ec,stroke:#880e4f
    style N8 fill:#fff8e1,stroke:#f9a825
    style N9 fill:#e0f2f1,stroke:#00695c
    style N10 fill:#fff3f3,stroke:#D71E28
```

## ResearchState — Data Flow

```mermaid
flowchart LR
    RS["ResearchState\n(TypedDict)"]

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

    company_info["company_info: Dict\nname, ticker, website, sector\nemployees, description, HQ"]
    financial_data["financial_data: List[Dict]\nfiling_type, period, revenue\nnet_income, total_assets, cash"]
    news_data["news_data: Dict\n{ news_items: List[Dict] }\ntitle, date, sentiment, severity\nis_material, event_types, source"]
    product_data["product_data: Dict\n{ products: List[Dict] }\nname, category, description"]
    industry_data["industry_data: Dict\nnaics_code, sector, trends\npeers: List, key_drivers"]
    tickered_peers["tickered_peers: List[Dict]\n{ name, ticker }"]
    peer_financial_data["peer_financial_data: List[Dict]\npeer_name, ticker, metrics\nfiling_type, filing_period"]
    officer_data["officer_data: Dict\n{ officers: List[Dict] }\nname, role, background_summary\nrisk_flags, banking_relevance"]
    temporal_scores["temporal_scores: Dict\nper-item relevance 0–1"]
    temporal_summary["temporal_summary: Dict\nfresh/recent/aged/stale counts"]
    graph_populated["graph_populated: bool"]
    summary["summary: Dict\nexecutive_summary, key_bullets"]
    errors["errors: List[str]"]
    completed_steps["completed_steps: List[str]\nprogress bar keys"]
```

## Individual Agent Details

### WebScraperAgent
```
Input:  company_name, website URL
Tools:  requests + BeautifulSoup (HTML scrape)
LLM:    Claude — structured company profile extraction
Output: { name, ticker, description, employees, headquarters, sector, founded, ... }
```

### EdgarAgent
```
Input:  company_name, ticker
Tools:  sec-edgar-downloader → local sec-edgar-filings/
        _normalise_ticker() alias map (e.g. "3M" → "MMM")
        Foreign ticker skip (.KS, .HK, .L, .DE, ...)
LLM:    (none — regex/text extraction from filing text)
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

### OfficerAgent
```
Input:  company_name
Tools:  DuckDuckGo — 1 discovery query + 4 deep-profile queries per officer
LLM:    Claude — extract officer list; build deep profile per person
Output: { officers: [{ name, role, background_summary, education, previous_roles,
           tenure_years, linkedin_url, key_achievements, recent_news,
           publications_speaking, board_memberships, risk_flags,
           banking_relevance, confidence }] }
```

### TemporalDimension
```
Input:  All dimension data from ResearchState
Logic:  Dimension-specific decay curves:
          News:               90-day window  (fast decay)
          Quarterly Finance: 120-day window
          Industry Trends:   180-day window
          Annual Finance:    365-day window
          Products:          730-day window
        Boost: high-severity news, 10-K filings
        Prune: items with relevance_score < 0.3
Output: { relevance_scores, temporal_summary: { fresh, recent, aged, stale } }
```

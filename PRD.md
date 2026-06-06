# Product Requirements Document: Context Fabric

## 1. Product Overview

### Product Name
**Context Fabric** — Commercial Banking Knowledge Graph

### Vision Statement
An AI-powered knowledge graph system that gives commercial relationship managers timely, comprehensive, and actionable intelligence on their clients by automatically researching companies across 7 dimensions and presenting interconnected insights through an interactive dashboard with PDF export and a callable service API.

### Product Type
Enterprise intelligence platform for commercial banking relationship management

---

## 2. Problem Statement

Commercial relationship managers need comprehensive, up-to-date intelligence before every client meeting. Manual research is:

- **Time-consuming** — 30–60 min per meeting across multiple data sources
- **Fragmented** — SEC filings, news, LinkedIn, company sites all in silos
- **Stale** — no automatic freshness tracking; outdated insights reach the meeting room
- **Shallow** — raw data without synthesized recommendations or officer profiles
- **Not callable** — no API for downstream CRM or workflow integration

**Result**: under-prepared meetings, missed cross-sell opportunities, compliance gaps.

---

## 3. Target Users

### Primary: Commercial Relationship Manager (CRM)
- Manages commercial banking relationships ($10M–$500M revenue clients)
- Needs meeting prep in <5 minutes
- Pain: information overload, disconnected sources, no actionable summary

### Secondary
- **Credit Analysts** — risk monitoring, financial trend review
- **Compliance Officers** — policy/regulatory exposure flags
- **Product Specialists** — cross-sell opportunity identification
- **System Integrators** — service API consumers (CRM, workflow tools)

---

## 4. Intelligence Dimensions

### Dimension 1: Company Profile (WebScraperAgent)
- Source: Company website + BeautifulSoup
- Extracts: description, sector, employees, HQ, founded date, business model
- Claude converts scraped HTML to structured profile

### Dimension 2: Financial Data (EdgarAgent)
- Source: SEC EDGAR (10-K and 10-Q filings)
- Extracts: revenue, net income, operating income, total assets, cash, equity
- Ticker normalisation: alias map (3M→MMM) + foreign ticker skip
- Files cached locally in `sec-edgar-filings/`

### Dimension 3: News & Sentiment (NewsAgent + NewsClassifier)
- Source: DuckDuckGo (ddgs) — negative + general queries
- Classifies in batches of 5 via Claude: sentiment, severity, is_material, event_types
- Stock price sparklines around event dates via yfinance

### Dimension 4: Product Portfolio (ProductAgent)
- Source: Claude AI-generated based on sector + size profile
- Maps likely banking product needs to client characteristics
- Future: replace with real transaction history

### Dimension 5: Industry & Peers (IndustryAgent)
- Source: NAICS classification via Claude + DuckDuckGo
- Outputs: naics_code, sector, peer companies with tickers, trends, key drivers
- Peer tickers feed into Dimension 6

### Dimension 6: Peer Financial Comparison (EdgarAgent per peer)
- Source: SEC EDGAR 10-K/10-Q for each peer company
- Renders as 6 SVG bar charts in the Industry Analysis tab
- Foreign / invalid tickers gracefully skipped

### Dimension 7: Officer Intelligence (OfficerAgent) ← NEW
- Source: DuckDuckGo web search (discovery + deep profiling)
- Per-officer profile: background, education, previous roles, tenure, LinkedIn
- Risk flags, banking relevance, key achievements, publications, board seats
- Confidence scoring (high / medium / low)
- Manual search: POST /officer/search for any named individual

### Applied to All: Temporal Dimension (TemporalDimension)
- Dimension-specific decay curves:
  - News: 90-day window
  - Quarterly filings: 120-day window
  - Industry trends: 180-day window
  - Annual filings: 365-day window
  - Products: 730-day window
- Prune items below relevance threshold (0.3)
- Boost: high-severity news, 10-K filings
- Freshness summary: fresh / recent / aged / stale counts per dimension

---

## 5. Feature Set (Current Implementation)

### 5.1 Research Orchestration
- LangGraph 9-node sequential workflow
- Background task execution (non-blocking API)
- Unique job IDs, status polling every 2 seconds
- Per-node progress bar in frontend
- Error isolation: one failed node does not block others

### 5.2 Interactive Dashboard — 7 Tabs
1. **Executive Summary** — AI-generated brief + freshness indicators + meeting checklist
2. **Financial Metrics** — Income statement, balance sheet, cash flow, period-over-period
3. **Industry Analysis** — NAICS sector, peer benchmarking, 6 SVG bar charts
4. **News & Sentiment** — Classified news, severity, stock sparklines
5. **Data Freshness** — Per-dimension temporal scores
6. **Knowledge Graph** — Force-directed visualization, clickable node detail panel
7. **Officer Intelligence** — Executive cards, risk flags, expandable profiles, manual search

### 5.3 PDF Export
- One-click **⬇ Export PDF** button in dashboard header
- A4 format via reportlab; Wells Fargo brand styling
- Sections: cover page, company overview, financial highlights, peer comparison,
  industry, news & risk signals, officer profiles, product portfolio
- Streamed as `application/pdf` from `GET /company/{name}/report/pdf`

### 5.4 Service API
- `GET /company/{name}/report` — complete JSON intelligence package
- `GET /company/{name}/report/pdf` — PDF binary
- `X-API-Key` header auth (controlled by `BANKING_API_KEY` env var)
- `BANKING_CORS_ORIGINS` env var for cross-origin production deployments
- Full OpenAPI/Swagger docs at `/docs`

### 5.5 Knowledge Graph Storage (Neo4j)
Node types: `Company`, `Financial`, `News`, `Product`, `Industry`, `PeerCompany`, `Officer`

Relationships:
```
(:Company)-[:HAS_FILING]->(:Financial)
(:Company)-[:MENTIONED_IN]->(:News)
(:Company)-[:OFFERS]->(:Product)
(:Company)-[:BELONGS_TO]->(:Industry)
(:Company)-[:HAS_PEER]->(:PeerCompany)
(:Company)-[:HAS_OFFICER]->(:Officer)
(:Company)-[:PEER_OF]-(:Company)
```

---

## 6. Technical Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, TailwindCSS |
| Backend | FastAPI, Python 3.10+, uvicorn |
| AI Orchestration | LangGraph + LangChain |
| LLM | Claude Sonnet 4.6 (Anthropic API) |
| Graph DB | Neo4j 4.x (Docker) |
| PDF | reportlab 4.x |
| Web Search | ddgs (DuckDuckGo) |
| SEC Data | sec-edgar-downloader |
| Stock Data | yfinance |
| Graph Viz | react-force-graph-2d |

### Diagrams
- **System architecture**: [docs/architecture.md](docs/architecture.md)
- **Agent workflow**: [docs/agent_flow.md](docs/agent_flow.md)

### API Endpoints

```
POST /research/start                     Start async research job
GET  /research/status/{job_id}           Poll progress
GET  /research/jobs                      List all jobs

GET  /companies                          All companies in graph
GET  /company/{name}/graph               Full graph data
GET  /company/{name}/visualization       Force-graph data
GET  /company/{name}/freshness           Temporal freshness scores
GET  /company/{name}/peer-comparison     EDGAR peer financials
GET  /company/{name}/officers            Stored officer profiles
GET  /company/{name}/report             ★ JSON report (API key)
GET  /company/{name}/report/pdf         ★ PDF brief   (API key)

POST /officer/search                     Manual officer research
GET  /stock/{ticker}/around-dates        Price context for news dates

DELETE /company/{name}                   Clear company data
GET  /health                             Health check
```

---

## 7. User Workflows

### 7.1 Pre-Meeting Preparation
1. Open http://localhost:3000/banking
2. Enter company name + ticker + website
3. Click **Start AI Research** — monitor 9-step progress bar
4. Review 7-tab dashboard (60–120 second total)
5. Click **⬇ Export PDF** — download formatted brief
6. Use brief for meeting talking points

### 7.2 Service Integration
1. `POST /research/start` with company details
2. Poll `GET /research/status/{job_id}` until `status == "completed"`
3. Call `GET /company/{name}/report` for structured JSON
4. Or `GET /company/{name}/report/pdf` for formatted PDF

### 7.3 Officer Intelligence
- Automatic: officers profiled during research workflow
- Manual: `POST /officer/search` for any contact — name + company + role
- UI: Officer Intelligence tab shows cards with risk flags, LinkedIn, re-search button

---

## 8. Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| End-to-end research time | < 120 s | 60–150 s |
| API P95 latency | < 500 ms | < 300 ms (non-research) |
| Graph visualization render | < 2 s | ~1 s |
| PDF generation | < 5 s | ~2 s |
| Data freshness (avg age) | < 60 days | Varies by company |

---

## 9. Constraints & Known Limitations

- **Public companies only** for financial data — requires SEC EDGAR ticker
- **DuckDuckGo rate limits** (~10 req/min) — news + officer search may throttle
- **Officer confidence** — web search quality varies; always show confidence badge
- **Sequential LangGraph** — nodes run in order; no parallelism within a workflow
- **Local Neo4j** — single node; production needs Neo4j Aura or cluster
- **No auth on dashboard** — API key only protects report endpoints; add SSO for production

---

## 10. Completed Features ✅

- [x] 7-dimension automated research (added Peer Financials + Officer Intelligence)
- [x] Neo4j knowledge graph with all 7 node types
- [x] LangGraph 9-node sequential orchestration
- [x] Temporal freshness scoring + decay curves + pruning
- [x] FastAPI backend with full RESTful API
- [x] Next.js 16 interactive dashboard — 7 tabs
- [x] PDF export (reportlab A4 brief)
- [x] Service API with X-API-Key auth
- [x] Peer financial comparison (6 SVG bar charts)
- [x] Officer Intelligence tab (auto + manual search)
- [x] Knowledge graph force visualization with node detail panel
- [x] News sentiment classification (batch, 5 items per LLM call)
- [x] Stock price sparklines around news event dates
- [x] EDGAR ticker normalisation + foreign ticker skip
- [x] Real-time research progress bar (9 steps)
- [x] Architecture and agent flow Mermaid diagrams

---

## 11. Roadmap

### Phase 2 — Production Hardening
- [ ] SSO / user authentication (OAuth2, SAML)
- [ ] Scheduled auto-refresh (daily/weekly cron)
- [ ] Email/Slack alerts for high-severity news or stale data
- [ ] Neo4j Aura or enterprise deployment
- [ ] Job queue (Celery/Redis) for concurrent research requests
- [ ] S3/cloud storage for EDGAR filing cache

### Phase 3 — Data Depth
- [ ] Real transaction data integration (replace demo products)
- [ ] Policy & compliance library (KYC, AML, sanctions)
- [ ] Bloomberg/FactSet financial data feeds
- [ ] LinkedIn API integration for officer profiles
- [ ] Internal CRM sync (Salesforce, HubSpot)

### Phase 4 — AI-Powered Insights
- [ ] Natural language query interface ("What changed for Tesla since last quarter?")
- [ ] AI-generated meeting agendas + talking points
- [ ] Predictive cross-sell propensity scoring
- [ ] Portfolio-level CRM view (all clients of a banker)
- [ ] PowerPoint / Excel export
- [ ] ESG scoring integration

---

## 12. What This Product Is NOT

- ❌ Not a credit decisioning tool — intelligence only, decisions remain human-driven
- ❌ Not real-time transaction monitoring — periodic / historical data
- ❌ Not a CRM replacement — augments existing systems
- ❌ Not optimised for private companies — limited data without SEC filings
- ❌ Not mobile-optimised — desktop browser only (current)

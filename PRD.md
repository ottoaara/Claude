# Product Requirements Document: Context Fabric

## 1. Product Overview

### Product Name
**Context Fabric** — Commercial Banking Knowledge Graph

### Vision Statement
An AI-powered knowledge graph system that gives commercial relationship managers timely, comprehensive, and actionable intelligence on their clients by automatically researching companies across 7 dimensions and presenting interconnected insights through an interactive dashboard, with RM workflow tools (activity log, deal tracking, portfolio view, pre-meeting briefs), PDF export, and a callable service API.

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
- Extracts: revenue, net income, operating income, EBITDA, total assets, cash, equity, long-term debt, D&A, operating cash flow, free cash flow, interest expense, and 20+ more fields
- Ticker normalisation: alias map (3M→MMM) + foreign ticker skip
- **Disk cache first**: if filing already exists at `sec-edgar-filings/{TICKER}/{TYPE}/`, skip download entirely
- `is_filing_stale()` also checks disk before hitting SEC API (fast-path avoids live HTTP call)
- Files cached locally in `sec-edgar-filings/` (55+ tickers pre-downloaded)

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

### Dimension 7: Officer Intelligence (OfficerAgent)
- Source: DuckDuckGo web search (discovery + deep profiling)
- Per-officer profile: background, education, previous roles, tenure, LinkedIn
- Risk flags, banking relevance, key achievements, publications, board seats
- Confidence scoring (high / medium / low)
- Manual search: POST /officer/search for any named individual
- Always uses Claude Sonnet 4.6 regardless of LLM_PROVIDER env setting

### Relationship Intelligence Layer (cross-cutting)
- 17 Wells Fargo officers seeded in Neo4j with real board memberships and education data
- Board Interlock Map: identifies company officers who share external board seats with WF officers
- Alumni Network: identifies company officers who attended the same institution as WF officers
- Fuzzy matching: handles partial names, board name variations, school abbreviations
- Warm Entry Points surfaced in the Pitch tab and Meeting Brief
- Source: `(:Company)-[:HAS_OFFICER]->(:Officer)` cross-referenced against `(:Company {name:"Wells Fargo"})-[:HAS_OFFICER]->(:Officer)`

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

### 5.2 Interactive Dashboard — 8 Tabs
1. **Executive Summary** — AI-generated brief + Deal Trigger Alerts (Claude-classified triggers with urgency/product/action)
2. **Financial Metrics** — Income statement, balance sheet, cash flow, period-over-period + Covenant Watch (D/EBITDA, interest coverage, net margin, ROA vs thresholds)
3. **Industry Analysis** — NAICS sector, peer benchmarking, 6 SVG bar charts
4. **News & Sentiment** — Classified news, severity, stock sparklines, configurable freshness windows
5. **Knowledge Graph** — Force-directed visualization, clickable node detail panel
6. **Officer Intelligence** — Executive cards, risk flags, expandable profiles, manual search, Board Interlock Map, Alumni Network
7. **Pitch** — Incumbent Bank detection, product recommendations, warm entry points, relationship-based sales approach
8. **Activity** — RM Activity Log (calls/emails/meetings) + Prior Deals History (products, status, amount)

### 5.3 Pre-Meeting Tools
- **One-Click Meeting Brief** — Modal with optional contact name/role; Claude synthesises headline, 3 positives/3 risks, 5 smart questions, warm entry points, avoid-mentioning list, and pre-call email draft
- **Incumbent Bank Detection** — On-demand DDG/SEC search for credit agreements; identifies primary bank, other lenders, facility type/size/maturity, WF opportunity note
- **Meeting Brief button** in dashboard header; always available when a company is loaded

### 5.4 RM Portfolio Tools
- **Portfolio Dashboard** — `/rm` page; sortable table of all companies with last contact age, news risk badge, active deal count, activity count; click-through to company research
- **Industry Heat Map** — NAICS sector grid showing risk score, company count, sentiment, deal count
- **RM Activity Log** — Log calls, emails, meetings with contact name/role/notes/next action; color-coded by type
- **Prior Deals History** — Track WF products by category (Treasury, Credit, Capital Markets, etc.), status (pipeline/active/closed/lost), amount, and date

### 5.5 PDF Export
- One-click Export PDF button in dashboard header
- A4 format via reportlab; Wells Fargo brand styling
- Sections: cover page, company overview, financial highlights, peer comparison,
  industry, news & risk signals, officer profiles, product portfolio
- Streamed as `application/pdf` from `GET /company/{name}/report/pdf`

### 5.6 Service API
- `GET /company/{name}/report` — complete JSON intelligence package
- `GET /company/{name}/report/pdf` — PDF binary
- `X-API-Key` header auth (controlled by `BANKING_API_KEY` env var)
- `BANKING_CORS_ORIGINS` env var for cross-origin production deployments
- Full OpenAPI/Swagger docs at `/docs`

### 5.7 Knowledge Graph Storage (Neo4j)
Node types: `Company`, `Financial`, `News`, `Product`, `Industry`, `PeerCompany`, `Officer`, `Activity`, `Deal`

Relationships:
```
(:Company)-[:HAS_FILING]->(:Financial)
(:Company)-[:MENTIONED_IN]->(:News)
(:Company)-[:OFFERS]->(:Product)
(:Company)-[:BELONGS_TO]->(:Industry)
(:Company)-[:HAS_PEER]->(:PeerCompany)
(:Company)-[:HAS_OFFICER]->(:Officer)
(:Company)-[:PEER_OF]-(:Company)
(:Company)-[:HAS_ACTIVITY]->(:Activity)
(:Company)-[:HAS_DEAL]->(:Deal)
```

---

## 6. Technical Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, TailwindCSS |
| Backend | FastAPI, Python 3.10+, uvicorn |
| AI Orchestration | LangGraph + LangChain |
| LLM | Claude Sonnet 4.6 (Anthropic) or Ollama / llama3 (local) |
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
GET  /company/{name}/triggers            Deal trigger analysis (Claude)
GET  /company/{name}/covenant-watch      Financial ratio monitoring
GET  /company/{name}/incumbent-bank      Incumbent bank detection
GET  /company/{name}/meeting-brief       Pre-meeting synthesis brief
GET  /company/{name}/activity            RM activity log
POST /company/{name}/activity            Log call/email/meeting
DELETE /activity/{activity_id}           Remove activity entry
GET  /company/{name}/deals               Prior WF products/deals
POST /company/{name}/deals               Add deal record
DELETE /deal/{deal_id}                   Remove deal record
GET  /company/{name}/relationship-map    Board interlock + alumni connections
GET  /rm/portfolio                       All companies with RM stats
GET  /rm/industry-heatmap                Sector risk scores
GET  /company/{name}/report              JSON report (API key)
GET  /company/{name}/report/pdf          PDF brief   (API key)

POST /officer/search                     Manual officer research
GET  /stock/{ticker}/around-dates        Price context for news dates

DELETE /company/{name}                   Clear company data
GET  /health                             Health check
```

---

## 7. User Workflows

### 7.1 Pre-Meeting Preparation
1. Open http://localhost:3000/banking
2. Enter company name + ticker + website (or select from previously researched companies)
3. Click **Start AI Research** — monitor 9-step progress bar
4. Review 8-tab dashboard (60–120 second total)
5. Click **Meeting Brief** in header — enter contact name/role, generate AI brief
6. Click **Export PDF** — download formatted brief
7. Use brief for meeting talking points

### 7.2 Service Integration
1. `POST /research/start` with company details
2. Poll `GET /research/status/{job_id}` until `status == "completed"`
3. Call `GET /company/{name}/report` for structured JSON
4. Or `GET /company/{name}/report/pdf` for formatted PDF

### 7.3 Officer Intelligence
- Automatic: officers profiled during research workflow
- Manual: `POST /officer/search` for any contact — name + company + role
- UI: Officer Intelligence tab shows cards with risk flags, LinkedIn, re-search button
- Board Interlock Map: see shared external board seats between company officers and WF officers
- Alumni Network: see shared institutional connections

### 7.4 Meeting Brief
1. Load or research a company
2. Click **Meeting Brief** button in dashboard header
3. Optionally enter contact name and role
4. Claude synthesises all data into: headline, 3 positives, 3 risks, 5 smart questions, warm entry points, avoid-mentioning list, pre-call email draft

### 7.5 RM Activity Tracking
1. Open company research, click **Activity** tab
2. Click **Log Activity** — select type (call/email/meeting/note), date, contact, notes, next action
3. Click **Deals** sub-tab — add WF products with category, status, amount, date
4. All activity and deals persist in Neo4j

### 7.6 Portfolio Management
1. Open http://localhost:3000/rm
2. View all companies with last contact age, news risk, active deals, activity count
3. Sort by any column (name, risk, contact recency, deal count)
4. Click **Research** on any row to jump to full company dashboard
5. Review Industry Heat Map below table for sector-level risk view

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
- **LLM quality varies by provider** — Claude Sonnet 4.6 produces higher-quality structured output than Ollama llama3; triggers/recommendations may be less detailed with local model
- **Local Neo4j** — single node; production needs Neo4j Aura or cluster
- **No auth on dashboard** — API key only protects report endpoints; add SSO for production
- **Duplicate Company nodes** — prevented by case-insensitive name lookup in `add_peer_financial_data`

---

## 10. Completed Features

- [x] 7-dimension automated research (added Peer Financials + Officer Intelligence)
- [x] Neo4j knowledge graph with 9 node types (added Activity, Deal)
- [x] LangGraph 9-node sequential orchestration
- [x] Temporal freshness scoring + decay curves + pruning
- [x] FastAPI backend with full RESTful API (26 endpoints)
- [x] Next.js interactive dashboard — 8 tabs
- [x] PDF export (reportlab A4 brief)
- [x] Service API with X-API-Key auth
- [x] Peer financial comparison (6 SVG bar charts)
- [x] Officer Intelligence tab (auto + manual search)
- [x] Board Interlock Map (company officers sharing external board seats with WF officers)
- [x] Alumni Network (shared institutional affiliations with WF officers)
- [x] Relationship Map + Warm Entry Points in Pitch tab
- [x] Deal Trigger Alerts (Claude classifies news + financials into deal types with urgency)
- [x] Covenant Watch (D/EBITDA, interest coverage, net margin, ROA vs thresholds, green/yellow/red)
- [x] Incumbent Bank Detection (DDG + SEC search for credit agreement language)
- [x] One-Click Meeting Brief (Claude synthesis: headline, positives/risks, smart questions, email draft)
- [x] RM Activity Log (calls/emails/meetings with contact, notes, next action)
- [x] Prior Deals History (WF products by category, status, amount, date)
- [x] RM Portfolio Dashboard (/rm page: sortable company table + Industry Heat Map)
- [x] Knowledge graph force visualization with node detail panel
- [x] News sentiment classification (batch, 5 items per LLM call)
- [x] Stock price sparklines around news event dates
- [x] EDGAR ticker normalisation + foreign ticker skip
- [x] Real-time research progress bar (9 steps)
- [x] Icon-free UI (no emoji; text labels only)
- [x] Architecture and agent flow Mermaid diagrams
- [x] LLM provider abstraction — `llm_factory.get_llm()` routes to Anthropic or Ollama
- [x] Ollama JSON mode (`format=json`) to force valid JSON output from local models
- [x] `robust_parse_json` unwraps single-key wrapper objects (llama3 compatibility)
- [x] EDGAR disk cache — `fetch_filings()` and `is_filing_stale()` skip SEC HTTP calls when files exist locally
- [x] Peer comparison Cypher fix — join by ticker (not name) + PeerCompany node fallback
- [x] Duplicate Company node prevention — case-insensitive lookup before write
- [x] `FinancialMetrics` self-fetching — reads directly from graph API, no prop dependency
- [x] `OfficerResearch` null guard — `wf_officers ?? []` prevents crash on partial board interlock data
- [x] Universal TTL constants (`FINANCIAL_CACHE_TTL_DAYS`, `NAICS_CACHE_TTL_DAYS`, etc.)

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
- [ ] Predictive cross-sell propensity scoring
- [ ] PowerPoint / Excel export
- [ ] ESG scoring integration

---

## 12. What This Product Is NOT

- Not a credit decisioning tool — intelligence only, decisions remain human-driven
- Not real-time transaction monitoring — periodic / historical data
- Not a CRM replacement — augments existing systems
- Not optimised for private companies — limited data without SEC filings
- Not mobile-optimised — desktop browser only (current)

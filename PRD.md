# Product Requirements Document: Commercial Banking Knowledge Graph

## 1. Product Overview

### Product Name
**Context Fabric** - Commercial Banking Knowledge Graph

### Vision Statement
An AI-powered knowledge graph system that provides commercial relationship managers with timely, comprehensive, and actionable intelligence about their clients by automatically researching companies across multiple dimensions and presenting interconnected insights through an interactive visual dashboard.

### Product Type
Enterprise SaaS platform for commercial banking relationship management

---

## 2. Problem Statement

Commercial relationship managers need to prepare for client meetings with comprehensive, up-to-date information about their clients' financial health, industry position, and product needs. Currently, this research is:

- **Time-consuming**: Manual research across multiple data sources takes hours
- **Fragmented**: Data exists in silos (SEC filings, news sites, internal systems)
- **Potentially stale**: No automatic freshness tracking leads to outdated insights
- **Incomplete**: Missing connections between different data dimensions
- **Not actionable**: Raw data without synthesized recommendations

This results in under-prepared meetings, missed cross-sell opportunities, and potential compliance risks.

---

## 3. Target Users

### Primary User: Commercial Relationship Manager (CRM)
- **Role**: Manages relationships with commercial banking clients ($10M-$500M revenue)
- **Responsibilities**: 
  - Prepare for quarterly business reviews
  - Identify cross-sell opportunities
  - Monitor client financial health and risk
  - Stay current on client industry trends
- **Pain Points**:
  - Limited time for research (30-60 min per meeting prep)
  - Information overload from multiple sources
  - Difficulty connecting data points to actionable insights
  - Need to demonstrate value and expertise to clients

### Secondary Users
- **Credit Analysts**: Risk assessment and monitoring
- **Product Specialists**: Identifying product fit opportunities
- **Compliance Officers**: Policy and regulatory monitoring

---

## 4. Key Features

### 4.1 Automated Multi-Dimensional Research

#### Dimension 1: Financial Data (Edgar Agent)
- **Data Source**: SEC Edgar database (10-K and 10-Q filings)
- **Functionality**:
  - Automatic download of latest filings for public companies
  - Extract key financial metrics:
    - Income statement (revenue, net income, operating income)
    - Balance sheet (assets, liabilities, equity)
    - Cash flow statement
    - Key financial ratios
  - Track quarterly and annual trends
  - Filing metadata (period, filing date, document type)
- **Requirements**:
  - Must have valid stock ticker for full data
  - Cache downloaded filings locally to avoid redundant API calls
  - Handle companies with multiple entity filers

#### Dimension 2: Company Information (Web Scraper Agent)
- **Data Source**: Company websites and public web pages
- **Functionality**:
  - Extract company description and overview
  - Identify business model and target markets
  - Capture company size, locations, leadership
  - Extract mission/vision statements
- **Requirements**:
  - Respect robots.txt and rate limits
  - Handle various website structures
  - Gracefully fail for sites with bot protection

#### Dimension 3: News & Sentiment (News Agent)
- **Data Source**: Web search (DuckDuckGo)
- **Functionality**:
  - Search for recent company news (past 90 days priority)
  - AI-powered sentiment classification (positive/negative/neutral)
  - Severity scoring (high/medium/low)
  - Key event extraction (acquisitions, lawsuits, leadership changes)
- **Requirements**:
  - Focus on recent, relevant news
  - Filter out noise and promotional content
  - Identify material events that impact creditworthiness

#### Dimension 4: Product Portfolio (Product Agent)
- **Data Source**: AI-generated based on company profile (Demo)
- **Functionality**:
  - Generate likely product needs based on industry and size
  - Map banking products to client characteristics
  - Identify saturation gaps
- **Requirements**:
  - **Future**: Integrate with internal transaction history
  - **Future**: Real product database and recommendation engine
  - Current: Provide plausible demo data for visualization

#### Dimension 5: Industry Analysis (Industry Agent)
- **Data Source**: NAICS classification and peer comparison
- **Functionality**:
  - Classify company by NAICS sector
  - Identify peer companies in same sector
  - Compare financial metrics against industry averages
  - Identify industry trends and market position
- **Requirements**:
  - Accurate NAICS code mapping
  - Representative peer selection
  - Industry benchmark data sources

#### Dimension 6: Temporal Dimension (Applied to All)
- **Functionality**:
  - Score all data items for recency and relevance
  - Apply dimension-specific decay curves:
    - News: 90-day window (fast decay)
    - Quarterly financials: 120-day window
    - Industry trends: 180-day window
    - Annual financials: 365-day window
    - Products: 730-day window
  - Automatically prune stale data below relevance threshold (0.3)
  - Boost important content (severity, sentiment, filing type)
  - Provide temporal summary (fresh/recent/aged/stale breakdown)
- **Requirements**:
  - All data must include timestamp/date fields
  - Scoring must be fast (<15ms for 100 items)
  - Configurable windows and thresholds per deployment
  - Visual indicators of data freshness in UI

### 4.2 Interactive Knowledge Graph Visualization

- **Graph Structure**:
  - Central company node with bidirectional relationships
  - Node types: Company, Financial, News, Product, Industry, Peer
  - Relationship types: HAS_FILING, MENTIONED_IN, OFFERS, BELONGS_TO, PEER_OF
  - Color-coded by node type
  - Size-scaled by relevance score

- **Interactivity**:
  - Click nodes to view detailed information
  - Pan, zoom, and drag nodes
  - Real-time force simulation for optimal layout
  - Filter by dimension or relevance score

- **Performance**:
  - Handle 50-200 nodes smoothly
  - Render in <2 seconds
  - Responsive on desktop browsers (Chrome, Safari, Edge)

### 4.3 Real-Time Research Progress Tracking

- **Progress Indicators**:
  - Per-dimension status (pending, in-progress, completed, failed)
  - Live updates via polling (every 2 seconds)
  - Estimated time remaining
  - Error handling with actionable messages

- **Job Management**:
  - Unique job IDs for each research request
  - Job history and status lookup
  - Ability to view past research results

### 4.4 Company Research Dashboard

- **Input Form**:
  - Company name (required)
  - Stock ticker (optional, enables financial data)
  - Website URL (optional, improves company info extraction)
  - Clear validation and error messages

- **Results View**:
  - Executive summary (AI-generated)
  - Dimension-by-dimension breakdown
  - Graph visualization
  - Export capabilities (future)

### 4.5 RESTful API

**Core Endpoints**:

```
POST /research/start
  - Start new company research
  - Returns job_id for status tracking

GET /research/status/{job_id}
  - Check research progress
  - Returns current status and results

GET /research/jobs
  - List all research jobs
  - Filter by status, date

GET /company/{company_name}/graph
  - Get complete company knowledge graph
  - Includes all dimensions and relationships

GET /company/{company_name}/visualization
  - Get visualization-ready data structure
  - Nodes and links formatted for react-force-graph

DELETE /company/{company_name}
  - Clear company data from graph database
  - For testing and data refresh

GET /companies
  - List all companies in system
  - Pagination support

GET /health
  - System health check
  - Database connectivity status
```

**API Requirements**:
- OpenAPI/Swagger documentation at `/docs`
- JSON request/response format
- CORS enabled for frontend
- Error responses with clear messages
- Idempotent where applicable

---

## 5. Technical Architecture

### 5.1 Technology Stack

**Backend**:
- **Framework**: FastAPI (Python 3.11+)
- **AI Orchestration**: LangGraph + LangChain
- **LLM**: Claude Sonnet 4.6 (Anthropic API)
- **Database**: Neo4j (graph database)
- **Web Scraping**: BeautifulSoup, Requests
- **SEC Data**: sec-edgar-downloader
- **News Search**: DuckDuckGo Search API

**Frontend**:
- **Framework**: Next.js 16 (React 19)
- **Styling**: TailwindCSS
- **Visualization**: react-force-graph-2d
- **HTTP Client**: Fetch API
- **Type Safety**: TypeScript

**Infrastructure**:
- **Containerization**: Docker (Neo4j)
- **Environment**: Python virtual environment
- **Development**: Hot reload for API and frontend

### 5.2 Data Flow Architecture

```
User Input (Company Name)
    ↓
FastAPI Endpoint (/research/start)
    ↓
LangGraph Research Orchestrator
    ├─→ Web Scraper Agent      (Dimension 1: Company Info)
    ├─→ Edgar Agent            (Dimension 2: Financials)
    ├─→ News Agent             (Dimension 3: News & Sentiment)
    ├─→ Product Agent          (Dimension 4: Products)
    └─→ Industry Agent         (Dimension 5: Industry)
         ↓
    Temporal Dimension Processor
         ├─ Score for recency and relevance
         ├─ Apply decay curves
         └─ Prune stale data
         ↓
    Neo4j Knowledge Graph
         ├─ Create/update Company node
         ├─ Create relationship nodes
         └─ Store with relevance scores
         ↓
    AI Summary Generator (Claude)
         ↓
    Response to Frontend
         ↓
    Interactive Visualization
```

### 5.3 Neo4j Graph Schema

**Nodes**:
```cypher
// Company (central node)
(:Company {
  name: String,
  ticker: String?,
  website: String?,
  naics_code: String?,
  sector: String?,
  description: String?
})

// Financial Filing
(:Financial {
  filing_type: String,  // "10-K", "10-Q"
  period: String,       // "2024-Q1", "2024"
  filing_date: Date,
  revenue: Float?,
  net_income: Float?,
  assets: Float?,
  liabilities: Float?,
  equity: Float?,
  relevance_score: Float
})

// News Article
(:News {
  title: String,
  url: String?,
  date: Date,
  summary: String?,
  sentiment: String,    // "positive", "negative", "neutral"
  severity: String,     // "high", "medium", "low"
  relevance_score: Float
})

// Product
(:Product {
  name: String,
  category: String?,
  description: String?,
  revenue_impact: String?,  // "high", "medium", "low"
  timestamp: Date,
  relevance_score: Float
})

// Industry
(:Industry {
  naics_code: String,
  sector: String,
  description: String?
})
```

**Relationships**:
```cypher
(:Company)-[:HAS_FILING]->(:Financial)
(:Company)-[:MENTIONED_IN]->(:News)
(:Company)-[:OFFERS]->(:Product)
(:Company)-[:BELONGS_TO]->(:Industry)
(:Company)-[:PEER_OF]-(:Company)
```

---

## 6. User Workflows

### 6.1 Primary Workflow: Prepare for Client Meeting

**Scenario**: CRM has a meeting with Tesla in 2 days and needs current intelligence.

1. **Navigate to dashboard** (`http://localhost:3000/banking`)
2. **Enter company details**:
   - Company Name: "Tesla"
   - Ticker: "TSLA"
   - Website: "https://www.tesla.com"
3. **Click "Start AI Research"**
4. **Monitor progress** (30-90 seconds):
   - ✓ Company Info: 5 seconds
   - ✓ Financials: 30 seconds (downloading 10-K/10-Q)
   - ✓ News: 20 seconds (searching and analyzing)
   - ✓ Products: 10 seconds (generating)
   - ✓ Industry: 15 seconds (peer analysis)
5. **Review summary**: AI-generated executive summary highlighting:
   - Recent financial performance
   - Material news events
   - Industry positioning
   - Product opportunities
6. **Explore graph**: Visual relationships between dimensions
7. **Prepare talking points**: Use insights for meeting agenda

**Expected Outcome**: CRM has comprehensive, current intelligence in <2 minutes vs. 30-60 minutes of manual research.

### 6.2 Monitoring Workflow: Risk Alert

**Scenario**: Compliance wants to monitor existing clients for negative news.

1. **Use API to batch research** 50 existing clients
2. **Filter results** for high-severity negative news
3. **Review flagged companies** in dashboard
4. **Escalate** to credit team if needed

**Future Enhancement**: Automated alerts and scheduled refreshes.

---

## 7. Success Metrics

### 7.1 Product Success Metrics

**Efficiency Gains**:
- **Target**: Reduce meeting prep time from 30-60 min to <5 min (90% reduction)
- **Measurement**: User surveys and time-tracking analytics

**Research Coverage**:
- **Target**: 100% of clients researched before quarterly reviews
- **Measurement**: Research job completions vs. scheduled meetings

**Cross-Sell Lift**:
- **Target**: 20% increase in product recommendations per meeting
- **Measurement**: Product opportunities identified vs. baseline

**Data Freshness**:
- **Target**: >80% of data <90 days old at time of meeting
- **Measurement**: Temporal dimension scores in knowledge graph

### 7.2 Technical Performance Metrics

**Research Speed**:
- **Target**: Complete 5-dimension research in <90 seconds
- **Current**: 30-120 seconds depending on company
- **Measurement**: Job completion time tracking

**API Reliability**:
- **Target**: 99.5% uptime
- **Target**: <500ms P95 latency for API endpoints
- **Measurement**: API monitoring and logging

**Graph Query Performance**:
- **Target**: Visualization data retrieved in <2 seconds
- **Measurement**: Neo4j query execution times

**User Experience**:
- **Target**: <3 second initial page load
- **Target**: 100% of graph interactions <100ms response time
- **Measurement**: Frontend performance monitoring

### 7.3 Data Quality Metrics

**Completeness**:
- **Target**: >90% of public companies have financial data
- **Measurement**: Successful Edgar extractions / attempts

**Accuracy**:
- **Target**: >95% sentiment classification accuracy
- **Measurement**: Manual review and user feedback

**Freshness**:
- **Target**: Average data age <60 days across all dimensions
- **Measurement**: Temporal dimension analytics

---

## 8. What This Product Is NOT

### Explicit Non-Goals

❌ **Not a toy demo**: Production-grade system with real data sources, not mock data

❌ **Not for private companies**: Requires public financial data (SEC filings), focused on companies with stock tickers

❌ **Not a CRM replacement**: Augments existing CRM systems, doesn't replace them

❌ **Not a credit decisioning tool**: Provides intelligence, but credit decisions remain human-driven

❌ **Not real-time transaction monitoring**: Historical and periodic data, not live transaction feeds

❌ **Not a general-purpose research tool**: Purpose-built for commercial banking relationship management

❌ **Not a standalone product recommendation engine**: Product insights are one dimension of broader relationship intelligence

---

## 9. Constraints & Limitations

### 9.1 Current Implementation Limitations

**Data Source Limitations**:
- **Edgar**: Only public companies with SEC filings
- **News**: DuckDuckGo rate limits (~10 requests/min)
- **Web Scraping**: Fails for sites with aggressive bot protection
- **Products**: AI-generated demo data, not real transaction history

**Performance Constraints**:
- **Edgar Downloads**: First-time download can take 30-60 seconds
- **Sequential Processing**: News agent processes articles one-by-one
- **No Caching**: Repeated research re-fetches all data (future: implement caching)

**Scalability**:
- **Single-threaded**: LangGraph orchestration is sequential
- **No Queue**: Research requests are synchronous (future: job queue)
- **Local Storage**: Edgar filings stored locally (future: S3/cloud storage)

### 9.2 Technical Constraints

**Infrastructure**:
- **Neo4j Requirement**: Must have Neo4j running (Docker or installed)
- **API Keys Required**: Anthropic API key mandatory
- **Python 3.11+**: Not compatible with older Python versions
- **Desktop/Browser Only**: Not optimized for mobile

**Cost Considerations**:
- **Anthropic API**: ~$0.05-0.15 per company research (Claude Sonnet 4.6)
- **Rate Limits**: Anthropic API has tier-based limits
- **Neo4j**: Community edition has limitations (future: Aura or Enterprise)

---

## 10. Future Enhancements

### Phase 2: Product-Market Fit (Next 3-6 months)

**Priority 1: Real Transaction Data Integration**
- Connect to internal banking transaction database
- Map real product holdings to companies
- Calculate actual product saturation and gaps
- Generate data-driven cross-sell recommendations

**Priority 2: Policy & Compliance Library** (Dimension #5 from original spec)
- Integrate policy database
- Automatic compliance checks (KYC, AML, sanctions)
- Regulatory change alerts
- Industry-specific policies (healthcare, cannabis, etc.)

**Priority 3: Automated Refresh & Alerts**
- Scheduled daily/weekly research updates
- Email/Slack alerts for material events
- Proactive risk monitoring
- Stale data warnings

### Phase 3: Enterprise Features (6-12 months)

**Multi-User & Collaboration**:
- User authentication and authorization
- Role-based access control (CRM, Credit, Compliance)
- Shared notes and annotations on graph
- Meeting prep collaboration workspace

**Advanced Analytics**:
- Historical trend tracking (financial, sentiment, risk)
- Portfolio-level views (all clients of a CRM)
- Benchmarking against peer portfolios
- Predictive risk scoring

**Integration Ecosystem**:
- CRM integration (Salesforce, HubSpot)
- Calendar integration (auto-prep before meetings)
- Bloomberg/FactSet financial data feeds
- Internal core banking system connectors

**Export & Reporting**:
- PDF meeting prep reports
- PowerPoint slide generation
- Excel data exports
- Custom report templates

### Phase 4: AI-Powered Insights (12+ months)

**Conversational Interface**:
- Natural language queries ("What's changed for Tesla since last quarter?")
- AI-generated meeting agendas
- Talking point recommendations
- Post-meeting action item tracking

**Advanced Research Capabilities**:
- Multi-company comparison views
- M&A target identification
- Supply chain risk analysis
- ESG scoring integration

**Predictive Analytics**:
- Churn risk prediction
- Cross-sell propensity scoring
- Credit risk early warning
- Revenue forecasting

---

## 11. Development Roadmap

### MVP (Complete) ✅
- [x] 5-dimension research orchestration
- [x] Neo4j knowledge graph storage
- [x] Temporal dimension scoring and pruning
- [x] FastAPI backend with RESTful endpoints
- [x] Next.js frontend dashboard
- [x] Interactive graph visualization
- [x] Real-time progress tracking
- [x] AI-generated summaries

### V1.1 (Next Sprint - 2 weeks)
- [ ] Implement API response caching (Redis)
- [ ] Add job queue for background processing (Celery)
- [ ] Improve error handling and retry logic
- [ ] Add unit and integration tests (80% coverage target)
- [ ] Performance optimization (target <60s research time)
- [ ] User feedback collection mechanism

### V1.2 (1 month)
- [ ] User authentication (OAuth2)
- [ ] Multi-tenant support (company isolation)
- [ ] Historical research tracking (compare point-in-time)
- [ ] Export to PDF report
- [ ] Bloomberg/FactSet API integration (premium tier)
- [ ] Mobile-responsive design

### V2.0 (3 months)
- [ ] Real transaction data integration
- [ ] Policy & compliance library
- [ ] Automated scheduled refreshes
- [ ] Email/Slack alert system
- [ ] Portfolio-level analytics
- [ ] CRM integration (Salesforce)

---

## 12. Open Questions & Decisions Needed

### Business Questions
1. **Pricing Model**: Per-user subscription? Per-research credit? Enterprise license?
2. **Data Retention**: How long should we keep historical graph data?
3. **Refresh Frequency**: Should data auto-refresh daily, weekly, or on-demand only?
4. **Access Control**: Who can see what data? (CRM only sees their clients vs. firm-wide)

### Technical Questions
1. **Scalability Target**: How many users and companies in Year 1?
2. **Cloud Deployment**: AWS, Azure, or GCP? Multi-region?
3. **Neo4j Edition**: Community, Enterprise, or Aura (managed cloud)?
4. **Caching Strategy**: Redis for API responses? How to invalidate?

### Product Questions
1. **Mobile Support**: Do CRMs need mobile access for on-the-go prep?
2. **Offline Mode**: Should the app work without internet (cached data)?
3. **Customization**: Can users configure which dimensions to prioritize?
4. **Collaboration**: Do multiple CRMs need to share insights on same company?

---

## 13. Dependencies & Prerequisites

### External Dependencies
- **Anthropic API**: Claude Sonnet 4.6 access and API key
- **SEC Edgar**: Public data source (no authentication required)
- **DuckDuckGo Search**: Rate limits apply
- **Neo4j Database**: Self-hosted or Aura cloud instance

### Internal Dependencies (Future)
- **Transaction Database**: For real product saturation analysis
- **Policy Library Database**: For compliance checks
- **User Directory**: For authentication and authorization
- **CRM System**: For integration and client list sync

### Infrastructure Prerequisites
- **Docker**: For Neo4j containerization
- **Python 3.11+**: Runtime environment
- **Node.js 18+**: For frontend build and dev server
- **Cloud Storage**: For Edgar filing cache (future: S3)
- **Monitoring**: Application performance monitoring (future: Datadog/New Relic)

---

## 14. Security & Compliance Considerations

### Data Security
- **Encryption in Transit**: HTTPS/TLS for all API communication
- **Encryption at Rest**: Neo4j database encryption (Enterprise feature)
- **API Key Management**: Environment variables, never in code
- **Access Logs**: Audit trail of all research requests

### Compliance
- **Data Privacy**: No PII stored (company data only, not individual customer data)
- **Data Retention**: Configurable retention policies per regulatory requirements
- **Audit Trail**: Who accessed what company data and when
- **Right to Deletion**: Ability to purge company data on request

### Banking-Specific
- **Fair Lending**: Ensure AI doesn't introduce bias in recommendations
- **Know Your Customer (KYC)**: Verify company identity and sanctions screening (future)
- **AML Monitoring**: Flag suspicious activities or high-risk industries (future)

---

## 15. Glossary

**CRM**: Commercial Relationship Manager - banker managing business client relationships

**NAICS**: North American Industry Classification System - standard for industry categorization

**10-K**: Annual financial report filed with SEC by public companies

**10-Q**: Quarterly financial report filed with SEC by public companies

**Knowledge Graph**: Database that stores entities (nodes) and relationships (edges) between them

**Temporal Dimension**: Time-based scoring system that weights data by freshness and relevance

**LangGraph**: Framework for building stateful, multi-agent AI workflows with LangChain

**Neo4j**: Graph database management system optimized for connected data

**Relevance Score**: Combined metric (0.0-1.0) of data recency and content importance

**Cross-Sell**: Selling additional products to existing customers

**Edgar**: SEC's Electronic Data Gathering, Analysis, and Retrieval system for public company filings

---

## Appendix A: Example API Requests & Responses

### Start Research Request
```bash
curl -X POST http://localhost:8000/research/start \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tesla Inc.",
    "ticker": "TSLA",
    "website": "https://www.tesla.com"
  }'
```

### Response
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "company_name": "Tesla Inc.",
  "created_at": "2026-06-06T10:30:00Z"
}
```

### Check Status Request
```bash
curl http://localhost:8000/research/status/550e8400-e29b-41d4-a716-446655440000
```

### Status Response
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "company_name": "Tesla Inc.",
  "progress": {
    "company_info": "completed",
    "financials": "completed",
    "news": "completed",
    "products": "completed",
    "industry": "completed"
  },
  "result": {
    "summary": "Tesla Inc. is an electric vehicle and clean energy company...",
    "dimensions": {
      "financials": {
        "latest_filing": "10-Q 2024-Q1",
        "revenue": 21301.0,
        "net_income": 1129.0
      },
      "news": {
        "total_articles": 12,
        "sentiment_breakdown": {
          "positive": 7,
          "neutral": 3,
          "negative": 2
        }
      }
    },
    "temporal_summary": {
      "total_items": 47,
      "fresh_items": 15,
      "recent_items": 20,
      "avg_relevance_score": 0.72
    }
  },
  "completed_at": "2026-06-06T10:31:23Z"
}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-06 | Claude Code | Initial PRD based on existing implementation and Project_01 concept |


# Commercial Banking Knowledge Graph

An AI-powered knowledge graph system for commercial bankers to prepare for sales meetings. Automatically researches companies across 5 dimensions and builds an interactive knowledge graph.

## Architecture

### 5 Dimensions

1. **Customer Info** - Company information from public websites
2. **Financial Data** - SEC Edgar 10-K and 10-Q filings
3. **Negative News** - Web search for recent news and sentiment analysis
4. **Product Portfolio** - Generated product data (mock for demo)
5. **Industry Analysis** - NAICS classification, peer comparison, industry trends

### Temporal Dimension

All data is scored for recency and relevance, with automatic pruning of outdated information.

### Tech Stack

- **Backend**: FastAPI + LangGraph + LangChain
- **Database**: Neo4j (graph database)
- **AI**: Claude Sonnet 4.6 (via Anthropic API)
- **Frontend**: Next.js 16 + React + TailwindCSS
- **Visualization**: react-force-graph-2d

## Setup

### Prerequisites

1. **Neo4j Database**
   ```bash
   # Option 1: Docker (Recommended)
   docker run \
     --name banking-neo4j \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/password \
     -e NEO4J_PLUGINS='["apoc"]' \
     neo4j:latest
   
   # Option 2: Download from https://neo4j.com/download/
   ```

2. **Python Environment**
   ```bash
   # Activate virtual environment
   source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Node.js** (for frontend)
   ```bash
   cd src/kg_frontend
   npm install
   ```

### Environment Variables

Create a `.env` file in the project root:

```env
# Anthropic API
ANTHROPIC_API_KEY=your_api_key_here

# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# User Info
USER_EMAIL=ottoaara@gmail.com
```

## Running the System

### Start Neo4j
```bash
# If using Docker
docker start banking-neo4j

# Verify Neo4j is running at http://localhost:7474
```

### Start Backend API
```bash
# From project root
python -m uvicorn src.banking_kg.api:app --reload --port 8000
```

API will be available at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

### Start Frontend Dashboard
```bash
# In a new terminal
cd src/kg_frontend
npm run dev
```

Dashboard will be available at: `http://localhost:3000/banking`

## Usage

1. Navigate to `http://localhost:3000/banking`
2. Enter a company name (required)
3. Optionally provide:
   - Stock ticker (for SEC financial data)
   - Website URL (for company info scraping)
4. Click "Start AI Research"
5. Watch the progress as agents research across all 5 dimensions
6. Explore the interactive knowledge graph visualization

## API Endpoints

### Research
- `POST /research/start` - Start company research
- `GET /research/status/{job_id}` - Check research progress
- `GET /research/jobs` - List all research jobs

### Company Data
- `GET /company/{company_name}/graph` - Get complete company graph
- `GET /company/{company_name}/visualization` - Get visualization data
- `DELETE /company/{company_name}` - Clear company data
- `GET /companies` - List all companies

### System
- `GET /` - API info
- `GET /health` - Health check

## Example Companies to Try

With ticker (for full financial data):
- Apple Inc. (AAPL)
- Microsoft Corporation (MSFT)
- JPMorgan Chase & Co. (JPM)
- Goldman Sachs (GS)

Without ticker (limited data):
- Any private company or startup

## Project Structure

```
Claude/
├── src/
│   └── banking_kg/
│       ├── agents/
│       │   ├── edgar_agent.py         # SEC filings
│       │   ├── web_scraper_agent.py   # Company websites
│       │   ├── news_agent.py          # News search
│       │   ├── product_agent.py       # Product generation
│       │   └── industry_agent.py      # Industry analysis
│       ├── neo4j_db.py                # Neo4j interface
│       ├── temporal.py                # Temporal dimension
│       ├── research_orchestrator.py   # LangGraph workflow
│       └── api.py                     # FastAPI backend
│   └── kg_frontend/                   # Next.js dashboard
│       ├── app/banking/page.tsx
│       └── components/
│           ├── CompanyResearchForm.tsx
│           ├── ResearchProgress.tsx
│           └── GraphVisualization.tsx
└── requirements.txt
```

## How It Works

### Research Workflow (LangGraph)

```
1. Scrape Company Info (Web Agent)
   ├─→ 2. Fetch Financials (Edgar Agent)
   ├─→ 3. Search News (News Agent)
   ├─→ 4. Generate Products (Product Agent)
   └─→ 5. Analyze Industry (Industry Agent)
        ↓
6. Apply Temporal Scoring
        ↓
7. Populate Neo4j Graph
        ↓
8. Generate Summary
```

### Graph Schema

**Nodes:**
- Company (with ticker, website, sector, NAICS)
- Financial (10-K, 10-Q filings)
- News (articles with sentiment)
- Product (offerings with features)
- Industry (NAICS codes and sectors)

**Relationships:**
- Company -[HAS_FILING]→ Financial
- Company -[MENTIONED_IN]→ News
- Company -[OFFERS]→ Product
- Company -[BELONGS_TO]→ Industry
- Company -[PEER_OF]- Company

## Temporal Dimension

The system automatically scores data for relevance:

- **News**: 90-day window (high decay)
- **Financial**: 365-day window (low decay)
- **Products**: 730-day window (medium decay)
- **Industry**: 180-day window (medium decay)

Items below the relevance threshold are pruned to keep the graph focused on current, actionable data.

## Demo Limitations

- **Product data** is AI-generated (no real product database)
- **Financial analysis** requires valid stock tickers
- **News search** uses DuckDuckGo (rate-limited)
- **Web scraping** may fail for sites with bot protection

## Troubleshooting

### Neo4j Connection Failed
- Verify Neo4j is running: `docker ps` or check http://localhost:7474
- Check credentials in `.env` match Neo4j settings

### API Errors
- Check `ANTHROPIC_API_KEY` is set correctly
- Verify all dependencies installed: `pip list`

### Frontend Not Loading
- Check backend is running at http://localhost:8000
- Check API URL in frontend components matches backend port

### Research Taking Too Long
- Edgar downloads can be slow for companies with many filings
- News search is sequential and may take 30-60 seconds
- Check backend logs for progress

## Future Enhancements

- [ ] Real product database integration
- [ ] Bloomberg/FactSet financial data
- [ ] Credit scoring model
- [ ] Multi-company comparison views
- [ ] Historical tracking and change detection
- [ ] Export to PDF report
- [ ] Real-time news alerts
- [ ] Integration with CRM systems

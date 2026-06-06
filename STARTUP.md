# Context Fabric - Startup Guide

## Quick Start (5 minutes)

### 1. Start Neo4j Database

```bash
# Start Neo4j Docker container
docker run \
  --name banking-neo4j \
  -d \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Verify Neo4j is running
open http://localhost:7474
# Login: neo4j / password
```

### 2. Configure Environment

```bash
# Ensure .env file exists with your API keys
cat .env
```

Required variables:
```
ANTHROPIC_API_KEY=your_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
USER_EMAIL=your_email@example.com
```

### 3. Start Backend API

```bash
# Activate virtual environment
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

# Start FastAPI server
python -m uvicorn src.banking_kg.api:app --reload --port 8000
```

Backend will be available at: **http://localhost:8000**  
API docs at: **http://localhost:8000/docs**

### 4. Start Frontend Dashboard

```bash
# In a new terminal
cd src/kg_frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Dashboard will be available at: **http://localhost:3000/banking**

---

## Using the Prototype

### 1. Navigate to Dashboard
Open: **http://localhost:3000/banking**

### 2. Enter Company Information
- **Company Name** (required): e.g., "Tesla"
- **Ticker** (optional): e.g., "TSLA" (needed for SEC financial data)
- **Website** (optional): e.g., "https://www.tesla.com"

### 3. Start Research
Click **"Start AI Research"** and watch the AI agents work across 5 dimensions:
- 🌐 Company Info (web scraping)
- 💰 Financials (SEC Edgar 10-K/10-Q)
- 📰 News & Sentiment
- 🏭 Products (generated for demo)
- 🏢 Industry Analysis (NAICS & peers)

Research typically takes **30-90 seconds**.

### 4. View Results

The dashboard has **4 tabs**:

#### 📋 Executive Summary
- AI-generated meeting prep summary
- Data freshness indicators
- Meeting checklist

#### 💰 Financial Metrics
- **Income Statement**: Revenue, Operating Income, Net Income
- **Balance Sheet**: Assets, Liabilities, Equity
- **Cash Flow**: Operating, Investing, Financing
- Period-over-period comparisons

#### 🏢 Industry Analysis
- NAICS sector classification
- Peer company identification
- **Industry Comparison**: Company vs. sector averages
- Performance indicators (Above/Average/Below)

#### 🔗 Knowledge Graph
- Interactive visualization of all relationships
- Click nodes to see detailed attributes
- Color-coded by dimension type

---

## Example Companies to Try

### Public Companies (with ticker for full data):
- **Tesla** (TSLA)
- **Apple Inc.** (AAPL)
- **Microsoft Corporation** (MSFT)
- **JPMorgan Chase & Co.** (JPM)
- **Goldman Sachs** (GS)
- **Bank of America** (BAC)

### Private Companies (limited data):
- Stripe
- SpaceX
- OpenAI

---

## What's New in the Cleaned Prototype

### ✅ Improved Backend
- Better error handling and logging
- Structured API responses
- Graceful startup/shutdown

### ✅ Clean Frontend Architecture
- **API Client** (`lib/api.ts`): Centralized API calls, no hardcoded URLs
- **TypeScript Types**: Full type safety across components
- **Component Separation**:
  - `FinancialMetrics`: Income Statement, Balance Sheet, Cash Flow
  - `IndustryComparison`: NAICS analysis and peer benchmarking
  - `ExecutiveSummary`: AI summary with data freshness
  - `GraphVisualization`: Interactive knowledge graph

### ✅ Enhanced UX
- **Tab Navigation**: Clean separation of views
- **Data Freshness**: Temporal dimension displayed prominently
- **Financial Breakdown**: Separate cards for each statement
- **Industry Benchmarking**: Company vs. sector averages
- **Meeting Checklist**: Actionable prep steps

### ✅ Better Error Handling
- Custom `APIError` class
- User-friendly error messages
- Network failure recovery

---

## Troubleshooting

### Neo4j Not Running
```bash
# Check if container exists
docker ps -a | grep neo4j

# Start existing container
docker start banking-neo4j

# Or create new container (see step 1)
```

### Backend Won't Start
```bash
# Check dependencies
pip list | grep -E "fastapi|neo4j|langchain|anthropic"

# Reinstall if needed
pip install -r requirements.txt

# Check .env file
cat .env
```

### Frontend Build Errors
```bash
cd src/kg_frontend

# Clear and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for TypeScript errors
npm run build
```

### API Connection Failed
- Ensure backend is running at `http://localhost:8000`
- Check CORS settings in `src/banking_kg/api.py`
- Verify `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)

### Research Taking Too Long
- **Edgar downloads**: First-time downloads cached to `./data/edgar_downloads/`
- **News search**: Sequential processing, takes 30-60s
- **Check logs**: Backend terminal shows progress

---

## Stopping the System

```bash
# Stop frontend (Ctrl+C in terminal)

# Stop backend (Ctrl+C in terminal)

# Stop Neo4j
docker stop banking-neo4j

# Or keep Neo4j running for next session
```

---

## Next Steps

1. **Review PRD.md**: Understand the full product vision
2. **Test with real companies**: Try 3-5 companies in your target market
3. **Customize**: Modify components in `src/kg_frontend/components/`
4. **Extend backend**: Add new agents in `src/banking_kg/agents/`
5. **Deploy**: See deployment section in PRD.md

---

## Key Files Reference

### Backend
- `src/banking_kg/api.py` - FastAPI endpoints
- `src/banking_kg/research_orchestrator.py` - LangGraph workflow
- `src/banking_kg/neo4j_db.py` - Graph database interface
- `src/banking_kg/temporal.py` - Data freshness scoring
- `src/banking_kg/agents/` - 5 research agents

### Frontend
- `src/kg_frontend/app/banking/page.tsx` - Main dashboard
- `src/kg_frontend/lib/api.ts` - API client
- `src/kg_frontend/components/` - UI components

### Configuration
- `.env` - Environment variables
- `requirements.txt` - Python dependencies
- `src/kg_frontend/package.json` - Node dependencies

---

**Ready to start?** Run the 4 steps above and visit http://localhost:3000/banking

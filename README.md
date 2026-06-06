# Context Fabric

> AI-Powered Commercial Banking Knowledge Graph for Sales Meeting Preparation

Context Fabric is an intelligent research platform that helps commercial relationship managers prepare for client meetings by automatically researching companies across 5 dimensions and presenting insights through an interactive dashboard.

## 🚀 Quick Start

### Prerequisites

Before starting, ensure you have:
- **Docker** (for Neo4j database)
- **Python 3.11+** with virtual environment activated
- **Node.js 18+** and npm
- **Anthropic API key** ([Get one here](https://console.anthropic.com))

### Installation

**1. Clone and navigate to project root:**
```bash
cd /Users/aaronotto/Desktop/Claude
```

**2. Configure environment variables:**
```bash
# Check if .env file exists
cat .env

# If missing, copy from example
cp .env.example .env
```

Edit `.env` and add your API key:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
USER_EMAIL=your_email@example.com
```

**3. Install Python dependencies:**
```bash
# Activate virtual environment
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**4. Install frontend dependencies:**
```bash
cd src/kg_frontend
npm install
cd ../..
```

---

## ▶️ Starting the Demo

You need **3 terminals**, all starting from the project root: `/Users/aaronotto/Desktop/Claude`

### Terminal 1: Start Neo4j Database

```bash
cd /Users/aaronotto/Desktop/Claude

# Start Neo4j (first time)
docker run \
  --name banking-neo4j \
  -d \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# For subsequent starts (if container already exists)
docker start banking-neo4j

# Verify Neo4j is running
open http://localhost:7474
# Login: neo4j / password
```

### Terminal 2: Start Backend API

```bash
cd /Users/aaronotto/Desktop/Claude

# Activate virtual environment
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

# Start FastAPI server
python -m uvicorn src.banking_kg.api:app --reload --port 8000
```

**Backend running at:** http://localhost:8000  
**API docs:** http://localhost:8000/docs

### Terminal 3: Start Frontend Dashboard

```bash
cd /Users/aaronotto/Desktop/Claude
cd src/kg_frontend

# Start Next.js development server
npm run dev
```

**Dashboard running at:** http://localhost:3000/banking

---

## 🎯 Using the Demo

### 1. Open Dashboard
Navigate to: **http://localhost:3000/banking**

### 2. Enter Company Information
- **Company Name** (required): e.g., "Tesla"
- **Stock Ticker** (optional): e.g., "TSLA" - enables SEC financial data
- **Website** (optional): e.g., "https://www.tesla.com"

### 3. Start AI Research
Click **"Start AI Research"** and watch the progress across 5 dimensions:
- 🌐 **Company Info** - Web scraping from company website
- 💰 **Financials** - SEC Edgar 10-K and 10-Q filings
- 📰 **News** - Recent news with sentiment analysis
- 🏭 **Products** - Product portfolio (AI-generated for demo)
- 🏢 **Industry** - NAICS classification and peer comparison

Research typically completes in **30-90 seconds**.

### 4. Explore Results

Navigate through **4 tabs**:

**📋 Executive Summary**
- AI-generated meeting preparation summary
- Data freshness indicators (fresh/recent/aged/stale)
- Meeting preparation checklist

**💰 Financial Metrics**
- **Income Statement**: Revenue, Operating Income, Net Income
- **Balance Sheet**: Assets, Liabilities, Equity
- **Cash Flow**: Operating, Investing, Financing
- Period-over-period comparisons

**🏢 Industry Analysis**
- NAICS sector classification
- Peer company identification
- Company vs. industry average comparison
- Performance indicators (Above Average / Average / Below Average)

**🔗 Knowledge Graph**
- Interactive visualization of all data relationships
- Click nodes to see detailed information
- Color-coded by dimension type

---

## 📊 Example Companies to Try

### Public Companies (need ticker for full financial data):
- **Tesla** - TSLA
- **Apple Inc.** - AAPL
- **Microsoft Corporation** - MSFT
- **JPMorgan Chase & Co.** - JPM
- **Goldman Sachs** - GS
- **Bank of America** - BAC

### Private Companies (limited data without ticker):
- Stripe
- SpaceX
- OpenAI

---

## 🛑 Stopping the Demo

```bash
# Stop frontend (Terminal 3)
# Press Ctrl+C

# Stop backend (Terminal 2)
# Press Ctrl+C

# Stop Neo4j (Terminal 1)
docker stop banking-neo4j

# Optional: Remove Neo4j container completely
docker rm banking-neo4j
```

---

## 🔧 Troubleshooting

### Neo4j Connection Failed

```bash
# Check if Neo4j is running
docker ps | grep neo4j

# View logs
docker logs banking-neo4j

# Restart Neo4j
docker restart banking-neo4j
```

### Backend Won't Start

```bash
# Verify virtual environment is activated
which python
# Should show: /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/python

# Check dependencies
pip list | grep -E "fastapi|neo4j|langchain|anthropic"

# Reinstall if needed
pip install -r requirements.txt

# Verify .env file
cat .env | grep ANTHROPIC_API_KEY
```

### Frontend Errors

```bash
cd src/kg_frontend

# Clear and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for errors
npm run build
```

### Research Taking Too Long

- **Edgar downloads**: First-time downloads can take 30-60 seconds, then cached
- **News search**: Sequential processing takes 30-60 seconds
- **Check backend logs**: Terminal 2 shows progress and errors

### API Connection Issues

- Verify backend is running: http://localhost:8000/health
- Check CORS settings in `src/banking_kg/api.py`
- Ensure frontend API URL is correct (defaults to `http://localhost:8000`)

---

## 📁 Project Structure

```
Claude/
├── README.md                    # This file
├── PRD.md                       # Product Requirements Document
├── STARTUP.md                   # Detailed startup guide
├── .env                         # Environment variables (gitignored)
├── requirements.txt             # Python dependencies
├── src/
│   ├── banking_kg/              # Backend (FastAPI + LangGraph)
│   │   ├── api.py               # FastAPI endpoints
│   │   ├── research_orchestrator.py  # LangGraph workflow
│   │   ├── neo4j_db.py          # Neo4j interface
│   │   ├── temporal.py          # Data freshness scoring
│   │   └── agents/              # 5 research agents
│   │       ├── edgar_agent.py
│   │       ├── web_scraper_agent.py
│   │       ├── news_agent.py
│   │       ├── product_agent.py
│   │       └── industry_agent.py
│   └── kg_frontend/             # Frontend (Next.js + React)
│       ├── app/banking/page.tsx # Main dashboard
│       ├── lib/api.ts           # API client
│       └── components/          # UI components
│           ├── ExecutiveSummary.tsx
│           ├── FinancialMetrics.tsx
│           ├── IndustryComparison.tsx
│           └── GraphVisualization.tsx
└── data/                        # Edgar filing cache
```

---

## 🎨 Features

### Current Implementation (MVP)
- ✅ 5-dimension automated research
- ✅ Neo4j knowledge graph storage
- ✅ Temporal dimension (data freshness scoring)
- ✅ FastAPI backend with RESTful endpoints
- ✅ Next.js interactive dashboard
- ✅ Financial metrics (Income Statement, Balance Sheet, Cash Flow)
- ✅ Industry comparison (NAICS + peer benchmarking)
- ✅ Real-time progress tracking
- ✅ Interactive graph visualization

### Roadmap (See PRD.md)
- 🔜 Real transaction data integration
- 🔜 Policy & compliance library
- 🔜 Automated scheduled refreshes
- 🔜 Email/Slack alerts
- 🔜 User authentication
- 🔜 CRM integration (Salesforce)
- 🔜 Export to PDF reports

---

## 📚 Documentation

- **[PRD.md](PRD.md)** - Full product requirements and vision
- **[STARTUP.md](STARTUP.md)** - Detailed startup instructions
- **[QUICKSTART.md](QUICKSTART.md)** - Quick reference guide
- **[README_BANKING_KG.md](README_BANKING_KG.md)** - Technical architecture
- **[TEMPORAL_DIMENSION.md](TEMPORAL_DIMENSION.md)** - Data freshness algorithm

---

## 🤝 Support

For issues or questions:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review detailed logs in Terminal 2 (backend)
3. Check API health: http://localhost:8000/health
4. Verify Neo4j at: http://localhost:7474

---

## 📄 License

See project documentation for license information.

---

**Built with:** FastAPI • LangGraph • Claude Sonnet 4.6 • Neo4j • Next.js • React • TailwindCSS

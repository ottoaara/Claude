# Quick Start Guide - Banking Knowledge Graph

## 1. Setup (First Time Only)

### Install Neo4j with Docker

```bash
# Start Neo4j
./scripts/start_neo4j.sh

# Or manually:
docker run \
  --name banking-neo4j \
  -d \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### Configure Environment

```bash
# Copy example .env
cp .env.example .env

# Edit .env and add your Anthropic API key
nano .env
```

Required in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
USER_EMAIL=your_email@example.com
```

### Install Dependencies

```bash
# Activate virtual environment
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install frontend packages
cd src/kg_frontend
npm install
cd ../..
```

## 2. Running the System

### Terminal 1: Start Neo4j (if not already running)

```bash
docker start banking-neo4j

# Verify at http://localhost:7474
# Login: neo4j / password
```

### Terminal 2: Start Backend API

```bash
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

python -m uvicorn src.banking_kg.api:app --reload --port 8000
```

Backend running at: http://localhost:8000  
API docs at: http://localhost:8000/docs

### Terminal 3: Start Frontend Dashboard

```bash
cd src/kg_frontend
npm run dev
```

Dashboard at: http://localhost:3000/banking

## 3. Using the System

1. **Navigate to Dashboard**: http://localhost:3000/banking

2. **Enter Company Info**:
   - Company Name: e.g., "Tesla"
   - Ticker (optional): e.g., "TSLA" (needed for SEC data)
   - Website (optional): e.g., "https://www.tesla.com"

3. **Start Research**: Click "Start AI Research"

4. **Watch Progress**: See real-time progress across 5 dimensions:
   - 🌐 Company Info (web scraping)
   - 💰 Financials (SEC Edgar)
   - 📰 News (search & sentiment)
   - 🏭 Products (generated)
   - 🏢 Industry (NAICS & peers)

5. **Explore Graph**: Interactive visualization shows relationships between:
   - Company ← → Financials, News, Products, Industry, Peers

## 4. Testing

Run a quick test without the frontend:

```bash
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

# Make sure Neo4j is running first
python scripts/test_system.py
```

## 5. API Usage (Alternative to UI)

### Start Research via API

```bash
curl -X POST http://localhost:8000/research/start \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Apple Inc.",
    "ticker": "AAPL",
    "website": "https://www.apple.com"
  }'
```

Response:
```json
{
  "job_id": "abc-123-def",
  "status": "pending",
  "company_name": "Apple Inc."
}
```

### Check Research Status

```bash
curl http://localhost:8000/research/status/abc-123-def
```

### Get Graph Visualization

```bash
curl http://localhost:8000/company/Apple%20Inc./visualization
```

## 6. Example Companies to Try

### Public Companies with Full Data (need ticker):
- **Tesla** (TSLA)
- **Apple Inc.** (AAPL)
- **Microsoft Corporation** (MSFT)
- **JPMorgan Chase & Co.** (JPM)
- **Goldman Sachs** (GS)
- **Bank of America** (BAC)

### Any Company (limited data without ticker):
- Stripe
- SpaceX
- OpenAI

## Troubleshooting

### "Neo4j connection failed"
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Start if needed
docker start banking-neo4j

# Check logs
docker logs banking-neo4j
```

### "Module not found" errors
```bash
# Reinstall dependencies
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate
pip install -r requirements.txt
```

### "Anthropic API error"
- Check your API key in `.env`
- Verify you have credits: https://console.anthropic.com

### Frontend won't start
```bash
cd src/kg_frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Research is slow
- Edgar downloads can take 30-60s for companies with many filings
- News searches are sequential (30-60s)
- First run downloads filing data to `./data/edgar_downloads/`

## What Gets Created

```
Claude/
├── .env                      # Your API keys (gitignored)
├── data/
│   └── edgar_downloads/      # SEC filing cache
└── memory/
    └── knowledge_graph/
        └── graph.json        # Legacy JSON graph (not used in Neo4j mode)
```

Neo4j data is stored in Docker volume: `neo4j_banking_data`

## Next Steps

- Read [README_BANKING_KG.md](README_BANKING_KG.md) for architecture details
- Explore API docs at http://localhost:8000/docs
- Browse Neo4j graph at http://localhost:7474
- Check `src/banking_kg/` for implementation details

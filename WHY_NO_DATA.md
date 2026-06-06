# Why Am I Not Seeing Financial Metrics or Industry Data?

## TL;DR - Run This First

```bash
cd /Users/aaronotto/Desktop/Claude
./quick_check.sh
```

This will tell you what's wrong.

---

## Most Common Reasons

### 1. **You didn't provide a stock ticker** ⭐ MOST COMMON

The financial metrics come from SEC Edgar filings, which require a valid stock ticker.

**Fix:** When researching, make sure to fill in the "Stock Ticker" field:
- Tesla → **TSLA**
- Apple → **AAPL**
- Microsoft → **MSFT**
- JPMorgan → **JPM**

Without a ticker, you'll see:
```
No financial data available
Make sure to provide a valid stock ticker when researching the company.
```

### 2. **Research hasn't finished yet**

The research takes 30-90 seconds. The tabs appear immediately but data loads progressively.

**Fix:** Wait for the "Research Complete" message before switching tabs.

### 3. **Backend isn't running**

If the API isn't running, no data will load.

**Check:**
```bash
curl http://localhost:8000/health
```

**Fix:**
```bash
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate
python -m uvicorn src.banking_kg.api:app --reload --port 8000
```

### 4. **ANTHROPIC_API_KEY not set**

The system uses Claude to extract financial data from SEC filings.

**Check:** Look in `.env` file for:
```
ANTHROPIC_API_KEY=sk-ant-...
```

**Fix:** Add your Anthropic API key to the `.env` file.

### 5. **Neo4j not running**

The knowledge graph requires Neo4j.

**Check:**
```bash
docker ps | grep neo4j
```

**Fix:**
```bash
docker start banking-neo4j
```

Or if container doesn't exist:
```bash
docker run --name banking-neo4j -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest
```

---

## How to Verify Data is Working

### Backend Test (No Frontend)

```bash
cd /Users/aaronotto/Desktop/Claude
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate
python test_research.py
```

**What you should see:**
```
✅ Completed steps: ['company_info', 'financials', 'news', 'products', 'industry', ...]
💰 Financial filings found: 4
   - 10-K 2023: Revenue=$96773.0M
   - 10-Q 2023-Q3: Revenue=$23350.0M
🏢 Industry: Motor Vehicle Manufacturing
   NAICS Code: 3361
```

If this works, the backend is fine. The issue is frontend.

If this doesn't work, the issue is backend (likely API key or ticker).

### Full System Test

1. Start all services:
   ```bash
   # Terminal 1: Neo4j
   docker start banking-neo4j
   
   # Terminal 2: Backend
   source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate
   python -m uvicorn src.banking_kg.api:app --reload --port 8000
   
   # Terminal 3: Frontend
   cd src/kg_frontend
   npm run dev
   ```

2. Open: http://localhost:3000/banking

3. Research **Tesla** with ticker **TSLA**

4. Wait for "Research Complete"

5. Check tabs:
   - **Executive Summary** → Should show company overview, financials snapshot, news
   - **Financial Metrics** → Should show 3 sections (Income/Balance/Cash Flow)
   - **Industry Analysis** → Should show NAICS classification and peers
   - **Knowledge Graph** → Should show force-directed graph

### What You Should See in Logs

**Backend (Terminal 2):**
```
💰 Fetching financials for ticker: 'TSLA'
📊 Edgar Agent: Starting financial research for ticker 'TSLA'
   Fetching 10-K filings...
   Found 2 10-K filing(s)
   ✅ Extracted: Period=2023, Revenue=96773.0
   
🏢 Analyzing industry for Tesla Inc....
   ✅ Industry analysis completed:
      NAICS: 3361
      Sector: Motor Vehicle Manufacturing
      Peers: 5

✅ Research result structure:
   - Financials: 4 filings
   - Industry: Motor Vehicle Manufacturing
   - News: 8 items

✅ Research completed for Tesla Inc.
   API storing result with:
   - Financials: 4 filings
   - Industry: Motor Vehicle Manufacturing
```

**Browser Console (F12):**
```
Research completed with result: {...}
Financials: (4) [{period: "2023", revenue: 96773, ...}, ...]
Industry: {naics_code: "3361", naics_sector_name: "Motor Vehicle Manufacturing", ...}
FinancialMetrics received: (4) [{...}, {...}, {...}, {...}]
Latest filing: {period: "2023", revenue: 96773, ...}
```

---

## Still Not Working?

### Debug Steps:

1. **Run quick check:**
   ```bash
   ./quick_check.sh
   ```

2. **Test backend only:**
   ```bash
   python test_research.py
   ```

3. **Check API directly:**
   Start research:
   ```bash
   curl -X POST http://localhost:8000/research/start \
     -H "Content-Type: application/json" \
     -d '{"company_name": "Tesla Inc.", "ticker": "TSLA", "website": "https://www.tesla.com"}'
   ```
   
   Copy the `job_id`, wait 60 seconds, then:
   ```bash
   curl http://localhost:8000/research/status/JOB_ID_HERE | python3 -m json.tool
   ```
   
   Look for `result.dimensions.financials` array.

4. **Check browser console** for errors

5. **Provide these logs:**
   - Last 50 lines from Terminal 2 (backend)
   - Browser console screenshot
   - API status response from step 3

---

## Expected Data Structure

The backend returns:
```json
{
  "summary": "Text summary...",
  "dimensions": {
    "financials": [
      {
        "period": "2023",
        "filing_type": "10-K",
        "filing_date": "2024-01-29",
        "revenue": 96773,
        "net_income": 14997,
        "operating_income": 8891,
        "assets": 106618,
        "liabilities": 54635,
        "equity": 51983,
        "operating_cash_flow": 13256,
        "investing_cash_flow": -8896,
        "financing_cash_flow": -4217
      }
    ],
    "industry": {
      "naics_code": "3361",
      "naics_sector_name": "Motor Vehicle Manufacturing",
      "peer_companies": ["Ford", "GM", "Rivian", ...]
    },
    "news": [...],
    "products": [...],
    "company_info": {...}
  }
}
```

The frontend expects exactly this structure.

---

## Quick Fix Checklist

- [ ] Backend running on port 8000
- [ ] Neo4j running (docker ps shows it)
- [ ] Frontend running on port 3000
- [ ] `.env` file has ANTHROPIC_API_KEY
- [ ] **Ticker provided when researching** ⭐
- [ ] Waited for "Research Complete" message
- [ ] Checked backend Terminal 2 for errors
- [ ] Checked browser console (F12) for errors

If all checked and still no data → See [TROUBLESHOOT.md](TROUBLESHOOT.md)

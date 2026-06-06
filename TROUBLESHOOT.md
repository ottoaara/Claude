# Troubleshooting: No Financial Metrics

## Quick Diagnosis Steps

### Step 1: Is the backend running?
```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "orchestrator_ready": true
}
```

### Step 2: Can we reach the API?
```bash
curl http://localhost:8000/companies
```

Should return a list of companies (may be empty if no research done yet).

### Step 3: Start a research and capture the job ID
```bash
curl -X POST http://localhost:8000/research/start \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tesla Inc.",
    "ticker": "TSLA",
    "website": "https://www.tesla.com"
  }'
```

Output will include a `job_id`. Copy it.

### Step 4: Wait 60 seconds, then check status
```bash
# Replace JOB_ID_HERE with the actual job ID from step 3
curl http://localhost:8000/research/status/JOB_ID_HERE | python3 -m json.tool
```

Look for:
- `"status": "completed"` or `"failed"`
- `"result"` → `"dimensions"` → `"financials"` (should be an array)
- `"result"` → `"dimensions"` → `"industry"` (should be an object)

### Step 5: Check backend logs

In Terminal 2 (where the backend is running), look for:

**Good signs:**
```
📊 Edgar Agent: Starting financial research for ticker 'TSLA'
   Fetching 10-K filings...
   Found 2 10-K filing(s)
   ✅ Extracted: Period=2023, Revenue=96773.0
```

```
✅ Research result structure:
   - Financials: 4 filings
   - Industry: Motor Vehicle Manufacturing
```

**Bad signs:**
```
⚠️  No ticker provided, skipping financial data
```
```
❌ Financial data error: ...
```

## Common Issues

### Issue 1: "No financial data available"

**Possible causes:**
1. Ticker not provided or invalid
2. Edgar agent failing to download filings
3. Claude failing to extract data from filings

**Check:**
- Backend logs show ticker being passed: `Fetching financials for ticker: 'TSLA'`
- Edgar found filings: `Found 2 10-K filing(s)`
- Extraction succeeded: `✅ Extracted: Period=2023, Revenue=96773.0`

### Issue 2: Frontend shows data briefly then disappears

**Possible causes:**
1. React re-render clearing state
2. API polling clearing completed results

**Check browser console for:**
```
Research completed with result: {summary: "...", dimensions: {...}}
Financials: [{period: "2023", ...}, ...]
```

If you see this but UI shows "No data", it's a frontend rendering issue.

### Issue 3: Backend crashes during research

**Check backend terminal for:**
```
❌ Research failed for Tesla Inc.: ...
```

Common errors:
- `ANTHROPIC_API_KEY` not set
- Neo4j not running
- Network timeout downloading filings

## Manual Test Script

Run this to test backend only (no frontend):

```bash
cd /Users/aaronotto/Desktop/Claude
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate
python test_research.py
```

Expected output:
```
✅ Completed steps: ['company_info', 'financials', 'news', 'products', 'industry', ...]
💰 Financial filings found: 4
   - 10-K 2023: Revenue=$96773.0M
   - 10-Q 2023-Q3: Revenue=$...M
```

If this works but the API doesn't, the issue is in the API layer.

## Debug Checklist

- [ ] Backend is running (`curl http://localhost:8000/health`)
- [ ] Neo4j is running (`docker ps | grep neo4j`)
- [ ] API key is set (`echo $ANTHROPIC_API_KEY` or check `.env`)
- [ ] Ticker is valid and being passed
- [ ] Backend logs show Edgar agent running
- [ ] Backend logs show financials being extracted
- [ ] Backend logs show result structure with financials count > 0
- [ ] API status endpoint returns completed result
- [ ] Browser console shows result being received
- [ ] Frontend components receive the data (check console logs)

## Next Steps

If all checks pass but UI still shows "No data":

1. **Check browser console** (F12) for errors
2. **Check component props** - Add `console.log` in FinancialMetrics
3. **Verify data structure** - The frontend expects:
   ```javascript
   {
     dimensions: {
       financials: [{
         period: "2023",
         filing_type: "10-K",
         revenue: 96773,
         net_income: 14997,
         ...
       }]
     }
   }
   ```

4. **Test with different company** - Try AAPL, MSFT, JPM

## Contact Points

If still stuck, provide:
1. Backend terminal output (last 100 lines)
2. Browser console output
3. API status response (`curl http://localhost:8000/research/status/JOB_ID`)
4. Company and ticker you're testing with

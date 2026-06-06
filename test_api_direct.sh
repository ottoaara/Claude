#!/bin/bash

echo "=========================================="
echo "Testing Banking KG API Directly"
echo "=========================================="

# Start research
echo ""
echo "1. Starting research for Tesla (TSLA)..."
RESPONSE=$(curl -s -X POST http://localhost:8000/research/start \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tesla Inc.",
    "ticker": "TSLA",
    "website": "https://www.tesla.com"
  }')

echo "$RESPONSE" | python3 -m json.tool

JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")

echo ""
echo "Job ID: $JOB_ID"
echo ""
echo "2. Waiting for research to complete (60 seconds)..."
sleep 60

echo ""
echo "3. Checking research status..."
STATUS=$(curl -s http://localhost:8000/research/status/$JOB_ID)

echo "$STATUS" | python3 -m json.tool

echo ""
echo "4. Extracting key data..."
echo ""
echo "Financials count:"
echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('result', {}).get('dimensions', {}).get('financials', [])))"

echo ""
echo "First financial filing (if any):"
echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); financials=data.get('result', {}).get('dimensions', {}).get('financials', []); print(financials[0] if financials else 'None')" | python3 -m json.tool 2>/dev/null || echo "No financials found"

echo ""
echo "Industry:"
echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); industry=data.get('result', {}).get('dimensions', {}).get('industry', {}); print(f\"NAICS: {industry.get('naics_code', 'N/A')}, Sector: {industry.get('naics_sector_name', 'N/A')}\")"

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="

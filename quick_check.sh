#!/bin/bash

echo "🔍 Quick System Check"
echo "===================="
echo ""

# Check if backend is running
echo "1. Backend API Health:"
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "   ✅ Backend is running"
    echo "   $HEALTH" | python3 -m json.tool 2>/dev/null
else
    echo "   ❌ Backend is NOT running"
    echo "   Start it with: python -m uvicorn src.banking_kg.api:app --reload --port 8000"
    exit 1
fi

echo ""

# Check Neo4j
echo "2. Neo4j Status:"
if docker ps | grep -q neo4j; then
    echo "   ✅ Neo4j container is running"
else
    echo "   ❌ Neo4j is NOT running"
    echo "   Start it with: docker start banking-neo4j"
fi

echo ""

# Check .env
echo "3. Environment Variables:"
if [ -f .env ]; then
    echo "   ✅ .env file exists"
    if grep -q "ANTHROPIC_API_KEY=sk-" .env; then
        echo "   ✅ ANTHROPIC_API_KEY is set"
    else
        echo "   ⚠️  ANTHROPIC_API_KEY might not be set properly"
    fi
else
    echo "   ❌ .env file not found"
fi

echo ""

# Check frontend
echo "4. Frontend:"
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo "   ✅ Frontend is running at http://localhost:3000"
else
    echo "   ❌ Frontend is NOT running"
    echo "   Start it with: cd src/kg_frontend && npm run dev"
fi

echo ""
echo "===================="
echo "✅ System Check Complete"
echo ""
echo "Next steps:"
echo "1. Make sure all services above are running"
echo "2. Open http://localhost:3000/banking"
echo "3. Research a company with a ticker (e.g., Tesla - TSLA)"
echo "4. Watch Terminal 2 (backend) for debug output"
echo "5. Open browser console (F12) to see frontend logs"
echo ""

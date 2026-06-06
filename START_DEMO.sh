#!/bin/bash

echo "========================================="
echo "WELLS FARGO CONTEXT FABRIC - DEMO STARTUP"
echo "========================================="
echo ""

# Check Docker
if ! docker ps &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✅ Docker is running"

# Start Neo4j
echo ""
echo "Starting Neo4j..."
docker start banking-neo4j 2>/dev/null || docker run --name banking-neo4j -d -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
sleep 5
echo "✅ Neo4j started"

echo ""
echo "========================================="
echo "NEXT STEPS:"
echo "========================================="
echo ""
echo "Open 2 NEW terminal windows and run these commands:"
echo ""
echo "TERMINAL 2 (Backend):"
echo "  cd /Users/aaronotto/Desktop/Claude"
echo "  source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate"
echo "  python -m uvicorn src.banking_kg.api:app --reload --port 8000"
echo ""
echo "TERMINAL 3 (Frontend):"
echo "  cd /Users/aaronotto/Desktop/Claude/src/kg_frontend"
echo "  npm run dev"
echo ""
echo "Then open: http://localhost:3000/banking"
echo ""

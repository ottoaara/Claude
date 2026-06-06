#!/bin/bash
# ============================================================
# start.sh — Single-command launcher for the Banking KG App
# Usage: ./start.sh
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="/Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate"
FRONTEND_DIR="$PROJECT_DIR/src/kg_frontend"
BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"
BACKEND_PID_FILE="$PROJECT_DIR/api.pid"
FRONTEND_PID_FILE="$PROJECT_DIR/frontend.pid"

echo "============================================"
echo "  Banking Knowledge Graph — Starting App"
echo "============================================"
echo ""

# ── 1. Neo4j ──────────────────────────────────
if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
  echo "▶ Starting Neo4j..."
  docker start banking-neo4j 2>/dev/null || \
    docker run --name banking-neo4j -d \
      -p 7474:7474 -p 7687:7687 \
      -e NEO4J_AUTH=neo4j/password neo4j:latest
  echo "  Neo4j started (http://localhost:7474)"
else
  echo "⚠  Docker not running — skipping Neo4j."
  echo "   Install Docker Desktop or start it to enable Neo4j."
fi

echo ""

# ── 2. Backend (FastAPI) ───────────────────────
echo "▶ Starting backend on http://localhost:8000 ..."
source "$VENV"
cd "$PROJECT_DIR"
nohup python -m uvicorn src.banking_kg.api:app --reload --port 8000 \
  > "$BACKEND_LOG" 2>&1 &
echo $! > "$BACKEND_PID_FILE"
echo "  Backend PID: $(cat $BACKEND_PID_FILE)  (logs: backend.log)"

echo ""

# ── 3. Frontend (Next.js) ─────────────────────
echo "▶ Starting frontend on http://localhost:3000 ..."
cd "$FRONTEND_DIR"
nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
echo $! > "$FRONTEND_PID_FILE"
echo "  Frontend PID: $(cat $FRONTEND_PID_FILE)  (logs: frontend.log)"

echo ""
echo "============================================"
echo "  All services started!"
echo ""
echo "  App:     http://localhost:3000/banking"
echo "  API:     http://localhost:8000/docs"
echo "  Neo4j:   http://localhost:7474"
echo ""
echo "  To stop: ./stop.sh"
echo "============================================"

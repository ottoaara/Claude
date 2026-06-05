#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting Knowledge Graph API on :8000..."
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate
cd "$ROOT" && uvicorn src.kg_app.main:app --reload --port 8000 &
API_PID=$!

echo "Starting frontend on :3000..."
cd "$ROOT/src/kg_frontend" && /opt/homebrew/bin/npm run dev &
FRONT_PID=$!

trap "kill $API_PID $FRONT_PID 2>/dev/null" EXIT
echo "Both running. Open http://localhost:3000"
wait

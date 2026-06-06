#!/bin/bash
# stop.sh — Stop all Banking KG App services

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping Banking KG App..."

# Stop backend
if [ -f "$PROJECT_DIR/api.pid" ]; then
  kill "$(cat $PROJECT_DIR/api.pid)" 2>/dev/null && echo "  Backend stopped."
  rm -f "$PROJECT_DIR/api.pid"
fi

# Stop frontend
if [ -f "$PROJECT_DIR/frontend.pid" ]; then
  kill "$(cat $PROJECT_DIR/frontend.pid)" 2>/dev/null && echo "  Frontend stopped."
  rm -f "$PROJECT_DIR/frontend.pid"
fi

# Stop Neo4j
if command -v docker &> /dev/null; then
  docker stop banking-neo4j 2>/dev/null && echo "  Neo4j stopped."
fi

echo "Done."

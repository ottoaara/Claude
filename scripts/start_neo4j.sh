#!/bin/bash

# Start Neo4j using Docker for Banking Knowledge Graph

echo "🚀 Starting Neo4j database for Banking Knowledge Graph..."

# Check if container already exists
if docker ps -a | grep -q banking-neo4j; then
    echo "📦 Container exists, starting..."
    docker start banking-neo4j
else
    echo "📦 Creating new Neo4j container..."
    docker run \
        --name banking-neo4j \
        -d \
        -p 7474:7474 -p 7687:7687 \
        -e NEO4J_AUTH=neo4j/password \
        -e NEO4J_PLUGINS='["apoc"]' \
        -v neo4j_banking_data:/data \
        neo4j:latest
fi

echo "⏳ Waiting for Neo4j to be ready..."
sleep 10

echo "✅ Neo4j is running!"
echo "   Browser: http://localhost:7474"
echo "   Bolt: bolt://localhost:7687"
echo "   Username: neo4j"
echo "   Password: password"

import json
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.knowledge_graph import add_entity, add_relation, query_entity, get_neighbors, export_context


@pytest.fixture(autouse=True)
def tmp_graph(tmp_path, monkeypatch):
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps({"entities": {}, "relations": []}))
    import src.knowledge_graph as kg
    monkeypatch.setattr(kg, "GRAPH_PATH", graph_file)
    return graph_file


def test_add_and_query_entity():
    add_entity("Alice", "person", {"role": "engineer"})
    result = query_entity("Alice")
    assert result["type"] == "person"
    assert result["attributes"]["role"] == "engineer"


def test_query_missing_entity():
    assert query_entity("nobody") is None


def test_add_relation_and_get_neighbors():
    add_entity("A", "concept")
    add_entity("B", "concept")
    add_relation("A", "links_to", "B")
    neighbors = get_neighbors("A")
    assert any(n["relation"] == "links_to" and n["entity"] == "B" for n in neighbors)
    neighbors_b = get_neighbors("B")
    assert any(n["direction"] == "inbound" and n["entity"] == "A" for n in neighbors_b)


def test_duplicate_relation_not_added():
    add_entity("X", "thing")
    add_entity("Y", "thing")
    add_relation("X", "knows", "Y")
    add_relation("X", "knows", "Y")
    neighbors = get_neighbors("X")
    assert len([n for n in neighbors if n["relation"] == "knows"]) == 1


def test_export_context():
    add_entity("Bob", "person", {"team": "backend"})
    add_entity("ProjectZ", "project")
    add_relation("Bob", "works_on", "ProjectZ")
    ctx = export_context("Bob")
    assert "Bob" in ctx
    assert "works_on" in ctx
    assert "ProjectZ" in ctx


def test_export_context_missing():
    result = export_context("ghost")
    assert "No entity found" in result

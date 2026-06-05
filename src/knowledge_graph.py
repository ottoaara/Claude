import json
from pathlib import Path

GRAPH_PATH = Path(__file__).parent.parent / "memory" / "knowledge_graph" / "graph.json"


def _load() -> dict:
    if not GRAPH_PATH.exists():
        return {"entities": {}, "relations": []}
    return json.loads(GRAPH_PATH.read_text())


def _save(graph: dict) -> None:
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_PATH.write_text(json.dumps(graph, indent=2))


def add_entity(name: str, entity_type: str, attributes: dict | None = None) -> None:
    graph = _load()
    graph["entities"][name] = {"type": entity_type, "attributes": attributes or {}}
    _save(graph)


def add_relation(from_entity: str, relation: str, to_entity: str) -> None:
    graph = _load()
    edge = {"from": from_entity, "relation": relation, "to": to_entity}
    if edge not in graph["relations"]:
        graph["relations"].append(edge)
    _save(graph)


def query_entity(name: str) -> dict | None:
    graph = _load()
    entity = graph["entities"].get(name)
    if entity is None:
        return None
    return {"name": name, **entity}


def get_neighbors(name: str) -> list[dict]:
    graph = _load()
    neighbors = []
    for rel in graph["relations"]:
        if rel["from"] == name:
            neighbors.append({"direction": "outbound", "relation": rel["relation"], "entity": rel["to"]})
        elif rel["to"] == name:
            neighbors.append({"direction": "inbound", "relation": rel["relation"], "entity": rel["from"]})
    return neighbors


def export_context(name: str) -> str:
    entity = query_entity(name)
    if entity is None:
        return f"No entity found: {name}"

    lines = [f"Entity: {name} (type: {entity['type']})"]
    for k, v in entity.get("attributes", {}).items():
        lines.append(f"  {k}: {v}")

    neighbors = get_neighbors(name)
    if neighbors:
        lines.append("Relations:")
        for n in neighbors:
            arrow = f"--[{n['relation']}]-->" if n["direction"] == "outbound" else f"<--[{n['relation']}]--"
            lines.append(f"  {name} {arrow} {n['entity']}")

    return "\n".join(lines)

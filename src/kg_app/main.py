from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.knowledge_graph import add_entity, add_relation, query_entity, get_neighbors, _load, _save

app = FastAPI(title="Knowledge Graph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EntityIn(BaseModel):
    name: str
    type: str
    attributes: dict = {}


class RelationIn(BaseModel):
    from_entity: str
    relation: str
    to_entity: str


@app.get("/graph")
def get_graph():
    return _load()


@app.post("/entity", status_code=201)
def create_entity(body: EntityIn):
    if query_entity(body.name):
        raise HTTPException(status_code=409, detail=f"Entity '{body.name}' already exists")
    add_entity(body.name, body.type, body.attributes)
    return {"ok": True}


@app.post("/relation", status_code=201)
def create_relation(body: RelationIn):
    add_relation(body.from_entity, body.relation, body.to_entity)
    return {"ok": True}


@app.delete("/entity/{name}")
def delete_entity(name: str):
    graph = _load()
    if name not in graph["entities"]:
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found")
    del graph["entities"][name]
    graph["relations"] = [
        r for r in graph["relations"]
        if r["from"] != name and r["to"] != name
    ]
    _save(graph)
    return {"ok": True}

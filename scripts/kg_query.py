#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.knowledge_graph import add_entity, add_relation, export_context, query_entity, get_neighbors, _load

parser = argparse.ArgumentParser(description="Knowledge graph CLI")
sub = parser.add_subparsers(dest="cmd")

q = sub.add_parser("query", help="Look up an entity")
q.add_argument("entity")

ctx = sub.add_parser("context", help="Export full context for an entity")
ctx.add_argument("entity")

nb = sub.add_parser("neighbors", help="List relations for an entity")
nb.add_argument("entity")

ae = sub.add_parser("add-entity", help="Add a new entity")
ae.add_argument("name")
ae.add_argument("type")

ar = sub.add_parser("add-relation", help="Add a relation")
ar.add_argument("from_entity")
ar.add_argument("relation")
ar.add_argument("to_entity")

sub.add_parser("list", help="List all entities")

args = parser.parse_args()

if args.cmd == "query":
    result = query_entity(args.entity)
    print(result if result else f"Not found: {args.entity}")

elif args.cmd == "context":
    print(export_context(args.entity))

elif args.cmd == "neighbors":
    for n in get_neighbors(args.entity):
        print(n)

elif args.cmd == "add-entity":
    add_entity(args.name, args.type)
    print(f"Added entity: {args.name}")

elif args.cmd == "add-relation":
    add_relation(args.from_entity, args.relation, args.to_entity)
    print(f"Added: {args.from_entity} --[{args.relation}]--> {args.to_entity}")

elif args.cmd == "list":
    graph = _load()
    for name, data in graph["entities"].items():
        print(f"{name} ({data['type']})")

else:
    parser.print_help()

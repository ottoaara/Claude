# Claude Project

## Overview
This project uses the Anthropic Claude API.

## Project Rules
- Be concise
- Run tests before done

## Project Structure
```
Claude/
├── CLAUDE.md
├── README.md
├── .gitignore
├── requirements.txt
├── _claude.py           # Entry point / scratch
├── .claude/             # Claude configuration & context
│   ├── settings.json
│   ├── hooks.json
│   ├── commands/        # Custom slash commands
│   ├── agents/          # Reusable AI agent definitions
│   └── skills/          # Reusable instruction packs
├── src/                 # Source code
│   └── __init__.py
├── tests/               # Tests
│   └── __init__.py
├── docs/                # Project documentation
├── memory/              # Long-term project notes
└── scripts/             # Helper scripts & tools
```

## Setup
```bash
# Activate virtual environment
source /Users/aaronotto/.local/share/virtualenvs/ice_breaker-tUk_0iHV/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables
Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Knowledge Graph
Structured context is stored in `memory/knowledge_graph/graph.json` as entities and typed relations.

- Module: `src/knowledge_graph.py` — `add_entity`, `add_relation`, `query_entity`, `get_neighbors`, `export_context`
- CLI: `python scripts/kg_query.py <cmd>` — commands: `list`, `query <name>`, `context <name>`, `neighbors <name>`, `add-entity <name> <type>`, `add-relation <from> <rel> <to>`

Load context for a session: `python scripts/kg_query.py context Aaron`

## Commands
- Run tests: `pytest tests/`

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

## Commands
- Run tests: `pytest tests/`

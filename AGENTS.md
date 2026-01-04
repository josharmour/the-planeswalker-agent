AGENTS.md

Operational Directives for AI Agents (Jules, Gemini) working on Project Antigravity.

Project Context

This is The Planeswalker Agent, a LangGraph-based AI designed to solve the Magic: The Gathering metagame.

Primary Goal: Bridge semantic understanding (card text) with statistical analysis (EDHREC/17Lands).

Architecture: Python 3.11+, LangGraph, ChromaDB, NetworkX.

Coding Standards

Type Hinting: All functions must use Python typing.

No Hallucinations: When querying card data, ALWAYS default to the local Vector DB or Scryfall API. Do not guess card text.

Modular Tools: Keep tools (Data Layer) separate from logic (Cognitive Layer).

Error Handling: All API calls (Scryfall, EDHREC) must have exponential backoff and retry logic.

Environment Interaction

Virtual Env: Always ensure venv is active before running scripts.

Secrets: Never print API keys to console. Use python-dotenv.

Data Persistence: Store large datasets (JSON/CSV) in the data/ folder, which is .gitignored.

Critical Workflows

Ingestion: Run python ingest_data.py to refresh card data.

Agent Test: Run python mtg_agent.py to test the routing logic.
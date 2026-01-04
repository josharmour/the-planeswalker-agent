The Planeswalker Agent

An Agentic AI Domain Expert for Magic: The Gathering

Project Codename: Antigravity Module Alpha Architecture: LangGraph Multi-Agent System

Overview

The Planeswalker Agent is an AI system designed to "solve" the Magic: The Gathering metagame by combining static rules knowledge, dynamic metagame statistics (EDHREC/17Lands), and probabilistic gameplay simulation.

Architecture

The system uses a StateGraph workflow:

Router: Determines if the query is Constructed (Commander/Modern) or Limited (Draft/Sealed).

Data Layer:

Oracle: Vector DB (Chroma) for semantic card search.

Metagame: API wrappers for EDHREC and 17Lands.

Cognitive Layer:

Synergy Graph: NetworkX graph linking cards by mechanical synergy.

Simulator: Monte Carlo engine for checking mana curves and "goldfishing".

Getting Started

1. Environment Setup

Initialize the repo and install dependencies:

git init
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


2. Data Ingestion (Sprint 1)

Download the latest Oracle card data from Scryfall and populate the local cache:

python ingest_data.py


3. Testing Metagame Integrations (Sprint 2)

Test EDHREC and 17Lands API integrations:

python test_metagame.py


4. Running the Agent

The agent can run in two modes:

**Interactive Mode:**
python mtg_agent.py

**Single Query Mode:**
python mtg_agent.py "your question here"


Example Queries:
- "Find me cards that draw when they enter the battlefield"
- "What are good cards for an Atraxa deck?"
- "What's the best color pair in MKM draft?"
- "Show me powerful Commander staples"


How It Works

The agent uses a LangGraph StateGraph workflow:

1. Router: Classifies your query as Constructed (Commander) or Limited (Draft/Sealed)
2. Oracle: Performs semantic card search using ChromaDB vector database
3. Metagame: Fetches relevant statistics from EDHREC (Constructed) or 17Lands (Limited)
4. Synthesizer: Combines all results into a comprehensive response

All data is cached locally for offline usage and faster responses.


Roadmap

[x] Project Initialization

[x] Sprint 1: Scryfall Data & Vector DB

[x] Sprint 2: EDHREC & 17Lands Integration

[x] LangGraph Agent Implementation

[ ] Sprint 3: Synergy Graph Implementation

[ ] Sprint 4: Simulation Engine

Collaborators

User: Lead Architect

Jules: Co-Pilot / Agent

Gemini: Model Support

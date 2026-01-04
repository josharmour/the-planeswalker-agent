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


3. Running the Agent

Start the agent in CLI mode:

python mtg_agent.py


Roadmap

[x] Project Initialization

[x] Sprint 1: Scryfall Data & Vector DB

[ ] Sprint 2: EDHREC & 17Lands Integration

[ ] Sprint 3: Synergy Graph Implementation

[ ] Sprint 4: Simulation Engine

Collaborators

User: Lead Architect

Jules: Co-Pilot / Agent

Gemini: Model Support

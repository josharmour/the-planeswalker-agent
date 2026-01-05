The Planeswalker Agent

An Agentic AI Domain Expert for Magic: The Gathering

Project Codename: Antigravity Module Beta Architecture: LangGraph Multi-Agent System

Overview

The Planeswalker Agent is an AI system designed to "solve" the Magic: The Gathering metagame by combining static rules knowledge, dynamic metagame statistics (EDHREC/17Lands/MTGGoldfish), and probabilistic gameplay simulation.

Architecture

The system uses a StateGraph workflow:

Router: Determines if the query is Constructed (Commander/Modern) or Limited (Draft/Sealed).

Data Layer:

Oracle: Vector DB (Chroma) for semantic card search.

Metagame: API wrappers for EDHREC (Commander), 17Lands (Limited), and MTGGoldfish (Competitive Formats).

Cognitive Layer:

Synergy Graph: NetworkX graph linking cards by mechanical synergy.

Simulator: Monte Carlo engine for checking mana curves and "goldfishing" with realistic mana tracking.

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


3. Building Synergy Graph (Sprint 3)

Build the card synergy graph using NetworkX:

python build_synergy_graph.py


4. Testing Components

Test metagame integrations:
python test_metagame.py

Test synergy detection:
python test_synergy.py

Test Monte Carlo simulation:
python test_simulator.py


5. Running the Agent

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
- "What's the best Standard deck right now?"


How It Works

The agent uses a LangGraph StateGraph workflow:

1. Router: Classifies your query as Constructed (Commander) or Limited (Draft/Sealed)
2. Oracle: Performs semantic card search using ChromaDB vector database with query preprocessing
3. Synergy: Analyzes card interactions using NetworkX graph
4. Metagame: Fetches relevant statistics from EDHREC, 17Lands, or MTGGoldfish
5. Synthesizer: Combines all results into a comprehensive response

All data is cached locally for offline usage and faster responses.

The agent now provides:
- Semantic card search (currently TF-IDF based)
- Card synergy recommendations
- Combo detection
- Deck building suggestions
- Live metagame statistics
- Monte Carlo simulation for deck testing with realistic mana tracking


Roadmap

[x] Project Initialization

[x] Sprint 1: Scryfall Data & Vector DB

[x] Sprint 2: EDHREC & 17Lands Integration

[x] LangGraph Agent Implementation

[x] Sprint 3: Synergy Graph Implementation

[x] Sprint 4: Simulation Engine

[x] Performance Optimization & Caching

[x] Competitive Metagame Integration (MTGGoldfish)


Features

Data Layer:
- Scryfall Oracle card database with semantic search (ChromaDB + TF-IDF)
- EDHREC Commander metagame statistics with caching
- 17Lands Limited format statistics (Draft/Sealed)
- MTGGoldfish integration for competitive format metagame data (Standard, Modern, etc.) with caching

Cognitive Layer:
- NetworkX synergy graph for card interaction analysis
- Monte Carlo simulation engine for deck testing
- Mana curve analysis and optimization
- Opening hand simulation with mulligan decisions
- Goldfishing (turn-by-turn gameplay simulation)
- Realistic mana tracking via `mana_utils`

Agent Layer:
- LangGraph StateGraph workflow orchestration
- Intelligent query routing (Constructed vs Limited)
- Multi-source data synthesis
- Interactive and single-query CLI modes

Performance & Improvements
- **Singleton Pattern:** Resources (VectorStore, SynergyGraph) are initialized once and reused, significantly reducing query time.
- **Caching:** Extensive caching for external APIs (EDHREC, 17Lands, MTGGoldfish) to improve response times and reduce network load.
- **Query Preprocessing:** Enhanced search accuracy by mapping common user terms to database keywords (e.g., "counterspell" -> "counter target spell").

Known Limitations
- **Search Quality:** The current TF-IDF based search has limitations with semantic understanding. A migration to Sentence Transformers is recommended for better accuracy (see `EMBEDDING_COMPARISON.md`).

Documentation
- `BUG_FIXES.md`: Details recent bug fixes and search improvements.
- `PERFORMANCE_OPTIMIZATION.md`: Analysis of performance improvements and benchmark results.
- `EMBEDDING_COMPARISON.md`: Technical comparison between TF-IDF and Sentence Transformers.

Collaborators

User: Lead Architect

Jules: Co-Pilot / Agent

Gemini: Model Support

Claude: Architecture Implementation

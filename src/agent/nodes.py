"""Node functions for The Planeswalker Agent workflow."""

from typing import Dict, Any, List
from src.agent.state import AgentState
from src.data.chroma import VectorStore
from src.data.edhrec import EDHRECClient
from src.data.seventeenlands import SeventeenLandsClient


def router_node(state: AgentState) -> AgentState:
    """
    Route the query to the appropriate metagame source.

    Classifies queries as either:
    - "constructed": Commander, Modern, Standard, etc. -> EDHREC
    - "limited": Draft, Sealed -> 17Lands

    Args:
        state: Current agent state with user_query

    Returns:
        Updated state with query_type set
    """
    query = state["user_query"].lower()

    # Keywords for Limited format
    limited_keywords = [
        "draft", "sealed", "limited", "pick", "pack",
        "color pair", "archetype", "premier draft", "quick draft",
        "arena", "mtga"
    ]

    # Keywords for Constructed format
    constructed_keywords = [
        "commander", "edh", "modern", "standard", "pioneer",
        "legacy", "vintage", "deck", "build", "staple",
        "combo", "synergy"
    ]

    # Check for Limited indicators
    limited_score = sum(1 for kw in limited_keywords if kw in query)

    # Check for Constructed indicators
    constructed_score = sum(1 for kw in constructed_keywords if kw in query)

    # Default to constructed if unclear (Commander is most popular)
    if limited_score > constructed_score:
        query_type = "limited"
    else:
        query_type = "constructed"

    print(f"[Router] Classified query as: {query_type.upper()}")

    state["query_type"] = query_type
    if "metadata" not in state:
        state["metadata"] = {}
    state["metadata"]["routing_scores"] = {
        "limited": limited_score,
        "constructed": constructed_score
    }

    return state


def oracle_node(state: AgentState) -> AgentState:
    """
    Perform semantic card search using ChromaDB.

    Searches the vector database for cards relevant to the query.

    Args:
        state: Current agent state with user_query

    Returns:
        Updated state with oracle_results
    """
    query = state["user_query"]
    print(f"[Oracle] Searching card database for: '{query}'")

    try:
        store = VectorStore()

        # Perform semantic search
        results = store.query_similar(query, n_results=5)

        # Format results
        oracle_results = []
        if results and 'ids' in results and len(results['ids']) > 0:
            ids = results['ids'][0]
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]

            for i in range(len(ids)):
                oracle_results.append({
                    "id": ids[i],
                    "name": metadatas[i].get("name", "Unknown"),
                    "type_line": metadatas[i].get("type_line", ""),
                    "text": documents[i],
                    "metadata": metadatas[i]
                })

            print(f"[Oracle] Found {len(oracle_results)} relevant cards")
        else:
            print("[Oracle] No cards found")

        state["oracle_results"] = oracle_results

    except Exception as e:
        print(f"[Oracle] Error: {e}")
        state["oracle_results"] = []

    return state


def constructed_metagame_node(state: AgentState) -> AgentState:
    """
    Fetch Constructed (Commander) metagame data from EDHREC.

    Only runs if query_type is "constructed".

    Args:
        state: Current agent state

    Returns:
        Updated state with metagame_results from EDHREC
    """
    if state.get("query_type") != "constructed":
        print("[Constructed] Skipping (not a constructed query)")
        return state

    print("[Constructed] Fetching EDHREC data...")

    try:
        client = EDHRECClient()

        # Check if query mentions a specific commander
        query = state["user_query"].lower()
        oracle_results = state.get("oracle_results", [])

        metagame_data = {}

        # If we found legendary creatures, try to get their EDHREC data
        commanders_found = []
        for card in oracle_results[:3]:  # Check top 3 results
            type_line = card.get("type_line", "").lower()
            if "legendary" in type_line and "creature" in type_line:
                commanders_found.append(card["name"])

        if commanders_found:
            print(f"[Constructed] Found potential commanders: {commanders_found}")
            # Get data for the first commander
            commander_name = commanders_found[0]
            commander_data = client.get_commander_page(commander_name)
            metagame_data["commander_recommendations"] = commander_data
        else:
            # Get general top commanders
            top_commanders = client.get_top_commanders(timeframe="week")
            metagame_data["top_commanders"] = top_commanders[:10]

        state["metagame_results"] = metagame_data
        print(f"[Constructed] Retrieved metagame data")

    except Exception as e:
        print(f"[Constructed] Error: {e}")
        state["metagame_results"] = {"error": str(e)}

    return state


def limited_metagame_node(state: AgentState) -> AgentState:
    """
    Fetch Limited (Draft/Sealed) metagame data from 17Lands.

    Only runs if query_type is "limited".

    Args:
        state: Current agent state

    Returns:
        Updated state with metagame_results from 17Lands
    """
    if state.get("query_type") != "limited":
        print("[Limited] Skipping (not a limited query)")
        return state

    print("[Limited] Fetching 17Lands data...")

    try:
        client = SeventeenLandsClient()

        # Extract set code from query if present
        # Common recent sets: MKM, LCI, WOE, etc.
        query = state["user_query"].upper()
        set_codes = ["MKM", "LCI", "WOE", "LTR", "MOM"]

        expansion = None
        for code in set_codes:
            if code in query:
                expansion = code
                break

        # Default to most recent set if none specified
        if not expansion:
            expansion = "MKM"  # Murders at Karlov Manor

        metagame_data = {}

        # Get color pair data
        color_pairs = client.get_color_pair_data(expansion=expansion, format_type="PremierDraft")
        metagame_data["color_pairs"] = color_pairs

        # Get set stats
        set_stats = client.get_set_stats(expansion=expansion, format_type="PremierDraft")
        metagame_data["set_stats"] = set_stats

        state["metagame_results"] = metagame_data
        print(f"[Limited] Retrieved metagame data for {expansion}")

    except Exception as e:
        print(f"[Limited] Error: {e}")
        state["metagame_results"] = {"error": str(e)}

    return state


def synthesizer_node(state: AgentState) -> AgentState:
    """
    Synthesize results from Oracle and Metagame into a final response.

    Combines semantic card search results with metagame statistics
    to provide a comprehensive answer.

    Args:
        state: Current agent state with all results

    Returns:
        Updated state with final_response
    """
    print("[Synthesizer] Combining results...")

    query = state["user_query"]
    query_type = state.get("query_type", "unknown")
    oracle_results = state.get("oracle_results", [])
    metagame_results = state.get("metagame_results", {})

    response_parts = []

    # Header
    response_parts.append(f"Query: {query}")
    response_parts.append(f"Type: {query_type.title()}")
    response_parts.append("")

    # Oracle results
    if oracle_results:
        response_parts.append("=== Relevant Cards ===")
        for i, card in enumerate(oracle_results[:5], 1):
            response_parts.append(f"\n{i}. {card['name']}")
            response_parts.append(f"   Type: {card['type_line']}")
            if "mana_cost" in card.get("metadata", {}):
                response_parts.append(f"   Cost: {card['metadata']['mana_cost']}")
        response_parts.append("")
    else:
        response_parts.append("No relevant cards found in database.")
        response_parts.append("")

    # Metagame results
    if metagame_results and "error" not in metagame_results:
        if query_type == "constructed":
            response_parts.append("=== Commander Metagame ===")

            if "commander_recommendations" in metagame_results:
                cmd_data = metagame_results["commander_recommendations"]
                response_parts.append(f"\nCommander: {cmd_data.get('commander', 'Unknown')}")

                cards = cmd_data.get("cards", [])
                if cards:
                    response_parts.append("\nTop Recommendations:")
                    for card in cards[:5]:
                        response_parts.append(f"  - {card.get('name', 'Unknown')}")

                themes = cmd_data.get("themes", [])
                if themes:
                    response_parts.append(f"\nCommon Themes: {', '.join(themes[:5])}")

            elif "top_commanders" in metagame_results:
                commanders = metagame_results["top_commanders"]
                if commanders:
                    response_parts.append("\nTrending Commanders:")
                    for cmd in commanders[:5]:
                        response_parts.append(f"  - {cmd.get('name', 'Unknown')}")

        elif query_type == "limited":
            response_parts.append("=== Limited Metagame ===")

            color_pairs = metagame_results.get("color_pairs", [])
            if color_pairs:
                response_parts.append("\nColor Pair Win Rates:")
                # Sort by win rate if available
                sorted_pairs = sorted(
                    color_pairs,
                    key=lambda x: x.get("win_rate", 0),
                    reverse=True
                )
                for pair in sorted_pairs[:5]:
                    win_rate = pair.get("win_rate", 0)
                    if win_rate > 0:
                        response_parts.append(
                            f"  {pair['colors']} ({pair['name']}): {win_rate:.1%}"
                        )
                    else:
                        response_parts.append(
                            f"  {pair['colors']} ({pair['name']})"
                        )

            set_stats = metagame_results.get("set_stats", {})
            if set_stats and "expansion" in set_stats:
                response_parts.append(f"\nSet: {set_stats['expansion']}")

        response_parts.append("")

    # Footer
    response_parts.append("---")
    response_parts.append("Powered by: Scryfall, ChromaDB, EDHREC, 17Lands")

    final_response = "\n".join(response_parts)
    state["final_response"] = final_response

    print("[Synthesizer] Response generated")

    return state

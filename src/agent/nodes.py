from typing import Dict, Any, List
from src.agent.state import AgentState
from src.data.chroma import get_vector_store
from src.data.edhrec import EDHRECClient
from src.data.seventeenlands import SeventeenLandsClient
from src.data.mtggoldfish import MTGGoldfishClient
from src.cognitive import get_synergy_graph
from src.config import config


def router_node(state: AgentState) -> AgentState:
    """
    Route the query to the appropriate metagame source.

    Classifies queries as:
    - "limited": Draft, Sealed -> 17Lands
    - "commander": Commander/EDH -> EDHREC
    - "standard", "modern", "pioneer", "legacy", "pauper" -> MTGGoldfish
    - "constructed": Generic constructed -> Default to Commander (EDHREC)
    """
    query = state["user_query"].lower()

    # Keywords for Limited format
    limited_keywords = [
        "draft", "sealed", "limited", "pick", "pack",
        "color pair", "archetype", "premier draft", "quick draft",
        "arena", "mtga"
    ]

    # Explicit format keywords
    formats = {
        "standard": ["standard"],
        "modern": ["modern"],
        "pioneer": ["pioneer"],
        "legacy": ["legacy"],
        "pauper": ["pauper"],
        "commander": ["commander", "edh"],
        "limited": limited_keywords
    }

    # Check for specific format mentions first
    query_type = "constructed"  # Default
    
    # Check simple formats first
    for fmt, keywords in formats.items():
        if any(kw in query for kw in keywords):
            query_type = fmt
            break
            
    print(f"[Router] Classified query as: {query_type.upper()}")

    state["query_type"] = query_type
    if "metadata" not in state:
        state["metadata"] = {}
    
    return state


def oracle_node(state: AgentState) -> AgentState:
    """
    Perform semantic card search using ChromaDB.
    """
    query = state["user_query"]
    print(f"[Oracle] Searching card database for: '{query}'")

    try:
        store = get_vector_store()

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
    Fetch Constructed metagame data.
    
    Supports:
    - Commander -> EDHREC
    - Standard, Modern, Pioneer -> MTGGoldfish
    """
    query_type = state.get("query_type", "constructed")
    user_query = state.get("user_query", "").lower()
    
    # If limited, skip
    if query_type == "limited":
        return state

    print(f"[{query_type.title()}] Fetching metagame data...")
    state["metagame_results"] = {}

    try:
        # CASE 1: Commander / Generic Constructed -> EDHREC
        if query_type in ["commander", "constructed"]:
            client = EDHRECClient()

            # Check if query mentions a specific commander
            oracle_results = state.get("oracle_results", [])
            commanders_found = []
            
            for card in oracle_results[:3]:
                type_line = card.get("type_line", "").lower()
                if "legendary" in type_line and "creature" in type_line:
                    commanders_found.append(card["name"])

            if commanders_found:
                print(f"[Commander] Found potential commanders: {commanders_found}")
                commander_name = commanders_found[0]
                commander_data = client.get_commander_page(commander_name)
                state["metagame_results"]["commander_recommendations"] = commander_data
            else:
                top_commanders = client.get_top_commanders(timeframe="week")
                state["metagame_results"]["top_commanders"] = top_commanders[:10]
                
        # CASE 2: Competitive Formats -> MTGGoldfish
        elif query_type in ["standard", "modern", "pioneer", "legacy", "pauper"]:
            client = MTGGoldfishClient()
            decks = client.get_metagame(query_type)
            state["metagame_results"]["top_decks"] = decks
            print(f"[{query_type.title()}] Found {len(decks)} top decks")
            
            # --- CONTEXT AWARENESS FOR DECKS ---
            target_deck = None
            
            # Scenario A: "What is the best deck?"
            if "best" in user_query or "top" in user_query:
                if decks:
                    target_deck = decks[0]
                    print(f"[{query_type.title()}] 'Best' deck requested. Targeting: {target_deck['name']}")

            # Scenario B: "Tell me about [Deck Name]"
            # We check if any deck name from our results is in the user query
            else:
                for deck in decks:
                    # Simple fuzzy matching: check if prominent parts of deck name appear in query
                    # e.g., "Dimir Midrange" -> check "dimir" and "midrange" or exact string
                    clean_name = deck["name"].lower()
                    if clean_name in user_query:
                        target_deck = deck
                        print(f"[{query_type.title()}] Specific deck requested: {deck['name']}")
                        break
            
            # Fetch Decklist if we have a target
            if target_deck and "url" in target_deck:
                print(f"[{query_type.title()}] Fetching deck list for {target_deck['name']}...")
                deck_list = client.get_deck_list(target_deck["url"])
                state["metagame_results"]["focus_deck"] = {
                    "info": target_deck,
                    "list": deck_list
                }

    except Exception as e:
        print(f"[{query_type.title()}] Error: {e}")
        state["metagame_results"] = {"error": str(e)}

    return state


def limited_metagame_node(state: AgentState) -> AgentState:
    """
    Fetch Limited (Draft/Sealed) metagame data from 17Lands.
    """
    if state.get("query_type") != "limited":
        return state

    print("[Limited] Fetching 17Lands data...")

    try:
        client = SeventeenLandsClient()
        query = state["user_query"].upper()
        # Simple expansion detection
        set_codes = ["MKM", "LCI", "WOE", "LTR", "MOM"]
        expansion = next((code for code in set_codes if code in query), "MKM")

        metagame_data = {}
        metagame_data["color_pairs"] = client.get_color_pair_data(expansion=expansion, format_type="PremierDraft")
        metagame_data["set_stats"] = client.get_set_stats(expansion=expansion, format_type="PremierDraft")

        state["metagame_results"] = metagame_data

    except Exception as e:
        print(f"[Limited] Error: {e}")
        state["metagame_results"] = {"error": str(e)}

    return state


def synergy_node(state: AgentState) -> AgentState:
    """
    Find card synergies using the synergy graph.
    """
    oracle_results = state.get("oracle_results", [])

    if not oracle_results:
        state["synergy_results"] = None
        return state

    print("[Synergy] Analyzing card interactions...")

    try:
        graph = get_synergy_graph()
        if graph is None:
            print("[Synergy] Synergy graph not available.")
            state["synergy_results"] = None
            return state

        synergy_results = {}
        card_names = [card["name"] for card in oracle_results[:3]]

        for card_name in card_names:
            synergies = graph.find_synergies_for_card(card_name, top_n=5)
            if synergies:
                synergy_results[card_name] = [
                    {
                        "card": syn_card,
                        "score": score,
                        "types": syn_types
                    }
                    for syn_card, score, syn_types in synergies
                ]

        state["synergy_results"] = synergy_results

    except Exception as e:
        print(f"[Synergy] Error: {e}")
        state["synergy_results"] = None

    return state


def synthesizer_node(state: AgentState) -> AgentState:
    """
    Synthesize results into a final response.

    If an LLM provider is configured (OpenAI/Anthropic), uses AI to generate
    a natural language response. Otherwise, falls back to template-based formatting.
    """
    print("[Synthesizer] Combining results...")

    query = state["user_query"]
    query_type = state.get("query_type", "unknown")
    oracle_results = state.get("oracle_results", [])
    synergy_results = state.get("synergy_results", {})
    metagame_results = state.get("metagame_results", {})

    # Try LLM-based synthesis if configured
    llm_provider = config.get_active_llm_provider()
    if llm_provider:
        print(f"[Synthesizer] Using LLM provider: {llm_provider}")
        try:
            from src.data.openai_realtime import synthesize_with_llm
            llm_response = synthesize_with_llm(
                user_query=query,
                oracle_results=oracle_results or [],
                synergy_results=synergy_results,
                metagame_results=metagame_results,
                query_type=query_type,
            )
            if llm_response:
                state["final_response"] = llm_response
                print("[Synthesizer] LLM response generated successfully")
                return state
        except Exception as e:
            print(f"[Synthesizer] LLM synthesis failed: {e}, falling back to template")

    # Fall back to template-based response
    print("[Synthesizer] Using template-based response")

    response_parts = []
    response_parts.append(f"Query: {query}")
    response_parts.append(f"Type: {query_type.title()}")
    response_parts.append("")
    
    # Check if we have a "Focus Deck" (Detailed View)
    focus_deck = metagame_results.get("focus_deck")

    # 1. Oracle Results (Context)
    # Only show if they seem relevant or if we didn't find specific metagame data
    # If we have a focus deck, we might hide this to reduce noise, or keep it if it's small.
    if oracle_results and not focus_deck:
        response_parts.append("=== Relevant Cards ===")
        for i, card in enumerate(oracle_results[:3], 1):
             response_parts.append(f"{i}. {card['name']} ({card['type_line']})")
        response_parts.append("")

    # 2. Metagame Results (The Meat)
    if metagame_results and "error" not in metagame_results:
        
        # COMMANDER RECS
        if "commander_recommendations" in metagame_results:
            cmd_data = metagame_results["commander_recommendations"]
            response_parts.append(f"=== Commander: {cmd_data.get('commander', 'Unknown')} ===")
            
            themes = cmd_data.get("themes", [])
            if themes:
                response_parts.append(f"Themes: {', '.join(themes[:3])}")
            
            cards = cmd_data.get("cards", [])
            if cards:
                response_parts.append("\nTop Synergies:")
                for card in cards[:5]:
                    response_parts.append(f"  - {card.get('name', 'Unknown')}")

        # TOP COMMANDERS
        elif "top_commanders" in metagame_results:
            response_parts.append("=== Trending Commanders ===")
            for cmd in metagame_results["top_commanders"][:5]:
                response_parts.append(f"  - {cmd.get('name', 'Unknown')}")

        # FOCUS DECK (Detailed List)
        elif focus_deck:
            info = focus_deck.get("info", {})
            deck_list = focus_deck.get("list", {})
            
            response_parts.append(f"=== Deck Focus: {info.get('name', 'Unknown')} ===")
            response_parts.append(f"Meta Share: {info.get('meta_share', 'N/A')}")
            if info.get('colors'):
                response_parts.append(f"Colors: {', '.join(info['colors'])}")
            
            response_parts.append("\n== Mainboard ==")
            # Show top 15 cards to avoid spamming 60 lines, or just show spells?
            # Let's show everything but compacted if possible.
            # For now, just listing them.
            if deck_list.get("mainboard"):
                for line in deck_list["mainboard"][:20]: # Limit to top 20 lines for brevity in UI
                    response_parts.append(f"  {line}")
                if len(deck_list["mainboard"]) > 20:
                    response_parts.append(f"  ... and {len(deck_list['mainboard']) - 20} more cards")
            
            if deck_list.get("sideboard"):
                response_parts.append("\n== Sideboard ==")
                for line in deck_list["sideboard"]:
                    response_parts.append(f"  {line}")
            
            response_parts.append("")

        # META DECKS LIST (General View)
        elif "top_decks" in metagame_results:
            response_parts.append(f"=== {query_type.title()} Metagame ===")
            decks = metagame_results["top_decks"]
            if decks:
                for i, deck in enumerate(decks[:8], 1):
                    share = deck.get('meta_share', '').replace('\n', '').strip()
                    response_parts.append(f"{i}. {deck['name']}")
                    response_parts.append(f"   Share: {share}")
                    response_parts.append("")
            else:
                response_parts.append("No active meta decks found.")

        # LIMITED
        elif "color_pairs" in metagame_results:
            response_parts.append("=== Limited Metagame ===")
            pairs = sorted(metagame_results["color_pairs"], key=lambda x: x.get("win_rate", 0), reverse=True)
            for pair in pairs[:5]:
                response_parts.append(f"  {pair['colors']}: {pair.get('win_rate', 0):.1%}")

    # 3. Synergy (Bonus)
    if synergy_results:
        response_parts.append("=== Card Interactions ===")
        for card_name, synergies in synergy_results.items():
            if synergies:
                response_parts.append(f"For {card_name}:")
                for syn in synergies[:2]:
                    response_parts.append(f"  + {syn['card']}")
        response_parts.append("")

    response_parts.append("---")
    response_parts.append(f"Powered by: Scryfall, {query_type.title()} Sources")

    state["final_response"] = "\n".join(response_parts)
    print("[Synthesizer] Response generated")

    return state

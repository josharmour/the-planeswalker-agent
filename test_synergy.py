"""Test script for synergy graph functionality."""

from src.cognitive import SynergyGraph


def main():
    """Test synergy graph with sample cards."""
    print("=" * 60)
    print("SYNERGY GRAPH TEST SUITE")
    print("=" * 60)
    print()

    # Load synergy graph
    graph = SynergyGraph()

    if not graph.load():
        print("Error: Synergy graph not found.")
        print("Please run 'python build_synergy_graph.py' first.")
        return

    # Display stats
    stats = graph.stats()
    print("Graph Statistics:")
    print(f"  Cards in graph: {stats['num_cards']}")
    print(f"  Synergy relationships: {stats['num_synergies']}")
    print(f"  Avg synergies per card: {stats['avg_synergies_per_card']:.1f}")
    print(f"  Graph density: {stats['density']:.4f}")
    print()

    # Test 1: Find synergies for specific cards
    print("Test 1: Finding synergies for specific cards")
    print("-" * 60)

    test_cards = ["Mulldrifter", "Lightning Bolt", "Birds of Paradise"]

    for card_name in test_cards:
        print(f"\n{card_name}:")
        synergies = graph.find_synergies_for_card(card_name, top_n=5)

        if not synergies:
            print("  No synergies found")
            continue

        for syn_card, score, syn_types in synergies:
            types_str = ", ".join(syn_types) if syn_types else "general"
            print(f"  - {syn_card} (score: {score:.2f}, types: {types_str})")

    print()

    # Test 2: Find combo pieces
    print("Test 2: Finding strong combo pieces (score >= 0.5)")
    print("-" * 60)

    for card_name in ["Birds of Paradise", "Llanowar Elves"]:
        combos = graph.find_combo_pieces(card_name, threshold=0.5)

        if combos:
            print(f"\n{card_name} combos with:")
            for combo_card in combos[:5]:
                print(f"  - {combo_card}")
        else:
            print(f"\n{card_name}: No strong combos found (threshold = 0.5)")

    print()

    # Test 3: Cluster recommendations
    print("Test 3: Deck recommendations based on seed cards")
    print("-" * 60)

    seed_cards = ["Mulldrifter", "Counterspell"]
    print(f"\nSeed cards: {', '.join(seed_cards)}")
    print("Recommended additions:")

    recommendations = graph.get_cluster_recommendations(seed_cards, top_n=5)

    for card, score in recommendations:
        print(f"  - {card} (score: {score:.2f})")

    print()
    print("=" * 60)
    print("Test suite complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

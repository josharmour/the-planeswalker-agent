"""Test script for the Monte Carlo simulation engine."""

from src.cognitive.simulator import Deck, ManaCurveAnalyzer, GoldfishSimulator, MonteCarloSimulator


def create_sample_deck() -> list:
    """Create a sample 60-card deck for testing."""
    deck = []

    # 24 Lands
    for i in range(24):
        deck.append({
            "name": f"Island {i+1}",
            "type_line": "Basic Land — Island",
            "cmc": 0,
            "produced_mana": ["U"],
            "oracle_text": "{T}: Add {U}."
        })

    # 1-drops (4 cards)
    for i in range(4):
        deck.append({
            "name": f"One Drop {i+1}",
            "type_line": "Creature",
            "cmc": 1,
            "mana_cost": "{U}"
        })

    # 2-drops (8 cards)
    for i in range(8):
        deck.append({
            "name": f"Two Drop {i+1}",
            "type_line": "Creature",
            "cmc": 2,
            "mana_cost": "{1}{U}"
        })

    # 3-drops (10 cards)
    for i in range(10):
        deck.append({
            "name": f"Three Drop {i+1}",
            "type_line": "Creature",
            "cmc": 3,
            "mana_cost": "{2}{U}"
        })

    # 4-drops (8 cards)
    for i in range(8):
        deck.append({
            "name": f"Four Drop {i+1}",
            "type_line": "Creature",
            "cmc": 4,
            "mana_cost": "{2}{U}{U}"
        })

    # 5-drops (4 cards)
    for i in range(4):
        deck.append({
            "name": f"Five Drop {i+1}",
            "type_line": "Creature",
            "cmc": 5,
            "mana_cost": "{3}{U}{U}"
        })

    # 6-drops (2 cards)
    for i in range(2):
        deck.append({
            "name": f"Six Drop {i+1}",
            "type_line": "Creature",
            "cmc": 6,
            "mana_cost": "{4}{U}{U}"
        })

    return deck


def test_mana_curve_analysis():
    """Test mana curve analyzer."""
    print("=" * 60)
    print("TEST 1: MANA CURVE ANALYSIS")
    print("=" * 60)
    print()

    deck = create_sample_deck()
    analysis = ManaCurveAnalyzer.analyze_curve(deck)

    print(f"Total Cards: {analysis['total_cards']}")
    print(f"Lands: {analysis['lands']}")
    print(f"Spells: {analysis['spells']}")
    print(f"Land Ratio: {analysis['land_ratio']:.1%}")
    print(f"Average CMC: {analysis['avg_cmc']:.2f}")
    print(f"Median CMC: {analysis['median_cmc']:.1f}")
    print()
    print("CMC Distribution:")
    for cmc in sorted(analysis['cmc_distribution'].keys()):
        count = analysis['cmc_distribution'][cmc]
        print(f"  {int(cmc)}: {'█' * count} ({count})")
    print()


def test_opening_hand_simulation():
    """Test opening hand simulator."""
    print("=" * 60)
    print("TEST 2: OPENING HAND SIMULATION")
    print("=" * 60)
    print()

    deck_cards = create_sample_deck()
    deck = Deck(deck_cards)
    simulator = GoldfishSimulator(deck)

    print("Simulating 3 sample opening hands:\n")
    for i in range(3):
        result = simulator.simulate_opening_hand()
        print(f"Hand {i+1}:")
        print(f"  Lands: {result['lands']}")
        print(f"  Spells: {result['spells']}")
        print(f"  Keep: {'Yes' if result['keep'] else 'No (would mulligan)'}")
        print()


def test_goldfish_simulation():
    """Test goldfish simulator."""
    print("=" * 60)
    print("TEST 3: GOLDFISH SIMULATION")
    print("=" * 60)
    print()

    deck_cards = create_sample_deck()
    deck = Deck(deck_cards)
    simulator = GoldfishSimulator(deck)

    print("Simulating first 5 turns of one game:\n")
    result = simulator.simulate_turns(num_turns=5)

    for turn_data in result['turns']:
        print(f"Turn {turn_data['turn']}:")
        print(f"  Land played: {turn_data['land_played']}")
        print(f"  Lands in play: {turn_data['lands_in_play']}")
        print(f"  Available mana: {turn_data['available_mana']}")
        print(f"  Spells cast: {turn_data['spells_cast']}")
        print(f"  Cards in hand: {turn_data['cards_in_hand']}")
        print()

    print(f"Summary:")
    print(f"  Total lands played: {result['lands_played']}")
    print(f"  Total spells cast: {result['spells_cast']}")
    print(f"  Cards drawn: {result['cards_drawn']}")
    print(f"  Final hand size: {result['final_hand_size']}")
    print(f"  Cards on battlefield: {result['final_battlefield_size']}")
    print()


def test_monte_carlo_analysis():
    """Test Monte Carlo analyzer."""
    print("=" * 60)
    print("TEST 4: MONTE CARLO ANALYSIS")
    print("=" * 60)
    print()

    deck_cards = create_sample_deck()
    simulator = MonteCarloSimulator(deck_cards)

    # Run full analysis with fewer iterations for testing
    analysis = simulator.full_analysis(hand_iterations=100, goldfish_iterations=50)

    print("\nRESULTS:")
    print("-" * 60)

    # Mana curve
    print("\nMana Curve:")
    curve = analysis['mana_curve']
    print(f"  Lands: {curve['lands']} ({curve['land_ratio']:.1%})")
    print(f"  Average CMC: {curve['avg_cmc']:.2f}")

    # Opening hands
    print("\nOpening Hands (100 iterations):")
    hands = analysis['opening_hands']
    print(f"  Average lands in opening hand: {hands['avg_lands']:.2f}")
    print(f"  Keep rate (2-5 lands): {hands['keep_rate']:.1%}")
    print(f"  Land distribution: {hands['land_distribution']}")

    # Goldfish
    print("\nGoldfish Simulation (50 games, 5 turns each):")
    goldfish = analysis['goldfish']
    print(f"  Average lands played: {goldfish['avg_lands_played']:.2f}")
    print(f"  Average spells cast: {goldfish['avg_spells_cast']:.2f}")
    print(f"  Median spells cast: {goldfish['median_spells_cast']:.1f}")

    print("\n  Turn-by-turn averages:")
    for turn_key in sorted(goldfish['turn_stats'].keys()):
        turn_data = goldfish['turn_stats'][turn_key]
        turn_num = turn_key.split('_')[1]
        print(f"    Turn {turn_num}: {turn_data['avg_lands']:.1f} lands, {turn_data['avg_spells_cast']:.2f} spells cast")

    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SIMULATION ENGINE TEST SUITE")
    print("=" * 60)
    print()

    test_mana_curve_analysis()
    test_opening_hand_simulation()
    test_goldfish_simulation()
    test_monte_carlo_analysis()

    print("=" * 60)
    print("All tests complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

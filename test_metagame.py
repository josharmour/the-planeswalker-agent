"""Test script for metagame data integrations (EDHREC and 17Lands)."""

import sys
from src.data.edhrec import EDHRECClient
from src.data.seventeenlands import SeventeenLandsClient


def test_edhrec():
    """Test EDHREC client functionality."""
    print("=" * 60)
    print("Testing EDHREC Integration")
    print("=" * 60)

    client = EDHRECClient()

    # Test 1: Get top commanders
    print("\n[Test 1] Fetching top commanders...")
    try:
        commanders = client.get_top_commanders(timeframe="week")
        if commanders:
            print(f"✓ Found {len(commanders)} top commanders")
            print(f"  Top 5: {[c.get('name', 'Unknown') for c in commanders[:5]]}")
        else:
            print("⚠ No commanders found (may be due to network restrictions)")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 2: Get specific commander page
    print("\n[Test 2] Fetching commander page for 'Atraxa, Praetors Voice'...")
    try:
        commander_data = client.get_commander_page("Atraxa, Praetors Voice")
        if commander_data and "error" not in commander_data:
            print(f"✓ Successfully fetched commander data")
            print(f"  URL: {commander_data.get('url')}")
            cards = commander_data.get('cards', [])
            if cards:
                print(f"  Found {len(cards)} card recommendations")
                print(f"  Sample cards: {[c.get('name', 'Unknown') for c in cards[:3]]}")
            themes = commander_data.get('themes', [])
            if themes:
                print(f"  Themes: {themes[:5]}")
        else:
            print(f"⚠ Limited data retrieved: {commander_data.get('error', 'Unknown issue')}")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_17lands():
    """Test 17Lands client functionality."""
    print("\n" + "=" * 60)
    print("Testing 17Lands Integration")
    print("=" * 60)

    client = SeventeenLandsClient()

    # Test 1: Get general card data
    print("\n[Test 1] Fetching general card data...")
    try:
        card_data = client.get_card_data()
        if card_data and "error" not in card_data:
            print(f"✓ Successfully fetched card data")
            print(f"  Keys in response: {list(card_data.keys())[:5]}")
        else:
            print(f"⚠ Limited data: {card_data.get('error', 'Unknown issue')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 2: Get card ratings for a recent set
    print("\n[Test 2] Fetching card ratings for Murders at Karlov Manor (MKM)...")
    try:
        ratings = client.get_card_ratings(expansion="MKM", format_type="PremierDraft")
        if ratings:
            print(f"✓ Found {len(ratings)} card ratings")
            if isinstance(ratings, list) and len(ratings) > 0:
                print(f"  Sample rating keys: {list(ratings[0].keys()) if isinstance(ratings[0], dict) else 'N/A'}")
        else:
            print("⚠ No card ratings found (may be due to API changes or network restrictions)")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 3: Get color pair data
    print("\n[Test 3] Fetching color pair data for MKM...")
    try:
        color_pairs = client.get_color_pair_data(expansion="MKM", format_type="PremierDraft")
        if color_pairs:
            print(f"✓ Found {len(color_pairs)} color pairs")
            pairs_display = [f"{cp['colors']} ({cp['name']})" for cp in color_pairs[:3]]
            print(f"  Color pairs: {pairs_display}")
        else:
            print("⚠ No color pair data found")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 4: Get set stats
    print("\n[Test 4] Fetching set statistics for MKM...")
    try:
        stats = client.get_set_stats(expansion="MKM", format_type="PremierDraft")
        if stats and "error" not in stats:
            print(f"✓ Successfully fetched set stats")
            print(f"  Expansion: {stats.get('expansion')}")
            print(f"  Total cards: {stats.get('total_cards', 'Unknown')}")
        else:
            print(f"⚠ Limited stats: {stats.get('error', 'Unknown issue')}")
    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    """Run all metagame integration tests."""
    print("\n" + "=" * 60)
    print("METAGAME DATA INTEGRATION TEST SUITE")
    print("=" * 60)
    print("\nNote: Some tests may fail due to network restrictions")
    print("or changes in external APIs. Cached data will be used when available.\n")

    # Test EDHREC
    test_edhrec()

    # Test 17Lands
    test_17lands()

    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)
    print("\nNote: Both clients implement caching, so subsequent runs")
    print("will be faster and work offline using cached data.")


if __name__ == "__main__":
    main()

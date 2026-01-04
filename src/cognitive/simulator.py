"""Monte Carlo simulation engine for deck testing and analysis."""

import random
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import Counter
import statistics


class ManaUtils:
    """Utilities for complex mana calculation and checking."""

    @staticmethod
    def parse_cost(mana_cost: str) -> Dict[str, int]:
        """
        Parses mana cost string like "{3}{U}{U}" into {'C': 3, 'U': 2}.
        'C' represents generic/colorless requirement.
        """
        if not mana_cost:
            return {'C': 0}

        cost = {'C': 0, 'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0}

        # Find all {X} patterns
        symbols = re.findall(r'\{([^}]+)\}', mana_cost)

        for sym in symbols:
            if sym.isdigit():
                cost['C'] += int(sym)
            elif sym == 'X':
                pass
            elif '/' in sym:
                # Hybrid mana, e.g., {U/B}, {2/W}
                parts = sym.split('/')
                if parts[0].isdigit():
                     cost['C'] += int(parts[0])
                else:
                    # Treat {U/B} as the first color for conservative estimate
                    if parts[0] in cost:
                        cost[parts[0]] += 1
            elif sym in cost:
                cost[sym] += 1

        return cost

    @staticmethod
    def get_mana_sources(card: Dict[str, Any]) -> List[Set[str]]:
        """
        Returns a list of mana points this card can produce.
        Each point is a set of possible colors ('W','U','B','R','G','C').
        """
        produced = card.get('produced_mana')
        if not produced:
            return []

        oracle_text = card.get('oracle_text', '')

        # Regex to find "Add {X}{Y}..." (TWO or more consecutive mana symbols)
        # This distinguishes "Add {C}{G}" (2 mana) from "Add {U} or {B}" (1 mana).
        add_matches = re.findall(r'Add\s*((?:\{[WUBRGC0-9]\}){2,})', oracle_text)

        sources = []

        if add_matches:
            # Parse the first match (usually the primary ability)
            symbols = re.findall(r'\{([^}]+)\}', add_matches[0])
            for sym in symbols:
                if sym in ['W', 'U', 'B', 'R', 'G', 'C']:
                    sources.append({sym})
                elif sym.isdigit():
                     count = int(sym)
                     for _ in range(count):
                         sources.append({'C'})
        else:
            # Fallback if no specific multiple-mana quantity found but produced_mana exists
            # Assume 1 mana, capable of producing any color in produced_mana
            sources.append(set(produced))

        return sources

    @staticmethod
    def pay(mana_pool: List[Set[str]], cost: Dict[str, int]) -> bool:
        """
        Attempts to pay the cost using mana_pool.
        If successful, modifies mana_pool in-place by removing used sources and returns True.
        If unsuccessful, leaves mana_pool unchanged (or partially modified, so pass a copy!)
        """
        # Sort pool by flexibility (most restrictive first)
        mana_pool.sort(key=lambda x: len(x))

        # Check colored costs
        for color in ['W', 'U', 'B', 'R', 'G']:
            required = cost.get(color, 0)
            for _ in range(required):
                # Find a source that has this color
                found_idx = -1
                for i, source in enumerate(mana_pool):
                    if color in source:
                        found_idx = i
                        break

                if found_idx != -1:
                    mana_pool.pop(found_idx)
                else:
                    return False

        # Check generic cost
        generic_needed = cost.get('C', 0)
        if len(mana_pool) >= generic_needed:
            # Consume generic mana
            for _ in range(generic_needed):
                if mana_pool:
                    mana_pool.pop(0)
            return True
        else:
            return False


class Deck:
    """Represents a Magic: The Gathering deck for simulation."""

    def __init__(self, cards: List[Dict[str, Any]]):
        """
        Initialize a deck.

        Args:
            cards: List of card dictionaries with 'name', 'cmc', 'type_line', etc.
        """
        self.cards = cards.copy()
        self.library = cards.copy()
        self.hand: List[Dict[str, Any]] = []
        self.battlefield: List[Dict[str, Any]] = []
        self.graveyard: List[Dict[str, Any]] = []
        self.mana_pool: Dict[str, int] = {}

    def shuffle(self) -> None:
        """Shuffle the library."""
        random.shuffle(self.library)

    def draw(self, n: int = 1) -> List[Dict[str, Any]]:
        """
        Draw n cards from the library.

        Args:
            n: Number of cards to draw

        Returns:
            List of drawn cards
        """
        drawn = []
        for _ in range(n):
            if self.library:
                card = self.library.pop(0)
                self.hand.append(card)
                drawn.append(card)
        return drawn

    def mulligan(self, cards_to_keep: int) -> None:
        """
        Mulligan to n cards.

        Args:
            cards_to_keep: Number of cards to keep (typically hand_size - 1)
        """
        # Put hand back
        self.library.extend(self.hand)
        self.hand = []

        # Shuffle
        self.shuffle()

        # Draw new hand
        self.draw(cards_to_keep)

    def reset(self) -> None:
        """Reset deck to initial state."""
        self.library = self.cards.copy()
        self.hand = []
        self.battlefield = []
        self.graveyard = []
        self.mana_pool = {}

    def count_lands_in_hand(self) -> int:
        """Count number of lands in current hand."""
        count = 0
        for card in self.hand:
            type_line = card.get("type_line", "").lower()
            if "land" in type_line:
                count += 1
        return count

    def count_spells_in_hand(self) -> int:
        """Count number of non-land cards in hand."""
        return len(self.hand) - self.count_lands_in_hand()

    def get_available_mana_sources(self) -> List[Set[str]]:
        """
        Calculates available mana sources from battlefield.
        Returns a list of sets, where each set represents a mana point's capabilities.
        """
        sources = []
        for card in self.battlefield:
            card_sources = ManaUtils.get_mana_sources(card)
            sources.extend(card_sources)
        return sources

    def get_castable_spells(self, mana_sources: List[Set[str]]) -> List[Dict[str, Any]]:
        """
        Get spells in hand that can be cast with available mana.

        Args:
            mana_sources: List of available mana sources

        Returns:
            List of castable cards
        """
        castable = []
        for card in self.hand:
            type_line = card.get("type_line", "").lower()
            if "land" not in type_line:  # Not a land
                # Parse cost
                cost = ManaUtils.parse_cost(card.get('mana_cost', ''))
                # Check if we can pay (using a copy of sources to avoid modification)
                if ManaUtils.pay(mana_sources[:], cost):
                    castable.append(card)
        return castable


class ManaCurveAnalyzer:
    """Analyzes mana curve statistics for a deck."""

    @staticmethod
    def analyze_curve(cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the mana curve of a deck.

        Args:
            cards: List of card dictionaries

        Returns:
            Dictionary with curve statistics
        """
        cmcs = []
        lands = 0
        spells = 0

        for card in cards:
            type_line = card.get("type_line", "").lower()
            cmc = card.get("cmc", 0)

            if "land" in type_line:
                lands += 1
            else:
                spells += 1
                cmcs.append(cmc)

        # Calculate statistics
        if cmcs:
            avg_cmc = statistics.mean(cmcs)
            median_cmc = statistics.median(cmcs)
            try:
                mode_cmc = statistics.mode(cmcs)
            except statistics.StatisticsError:
                mode_cmc = None
        else:
            avg_cmc = 0
            median_cmc = 0
            mode_cmc = None

        # CMC distribution
        cmc_distribution = Counter(cmcs)

        return {
            "total_cards": len(cards),
            "lands": lands,
            "spells": spells,
            "land_ratio": lands / len(cards) if cards else 0,
            "avg_cmc": avg_cmc,
            "median_cmc": median_cmc,
            "mode_cmc": mode_cmc,
            "cmc_distribution": dict(cmc_distribution)
        }


class GoldfishSimulator:
    """Simulates playing a deck without an opponent (goldfishing)."""

    def __init__(self, deck: Deck):
        """
        Initialize the goldfish simulator.

        Args:
            deck: Deck to simulate
        """
        self.deck = deck

    def simulate_opening_hand(self, hand_size: int = 7) -> Dict[str, Any]:
        """
        Simulate drawing an opening hand.

        Args:
            hand_size: Size of opening hand

        Returns:
            Statistics about the opening hand
        """
        self.deck.reset()
        self.deck.shuffle()
        self.deck.draw(hand_size)

        lands = self.deck.count_lands_in_hand()
        spells = self.deck.count_spells_in_hand()

        # Simple mulligan decision: keep if 2-5 lands
        keep = 2 <= lands <= 5

        return {
            "hand_size": hand_size,
            "lands": lands,
            "spells": spells,
            "keep": keep,
            "hand": [card.get("name", "Unknown") for card in self.deck.hand]
        }

    def simulate_turns(self, num_turns: int = 5, starting_hand_size: int = 7) -> Dict[str, Any]:
        """
        Simulate playing out the first N turns.

        Args:
            num_turns: Number of turns to simulate
            starting_hand_size: Size of opening hand

        Returns:
            Statistics about the game simulation
        """
        self.deck.reset()
        self.deck.shuffle()
        self.deck.draw(starting_hand_size)

        turn_data = []
        lands_played_total = 0
        spells_cast_total = 0
        cards_drawn_total = starting_hand_size

        for turn in range(1, num_turns + 1):
            # Draw for turn (except turn 1 on the play)
            if turn > 1:
                self.deck.draw(1)
                cards_drawn_total += 1

            # Try to play a land
            land_played = False
            for card in self.deck.hand[:]:
                type_line = card.get("type_line", "").lower()
                if "land" in type_line:
                    self.deck.hand.remove(card)
                    self.deck.battlefield.append(card)
                    lands_played_total += 1
                    land_played = True
                    break

            # Count available mana
            mana_sources = self.deck.get_available_mana_sources()

            # Simple metric for display/stats (just count sources)
            available_mana_count = len(mana_sources)

            # Try to cast spells
            spells_cast_this_turn = 0

            # Get castable spells (this checks against full mana pool)
            castable = self.deck.get_castable_spells(mana_sources)

            # Cast spells in order of decreasing CMC (greedy)
            castable.sort(key=lambda c: c.get("cmc", 0), reverse=True)

            for spell in castable:
                cost = ManaUtils.parse_cost(spell.get('mana_cost', ''))

                # Try to pay (this modifies mana_sources in place)
                if ManaUtils.pay(mana_sources, cost):
                    self.deck.hand.remove(spell)
                    self.deck.battlefield.append(spell)
                    spells_cast_this_turn += 1
                    spells_cast_total += 1

            turn_data.append({
                "turn": turn,
                "land_played": land_played,
                "lands_in_play": lands_played_total,
                "spells_cast": spells_cast_this_turn,
                "cards_in_hand": len(self.deck.hand),
                "available_mana": available_mana_count
            })

        return {
            "num_turns": num_turns,
            "lands_played": lands_played_total,
            "spells_cast": spells_cast_total,
            "cards_drawn": cards_drawn_total,
            "final_hand_size": len(self.deck.hand),
            "final_battlefield_size": len(self.deck.battlefield),
            "turns": turn_data
        }


class MonteCarloSimulator:
    """Runs Monte Carlo simulations for statistical deck analysis."""

    def __init__(self, cards: List[Dict[str, Any]]):
        """
        Initialize the Monte Carlo simulator.

        Args:
            cards: List of card dictionaries representing the deck
        """
        self.cards = cards
        self.deck = Deck(cards)

    def run_opening_hand_analysis(self, iterations: int = 1000) -> Dict[str, Any]:
        """
        Run Monte Carlo analysis of opening hands.

        Args:
            iterations: Number of hands to simulate

        Returns:
            Aggregated statistics
        """
        print(f"Running {iterations} opening hand simulations...")

        simulator = GoldfishSimulator(self.deck)
        results = []

        for _ in range(iterations):
            result = simulator.simulate_opening_hand()
            results.append(result)

        # Aggregate statistics
        lands_counts = [r["lands"] for r in results]
        keep_rate = sum(1 for r in results if r["keep"]) / len(results)

        return {
            "iterations": iterations,
            "avg_lands": statistics.mean(lands_counts),
            "median_lands": statistics.median(lands_counts),
            "keep_rate": keep_rate,
            "land_distribution": dict(Counter(lands_counts))
        }

    def run_goldfish_analysis(self, iterations: int = 100, num_turns: int = 5) -> Dict[str, Any]:
        """
        Run Monte Carlo goldfish simulations.

        Args:
            iterations: Number of games to simulate
            num_turns: Number of turns per game

        Returns:
            Aggregated statistics
        """
        print(f"Running {iterations} goldfish simulations ({num_turns} turns each)...")

        simulator = GoldfishSimulator(self.deck)
        results = []

        for _ in range(iterations):
            result = simulator.simulate_turns(num_turns=num_turns)
            results.append(result)

        # Aggregate statistics
        lands_played = [r["lands_played"] for r in results]
        spells_cast = [r["spells_cast"] for r in results]

        # Per-turn statistics
        turn_stats = {}
        for turn_num in range(1, num_turns + 1):
            turn_lands = [r["turns"][turn_num - 1]["lands_in_play"] for r in results]
            turn_spells = [r["turns"][turn_num - 1]["spells_cast"] for r in results]

            turn_stats[f"turn_{turn_num}"] = {
                "avg_lands": statistics.mean(turn_lands),
                "avg_spells_cast": statistics.mean(turn_spells)
            }

        return {
            "iterations": iterations,
            "num_turns": num_turns,
            "avg_lands_played": statistics.mean(lands_played),
            "avg_spells_cast": statistics.mean(spells_cast),
            "median_spells_cast": statistics.median(spells_cast),
            "turn_stats": turn_stats
        }

    def full_analysis(self, hand_iterations: int = 1000, goldfish_iterations: int = 100) -> Dict[str, Any]:
        """
        Run complete deck analysis.

        Args:
            hand_iterations: Number of opening hands to simulate
            goldfish_iterations: Number of goldfish games to simulate

        Returns:
            Complete analysis results
        """
        print("\n" + "=" * 60)
        print("MONTE CARLO DECK ANALYSIS")
        print("=" * 60)
        print()

        # Mana curve analysis
        print("Analyzing mana curve...")
        curve_analysis = ManaCurveAnalyzer.analyze_curve(self.cards)

        # Opening hand analysis
        hand_analysis = self.run_opening_hand_analysis(iterations=hand_iterations)

        # Goldfish analysis
        goldfish_analysis = self.run_goldfish_analysis(iterations=goldfish_iterations)

        return {
            "deck_size": len(self.cards),
            "mana_curve": curve_analysis,
            "opening_hands": hand_analysis,
            "goldfish": goldfish_analysis
        }

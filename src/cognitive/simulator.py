"""Monte Carlo simulation engine for deck testing and analysis."""

import random
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import statistics


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

    def get_castable_spells(self, available_mana: int) -> List[Dict[str, Any]]:
        """
        Get spells in hand that can be cast with available mana.

        Args:
            available_mana: Amount of mana available

        Returns:
            List of castable cards
        """
        castable = []
        for card in self.hand:
            type_line = card.get("type_line", "").lower()
            if "land" not in type_line:  # Not a land
                cmc = card.get("cmc", 0)
                if cmc <= available_mana:
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

            # Count available mana (simplified: 1 per land)
            available_mana = lands_played_total

            # Try to cast spells
            spells_cast_this_turn = 0
            castable = self.deck.get_castable_spells(available_mana)

            # Cast spells in order of decreasing CMC (greedy)
            castable.sort(key=lambda c: c.get("cmc", 0), reverse=True)

            for spell in castable:
                cmc = spell.get("cmc", 0)
                if cmc <= available_mana:
                    self.deck.hand.remove(spell)
                    self.deck.battlefield.append(spell)
                    available_mana -= cmc
                    spells_cast_this_turn += 1
                    spells_cast_total += 1

            turn_data.append({
                "turn": turn,
                "land_played": land_played,
                "lands_in_play": lands_played_total,
                "spells_cast": spells_cast_this_turn,
                "cards_in_hand": len(self.deck.hand),
                "available_mana": lands_played_total
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

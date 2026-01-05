"""Synergy graph for detecting card interactions and combos."""

from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
import networkx as nx
import json
import re


class SynergyGraph:
    """
    NetworkX-based graph for analyzing card synergies and interactions.

    Nodes represent cards, edges represent synergy relationships.
    Edge weights indicate strength of synergy.
    """

    GRAPH_CACHE_PATH = Path("data/synergy_graph.json")

    # Synergy keywords that indicate interactions
    SYNERGY_KEYWORDS = {
        "tribal": ["elf", "goblin", "merfolk", "zombie", "vampire", "dragon", "angel", "demon"],
        "mechanics": ["sacrifice", "draw", "discard", "counter", "destroy", "exile", "token", "ETB"],
        "keywords": ["flying", "first strike", "deathtouch", "vigilance", "trample", "lifelink", "haste"],
        "card_types": ["artifact", "creature", "enchantment", "instant", "sorcery", "planeswalker"],
        "themes": ["graveyard", "lifegain", "+1/+1 counter", "ramp", "mill"]
    }

    def __init__(self):
        """Initialize the synergy graph."""
        self.graph = nx.Graph()
        self.card_index: Dict[str, Dict[str, Any]] = {}
        # Inverted index for faster synergy lookups
        # Format: "category:value" -> Set[card_names]
        self.feature_index: Dict[str, Set[str]] = {}

    def add_card(self, card: Dict[str, Any]) -> None:
        """
        Add a card to the synergy graph.

        Args:
            card: Card dictionary with name, oracle_text, type_line, etc.
        """
        card_name = card.get("name", "")
        if not card_name:
            return

        # Extract relevant features
        features = self._extract_card_features(card)

        # Add node with features
        self.graph.add_node(
            card_name,
            **features
        )

        # Index for quick lookup
        self.card_index[card_name] = {
            "features": features,
            "card": card
        }

        # Update inverted index
        self._update_index(card_name, features)

    def _update_index(self, card_name: str, features: Dict[str, Any]) -> None:
        """Update the inverted index with a card's features."""
        # Index tribes
        for tribe in features.get("tribes", []):
            key = f"tribe:{tribe}"
            if key not in self.feature_index:
                self.feature_index[key] = set()
            self.feature_index[key].add(card_name)

        # Index mechanics
        for mechanic in features.get("mechanics", []):
            key = f"mechanic:{mechanic}"
            if key not in self.feature_index:
                self.feature_index[key] = set()
            self.feature_index[key].add(card_name)

        # Index themes
        for theme in features.get("themes", []):
            key = f"theme:{theme}"
            if key not in self.feature_index:
                self.feature_index[key] = set()
            self.feature_index[key].add(card_name)

        # Index keywords
        for keyword in features.get("keywords", []):
            key = f"keyword:{keyword}"
            if key not in self.feature_index:
                self.feature_index[key] = set()
            self.feature_index[key].add(card_name)

    def _extract_card_features(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract synergy-relevant features from a card.

        Args:
            card: Card dictionary

        Returns:
            Dictionary of extracted features
        """
        oracle_text = card.get("oracle_text", "").lower()
        type_line = card.get("type_line", "").lower()
        name = card.get("name", "").lower()
        keywords = [kw.lower() for kw in card.get("keywords", [])]

        features = {
            "type_line": type_line,
            "oracle_text": oracle_text,
            "keywords": keywords,
            "colors": card.get("colors", []),
            "cmc": card.get("cmc", 0),
            "power": card.get("power"),
            "toughness": card.get("toughness")
        }

        # Extract tribes
        tribes = []
        for tribe in self.SYNERGY_KEYWORDS["tribal"]:
            if tribe in type_line or tribe in oracle_text:
                tribes.append(tribe)
        features["tribes"] = tribes

        # Extract mechanics
        mechanics = []
        for mechanic in self.SYNERGY_KEYWORDS["mechanics"]:
            if mechanic in oracle_text:
                mechanics.append(mechanic)
        features["mechanics"] = mechanics

        # Extract themes
        themes = []
        for theme in self.SYNERGY_KEYWORDS["themes"]:
            if theme in oracle_text:
                themes.append(theme)
        features["themes"] = themes

        # Card types
        card_types = []
        for ctype in self.SYNERGY_KEYWORDS["card_types"]:
            if ctype in type_line:
                card_types.append(ctype)
        features["card_types"] = card_types

        return features

    def build_synergies(self) -> None:
        """
        Build synergy edges between all cards in the graph.

        Analyzes all card pairs and creates weighted edges based on
        synergy strength.
        """
        print(f"Building synergies for {len(self.graph.nodes)} cards...")

        cards = list(self.graph.nodes(data=True))
        edge_count = 0
        total_cards = len(cards)

        # batch size for reporting
        report_interval = 1000

        for i, (card_name, card_data) in enumerate(cards):
            if (i + 1) % report_interval == 0:
                print(f"  Processed {i+1}/{total_cards} cards... ({edge_count} edges)")

            # Get candidates from inverted index
            # This drastically reduces O(N^2) to roughly O(N * Avg_Candidates)
            candidates = self._get_candidates(card_name, card_data)

            for candidate_name in candidates:
                # Avoid self-loops and duplicate checks (canonical ordering)
                if candidate_name <= card_name:
                    continue

                # Candidate data might not be in the graph yet if we are streaming,
                # but here we assume graph is fully populated with nodes first.
                candidate_data = self.graph.nodes[candidate_name]

                synergy_score = self._calculate_synergy(
                    card_name, card_data,
                    candidate_name, candidate_data
                )

                # Only add edge if there's meaningful synergy
                # Threshold > 0.45 ensures only strong interactions (Tribal/Combos) are saved
                # This keeps the graph size manageable and high-quality.
                if synergy_score > 0.45:
                    self.graph.add_edge(
                        card_name,
                        candidate_name,
                        weight=synergy_score,
                        synergy_types=self._get_synergy_types(card_data, candidate_data)
                    )
                    edge_count += 1

        print(f"Created {edge_count} synergy relationships")

    def _get_candidates(self, card_name: str, card_data: Dict[str, Any]) -> Set[str]:
        """Get set of candidate cards that share at least one feature."""
        candidates = set()

        # Check tribes
        for tribe in card_data.get("tribes", []):
            key = f"tribe:{tribe}"
            candidates.update(self.feature_index.get(key, set()))

        # Check mechanics
        for mechanic in card_data.get("mechanics", []):
            key = f"mechanic:{mechanic}"
            candidates.update(self.feature_index.get(key, set()))

        # Check themes
        for theme in card_data.get("themes", []):
            key = f"theme:{theme}"
            candidates.update(self.feature_index.get(key, set()))

        # Keywords often produce too many poor matches (e.g., "Flying"),
        # preventing the "Flying" index from exploding candidates is wise,
        # but for now we'll include them since they are part of synergy calculation.
        # Determine if we want to restrict this.
        # For optimization, we might SKIP common keywords if we want strict combos.
        # But let's proceed with including everything first.
        for keyword in card_data.get("keywords", []):
            key = f"keyword:{keyword}"
            candidates.update(self.feature_index.get(key, set()))

        # Remove self
        candidates.discard(card_name)

        return candidates

    def _calculate_synergy(
        self,
        card1_name: str,
        card1_data: Dict[str, Any],
        card2_name: str,
        card2_data: Dict[str, Any]
    ) -> float:
        """
        Calculate synergy score between two cards.

        Args:
            card1_name: Name of first card
            card1_data: Features of first card
            card2_name: Name of second card
            card2_data: Features of second card

        Returns:
            Synergy score (0.0 to 1.0)
        """
        score = 0.0

        # Tribal synergy (strong)
        tribes1 = set(card1_data.get("tribes", []))
        tribes2 = set(card2_data.get("tribes", []))
        if tribes1 & tribes2:  # Intersection
            score += 0.4

        # Mechanic synergy (medium)
        mechanics1 = set(card1_data.get("mechanics", []))
        mechanics2 = set(card2_data.get("mechanics", []))
        mechanic_overlap = len(mechanics1 & mechanics2)
        if mechanic_overlap > 0:
            score += 0.2 * min(mechanic_overlap, 2)  # Cap at 0.4

        # Theme synergy (medium)
        themes1 = set(card1_data.get("themes", []))
        themes2 = set(card2_data.get("themes", []))
        if themes1 & themes2:
            score += 0.2

        # Keyword synergy (weak)
        keywords1 = set(card1_data.get("keywords", []))
        keywords2 = set(card2_data.get("keywords", []))
        if keywords1 & keywords2:
            score += 0.1

        # Color identity synergy (weak bonus)
        colors1 = set(card1_data.get("colors", []))
        colors2 = set(card2_data.get("colors", []))
        if colors1 and colors2 and (colors1 & colors2):
            score += 0.05

        # Mana curve synergy (very weak bonus for complementary costs)
        cmc1 = card1_data.get("cmc", 0)
        cmc2 = card2_data.get("cmc", 0)
        if abs(cmc1 - cmc2) >= 2 and cmc1 < 7 and cmc2 < 7:
            score += 0.05  # Reward diverse mana curve

        return min(score, 1.0)  # Cap at 1.0

    def _get_synergy_types(
        self,
        card1_data: Dict[str, Any],
        card2_data: Dict[str, Any]
    ) -> List[str]:
        """Get list of synergy types between two cards."""
        types = []

        if set(card1_data.get("tribes", [])) & set(card2_data.get("tribes", [])):
            types.append("tribal")

        if set(card1_data.get("mechanics", [])) & set(card2_data.get("mechanics", [])):
            types.append("mechanic")

        if set(card1_data.get("themes", [])) & set(card2_data.get("themes", [])):
            types.append("theme")

        if set(card1_data.get("keywords", [])) & set(card2_data.get("keywords", [])):
            types.append("keyword")

        return types

    def find_synergies_for_card(
        self,
        card_name: str,
        top_n: int = 10
    ) -> List[Tuple[str, float, List[str]]]:
        """
        Find cards with highest synergy to the given card.

        Args:
            card_name: Name of the card to find synergies for
            top_n: Number of top synergies to return

        Returns:
            List of (card_name, synergy_score, synergy_types) tuples
        """
        if card_name not in self.graph:
            return []

        # Get all neighbors with edge weights
        neighbors = []
        for neighbor in self.graph.neighbors(card_name):
            edge_data = self.graph[card_name][neighbor]
            weight = edge_data.get("weight", 0)
            synergy_types = edge_data.get("synergy_types", [])
            neighbors.append((neighbor, weight, synergy_types))

        # Sort by weight descending
        neighbors.sort(key=lambda x: x[1], reverse=True)

        return neighbors[:top_n]

    def find_combo_pieces(
        self,
        card_name: str,
        threshold: float = 0.5
    ) -> List[str]:
        """
        Find potential combo pieces for a card.

        Args:
            card_name: Name of the card
            threshold: Minimum synergy score to consider a combo

        Returns:
            List of card names that form strong combos
        """
        synergies = self.find_synergies_for_card(card_name, top_n=50)

        # Filter by threshold
        combos = [
            card for card, score, _ in synergies
            if score >= threshold
        ]

        return combos

    def get_cluster_recommendations(
        self,
        seed_cards: List[str],
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get card recommendations based on a cluster of seed cards.

        Args:
            seed_cards: List of card names to base recommendations on
            top_n: Number of recommendations to return

        Returns:
            List of (card_name, aggregate_score) tuples
        """
        # Aggregate synergy scores from all seed cards
        candidate_scores: Dict[str, float] = {}

        for seed_card in seed_cards:
            if seed_card not in self.graph:
                continue

            synergies = self.find_synergies_for_card(seed_card, top_n=50)

            for card, score, _ in synergies:
                # Don't recommend seed cards
                if card in seed_cards:
                    continue

                # Aggregate scores
                if card in candidate_scores:
                    candidate_scores[card] += score
                else:
                    candidate_scores[card] = score

        # Normalize by number of seed cards
        if seed_cards:
            for card in candidate_scores:
                candidate_scores[card] /= len(seed_cards)

        # Sort and return top N
        recommendations = sorted(
            candidate_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return recommendations[:top_n]

    def save(self) -> None:
        """Save the synergy graph to disk using streaming write to avoid OOM."""
        self.GRAPH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Saving graph to {self.GRAPH_CACHE_PATH}...")
        
        try:
            with open(self.GRAPH_CACHE_PATH, 'w', encoding='utf-8') as f:
                f.write('{"nodes": [')
                
                # Write nodes
                nodes = list(self.graph.nodes(data=True))
                total_nodes = len(nodes)
                for i, (node, data) in enumerate(nodes):
                    if i > 0: f.write(',')
                    entry = [node, data]
                    f.write(json.dumps(entry))
                    
                f.write('], "edges": [')
                
                # Write edges
                edges = list(self.graph.edges(data=True))
                total_edges = len(edges)
                for i, (u, v, data) in enumerate(edges):
                    if i > 0: f.write(',')
                    entry = [u, v, data]
                    f.write(json.dumps(entry))
                    
                f.write(']}')
                
            print(f"Saved {total_nodes} nodes and {total_edges} edges successfully")
            
        except Exception as e:
            print(f"Error saving graph: {e}")

    def load(self) -> bool:
        """
        Load synergy graph from disk.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.GRAPH_CACHE_PATH.exists():
            return False

        try:
            with open(self.GRAPH_CACHE_PATH, 'r') as f:
                data = json.load(f)

            # Rebuild graph
            self.graph = nx.Graph()

            # Add nodes
            for node_name, node_data in data["nodes"]:
                self.graph.add_node(node_name, **node_data)

            # Add edges
            for u, v, edge_data in data["edges"]:
                self.graph.add_edge(u, v, **edge_data)

            # Rebuild index
            self.card_index = {
                node: {"features": data}
                for node, data in self.graph.nodes(data=True)
            }

            print(f"Loaded synergy graph from {self.GRAPH_CACHE_PATH}")
            print(f"  Nodes: {len(self.graph.nodes)}")
            print(f"  Edges: {len(self.graph.edges)}")

            return True

        except Exception as e:
            print(f"Error loading synergy graph: {e}")
            return False

    def stats(self) -> Dict[str, Any]:
        """Get statistics about the synergy graph."""
        return {
            "num_cards": len(self.graph.nodes),
            "num_synergies": len(self.graph.edges),
            "avg_synergies_per_card": (
                2 * len(self.graph.edges) / len(self.graph.nodes)
                if len(self.graph.nodes) > 0 else 0
            ),
            "density": nx.density(self.graph)
        }

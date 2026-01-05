"""ChromaDB vector store for semantic card search using sentence-transformers."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np


class VectorStore:
    """Manages card embeddings and semantic search using ChromaDB and sentence-transformers."""

    PERSIST_DIR = Path("data/chroma_db")
    COLLECTION_NAME = "mtg_cards"
    MODEL_NAME = "all-MiniLM-L6-v2"  # 90MB, fast, excellent quality

    def __init__(self):
        """Initialize ChromaDB client and sentence-transformer model."""
        self.PERSIST_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.PERSIST_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Load sentence-transformer model
        print(f"Loading sentence-transformer model '{self.MODEL_NAME}'...")
        self.model = SentenceTransformer(self.MODEL_NAME)
        print("Model loaded successfully")

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Magic: The Gathering card embeddings (sentence-transformers)", "hnsw:space": "cosine"}
        )

    def _prepare_card_text(self, card: Dict[str, Any]) -> str:
        """
        Prepare searchable text from card data.

        Args:
            card: Card dictionary from Scryfall

        Returns:
            Formatted text for embedding
        """
        parts = []

        # Card name
        if "name" in card:
            parts.append(f"Name: {card['name']}")

        # Type line
        if "type_line" in card:
            parts.append(f"Type: {card['type_line']}")

        # Oracle text (rules text)
        if "oracle_text" in card:
            parts.append(f"Text: {card['oracle_text']}")

        # Mana cost
        if "mana_cost" in card:
            parts.append(f"Cost: {card['mana_cost']}")

        # Power/Toughness for creatures
        if "power" in card and "toughness" in card:
            parts.append(f"P/T: {card['power']}/{card['toughness']}")

        # Keywords
        if "keywords" in card and card["keywords"]:
            parts.append(f"Keywords: {', '.join(card['keywords'])}")

        return " | ".join(parts)

    def _prepare_metadata(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metadata from card.

        Args:
            card: Card dictionary from Scryfall

        Returns:
            Metadata dictionary
        """
        metadata = {
            "name": card.get("name", ""),
            "type_line": card.get("type_line", ""),
            "set": card.get("set", ""),
            "rarity": card.get("rarity", ""),
        }

        # Add colors if available
        if "colors" in card:
            metadata["colors"] = ",".join(card["colors"])

        # Add mana cost if available
        if "mana_cost" in card:
            metadata["mana_cost"] = card["mana_cost"]

        # Add CMC if available
        if "cmc" in card:
            metadata["cmc"] = str(int(card["cmc"]))

        return metadata

    def upsert_cards(self, cards: List[Dict[str, Any]], batch_size: int = 32) -> None:
        """
        Insert or update cards in the vector database using sentence-transformers.

        Args:
            cards: List of card dictionaries from Scryfall
            batch_size: Number of cards to encode per batch (32 is optimal for CPU)
        """
        total = len(cards)
        print(f"Upserting {total} cards into ChromaDB with sentence-transformers...")

        # Prepare all card data first
        card_data = []
        for card in cards:
            if card.get("id"):
                card_data.append({
                    "id": card["id"],
                    "text": self._prepare_card_text(card),
                    "metadata": self._prepare_metadata(card)
                })

        # Process in batches
        for i in range(0, len(card_data), batch_size):
            batch = card_data[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(card_data) + batch_size - 1) // batch_size

            # Extract texts for encoding
            texts = [item["text"] for item in batch]

            # Encode batch using sentence-transformers
            print(f"  Encoding batch {batch_num}/{total_batches}...")
            embeddings = self.model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                batch_size=batch_size
            )

            # Prepare data for ChromaDB
            ids = [item["id"] for item in batch]
            documents = texts
            metadatas = [item["metadata"] for item in batch]
            embeddings_list = [emb.tolist() for emb in embeddings]

            # Add batch to ChromaDB
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings_list,
                metadatas=metadatas
            )

            print(f"  Batch {batch_num}/{total_batches} complete ({len(ids)} cards)")

        print(f"✓ Upserted {total} cards successfully with semantic embeddings")

    def query_similar(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for cards similar to the query using semantic understanding.

        No preprocessing needed - sentence-transformers understands natural language.

        Args:
            query: Natural language search query
            n_results: Number of results to return

        Returns:
            Dictionary with 'ids', 'documents', 'metadatas' keys
        """
        # Encode query directly - no preprocessing needed!
        # Model understands: "counterspells", "Atraxa deck", "sacrifice outlets", etc.
        query_embedding = self.model.encode(
            query,
            convert_to_numpy=True
        )

        # Search with semantic embedding
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )

        return results

    def count(self) -> int:
        """
        Get the total number of cards in the database.

        Returns:
            Number of cards stored
        """
        return self.collection.count()


# Singleton instance for performance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Get or create the singleton VectorStore instance.

    This avoids reinitializing the model and ChromaDB on every query.
    The first call will initialize the store (2-3s), subsequent calls are instant.

    Returns:
        Singleton VectorStore instance
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        print("[VectorStore] Initializing singleton instance with sentence-transformers...")
        _vector_store_instance = VectorStore()
        print(f"[VectorStore] Ready ({_vector_store_instance.count()} cards indexed)")
    return _vector_store_instance

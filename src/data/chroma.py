"""ChromaDB vector store for semantic card search."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pickle


class TFIDFEmbeddingFunction:
    """Simple TF-IDF based embedding function that runs completely locally."""

    def __init__(self):
        self.name = "tfidf"
        self.vectorizer = TfidfVectorizer(
            max_features=384,  # Match typical embedding dimension
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.is_fitted = False
        self.documents_cache = []

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for input texts."""
        # Cache documents for fitting
        self.documents_cache.extend(input)

        if not self.is_fitted and self.documents_cache:
            # Fit on first batch
            self.vectorizer.fit(self.documents_cache)
            self.is_fitted = True

        if self.is_fitted:
            # Transform documents to vectors
            vectors = self.vectorizer.transform(input).toarray()
        else:
            # Return zero vectors if not fitted yet
            vectors = np.zeros((len(input), 384))

        return vectors.tolist()


class VectorStore:
    """Manages card embeddings and semantic search using ChromaDB."""

    PERSIST_DIR = Path("data/chroma_db")
    COLLECTION_NAME = "mtg_cards"
    VECTORIZER_PATH = Path("data/vectorizer.pkl")

    def __init__(self):
        """Initialize ChromaDB client and collection."""
        self.PERSIST_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.PERSIST_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Load or initialize TF-IDF vectorizer
        if self.VECTORIZER_PATH.exists():
            print("Loading saved vectorizer...")
            with open(self.VECTORIZER_PATH, 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.is_vectorizer_fitted = True
        else:
            self.vectorizer = TfidfVectorizer(
                max_features=384,
                stop_words='english',
                ngram_range=(1, 2)
            )
            self.is_vectorizer_fitted = False

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Magic: The Gathering card embeddings", "hnsw:space": "cosine"}
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

    def upsert_cards(self, cards: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """
        Insert or update cards in the vector database.

        Args:
            cards: List of card dictionaries from Scryfall
            batch_size: Number of cards to process per batch
        """
        total = len(cards)
        print(f"Upserting {total} cards into ChromaDB...")

        # First pass: collect all documents for fitting vectorizer
        all_docs = []
        for card in cards:
            if card.get("id"):
                all_docs.append(self._prepare_card_text(card))

        # Fit vectorizer on all documents
        print("  Fitting TF-IDF vectorizer on card texts...")
        self.vectorizer.fit(all_docs)
        self.is_vectorizer_fitted = True

        # Save vectorizer for later use
        print("  Saving vectorizer...")
        with open(self.VECTORIZER_PATH, 'wb') as f:
            pickle.dump(self.vectorizer, f)

        # Second pass: process and add cards in batches
        for i in range(0, total, batch_size):
            batch = cards[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embeddings = []

            for card in batch:
                # Use Scryfall ID as unique identifier
                card_id = card.get("id")
                if not card_id:
                    continue

                doc_text = self._prepare_card_text(card)
                ids.append(card_id)
                documents.append(doc_text)
                metadatas.append(self._prepare_metadata(card))

                # Compute embedding locally
                embedding = self.vectorizer.transform([doc_text]).toarray()[0].tolist()
                embeddings.append(embedding)

            # Add batch with pre-computed embeddings
            if ids:
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )

            print(f"  Batch {batch_num}/{total_batches} complete ({len(ids)} cards)")

        print(f"✓ Upserted {total} cards successfully")

    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess user query to match card database terminology.

        Args:
            query: Raw user query

        Returns:
            Preprocessed query text optimized for TF-IDF matching
        """
        # Convert to lowercase for processing
        query = query.lower()

        # Common MTG query expansions to improve TF-IDF matching
        # Maps user terms to database terms
        expansions = {
            'counterspell': 'counter target spell instant',
            'counterspells': 'counter target spell instant',
            'removal': 'destroy target creature exile',
            'board wipe': 'destroy all creatures',
            'boardwipe': 'destroy all creatures',
            'wipe': 'destroy all',
            'ramp': 'search basic land forest plains',
            'draw': 'draw card',
            'card draw': 'draw card',
            'lifegain': 'gain life',
            'life gain': 'gain life',
            'tutor': 'search library',
            'fetch': 'search library',
            'mill': 'library graveyard',
            'graveyard recursion': 'return graveyard battlefield hand',
            'recursion': 'return graveyard',
            'flicker': 'exile return battlefield',
            'blink': 'exile return battlefield',
            'token': 'create token creature',
            'tokens': 'create token creature',
            'etb': 'enters battlefield',
            'enter the battlefield': 'enters battlefield',
            'enters the battlefield': 'enters battlefield',
            'ltb': 'leaves battlefield',
            'leaves the battlefield': 'leaves battlefield',
            'combat trick': 'instant target creature',
            'pump spell': 'target creature gets',
            'evasion': 'unblockable flying',
            'cantrip': 'draw card instant sorcery',
            'planeswalker': 'planeswalker loyalty',
            'tribal': 'creature type',
            'atraxa': 'proliferate counter planeswalker',
            'proliferate': 'proliferate counter',
            'commander staples': 'legendary creature powerful',
            'staples': 'powerful',
            'powerful': 'legendary rare mythic',
        }

        # Apply expansions (check for exact phrase matches first)
        for term, expansion in expansions.items():
            if term in query:
                query = query.replace(term, expansion)

        # Keep the original if it's already good (contains card type keywords)
        # This helps queries like "Show me powerful Commander staples" stay broad
        return query

    def query_similar(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for cards similar to the query.

        Args:
            query: Natural language search query
            n_results: Number of results to return

        Returns:
            Dictionary with 'ids', 'documents', 'metadatas' keys
        """
        if not self.is_vectorizer_fitted:
            raise RuntimeError("Vectorizer not fitted. Please run upsert_cards first.")

        # Preprocess query to improve matching
        processed_query = self._preprocess_query(query)

        # Compute query embedding locally
        query_embedding = self.vectorizer.transform([processed_query]).toarray()[0].tolist()

        # Query with pre-computed embedding
        results = self.collection.query(
            query_embeddings=[query_embedding],
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

    This avoids reinitializing ChromaDB on every query, which takes ~30+ seconds.
    The first call will initialize the store, subsequent calls return the cached instance.

    Returns:
        Singleton VectorStore instance
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        print("[VectorStore] Initializing singleton instance...")
        _vector_store_instance = VectorStore()
        print(f"[VectorStore] Ready ({_vector_store_instance.count()} cards indexed)")
    return _vector_store_instance

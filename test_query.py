from src.data.chroma import VectorStore
import sys

def test_search(query):
    print(f"\nSearching for: '{query}'")
    store = VectorStore()
    results = store.query_similar(query, n_results=3)

    # Chroma returns lists of lists (one list per query)
    ids = results['ids'][0]
    docs = results['documents'][0]
    metas = results['metadatas'][0]

    for i in range(len(ids)):
        print(f"\nResult {i+1}:")
        print(f"Name: {metas[i].get('name')}")
        print(f"Text: {docs[i]}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "flyer that draws cards"

    test_search(query)

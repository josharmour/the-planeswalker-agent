import requests
import json
import os
import time

# Configuration
SCRYFALL_BULK_URL = "https://api.scryfall.com/bulk-data/oracle-cards"
DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "oracle_cards.json")

def fetch_scryfall_data():
    """
    Downloads the latest 'Oracle Cards' object from Scryfall.
    This is the lightweight JSON containing gameplay-relevant data.
    """
    print("--- Contacting Scryfall API ---")
    
    # 1. Get the download URI
    try:
        response = requests.get(SCRYFALL_BULK_URL)
        response.raise_for_status()
        metadata = response.json()
        download_uri = metadata['download_uri']
        print(f"Found Bulk Data: {metadata['updated_at']}")
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return

    # 2. Download the actual file
    print(f"Downloading from {download_uri}...")
    try:
        data_response = requests.get(download_uri, stream=True)
        data_response.raise_for_status()
        
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        with open(OUTPUT_FILE, 'wb') as f:
            for chunk in data_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"Success! Data saved to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error downloading bulk data: {e}")

def process_for_embedding():
    """
    Stub for Sprint 1, Task 1.2
    Reads the JSON and prepares 'Rich Context' strings for the Vector DB.
    """
    if not os.path.exists(OUTPUT_FILE):
        print("No data file found. Run download first.")
        return

    print("--- Processing Data for Embeddings (Stub) ---")
    # Future logic: Load JSON, iterate cards, format strings -> ChromaDB
    # Example logic:
    # with open(OUTPUT_FILE, 'r') as f:
    #     cards = json.load(f)
    #     for card in cards[:5]:
    #         print(f"Ready to embed: {card['name']} | {card.get('oracle_text', '')}")

if __name__ == "__main__":
    fetch_scryfall_data()
    # process_for_embedding()

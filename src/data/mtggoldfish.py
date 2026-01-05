"""MTGGoldfish scraper for fetching metagame data."""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time

class MTGGoldfishClient:
    """Client for scraping metagame data from MTGGoldfish."""

    BASE_URL = "https://www.mtggoldfish.com"

    def __init__(self):
        """Initialize the client."""
        # Use a polite user agent
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def get_metagame(self, format_name: str) -> List[Dict[str, Any]]:
        """
        Get metagame breakdown for a specific format.

        Args:
            format_name: 'standard', 'modern', 'pioneer', 'legacy', 'pauper', etc.

        Returns:
            List of deck dictionaries with name, share, url, etc.
        """
        format_name = format_name.lower()
        url = f"{self.BASE_URL}/metagame/{format_name}#paper"

        print(f"Scraping {url}...")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            decks = []
            
            # The metagame breakdown is usually in a table or list
            # Select the visible archetype items
            # This selector aims at the "archetype-tile" or table rows depending on view
            # MTGGoldfish uses .archetype-tile for the visual grid
            
            tiles = soup.select(".archetype-tile")
            
            for tile in tiles[:12]:  # Top 12 decks
                deck_data = self._parse_tile(tile)
                if deck_data:
                    decks.append(deck_data)
                    
            return decks

        except Exception as e:
            print(f"Error scraping MTGGoldfish: {e}")
            return []

    def _parse_tile(self, tile) -> Optional[Dict[str, Any]]:
        """Parse a single archetype tile."""
        try:
            # Name and Link
            title_tag = tile.select_one(".deck-price-paper a")
            if not title_tag:
                 # Try alternative layout
                 title_tag = tile.select_one(".archetype-tile-title a")
            
            if not title_tag:
                return None
                
            name = title_tag.text.strip()
            relative_url = title_tag['href']
            url = f"{self.BASE_URL}{relative_url}"
            
            # Meta Share
            share_tag = tile.select_one(".archetype-tile-statistic-value")
            meta_share = share_tag.text.strip() if share_tag else "N/A"
            
            # Colors
            colors = []
            manacost_tag = tile.select_one(".manacost-container")
            if manacost_tag:
                for img in manacost_tag.select("img"):
                    alt = img.get('alt', '')
                    if alt:
                        colors.append(alt)
            
            return {
                "name": name,
                "meta_share": meta_share,
                "url": url,
                "colors": colors
            }
        except Exception as e:
            # Fail silently for individual tiles to keep the rest
            return None

    def get_deck_list(self, url: str) -> Dict[str, Any]:
        """
        Scrape a specific deck page to get the full card list.
        
        Args:
            url: Full URL to the deck page
            
        Returns:
            Dictionary with 'mainboard' and 'sideboard' lists of formatted strings
        """
        print(f"Scraping deck list from {url}...")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            deck_data = {
                "mainboard": [],
                "sideboard": []
            }
            
            # MTGGoldfish deck layout typically uses a table
            # We look for rows with card quantities and names
            # The structure is often: <td class="deck-header">...</td> for Mainboard/Sideboard separators
            # But simpler is to look for 'deck-col-qty' and 'deck-col-card' classes
            
            # Let's try to parse the clipboard input hidden textarea if available, it's often cleaner
            textarea = soup.select_one("textarea.copy-paste-box")
            if textarea:
                full_text = textarea.text.strip()
                current_section = "mainboard"
                
                for line in full_text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.lower() == "sideboard":
                        current_section = "sideboard"
                        continue
                        
                    deck_data[current_section].append(line)
                    
                return deck_data

            # Fallback to table parsing if copy-paste box is missing
            # This is a simplified fallback
            rows = soup.select("tr")
            current_section = "mainboard"
            
            for row in rows:
                qty_cell = row.select_one(".deck-col-qty")
                card_cell = row.select_one(".deck-col-card a")
                
                if not qty_cell or not card_cell:
                    # Check if it's a header like "Sideboard"
                    header = row.select_one("th") or row.select_one("h3") # Structure varies
                    if header and "sideboard" in header.text.lower():
                        current_section = "sideboard"
                    continue
                    
                qty = qty_cell.text.strip()
                name = card_cell.text.strip()
                deck_data[current_section].append(f"{qty} {name}")
                
            return deck_data

        except Exception as e:
            print(f"Error getting deck list: {e}")
            return {"mainboard": [], "sideboard": [], "error": str(e)}

if __name__ == "__main__":
    # Simple test
    client = MTGGoldfishClient()
    print("Standard Metagame:")
    decks = client.get_metagame("standard")
    for d in decks:
        print(f"- {d['name']} ({d['meta_share']})")

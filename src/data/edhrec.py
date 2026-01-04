"""EDHREC integration for Commander metagame statistics."""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup


class EDHRECClient:
    """
    Client for accessing EDHREC Commander metagame data.

    Note: EDHREC does not provide an official API. This client scrapes
    public pages and should be used respectfully with appropriate caching.
    """

    BASE_URL = "https://edhrec.com"
    CACHE_DIR = Path("data/edhrec_cache")
    CACHE_DURATION = 86400  # 24 hours in seconds

    def __init__(self):
        """Initialize EDHREC client and ensure cache directory exists."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PlaneswalkerAgent/1.0 (Educational MTG AI Project)'
        })

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a given key."""
        # Sanitize key for filesystem
        safe_key = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in key)
        return self.CACHE_DIR / f"{safe_key}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cached data is still valid."""
        if not cache_path.exists():
            return False

        age = time.time() - cache_path.stat().st_mtime
        return age < self.CACHE_DURATION

    def _read_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Read data from cache if available and valid."""
        cache_path = self._get_cache_path(key)

        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read cache for {key}: {e}")

        return None

    def _write_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Write data to cache."""
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to write cache for {key}: {e}")

    def _retry_request(self, url: str, max_retries: int = 5) -> requests.Response:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            url: The URL to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            The successful response

        Raises:
            Exception: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to fetch {url} after {max_retries} attempts: {e}")

                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Request failed (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)

    def get_commander_page(self, commander_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch EDHREC page data for a specific commander.

        Args:
            commander_name: Name of the commander (will be URL-encoded)
            force_refresh: If True, bypass cache

        Returns:
            Dictionary containing commander page data
        """
        cache_key = f"commander_{commander_name.lower().replace(' ', '-')}"

        # Check cache first
        if not force_refresh:
            cached_data = self._read_cache(cache_key)
            if cached_data:
                print(f"Using cached data for {commander_name}")
                return cached_data

        # Build URL
        url_name = commander_name.lower().replace(' ', '-').replace(',', '')
        url = f"{self.BASE_URL}/commanders/{url_name}"

        print(f"Fetching EDHREC data for {commander_name}...")

        try:
            response = self._retry_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract basic info (this is a simplified example)
            data = {
                "commander": commander_name,
                "url": url,
                "fetched_at": time.time(),
                "cards": self._extract_card_recommendations(soup),
                "themes": self._extract_themes(soup),
            }

            # Cache the result
            self._write_cache(cache_key, data)

            return data

        except Exception as e:
            print(f"Error fetching EDHREC data for {commander_name}: {e}")
            return {
                "commander": commander_name,
                "error": str(e),
                "url": url
            }

    def _extract_card_recommendations(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract card recommendations from EDHREC page."""
        cards = []

        # Helper to check for partial class match
        def class_contains(tag, text):
            return tag.has_attr('class') and any(text in c for c in tag['class'])

        # Try to find new React-style card containers
        card_containers = soup.find_all(lambda t: t.name == 'div' and class_contains(t, 'Card_container'))

        # Fallback to legacy selectors
        if not card_containers:
            card_containers = soup.find_all('div', class_='card-panel') or soup.find_all('a', class_='card')

        for panel in card_containers[:20]:  # Limit to top 20
            card_name = None

            # 1. Extract Name
            # New structure name
            name_span = panel.find(lambda t: t.name == 'span' and class_contains(t, 'Card_name'))
            if name_span:
                card_name = name_span.get_text(strip=True)

            # Legacy structure name or fallback
            if not card_name:
                card_name = panel.get('data-name')

            if not card_name:
                # Only fallback to get_text on panel if it's NOT the new container structure
                # (to avoid grabbing all text in the container)
                is_new_container = panel.name == 'div' and class_contains(panel, 'Card_container')
                if not is_new_container:
                    card_name = panel.get_text(strip=True)

            if not card_name:
                continue

            # 2. Extract Synergy
            synergy_score = "high"  # Default

            # Find "synergy" text within this panel
            synergy_label = panel.find(string=lambda t: t and 'synergy' == t.lower().strip())

            if synergy_label:
                # Expecting structure: <span>Score</span><span>synergy</span>
                label_span = synergy_label.parent
                if label_span:
                    score_span = label_span.find_previous_sibling('span')
                    if score_span:
                        synergy_score = score_span.get_text(strip=True)

            cards.append({
                "name": card_name,
                "synergy": synergy_score
            })

        return cards

    def _extract_themes(self, soup: BeautifulSoup) -> List[str]:
        """Extract deck themes from EDHREC page."""
        themes = []

        # Extract theme information
        theme_sections = soup.find_all('div', class_='theme') or soup.find_all('a', href=lambda x: x and '/themes/' in x if x else False)

        for theme in theme_sections[:10]:  # Limit to top 10
            theme_name = theme.get_text(strip=True)
            if theme_name:
                themes.append(theme_name)

        return themes

    def get_top_commanders(self, timeframe: str = "week", force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of top commanders for a given timeframe.

        Args:
            timeframe: Time period ('week', 'month', 'year', '2years')
            force_refresh: If True, bypass cache

        Returns:
            List of commander data dictionaries
        """
        cache_key = f"top_commanders_{timeframe}"

        # Check cache first
        if not force_refresh:
            cached_data = self._read_cache(cache_key)
            if cached_data:
                print(f"Using cached top commanders for {timeframe}")
                return cached_data.get("commanders", [])

        url = f"{self.BASE_URL}/top/commanders/{timeframe}"

        print(f"Fetching top commanders for {timeframe}...")

        try:
            response = self._retry_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            commanders = []
            # Extract commander cards from the page
            commander_cards = soup.find_all('a', class_='card') or soup.find_all('div', class_='commander')

            for card in commander_cards[:50]:  # Limit to top 50
                name = card.get('data-name') or card.get_text(strip=True)
                if name:
                    commanders.append({
                        "name": name,
                        "timeframe": timeframe
                    })

            data = {
                "commanders": commanders,
                "timeframe": timeframe,
                "fetched_at": time.time()
            }

            # Cache the result
            self._write_cache(cache_key, data)

            return commanders

        except Exception as e:
            print(f"Error fetching top commanders: {e}")
            return []

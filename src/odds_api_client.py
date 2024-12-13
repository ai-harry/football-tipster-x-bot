import os
import json
import time
from datetime import datetime
import requests
import socket
import socks
from typing import Dict, List, Optional
import logging
from cachetools import TTLCache

logger = logging.getLogger(__name__)

class OddsAPIClient:
    """Client for interacting with the Odds API."""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ODDS_API_KEY')
        if not self.api_key:
            raise ValueError("No API key provided")
            
        self.cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour cache
        self.last_request_time = 0
        self.min_request_interval = 5  # Minimum 5 seconds between requests
        
    def _wait_for_rate_limit(self, attempt: int):
        """Wait with exponential backoff."""
        sleep_time = min(60, self.min_request_interval * (2 ** attempt))
        logger.info(f"Rate limiting: waiting {sleep_time:.1f} seconds")
        time.sleep(sleep_time)

    def get_odds(self, sport_key: str, regions: List[str], markets: List[str]) -> Optional[Dict]:
        """Get odds data with caching and rate limiting."""
        try:
            cache_key = f"{sport_key}:{','.join(sorted(regions))}:{','.join(sorted(markets))}"
            
            if cache_key in self.cache:
                logger.info("Returning cached odds data")
                return self.cache[cache_key]
            
            attempt = 0
            while True:
                self._wait_for_rate_limit(attempt)
                
                url = f"{self.BASE_URL}/sports/{sport_key}/odds"
                params = {
                    'apiKey': self.api_key,
                    'regions': ','.join(regions),
                    'markets': ','.join(markets)
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 429:
                    logger.warning("Rate limit hit, retrying with backoff")
                    attempt += 1
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                self.cache[cache_key] = data
                logger.info(f"Cached odds data for {cache_key}")
                
                return data
                
        except Exception as e:
            logger.error(f"Error fetching odds: {str(e)}")
            return None
    
    def save_odds_data(self, data: List[Dict], filename: str = None) -> None:
        """Save odds data to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'odds_data_{timestamp}.json'
        
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2) 
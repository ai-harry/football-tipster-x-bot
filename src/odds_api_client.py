import os
import json
import time
from datetime import datetime
import requests
import socket
import socks
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class OddsAPIClient:
    """Client for interacting with the Odds API."""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_odds(self, sport_key: str, regions: List[str], markets: List[str]) -> Optional[Dict]:
        """Get odds data for a specific sport."""
        try:
            url = f"{self.BASE_URL}/sports/{sport_key}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': ','.join(regions),
                'markets': ','.join(markets)
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise exception for bad status codes
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {sport_key}: {str(e)}")
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
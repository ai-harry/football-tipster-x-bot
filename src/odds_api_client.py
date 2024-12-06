import os
import json
import time
from datetime import datetime
import requests
import socket
import socks
from typing import Dict, List

class OddsAPIClient:
    """Client for interacting with The Odds API."""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        # Store original socket
        self._original_socket = socket.socket
    
    def get_odds(self, 
                 sport: str,
                 regions: List[str] = ['us'],
                 markets: List[str] = ['h2h']) -> List[Dict]:
        """Get odds data for a sport."""
        # Reset socket to original (no proxy)
        socket.socket = self._original_socket
        
        params = {
            'apiKey': self.api_key,
            'regions': ','.join(regions),
            'markets': ','.join(markets)
        }
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/sports/{sport}/odds",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        finally:
            # Restore SOCKS proxy for other connections
            socket.socket = socks.socksocket
    
    def save_odds_data(self, data: List[Dict], filename: str = None) -> None:
        """Save odds data to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'odds_data_{timestamp}.json'
        
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2) 
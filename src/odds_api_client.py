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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        self.MIN_REQUEST_INTERVAL = 5  # 5 seconds between requests
        
        # Configure session with retries
        self.session = requests.Session()
        retries = Retry(
            total=5,  # Total number of retries
            backoff_factor=1,  # Wait 1, 2, 4, 8, 16 seconds between retries
            status_forcelist=[408, 429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["GET"]  # Only retry on GET requests
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Test connection on initialization
        self._test_connection()
        
    def _test_connection(self):
        """Test the connection to the API."""
        try:
            # Try to resolve the hostname
            socket.gethostbyname('api.the-odds-api.com')
            logger.info("Successfully resolved api.the-odds-api.com")
            
            # Test the API connection
            response = self.session.get(f"{self.BASE_URL}/sports", 
                                      params={'apiKey': self.api_key},
                                      timeout=10)
            response.raise_for_status()
            logger.info("Successfully connected to The Odds API")
            
        except socket.gaierror as e:
            logger.error(f"DNS resolution failed: {str(e)}")
            logger.info("Checking system DNS settings...")
            # Log DNS servers for debugging
            try:
                import dns.resolver
                dns_servers = dns.resolver.get_default_resolver().nameservers
                logger.info(f"System DNS servers: {dns_servers}")
            except:
                logger.warning("Could not retrieve DNS server information")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API connection test failed: {str(e)}")
            
    def _wait_for_rate_limit(self, attempt: int):
        """Wait with exponential backoff."""
        sleep_time = min(60, self.MIN_REQUEST_INTERVAL * (2 ** attempt))
        logger.info(f"Rate limiting: waiting {sleep_time:.1f} seconds")
        time.sleep(sleep_time)

    def get_odds(self, sport_key: str, regions: List[str], markets: List[str]) -> Optional[Dict]:
        """Get odds data with caching and rate limiting."""
        try:
            cache_key = f"{sport_key}:{','.join(sorted(regions))}:{','.join(sorted(markets))}"
            
            if cache_key in self.cache:
                logger.info("Returning cached odds data")
                return self.cache[cache_key]
            
            url = f"{self.BASE_URL}/sports/{sport_key}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': ','.join(regions),
                'markets': ','.join(markets)
            }
            
            # Log the request URL (without API key)
            safe_url = url.replace(self.api_key, 'XXXXX')
            logger.info(f"Requesting odds from: {safe_url}")
            
            # Ensure minimum interval between requests
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.MIN_REQUEST_INTERVAL:
                sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last
                logger.info(f"Rate limiting: waiting {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.cache[cache_key] = data
            logger.info(f"Successfully fetched odds for {sport_key}")
            
            return data
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            logger.info("Please check your internet connection and DNS settings")
            return None
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out: {str(e)}")
            return None
            
        except requests.exceptions.RequestException as e:
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
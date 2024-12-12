import tweepy
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TwitterPoster:
    """Handles posting to Twitter/X platform."""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        """Initialize Twitter API client."""
        try:
            # Initialize the Twitter client without proxies
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Test the connection
            self.client.get_me()
            logger.info("Twitter client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            raise

    def post_tweet(self, text: str) -> bool:
        """Post a tweet."""
        try:
            response = self.client.create_tweet(text=text)
            logger.info("Tweet posted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {str(e)}")
            return False
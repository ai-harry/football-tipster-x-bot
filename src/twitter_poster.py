import tweepy
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class TwitterPoster:
    """Posts tweets using Twitter API v2."""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        """Initialize Twitter client."""
        try:
            # Initialize Twitter client with v2 API
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Store account info
            me = self.client.get_me()
            if me.data:
                self.account_info = me.data  # Store the account info
                logger.info(f"Successfully authenticated as @{me.data.username}")
            else:
                raise Exception("Failed to get user information")
            
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            raise

    def post_tweet(self, tweet_text: str) -> Dict:
        """Post a tweet and return the result."""
        try:
            # Post tweet
            response = self.client.create_tweet(text=tweet_text)
            
            # Get tweet ID and construct URL
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/{self.account_info.username}/status/{tweet_id}"
            
            logger.info(f"Tweet posted successfully: {tweet_url}")
            
            return {
                'success': True,
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'account': self.account_info.username
            }
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_credentials(self) -> Dict:
        """Verify Twitter credentials and return account info."""
        try:
            me = self.client.get_me()
            return {
                'success': True,
                'username': me.data.username,
                'id': me.data.id
            }
        except Exception as e:
            logger.error(f"Failed to verify credentials: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
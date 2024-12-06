import tweepy
from typing import Dict

class TwitterPoster:
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        """Initialize Twitter API client with basic authentication."""
        try:
            print(f"\nAttempting Twitter authentication...")
            print(f"API Key: {api_key[:8]}...")
            print(f"Access Token: {access_token[:8]}...")
            
            # Set up authentication
            auth = tweepy.OAuthHandler(api_key, api_secret)
            auth.set_access_token(access_token, access_token_secret)
            
            # Create Client instance (v2 API)
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            
            # Verify credentials using v1 API (just for checking)
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            user = self.api.verify_credentials()
            print(f"✅ Twitter authentication successful as @{user.screen_name}")
            
        except Exception as e:
            print(f"❌ Failed to authenticate with Twitter: {str(e)}")
            raise
    
    def post_tweet(self, tweet_text: str) -> Dict:
        """Post a tweet using Twitter API v2."""
        try:
            # Post tweet using v2 endpoint
            response = self.client.create_tweet(text=tweet_text)
            tweet_id = response.data['id']
            
            print(f"\n✅ Tweet posted successfully!")
            print(f"🔗 https://twitter.com/i/status/{tweet_id}")
            
            return {
                'success': True,
                'tweet_id': tweet_id
            }
            
        except Exception as e:
            print(f"\n❌ Twitter Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 
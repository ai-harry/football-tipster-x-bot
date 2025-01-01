import tweepy
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
import random

logger = logging.getLogger(__name__)

class TwitterPoster:
    """Handles posting to Twitter/X platform with robust rate limit handling."""
    
    def __init__(self, api_key: str = None, api_secret: str = None, 
                 access_token: str = None, access_token_secret: str = None, 
                 test_mode: bool = False):
        """Initialize Twitter API client."""
        self.test_mode = test_mode
        
        # Free tier rate limits
        self.TWEETS_PER_DAY = 17
        self.MINUTES_PER_DAY = 24 * 60
        self.INTERVAL_MINUTES = self.MINUTES_PER_DAY // self.TWEETS_PER_DAY
        
        # Schedule tracking
        self.last_tweet_time = None
        self.next_scheduled_time = None
        self.tweets_posted_today = 0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if test_mode:
            logger.info("Twitter client initialized in TEST MODE")
            return
            
        # try:
        #     # Initialize both v1.1 and v2 clients
        #     auth = tweepy.OAuthHandler(api_key, api_secret)
        #     auth.set_access_token(access_token, access_token_secret)
            
        #     self.api = tweepy.API(auth, wait_on_rate_limit=True)
        #     self.client = tweepy.Client(
        #         consumer_key=api_key,
        #         consumer_secret=api_secret,
        #         access_token=access_token,
        #         access_token_secret=access_token_secret,
        #         wait_on_rate_limit=True
        #     )
            
        #     # Verify credentials
        #     self._verify_credentials()
            
        #     # Calculate first tweet time
        #     self._schedule_next_tweet()
            
        #     logger.info(f"Twitter client initialized successfully. Will post {self.TWEETS_PER_DAY} tweets per day")
        #     logger.info(f"Tweet interval: {self.INTERVAL_MINUTES} minutes")
        #     if self.next_scheduled_time:
        #         logger.info(f"First tweet scheduled for: {self.next_scheduled_time.strftime('%H:%M:%S')}")
            
        # except Exception as e:
        #     logger.error(f"Failed to initialize Twitter client: {str(e)}")
        #     raise

    def _verify_credentials(self):
        """Verify Twitter API credentials."""
        try:
            self.api.verify_credentials()
            self.client.get_me()
            logger.info("Twitter credentials verified successfully")
        except Exception as e:
            logger.error(f"Credential verification failed: {str(e)}")
            raise

    def _schedule_next_tweet(self):
        """Calculate the next tweet time."""
        current_time = datetime.now()
        
        if not self.last_tweet_time:
            # First tweet of the day
            self.next_scheduled_time = current_time
        else:
            # Schedule next tweet at exact interval
            self.next_scheduled_time = self.last_tweet_time + timedelta(minutes=self.INTERVAL_MINUTES)
            
            # If next time is in the past, schedule for now
            if self.next_scheduled_time < current_time:
                self.next_scheduled_time = current_time

    def can_tweet_now(self) -> bool:
        """Check if we can tweet now."""
        self._check_daily_reset()
        
        if self.tweets_posted_today >= self.TWEETS_PER_DAY:
            next_reset = self.daily_reset_time + timedelta(days=1)
            logger.warning(f"Daily tweet limit reached. Next reset at {next_reset.strftime('%H:%M:%S')}")
            return False
            
        current_time = datetime.now()
        
        if not self.next_scheduled_time:
            self._schedule_next_tweet()
            return True
            
        time_until_next = (self.next_scheduled_time - current_time).total_seconds()
        if time_until_next > 0:
            minutes, seconds = divmod(time_until_next, 60)
            logger.info(f"Waiting {int(minutes)} minutes and {int(seconds)} seconds until next tweet window")
            return False
            
        return True

    def post_tweet(self, text: str) -> bool:
        """Post a tweet with precise scheduling."""
        if self.test_mode:
            logger.info(f"TEST MODE - Would tweet: {text}")
            return True
            
        if not self.can_tweet_now():
            logger.info(f"Cannot tweet now. Next tweet scheduled for: {self.next_scheduled_time.strftime('%H:%M:%S')}")
            return False
            
        try:
            # Wait until exact scheduled time
            current_time = datetime.now()
            if self.next_scheduled_time > current_time:
                wait_seconds = (self.next_scheduled_time - current_time).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"Waiting {wait_seconds:.1f} seconds for exact schedule...")
                    time.sleep(wait_seconds)
            
            # Try v2 endpoint first
            try:
                response = self.client.create_tweet(text=text)
                tweet_id = response.data['id']
                logger.info(f"Tweet posted successfully via v2 API. Tweet ID: {tweet_id}")
            except Exception as e:
                # Fallback to v1.1 endpoint
                logger.warning(f"v2 API failed, trying v1.1: {str(e)}")
                status = self.api.update_status(text)
                tweet_id = status.id
                logger.info(f"Tweet posted successfully via v1.1 API. Tweet ID: {tweet_id}")
            
            # Update tracking
            self.last_tweet_time = datetime.now()
            self.tweets_posted_today += 1
            self._schedule_next_tweet()
            
            # Log status
            remaining_tweets = self.TWEETS_PER_DAY - self.tweets_posted_today
            logger.info(f"Tweet posted successfully. {remaining_tweets} tweets remaining today")
            logger.info(f"Next tweet scheduled for: {self.next_scheduled_time.strftime('%H:%M:%S')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {str(e)}")
            return False

    def _check_daily_reset(self):
        """Reset tweet counter at midnight UTC."""
        current_time = datetime.now()
        if current_time.date() > self.daily_reset_time.date():
            logger.info("New day started - resetting tweet counter")
            self.tweets_posted_today = 0
            self.daily_reset_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            self._schedule_next_tweet()

    def get_next_tweet_time(self) -> datetime:
        """Get the next scheduled tweet time."""
        if not self.next_scheduled_time:
            self._schedule_next_tweet()
        
        return self.next_scheduled_time
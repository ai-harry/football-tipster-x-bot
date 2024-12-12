import os
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from src.odds_api_client import OddsAPIClient
from src.openai_analyzer import OddsAnalyzer
from src.tweet_generator import TweetGenerator
from src.twitter_poster import TwitterPoster
from dotenv import load_dotenv
import tweepy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('betting_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BettingBot:
    """Automated betting analysis and tweet posting bot."""
    
    def __init__(self):
        """Initialize the betting bot with all required clients."""
        load_dotenv()
        
        try:
            # Get API keys
            odds_api_key = os.getenv('ODDS_API_KEY')
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not odds_api_key or not openai_api_key:
                raise ValueError("Missing required API keys")
            
            # Initialize clients without proxy settings
            self.odds_client = OddsAPIClient(odds_api_key)
            self.analyzer = OddsAnalyzer(openai_api_key)
            self.tweet_gen = TweetGenerator(openai_api_key)
            
            # Initialize Twitter client
            twitter_api_key = os.getenv('TWITTER_API_KEY')
            twitter_api_secret = os.getenv('TWITTER_API_SECRET')
            twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            
            if not all([twitter_api_key, twitter_api_secret, twitter_access_token, twitter_access_token_secret]):
                raise ValueError("Missing Twitter credentials")
            
            self.twitter = TwitterPoster(
                api_key=twitter_api_key,
                api_secret=twitter_api_secret,
                access_token=twitter_access_token,
                access_token_secret=twitter_access_token_secret
            )
            
            # Track timing and content
            self.last_tweet_time = None
            self.last_analyzed_matches = set()
            
            logger.info("BettingBot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize BettingBot: {str(e)}")
            raise

    def can_post_tweet(self) -> bool:
        """Check if enough time has passed since last tweet."""
        if not self.last_tweet_time:
            return True
            
        time_since_last = datetime.now() - self.last_tweet_time
        if time_since_last.total_seconds() < 3600:  # 1 hour in seconds
            logger.info(f"Only {time_since_last.total_seconds()/60:.1f} minutes since last tweet. Waiting...")
            return False
        return True

    def analyze_and_post(self) -> Optional[Dict]:
        """Run the complete analysis and posting process."""
        try:
            # Check if we can post
            if not self.can_post_tweet():
                return None

            # Updated sport keys to exact API endpoint names
            sports = [
                'soccer_epl',                # English Premier League
                'soccer_spain_la_liga',      # Spanish La Liga
                'soccer_germany_bundesliga', # German Bundesliga
                'soccer_italy_serie_a'       # Italian Serie A
            ]
            
            odds_data = {}
            valuable_matches = []
            
            for sport in sports:
                try:
                    sport_odds = self.odds_client.get_odds(
                        sport_key=sport,
                        regions=['uk', 'eu'],
                        markets=['h2h', 'totals']
                    )
                    
                    if sport_odds:
                        logger.info(f"Successfully fetched odds for {sport}")
                        # Process matches for this sport
                        for match in sport_odds:
                            match_id = f"{match['home_team']}_{match['away_team']}"
                            
                            # Skip recently analyzed matches
                            if match_id in self.last_analyzed_matches:
                                continue
                                
                            # Add to valuable matches if it meets criteria
                            if self._has_betting_value(match):
                                valuable_matches.append({
                                    'match_id': match_id,
                                    'sport': sport,
                                    'match_data': match
                                })
                                logger.info(f"Found valuable match: {match_id}")
                    else:
                        logger.warning(f"No odds data available for {sport}")
                except Exception as e:
                    logger.error(f"Error fetching odds for {sport}: {str(e)}")
                    continue

            if not valuable_matches:
                logger.info("No valuable betting opportunities found")
                return None

            # Sort matches by value potential and take the best one
            valuable_matches.sort(key=self._calculate_value_score, reverse=True)
            best_match = valuable_matches[0]
            logger.info(f"Selected best match: {best_match['match_id']}")

            # Generate and post tweet
            tweet = self.tweet_gen.generate_optimized_tweet(best_match)
            
            if tweet:
                result = self.twitter.post_tweet(tweet)
                
                if result:
                    # Update tracking
                    self.last_tweet_time = datetime.now()
                    self.last_analyzed_matches.add(best_match['match_id'])
                    
                    logger.info(f"Successfully posted tweet at {self.last_tweet_time}")
                    
                    return {
                        'timestamp': self.last_tweet_time,
                        'match': best_match,
                        'tweet': tweet
                    }

            return None

        except Exception as e:
            logger.error(f"Error in analyze_and_post: {str(e)}")
            return None

    def _has_betting_value(self, match: Dict) -> bool:
        """Determine if a match has potential betting value."""
        try:
            # Check if match has bookmakers data
            if not match.get('bookmakers'):
                return False
            
            # Calculate odds variance
            odds_variance = self._calculate_odds_variance(match)
            
            # Lower the threshold to find more matches
            min_variance = 0.10  # Reduced from 0.15
            
            has_value = odds_variance > min_variance
            if has_value:
                logger.info(f"Match {match['home_team']} vs {match['away_team']} has value (variance: {odds_variance:.2f})")
            
            return has_value
            
        except Exception as e:
            logger.error(f"Error checking match value: {str(e)}")
            return False

    def _calculate_odds_variance(self, match: Dict) -> float:
        """Calculate the variance in odds across bookmakers."""
        try:
            all_odds = []
            for bookmaker in match.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            all_odds.append(outcome['price'])
            
            if not all_odds:
                return 0
                
            return max(all_odds) - min(all_odds)
            
        except Exception as e:
            logger.error(f"Error calculating odds variance: {str(e)}")
            return 0

    def _calculate_value_score(self, match: Dict) -> float:
        """Calculate a value score for sorting matches."""
        try:
            odds_variance = self._calculate_odds_variance(match['match_data'])
            return odds_variance
            
        except Exception as e:
            logger.error(f"Error calculating value score: {str(e)}")
            return 0

    def run_scheduled(self):
        """Run the bot on a schedule."""
        logger.info("Starting scheduled bot...")
        
        # Schedule the job to run every 1 hour
        schedule.every(1).hours.do(self.analyze_and_post)
        
        # Run first analysis immediately
        self.analyze_and_post()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Schedule error: {str(e)}")
                time.sleep(300)  # Wait 5 minutes on error before retrying
                continue

def main():
    """Main function to start the bot."""
    try:
        bot = BettingBot()
        bot.run_scheduled()
        
    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}")
        raise

if __name__ == '__main__':
    main() 
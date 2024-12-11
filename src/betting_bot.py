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
            self.odds_client = OddsAPIClient(os.getenv('ODDS_API_KEY'))
            self.analyzer = OddsAnalyzer(os.getenv('OPENAI_API_KEY'))
            self.tweet_gen = TweetGenerator(os.getenv('OPENAI_API_KEY'))
            self.twitter = TwitterPoster(
                api_key=os.getenv('TWITTER_API_KEY'),
                api_secret=os.getenv('TWITTER_API_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            
            # Track posted matches to avoid repetition
            self.posted_matches = {}
            
            logger.info("BettingBot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize BettingBot: {str(e)}")
            raise
    
    def analyze_and_post(self) -> Optional[Dict]:
        """Run the complete analysis and posting process."""
        try:
            # Get current matches data
            odds_data = self.odds_client.get_odds(['soccer_epl', 'soccer_spain_la_liga', 
                                                 'soccer_germany_bundesliga1', 'soccer_italy_serie_a'])
            
            if not odds_data:
                logger.warning("No odds data available")
                return None

            # Filter out already posted matches
            fresh_matches = self._filter_fresh_matches(odds_data)
            
            if not fresh_matches:
                logger.info("No new matches to analyze")
                return None

            # Analyze fresh matches
            analysis = self.analyzer.analyze_odds(fresh_matches)
            
            if not analysis:
                logger.warning("No valuable betting opportunities found")
                return None

            # Generate tweet with fresh analysis
            tweet = self.tweet_gen.generate_optimized_tweet(analysis)
            
            if not tweet:
                logger.error("Failed to generate tweet")
                return None

            # Post tweet
            post_result = self.twitter.post_tweet(tweet)
            
            if post_result:
                # Update posted matches
                self._update_posted_matches(fresh_matches)
                
                return {
                    'timestamp': datetime.now(),
                    'analysis': analysis,
                    'tweet': tweet,
                    'post_result': post_result
                }
            
            return None

        except Exception as e:
            logger.error(f"Error in analyze_and_post: {str(e)}")
            return None

    def _filter_fresh_matches(self, odds_data: Dict) -> Dict:
        """Filter out matches that were already posted about."""
        fresh_matches = {}
        current_time = datetime.now()

        for sport_key, matches in odds_data.items():
            fresh_matches[sport_key] = []
            
            for match in matches:
                match_id = f"{match['home_team']}_{match['away_team']}_{match['commence_time']}"
                
                # Check if match was posted and if it's been less than 4 hours
                if match_id in self.posted_matches:
                    post_time = self.posted_matches[match_id]
                    if (current_time - post_time) < timedelta(hours=4):
                        continue
                
                fresh_matches[sport_key].append(match)

        return fresh_matches

    def _update_posted_matches(self, matches: Dict):
        """Update the record of posted matches."""
        current_time = datetime.now()
        
        # Add new matches
        for sport_key, sport_matches in matches.items():
            for match in sport_matches:
                match_id = f"{match['home_team']}_{match['away_team']}_{match['commence_time']}"
                self.posted_matches[match_id] = current_time

        # Clean up old entries (older than 4 hours)
        self._cleanup_old_matches()

    def _cleanup_old_matches(self):
        """Remove matches older than 4 hours from posted_matches."""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=4)
        
        self.posted_matches = {
            match_id: post_time 
            for match_id, post_time in self.posted_matches.items() 
            if post_time > cutoff_time
        }
    
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
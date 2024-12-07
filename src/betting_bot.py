import os
import schedule
import time
import logging
from datetime import datetime
from typing import Dict, Optional

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
            
            logger.info("BettingBot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize BettingBot: {str(e)}")
            raise
    
    def analyze_and_post(self) -> Optional[Dict]:
        """Run the complete analysis and posting process."""
        try:
            logger.info("Starting analysis and posting process")
            
            # Fetch odds data
            logger.info("Fetching odds data...")
            odds_data = self.odds_client.get_odds('soccer_epl', ['us'], ['h2h'])
            logger.info(f"Found {len(odds_data)} matches to analyze")
            
            if not odds_data:
                logger.warning("No odds data available. Skipping analysis.")
                return None
            
            # Analyze odds
            logger.info("Analyzing odds data...")
            analysis = self.analyzer.analyze_odds(odds_data)
            
            # Generate tweet
            logger.info("Generating tweet...")
            tweet = self.tweet_gen.generate_optimized_tweet(analysis)
            
            if not self.tweet_gen.validate_tweet(tweet):
                logger.error("Generated tweet failed validation")
                return None
            
            # Post tweet
            logger.info("Posting tweet...")
            post_result = self.twitter.post_tweet(tweet)
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results = {
                'timestamp': timestamp,
                'odds_data': odds_data,
                'analysis': analysis,
                'tweet': tweet,
                'twitter_post': post_result
            }
            
            # Save to JSON
            self.analyzer.save_analysis(results, f'analysis_{timestamp}.json')
            
            logger.info("Process completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in analyze_and_post: {str(e)}")
            return None
    
    def run_scheduled(self):
        """Run the bot on a schedule."""
        logger.info("Starting scheduled bot...")
        
        # Schedule the job to run every 2 hours
        schedule.every(2).hours.do(self.analyze_and_post)
        
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
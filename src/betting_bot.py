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
    
    # Add supported sports list
    SUPPORTED_SPORTS = [
        'soccer_epl',                # English Premier League
        'soccer_spain_la_liga',      # Spanish La Liga
        'soccer_germany_bundesliga', # German Bundesliga
        'soccer_italy_serie_a',      # Italian Serie A
        'soccer_france_ligue_one',   # French Ligue 1
        'soccer_uefa_champs_league', # UEFA Champions League
        'soccer_uefa_europa_league'  # UEFA Europa League
    ]
    
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
            
            # Clear the analyzed matches set every 24 hours
            schedule.every(24).hours.do(self.last_analyzed_matches.clear)
            
            logger.info("BettingBot initialized successfully")
            logger.info(f"Monitoring {len(self.SUPPORTED_SPORTS)} sports leagues")
            
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
                logger.info("Skipping this run - too soon since last tweet")
                return None

            # Get current matches
            current_matches = self._get_current_matches()
            
            if not current_matches:
                logger.info("No new matches to analyze")
                return None
            
            # Filter out previously analyzed matches
            new_matches = [
                match for match in current_matches 
                if match['match_id'] not in self.last_analyzed_matches
            ]
            
            if not new_matches:
                logger.info("All current matches have been analyzed")
                return None

            # Sort by value and get best match
            best_match = self._get_best_match(new_matches)
            
            if not best_match:
                logger.info("No valuable matches found")
                return None

            # Generate and post tweet
            tweet = self.tweet_gen.generate_optimized_tweet(best_match)
            
            if tweet:
                result = self.twitter.post_tweet(tweet)
                
                if result:
                    # Update tracking
                    self.last_tweet_time = datetime.now()
                    self.last_analyzed_matches.add(best_match['match_id'])
                    
                    logger.info(f"Successfully posted tweet at {self.last_tweet_time}")
                    logger.info(f"Next scheduled run will be at {schedule.next_run()}")
                    
                    return {
                        'timestamp': self.last_tweet_time,
                        'match': best_match,
                        'tweet': tweet
                    }

            return None

        except Exception as e:
            logger.error(f"Error in analyze_and_post: {str(e)}")
            return None

    def _get_current_matches(self) -> List[Dict]:
        """Get current matches to analyze."""
        try:
            matches = []
            for sport in self.SUPPORTED_SPORTS:
                try:
                    logger.info(f"Fetching odds for {sport}")
                    sport_odds = self.odds_client.get_odds(
                        sport_key=sport,
                        regions=['uk', 'eu'],
                        markets=['h2h', 'totals']
                    )
                    if sport_odds:
                        logger.info(f"Found {len(sport_odds)} matches for {sport}")
                        for match in sport_odds:
                            match_id = f"{match['home_team']}_{match['away_team']}"
                            matches.append({
                                'match_id': match_id,
                                'sport': sport,
                                'match_data': match
                            })
                    else:
                        logger.info(f"No matches found for {sport}")
                except Exception as e:
                    logger.error(f"Error fetching odds for {sport}: {str(e)}")
                    continue
                
            logger.info(f"Total matches found across all sports: {len(matches)}")
            return matches
        except Exception as e:
            logger.error(f"Error getting current matches: {str(e)}")
            return []

    def _get_best_match(self, matches: List[Dict]) -> Optional[Dict]:
        """Get the best match based on value."""
        try:
            valuable_matches = [
                match for match in matches 
                if self._has_betting_value(match['match_data'])
            ]
            
            if not valuable_matches:
                return None
            
            # Sort by value score
            valuable_matches.sort(
                key=lambda x: self._calculate_value_score(x['match_data']), 
                reverse=True
            )
            
            return valuable_matches[0]
            
        except Exception as e:
            logger.error(f"Error getting best match: {str(e)}")
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
        try:
            logger.info("Starting scheduled bot...")
            
            # Schedule the job to run every 1 hour
            schedule.every(1).hours.do(self.analyze_and_post)
            
            # Run first analysis immediately
            self.analyze_and_post()
            
            # Keep the script running
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                    
                    next_run = schedule.next_run()
                    if next_run:
                        time_until_next = next_run - datetime.now()
                        logger.info(f"Scheduler is running... Next run in {time_until_next.seconds//60} minutes")
                    
                except Exception as e:
                    logger.error(f"Schedule iteration error: {str(e)}")
                    time.sleep(300)  # Wait 5 minutes on error
                    continue
                
        except Exception as e:
            logger.error(f"Critical error in scheduler: {str(e)}")
            raise

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
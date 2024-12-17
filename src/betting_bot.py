import os
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
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('betting_bot.log', mode='w', encoding='utf-8'),
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
    
    def __init__(self, test_mode: bool = False):
        """Initialize the betting bot with all required clients."""
        load_dotenv()
        
        try:
            # Get API keys from environment variables
            odds_api_key = os.getenv('ODDS_API_KEY')
            openai_api_key = os.getenv('OPENAI_API_KEY')
            openai_org_id = os.getenv('OPENAI_ORG_ID')  # Get org ID from env
            
            if not all([odds_api_key, openai_api_key]):
                raise ValueError("Missing required environment variables")
            
            # Initialize clients
            self.odds_client = OddsAPIClient(odds_api_key)
            self.analyzer = OddsAnalyzer(openai_api_key, openai_org_id)  # Pass org ID
            self.tweet_gen = TweetGenerator()
            
            # Initialize Twitter in test mode or with credentials
            if test_mode:
                self.twitter = TwitterPoster(test_mode=True)
            else:
                twitter_api_key = os.getenv('TWITTER_API_KEY')
                twitter_api_secret = os.getenv('TWITTER_API_SECRET')
                twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
                twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
                
                if not all([twitter_api_key, twitter_api_secret, 
                           twitter_access_token, twitter_access_token_secret]):
                    raise ValueError("Missing Twitter credentials")
                    
                self.twitter = TwitterPoster(
                    api_key=twitter_api_key,
                    api_secret=twitter_api_secret,
                    access_token=twitter_access_token,
                    access_token_secret=twitter_access_token_secret
                )
            
            # Initialize tracking variables
            self.last_tweet_time = None
            self.tweeted_matches = {}
            self.recent_tweets = set()
            self.analyzed_matches = set()
            
            # Start a background thread for cleanup
            self._start_cleanup_thread()
            
            logger.info("BettingBot initialized successfully")
            logger.info(f"Monitoring {len(self.SUPPORTED_SPORTS)} sports leagues")
            
        except Exception as e:
            logger.error(f"Failed to initialize BettingBot: {str(e)}")
            raise

    def _start_cleanup_thread(self):
        """Start a background thread to clean up old matches every 24 hours."""
        def cleanup_loop():
            while True:
                time.sleep(86400)  # 24 hours
                self._clear_old_matches()
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()

    def _clear_old_matches(self):
        """Clear matches older than 24 hours."""
        current_time = datetime.now()
        # Keep only matches from last 24 hours
        self.tweeted_matches = {
            match_id: timestamp 
            for match_id, timestamp in self.tweeted_matches.items()
            if (current_time - timestamp).total_seconds() < 86400  # 24 hours
        }
        logger.info(f"Cleared old matches. Currently tracking {len(self.tweeted_matches)} matches")

    def can_post_tweet(self) -> bool:
        """Check if enough time has passed since last tweet."""
        if not self.last_tweet_time:
            return True
        
        time_since_last = datetime.now() - self.last_tweet_time
        if time_since_last.total_seconds() < 3600:  # Exactly 1 hour in seconds
            logger.info(f"Only {time_since_last.total_seconds()/60:.1f} minutes since last tweet. Waiting...")
            return False
        return True

    def analyze_and_post(self):
        """Analyze matches and post about the best value bet."""
        try:
            # Get current matches
            current_matches = self._get_current_matches()
            
            if not current_matches:
                logger.info("No matches found to analyze")
                return
            
            # Filter out already tweeted matches
            new_matches = []
            for match in current_matches:
                if not self._is_duplicate(match):
                    new_matches.append(match)
            
            if not new_matches:
                logger.info("No new matches to analyze")
                return

            # Process only one match at a time
            for match in new_matches[:1]:  # Take only the first match
                if not self.twitter.can_tweet_now():
                    logger.info("Waiting for next tweet window")
                    return
                    
                # Generate and post tweet
                try:
                    tweet_text = self.tweet_gen.generate_tweet(match)
                    if not tweet_text:
                        logger.warning("Failed to generate tweet text")
                        continue
                    
                    success = self.twitter.post_tweet(tweet_text)
                    if success:
                        match_id = f"{match['match_data']['home_team']}-{match['match_data']['away_team']}"
                        self.tweeted_matches[match_id] = datetime.now()
                        logger.info(f"Successfully tweeted about match: {match_id}")
                        break
                    else:
                        logger.warning("Failed to post tweet")
                
                    # If posting failed, wait before trying next match
                    time.sleep(5)
                
                except Exception as e:
                    logger.error(f"Error processing match: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in analyze_and_post: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)

    def _get_current_matches(self) -> List[Dict]:
        """Get current matches to analyze."""
        try:
            matches = []
            total_matches = 0
            max_matches_per_league = 3  # Limit matches per league
            
            for sport in self.SUPPORTED_SPORTS:
                try:
                    logger.info(f"Fetching odds for {sport}")
                    sport_odds = self.odds_client.get_odds(
                        sport_key=sport,
                        regions=['uk', 'eu'],
                        markets=['h2h', 'totals']
                    )
                    
                    if sport_odds:
                        # Sort matches by start time and take only the closest ones
                        sorted_matches = sorted(
                            sport_odds,
                            key=lambda x: x.get('commence_time', ''),
                            reverse=False
                        )[:max_matches_per_league]
                        
                        logger.info(f"Found {len(sorted_matches)} matches for {sport}")
                        
                        for match in sorted_matches:
                            match_id = f"{match['home_team']}_{match['away_team']}"
                            matches.append({
                                'match_id': match_id,
                                'sport': sport,
                                'match_data': match
                            })
                            total_matches += 1
                            
                            # Add delay between processing matches
                            time.sleep(1)  # 1 second delay between matches
                            
                    else:
                        logger.info(f"No matches found for {sport}")
                        
                    # Add delay between leagues
                    time.sleep(2)  # 2 seconds delay between leagues
                    
                except Exception as e:
                    logger.error(f"Error fetching odds for {sport}: {str(e)}")
                    continue
                    
            logger.info(f"Total matches found across all sports: {total_matches}")
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
            # Ensure we're accessing the match data correctly
            match_data = match.get('match_data', match)  # Handle both direct match data and wrapped match objects
            
            # Calculate odds variance
            odds_variance = self._calculate_odds_variance(match_data)
            
            # Log for debugging
            logger.info(f"Calculated value score: {odds_variance} for match: {match_data.get('home_team')} vs {match_data.get('away_team')}")
            
            return odds_variance
            
        except Exception as e:
            logger.error(f"Error calculating value score: {str(e)}")
            return 0.0

    def run_scheduled(self):
        """Run the bot continuously."""
        logger.info("Starting automated betting bot")
        
        while True:
            try:
                current_time = datetime.now()
                
                # Check if we can tweet
                if self.twitter.can_tweet_now():
                    self.analyze_and_post()
                else:
                    # Calculate time until next tweet
                    next_time = self.twitter.next_scheduled_time
                    if next_time:
                        time_until_next = (next_time - current_time).total_seconds()
                        minutes, seconds = divmod(time_until_next, 60)
                        logger.info(f"Waiting {int(minutes)} minutes and {int(seconds)} seconds until next tweet window")
                
                # Sleep for 5 minutes before next check
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in scheduler: {str(e)}")
                time.sleep(300)  # Wait 5 minutes on error
                continue

    def _is_duplicate(self, match: Dict) -> bool:
        """Check if match has already been tweeted or analyzed."""
        try:
            # Extract team names from match_data
            home_team = match['match_data']['home_team']
            away_team = match['match_data']['away_team']
            
            match_id = f"{home_team}-{away_team}"
            reverse_id = f"{away_team}-{home_team}"
            
            # Check if match was already tweeted
            if match_id in self.tweeted_matches or reverse_id in self.tweeted_matches:
                logger.info(f"Skipping duplicate match: {match_id}")
                return True
            
            # Check if match was analyzed recently
            if match_id in self.analyzed_matches:
                logger.info(f"Match was recently analyzed: {match_id}")
                return True
            
            # Add to analyzed matches
            self.analyzed_matches.add(match_id)
            logger.debug(f"New match added to analysis: {match_id}")
            return False
        
        except KeyError as e:
            logger.error(f"Invalid match data structure: {str(e)}")
            logger.debug(f"Match data: {match}")
            return True
        except Exception as e:
            logger.error(f"Error checking duplicate match: {str(e)}")
            return True

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
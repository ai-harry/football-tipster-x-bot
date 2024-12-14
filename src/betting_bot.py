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
        logging.FileHandler('betting_bot.log', mode='w'),
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
            self.analyzed_team_pairs = set()
            self.recent_tweets = set()
            
            # Clear tracking sets every 24 hours
            schedule.every(24).hours.do(self._clear_tracking_data)
            
            logger.info("BettingBot initialized successfully")
            logger.info(f"Monitoring {len(self.SUPPORTED_SPORTS)} sports leagues")
            
        except Exception as e:
            logger.error(f"Failed to initialize BettingBot: {str(e)}")
            raise

    def _clear_tracking_data(self):
        """Clear tracking data for matches and teams."""
        self.last_analyzed_matches.clear()
        self.analyzed_team_pairs.clear()
        self.recent_tweets.clear()
        logger.info("Cleared tracking data")

    def can_post_tweet(self) -> bool:
        """Check if enough time has passed since last tweet."""
        if not self.last_tweet_time:
            return True
        
        time_since_last = datetime.now() - self.last_tweet_time
        if time_since_last.total_seconds() < 3600:  # 1 hour in seconds (changed from 1800)
            logger.info(f"Only {time_since_last.total_seconds()/60:.1f} minutes since last tweet. Waiting...")
            return False
        return True

    def analyze_and_post(self) -> Optional[Dict]:
        """Run the complete analysis and posting process."""
        try:
            current_time = datetime.now()
            logger.info(f"=== Starting new analysis cycle at {current_time} ===")
            
            # Check if we can post
            if not self.can_post_tweet():
                logger.info("Waiting for next cycle due to time restriction")
                return None
            
            # Get current matches
            current_matches = self._get_current_matches()
            
            if not current_matches:
                logger.info("No matches found to analyze")
                return None
            
            # Filter out duplicates and recently analyzed matches
            new_matches = [
                match for match in current_matches 
                if not self._is_duplicate_match(match) and
                match['match_id'] not in self.last_analyzed_matches
            ]
            
            if not new_matches:
                logger.info("No new matches to analyze")
                return None

            # Get best match and post
            best_match = self._get_best_match(new_matches)
            if best_match:
                tweet = self.tweet_gen.generate_optimized_tweet(best_match)
                if tweet and tweet not in self.recent_tweets:
                    result = self.twitter.post_tweet(tweet)
                    if result:
                        self.last_tweet_time = current_time
                        self.last_analyzed_matches.add(best_match['match_id'])
                        self.recent_tweets.add(tweet)
                        
                        # Schedule next run exactly one hour from now
                        next_run = current_time + timedelta(hours=1)
                        logger.info(f"=== Successfully posted new tweet ===")
                        logger.info(f"Match: {best_match['match_data']['home_team']} vs {best_match['match_data']['away_team']}")
                        logger.info(f"Next analysis scheduled for: {next_run}")
                        logger.info("=== Analysis cycle complete ===")
                        
                        return {
                            'timestamp': current_time,
                            'match': best_match,
                            'tweet': tweet
                        }
                else:
                    logger.info("Tweet already posted or invalid")
            else:
                logger.info("No valuable matches found")
            
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
        """Run the bot on a schedule."""
        try:
            logger.info("=== Starting scheduled bot ===")
            
            # Run first analysis immediately
            logger.info("Running initial analysis...")
            self.analyze_and_post()
            
            # Schedule to run every hour (changed from 30 minutes)
            schedule.every().hour.at(":00").do(self.analyze_and_post)
            
            # Keep the script running
            while True:
                try:
                    schedule.run_pending()
                    
                    # Log time until next run
                    next_run = schedule.next_run()
                    if next_run:
                        time_until = (next_run - datetime.now()).total_seconds() / 60
                        logger.info(f"=== Next scheduled run in {time_until:.1f} minutes ===")
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Schedule iteration error: {str(e)}")
                    time.sleep(300)  # Wait 5 minutes on error
                    continue
                
        except Exception as e:
            logger.error(f"Critical error in scheduler: {str(e)}")
            raise

    def _is_duplicate_match(self, match: Dict) -> bool:
        """Check if this match or team combination has been analyzed recently."""
        try:
            home_team = match['match_data']['home_team']
            away_team = match['match_data']['away_team']
            team_pair = f"{home_team}-{away_team}"
            
            # Check if we've already analyzed this team combination
            if team_pair in self.analyzed_team_pairs:
                logger.info(f"Skipping duplicate match: {team_pair}")
                return True
                
            # Add to tracked teams
            self.analyzed_team_pairs.add(team_pair)
            return False
            
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
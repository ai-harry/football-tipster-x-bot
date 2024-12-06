import os
import json
from datetime import datetime, timedelta
from typing import List, Dict
from odds_api_client import OddsAPIClient
from openai_analyzer import OddsAnalyzer
from tweet_generator import TweetGenerator
from twitter_poster import TwitterPoster
from dotenv import load_dotenv
import time

# Priority leagues for analysis
PRIORITY_LEAGUES = [
    'soccer_epl',           # English Premier League
    'soccer_spain_la_liga', # Spanish La Liga
    'soccer_germany_bundesliga1'  # German Bundesliga
]

# Available markets in free tier
MARKETS = ['h2h']  # Free tier only supports h2h markets

class RequestTracker:
    """Track API requests to stay within limits"""
    def __init__(self, max_requests=500):
        self.max_requests = max_requests
        self.current_requests = 0
        self.last_request_time = None
        
    def can_make_request(self) -> bool:
        """Check if we can make another request"""
        if self.current_requests >= self.max_requests:
            return False
        
        # Ensure at least 1 second between requests to avoid rate limiting
        if self.last_request_time and (datetime.now() - self.last_request_time).total_seconds() < 1:
            time.sleep(1)
        
        return True
    
    def log_request(self):
        """Log a successful request"""
        self.current_requests += 1
        self.last_request_time = datetime.now()

def get_optimized_odds_data(odds_client: OddsAPIClient, request_tracker: RequestTracker) -> Dict:
    """Fetch optimized odds data within API limits"""
    optimized_data = {
        'timestamp': datetime.now().isoformat(),
        'leagues': {},
        'request_count': 0
    }
    
    for league in PRIORITY_LEAGUES:
        try:
            if not request_tracker.can_make_request():
                print("WARNING: Approaching API request limit. Stopping data collection.")
                break
                
            print(f"Fetching data for {league}...")
            league_data = {
                'current_odds': {},
                'matches': []
            }
            
            # Fetch current odds
            if request_tracker.can_make_request():
                odds_response = odds_client.get_odds(
                    sport=league,
                    regions=['us', 'uk'],  # Prioritize major regions
                    markets=MARKETS
                )
                request_tracker.log_request()
                
                if odds_response:
                    league_data['current_odds'] = odds_response
                    
                    # Extract matches for detailed analysis
                    for game in odds_response:
                        match_data = {
                            'home_team': game.get('home_team'),
                            'away_team': game.get('away_team'),
                            'commence_time': game.get('commence_time'),
                            'bookmaker_odds': {},
                            'analysis': {}
                        }
                        
                        # Calculate average odds and odds movement
                        home_odds = []
                        away_odds = []
                        draw_odds = []
                        
                        for site in game.get('sites', []):
                            if 'odds' in site and 'h2h' in site['odds']:
                                match_data['bookmaker_odds'][site['site_key']] = {
                                    'odds': site['odds']['h2h'],
                                    'last_update': site['last_update']
                                }
                                home_odds.append(site['odds']['h2h'][0])
                                away_odds.append(site['odds']['h2h'][1])
                                if len(site['odds']['h2h']) > 2:
                                    draw_odds.append(site['odds']['h2h'][2])
                        
                        # Basic statistical analysis
                        if home_odds and away_odds:
                            match_data['analysis'] = {
                                'avg_home_odds': sum(home_odds) / len(home_odds),
                                'avg_away_odds': sum(away_odds) / len(away_odds),
                                'avg_draw_odds': sum(draw_odds) / len(draw_odds) if draw_odds else None,
                                'odds_variance': {
                                    'home': max(home_odds) - min(home_odds),
                                    'away': max(away_odds) - min(away_odds),
                                    'draw': max(draw_odds) - min(draw_odds) if draw_odds else None
                                },
                                'bookmaker_confidence': len(game.get('sites', [])),
                            }
                        
                        league_data['matches'].append(match_data)
            
            optimized_data['leagues'][league] = league_data
            
        except Exception as e:
            print(f"Error fetching data for {league}: {str(e)}")
            continue
    
    optimized_data['request_count'] = request_tracker.current_requests
    return optimized_data

def main():
    """Main function to fetch odds and generate analysis."""
    load_dotenv()
    print("Starting optimized analysis process...")
    
    try:
        print("Initializing clients...")
        odds_client = OddsAPIClient(os.getenv('ODDS_API_KEY'))
        analyzer = OddsAnalyzer(os.getenv('OPENAI_API_KEY'))
        tweet_gen = TweetGenerator(os.getenv('OPENAI_API_KEY'))
        twitter = TwitterPoster(
            api_key=os.getenv('TWITTER_API_KEY'),
            api_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        )
        
        request_tracker = RequestTracker(max_requests=450)  # Leave buffer for safety
        
        print("Fetching optimized odds data...")
        optimized_odds_data = get_optimized_odds_data(odds_client, request_tracker)
        
        print("Analyzing data...")
        analysis = analyzer.analyze_optimized_odds(optimized_odds_data)
        
        print("Generating insights...")
        insights = {
            'odds_analysis': analysis,
            'value_bets': analyzer.identify_value_bets(optimized_odds_data),
            'request_usage': request_tracker.current_requests
        }
        
        print("Generating tweet...")
        tweet = tweet_gen.generate_optimized_tweet(insights)
        
        print("Posting to Twitter...")
        post_result = twitter.post_tweet(tweet)
        
        print("Saving results...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'analysis_results_{timestamp}.json'
        
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'odds_data': optimized_odds_data,
                'analysis': insights,
                'twitter_post': post_result
            }, f, indent=4)
        
        print(f"\nProcess completed successfully! Results saved to {output_file}")
        print(f"API Requests used: {request_tracker.current_requests}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        with open('error_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()}: {str(e)}\n")

if __name__ == '__main__':
    main() 
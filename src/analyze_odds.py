import os
import json
from odds_api_client import OddsAPIClient
from openai_analyzer import OddsAnalyzer
from tweet_generator import TweetGenerator
from twitter_poster import TwitterPoster
from dotenv import load_dotenv

def main():
    """Main function to fetch odds and generate analysis."""
    load_dotenv()
    print("Starting process...")
    
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
        
        print("Fetching odds data...")
        odds_data = odds_client.get_odds('soccer_epl', ['us'], ['h2h'])
        print(f"Found {len(odds_data)} matches")
        
        print("Analyzing odds...")
        analysis = analyzer.analyze_odds(odds_data)
        
        print("Generating tweet...")
        tweet = tweet_gen.generate_tweet(analysis)
        
        print("Posting to Twitter...")
        post_result = twitter.post_tweet(tweet)
        
        print("Saving results...")
        analysis['twitter_post'] = post_result
        analyzer.save_analysis(analysis, 'analysis_with_tweet.json')
        
        print("\nProcess completed successfully!")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == '__main__':
    main() 
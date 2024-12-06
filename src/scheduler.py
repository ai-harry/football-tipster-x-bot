import schedule
import time
from datetime import datetime
import os
from dotenv import load_dotenv
from odds_api_client import OddsAPIClient
from openai_analyzer import OddsAnalyzer
from tweet_generator import TweetGenerator
from twitter_poster import TwitterPoster

def job():
    """Run the analysis and posting job"""
    try:
        print(f"\n🕒 Starting scheduled job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize clients
        odds_client = OddsAPIClient(os.getenv('ODDS_API_KEY'))
        analyzer = OddsAnalyzer(os.getenv('OPENAI_API_KEY'))
        tweet_gen = TweetGenerator(os.getenv('OPENAI_API_KEY'))
        twitter = TwitterPoster(
            api_key=os.getenv('TWITTER_API_KEY'),
            api_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        )
        
        # Fetch and analyze odds
        odds_data = odds_client.get_odds(
            sport='soccer_epl',
            regions=['us', 'uk'],
            markets=['h2h']
        )
        
        if odds_data:
            # Analyze odds
            analysis = analyzer.analyze_optimized_odds(odds_data)
            
            # Generate and post tweet
            tweet = tweet_gen.generate_optimized_tweet(analysis)
            if tweet:
                result = twitter.post_tweet(tweet)
                print(f"✅ Tweet posted: {result['tweet_url']}")
            
            # Save analysis
            analyzer.save_analysis(analysis)
        
        print("✅ Job completed successfully")
        
    except Exception as e:
        print(f"❌ Error in scheduled job: {str(e)}")

def run_scheduler():
    """Run the scheduler"""
    load_dotenv()  # Load environment variables
    
    # Schedule the job every 2 hours
    schedule.every(2).hours.do(job)
    
    # Run the job immediately once
    job()
    
    print("🤖 Bot started! Running every 2 hours...")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute for pending jobs

if __name__ == "__main__":
    run_scheduler() 
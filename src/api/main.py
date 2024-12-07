from fastapi import FastAPI, HTTPException, BackgroundTasks
from threading import Thread, Event
import logging
import sys
import os
from typing import Dict

# Import from src package
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
        logging.FileHandler('betting_bot_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Football Betting Bot API")

# Global variables for controlling the automation
automation_thread: Thread = None
stop_event = Event()
automation_status = {"running": False, "last_error": None}

def run_automation():
    """Background task that runs the betting automation"""
    try:
        load_dotenv()
        
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
        
        logger.info("Automation started")
        
        while not stop_event.is_set():
            try:
                # Fetch odds data
                odds_data = odds_client.get_odds(
                    sport='soccer_epl',
                    regions=['us', 'uk'],
                    markets=['h2h']
                )
                
                if odds_data:
                    # Analyze odds
                    analysis = analyzer.analyze_odds(odds_data)
                    
                    # Generate and post tweet
                    tweet = tweet_gen.generate_optimized_tweet(analysis)
                    if tweet:
                        result = twitter.post_tweet(tweet)
                        logger.info(f"Tweet posted: {result.get('tweet_url')}")
                    
                    # Save analysis
                    analyzer.save_analysis(analysis)
                
                # Wait for 2 hours before next iteration
                stop_event.wait(7200)  # 2 hours in seconds
                
            except Exception as e:
                logger.error(f"Error in automation loop: {str(e)}")
                automation_status["last_error"] = str(e)
                stop_event.wait(300)  # Wait 5 minutes on error
                
    except Exception as e:
        logger.error(f"Critical error in automation: {str(e)}")
        automation_status["last_error"] = str(e)
    finally:
        automation_status["running"] = False
        logger.info("Automation stopped")

@app.post("/start")
async def start_automation(background_tasks: BackgroundTasks) -> Dict:
    """Start the betting automation"""
    global automation_thread, stop_event
    
    if automation_status["running"]:
        raise HTTPException(status_code=400, detail="Automation is already running")
    
    try:
        # Reset the stop event and status
        stop_event.clear()
        automation_status["running"] = True
        automation_status["last_error"] = None
        
        # Start automation in background thread
        automation_thread = Thread(target=run_automation)
        automation_thread.start()
        
        logger.info("Automation process started")
        return {"status": "started", "message": "Betting automation started successfully"}
        
    except Exception as e:
        logger.error(f"Failed to start automation: {str(e)}")
        automation_status["running"] = False
        automation_status["last_error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
async def stop_automation() -> Dict:
    """Stop the betting automation"""
    global automation_thread, stop_event
    
    if not automation_status["running"]:
        raise HTTPException(status_code=400, detail="Automation is not running")
    
    try:
        # Signal the automation to stop
        stop_event.set()
        
        # Wait for thread to finish
        if automation_thread and automation_thread.is_alive():
            automation_thread.join(timeout=30)
        
        automation_status["running"] = False
        logger.info("Automation process stopped")
        return {"status": "stopped", "message": "Betting automation stopped successfully"}
        
    except Exception as e:
        logger.error(f"Failed to stop automation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status() -> Dict:
    """Get current automation status"""
    return {
        "running": automation_status["running"],
        "last_error": automation_status["last_error"]
    }

@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Football Betting Bot API",
        "version": "1.0",
        "endpoints": {
            "start": "/start",
            "stop": "/stop",
            "status": "/status",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
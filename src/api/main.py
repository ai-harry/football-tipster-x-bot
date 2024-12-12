from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from threading import Thread, Event
import logging
import sys
import os
from typing import Dict, Optional
from dotenv import load_dotenv

# Update the import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.betting_bot import BettingBot
from src.api.models import TwitterCredentials, PromptTemplate, PromptUpdateResponse, ConfigResponse
from src.api.config_manager import ConfigManager

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

app = FastAPI(title="Football Betting Bot API", description="API for managing football betting automation and configuration")
config_manager = ConfigManager()

# Global variables for controlling the automation
automation_thread: Thread = None
stop_event = Event()
automation_status = {"running": False, "last_error": None}

def run_automation():
    """Background task that runs the betting automation"""
    try:
        load_dotenv()
        
        # Initialize betting bot
        bot = BettingBot()
        
        logger.info("Automation started")
        
        while not stop_event.is_set():
            try:
                # Run one iteration of analysis and posting
                result = bot.analyze_and_post()
                if result:
                    logger.info("Successfully completed analysis and posting")
                
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

@app.post("/configure/twitter-credentials", tags=["Configuration"])
async def configure_twitter_credentials(
    credentials: TwitterCredentials
) -> ConfigResponse:
    """
    Configure Twitter API credentials for the bot.
    
    Example request:    ```json
    {
        "api_key": "your_api_key",
        "api_secret": "your_api_secret",
        "access_token": "your_access_token",
        "access_token_secret": "your_access_token_secret"
    }    ```
    """
    success = config_manager.set_twitter_credentials(credentials)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to save credentials")
    
    return ConfigResponse(
        success=True,
        message="Twitter credentials configured successfully"
    )

@app.get("/configure/prompt", tags=["Configuration"])
async def get_prompt_template() -> PromptUpdateResponse:
    """Get the current prompt template used for bet analysis."""
    template = config_manager.get_prompt_template()
    return PromptUpdateResponse(
        success=True,
        message="Current prompt template retrieved",
        current_template=template
    )

@app.post("/configure/prompt", tags=["Configuration"])
async def update_prompt_template(
    prompt: PromptTemplate
) -> PromptUpdateResponse:
    """
    Update the prompt template used for bet analysis.
    
    Example request:    ```json
    {
        "template": "Analyze this bet: {bet_details}\n\nConsider: {analysis_points}"
    }    ```
    """
    success = config_manager.set_prompt_template(prompt)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update prompt template")
    
    return PromptUpdateResponse(
        success=True,
        message="Prompt template updated successfully",
        current_template=prompt.template
    )

@app.post("/start", tags=["Automation"])
async def start_automation(background_tasks: BackgroundTasks) -> ConfigResponse:
    """
    Start the betting automation.
    
    Requires Twitter credentials to be configured first.
    """
    global automation_thread, stop_event
    
    # Check if automation is already running
    if automation_status["running"]:
        raise HTTPException(status_code=400, detail="Automation is already running")
    
    # Check for Twitter credentials
    credentials = config_manager.get_twitter_credentials()
    if not credentials:
        raise HTTPException(
            status_code=400,
            detail="Twitter credentials not configured. Please configure credentials first."
        )
    
    try:
        # Reset the stop event and status
        stop_event.clear()
        automation_status["running"] = True
        automation_status["last_error"] = None
        
        # Start automation in background thread
        automation_thread = Thread(target=run_automation)
        automation_thread.start()
        
        logger.info("Automation process started")
        return ConfigResponse(success=True, message="Betting automation started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start automation: {str(e)}")
        automation_status["running"] = False
        automation_status["last_error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop", tags=["Automation"])
async def stop_automation() -> ConfigResponse:
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
        return ConfigResponse(success=True, message="Betting automation stopped successfully")
        
    except Exception as e:
        logger.error(f"Failed to stop automation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", tags=["Automation"])
async def get_status() -> Dict:
    """Get current automation status"""
    return {
        "running": automation_status["running"],
        "last_error": automation_status["last_error"]
    }

@app.get("/health", tags=["System"])
async def health_check() -> Dict:
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Football Betting Bot API",
        "version": "1.0",
        "endpoints": {
            "configuration": {
                "twitter_credentials": "/configure/twitter-credentials",
                "prompt": "/configure/prompt"
            },
            "automation": {
                "start": "/start",
                "stop": "/stop",
                "status": "/status"
            },
            "system": {
                "health": "/health",
                "docs": "/docs"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
from fastapi import FastAPI, HTTPException
from typing import Dict
from src.betting_bot import BettingBot
import logging
from dotenv import load_dotenv

app = FastAPI(title="Football Betting Bot API")
bot = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "message": "Football Betting Bot API"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/start")
async def start_automation():
    """Start the betting automation."""
    global bot
    try:
        if bot is None:
            bot = BettingBot()
        
        # Start the automation
        bot.run_scheduled()
        return {"status": "success", "message": "Automation process started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
async def stop_automation():
    """Stop the betting automation."""
    global bot
    try:
        if bot:
            bot = None
        return {"status": "success", "message": "Automation stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """Get automation status."""
    return {
        "status": "running" if bot is not None else "stopped",
        "message": "Automation is running" if bot is not None else "Automation is stopped"
    } 
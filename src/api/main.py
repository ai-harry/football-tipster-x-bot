from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from src.betting_bot import BettingBot
from src.chat_handler import ChatHandler
from pydantic import BaseModel
import logging
from dotenv import load_dotenv

app = FastAPI(title="Sports Analytics Bot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

bot = None
chat_handler = None

class ChatQuery(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str

@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "message": "Sports Analytics Bot API"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    """Chat endpoint for terminal interaction."""
    global bot, chat_handler
    try:
        if not chat_handler:
            return {"response": "System not initialized. Please start the bot first."}
        
        response = await chat_handler.handle_query(query.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/start")
# async def start_automation(background_tasks: BackgroundTasks):
#     """Start the betting automation."""
#     global bot, chat_handler
#     try:
#         if bot is None:
#             bot = BettingBot()
#             chat_handler = ChatHandler(bot)
        
#         # Run the automation in a background task
#         background_tasks.add_task(bot.run_scheduled)
#         return {"status": "success", "message": "Automation process started"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/stop")
# async def stop_automation():
#     """Stop the betting automation."""
#     global bot, chat_handler
#     try:
#         if bot:
#             bot = None
#             chat_handler = None
#         return {"status": "success", "message": "Automation stopped"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/status")
# async def get_status():
#     """Get automation status."""
#     return {
#         "status": "running" if bot is not None else "stopped",
#         "message": "Automation is running" if bot is not None else "Automation is stopped"
#     } 

@app.on_event("startup")
async def startup_event():
    global bot, chat_handler
    if bot is None:
        # Initialize with test_mode=False for production
        bot = BettingBot(test_mode=False)
    if chat_handler is None:
        chat_handler = ChatHandler(bot)
  
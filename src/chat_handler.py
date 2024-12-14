from typing import Dict, List, Optional
import openai
import logging
from datetime import datetime
from src.betting_bot import BettingBot
import os
import json

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, bot: BettingBot):
        self.bot = bot
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.functions = [
            {
                "name": "get_current_value_bets",
                "description": "Get current value betting opportunities using real-time odds data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "min_value_threshold": {
                            "type": "number",
                            "description": "Minimum value threshold percentage"
                        }
                    }
                }
            },
            {
                "name": "get_live_matches",
                "description": "Get current live matches and odds",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "league": {
                            "type": "string",
                            "description": "League name (optional)",
                            "enum": ["EPL", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
                        }
                    }
                }
            }
        ]

    async def handle_query(self, query: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a betting analysis assistant. Use the available tools to provide real-time odds and value betting opportunities."
                    },
                    {"role": "user", "content": query}
                ],
                tools=self.functions,
                tool_choice="auto"
            )

            tool_call = response.choices[0].message.tool_calls[0] if response.choices[0].message.tool_calls else None
            
            if tool_call:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                if tool_name == "get_current_value_bets":
                    result = await self._get_current_value_bets(
                        min_value_threshold=tool_args.get("min_value_threshold", 5)
                    )
                elif tool_name == "get_live_matches":
                    result = await self._get_live_matches(
                        league=tool_args.get("league")
                    )
                else:
                    result = "Unknown tool called"
                
                return result
            
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Chat handling error: {str(e)}")
            return f"Error processing request: {str(e)}"

    async def _get_current_value_bets(self, min_value_threshold: float = 5.0) -> str:
        try:
            matches = self.bot._get_current_matches()
            
            value_bets = []
            for match in matches:
                value_score = self.bot._calculate_value_score(match)
                if value_score > min_value_threshold:
                    match_data = match['match_data']
                    value_bets.append({
                        'match': f"{match_data['home_team']} vs {match_data['away_team']}",
                        'league': match['sport'],
                        'value_score': value_score,
                        'odds': self._get_best_odds(match_data)
                    })
            
            if not value_bets:
                return "No value betting opportunities found at this time."
            
            response = f"Found {len(value_bets)} value betting opportunities:\n\n"
            for bet in value_bets:
                response += f"🎯 {bet['match']} ({bet['league']})\n"
                response += f"Value Score: {bet['value_score']:.1f}%\n"
                response += f"Best Odds: {bet['odds']}\n\n"
            
            response += f"\nAnalysis based on current odds as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            return response

        except Exception as e:
            logger.error(f"Error getting value bets: {str(e)}")
            return "Error analyzing value bets"

    async def _get_live_matches(self, league: Optional[str] = None) -> str:
        try:
            matches = self.bot._get_current_matches()
            
            if league:
                matches = [m for m in matches if league.lower() in m['sport'].lower()]
            
            if not matches:
                return f"No live matches found{' for ' + league if league else ''}"
            
            response = f"Current matches{' in ' + league if league else ''}:\n\n"
            
            for match in matches[:5]:
                match_data = match['match_data']
                response += f"⚽ {match_data['home_team']} vs {match_data['away_team']}\n"
                response += f"League: {match['sport']}\n"
                response += f"Odds: {self._get_best_odds(match_data)}\n\n"
            
            response += f"\nOdds updated as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            return response

        except Exception as e:
            logger.error(f"Error getting live matches: {str(e)}")
            return "Error fetching live matches"

    def _get_best_odds(self, match_data: Dict) -> str:
        best_odds = {'home': 0, 'away': 0}
        
        for bookmaker in match_data.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        if outcome['name'] == match_data['home_team']:
                            best_odds['home'] = max(best_odds['home'], outcome['price'])
                        elif outcome['name'] == match_data['away_team']:
                            best_odds['away'] = max(best_odds['away'], outcome['price'])
        
        return f"Home: {best_odds['home']:.2f}, Away: {best_odds['away']:.2f}"
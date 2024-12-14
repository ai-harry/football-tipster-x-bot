from typing import Dict, List, Optional
import openai
import logging
from datetime import datetime
from src.betting_bot import BettingBot
import os

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, bot: BettingBot):
        self.bot = bot
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.functions = [
            {
                "name": "get_odds",
                "description": "Get current betting odds for a team or match",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "league": {
                            "type": "string",
                            "description": "The league name (EPL, La Liga, etc.)",
                            "enum": ["EPL", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
                        },
                        "team": {
                            "type": "string",
                            "description": "The team name to get odds for"
                        }
                    },
                    "required": ["team"]
                }
            },
            {
                "name": "analyze_value",
                "description": "Analyze betting value for a specific match",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "match": {
                            "type": "string",
                            "description": "The match to analyze (format: Team1 vs Team2)"
                        }
                    },
                    "required": ["match"]
                }
            },
            {
                "name": "get_matches",
                "description": "Get upcoming matches for a league",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "league": {
                            "type": "string",
                            "description": "The league name",
                            "enum": ["EPL", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
                        }
                    },
                    "required": ["league"]
                }
            },
            {
                "name": "system_status",
                "description": "Check the current status of the betting bot",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    async def handle_query(self, query: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": query}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Chat handling error: {str(e)}")
            return "Failed to process query"

    async def _execute_function(self, function_call: Dict) -> str:
        name = function_call["name"]
        args = eval(function_call["arguments"])  # Note: Be careful with eval in production

        if name == "get_odds":
            return await self._get_odds(args.get("league"), args.get("team"))
        elif name == "analyze_value":
            return await self._analyze_value(args.get("match"))
        elif name == "get_matches":
            return await self._get_matches(args.get("league"))
        elif name == "system_status":
            return await self._system_status()
        else:
            return "Unknown function called"

    async def _get_odds(self, league: Optional[str], team: str) -> str:
        matches = self.bot._get_current_matches()
        for match in matches:
            if team.lower() in match['match_data']['home_team'].lower() or \
               team.lower() in match['match_data']['away_team'].lower():
                odds = self._format_match_odds(match['match_data'])
                return f"Odds for {team}:\n{odds}"
        return f"No upcoming matches found for {team}"

    async def _analyze_value(self, match: str) -> str:
        matches = self.bot._get_current_matches()
        for m in matches:
            match_str = f"{m['match_data']['home_team']} vs {m['match_data']['away_team']}"
            if match.lower() in match_str.lower():
                value_score = self.bot._calculate_value_score(m)
                return f"Value analysis for {match_str}:\nValue Score: {value_score:.2f}\n"
        return f"Match not found: {match}"

    async def _get_matches(self, league: str) -> str:
        matches = self.bot._get_current_matches()
        league_matches = [m for m in matches if league.lower() in m['sport'].lower()]
        if not league_matches:
            return f"No upcoming matches found for {league}"
        
        response = f"Upcoming {league} matches:\n"
        for match in league_matches[:5]:  # Show first 5 matches
            response += f"• {match['match_data']['home_team']} vs {match['match_data']['away_team']}\n"
        return response

    async def _system_status(self) -> str:
        last_tweet = self.bot.last_tweet_time
        if not last_tweet:
            return "System is running but hasn't posted any tweets yet"
        
        time_since = datetime.now() - last_tweet
        next_post = 60 - (time_since.total_seconds() / 60)
        
        return (f"System Status:\n"
                f"• Running: Yes\n"
                f"• Last Tweet: {last_tweet.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"• Next Post In: {next_post:.1f} minutes\n"
                f"• Tracked Matches: {len(self.bot.tweeted_matches)}")

    def _format_match_odds(self, match: Dict) -> str:
        odds_str = f"Match: {match['home_team']} vs {match['away_team']}\n"
        for bookmaker in match.get('bookmakers', [])[:1]:  # Show first bookmaker
            odds_str += f"Bookmaker: {bookmaker['title']}\n"
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        odds_str += f"• {outcome['name']}: {outcome['price']:.2f}\n"
        return odds_str 
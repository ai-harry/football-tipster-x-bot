from datetime import datetime
import random
import logging
from typing import Dict, Optional
from openai import OpenAI
from .api.utils import create_openai_client

logger = logging.getLogger(__name__)

class TweetGenerator:
    """Generates tweets from odds analysis using OpenAI."""
    
    LEAGUE_DISPLAY = {
        'soccer_epl': 'Premier League',
        'soccer_spain_la_liga': 'La Liga',
        'soccer_germany_bundesliga': 'Bundesliga',
        'soccer_italy_serie_a': 'Serie A'
    }
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        try:
            self.client = create_openai_client(api_key)
            logger.info("Tweet generator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize tweet generator: {str(e)}")
            raise
        
    def generate_optimized_tweet(self, data: Dict) -> str:
        """Generate a tweet with specific betting insights."""
        try:
            match_data = data['match_data']
            sport = data['sport']
            
            # Extract odds and calculate probabilities
            odds_info = self._extract_odds_info(match_data)
            if not odds_info:
                return None
                
            # Format match details
            match_details = self._format_match_details(
                match_data, 
                sport, 
                odds_info
            )
            
            # Create prompts
            system_prompt = """You are an expert football betting analyst sharing valuable insights. Your tweets must:

1. Always include specific teams and exact odds
2. Highlight the best available odds and clear value opportunities
3. Include one concrete stat or recent form information
4. Explain why the odds represent value
5. Sound natural while being precise and informative

Avoid:
- Vague statements about "patterns" or "trends"
- Generic phrases like "worth watching" or "keep an eye on"
- Tweets without specific odds or probabilities
- Marketing-style language or excessive hype
- Repetitive phrases or structures"""

            user_prompt = f"""Create a valuable betting insight tweet for this match:

{match_details}

Requirements:
1. Start with a brief, natural greeting
2. Mention both teams and the specific league
3. State the best available odds clearly
4. Explain the value based on probability comparison
5. Include one relevant team stat or form info
6. Add 1-2 relevant hashtags
7. Keep under 280 characters
8. Sound like a knowledgeable bettor sharing insights

Example structure:
"[Greeting] [League] value: [Team] @ [odds] vs [Team]. [Specific stat]. Our analysis shows [X]% probability vs implied [Y]%. [Value explanation] #[League] #BettingValue"
"""

            # Generate tweet using the new OpenAI client structure
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            tweet = response.choices[0].message.content.strip()
            
            if len(tweet) > 280:
                tweet = self._trim_tweet(tweet)
            
            return tweet
            
        except Exception as e:
            logger.error(f"Tweet generation error: {str(e)}")
            return None

    def _extract_odds_info(self, match_data: Dict) -> Dict:
        """Extract and analyze odds from match data."""
        try:
            best_odds = {'home': 0, 'away': 0, 'draw': 0}
            implied_probs = {'home': 0, 'away': 0, 'draw': 0}
            
            for bookmaker in match_data.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            odds = outcome['price']
                            implied_prob = (1 / odds) * 100
                            
                            if outcome['name'] == match_data['home_team']:
                                best_odds['home'] = max(best_odds['home'], odds)
                                implied_probs['home'] = implied_prob
                            elif outcome['name'] == match_data['away_team']:
                                best_odds['away'] = max(best_odds['away'], odds)
                                implied_probs['away'] = implied_prob
                            else:
                                best_odds['draw'] = max(best_odds['draw'], odds)
                                implied_probs['draw'] = implied_prob
            
            return {
                'best_odds': best_odds,
                'implied_probs': implied_probs
            }
            
        except Exception as e:
            logger.error(f"Error extracting odds info: {str(e)}")
            return None

    def _format_match_details(self, match_data: Dict, sport: str, odds_info: Dict) -> str:
        """Format match details for the prompt."""
        league_name = self.LEAGUE_DISPLAY.get(sport, sport)
        
        return f"""Match: {match_data['home_team']} vs {match_data['away_team']}
League: {league_name}
Start Time: {match_data.get('commence_time', 'Unknown')}

Best Available Odds:
- Home Win: {odds_info['best_odds']['home']:.2f} (Implied {odds_info['implied_probs']['home']:.1f}%)
- Away Win: {odds_info['best_odds']['away']:.2f} (Implied {odds_info['implied_probs']['away']:.1f}%)
- Draw: {odds_info['best_odds']['draw']:.2f} (Implied {odds_info['implied_probs']['draw']:.1f}%)

Recent Form:
{self._get_form_info(match_data)}"""

    def _get_form_info(self, match_data: Dict) -> str:
        """Extract form information if available."""
        home_team = match_data['home_team']
        away_team = match_data['away_team']
        
        # You can expand this to include actual form data from your data source
        return f"- {home_team}: Recent performance and stats\n- {away_team}: Recent performance and stats"

    def _trim_tweet(self, tweet: str) -> str:
        """Trim tweet while maintaining readability."""
        if len(tweet) <= 280:
            return tweet
            
        sentences = tweet.split('.')
        trimmed = ''
        for sentence in sentences:
            if len(trimmed + sentence + '.') <= 277:
                trimmed += sentence + '.'
            else:
                break
        
        return trimmed.strip() + '...'
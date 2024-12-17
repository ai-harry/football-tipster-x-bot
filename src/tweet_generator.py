from datetime import datetime
import random
import logging
from typing import Dict, Optional
import openai
import os

logger = logging.getLogger(__name__)

class TweetGenerator:
    """Generates tweets from odds analysis using OpenAI GPT-4."""
    
    def __init__(self, api_key: str = None):
        """Initialize OpenAI client."""
        self.client = openai.OpenAI(api_key=api_key)
        
        # System prompt for GPT-4
        self.system_prompt = """You are an expert football betting analyst. Generate concise, informative tweets about betting opportunities.
Focus on:
1. Exact odds and implied probabilities
2. Value betting opportunities
3. Key statistics and insights
4. Clear betting recommendations
Keep tweets professional and data-driven."""

        self.user_prompt_template = """Create a betting analysis tweet for:
Match: {match}
League: {league}
Odds: {odds}
Value Analysis: {analysis}

Requirements:
1. No greetings or introductions
2. State the best available odds clearly
3. Explain the value based on probability comparison
4. Include one relevant team stat or form info
5. Add 1-2 relevant hashtags
6. Keep under 280 characters
7. Sound like a knowledgeable bettor
8. Do not use colons or quotation marks
9. Include exact odds and probabilities
10. Highlight any significant value opportunities
11. Be specific about betting recommendations"""

        logger.info("Tweet generator initialized successfully")

    def generate_tweet(self, match_data: Dict) -> Optional[str]:
        """Generate a tweet using GPT-4."""
        try:
            # Extract match details
            home_team = match_data['match_data']['home_team']
            away_team = match_data['match_data']['away_team']
            sport = match_data['sport']
            
            # Get odds and probabilities
            odds_info = self._extract_odds_info(match_data['match_data'])
            if not odds_info:
                return None

            # Format match details for GPT-4
            match_details = {
                'match': f"{home_team} vs {away_team}",
                'league': self._get_league_name(sport),
                'odds': self._format_odds(odds_info),
                'analysis': self._analyze_value(odds_info)
            }

            # Get GPT-4 response
            response = self.client.chat.completions.create(
                model="gpt-4",  # Specifically use GPT-4
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.user_prompt_template.format(**match_details)}
                ],
                temperature=0.7,
                max_tokens=150
            )

            tweet = response.choices[0].message.content.strip()
            
            # Ensure hashtags are present
            if not any(tag in tweet for tag in ['#EPL', '#LaLiga', '#Bundesliga', '#SerieA', '#Ligue1', '#UCL', '#UEL']):
                tweet += f" {self._get_league_hashtag(sport)}"
            if '#FootballBetting' not in tweet:
                tweet += ' #FootballBetting'
            if '#ValueBet' not in tweet:
                tweet += ' #ValueBet'

            # Trim if needed
            if len(tweet) > 280:
                tweet = tweet[:277] + "..."

            logger.info(f"Generated tweet: {tweet}")
            return tweet

        except Exception as e:
            logger.error(f"Tweet generation error: {str(e)}")
            return None

    def _extract_odds_info(self, match_data: Dict) -> Dict:
        """Extract and process odds information."""
        best_odds = {'home': 0, 'away': 0, 'draw': 0}
        bookmaker_count = 0
        
        for bookmaker in match_data.get('bookmakers', []):
            bookmaker_count += 1
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        if outcome['name'] == match_data['home_team']:
                            best_odds['home'] = max(best_odds['home'], outcome['price'])
                        elif outcome['name'] == match_data['away_team']:
                            best_odds['away'] = max(best_odds['away'], outcome['price'])
                        else:
                            best_odds['draw'] = max(best_odds['draw'], outcome['price'])

        if not bookmaker_count:
            return None

        # Calculate implied probabilities
        implied_prob = {
            'home': round((1 / best_odds['home']) * 100, 1) if best_odds['home'] else 0,
            'away': round((1 / best_odds['away']) * 100, 1) if best_odds['away'] else 0,
            'draw': round((1 / best_odds['draw']) * 100, 1) if best_odds['draw'] else 0
        }

        return {
            'odds': best_odds,
            'probabilities': implied_prob,
            'bookmaker_count': bookmaker_count
        }

    def _format_odds(self, odds_info: Dict) -> str:
        """Format odds information for the prompt."""
        odds = odds_info['odds']
        probs = odds_info['probabilities']
        return (
            f"Home: {odds['home']:.2f} ({probs['home']}%), "
            f"Draw: {odds['draw']:.2f} ({probs['draw']}%), "
            f"Away: {odds['away']:.2f} ({probs['away']}%)"
        )

    def _analyze_value(self, odds_info: Dict) -> str:
        """Analyze betting value."""
        odds = odds_info['odds']
        probs = odds_info['probabilities']
        
        analysis = []
        
        # Check for high odds value
        max_odds = max(odds.values())
        if max_odds > 3.5:
            analysis.append(f"High potential return at {max_odds:.2f}")
            
        # Check for strong favorites
        max_prob = max(probs.values())
        if max_prob > 65:
            analysis.append(f"Strong favorite with {max_prob:.1f}% implied probability")
            
        # Check for competitive matchup
        if all(30 < p < 45 for p in probs.values()):
            analysis.append("Very competitive matchup with balanced odds")

        return '. '.join(analysis) if analysis else "No significant value detected"

    def _get_league_name(self, sport: str) -> str:
        """Get human-readable league name."""
        return {
            'soccer_epl': 'English Premier League',
            'soccer_spain_la_liga': 'La Liga',
            'soccer_germany_bundesliga': 'Bundesliga',
            'soccer_italy_serie_a': 'Serie A',
            'soccer_france_ligue_one': 'Ligue 1',
            'soccer_uefa_champs_league': 'UEFA Champions League',
            'soccer_uefa_europa_league': 'UEFA Europa League'
        }.get(sport, 'Football')

    def _get_league_hashtag(self, sport: str) -> str:
        """Get league-specific hashtag."""
        return {
            'soccer_epl': '#EPL',
            'soccer_spain_la_liga': '#LaLiga',
            'soccer_germany_bundesliga': '#Bundesliga',
            'soccer_italy_serie_a': '#SerieA',
            'soccer_france_ligue_one': '#Ligue1',
            'soccer_uefa_champs_league': '#UCL',
            'soccer_uefa_europa_league': '#UEL'
        }.get(sport, '#Football')
from datetime import datetime
import random
import logging
from typing import Dict, Set
from openai import OpenAI

logger = logging.getLogger(__name__)

class TweetGenerator:
    """Generates human-like tweets for sports betting insights."""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client and tweet components."""
        self.client = OpenAI(api_key=api_key)
        
        # Dynamic components for tweet variation
        self.greetings = {
            'morning': [
                "☀️ Early value spotted!",
                "🌅 Morning football fans!",
                "📊 Starting the day with this",
                "☕️ Early analysis for today"
            ],
            'afternoon': [
                "👋 Afternoon insight",
                "🎯 Just analyzed this one",
                "💭 Interesting odds alert",
                "📱 Quick midday update"
            ],
            'evening': [
                "🌆 Evening value pick",
                "👀 Night games looking good",
                "💡 Late action worth checking",
                "🤔 Interesting evening odds"
            ]
        }
        
        self.analysis_phrases = [
            "Form suggests",
            "Stats showing",
            "Numbers indicate",
            "Recent performance hints",
            "Data points to",
            "Trends showing"
        ]
        
        self.confidence_expressions = [
            "Looking solid",
            "Seems promising",
            "Worth considering",
            "Catching my eye",
            "Interesting value"
        ]
        
        self.used_phrases = set()  # Track recently used phrases

    def generate_optimized_tweet(self, analysis: Dict) -> str:
        """Generate a natural-sounding tweet based on betting analysis."""
        try:
            # Get time-appropriate greeting
            hour = datetime.now().hour
            time_of_day = (
                'morning' if 5 <= hour < 12
                else 'afternoon' if 12 <= hour < 18
                else 'evening'
            )
            
            # Select fresh phrases
            greeting = self._get_unique_phrase(self.greetings[time_of_day])
            analysis_phrase = self._get_unique_phrase(self.analysis_phrases)
            confidence = self._get_unique_phrase(self.confidence_expressions)
            
            # Create context for GPT
            prompt = self._create_prompt(
                analysis=analysis,
                greeting=greeting,
                analysis_phrase=analysis_phrase,
                confidence=confidence
            )
            
            # Generate tweet using GPT-4
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                presence_penalty=0.6,
                frequency_penalty=0.7
            )
            
            tweet = response.choices[0].message.content
            
            # Ensure tweet length
            if len(tweet) > 280:
                tweet = self._trim_tweet(tweet)
            
            return tweet
            
        except Exception as e:
            logger.error(f"Error generating tweet: {str(e)}")
            return self._generate_fallback_tweet(analysis)

    def _get_unique_phrase(self, phrases: list) -> str:
        """Get a phrase that hasn't been used recently."""
        available = [p for p in phrases if p not in self.used_phrases]
        if not available:
            available = phrases
            self.used_phrases.clear()
        
        phrase = random.choice(available)
        self.used_phrases.add(phrase)
        return phrase

    def _create_prompt(self, analysis: Dict, greeting: str, 
                      analysis_phrase: str, confidence: str) -> str:
        """Create a detailed prompt for GPT."""
        return f"""Create a natural, conversational tweet about this betting insight:

Match Details:
{self._format_match_details(analysis)}

Use these components naturally (but don't force all of them):
- Greeting: {greeting}
- Analysis phrase: {analysis_phrase}
- Confidence: {confidence}

Make it sound like a real person sharing their thoughts:
1. Be conversational and authentic
2. Include specific odds or stats naturally
3. Add one relevant emoji (not too many)
4. Use 1-2 natural hashtags
5. Keep it under 280 characters"""

    def _format_match_details(self, analysis: Dict) -> str:
        """Format match details for the prompt."""
        match_info = analysis.get('match_info', {})
        return f"""
Teams: {match_info.get('home_team')} vs {match_info.get('away_team')}
Current Odds: {match_info.get('odds')}
Key Stats: {match_info.get('key_stats', 'Recent form shows interesting pattern')}
Value Rating: {match_info.get('value_rating', 'Medium')}
"""

    def _trim_tweet(self, tweet: str) -> str:
        """Trim tweet to fit character limit while maintaining readability."""
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

    def _generate_fallback_tweet(self, analysis: Dict) -> str:
        """Generate a simple fallback tweet if main generation fails."""
        match_info = analysis.get('match_info', {})
        return (
            f"📊 Value alert for {match_info.get('home_team')} vs "
            f"{match_info.get('away_team')}! Odds: {match_info.get('odds')} "
            f"#FootballBetting"
        )

    # System prompt for GPT
    SYSTEM_PROMPT = """You are a casual sports betting enthusiast sharing insights with friends. 
Your style is:
- Natural and conversational
- Knowledgeable but not overly technical
- Friendly but professional
- Focused on sharing valuable insights

Avoid:
- Marketing language
- Excessive emojis
- Overly enthusiastic tone
- Bot-like patterns
- Repetitive phrases"""
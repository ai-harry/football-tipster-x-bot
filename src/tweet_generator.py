import os
from typing import Dict
from openai import OpenAI

class TweetGenerator:
    """Generates tweets from odds analysis using OpenAI GPT-4."""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=api_key)
        
        # Enhanced system prompt for GPT-4 with X guidelines
        self.TWEET_PROMPT = """You are a friendly and knowledgeable sports betting analyst who shares valuable insights on X (Twitter). Your style is conversational yet professional, like talking to a trusted friend who's an expert in sports betting.

Your tweets MUST:
1. Use a natural, conversational tone (e.g., "Hey football fans! 👋")
2. Share specific, actionable tips based on data
3. Include actual odds and probability percentages
4. Reference concrete historical stats or recent performance
5. Stay within 280 characters
6. Use strategic emojis to enhance readability
7. Include 2-3 relevant hashtags
8. Add brief responsible betting reminders

Content Structure:
1. Start with a friendly greeting or hook
2. Share the specific tip with actual team names
3. Back it up with key stats or odds
4. End with a clear, actionable insight
5. Add relevant hashtags

Example Format:
"🎯 Value Alert! [Team] showing strong form with [specific stat]. Odds of [X.XX] suggest [Y]% probability - our analysis shows [Z]% chance! Worth considering for today's match. #FootballTips #SmartBetting"

Remember: Be friendly and conversational while maintaining professionalism and responsible betting practices."""

    def generate_optimized_tweet(self, insights: Dict) -> str:
        """Generate an optimized tweet using GPT-4."""
        try:
            # Create a more detailed summary for GPT-4
            summary = "Today's Football Analysis:\n"
            
            # Extract league analysis with more detail
            for league, analyses in insights.get('odds_analysis', {}).get('league_analysis', {}).items():
                if analyses:  # Only add if there are analyses
                    for match_analysis in analyses:
                        match_info = match_analysis.get('match', '')
                        analysis_text = match_analysis.get('analysis', '')
                        value_rating = match_analysis.get('value_rating', '')
                        historical_data = match_analysis.get('historical_performance', '')
                        summary += f"\n{match_info}:\n- Analysis: {analysis_text[:200]}...\n- Value Rating: {value_rating}\n- Historical Data: {historical_data}"
            
            # Add value bets with detailed probability analysis
            if insights.get('value_bets'):
                summary += "\n\nTop Value Betting Opportunities:"
                for bet in insights['value_bets'][:2]:  # Limit to 2 value bets
                    match_name = bet.get('match', '')
                    confidence = bet.get('confidence_level', 0)
                    odds_var = bet.get('odds_variance', {})
                    implied_prob = bet.get('implied_probability', 0)
                    actual_prob = bet.get('calculated_probability', 0)
                    summary += f"\n{match_name}:\n- Confidence: {confidence}/10\n- Best Odds: {odds_var}\n- Implied Prob: {implied_prob}%\n- Our Calculated Prob: {actual_prob}%"

            # Add instruction for human-like, specific tips
            prompt = f"""Generate a friendly, conversational tweet about the best betting opportunity from this analysis. 
Make it sound natural and engaging, like a knowledgeable friend sharing a valuable tip.

Requirements:
1. Start with a friendly greeting or attention-grabbing hook
2. Use the actual team names and specific odds/probabilities
3. Include at least one concrete stat or historical fact
4. End with a clear, actionable insight
5. Add 2-3 relevant hashtags
6. Keep it conversational and human-like
7. Stay under 280 characters

Analysis data:
{summary}"""

            # Generate tweet using GPT-4
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.TWEET_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                presence_penalty=0.6,
                frequency_penalty=0.3
            )
            
            tweet = response.choices[0].message.content
            
            # Ensure tweet is within limits
            if len(tweet) > 280:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Compress this tweet to under 280 characters while keeping the specific team names and key insights:"},
                        {"role": "user", "content": tweet}
                    ],
                    temperature=0.2,
                    max_tokens=100
                )
                tweet = response.choices[0].message.content[:277] + "..."
            
            return tweet
            
        except Exception as e:
            print(f"\n❌ Tweet generation error: {str(e)}")
            return "🎯 Analyzing today's football matches for value betting opportunities. Updates coming soon! #FootballBetting #BettingTips"
    
    def validate_tweet(self, tweet: str) -> bool:
        """Validate tweet length and content."""
        if len(tweet) > 280:
            return False
        if not tweet.strip():
            return False
        return True
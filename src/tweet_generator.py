import os
from typing import Dict
from openai import OpenAI

class TweetGenerator:
    """Generates tweets from odds analysis using OpenAI GPT-4."""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=api_key)
        
        # Enhanced system prompt for GPT-4 with X guidelines
        self.TWEET_PROMPT = """You are an expert sports betting analyst creating engaging tweets that strictly comply with X's (Twitter's) guidelines and terms of service.

Your tweets MUST:
1. Follow X's content policies and community guidelines
2. Avoid any harmful, abusive, or misleading content
3. Not engage in spam or platform manipulation
4. Respect intellectual property rights
5. Include appropriate disclaimers when necessary

Content Guidelines:
1. Informative yet concise
2. Include key statistics and odds
3. Highlight the best value bets with detailed probability analysis
4. Use appropriate emojis strategically
5. Include relevant hashtags
6. Stay within 280 characters
7. Provide clear risk assessment
8. Reference historical performance data
9. Include responsible gambling disclaimers when appropriate
10. Avoid making absolute predictions or guarantees

Format:
- Lead with key insight or value bet
- Include specific odds and implied probabilities
- Add context from historical data
- End with clear, responsible prediction
- Use 2-3 relevant hashtags
- Add brief responsible betting reminder when appropriate

Remember: Always maintain professional tone and promote responsible betting practices."""

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
                        summary += f"\n{match_info}: {analysis_text[:200]}..."
            
            # Add value bets with detailed probability analysis
            if insights.get('value_bets'):
                summary += "\n\nValue Betting Opportunities:"
                for bet in insights['value_bets'][:2]:  # Limit to 2 value bets
                    match_name = bet.get('match', '')
                    confidence = bet.get('confidence_level', 0)
                    odds_var = bet.get('odds_variance', {})
                    summary += f"\n{match_name} (Confidence: {confidence}/10)"
                    if odds_var:
                        summary += f" Best odds: {odds_var}"

            # Add instruction to use real team names
            prompt = f"""Generate a tweet about the best betting opportunity from this analysis. 
Use the actual team names from the matches. Do not use generic 'Team A' or 'Team B'.
Make sure to include:
1. The specific teams involved
2. The actual odds and probabilities
3. Relevant historical stats
4. League name if available
5. A responsible betting reminder

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
import os
from typing import Dict
import socket
import socks
from openai import OpenAI

class TweetGenerator:
    """Generates tweets from betting analysis using OpenAI."""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self.api_key = api_key
        # Store original socket
        self._original_socket = socket.socket
        
    def generate_tweet(self, analysis: Dict) -> str:
        """Generate a tweet from betting analysis.
        
        Args:
            analysis: Dictionary containing betting analysis
            
        Returns:
            Generated tweet text
            
        Raises:
            openai.OpenAIError: If API call fails
        """
        try:
            # Reset socket to original (no proxy)
            socket.socket = self._original_socket
            
            # Initialize OpenAI client
            client = OpenAI(api_key=self.api_key)
            
            # Create prompt for tweet generation
            prompt = f"""
            Create an engaging sports betting tweet based on this analysis:
            {analysis['analysis']}

            Follow these specific guidelines:
            1. Structure:
               - Start with an attention-grabbing hook
               - Include one key betting insight
               - End with a clear value proposition
               - Add 2-3 relevant emojis strategically placed

            2. Content Requirements:
               - Focus on the strongest betting opportunity
               - Use specific team names
               - Include one key statistic or trend
               - Maintain professional tone while being engaging
               - Avoid direct odds mentions (compliance)

            3. Format:
               - Maximum 280 characters
               - Use line breaks for readability
               - Include hashtags: #FootballBetting #SoccerPicks
               - End with a call-to-action

            Example Format:
            🚨 [Attention Hook]
            [Key Insight about Match]
            [Value Proposition]
            #FootballBetting #SoccerPicks

            Make it compelling but responsible, avoiding aggressive gambling language.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional sports betting analyst creating engaging social media content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100,
                presence_penalty=0.6
            )
            
            tweet = response.choices[0].message.content.strip()
            
            # Ensure tweet meets length requirements
            if len(tweet) > 280:
                tweet = tweet[:277] + "..."
                
            return tweet
            
        except Exception as e:
            print(f"\n❌ Error generating tweet: {str(e)}")
            raise
        finally:
            # Restore SOCKS proxy for other connections
            socket.socket = socks.socksocket
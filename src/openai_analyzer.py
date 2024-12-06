import os
import json
from datetime import datetime
from typing import Dict, List
from openai import OpenAI

class OddsAnalyzer:
    """Analyzes football odds data using OpenAI API."""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=api_key)
    
    def analyze_odds(self, odds_data: List[Dict]) -> Dict:
        """Analyze odds data using OpenAI API."""
        try:
            prompt = self._create_analysis_prompt(odds_data[:1])
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Analyze this match briefly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis': response.choices[0].message.content,
                'analyzed_matches': 1,
                'model_used': 'gpt-3.5-turbo'
            }
            
        except Exception as e:
            print(f"\n❌ OpenAI API error: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis': "Unable to analyze due to API connection error.",
                'analyzed_matches': 0,
                'error': str(e)
            }
    
    def _create_analysis_prompt(self, odds_data: List[Dict]) -> str:
        """Create analysis prompt from odds data.
        
        Args:
            odds_data: List of odds data
            
        Returns:
            Formatted prompt string
        """
        matches = []
        for match in odds_data:
            match_info = (
                f"Match: {match['home_team']} vs {match['away_team']}\n"
                f"League: {match['sport_key']}\n"
                "Odds:\n"
            )
            
            # Add bookmaker odds
            for bookmaker in match['bookmakers']:
                match_info += f"{bookmaker['title']}:\n"
                for market in bookmaker['markets']:
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            match_info += f"- {outcome['name']}: {outcome['price']}\n"
            
            matches.append(match_info)
        
        prompt = "Please analyze these football matches and odds:\n\n"
        prompt += "\n---\n".join(matches)
        return prompt
    
    def save_analysis(self, analysis: Dict, filename: str = None) -> None:
        """Save analysis results to JSON file.
        
        Args:
            analysis: Analysis results dictionary
            filename: Optional filename, defaults to timestamp
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'analysis_{timestamp}.json'
        
        os.makedirs('analysis', exist_ok=True)
        filepath = os.path.join('analysis', filename)
        
        with open(filepath, 'w') as f:
            json.dump(analysis, f, indent=2)
            
        print(f"Analysis saved to {filepath}") 
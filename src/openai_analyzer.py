import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class OddsAnalyzer:
    """Analyzes football odds data using OpenAI API."""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        try:
            # Simple initialization
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI analyzer: {str(e)}")
            raise
        
        # System prompts for different analysis types
        self.SYSTEM_PROMPTS = {
            'match_analysis': """You are an expert football analyst and odds specialist. Analyze the provided match data and odds to:
1. Evaluate the implied probabilities from the odds
2. Identify potential value bets based on odds discrepancies
3. Consider team form and historical performance
4. Highlight any significant odds movements
5. Provide a confidence rating for predictions (1-10)

Format your analysis in clear sections and be specific with your insights.""",
            
            'value_bets': """You are a professional football betting analyst. For each match:
1. Calculate implied probabilities from different bookmakers
2. Identify odds discrepancies between bookmakers
3. Flag potential value bets where true probability might differ from implied odds
4. Rate each value bet opportunity (1-5 stars)
5. Provide a brief rationale for each identified value bet

Be conservative in your analysis and only highlight strong value opportunities."""
        }
    
    def analyze_odds(self, odds_data: List[Dict]) -> Dict:
        """Analyze odds data using GPT-4."""
        try:
            analysis_prompt = self._create_analysis_prompt(odds_data)
            
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use standard GPT-4
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPTS['match_analysis']},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis': response.choices[0].message.content,
                'analyzed_matches': len(odds_data)
            }
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis': "Unable to analyze due to API error.",
                'analyzed_matches': 0,
                'error': str(e)
            }
    
    def _create_analysis_prompt(self, odds_data: List[Dict]) -> str:
        """Create detailed analysis prompt from odds data."""
        prompt = """Analyze the following football matches and provide detailed insights:

"""
        for match in odds_data:
            # Match header
            prompt += f"""
=== MATCH ANALYSIS ===
{match['home_team']} vs {match['away_team']}
Competition: {match['sport_key']}
Start Time: {match['commence_time']}

ODDS COMPARISON:
"""
            # Organize odds by bookmaker
            for bookmaker in match['bookmakers']:
                prompt += f"\n{bookmaker['title']}:\n"
                for market in bookmaker['markets']:
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            implied_prob = round((1 / outcome['price']) * 100, 2)
                            prompt += f"- {outcome['name']}: {outcome['price']} (Implied Prob: {implied_prob}%)\n"
            
            prompt += "\nPlease provide:\n"
            prompt += "1. Match outcome prediction with confidence level\n"
            prompt += "2. Identification of any significant odds discrepancies\n"
            prompt += "3. Value bet opportunities (if any)\n"
            prompt += "4. Key factors influencing the odds\n"
            prompt += "5. Risk assessment (Low/Medium/High)\n\n"
        
        return prompt
    
    def _create_value_bets_prompt(self, odds_data: List[Dict]) -> str:
        """Create prompt specifically for value bet analysis."""
        prompt = """Analyze these matches for value betting opportunities. 
Consider odds discrepancies between bookmakers and identify potential value bets:

"""
        for match in odds_data:
            prompt += f"\n{match['home_team']} vs {match['away_team']}\n"
            prompt += "Bookmaker Odds Comparison:\n"
            
            # Create odds comparison table
            for bookmaker in match['bookmakers']:
                prompt += f"\n{bookmaker['title']}:\n"
                for market in bookmaker['markets']:
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            implied_prob = round((1 / outcome['price']) * 100, 2)
                            prompt += f"- {outcome['name']}: {outcome['price']} ({implied_prob}%)\n"
            
            prompt += "\nIdentify:\n"
            prompt += "1. Highest available odds for each outcome\n"
            prompt += "2. Significant odds discrepancies (>5% difference in implied probability)\n"
            prompt += "3. Potential arbitrage opportunities\n"
            prompt += "4. Value bet rating (1-5 stars)\n\n"
        
        return prompt
    
    def _get_unique_bookmakers(self, odds_data: List[Dict]) -> List[str]:
        """Extract unique bookmaker names from odds data."""
        bookmakers = set()
        for match in odds_data:
            for bookmaker in match['bookmakers']:
                bookmakers.add(bookmaker['title'])
        return list(bookmakers)
    
    def save_analysis(self, analysis: Dict, filename: str = None) -> None:
        """Save analysis results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'analysis_{timestamp}.json'
        
        os.makedirs('analysis', exist_ok=True)
        filepath = os.path.join('analysis', filename)
        
        with open(filepath, 'w') as f:
            json.dump(analysis, f, indent=2)
            
        print(f"Analysis saved to {filepath}") 
    
    def analyze_optimized_odds(self, optimized_data: Dict) -> Dict:
        """Analyze optimized odds data structure."""
        try:
            analysis_results = {
                'timestamp': datetime.now().isoformat(),
                'league_analysis': {},
                'overall_insights': []
            }
            
            for league_key, league_data in optimized_data['leagues'].items():
                matches = league_data.get('matches', [])
                if not matches:
                    continue
                    
                # Analyze each match in the league
                league_analysis = []
                for match in matches:
                    analysis_prompt = self._create_analysis_prompt([match])
                    
                    # Get match analysis from OpenAI
                    match_analysis = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": self.SYSTEM_PROMPTS['match_analysis']},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    league_analysis.append({
                        'match': f"{match['home_team']} vs {match['away_team']}",
                        'analysis': match_analysis.choices[0].message.content
                    })
                
                analysis_results['league_analysis'][league_key] = league_analysis
            
            return analysis_results
            
        except Exception as e:
            print(f"Error in analyze_optimized_odds: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            } 
    
    def identify_value_bets(self, optimized_data: Dict) -> List[Dict]:
        """Identify potential value betting opportunities."""
        value_bets = []
        
        for league_key, league_data in optimized_data['leagues'].items():
            for match in league_data.get('matches', []):
                # Skip if no bookmaker odds available
                if not match.get('bookmaker_odds'):
                    continue
                    
                analysis = match.get('analysis', {})
                
                # Check for significant odds variance (potential value)
                if analysis.get('odds_variance'):
                    home_variance = analysis['odds_variance'].get('home', 0)
                    away_variance = analysis['odds_variance'].get('away', 0)
                    draw_variance = analysis['odds_variance'].get('draw', 0)
                    
                    # If variance is significant (>0.5), flag as potential value bet
                    if any(var > 0.5 for var in [home_variance, away_variance, draw_variance]):
                        value_bets.append({
                            'match': f"{match['home_team']} vs {match['away_team']}",
                            'league': league_key,
                            'odds_variance': analysis['odds_variance'],
                            'confidence_level': analysis.get('bookmaker_confidence', 0)
                        })
        
        return value_bets 
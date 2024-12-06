# Football Tipster X Bot

An automated Python bot that fetches football betting odds, analyzes them, and posts betting tips on X (formerly Twitter).

## Features

- Fetches real-time football betting odds from The Odds API
- Analyzes odds data to identify valuable betting opportunities
- Automatically generates and posts betting tips on X
- Supports multiple football leagues and betting markets

## Setup

1. Create and activate a conda environment:
```bash
conda create -n tipster_bot python=3.11 -y
conda activate tipster_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file with your API keys:
```
ODDS_API_KEY=your_odds_api_key_here
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
```

## Usage

### Fetch Odds Data
```python
from src.odds_api_client import OddsAPIClient
import os

# Initialize client
client = OddsAPIClient(os.getenv('ODDS_API_KEY'))

# Get odds data
odds = client.get_odds(
    sport='soccer_epl',
    regions=['us', 'uk'],
    markets=['h2h']
)

# Save to JSON
client.save_odds_data(odds)
```

## Data Storage
- Odds data is saved in the `data/` directory
- Analysis results are saved in the `analysis/` directory

## Contributing
Feel free to open issues or submit pull requests.

## License
MIT License
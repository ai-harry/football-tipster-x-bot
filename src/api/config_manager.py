import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from .models import TwitterCredentials, PromptTemplate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigManager:
    DEFAULT_PROMPT = """Analyze the following bet details and provide insights:
{bet_details}

Key analysis points to consider:
{analysis_points}

Please provide a detailed analysis considering historical performance, current form, and relevant statistics."""

    def __init__(self):
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.credentials_file = self.config_dir / "credentials.json"
        self.prompt_file = self.config_dir / "prompt.json"
        self._load_configs()

    def _load_configs(self) -> None:
        if not self.prompt_file.exists():
            self._save_prompt(self.DEFAULT_PROMPT)
        
    def _save_credentials(self, credentials: TwitterCredentials) -> None:
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials.dict(), f)
        logger.info("Twitter credentials updated")

    def _save_prompt(self, prompt: str) -> None:
        with open(self.prompt_file, 'w') as f:
            json.dump({"template": prompt}, f)
        logger.info("Prompt template updated")

    def get_twitter_credentials(self) -> Optional[TwitterCredentials]:
        if not self.credentials_file.exists():
            return None
        with open(self.credentials_file, 'r') as f:
            return TwitterCredentials(**json.load(f))

    def set_twitter_credentials(self, credentials: TwitterCredentials) -> bool:
        try:
            # Here you would typically validate the credentials with Twitter's API
            self._save_credentials(credentials)
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")
            return False

    def get_prompt_template(self) -> str:
        if not self.prompt_file.exists():
            return self.DEFAULT_PROMPT
        with open(self.prompt_file, 'r') as f:
            data = json.load(f)
            return data.get("template", self.DEFAULT_PROMPT)

    def set_prompt_template(self, prompt: PromptTemplate) -> bool:
        try:
            self._save_prompt(prompt.template)
            return True
        except Exception as e:
            logger.error(f"Error saving prompt template: {str(e)}")
            return False 
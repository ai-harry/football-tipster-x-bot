from openai import OpenAI
import os
import logging

logger = logging.getLogger(__name__)

def create_openai_client(api_key: str) -> OpenAI:
    """Create OpenAI client with proper configuration."""
    try:
        # Ensure no proxy settings are inherited
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)
        
        # Create client with minimal configuration
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.openai.com/v1"
        )
        
        # Test connection
        client.models.list()
        return client
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {str(e)}")
        raise 
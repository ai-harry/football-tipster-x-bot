from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

def create_openai_client(api_key: str) -> OpenAI:
    """Create OpenAI client with minimal configuration."""
    try:
        # Create client with only the API key
        client = OpenAI(
            api_key=api_key
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {str(e)}")
        raise 
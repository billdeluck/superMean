# Directory: backend/utils/
# File: config_loader.py
# Description: Loads application configuration using Pydantic Settings.

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    # --- General Settings ---
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: Optional[str] = None # e.g., "logs/backend.log"

    # --- API Keys ---
    GEMINI_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    AIMLAPI_KEY: Optional[str] = None
    ROUTERAPI_KEY: Optional[str] = None
    # Add other API keys as needed

    # --- Model Router Settings ---
    MODEL_FALLBACK_CHAIN: str = "gemini,deepseek,aimlapi:gpt-4o"  # Default fallback chain

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

# Use lru_cache to load settings only once
@lru_cache()
def get_settings() -> Settings:
    """Returns the loaded settings instance."""
    # Ensure .env exists or provide guidance
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if not os.path.exists(env_path):
        # Check if template exists
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.template')
        if os.path.exists(template_path):
             print(f"Warning: .env file not found at {env_path}. Copied from .env.template. Please fill in your details.")
             import shutil
             shutil.copy(template_path, env_path)
        else:
            print(f"Warning: .env file not found at {env_path} and no .env.template exists. Using default settings and environment variables.")

    try:
        settings = Settings()
        # Example validation: Check if at least one LLM API key is set in production
        # if settings.ENVIRONMENT == "production" and not any([settings.GEMINI_API_KEY, settings.DEEPSEEK_API_KEY, settings.ROUTERAPI_KEY]):
        #     raise ValueError("At least one LLM API key must be configured in production environment.")
        return settings
    except Exception as e:
        print(f"Error loading settings: {e}")
        # Provide default settings or re-raise depending on desired behavior
        # For now, return default settings on error during initialization
        return Settings()

# --- Example Usage ---
# if __name__ == "__main__":
#     config = get_settings()
#     print(f"Environment: {config.ENVIRONMENT}")
#     print(f"Log Level: {config.LOG_LEVEL}")
#     print(f"Gemini Key Set: {'Yes' if config.GEMINI_API_KEY else 'No'}")
#     print(f"SerpApi Key Set: {'Yes' if config.SERPAPI_KEY else 'No'}")
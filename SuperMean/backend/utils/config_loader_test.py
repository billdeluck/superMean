# Test Snippet: backend/utils/config_loader.py
# Description: Verifies that settings are loaded correctly from .env.
# Command: python -m backend.utils.config_loader_test

# Create a file named backend/utils/config_loader_test.py with the following content:
import sys
import os
# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Create a dummy .env file for testing IN THE BACKEND DIRECTORY
env_content = """
ENVIRONMENT=testing
LOG_LEVEL=DEBUG
GEMINI_API_KEY=test_gemini_key
SERPAPI_KEY=test_serpapi_key
# This is a comment
EXTRA_VAR=should_be_ignored
"""
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
try:
    with open(env_path, 'w') as f:
        f.write(env_content)
    print(f"Created dummy .env file at: {env_path}")

    # Now import and test
    from backend.utils.config_loader import get_settings

    print("Imported get_settings successfully.")
    settings = get_settings()
    print("Settings loaded.")

    assert settings.ENVIRONMENT == "testing", f"Expected ENVIRONMENT 'testing', got '{settings.ENVIRONMENT}'"
    assert settings.LOG_LEVEL == "DEBUG", f"Expected LOG_LEVEL 'DEBUG', got '{settings.LOG_LEVEL}'"
    assert settings.GEMINI_API_KEY == "test_gemini_key", f"Expected GEMINI_API_KEY 'test_gemini_key', got '{settings.GEMINI_API_KEY}'"
    assert settings.SERPAPI_KEY == "test_serpapi_key", f"Expected SERPAPI_KEY 'test_serpapi_key', got '{settings.SERPAPI_KEY}'"
    assert not hasattr(settings, 'EXTRA_VAR'), "EXTRA_VAR should have been ignored"

    print("Config loader tests passed.")
    print(f"Loaded ENVIRONMENT: {settings.ENVIRONMENT}")
    print(f"Loaded LOG_LEVEL: {settings.LOG_LEVEL}")
    print(f"Loaded GEMINI_API_KEY: {'Set' if settings.GEMINI_API_KEY else 'Not Set'}")

except ImportError as e:
    print(f"Failed to import get_settings: {e}")
except Exception as e:
    print(f"An error occurred during config loader test: {e}")
finally:
    # Clean up the dummy .env file
    if os.path.exists(env_path):
        os.remove(env_path)
        print(f"Cleaned up dummy .env file: {env_path}")
# Test Snippet: backend/utils/error_handler.py
# Description: Verifies that custom exceptions can be raised and caught.
# Command: python -m backend.utils.error_handler_test

# Create a file named backend/utils/error_handler_test.py with the following content:
import sys
import os
# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from backend.utils.error_handler import SuperMeanException, ConfigurationError, ModelConnectionError, SkillError

    print("Custom exceptions imported successfully.")

    try:
        raise ConfigurationError("Test config issue", missing_key="TEST_KEY")
    except SuperMeanException as e:
        print(f"Caught expected exception: {e}")
        assert e.status_code == 500
        assert "Missing key - TEST_KEY" in e.message

    try:
        raise ModelConnectionError("Gemini-Pro", "Timeout connecting")
    except SuperMeanException as e:
        print(f"Caught expected exception: {e}")
        assert e.status_code == 503
        assert "Gemini-Pro" in e.message

    try:
        raise SkillError("web_search", "API key invalid")
    except SuperMeanException as e:
        print(f"Caught expected exception: {e}")
        assert e.status_code == 500
        assert "web_search" in e.message

    print("Custom exception tests passed.")

except ImportError as e:
    print(f"Failed to import exceptions: {e}")
except Exception as e:
    print(f"An error occurred during exception test: {e}")
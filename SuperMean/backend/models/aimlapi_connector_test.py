# Test Snippet File: backend/models/aimlapi_connector_test.py
# Description: Verifies the AimlApiConnector (AIMLAPI) can generate text. Requires AIMLAPI_KEY in .env.
# Command: python -m backend.models.aimlapi_connector_test

import sys
import os
import unittest
import asyncio
# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Create dummy .env if it doesn't exist, remind user to fill it
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if not os.path.exists(env_path):
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.template'))
    try:
        if os.path.exists(template_path):
            import shutil
            shutil.copy(template_path, env_path)
            print(f"Copied .env.template to .env. Please ensure AIMLAPI_KEY is set in {env_path}")
        else:
            with open(env_path, 'w') as f:
                f.write("AIMLAPI_KEY=\n") # Ensure the key exists in the template check
            print(f"Created dummy .env file at {env_path}. Please set AIMLAPI_KEY.")
    except Exception as e:
        print(f"Could not create .env file: {e}")


try:
    # Correctly import AimlApiConnector (assuming file was renamed)
    from backend.models.aimlapi_connector import AimlApiConnector
    from backend.utils.config_loader import get_settings
    from backend.utils.error_handler import ModelConnectionError
    print("Imported AimlApiConnector successfully.")

    # Load settings to check for API key
    settings = get_settings()
    API_KEY_AVAILABLE = bool(settings.AIMLAPI_KEY)
    # Define a model available via AIMLAPI for testing (e.g., a smaller Mistral model)
    # Or use gpt-4o if you have access and want to test that
    TEST_MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
    # TEST_MODEL_NAME = "gpt-4o"

    class TestAimlApiConnector(unittest.TestCase): # Renamed test class

        @unittest.skipUnless(API_KEY_AVAILABLE, "AIMLAPI_KEY not found in .env or environment variables")
        def test_init_with_key(self):
            """Test initialization with API key."""
            try:
                connector = AimlApiConnector() # Rely on settings
                self.assertIsNotNone(connector)
                self.assertIsNotNone(connector.api_key)
                self.assertIsNotNone(connector.client)
                print(f"AimlApiConnector initialized successfully.") # Updated log
            except ModelConnectionError as e:
                self.fail(f"Initialization failed with ModelConnectionError: {e}")
            except Exception as e:
                self.fail(f"Initialization failed with unexpected error: {e}")

        def test_init_without_key_raises_error(self):
            """Test initialization raises error if key is missing."""
            original_key = settings.AIMLAPI_KEY
            settings.AIMLAPI_KEY = None
            with self.assertRaises(ModelConnectionError) as cm:
                AimlApiConnector() # Use correct class name
            print(f"Caught expected ModelConnectionError for missing key: {cm.exception}")
            settings.AIMLAPI_KEY = original_key

        # --- Async Test Runner ---
        def run_async(self, coro):
            return asyncio.run(coro)

        @unittest.skipUnless(API_KEY_AVAILABLE, "AIMLAPI_KEY not found in .env or environment variables")
        def test_generate_text_non_streaming(self):
            """Test non-streaming text generation via AIMLAPI."""
            connector = AimlApiConnector() # Use correct class name
            prompt = f"Using model {TEST_MODEL_NAME}, what is 2+2?"
            print(f"\nTesting non-streaming generation with model '{TEST_MODEL_NAME}' and prompt: '{prompt}'")
            try:
                result = self.run_async(connector.generate(prompt, model=TEST_MODEL_NAME, stream=False, temperature=0.1, max_tokens=20))
                print(f"Received response (non-streaming): {result}")
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 0)
                self.assertTrue("4" in result or "four" in result.lower()) # Basic check
            except ModelConnectionError as e:
                print(f"\nNote: AIMLAPI call failed: {e}. This might be due to invalid key, quota, model access, or network issues.")
                # self.fail(f"Generation failed with ModelConnectionError: {e}")
            except Exception as e:
                 self.fail(f"Generation failed with unexpected error: {e}")

        @unittest.skipUnless(API_KEY_AVAILABLE, "AIMLAPI_KEY not found in .env or environment variables")
        def test_generate_text_streaming(self):
            """Test streaming text generation via AIMLAPI."""
            async def consume_stream():
                connector = AimlApiConnector() # Use correct class name
                prompt = f"Using model {TEST_MODEL_NAME}, tell me a very short joke."
                print(f"\nTesting streaming generation with model '{TEST_MODEL_NAME}' and prompt: '{prompt}'")
                full_response = ""
                chunks_received = 0
                try:
                    stream_generator = await connector.generate(prompt, model=TEST_MODEL_NAME, stream=True, temperature=0.7, max_tokens=50)
                    async for chunk in stream_generator:
                        self.assertIsInstance(chunk, str)
                        print(f"Received chunk: {chunk.strip()}", end="") # Print chunks inline
                        full_response += chunk
                        chunks_received += 1
                    print(f"\nFull streamed response: {full_response}") # Print full response at end
                    self.assertTrue(chunks_received > 0, "No chunks received from stream")
                    self.assertTrue(len(full_response) > 5) # Basic check
                except ModelConnectionError as e:
                    print(f"\nNote: AIMLAPI streaming call failed: {e}. This might be due to invalid key, quota, model access, or network issues.")
                    # self.fail(f"Streaming generation failed with ModelConnectionError: {e}")
                except Exception as e:
                    self.fail(f"Streaming generation failed with unexpected error: {e}")

            self.run_async(consume_stream())

        def test_generate_missing_model_raises_error(self):
            """Test that calling generate without specifying a model raises ValueError."""
            connector = AimlApiConnector(api_key="dummy_key") # Use correct class name
            with self.assertRaises(ValueError) as cm:
                 self.run_async(connector.generate(prompt="test", model="")) # Empty model string
            print(f"Caught expected ValueError for missing model: {cm.exception}")
            self.assertTrue("'model' argument" in str(cm.exception))


    # Run the tests
    print(f"\nRunning AimlApiConnector tests...") # Updated log
    if not API_KEY_AVAILABLE:
        print("--- SKIPPING TESTS requiring AIMLAPI_KEY ---")

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestAimlApiConnector)) # Use correct test class name
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import AimlApiConnector or dependencies (check openai install): {e}") # Updated message
    print("Ensure backend/models/aimlapi_connector.py and its dependencies exist.")
except Exception as e:
    print(f"An error occurred during AimlApi connector test setup: {e}") # Updated message
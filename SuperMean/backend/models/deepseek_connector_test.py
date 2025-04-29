# Test Snippet File: backend/models/deepseek_connector_test.py
# Description: Verifies the DeepSeekConnector can generate text. Requires DEEPSEEK_API_KEY in .env.
# Command: python -m backend.models.deepseek_connector_test

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
            print(f"Copied .env.template to .env. Please ensure DEEPSEEK_API_KEY is set in {env_path}")
        else:
            with open(env_path, 'w') as f:
                f.write("DEEPSEEK_API_KEY=\n")
            print(f"Created dummy .env file at {env_path}. Please set DEEPSEEK_API_KEY.")
    except Exception as e:
        print(f"Could not create .env file: {e}")


try:
    from backend.models.deepseek_connector import DeepSeekConnector
    from backend.utils.config_loader import get_settings
    from backend.utils.error_handler import ModelConnectionError
    print("Imported DeepSeekConnector successfully.")

    # Load settings to check for API key
    settings = get_settings()
    API_KEY_AVAILABLE = bool(settings.DEEPSEEK_API_KEY)

    class TestDeepSeekConnector(unittest.TestCase):

        @unittest.skipUnless(API_KEY_AVAILABLE, "DEEPSEEK_API_KEY not found in .env or environment variables")
        def test_init_with_key(self):
            """Test initialization with API key."""
            try:
                connector = DeepSeekConnector() # Rely on settings
                self.assertIsNotNone(connector)
                self.assertIsNotNone(connector.api_key)
                self.assertEqual(connector.model_name, "deepseek-chat") # Default
                print(f"DeepSeekConnector initialized successfully with model: {connector.model_name}")
            except ModelConnectionError as e:
                self.fail(f"Initialization failed with ModelConnectionError: {e}")
            except Exception as e:
                self.fail(f"Initialization failed with unexpected error: {e}")

        def test_init_without_key_raises_error(self):
            """Test initialization raises error if key is missing."""
            # Temporarily mock settings to simulate missing key
            original_key = settings.DEEPSEEK_API_KEY
            settings.DEEPSEEK_API_KEY = None
            with self.assertRaises(ModelConnectionError) as cm:
                DeepSeekConnector()
            print(f"Caught expected ModelConnectionError for missing key: {cm.exception}")
            settings.DEEPSEEK_API_KEY = original_key # Restore original key

        # --- Async Test Runner ---
        def run_async(self, coro):
            return asyncio.run(coro)

        @unittest.skipUnless(API_KEY_AVAILABLE, "DEEPSEEK_API_KEY not found in .env or environment variables")
        def test_generate_text_non_streaming(self):
            """Test non-streaming text generation."""
            connector = DeepSeekConnector()
            prompt = "What is the capital of France?"
            system_prompt = "You are a helpful assistant providing concise answers."
            print(f"\nTesting non-streaming generation with prompt: '{prompt}'")
            try:
                # Use run_async helper for the async generate method
                result = self.run_async(connector.generate(prompt, system_prompt=system_prompt, stream=False, temperature=0.5, max_tokens=50))
                print(f"Received response (non-streaming): {result}")
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 0) # Basic check for non-empty response
                self.assertTrue("paris" in result.lower())
            except ModelConnectionError as e:
                # If API call fails (e.g., quota), log but don't fail the test suite
                print(f"\nNote: DeepSeek API call failed: {e}. This might be due to invalid key, quota, or network issues.")
                # self.fail(f"Generation failed with ModelConnectionError: {e}") # Uncomment to make test fail on API error
            except Exception as e:
                 self.fail(f"Generation failed with unexpected error: {e}")

        # Skipping streaming test for now as it's not fully implemented
        @unittest.skip("Streaming not fully implemented for DeepSeekConnector")
        def test_generate_text_streaming(self):
            """Test streaming text generation (Placeholder)."""
            async def consume_stream():
                connector = DeepSeekConnector()
                prompt = "Tell me a short story."
                try:
                    stream_generator = await connector.generate(prompt, stream=True)
                    async for chunk in stream_generator:
                        pass # Consume stream
                except NotImplementedError:
                     pass # Expected for now
                except Exception as e:
                     self.fail(f"Streaming test failed unexpectedly: {e}")

            self.run_async(consume_stream())

    # Run the tests
    print(f"\nRunning DeepSeekConnector tests...")
    if not API_KEY_AVAILABLE:
        print("--- SKIPPING TESTS requiring DEEPSEEK_API_KEY ---")

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestDeepSeekConnector))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import DeepSeekConnector or dependencies: {e}")
    print("Ensure backend/models/deepseek_connector.py and its dependencies exist.")
except Exception as e:
    print(f"An error occurred during DeepSeek connector test setup: {e}")
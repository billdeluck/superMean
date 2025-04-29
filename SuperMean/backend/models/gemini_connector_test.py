# Test Snippet File: backend/models/gemini_connector_test.py
# Description: Verifies the GeminiConnector can generate text. Requires GEMINI_API_KEY in .env.
# Command: python -m backend.models.gemini_connector_test

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
            print(f"Copied .env.template to .env. Please ensure GEMINI_API_KEY is set in {env_path}")
        else:
            with open(env_path, 'w') as f:
                f.write("GEMINI_API_KEY=\n")
            print(f"Created dummy .env file at {env_path}. Please set GEMINI_API_KEY.")
    except Exception as e:
        print(f"Could not create .env file: {e}")


try:
    from backend.models.gemini_connector import GeminiConnector
    from backend.utils.config_loader import get_settings
    from backend.utils.error_handler import ModelConnectionError
    print("Imported GeminiConnector successfully.")

    # Load settings to check for API key
    settings = get_settings()
    API_KEY_AVAILABLE = bool(settings.GEMINI_API_KEY)

    class TestGeminiConnector(unittest.TestCase):

        @unittest.skipUnless(API_KEY_AVAILABLE, "GEMINI_API_KEY not found in .env or environment variables")
        def test_init_with_key(self):
            """Test initialization with API key."""
            try:
                connector = GeminiConnector() # Rely on settings
                self.assertIsNotNone(connector)
                self.assertIsNotNone(connector.model)
                print(f"GeminiConnector initialized successfully with model: {connector.model_name}")
            except ModelConnectionError as e:
                self.fail(f"Initialization failed with ModelConnectionError: {e}")
            except Exception as e:
                self.fail(f"Initialization failed with unexpected error: {e}")

        def test_init_without_key_raises_error(self):
            """Test initialization raises error if key is missing."""
            # Temporarily mock settings to simulate missing key
            original_key = settings.GEMINI_API_KEY
            settings.GEMINI_API_KEY = None
            with self.assertRaises(ModelConnectionError) as cm:
                GeminiConnector()
            print(f"Caught expected ModelConnectionError for missing key: {cm.exception}")
            settings.GEMINI_API_KEY = original_key # Restore original key

        # --- Async Test Runner ---
        def run_async(self, coro):
            # Use asyncio.run() which creates a new event loop
            return asyncio.run(coro)
            # Alternatively, manage a loop per test class if needed:
            # loop = asyncio.get_event_loop_policy().new_event_loop()
            # asyncio.set_event_loop(loop)
            # try:
            #     result = loop.run_until_complete(coro)
            # finally:
            #     loop.close()
            # return result

        @unittest.skipUnless(API_KEY_AVAILABLE, "GEMINI_API_KEY not found in .env or environment variables")
        def test_generate_text_non_streaming(self):
            """Test non-streaming text generation."""
            try:
                connector = GeminiConnector()
                prompt = "Explain the concept of 'large language model' in one sentence."
                print(f"\nTesting non-streaming generation with prompt: '{prompt}'")
                result = self.run_async(connector.generate(prompt, stream=False, temperature=0.7)) # Use run_async helper
                print(f"Received response (non-streaming): {result}")
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 10) # Basic check for non-empty response
                self.assertTrue("language model" in result.lower() or "llm" in result.lower())
            except ModelConnectionError as e:
                self.fail(f"Generation failed with ModelConnectionError: {e}")
            except Exception as e:
                 self.fail(f"Generation failed with unexpected error: {e}")

        @unittest.skipUnless(API_KEY_AVAILABLE, "GEMINI_API_KEY not found in .env or environment variables")
        def test_generate_text_streaming(self):
            """Test streaming text generation."""
            async def consume_stream():
                connector = GeminiConnector()
                prompt = "List three benefits of using Python."
                print(f"\nTesting streaming generation with prompt: '{prompt}'")
                full_response = ""
                chunks_received = 0
                try:
                    stream_generator = await connector.generate(prompt, stream=True, temperature=0.7)
                    async for chunk in stream_generator:
                        self.assertIsInstance(chunk, str)
                        print(f"Received chunk: {chunk.strip()}")
                        full_response += chunk
                        chunks_received += 1
                    print(f"\nFull streamed response: {full_response}")
                    self.assertTrue(chunks_received > 0, "No chunks received from stream")
                    self.assertTrue(len(full_response) > 10) # Basic check
                    self.assertTrue("python" in full_response.lower())
                    # Check for list format (very basic)
                    self.assertTrue("1." in full_response or "-" in full_response or "*" in full_response)
                except ModelConnectionError as e:
                    self.fail(f"Streaming generation failed with ModelConnectionError: {e}")
                except Exception as e:
                    self.fail(f"Streaming generation failed with unexpected error: {e}")

            # Run the async consumer function
            self.run_async(consume_stream()) # Use run_async helper

    # Run the tests
    print(f"\nRunning GeminiConnector tests...")
    if not API_KEY_AVAILABLE:
        print("--- SKIPPING TESTS requiring GEMINI_API_KEY ---")

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestGeminiConnector))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import GeminiConnector or dependencies: {e}")
    print("Ensure backend/models/gemini_connector.py and its dependencies exist.")
except Exception as e:
    print(f"An error occurred during Gemini connector test setup: {e}")
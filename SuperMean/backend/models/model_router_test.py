# Test Snippet File: backend/models/model_router_test.py
# Description: Verifies the ModelRouter routes requests correctly. (Reverted patch setup, fixed placeholder test)
# Command: python -m backend.models.model_router_test

import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# --- .env check remains the same ---
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if not os.path.exists(env_path):
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.template'))
    try:
        if os.path.exists(template_path):
            import shutil
            shutil.copy(template_path, env_path)
            print(f"Copied .env.template to .env. Please set API keys in {env_path} for full testing.")
        else:
            with open(env_path, 'w') as f:
                f.write("GEMINI_API_KEY=\nDEEPSEEK_API_KEY=\nAIMLAPI_KEY=\nROUTERAPI_KEY=\n")
            print(f"Created dummy .env file at {env_path}. Please set API keys for full testing.")
    except Exception as e:
        print(f"Could not create .env file: {e}")


try:
    # Import the class under test
    from backend.models.model_router import ModelRouter
    # Import necessary utilities and base classes
    from backend.utils.config_loader import Settings # Import Settings for type hinting
    from backend.utils.error_handler import ModelConnectionError, ConfigurationError
    from backend.models.base_model import BaseModelConnector
    # Import specific connectors only if needed for type checking within tests, not generally required
    print("Imported ModelRouter successfully.")


    class TestModelRouter(unittest.TestCase):

        def setUp(self):
            """Setup mock connectors using patcher start/stop."""
            print(f"\n--- Starting test: {self._testMethodName} ---")

            # --- CORRECTED PATCH SETUP ---
            # Patch the connector classes in their *original modules*
            self.gemini_patcher = patch('backend.models.gemini_connector.GeminiConnector')
            self.deepseek_patcher = patch('backend.models.deepseek_connector.DeepSeekConnector')
            self.aimlapi_patcher = patch('backend.models.aimlapi_connector.AimlApiConnector')
            # Patch the placeholder connector as well
            self.routerapi_patcher = patch('backend.models.router_api_connector.RouterApiConnector')

            # Start the patchers and get the Mock Class objects
            self.MockGeminiClass = self.gemini_patcher.start()
            self.MockDeepSeekClass = self.deepseek_patcher.start()
            self.MockAimlApiClass = self.aimlapi_patcher.start()
            self.MockRouterApiClass = self.routerapi_patcher.start() # Start placeholder patcher

            # Create mock instances that will be returned when the classes are instantiated
            self.mock_gemini_instance = self.MockGeminiClass.return_value
            self.mock_gemini_instance.generate = AsyncMock(return_value="Gemini: Mock Response") # Default return

            self.mock_deepseek_instance = self.MockDeepSeekClass.return_value
            self.mock_deepseek_instance.generate = AsyncMock(return_value="DeepSeek: Mock Response") # Default return

            self.mock_aimlapi_instance = self.MockAimlApiClass.return_value
            self.mock_aimlapi_instance.generate = AsyncMock(return_value="AIMLAPI (default): Mock Response") # Default return

            self.mock_routerapi_instance = self.MockRouterApiClass.return_value
            # Configure placeholder mock to raise NotImplementedError when generate is called
            self.mock_routerapi_instance.generate = AsyncMock(side_effect=NotImplementedError("Mock RouterAPI placeholder"))

            # Create dummy settings object enabling all keys for mock testing
            # Ensure fallback chain includes aimlapi and routerapi for specific tests
            self.mock_settings = Settings(
                GEMINI_API_KEY="fake", DEEPSEEK_API_KEY="fake",
                AIMLAPI_KEY="fake", ROUTERAPI_KEY="fake", # Provide key for placeholder check
                MODEL_FALLBACK_CHAIN="gemini,deepseek,aimlapi:gpt-4o,routerapi" # Full fallback chain
            )

            # Instantiate the router *after* patching is set up
            # Its _initialize_connectors will now import and use the *patched* classes
            self.router = ModelRouter(settings=self.mock_settings)

        def tearDown(self):
            """Stop all patches."""
            self.gemini_patcher.stop()
            self.deepseek_patcher.stop()
            self.aimlapi_patcher.stop()
            self.routerapi_patcher.stop() # Stop placeholder patcher
            print(f"--- Finished test: {self._testMethodName} ---")


        def run_async(self, coro):
            # Simple helper to run async functions in tests
            return asyncio.run(coro)

        def test_initialization(self):
            """Test that connectors were initialized using mocked classes."""
            # Check that the *patched* classes were called during init with the API key
            self.MockGeminiClass.assert_called_once_with(api_key='fake')
            self.MockDeepSeekClass.assert_called_once_with(api_key='fake')
            self.MockAimlApiClass.assert_called_once_with(api_key='fake')
            self.MockRouterApiClass.assert_called_once_with(api_key='fake') # Placeholder called

            # Check instances stored are the mocked ones
            self.assertIn("gemini", self.router.connectors)
            self.assertIn("deepseek", self.router.connectors)
            self.assertIn("aimlapi", self.router.connectors)
            self.assertIn("routerapi", self.router.connectors) # Placeholder should be initialized
            self.assertIs(self.router.connectors["gemini"], self.mock_gemini_instance)
            self.assertIs(self.router.connectors["deepseek"], self.mock_deepseek_instance)
            self.assertIs(self.router.connectors["aimlapi"], self.mock_aimlapi_instance)
            self.assertIs(self.router.connectors["routerapi"], self.mock_routerapi_instance) # Check placeholder instance
            print("Router initialized with correct mock connector instances.")

        def test_get_available_models(self):
            """Test listing available models."""
            available = self.router.get_available_models()
            # Expect all models (including placeholder) to be listed as initialized
            self.assertCountEqual(available, ["gemini", "deepseek", "aimlapi", "routerapi"])
            print(f"Available models reported: {available}")

        def test_route_to_preference_gemini(self):
            """Test routing to preferred Gemini connector."""
            expected_result = "Gemini response for hello"
            self.mock_gemini_instance.generate.return_value = expected_result # Customize return value for this test
            result = self.run_async(self.router.generate("hello", model_preference="gemini"))
            self.assertEqual(result, expected_result)
            # Gemini generate should be called without 'model' kwarg
            self.mock_gemini_instance.generate.assert_awaited_once_with(prompt="hello", stream=False)
            print("Routed to Gemini preference successfully.")

        def test_route_to_preference_deepseek(self):
            """Test routing to preferred DeepSeek connector."""
            expected_result = "DeepSeek response for hello"
            self.mock_deepseek_instance.generate.return_value = expected_result
            result = self.run_async(self.router.generate("hello", model_preference="deepseek"))
            self.assertEqual(result, expected_result)
             # DeepSeek generate should be called without 'model' kwarg
            self.mock_deepseek_instance.generate.assert_awaited_once_with(prompt="hello", stream=False)
            print("Routed to DeepSeek preference successfully.")

        def test_route_to_preference_aimlapi(self):
            """Test routing to preferred AIMLAPI connector with specific model."""
            expected_result = "AIMLAPI (gpt-4o) response for hello"
            self.mock_aimlapi_instance.generate.return_value = expected_result
            result = self.run_async(self.router.generate("hello", model_preference="aimlapi:gpt-4o"))
            self.assertEqual(result, expected_result)
            # AIMLAPI generate should be called WITH 'model' kwarg
            self.mock_aimlapi_instance.generate.assert_awaited_once_with(prompt="hello", stream=False, model="gpt-4o")
            print("Routed to AIMLAPI preference with model override successfully.")

        def test_route_to_fallback_gemini(self):
            """Test falling back to Gemini when preference is invalid."""
            expected_result = "Gemini fallback response"
            self.mock_gemini_instance.generate.return_value = expected_result
            # Use a non-existent preference to trigger fallback
            result = self.run_async(self.router.generate("hello", model_preference="nonexistent"))
            self.assertEqual(result, expected_result)
            # Gemini is the first in the fallback chain ("gemini,deepseek,aimlapi:gpt-4o,routerapi")
            self.mock_gemini_instance.generate.assert_awaited_once_with(prompt="hello", stream=False)
            self.mock_deepseek_instance.generate.assert_not_awaited()
            self.mock_aimlapi_instance.generate.assert_not_awaited()
            self.mock_routerapi_instance.generate.assert_not_awaited() # Placeholder should not be tried yet
            print("Fell back to Gemini successfully.")

        def test_route_to_fallback_deepseek(self):
            """Test falling back to DeepSeek if Gemini fails."""
            # Make Gemini mock raise an error
            self.mock_gemini_instance.generate.side_effect = ModelConnectionError("Gemini", "Mock connection error")
            expected_result = "DeepSeek fallback response"
            self.mock_deepseek_instance.generate.return_value = expected_result

            result = self.run_async(self.router.generate("hello", model_preference="nonexistent"))
            self.assertEqual(result, expected_result)
            # Gemini should be tried first and fail
            self.mock_gemini_instance.generate.assert_awaited_once()
            # DeepSeek is next in the chain and should succeed
            self.mock_deepseek_instance.generate.assert_awaited_once_with(prompt="hello", stream=False)
            self.mock_aimlapi_instance.generate.assert_not_awaited()
            self.mock_routerapi_instance.generate.assert_not_awaited()
            print("Fell back to DeepSeek after Gemini failure successfully.")

        def test_route_to_fallback_aimlapi(self):
            """Test falling back to AIMLAPI if Gemini and DeepSeek fail."""
            # Make first two fallbacks fail
            self.mock_gemini_instance.generate.side_effect = ModelConnectionError("Gemini", "Mock error")
            self.mock_deepseek_instance.generate.side_effect = ModelConnectionError("DeepSeek", "Mock error")
            expected_result = "AIMLAPI (gpt-4o): Last Resort"
            self.mock_aimlapi_instance.generate.return_value = expected_result

            result = self.run_async(self.router.generate("hello", model_preference="nonexistent"))
            self.assertEqual(result, expected_result)
            self.mock_gemini_instance.generate.assert_awaited_once()
            self.mock_deepseek_instance.generate.assert_awaited_once()
            # AIMLAPI is next, identified with specific model in fallback chain
            self.mock_aimlapi_instance.generate.assert_awaited_once_with(prompt="hello", stream=False, model="gpt-4o")
            self.mock_routerapi_instance.generate.assert_not_awaited() # Should not reach placeholder yet
            print("Fell back to AIMLAPI after Gemini/DeepSeek failure successfully.")

        def test_route_placeholder_skipped_in_fallback(self):
            """Test that the placeholder RouterApiConnector is skipped during fallback."""
            # Make all *real* connectors fail
            self.mock_gemini_instance.generate.side_effect = ModelConnectionError("Gemini", "Mock error")
            self.mock_deepseek_instance.generate.side_effect = ModelConnectionError("DeepSeek", "Mock error")
            self.mock_aimlapi_instance.generate.side_effect = ModelConnectionError("AimlApi", "Mock error")
            # The RouterAPI mock is already configured with NotImplementedError side_effect in setUp
            # The fallback chain includes 'routerapi' last

            # Expect the overall call to raise ModelConnectionError after all real models fail
            # and the placeholder is skipped.
            with self.assertRaises(ModelConnectionError) as cm:
                 self.run_async(self.router.generate("hello", model_preference="nonexistent"))

            final_error_msg = str(cm.exception)
            print(f"Caught expected final ModelConnectionError: {final_error_msg}")
            # Check that the error message indicates all failed/skipped
            self.assertTrue("No available model connector succeeded" in final_error_msg)
            self.assertTrue("Skipped (placeholder)" in final_error_msg) # Check placeholder skip message is present

            # Verify that the real connectors were tried
            self.mock_gemini_instance.generate.assert_awaited_once()
            self.mock_deepseek_instance.generate.assert_awaited_once()
            self.mock_aimlapi_instance.generate.assert_awaited_once()
            # ---> Verify the placeholder's generate method was *NOT* called <---
            self.mock_routerapi_instance.generate.assert_not_awaited()
            print("Placeholder was correctly skipped in fallback, final error raised.")


    # Run the tests
    print(f"\nRunning ModelRouter tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestModelRouter))
    runner = unittest.TextTestRunner(verbosity=2) # Increase verbosity
    result = runner.run(suite)

    # Exit with non-zero code if tests failed
    if not result.wasSuccessful():
        sys.exit(1)


except ImportError as e:
    print(f"Failed to import ModelRouter or dependencies: {e}", file=sys.stderr)
    print("Ensure backend/models/model_router.py structure is correct and all connector files exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during ModelRouter test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
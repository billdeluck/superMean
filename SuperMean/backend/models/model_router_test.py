# Test Snippet File: backend/models/model_router_test.py
# Description: Verifies the ModelRouter routes requests correctly. Requires API keys in .env for full testing.
# Command: python -m backend.models.model_router_test

import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

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
            print(f"Copied .env.template to .env. Please set API keys in {env_path} for full testing.")
        else:
            with open(env_path, 'w') as f:
                f.write("GEMINI_API_KEY=\nDEEPSEEK_API_KEY=\nAIMLAPI_KEY=\nROUTERAPI_KEY=\n")
            print(f"Created dummy .env file at {env_path}. Please set API keys for full testing.")
    except Exception as e:
        print(f"Could not create .env file: {e}")


try:
    from backend.models.model_router import ModelRouter
    from backend.utils.config_loader import get_settings, Settings
    from backend.utils.error_handler import ModelConnectionError, ConfigurationError
    from backend.models.base_model import BaseModelConnector
    print("Imported ModelRouter successfully.")

    # Load settings to check for API keys
    settings = get_settings()
    GEMINI_AVAILABLE = bool(settings.GEMINI_API_KEY)
    DEEPSEEK_AVAILABLE = bool(settings.DEEPSEEK_API_KEY)
    AIMLAPI_AVAILABLE = bool(settings.AIMLAPI_KEY)
    # ROUTERAPI_AVAILABLE = bool(settings.ROUTERAPI_KEY) # Placeholder might init without key

    # --- Mock Connectors for testing routing logic ---
    class MockGeminiConnector(BaseModelConnector):
         async def generate(self, prompt: str, **kwargs): return f"Gemini: {prompt}"
    class MockDeepSeekConnector(BaseModelConnector):
         async def generate(self, prompt: str, **kwargs): return f"DeepSeek: {prompt}"
    class MockAimlApiConnector(BaseModelConnector):
         async def generate(self, prompt: str, model: str, **kwargs): return f"AIMLAPI ({model}): {prompt}"
    class MockRouterApiConnector(BaseModelConnector): # Placeholder Mock
        async def generate(self, prompt: str, **kwargs): raise NotImplementedError("Mock RouterAPI not implemented")


    class TestModelRouter(unittest.TestCase):

        def setUp(self):
            """Setup mock connectors for each test."""
            # Use patching to replace real connectors with mocks during tests
            self.gemini_patch = patch('backend.models.model_router.GeminiConnector', MagicMock(spec=MockGeminiConnector, return_value=MockGeminiConnector()))
            self.deepseek_patch = patch('backend.models.model_router.DeepSeekConnector', MagicMock(spec=MockDeepSeekConnector, return_value=MockDeepSeekConnector()))
            self.aimlapi_patch = patch('backend.models.model_router.AimlApiConnector', MagicMock(spec=MockAimlApiConnector, return_value=MockAimlApiConnector()))
            self.routerapi_patch = patch('backend.models.model_router.RouterApiConnector', MagicMock(spec=MockRouterApiConnector, return_value=MockRouterApiConnector()))

            self.MockGemini = self.gemini_patch.start()
            self.MockDeepSeek = self.deepseek_patch.start()
            self.MockAimlApi = self.aimlapi_patch.start()
            self.MockRouterApi = self.routerapi_patch.start()

            # Ensure patches are applied before creating ModelRouter instance
            # Create a dummy settings object enabling all keys for mock testing
            self.mock_settings = Settings(
                GEMINI_API_KEY="fake", DEEPSEEK_API_KEY="fake",
                AIMLAPI_KEY="fake", ROUTERAPI_KEY="fake", # Fake key for placeholder init
                MODEL_FALLBACK_CHAIN="gemini,deepseek,aimlapi:gpt-4o" # Example fallback
            )
            self.router = ModelRouter(settings=self.mock_settings)


        def tearDown(self):
            """Stop all patches."""
            self.gemini_patch.stop()
            self.deepseek_patch.stop()
            self.aimlapi_patch.stop()
            self.routerapi_patch.stop()

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_initialization(self):
            """Test that connectors are initialized based on (mocked) settings."""
            self.assertIn("gemini", self.router.connectors)
            self.assertIn("deepseek", self.router.connectors)
            self.assertIn("aimlapi", self.router.connectors)
            self.assertIn("routerapi", self.router.connectors) # Placeholder should init
            self.assertIsInstance(self.router.connectors["gemini"], MockGeminiConnector)
            self.assertIsInstance(self.router.connectors["deepseek"], MockDeepSeekConnector)
            self.assertIsInstance(self.router.connectors["aimlapi"], MockAimlApiConnector)
            self.assertIsInstance(self.router.connectors["routerapi"], MockRouterApiConnector)
            print("Router initialized with mock connectors successfully.")

        def test_get_available_models(self):
            """Test listing available models."""
            available = self.router.get_available_models()
            self.assertListEqual(sorted(available), sorted(["gemini", "deepseek", "aimlapi", "routerapi"]))
            print(f"Available models reported: {available}")

        def test_route_to_preference_gemini(self):
            """Test routing to preferred Gemini connector."""
            result = self.run_async(self.router.generate("hello", model_preference="gemini"))
            self.assertEqual(result, "Gemini: hello")
            print("Routed to Gemini preference successfully.")

        def test_route_to_preference_deepseek(self):
            """Test routing to preferred DeepSeek connector."""
            result = self.run_async(self.router.generate("hello", model_preference="deepseek"))
            self.assertEqual(result, "DeepSeek: hello")
            print("Routed to DeepSeek preference successfully.")

        def test_route_to_preference_aimlapi(self):
            """Test routing to preferred AIMLAPI connector with specific model."""
            result = self.run_async(self.router.generate("hello", model_preference="aimlapi:gpt-4o"))
            self.assertEqual(result, "AIMLAPI (gpt-4o): hello")
            # Verify the mock was called with the correct model kwarg
            self.router.connectors["aimlapi"].generate.assert_called_once_with(prompt="hello", stream=False, model="gpt-4o")
            print("Routed to AIMLAPI preference with model override successfully.")

        def test_route_to_fallback_gemini(self):
            """Test falling back to Gemini when preference is invalid."""
            result = self.run_async(self.router.generate("hello", model_preference="nonexistent"))
            # Based on fallback chain "gemini,deepseek,aimlapi:gpt-4o"
            self.assertEqual(result, "Gemini: hello")
            print("Fell back to Gemini successfully.")

        def test_route_to_fallback_deepseek(self):
            """Test falling back to DeepSeek if Gemini fails."""
            # Make Gemini mock raise an error
            self.router.connectors["gemini"].generate = AsyncMock(side_effect=ModelConnectionError("Gemini", "Mock connection error"))
            result = self.run_async(self.router.generate("hello", model_preference="nonexistent"))
             # Based on fallback chain "gemini,deepseek,aimlapi:gpt-4o"
            self.assertEqual(result, "DeepSeek: hello")
            print("Fell back to DeepSeek after Gemini failure successfully.")

        def test_route_to_fallback_aimlapi(self):
            """Test falling back to AIMLAPI if Gemini and DeepSeek fail."""
            self.router.connectors["gemini"].generate = AsyncMock(side_effect=ModelConnectionError("Gemini", "Mock error"))
            self.router.connectors["deepseek"].generate = AsyncMock(side_effect=ModelConnectionError("DeepSeek", "Mock error"))
            result = self.run_async(self.router.generate("hello", model_preference="nonexistent"))
            # Based on fallback chain "gemini,deepseek,aimlapi:gpt-4o"
            self.assertEqual(result, "AIMLAPI (gpt-4o): hello")
             # Verify the mock was called with the correct model kwarg from fallback chain
            self.router.connectors["aimlapi"].generate.assert_called_once_with(prompt="hello", stream=False, model="gpt-4o")
            print("Fell back to AIMLAPI after Gemini/DeepSeek failure successfully.")

        def test_route_placeholder_skipped_in_fallback(self):
            """Test that the placeholder RouterApiConnector is skipped during fallback."""
            # Make Gemini, DeepSeek, AimlApi fail
            self.router.connectors["gemini"].generate = AsyncMock(side_effect=ModelConnectionError("Gemini", "Mock error"))
            self.router.connectors["deepseek"].generate = AsyncMock(side_effect=ModelConnectionError("DeepSeek", "Mock error"))
            self.router.connectors["aimlapi"].generate = AsyncMock(side_effect=ModelConnectionError("AimlApi", "Mock error"))
            # Add routerapi placeholder to fallback chain for test
            self.router.fallback_chain = ["gemini", "deepseek", "aimlapi:gpt-4o", "routerapi"]

            # Expect ModelConnectionError because all real connectors failed and placeholder raises NotImplementedError
            with self.assertRaises(ModelConnectionError) as cm:
                 self.run_async(self.router.generate("hello", model_preference="nonexistent"))
            print(f"Caught expected final ModelConnectionError after all fallbacks failed/skipped: {cm.exception}")
            self.assertTrue("No available model connector succeeded" in str(cm.exception))
            # Check that the placeholder's generate was called (and raised NotImplementedError, handled internally by router)
            self.router.connectors["routerapi"].generate.assert_called_once()


        def test_no_connectors_initialized_raises_error(self):
            """Test that router raises error if no connectors init (optional behavior)."""
            # This test depends on whether __init__ should raise an error
            # Currently, it only logs an error. To test raising, uncomment the raise in __init__
            # and modify this test.
            pass # Skipping for now as init only logs error


    # Run the tests
    print(f"\nRunning ModelRouter tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestModelRouter))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import ModelRouter or dependencies: {e}")
    print("Ensure backend/models/model_router.py and all connector files exist.")
except Exception as e:
    print(f"An error occurred during ModelRouter test setup: {e}")
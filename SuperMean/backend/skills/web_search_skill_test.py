# Test Snippet File: backend/skills/web_search_skill_test.py
# Description: Verifies the web_search_skill logic using mocking.
# Command: python -m backend.skills.web_search_skill_test

import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the GoogleSearch class from serpapi if the library isn't installed
try:
    from serpapi import GoogleSearch
except ImportError:
    # Create a mock class if serpapi is not installed
    GoogleSearch = MagicMock()
    # Ensure the module is recognized by patcher
    sys.modules['serpapi'] = MagicMock(GoogleSearch=GoogleSearch)


try:
    from backend.skills.web_search_skill import web_search
    from backend.skills import SkillError
    from backend.utils.config_loader import Settings # To mock settings
    print("Imported web search skill components successfully.")

    # Example SerpApi successful result structure
    MOCK_SERPAPI_RESULT = {
        "search_metadata": {"status": "Success"},
        "organic_results": [
            {
                "position": 1,
                "title": "Result 1 Title",
                "link": "https://example.com/result1",
                "snippet": "This is the snippet for result 1."
            },
            {
                "position": 2,
                "title": "Result 2 Title",
                "link": "https://example.com/result2",
                "snippet": "Snippet number two about the topic."
            }
        ]
    }
    # Example SerpApi error result
    MOCK_SERPAPI_ERROR = {
         "search_metadata": {"status": "Error"},
         "error": "Invalid API key."
    }

    class TestWebSearchSkill(unittest.TestCase):

        def setUp(self):
            # Patch get_settings to control API key availability
            self.settings_patch = patch('backend.skills.web_search_skill.get_settings')
            self.MockSettings = self.settings_patch.start()
            self.mock_settings = MagicMock(spec=Settings)
            self.MockSettings.return_value = self.mock_settings
            # Assume key is available by default in settings for most tests
            self.mock_settings.SERPAPI_KEY = "fake_test_key"
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def tearDown(self):
            self.settings_patch.stop()

        def run_async(self, coro):
            return asyncio.run(coro)

        @patch('backend.skills.web_search_skill.GoogleSearch') # Patch the class used in the skill file
        def test_search_success(self, MockGoogleSearch):
            """Test successful web search."""
            # Configure the mock GoogleSearch instance and its get_dict method
            mock_search_instance = MockGoogleSearch.return_value
            mock_search_instance.get_dict.return_value = MOCK_SERPAPI_RESULT

            query = "test query"
            num_results = 2
            results = self.run_async(web_search(query=query, num_results=num_results))

            # Assertions
            self.assertEqual(len(results), num_results)
            self.assertEqual(results[0]["title"], "Result 1 Title")
            self.assertEqual(results[0]["url"], "https://example.com/result1")
            self.assertEqual(results[0]["snippet"], "This is the snippet for result 1.")
            self.assertEqual(results[1]["position"], 2)
            # Check that GoogleSearch was initialized with correct params (excluding key)
            MockGoogleSearch.assert_called_once()
            call_args = MockGoogleSearch.call_args[0][0] # First positional arg (the dict)
            self.assertEqual(call_args['q'], query)
            self.assertEqual(call_args['num'], str(num_results))
            # Check that get_dict was called by the executor implicitly
            mock_search_instance.get_dict.assert_called_once()
            print("Successful search test passed.")

        @patch('backend.skills.web_search_skill.GoogleSearch')
        def test_search_with_api_key_arg(self, MockGoogleSearch):
            """Test passing API key directly as argument."""
            mock_search_instance = MockGoogleSearch.return_value
            mock_search_instance.get_dict.return_value = MOCK_SERPAPI_RESULT
            direct_api_key = "direct_key_123"

            # Make settings key None to ensure direct arg is used
            self.mock_settings.SERPAPI_KEY = None

            results = self.run_async(web_search(query="another query", api_key=direct_api_key))

            self.assertTrue(len(results) > 0)
            MockGoogleSearch.assert_called_once()
            call_args = MockGoogleSearch.call_args[0][0]
            self.assertEqual(call_args['api_key'], direct_api_key) # Verify direct key was used
            print("Search with direct API key passed.")

        def test_missing_api_key(self):
            """Test that ValueError is raised if no API key is available."""
            # Make settings key None and don't pass arg
            self.mock_settings.SERPAPI_KEY = None
            with self.assertRaises(ValueError) as cm:
                self.run_async(web_search(query="query without key"))
            self.assertIn("SerpApi key not found", str(cm.exception))
            print(f"Caught expected ValueError for missing API key: {cm.exception}")

        @patch('backend.skills.web_search_skill.GoogleSearch')
        def test_serpapi_returns_error(self, MockGoogleSearch):
            """Test handling of error message returned by SerpApi."""
            mock_search_instance = MockGoogleSearch.return_value
            mock_search_instance.get_dict.return_value = MOCK_SERPAPI_ERROR

            with self.assertRaises(SkillError) as cm:
                self.run_async(web_search(query="query causing error"))
            self.assertIn("SerpApi search failed", str(cm.exception))
            self.assertIn("Invalid API key", str(cm.exception)) # Check original error included
            print(f"Caught expected SkillError for SerpApi error response: {cm.exception}")

        @patch('backend.skills.web_search_skill.GoogleSearch')
        def test_serpapi_library_raises_exception(self, MockGoogleSearch):
            """Test handling of exceptions raised by the SerpApi library itself."""
            mock_search_instance = MockGoogleSearch.return_value
            # Simulate an exception during the get_dict call
            mock_search_instance.get_dict.side_effect = Exception("Network connection failed")

            with self.assertRaises(SkillError) as cm:
                self.run_async(web_search(query="query causing lib error"))
            self.assertIn("Web search failed", str(cm.exception))
            self.assertIn("Network connection failed", str(cm.exception)) # Check original error included
            print(f"Caught expected SkillError for SerpApi library exception: {cm.exception}")

        @unittest.skipIf(GoogleSearch is None, "Skipping test: google-search-results library not installed.")
        @patch('backend.skills.web_search_skill.GoogleSearch', None) # Simulate library not installed
        def test_library_not_installed(self):
             """Test error handling if serpapi library is not installed."""
             # Need to reload the module where the import happens, or patch at module level?
             # For simplicity, let's just try calling it, assuming the initial check works
             # This test setup is tricky, might need deeper patching or module reloading.
             # Re-importing the function might re-evaluate the check
             try:
                  from backend.skills.web_search_skill import web_search as ws_reloaded
                  with self.assertRaises(SkillError) as cm:
                       self.run_async(ws_reloaded(query="test"))
                  self.assertIn("library 'google-search-results' is not installed", str(cm.exception))
                  print(f"Caught expected SkillError for missing library: {cm.exception}")
             except ImportError:
                  self.fail("Test setup failed - could not re-import web_search")


    # Run the tests
    print("\nRunning Web Search Skill tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestWebSearchSkill))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import components: {e}")
    print("Ensure skill file, registry (__init__.py), ModelRouter, and utils exist.")
except Exception as e:
    print(f"An error occurred during test setup: {e}")
# Test Snippet File: backend/skills/summarizer_skill_test.py
# Description: Verifies the summarizer_skill logic using a mocked ModelRouter.
# Command: python -m backend.skills.summarizer_skill_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Import the skill function directly and SkillError
    from backend.skills.summarizer_skill import summarize_text
    from backend.skills import SkillError
    # We also need to mock the ModelRouter class
    from backend.models.model_router import ModelRouter
    print("Imported summarizer skill components successfully.")

    class TestSummarizerSkill(unittest.TestCase):

        def setUp(self):
            # Create a mock ModelRouter instance
            self.mock_router = MagicMock(spec=ModelRouter)
            # IMPORTANT: Configure the generate method as AsyncMock
            self.mock_router.generate = AsyncMock()
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_summarize_simple(self):
            """Test summarizing a simple piece of text."""
            input_text = "The quick brown fox jumps over the lazy dog. This sentence contains all letters of the English alphabet. It's often used for testing typefaces."
            expected_summary = "A sentence containing all English letters, used for testing typefaces."
            summary_length = "concise"
            target_model = "gemini" # Default

            # Configure the mock router's generate method
            self.mock_router.generate.return_value = expected_summary

            # Call the skill function
            result = self.run_async(summarize_text(
                text=input_text,
                model_router=self.mock_router,
                summary_length=summary_length
                # target_model uses default
            ))

            # Assertions
            self.assertEqual(result, expected_summary)
            # Verify the mock was called correctly
            self.mock_router.generate.assert_awaited_once()
            call_args = self.mock_router.generate.await_args
            self.assertIn(input_text, call_args.kwargs['prompt'])
            self.assertIn(summary_length, call_args.kwargs['prompt'])
            self.assertEqual(call_args.kwargs['model_preference'], target_model)
            print("Simple summarization test passed.")

        def test_summarize_with_target_model(self):
            """Test summarizing with a specific target model."""
            input_text = "Large language models are trained on vast amounts of text data to understand and generate human-like language."
            expected_summary = "LLMs learn from lots of text to generate language."
            summary_length = "very short"
            target_model = "aimlapi:gpt-3.5-turbo"

            self.mock_router.generate.return_value = expected_summary

            result = self.run_async(summarize_text(
                text=input_text,
                model_router=self.mock_router,
                summary_length=summary_length,
                target_model=target_model # Override default
            ))

            self.assertEqual(result, expected_summary)
            self.mock_router.generate.assert_awaited_once()
            call_args = self.mock_router.generate.await_args
            self.assertEqual(call_args.kwargs['model_preference'], target_model)
            print("Summarization with specific target model passed.")

        def test_summarize_empty_text(self):
            """Test summarizing empty text returns empty string."""
            input_text = "  " # Whitespace only
            expected_summary = ""

            # Call the skill function
            result = self.run_async(summarize_text(
                text=input_text,
                model_router=self.mock_router
            ))

            self.assertEqual(result, expected_summary)
            # Ensure the router was NOT called for empty input
            self.mock_router.generate.assert_not_awaited()
            print("Empty text summarization test passed.")


        def test_summarization_failure(self):
            """Test handling of errors from the model router during summarization."""
            input_text = "Some text that causes a failure."

            # Configure mock to raise an error
            self.mock_router.generate.side_effect = SkillError("LLM summarization failed")

            with self.assertRaises(SkillError) as cm:
                 self.run_async(summarize_text(
                    text=input_text,
                    model_router=self.mock_router
                 ))

            self.assertIn("Summarization failed", str(cm.exception))
            self.assertIn("LLM summarization failed", str(cm.exception)) # Check original error context
            print(f"Caught expected SkillError on summarization failure: {cm.exception}")


    # Run the tests
    print("\nRunning Summarizer Skill tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestSummarizerSkill))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import components: {e}")
    print("Ensure skill file, registry (__init__.py), ModelRouter, and utils exist.")
except Exception as e:
    print(f"An error occurred during test setup: {e}")
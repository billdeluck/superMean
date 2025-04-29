# Test Snippet File: backend/skills/code_writer_skill_test.py
# Description: Verifies the code_writer_skill logic using a mocked ModelRouter.
# Command: python -m backend.skills.code_writer_skill_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Import the skill function directly and SkillError
    from backend.skills.code_writer_skill import generate_code
    from backend.skills import SkillError
    # We also need to mock the ModelRouter class
    from backend.models.model_router import ModelRouter
    print("Imported code writer skill components successfully.")

    class TestCodeWriterSkill(unittest.TestCase):

        def setUp(self):
            # Create a mock ModelRouter instance
            self.mock_router = MagicMock(spec=ModelRouter)
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_generate_simple_python(self):
            """Test generating a simple Python function."""
            description = "Create a Python function that adds two numbers."
            language = "python"
            expected_code = "def add(a, b):\n  return a + b"

            # Configure the mock router's generate method
            self.mock_router.generate = AsyncMock(return_value=expected_code)

            # Call the skill function
            result = self.run_async(generate_code(
                description=description,
                language=language,
                model_router=self.mock_router
            ))

            # Assertions
            self.assertEqual(result, expected_code)
            # Verify the mock was called (can check args later if needed)
            self.mock_router.generate.assert_awaited_once()
            call_args = self.mock_router.generate.await_args
            self.assertIn(description, call_args.kwargs['prompt'])
            self.assertIn(language, call_args.kwargs['prompt'])
            self.assertEqual(call_args.kwargs['model_preference'], 'deepseek') # Default target
            print("Simple Python generation test passed.")


        def test_generate_with_context_and_target(self):
            """Test generation with context and a specific target model."""
            description = "Add error handling for division by zero."
            language = "python"
            context = "def divide(a, b):\n  return a / b"
            target_model = "aimlapi:gpt-4o"
            expected_code = """
def divide(a, b):
  if b == 0:
    raise ValueError("Cannot divide by zero")
  return a / b
""".strip() # Example expected output

            self.mock_router.generate = AsyncMock(return_value=expected_code)

            result = self.run_async(generate_code(
                description=description,
                language=language,
                context=context,
                target_model=target_model, # Override default
                model_router=self.mock_router,
                temperature=0.2 # Example of passing extra model kwarg
            ))

            self.assertEqual(result, expected_code)
            self.mock_router.generate.assert_awaited_once()
            call_args = self.mock_router.generate.await_args
            self.assertIn(description, call_args.kwargs['prompt'])
            self.assertIn(context, call_args.kwargs['prompt'])
            self.assertEqual(call_args.kwargs['model_preference'], target_model)
            self.assertEqual(call_args.kwargs['temperature'], 0.2) # Check extra kwarg
            print("Generation with context and target model test passed.")

        def test_generate_with_markdown_cleanup(self):
            """Test that markdown fences are removed from the output."""
            description = "Simple JS function"
            language = "javascript"
            # Simulate model output with markdown fences
            raw_model_output = f"```javascript\nfunction greet() {{\n  console.log('Hello!');\n}}\n```"
            expected_code = "function greet() {\n  console.log('Hello!');\n}"

            self.mock_router.generate = AsyncMock(return_value=raw_model_output)

            result = self.run_async(generate_code(
                description=description,
                language=language,
                model_router=self.mock_router
            ))
            self.assertEqual(result, expected_code)
            print("Markdown cleanup test passed.")


        def test_generation_failure(self):
            """Test handling of errors from the model router."""
            description = "Something complex"
            language = "rust"

            # Configure mock to raise an error
            self.mock_router.generate = AsyncMock(side_effect=SkillError("LLM unavailable"))

            with self.assertRaises(SkillError) as cm:
                 self.run_async(generate_code(
                    description=description,
                    language=language,
                    model_router=self.mock_router
                 ))

            self.assertIn("Code generation failed", str(cm.exception))
            self.assertIn("LLM unavailable", str(cm.exception))
            print(f"Caught expected SkillError on generation failure: {cm.exception}")


    # Run the tests
    print("\nRunning Code Writer Skill tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestCodeWriterSkill))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import components: {e}")
    print("Ensure skill file, registry (__init__.py), ModelRouter, and utils exist.")
except Exception as e:
    print(f"An error occurred during test setup: {e}")
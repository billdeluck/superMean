# Test Snippet File: backend/models/base_model_test.py
# Description: Verifies that the BaseModelConnector cannot be instantiated directly and enforces subclass implementation. (Revised Assertion Again)
# Command: python -m backend.models.base_model_test

import sys
import os
import unittest
import asyncio
# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from backend.models.base_model import BaseModelConnector
    print("Imported BaseModelConnector successfully.")

    class TestBaseModel(unittest.TestCase):

        def test_cannot_instantiate_abc(self):
            """Verify that the abstract base class cannot be instantiated directly."""
            with self.assertRaises(TypeError) as cm:
                BaseModelConnector()
            exception_text = str(cm.exception).lower()
            print(f"Caught expected TypeError: {cm.exception}")
            # Check for key parts case-insensitively
            self.assertTrue("can't instantiate abstract class" in exception_text)
            self.assertTrue("generate" in exception_text) # Check if the method name is mentioned

        def test_subclass_must_implement_generate(self):
            """Verify that a subclass must implement the abstract 'generate' method."""
            class IncompleteConnector(BaseModelConnector):
                # Missing the 'generate' method implementation
                pass

            with self.assertRaises(TypeError) as cm:
                IncompleteConnector()
            exception_text = str(cm.exception).lower()
            print(f"Caught expected TypeError for incomplete subclass: {cm.exception}")
            # Break down the check further and make it case-insensitive
            self.assertTrue("can't instantiate abstract class" in exception_text, "Missing 'can't instantiate abstract class'")
            self.assertTrue("incompleteconnector" in exception_text, "Missing class name 'IncompleteConnector'")
            self.assertTrue("abstract method" in exception_text, "Missing 'abstract method'")
            self.assertTrue("generate" in exception_text, "Missing method name 'generate'")


        def test_subclass_can_be_instantiated_with_implementation(self):
            """Verify a complete subclass can be instantiated."""
            class CompleteConnector(BaseModelConnector):
                async def generate(self, prompt: str, **kwargs) -> str:
                    return f"Generated response for: {prompt}"

            try:
                instance = CompleteConnector(api_key="test_key")
                self.assertIsInstance(instance, BaseModelConnector)
                self.assertEqual(instance.api_key, "test_key")
                self.assertEqual(instance.timeout, 60) # Default
                print("Complete subclass instantiated successfully.")
            except Exception as e:
                 self.fail(f"Instantiation of complete subclass failed: {e}")

        # Simple async test runner
        def run_async(self, coro):
            return asyncio.run(coro)

        def test_subclass_generate_works(self):
             """Verify the implemented generate method works."""
             class CompleteConnector(BaseModelConnector):
                 async def generate(self, prompt: str, **kwargs) -> str:
                     await asyncio.sleep(0.01) # Simulate async work
                     return f"Generated response for: {prompt}"

             instance = CompleteConnector(api_key="test_key")
             result = self.run_async(instance.generate("hello"))
             self.assertEqual(result, "Generated response for: hello")
             print("Implemented generate method test passed.")


    # Run the tests
    print("\nRunning BaseModelConnector tests...")
    suite = unittest.TestSuite()
    # Using loadTestsFromTestCase for compatibility with future Python versions
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestBaseModel))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import BaseModelConnector: {e}")
    print("Ensure backend/models/base_model.py exists and its dependencies (utils) are available.")
except Exception as e:
    print(f"An error occurred during base model test: {e}")
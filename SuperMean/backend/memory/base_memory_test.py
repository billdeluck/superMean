# Test Snippet File: backend/memory/base_memory_test.py
# Description: Verifies that the BaseMemory class cannot be instantiated directly and enforces subclass implementation. (Fixed Any import)
# Command: python -m backend.memory.base_memory_test

import sys
import os
import unittest
import asyncio
from typing import Any, List, Dict, Optional # <<< IMPORT ADDED HERE

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from backend.memory.base_memory import BaseMemory
    print("Imported BaseMemory successfully.")

    class TestBaseMemory(unittest.TestCase):

        def test_cannot_instantiate_abc(self):
            """Verify that the abstract base class cannot be instantiated directly."""
            with self.assertRaises(TypeError) as cm:
                BaseMemory()
            exception_text = str(cm.exception).lower()
            print(f"Caught expected TypeError: {cm.exception}")
            # Check for key parts case-insensitively
            self.assertTrue("can't instantiate abstract class" in exception_text)
            self.assertTrue("store" in exception_text) # Check one abstract method
            self.assertTrue("retrieve" in exception_text)
            self.assertTrue("search" in exception_text)
            self.assertTrue("delete" in exception_text)

        def test_subclass_must_implement_all(self):
            """Verify that a subclass must implement all abstract methods."""
            class IncompleteMemory(BaseMemory):
                # Missing several implementations
                 # Uses Any, requires import
                 async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool: return True
                 async def retrieve(self, key: str) -> Optional[Any]: return None
                 # Missing search, delete

            with self.assertRaises(TypeError) as cm:
                IncompleteMemory()
            exception_text = str(cm.exception).lower()
            print(f"Caught expected TypeError for incomplete subclass: {cm.exception}")
            self.assertTrue("can't instantiate abstract class" in exception_text)
            self.assertTrue("search" in exception_text) # Check a missing one
            self.assertTrue("delete" in exception_text) # Check another missing one

        def test_subclass_can_be_instantiated_with_implementation(self):
            """Verify a complete subclass can be instantiated."""
            class CompleteMemory(BaseMemory):
                 # Uses Any, requires import
                 async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool: return True
                 async def retrieve(self, key: str) -> Optional[Any]: return value if key == "test" else None
                 async def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]: return [{"key": "test", "value": "data", "score": 0.9}] if query == "find" else []
                 async def delete(self, key: str) -> bool: return True

            try:
                instance = CompleteMemory(config={"path": "/tmp"})
                self.assertIsInstance(instance, BaseMemory)
                self.assertEqual(instance.config, {"path": "/tmp"})
                print("Complete subclass instantiated successfully.")
            except Exception as e:
                 self.fail(f"Instantiation of complete subclass failed: {e}")

        # Simple async test runner
        def run_async(self, coro):
            return asyncio.run(coro)

        def test_subclass_methods_work(self):
             """Verify the implemented methods work."""
             class CompleteMemory(BaseMemory):
                 _data = {}
                 # Uses Any, requires import
                 async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool: self._data[key] = value; return True
                 async def retrieve(self, key: str) -> Optional[Any]: return self._data.get(key)
                 async def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]: return [{"key": k, "value": v, "metadata": {}} for k,v in self._data.items() if query in k or query in str(v)][:top_k] # Added metadata to match return type hint
                 async def delete(self, key: str) -> bool: return self._data.pop(key, None) is not None

             instance = CompleteMemory()
             self.assertTrue(self.run_async(instance.store("key1", "value1")))
             self.assertEqual(self.run_async(instance.retrieve("key1")), "value1")
             self.assertIsNone(self.run_async(instance.retrieve("key_unknown")))
             results = self.run_async(instance.search("value"))
             self.assertEqual(len(results), 1)
             self.assertEqual(results[0]["key"], "key1")
             self.assertTrue(self.run_async(instance.delete("key1")))
             self.assertFalse(self.run_async(instance.delete("key1"))) # Already deleted
             print("Implemented methods test passed.")


    # Run the tests
    print("\nRunning BaseMemory tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestBaseMemory))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import BaseMemory: {e}")
    print("Ensure backend/memory/base_memory.py exists and its dependencies (utils) are available.")
except Exception as e:
    print(f"An error occurred during base memory test: {e}")
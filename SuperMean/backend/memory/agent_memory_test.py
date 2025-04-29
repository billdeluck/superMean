# Test Snippet File: backend/memory/agent_memory_test.py
# Description: Verifies the functionality of the in-memory AgentMemory.
# Command: python -m backend.memory.agent_memory_test

import sys
import os
import unittest
import asyncio
from typing import Any, List, Dict, Optional # Import necessary types

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from backend.memory.agent_memory import AgentMemory
    print("Imported AgentMemory successfully.")

    class TestAgentMemory(unittest.TestCase):

        def setUp(self):
            """Set up a fresh AgentMemory instance for each test."""
            self.agent_id = "test_agent_001"
            self.memory = AgentMemory(agent_id=self.agent_id)
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            """Helper to run async functions."""
            return asyncio.run(coro)

        def test_initialization(self):
            """Test memory initialization."""
            self.assertEqual(self.memory.agent_id, self.agent_id)
            self.assertEqual(self.memory._data, {})
            print("Initialization test passed.")

        def test_store_and_retrieve(self):
            """Test storing and retrieving simple values."""
            key1 = "greeting"
            value1 = "Hello, World!"
            self.assertTrue(self.run_async(self.memory.store(key1, value1)))
            retrieved_value = self.run_async(self.memory.retrieve(key1))
            self.assertEqual(retrieved_value, value1)
            print("Store and retrieve simple value test passed.")

        def test_store_and_retrieve_with_metadata(self):
            """Test storing and retrieving with metadata."""
            key1 = "config"
            value1 = {"mode": "test", "level": 5}
            meta1 = {"source": "setup", "timestamp": "2024-01-01T10:00:00Z"}
            self.assertTrue(self.run_async(self.memory.store(key1, value1, meta1)))

            retrieved_entry = self.run_async(self.memory.retrieve_with_metadata(key1))
            self.assertIsNotNone(retrieved_entry)
            self.assertEqual(retrieved_entry["value"], value1)
            self.assertEqual(retrieved_entry["metadata"], meta1)

            # Test retrieving only value
            retrieved_value = self.run_async(self.memory.retrieve(key1))
            self.assertEqual(retrieved_value, value1)
            print("Store and retrieve with metadata test passed.")

        def test_retrieve_nonexistent_key(self):
            """Test retrieving a key that doesn't exist."""
            retrieved_value = self.run_async(self.memory.retrieve("nonexistent_key"))
            self.assertIsNone(retrieved_value)
            retrieved_entry = self.run_async(self.memory.retrieve_with_metadata("nonexistent_key"))
            self.assertIsNone(retrieved_entry)
            print("Retrieve nonexistent key test passed.")

        def test_store_overwrite(self):
            """Test overwriting an existing key."""
            key1 = "status"
            value1 = "initial"
            value2 = "updated"
            meta1 = {"v": 1}
            meta2 = {"v": 2}
            self.assertTrue(self.run_async(self.memory.store(key1, value1, meta1)))
            self.assertTrue(self.run_async(self.memory.store(key1, value2, meta2))) # Overwrite

            retrieved_entry = self.run_async(self.memory.retrieve_with_metadata(key1))
            self.assertIsNotNone(retrieved_entry)
            self.assertEqual(retrieved_entry["value"], value2)
            self.assertEqual(retrieved_entry["metadata"], meta2)
            print("Store overwrite test passed.")

        def test_delete(self):
            """Test deleting entries."""
            key1 = "temp_data"
            value1 = [1, 2, 3]
            self.assertTrue(self.run_async(self.memory.store(key1, value1)))
            self.assertIsNotNone(self.run_async(self.memory.retrieve(key1)))

            self.assertTrue(self.run_async(self.memory.delete(key1)))
            self.assertIsNone(self.run_async(self.memory.retrieve(key1)))

            # Test deleting nonexistent key
            self.assertFalse(self.run_async(self.memory.delete("nonexistent_key")))
            print("Delete test passed.")

        def test_search_simple(self):
            """Test basic search functionality."""
            self.run_async(self.memory.store("goal1", "Achieve world peace.", {"type": "ambitious"}))
            self.run_async(self.memory.store("task1", "Write report on peace.", {"type": "concrete"}))
            self.run_async(self.memory.store("memo", "Remember milk.", {"type": "chore"}))

            # Search by value content
            results = self.run_async(self.memory.search("peace"))
            self.assertEqual(len(results), 2)
            self.assertIn("goal1", [r["key"] for r in results])
            self.assertIn("task1", [r["key"] for r in results])

            # Search by key content
            results = self.run_async(self.memory.search("task"))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["key"], "task1")

            # Case-insensitive search
            results = self.run_async(self.memory.search("ACHIEVE"))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["key"], "goal1")

            # No results
            results = self.run_async(self.memory.search("xyz123"))
            self.assertEqual(len(results), 0)
            print("Simple search test passed.")

        def test_search_with_metadata_filter(self):
            """Test search with metadata filtering."""
            self.run_async(self.memory.store("goal1", "Achieve world peace.", {"type": "ambitious", "priority": 1}))
            self.run_async(self.memory.store("task1", "Write report on peace.", {"type": "concrete", "priority": 2}))
            self.run_async(self.memory.store("memo", "Remember milk.", {"type": "chore", "priority": 3}))

            # Filter by type = concrete
            results = self.run_async(self.memory.search("peace", filter_metadata={"type": "concrete"}))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["key"], "task1")

            # Filter by type = ambitious
            results = self.run_async(self.memory.search("peace", filter_metadata={"type": "ambitious"}))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["key"], "goal1")

            # Filter by priority = 3 (value doesn't matter for search term here)
            results = self.run_async(self.memory.search("re", filter_metadata={"priority": 3}))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["key"], "memo")

             # Filter by non-matching metadata
            results = self.run_async(self.memory.search("peace", filter_metadata={"type": "chore"}))
            self.assertEqual(len(results), 0)

            # Filter by multiple metadata fields
            results = self.run_async(self.memory.search("peace", filter_metadata={"type": "concrete", "priority": 2}))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["key"], "task1")

            results = self.run_async(self.memory.search("peace", filter_metadata={"type": "concrete", "priority": 1})) # Mismatch
            self.assertEqual(len(results), 0)
            print("Search with metadata filter test passed.")

        def test_search_top_k(self):
            """Test the top_k limit in search."""
            for i in range(10):
                self.run_async(self.memory.store(f"key_{i}", f"value_{i}_searchterm", {"index": i}))

            results = self.run_async(self.memory.search("searchterm", top_k=5))
            self.assertEqual(len(results), 5)

            results = self.run_async(self.memory.search("searchterm", top_k=15))
            self.assertEqual(len(results), 10) # Only 10 entries exist

            results = self.run_async(self.memory.search("searchterm", top_k=3))
            self.assertEqual(len(results), 3)
            print("Search top_k test passed.")

        def test_list_keys_and_clear(self):
            """Test listing keys and clearing memory."""
            keys = ["k1", "k2", "k3"]
            for k in keys:
                 self.run_async(self.memory.store(k, f"val_{k}"))

            stored_keys = self.run_async(self.memory.list_keys())
            self.assertCountEqual(stored_keys, keys) # Check elements regardless of order

            self.assertTrue(self.run_async(self.memory.clear()))
            self.assertEqual(len(self.run_async(self.memory.list_keys())), 0)
            self.assertEqual(self.memory._data, {})
            print("List keys and clear test passed.")


    # Run the tests
    print("\nRunning AgentMemory tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestAgentMemory))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import AgentMemory: {e}")
    print("Ensure backend/memory/agent_memory.py and its dependencies exist.")
except Exception as e:
    print(f"An error occurred during AgentMemory test setup: {e}")
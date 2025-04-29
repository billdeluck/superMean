# Test Snippet File: backend/memory/global_memory_test.py
# Description: Verifies the functionality of the ChromaDB-based GlobalMemory.
# Command: python -m backend.memory.global_memory_test

import sys
import os
import unittest
import asyncio
import shutil
import time
from typing import Any, List, Dict, Optional # Import necessary types

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Define path for test database
TEST_CHROMA_PATH = "./test_global_memory_db"

# Clean up any previous test DB before imports
if os.path.exists(TEST_CHROMA_PATH):
    try:
        shutil.rmtree(TEST_CHROMA_PATH)
        print(f"Removed previous test DB directory: {TEST_CHROMA_PATH}")
    except Exception as e:
        print(f"Error removing previous test DB directory: {e}")

try:
    from backend.memory.global_memory import GlobalMemory, DEFAULT_COLLECTION_NAME, VALUE_METADATA_KEY
    print("Imported GlobalMemory (ChromaDB) successfully.")

    class TestGlobalMemoryChroma(unittest.TestCase):

        test_db_path = TEST_CHROMA_PATH
        test_collection_name = f"test_{DEFAULT_COLLECTION_NAME}"

        @classmethod
        def setUpClass(cls):
            """Clean up directory before all tests in this class."""
            if os.path.exists(cls.test_db_path):
                shutil.rmtree(cls.test_db_path)

        @classmethod
        def tearDownClass(cls):
            """Clean up directory after all tests in this class."""
            # Add a small delay to release file locks if necessary
            time.sleep(0.1)
            if os.path.exists(cls.test_db_path):
                try:
                    shutil.rmtree(cls.test_db_path)
                    print(f"Cleaned up test DB directory: {cls.test_db_path}")
                except Exception as e:
                     print(f"Error cleaning up test DB directory: {e}")

        def setUp(self):
            """Set up before each test."""
            # Create a new instance for each test - it will use/create the same persistent dir
            self.memory_config = {"chroma_path": self.test_db_path, "collection_name": self.test_collection_name}
            self.memory1 = GlobalMemory(config=self.memory_config)
            self.memory2 = GlobalMemory(config=self.memory_config) # Second instance uses same dir/collection
            # Clear the collection content before each test method
            self.run_async(self.memory1.clear())
            print(f"\n--- Starting test: {self._testMethodName} ---")
            # Verify clear worked
            count = self.memory1._collection.count() if self.memory1._collection else 0
            self.assertEqual(count, 0, "Collection should be empty at start of test")


        def run_async(self, coro):
            """Helper to run async functions."""
            return asyncio.run(coro)

        def test_initialization(self):
            """Test memory initialization."""
            self.assertIsNotNone(self.memory1._client)
            self.assertIsNotNone(self.memory1._collection)
            self.assertEqual(self.memory1.collection_name, self.test_collection_name)
            # Check persistence directory exists
            self.assertTrue(os.path.exists(self.test_db_path))
            print("Initialization test passed.")

        def test_store_and_retrieve(self):
            """Test storing and retrieving values."""
            key1 = "fact_1"
            value1 = "Earth is round."
            meta1 = {"category": "science", "verified": True}
            key2 = "complex_data"
            value2 = {"a": [1, 2], "b": "hello"}
            meta2 = {"source": "test"}

            self.assertTrue(self.run_async(self.memory1.store(key1, value1, meta1)))
            self.assertTrue(self.run_async(self.memory2.store(key2, value2, meta2))) # Store via instance 2

            # Retrieve via instance 1
            retrieved_value1 = self.run_async(self.memory1.retrieve(key1))
            self.assertEqual(retrieved_value1, value1)

            retrieved_entry2 = self.run_async(self.memory1.retrieve_with_metadata(key2))
            self.assertIsNotNone(retrieved_entry2)
            self.assertEqual(retrieved_entry2["value"], value2) # Check deserialized value
            self.assertEqual(retrieved_entry2["metadata"], meta2) # Check user metadata
            self.assertIsInstance(retrieved_entry2["document"], str) # Check document is string

            # Check internal storage detail (optional)
            chroma_entry = self.memory1._collection.get(ids=[key2], include=['metadatas'])
            self.assertIn(VALUE_METADATA_KEY, chroma_entry['metadatas'][0])

            print("Store and retrieve test passed.")

        def test_retrieve_nonexistent_key(self):
            """Test retrieving a key that doesn't exist."""
            retrieved_value = self.run_async(self.memory1.retrieve("nonexistent_key"))
            self.assertIsNone(retrieved_value)
            retrieved_entry = self.run_async(self.memory1.retrieve_with_metadata("nonexistent_key"))
            self.assertIsNone(retrieved_entry)
            print("Retrieve nonexistent key test passed.")

        def test_delete(self):
            """Test deleting entries."""
            key1 = "temp_data_chroma"
            value1 = 99
            self.assertTrue(self.run_async(self.memory1.store(key1, value1)))
            # Verify existence via instance 2
            self.assertIsNotNone(self.run_async(self.memory2.retrieve(key1)))

            # Delete using instance 1
            self.assertTrue(self.run_async(self.memory1.delete(key1)))

            # Verify deletion using instance 2
            self.assertIsNone(self.run_async(self.memory2.retrieve(key1)))

            # Test deleting nonexistent key returns True (Chroma doesn't error)
            self.assertTrue(self.run_async(self.memory1.delete("nonexistent_key")))
            print("Delete test passed.")

        def test_search_metadata_filter(self):
            """Test search with metadata filtering."""
            self.run_async(self.memory1.store("item_a", "alpha", {"type": "letter", "group": 1}))
            self.run_async(self.memory2.store("item_b", "beta", {"type": "letter", "group": 1}))
            self.run_async(self.memory1.store("item_c", "charlie", {"type": "letter", "group": 2}))
            self.run_async(self.memory2.store("num_1", 123, {"type": "number", "group": 2}))

            # Filter by type = letter
            results = self.run_async(self.memory1.search("", filter_metadata={"type": "letter"}))
            self.assertEqual(len(results), 3)
            self.assertCountEqual([r["key"] for r in results], ["item_a", "item_b", "item_c"])

            # Filter by group = 1
            results = self.run_async(self.memory2.search("ignored_query", filter_metadata={"group": 1}))
            self.assertEqual(len(results), 2)
            self.assertCountEqual([r["key"] for r in results], ["item_a", "item_b"])

            # Filter by group = 2
            results = self.run_async(self.memory1.search("query", filter_metadata={"group": 2}))
            self.assertEqual(len(results), 2)
            self.assertCountEqual([r["key"] for r in results], ["item_c", "num_1"])

            # Filter by type = number
            results = self.run_async(self.memory2.search("", filter_metadata={"type": "number"}))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["key"], "num_1")
            self.assertEqual(results[0]["value"], 123) # Verify deserialized value

            # Filter by non-matching metadata
            results = self.run_async(self.memory1.search("", filter_metadata={"type": "symbol"}))
            self.assertEqual(len(results), 0)

            # Filter with multiple conditions (ChromaDB uses $and implicitly for dicts)
            results = self.run_async(self.memory2.search("", filter_metadata={"type": "letter", "group": 1}))
            self.assertEqual(len(results), 2)
            self.assertCountEqual([r["key"] for r in results], ["item_a", "item_b"])

            results = self.run_async(self.memory1.search("", filter_metadata={"type": "letter", "group": 3})) # No match
            self.assertEqual(len(results), 0)

            # Test complex filter ($and is implicit, use $or explicitly if needed)
            # results = self.run_async(self.memory1.search("", filter_metadata={"$or": [{"type":"number"}, {"group":1}]}))
            # self.assertEqual(len(results), 3) # item_a, item_b, num_1

            print("Search with metadata filter test passed.")


        def test_search_top_k(self):
            """Test the top_k limit in search."""
            for i in range(10):
                 self.run_async(self.memory1.store(f"key_{i}", f"value_{i}", {"index": i}))

            # Search requires a filter for this implementation
            results = self.run_async(self.memory1.search("", filter_metadata={"index": {"$gte": 0}}, top_k=5)) # Filter for all, limit 5
            self.assertEqual(len(results), 5)

            results = self.run_async(self.memory1.search("", filter_metadata={"index": {"$gte": 0}}, top_k=15))
            self.assertEqual(len(results), 10) # Only 10 entries exist

            results = self.run_async(self.memory1.search("", filter_metadata={"index": {"$lt": 3}}, top_k=5)) # Filter for 0,1,2
            self.assertEqual(len(results), 3)
            print("Search top_k test passed.")

        def test_list_keys_and_clear(self):
            """Test listing keys and clearing memory."""
            keys = ["k1", "k2", "k3"]
            for k in keys:
                 self.run_async(self.memory1.store(k, f"val_{k}"))

            stored_keys = self.run_async(self.memory2.list_keys()) # List via instance 2
            self.assertCountEqual(stored_keys, keys) # Check elements regardless of order

            self.assertTrue(self.run_async(self.memory1.clear())) # Clear via instance 1
            self.assertEqual(len(self.run_async(self.memory2.list_keys())), 0) # Verify via instance 2
            self.assertEqual(self.memory1._collection.count(), 0)
            print("List keys and clear test passed.")


    # Run the tests
    print("\nRunning GlobalMemory (ChromaDB) tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestGlobalMemoryChroma))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import GlobalMemory or ChromaDB: {e}")
    print("Ensure backend/memory/global_memory.py and its dependencies (chromadb) exist and are installed.")
except Exception as e:
    print(f"An error occurred during GlobalMemory test setup: {e}")
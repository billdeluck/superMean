# Test Snippet File: backend/skills/skills_test.py
# Description: Verifies the skill registration and calling mechanism. (Corrected)
# Command: python -m backend.skills.skills_test

import sys
import os
import unittest
import asyncio
from typing import Dict, Any, List, Optional

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Clear registry before defining test skills (important for re-runs)
if "_skills_registry" in sys.modules["backend.skills"].__dict__:
     sys.modules["backend.skills"].__dict__["_skills_registry"].clear()


try:
    # Import core functions from the skills package __init__
    from backend.skills import register_skill, execute_skill, list_skills, get_skill_metadata, SkillError, _skills_registry
    print("Imported skill functions successfully.")

    # --- Define some test skills ---
    @register_skill(name="test.add", description="Adds two numbers.", category="math")
    def add_sync(a: int, b: int) -> int:
        print(f"Executing sync add: {a} + {b}")
        return a + b

    @register_skill(name="test.greet", description="Generates a greeting.", category="text")
    async def greet_async(name: str = "World") -> str:
        print(f"Executing async greet for: {name}")
        await asyncio.sleep(0.01) # Simulate async work
        return f"Hello, {name}!"

    # Test skill with no explicit name (should use function name)
    @register_skill(description="Multiplies two numbers.", category="math")
    def multiply(x: float, y: float) -> float:
         print(f"Executing sync multiply: {x} * {y}")
         return x * y

    # Test skill that raises an error
    @register_skill(name="test.fail", category="debug")
    def fail_skill():
        raise ValueError("This skill is designed to fail.")


    class TestSkillsRegistry(unittest.TestCase):

        def setUp(self):
            # Registry should be populated by decorators above when module is loaded
            self.assertTrue("test.add" in _skills_registry)
            self.assertTrue("test.greet" in _skills_registry)
            self.assertTrue("multiply" in _skills_registry)
            self.assertTrue("test.fail" in _skills_registry)
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            # Helper to run the awaitable skill executions
            return asyncio.run(coro)

        def test_list_skills(self):
            """Test listing all skills."""
            skills = list_skills()
            skill_names = [s['name'] for s in skills]
            self.assertIn("test.add", skill_names)
            self.assertIn("test.greet", skill_names)
            self.assertIn("multiply", skill_names)
            self.assertIn("test.fail", skill_names)
            print(f"list_skills() found: {[s['name'] for s in skills]}")

        def test_list_skills_by_category(self):
            """Test listing skills filtered by category."""
            math_skills = list_skills(category="math")
            math_skill_names = [s['name'] for s in math_skills]
            self.assertIn("test.add", math_skill_names)
            self.assertIn("multiply", math_skill_names)
            self.assertNotIn("test.greet", math_skill_names)
            print(f"list_skills(category='math') found: {math_skill_names}")

            text_skills = list_skills(category="text")
            self.assertEqual(len(text_skills), 1)
            self.assertEqual(text_skills[0]["name"], "test.greet")
            print(f"list_skills(category='text') found: {[s['name'] for s in text_skills]}")

            nonexistent_skills = list_skills(category="nonexistent")
            self.assertEqual(len(nonexistent_skills), 0)
            print(f"list_skills(category='nonexistent') found: {nonexistent_skills}")

        def test_get_skill_metadata(self):
            """Test retrieving metadata for a specific skill."""
            metadata = get_skill_metadata("test.add")
            self.assertIsNotNone(metadata)
            self.assertEqual(metadata["description"], "Adds two numbers.")
            self.assertEqual(metadata["category"], "math")
            self.assertEqual(metadata["return_type"], "int") # Check corrected type name
            self.assertEqual(len(metadata["parameters"]), 2)
            self.assertEqual(metadata["parameters"][0]["name"], "a")
            self.assertEqual(metadata["parameters"][0]["type"], "int") # Check corrected type name
            self.assertTrue(metadata["parameters"][0]["required"])
            print(f"Metadata for 'test.add': {metadata}")

            metadata_greet = get_skill_metadata("test.greet")
            self.assertIsNotNone(metadata_greet)
            self.assertEqual(metadata_greet["category"], "text")
            self.assertEqual(metadata_greet["return_type"], "str") # Check corrected type name
            self.assertEqual(metadata_greet["parameters"][0]["name"], "name")
            self.assertEqual(metadata_greet["parameters"][0]["type"], "str") # Check corrected type name
            self.assertFalse(metadata_greet["parameters"][0]["required"]) # Has default
            self.assertEqual(metadata_greet["parameters"][0]["default"], "World")
            print(f"Metadata for 'test.greet': {metadata_greet}")

            self.assertIsNone(get_skill_metadata("nonexistent.skill"))
            print("Metadata retrieval tests passed.")

        def test_call_sync_skill(self):
            """Test calling a registered synchronous skill via execute_skill."""
            # Use execute_skill which returns the awaitable result
            result = self.run_async(execute_skill("test.add", 5, 3))
            self.assertEqual(result, 8)

            result_mult = self.run_async(execute_skill("multiply", y=4, x=2.5)) # Keyword args
            self.assertEqual(result_mult, 10.0)
            print("Sync skill calls passed.")

        def test_call_async_skill(self):
            """Test calling a registered asynchronous skill via execute_skill."""
             # Use execute_skill which returns the awaitable result
            result = self.run_async(execute_skill("test.greet", name="Tester"))
            self.assertEqual(result, "Hello, Tester!")

            result_default = self.run_async(execute_skill("test.greet")) # Use default arg
            self.assertEqual(result_default, "Hello, World!")
            print("Async skill calls passed.")

        def test_call_nonexistent_skill(self):
            """Test calling a skill that doesn't exist."""
            with self.assertRaises(SkillError) as cm:
                self.run_async(execute_skill("nonexistent.skill")) # Use execute_skill
            print(f"Caught expected SkillError for nonexistent skill: {cm.exception}")
            self.assertTrue("not found" in str(cm.exception))

        def test_call_skill_with_error(self):
            """Test calling a skill that raises an internal error."""
            with self.assertRaises(SkillError) as cm:
                 self.run_async(execute_skill("test.fail")) # Use execute_skill
            print(f"Caught expected SkillError for failing skill: {cm.exception}")
            # Check that the original exception type is the cause
            self.assertTrue("Execution failed" in str(cm.exception))
            self.assertIsInstance(cm.exception.__cause__, ValueError) # Check original cause
            self.assertTrue("designed to fail" in str(cm.exception.__cause__))


    # Run the tests
    print("\nRunning Skills Registry tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestSkillsRegistry))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import skill components: {e}")
    print("Ensure backend/skills/__init__.py exists and is importable.")
except Exception as e:
    print(f"An error occurred during skills test setup: {e}")
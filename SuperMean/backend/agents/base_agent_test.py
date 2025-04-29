# Test Snippet File: backend/agents/base_agent_test.py
# Description: Verifies the BaseAgent abstraction and helper methods. (Corrected Assertion)
# Command: python -m backend.agents.base_agent_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.agents.base_agent import BaseAgent
    from backend.models.model_router import ModelRouter # For mocking
    from backend.memory.base_memory import BaseMemory   # For mocking
    from backend.skills import SkillError, execute_skill as execute_skill_func # Import renamed func
    print("Imported BaseAgent successfully.")

    # --- Mock Components ---
    # Use MagicMock to allow flexible attribute access/method calls unless specified otherwise
    MockModelRouter = MagicMock(spec=ModelRouter)
    MockMemory = MagicMock(spec=BaseMemory)
    mock_execute_skill = AsyncMock() # Mock the standalone execute_skill function

    # --- Concrete Subclass for Testing ---
    class ConcreteAgent(BaseAgent):
        # Minimal implementation of the abstract method for testing base class features
        async def run(self, task_description: str, **kwargs) -> str:
            self.log.info(f"ConcreteAgent running task: {task_description}")
            # Example usage of helpers to ensure they can be called
            await self._remember("last_task_run", task_description)
            response = await self._call_llm("Briefly acknowledge task.", model_preference='gemini')
            return f"Ran task: {task_description}. LLM says: {response}"


    class TestBaseAgent(unittest.TestCase):

        def setUp(self):
            # Create NEW mock instances for each test
            self.mock_router_instance = MagicMock(spec=ModelRouter)
            self.mock_memory_instance = MagicMock(spec=BaseMemory)
            self.mock_execute_skill_instance = AsyncMock() # Reset the mock function for each test

            # Configure async methods on mocks needed for the concrete class or helpers
            self.mock_router_instance.generate = AsyncMock(return_value="Mock LLM Ack")
            self.mock_memory_instance.store = AsyncMock(return_value=True)
            self.mock_memory_instance.retrieve = AsyncMock(return_value="Mock Recalled Value")
            self.mock_memory_instance.search = AsyncMock(return_value=[{"key":"k", "value":"v"}])
            self.mock_execute_skill_instance.return_value = "Mock Skill Result" # Default result

            self.agent_id = "test_concrete_agent_01"
            self.agent_name = "ConcreteAgent"

            # Instantiate the concrete subclass for testing helpers (not needed for abstract test)
            # self.agent is now primarily for testing helper methods
            self.agent = ConcreteAgent(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                model_router=self.mock_router_instance,
                agent_memory=self.mock_memory_instance,
                execute_skill_func=self.mock_execute_skill_instance, # Pass the instance mock
                system_prompt="Test System Prompt"
            )
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_cannot_instantiate_abc(self):
            """Verify BaseAgent cannot be instantiated directly."""
            with self.assertRaises(TypeError) as cm:
                # Attempt to instantiate the abstract class directly
                BaseAgent(
                    agent_id="abc_id", agent_name="ABC",
                    model_router=self.mock_router_instance,
                    agent_memory=self.mock_memory_instance,
                    execute_skill_func=self.mock_execute_skill_instance
                )
            exception_text_lower = str(cm.exception).lower()
            print(f"Caught expected TypeError: {cm.exception}")
            # --- CORRECTED ASSERTIONS ---
            self.assertTrue("can't instantiate abstract class baseagent" in exception_text_lower)
            self.assertTrue("abstract method 'run'" in exception_text_lower) # Check for 'run'
            # --- END CORRECTIONS ---
            print("Abstract class instantiation test passed.")

        def test_subclass_instantiation(self):
            """Verify concrete subclass can be instantiated."""
            self.assertIsInstance(self.agent, BaseAgent)
            self.assertEqual(self.agent.agent_id, self.agent_id)
            self.assertEqual(self.agent.default_system_prompt, "Test System Prompt")
            print("Concrete subclass instantiation test passed.")

        def test_helper_call_llm(self):
            """Test the _call_llm helper method."""
            prompt = "Test LLM prompt"
            response = self.run_async(self.agent._call_llm(prompt, model_preference="test_model"))
            # Use the return value set in setUp
            self.assertEqual(response, "Mock LLM Ack")
            self.mock_router_instance.generate.assert_awaited_once()
            call_args, call_kwargs = self.mock_router_instance.generate.await_args
            self.assertTrue(call_kwargs['prompt'].startswith("Test System Prompt"))
            self.assertTrue(call_kwargs['prompt'].endswith(f"USER: {prompt}\n\nASSISTANT:"))
            self.assertEqual(call_kwargs['model_preference'], "test_model")
            print("Helper _call_llm test passed.")

        def test_helper_use_skill(self):
            """Test the _use_skill helper method."""
            skill_name = "test.some_skill"
            arg1 = 10
            kwarg1 = "value"
            response = self.run_async(self.agent._use_skill(skill_name, arg1, kw=kwarg1))
            self.assertEqual(response, "Mock Skill Result")
            # Assert that the mock function *instance* was called
            self.mock_execute_skill_instance.assert_awaited_once_with(skill_name, arg1, kw=kwarg1)
            print("Helper _use_skill test passed.")

        def test_helper_use_skill_passes_router_when_needed(self):
            """Test that _use_skill injects router for specific skills."""
            skill_name = "code.write" # Assumed to need router
            self.run_async(self.agent._use_skill(skill_name, "desc", "lang"))
            self.mock_execute_skill_instance.assert_awaited_once()
            call_args, call_kwargs = self.mock_execute_skill_instance.call_args
            self.assertEqual(call_args[0], skill_name)
            self.assertEqual(call_args[1], "desc")
            self.assertEqual(call_args[2], "lang")
            self.assertIn('model_router', call_kwargs)
            self.assertIs(call_kwargs['model_router'], self.mock_router_instance)
            print("Helper _use_skill router injection test passed.")

        def test_helper_memory_operations(self):
            """Test the memory helper methods (_remember, _recall, _search_memory)."""
            key = "memory_key"
            value = {"data": 123}
            meta = {"tag": "test"}

            result = self.run_async(self.agent._remember(key, value, meta))
            self.assertTrue(result)
            self.mock_memory_instance.store.assert_awaited_once()
            call_kwargs = self.mock_memory_instance.store.await_args.kwargs
            self.assertEqual(call_kwargs['key'], key)
            self.assertEqual(call_kwargs['value'], value)
            call_meta = call_kwargs['metadata']
            self.assertEqual(call_meta.get("tag"), "test")
            self.assertEqual(call_meta.get("agent_id"), self.agent_id)

            recalled_value = self.run_async(self.agent._recall(key))
            self.assertEqual(recalled_value, "Mock Recalled Value")
            self.mock_memory_instance.retrieve.assert_awaited_once_with(key=key)

            query = "search query"
            search_results = self.run_async(self.agent._search_memory(query, top_k=5))
            self.assertEqual(len(search_results), 1)
            self.mock_memory_instance.search.assert_awaited_once_with(query=query, top_k=5, filter_metadata=None)
            print("Helper memory operations test passed.")

        def test_run_method_calls_helpers(self):
            """Test that the concrete run method correctly uses helpers."""
            task = "Test the concrete agent"
            # Set specific recall value for this test
            # self.mock_memory_instance.retrieve.return_value = task # Not needed for this run impl

            expected_final_result = f"Ran task: {task}. LLM says: Mock LLM Ack"
            result = self.run_async(self.agent.run(task))

            self.assertEqual(result, expected_final_result)
            # Verify helpers were called by run implementation
            self.mock_memory_instance.store.assert_awaited_once_with(key="last_task_run", value=task, metadata={'agent_id': self.agent_id})
            self.mock_router_instance.generate.assert_awaited_once()
            # Ensure skill wasn't called by this simple run implementation
            self.mock_execute_skill_instance.assert_not_awaited()
            print("Concrete run method helper usage test passed.")


    # Run the tests
    print("\nRunning BaseAgent tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestBaseAgent))
    runner = unittest.TextTestRunner()
    runner.run(suite)

except ImportError as e:
    print(f"Failed to import components: {e}")
    print("Ensure agent/base_agent.py, ModelRouter, BaseMemory, skills exist.")
except Exception as e:
    print(f"An error occurred during test setup: {e}")
# Test Snippet File: backend/agents/design_agent_test.py
# Description: Verifies the DesignAgent functionality using mocked components.
# Command: python -m backend.agents.design_agent_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call # Import call
from typing import Dict, Any, List, Optional # Import necessary types

# Adjust path to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.agents.design_agent import DesignAgent
    from backend.models.model_router import ModelRouter # For mocking
    from backend.memory.base_memory import BaseMemory   # For mocking
    from backend.skills import SkillError, execute_skill as execute_skill_func # For mocking
    print("Imported DesignAgent components successfully.")

    # Mock search results for inspiration
    MOCK_INSPIRATION_RESULTS = [
        {"title": "Cool Design Site", "url": "http://cool.design", "snippet": "Example layouts."},
    ]

    class TestDesignAgent(unittest.TestCase):

        def setUp(self):
            """Set up fresh mocks for each test."""
            self.mock_router_instance = MagicMock(spec=ModelRouter)
            self.mock_memory_instance = MagicMock(spec=BaseMemory)
            self.mock_execute_skill = AsyncMock() # Mock the standalone execute_skill function

            # Configure async methods on mocks
            self.mock_router_instance.generate = AsyncMock(return_value="Mock Design Output") # LLM response
            self.mock_memory_instance.store = AsyncMock(return_value=True)
            # Configure skill mock side effect for search
            async def skill_side_effect(skill_name, *args, **kwargs):
                if skill_name == "web.search":
                    return MOCK_INSPIRATION_RESULTS
                else: return f"Mock result for {skill_name}"
            self.mock_execute_skill.side_effect = skill_side_effect

            # Create agent instance
            self.agent_id = "test_design_agent_01"
            self.agent = DesignAgent(
                agent_id=self.agent_id,
                model_router=self.mock_router_instance,
                agent_memory=self.mock_memory_instance,
                execute_skill_func=self.mock_execute_skill
            )
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def assertStoreCalledWith(self, key_prefix: str, status: str, check_value_dict: Optional[Dict] = None):
             """Helper assertion to check memory store calls via kwargs."""
             self.mock_memory_instance.store.assert_awaited()
             found = False
             for store_call in self.mock_memory_instance.store.await_args_list:
                 if 'key' in store_call.kwargs and store_call.kwargs['key'].startswith(key_prefix):
                     self.assertEqual(store_call.kwargs['metadata'].get('status'), status)
                     if check_value_dict is not None:
                          stored_value = store_call.kwargs.get('value')
                          self.assertIsInstance(stored_value, dict)
                          for k, v in check_value_dict.items():
                               self.assertIn(k, stored_value)
                               self.assertEqual(stored_value[k], v)
                     found = True
                     break
             self.assertTrue(found, f"Store call starting with key '{key_prefix}' not found in calls: {self.mock_memory_instance.store.await_args_list}")


        # --- Tests ---
        def test_run_simple_design_task(self):
            """Test a simple design task relying only on the LLM."""
            task = "Design a logo concept for a coffee shop named 'The Grind'"
            expected_output = "Concept: A stylized coffee bean morphing into a gear..."
            self.mock_router_instance.generate.return_value = expected_output

            result = self.run_async(self.agent.run(task_description=task))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['task'], task)
            self.assertEqual(result['design_output'], expected_output)

            # Verify only LLM was called (no skill)
            self.mock_router_instance.generate.assert_awaited_once()
            self.mock_execute_skill.assert_not_awaited()
            # Verify memory store
            self.assertStoreCalledWith(key_prefix='design_', status='success', check_value_dict=result)
            print("Simple design task test passed.")

        def test_run_design_with_context_and_format(self):
            """Test design task with context and target format."""
            task = "Refine the user profile screen based on feedback."
            context = "Feedback: Users find the settings hard to find."
            target_format = "markdown list"
            expected_output = "- Move settings icon to top right.\n- Add labels to icons."
            self.mock_router_instance.generate.return_value = expected_output

            result = self.run_async(self.agent.run(
                task_description=task,
                context=context,
                target_format=target_format
            ))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['design_output'], expected_output)
            # Update assertion to check correct number of LLM calls
            self.assertEqual(self.mock_router_instance.generate.await_count, 1)
            call_args = self.mock_router_instance.generate.await_args
            # Check prompt includes context and format instruction
            self.assertIn(context, call_args.kwargs['prompt'])
            self.assertIn(f"in {target_format} format", call_args.kwargs['prompt'])
            print("Design with context and format test passed.")

        def test_run_design_with_inspiration_search(self):
            """Test design task including web search for inspiration."""
            task = "Suggest UI layouts for a travel planning app"
            expected_llm_output = "Layout idea: A map-centric view with card overlays..."
            self.mock_router_instance.generate.return_value = expected_llm_output

            result = self.run_async(self.agent.run(
                task_description=task,
                search_inspiration=True # Override default config
            ))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['design_output'], expected_llm_output)

            # Verify web search skill was called
            self.mock_execute_skill.assert_awaited_once()
            skill_call_args = self.mock_execute_skill.await_args
            self.assertEqual(skill_call_args.args[0], "web.search")
            self.assertTrue(skill_call_args.kwargs['query'].startswith("design inspiration for"))

            # Verify LLM was called once
            self.assertEqual(self.mock_router_instance.generate.await_count, 1)
            llm_call_args = self.mock_router_instance.generate.await_args
            # Check prompt includes inspiration section
            self.assertIn("INSPIRATION FROM WEB SEARCH:", llm_call_args.kwargs['prompt'])
            self.assertIn("Cool Design Site", llm_call_args.kwargs['prompt']) # From mock result

            self.assertStoreCalledWith(key_prefix='design_', status='success', check_value_dict=result)
            print("Design with inspiration search test passed.")

        def test_run_llm_failure(self):
            """Test handling when the LLM call fails."""
            task = "Generate impossible design"
            self.mock_router_instance.generate.side_effect = SkillError("LLM design generation failed")

            with self.assertRaises(SkillError) as cm:
                 self.run_async(self.agent.run(task_description=task))

            # Check the error is properly propagated
            self.assertEqual(str(cm.exception), "LLM design generation failed")
            self.mock_router_instance.generate.assert_awaited_once() # LLM was called
            # Verify error stored
            self.assertStoreCalledWith(key_prefix='error_design_', status='error')
            print("LLM failure handling test passed.")

        def test_run_search_skill_failure_proceeds(self):
             """Test that design proceeds even if inspiration search fails."""
             task = "Design something despite search failure"
             expected_llm_output = "Design generated without inspiration."
             # Make search skill fail, but LLM succeed
             self.mock_execute_skill.side_effect = SkillError("Search API down")
             self.mock_router_instance.generate.return_value = expected_llm_output

             result = self.run_async(self.agent.run(task_description=task, search_inspiration=True))

             # Should still succeed overall
             self.assertEqual(result['status'], 'success')
             self.assertEqual(result['design_output'], expected_llm_output)
             # Verify search was called (and failed internally)
             self.mock_execute_skill.assert_awaited_once()
             # Verify LLM was called exactly once
             self.assertEqual(self.mock_router_instance.generate.await_count, 1)
             llm_call_args = self.mock_router_instance.generate.await_args
             # Check prompt DOES NOT include inspiration section
             self.assertNotIn("INSPIRATION FROM WEB SEARCH:", llm_call_args.kwargs['prompt'])
             print("Design proceeds after search failure test passed.")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning DesignAgent tests...")
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure agent/design_agent.py and its dependencies exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
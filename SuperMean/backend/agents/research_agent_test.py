# Test Snippet File: backend/agents/research_agent_test.py
# Description: Verifies the ResearchAgent functionality using mocked components.
# Command: python -m backend.agents.research_agent_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call # Import call
from typing import Dict, Any, List, Optional

# Adjust path to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.agents.research_agent import ResearchAgent
    from backend.models.model_router import ModelRouter # For mocking
    from backend.memory.base_memory import BaseMemory   # For mocking
    from backend.skills import SkillError, execute_skill as execute_skill_func # For mocking
    print("Imported ResearchAgent components successfully.")

    # Mock search results
    MOCK_SEARCH_RESULTS = [
        {"title": "Result A", "url": "http://a.com", "snippet": "Info about A.", "position": 1},
        {"title": "Result B", "url": "http://b.com", "snippet": "Info about B.", "position": 2},
    ]
    MOCK_SUMMARY = "A and B are related topics."

    class TestResearchAgent(unittest.TestCase):

        def setUp(self):
            """Set up fresh mocks for each test."""
            self.mock_router_instance = MagicMock(spec=ModelRouter)
            self.mock_memory_instance = MagicMock(spec=BaseMemory)
            self.mock_execute_skill = AsyncMock() # Mock the standalone execute_skill function

            # Configure async methods on mocks
            self.mock_memory_instance.store = AsyncMock(return_value=True)
            # Configure skill mock side effects based on skill name called
            async def skill_side_effect(skill_name, *args, **kwargs):
                if skill_name == "web.search":
                    return MOCK_SEARCH_RESULTS
                elif skill_name == "text.summarize":
                    return MOCK_SUMMARY
                else:
                    return f"Mock result for {skill_name}"
            self.mock_execute_skill.side_effect = skill_side_effect

            # Create agent instance
            self.agent_id = "test_research_agent_01"
            self.agent = ResearchAgent(
                agent_id=self.agent_id,
                model_router=self.mock_router_instance,
                agent_memory=self.mock_memory_instance,
                execute_skill_func=self.mock_execute_skill,
                config={'max_summary_sources': 2} # Limit sources for test
            )
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def assertStoreCalledWith(self, key_prefix: str, status: str, check_value_dict: Optional[Dict] = None):
             """Helper assertion to check memory store calls via kwargs."""
             self.mock_memory_instance.store.assert_awaited()
             found = False
             relevant_call = None
             for store_call in self.mock_memory_instance.store.await_args_list:
                 if 'key' in store_call.kwargs and store_call.kwargs['key'].startswith(key_prefix):
                     relevant_call = store_call
                     self.assertEqual(store_call.kwargs['metadata']['status'], status)
                     if check_value_dict is not None:
                          stored_value = store_call.kwargs['value']
                          self.assertIsInstance(stored_value, dict)
                          for k, v in check_value_dict.items():
                               self.assertIn(k, stored_value)
                               self.assertEqual(stored_value[k], v)
                     found = True
                     break
             self.assertTrue(found, f"Store call starting with key '{key_prefix}' not found in calls: {self.mock_memory_instance.store.await_args_list}")
             return relevant_call

        # --- Tests ---
        def test_run_search_and_summarize(self):
            """Test the default workflow: search and summarize."""
            query = "What are LLMs?"
            num_results = 5 # Agent default

            result = self.run_async(self.agent.run(query=query))

            # Assertions
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['query'], query)
            self.assertEqual(result['search_results'], MOCK_SEARCH_RESULTS)
            self.assertEqual(result['summary'], MOCK_SUMMARY)

            # Verify skill calls
            expected_calls = [
                # Call for web.search
                call('web.search', query=query, num_results=num_results),
                # Call for text.summarize (implicitly passes model_router)
                call('text.summarize', text=unittest.mock.ANY, summary_length='detailed paragraph', target_model='gemini', model_router=self.mock_router_instance)
            ]
            self.mock_execute_skill.assert_has_awaits(expected_calls, any_order=False)
            # Check the text passed to summarizer
            summarizer_call = self.mock_execute_skill.await_args_list[1]
            text_arg = summarizer_call.kwargs['text']
            self.assertIn("Source 1 (http://a.com)", text_arg)
            self.assertIn("Info about A.", text_arg)
            self.assertIn("Source 2 (http://b.com)", text_arg)
            self.assertIn("Info about B.", text_arg)

            # Verify memory calls (search results, summary, final result)
            self.assertEqual(self.mock_memory_instance.store.await_count, 3)
            self.assertStoreCalledWith(key_prefix=f'research_{query[:30]}', status='success', check_value_dict=result)
            print("Search and summarize test passed.")


        def test_run_search_only(self):
            """Test workflow with summarization disabled."""
            query = "Python benefits"
            num_results = 3

            result = self.run_async(self.agent.run(query=query, num_results=num_results, summarize=False))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['query'], query)
            self.assertEqual(result['search_results'], MOCK_SEARCH_RESULTS)
            self.assertNotIn('summary', result) # Summary should not be present

            # Verify only web.search skill was called
            self.mock_execute_skill.assert_awaited_once_with('web.search', query=query, num_results=num_results)

            # Verify memory calls (search results, final result)
            self.assertEqual(self.mock_memory_instance.store.await_count, 2)
            self.assertStoreCalledWith(key_prefix=f'research_{query[:30]}', status='success', check_value_dict=result)
            print("Search only test passed.")

        def test_run_search_fails(self):
            """Test handling when the web.search skill fails."""
            query = "Failing search"
            error_message = "SerpApi key invalid"
            self.mock_execute_skill.side_effect = SkillError(error_message) # Simulate search failure

            with self.assertRaises(SkillError) as cm:
                self.run_async(self.agent.run(query=query))

            self.assertIn(error_message, str(cm.exception))
            # Verify search skill was called, summarizer was not
            self.mock_execute_skill.assert_awaited_once_with('web.search', query=query, num_results=self.agent.config['default_search_results'])
            # Verify error was stored
            self.assertStoreCalledWith(key_prefix=f'error_research_{query[:30]}', status='error', check_value_dict={'error': f"Skill Error: {error_message}"})
            print("Search failure test passed.")

        def test_run_summarize_fails(self):
            """Test handling when the text.summarize skill fails."""
            query = "Summarization fail test"
            summarize_error = "LLM for summary unavailable"
            # Make search succeed, but summarize fail
            async def skill_side_effect(skill_name, *args, **kwargs):
                if skill_name == "web.search":
                    return MOCK_SEARCH_RESULTS
                elif skill_name == "text.summarize":
                    raise SkillError(summarize_error)
                else:
                    return f"Mock result for {skill_name}"
            self.mock_execute_skill.side_effect = skill_side_effect

            with self.assertRaises(SkillError) as cm:
                self.run_async(self.agent.run(query=query))

            self.assertIn(summarize_error, str(cm.exception))
            # Verify both skills were attempted
            self.assertEqual(self.mock_execute_skill.await_count, 2)
            # Verify error was stored
            self.assertStoreCalledWith(key_prefix=f'error_research_{query[:30]}', status='error', check_value_dict={'error': f"Skill Error: {summarize_error}"})
            print("Summarization failure test passed.")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning ResearchAgent tests...")
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure agent/research_agent.py and its dependencies exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
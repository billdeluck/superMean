# Test Snippet File: backend/agents/medical_agent_test.py
# Description: Verifies the MedicalAgent functionality using mocked components.
# Command: python -m backend.agents.medical_agent_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call # Import call
from typing import Dict, Any, List, Optional # Import necessary types

# Adjust path to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.agents.medical_agent import MedicalAgent
    from backend.models.model_router import ModelRouter # For mocking
    from backend.memory.base_memory import BaseMemory   # For mocking
    from backend.skills import SkillError, execute_skill as execute_skill_func # For mocking
    print("Imported MedicalAgent components successfully.")

    # Mock search results
    MOCK_MEDICAL_SEARCH = [
        {"title": "PubMed Study", "url": "http://pubmed.gov/123", "snippet": "Study found correlation..."},
        {"title": "Mayo Clinic Info", "url": "http://mayo.clinic/abc", "snippet": "General info on condition..."},
    ]
    MOCK_SUMMARY = "Studies show correlation, general info available."
    MOCK_LLM_RESPONSE = "Based on the summarized findings, the condition involves X and Y."

    class TestMedicalAgent(unittest.TestCase):

        def setUp(self):
            """Set up fresh mocks for each test."""
            self.mock_router_instance = MagicMock(spec=ModelRouter)
            self.mock_memory_instance = MagicMock(spec=BaseMemory)
            self.mock_execute_skill = AsyncMock() # Mock the standalone execute_skill function

            # Configure async methods on mocks
            self.mock_router_instance.generate = AsyncMock(return_value=MOCK_LLM_RESPONSE)
            self.mock_memory_instance.store = AsyncMock(return_value=True)
            # Configure skill mock side effects
            async def skill_side_effect(skill_name, *args, **kwargs):
                if skill_name == "web.search":
                    return MOCK_MEDICAL_SEARCH
                elif skill_name == "text.summarize":
                    return MOCK_SUMMARY
                else: return f"Mock result for {skill_name}"
            self.mock_execute_skill.side_effect = skill_side_effect

            # Create agent instance
            self.agent_id = "test_medical_agent_01"
            self.agent = MedicalAgent(
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
                              # Don't assert exact error message string match
                              if k != 'error' and k != 'response':
                                 self.assertIn(k, stored_value)
                                 self.assertEqual(stored_value[k], v)
                          # Check if error/response key exists if expected
                          if 'error' in check_value_dict: self.assertIn('error', stored_value)
                          if 'response' in check_value_dict: self.assertIn('response', stored_value)
                     found = True
                     break
             self.assertTrue(found, f"Store call starting with key '{key_prefix}' not found in calls: {self.mock_memory_instance.store.await_args_list}")


        # --- Tests ---
        def test_run_search_summarize_synthesize(self):
            """Test the default workflow: search, summarize, synthesize, add disclaimer."""
            query = "Information on tinnitus"
            num_results = 3 # Agent default

            result = self.run_async(self.agent.run(query=query))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['query'], query)
            self.assertTrue(result['response'].startswith(MOCK_LLM_RESPONSE))
            self.assertTrue(result['response'].endswith(self.agent.DISCLAIMER))
            self.assertEqual(result['disclaimer'], self.agent.DISCLAIMER)
            self.assertIn('search_results', result) # Check search results are stored if needed

            # Verify skill calls: search -> summarize -> llm
            self.assertEqual(self.mock_execute_skill.await_count, 2) # Search + Summarize
            expected_skill_calls = [
                call('web.search', query=unittest.mock.ANY, num_results=num_results), # Check query includes filter later
                call('text.summarize', text=unittest.mock.ANY, summary_length='concise paragraph', target_model='gemini', model_router=self.mock_router_instance)
            ]
            self.mock_execute_skill.assert_has_awaits(expected_skill_calls, any_order=False)
            # Check search query contains filter
            search_call_args, search_call_kwargs = self.mock_execute_skill.await_args_list[0]
            self.assertTrue(self.agent.config['search_filter'] in search_call_kwargs['query'])

            # Verify LLM call for synthesis
            self.mock_router_instance.generate.assert_awaited_once()
            llm_call_args, llm_call_kwargs = self.mock_router_instance.generate.await_args
            self.assertTrue(llm_call_kwargs['prompt'].startswith(f"Regarding the query '{query}'"))
            self.assertIn("SUMMARY OF FINDINGS FROM WEB SEARCH", llm_call_kwargs['prompt'])
            self.assertIn(MOCK_SUMMARY, llm_call_kwargs['prompt'])

            # Verify memory store
            self.assertStoreCalledWith(key_prefix=f'medical_info_{self.agent_id}_{query[:30]}', status='success', check_value_dict=result)
            print("Medical search, summarize, synthesize test passed.")

        def test_run_no_search(self):
            """Test workflow with search disabled."""
            query = "Causes of headache"
            expected_llm_resp = "Headaches can be caused by various factors."
            self.mock_router_instance.generate.return_value = expected_llm_resp

            result = self.run_async(self.agent.run(query=query, search=False))

            self.assertEqual(result['status'], 'success')
            self.assertNotIn('search_results', result)
            self.assertTrue(result['response'].startswith(expected_llm_resp))
            self.assertTrue(result['response'].endswith(self.agent.DISCLAIMER))

            # Verify no skill calls made
            self.mock_execute_skill.assert_not_awaited()
            # Verify LLM was called directly
            self.mock_router_instance.generate.assert_awaited_once()
            llm_call_args, llm_call_kwargs = self.mock_router_instance.generate.await_args
            self.assertIn("No external web context was available", llm_call_kwargs['prompt'])

            self.assertStoreCalledWith(key_prefix=f'medical_info_{self.agent_id}_{query[:30]}', status='success', check_value_dict=result)
            print("Medical no search test passed.")

        def test_run_search_fails_proceeds_with_disclaimer(self):
            """Test that LLM synthesis still happens with disclaimer if search fails."""
            query = "Treatment for insomnia"
            expected_llm_resp = "General information about insomnia includes lifestyle changes..."
            # Make search fail, LLM succeed
            self.mock_execute_skill.side_effect = SkillError("Search timed out")
            self.mock_router_instance.generate.return_value = expected_llm_resp

            result = self.run_async(self.agent.run(query=query)) # Search is true by default

            self.assertEqual(result['status'], 'success')
            self.assertTrue(result['response'].startswith(expected_llm_resp))
            self.assertTrue(result['response'].endswith(self.agent.DISCLAIMER))
            self.assertNotIn('search_results', result) # Search results should not be in final dict

            # Verify search skill was called (and failed)
            self.mock_execute_skill.assert_awaited_once()
            # Verify LLM was called
            self.mock_router_instance.generate.assert_awaited_once()
            llm_call_args, llm_call_kwargs = self.mock_router_instance.generate.await_args
            # Check prompt indicates search failure
            self.assertIn("Web search for external context failed", llm_call_kwargs['prompt'])

            self.assertStoreCalledWith(key_prefix=f'medical_info_{self.agent_id}_{query[:30]}', status='success', check_value_dict=result)
            print("Medical search failure proceeds test passed.")

        def test_run_llm_synthesis_fails(self):
            """Test handling when the final LLM synthesis call fails."""
            query = "Risks of procedure X"
            llm_error_msg = "LLM unavailable for synthesis"
            # Make search/summary succeed, but LLM fail
            async def skill_side_effect(skill_name, *args, **kwargs):
                 if skill_name == "web.search": return MOCK_MEDICAL_SEARCH
                 elif skill_name == "text.summarize": return MOCK_SUMMARY
                 else: return "Unexpected skill call"
            self.mock_execute_skill.side_effect = skill_side_effect
            self.mock_router_instance.generate.side_effect = SkillError(llm_error_msg)

            with self.assertRaises(SkillError) as cm:
                 self.run_async(self.agent.run(query=query))

            # Check the final raised error
            self.assertTrue(str(cm.exception).startswith("MedicalAgent unexpected error:"))
            self.assertIn(llm_error_msg, str(cm.exception.__cause__))

            # Verify search and summarize skills were called
            self.assertEqual(self.mock_execute_skill.await_count, 2)
            # Verify LLM was called
            self.mock_router_instance.generate.assert_awaited_once()
             # Verify error stored before exception was raised
            self.assertStoreCalledWith(key_prefix=f'error_medical_{query[:30]}', status='error', check_value_dict={'error': True})
            print("Medical LLM synthesis failure test passed.")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning MedicalAgent tests...")
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure agent/medical_agent.py and its dependencies exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
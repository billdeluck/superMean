# Test Snippet File: backend/super_agent/planner_test.py
# Description: Verifies the Planner's ability to create plans. (Corrected Assertions)
# Command: python -m backend.super_agent.planner_test

import sys
import os
import unittest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, call, ANY # Import call and ANY

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.super_agent.planner import Planner, PlanningError, ModelConnectionError
    from backend.models.model_router import ModelRouter # For mocking
    from backend.memory.base_memory import BaseMemory   # Optional: For mocking memory
    from backend.utils.config_loader import Settings # Import Settings for type hinting
    print("Imported Planner components successfully.")

    # --- Mock LLM Responses ---
    MOCK_PLAN_JSON_VALID = json.dumps([
        {"step_id": 1, "action_description": "Research topic A", "required_inputs": ["Goal"], "expected_output": "Research summary A", "suggested_executor": "ResearchAgent"},
        {"step_id": 2, "action_description": "Write code for feature B based on A", "required_inputs": ["Research summary A"], "expected_output": "Code for B", "suggested_executor": "DevAgent"},
        {"step_id": 3, "action_description": "Summarize code B", "required_inputs": ["Code for B"], "expected_output": "Code summary B", "suggested_executor": "text.summarize"}
    ])
    MOCK_PLAN_LIST_VALID = json.loads(MOCK_PLAN_JSON_VALID) # Parsed version
    MOCK_PLAN_JSON_INVALID_FORMAT = "{'step': 1, 'action': 'do stuff'}" # Not JSON list
    MOCK_PLAN_JSON_MISSING_KEYS = json.dumps([{"step_id": 1, "action_description": "Incomplete"}])


    class TestPlanner(unittest.TestCase):

        def setUp(self):
            self.mock_router_instance = MagicMock(spec=ModelRouter)
            self.mock_memory_instance = MagicMock(spec=BaseMemory)
            # Configure generate as AsyncMock
            self.mock_router_instance.generate = AsyncMock()
            self.mock_memory_instance.store = AsyncMock(return_value=True) # Mock memory store

            # Instantiate the Planner with mocks
            # Pass a dummy Settings object if needed by Planner init
            mock_settings = MagicMock(spec=Settings)
            mock_settings.MODEL_FALLBACK_CHAIN = "gemini,deepseek" # Example needed for init

            self.planner = Planner(
                model_router=self.mock_router_instance,
                memory=self.mock_memory_instance,
                # Pass mock settings if Planner expects it, otherwise None is fine if handled internally
                # config=None # Assuming Planner's config is optional or handled differently
            )
            # Override settings after init if needed for specific tests
            # self.planner.settings = mock_settings

            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_create_plan_success(self):
            """Test successful plan creation and parsing."""
            goal = "Develop feature X"
            # Configure LLM mock to return valid JSON
            self.mock_router_instance.generate.return_value = MOCK_PLAN_JSON_VALID

            plan = self.run_async(self.planner.create_plan(goal))

            # Assertions on plan content
            self.assertIsInstance(plan, list)
            self.assertEqual(len(plan), 3)
            self.assertEqual(plan[0]['step_id'], 1)
            self.assertEqual(plan[1]['suggested_executor'], 'DevAgent')
            self.assertEqual(plan[2]['required_inputs'], ['Code for B'])

            # Verify LLM was called correctly
            self.mock_router_instance.generate.assert_awaited_once()
            llm_call_args, llm_call_kwargs = self.mock_router_instance.generate.await_args
            self.assertTrue(llm_call_kwargs['prompt'].startswith(Planner.DEFAULT_SYSTEM_PROMPT))
            self.assertIn(f"Goal: {goal}", llm_call_kwargs['prompt'])

            # --- CORRECTED MEMORY ASSERTION ---
            # Verify plan was stored in memory using assert_awaited_once_with
            expected_store_key = f"plan_{goal[:50]}"
            expected_metadata = {"goal": goal}
            self.mock_memory_instance.store.assert_awaited_once_with(
                key=expected_store_key,
                value=MOCK_PLAN_LIST_VALID, # Check against the parsed list
                metadata=expected_metadata
            )
            # --- END CORRECTION ---
            print("Successful plan creation test passed.")

        def test_create_plan_with_context(self):
            """Test plan creation including context."""
            goal = "Update feature Y"
            context = "Current version is v1. Needs update for v2 spec."
            self.mock_router_instance.generate.return_value = MOCK_PLAN_JSON_VALID # Use same valid plan

            plan = self.run_async(self.planner.create_plan(goal, context=context))

            self.assertEqual(len(plan), 3) # Plan parsed correctly
            self.mock_router_instance.generate.assert_awaited_once()
            llm_call_args, llm_call_kwargs = self.mock_router_instance.generate.await_args
            # Verify context is included in the prompt to the LLM
            self.assertIn(f"Goal: {goal}", llm_call_kwargs['prompt'])
            self.assertIn(f"Context: {context}", llm_call_kwargs['prompt'])
            print("Plan creation with context test passed.")

        def test_create_plan_llm_failure(self):
            """Test handling when the LLM call fails."""
            goal = "Plan a failure"
            # Configure LLM mock to raise an error consistent with how it's wrapped
            error_cause = ModelConnectionError("LLM", "Timeout")
            self.mock_router_instance.generate.side_effect = error_cause

            with self.assertRaises(PlanningError) as cm:
                 self.run_async(self.planner.create_plan(goal))

            # Check the final PlanningError message and its cause
            self.assertTrue(str(cm.exception).startswith("LLM interaction failed during planning:"))
            self.assertIs(cm.exception.__cause__, error_cause) # Check original exception is preserved
            self.mock_router_instance.generate.assert_awaited_once() # LLM was called
            self.mock_memory_instance.store.assert_not_awaited() # Plan should not be stored
            print(f"Caught expected PlanningError on LLM failure: {cm.exception}")

        def test_create_plan_bad_json_format(self):
            """Test handling when the LLM returns non-JSON list format."""
            goal = "Plan with bad format"
            self.mock_router_instance.generate.return_value = MOCK_PLAN_JSON_INVALID_FORMAT

            with self.assertRaises(PlanningError) as cm:
                 self.run_async(self.planner.create_plan(goal))

            # Check the specific error message related to JSON parsing
            self.assertTrue(str(cm.exception).startswith("Failed to parse plan JSON from LLM:"))
            self.assertIsInstance(cm.exception.__cause__, json.JSONDecodeError)
            self.mock_router_instance.generate.assert_awaited_once()
            self.mock_memory_instance.store.assert_not_awaited()
            print(f"Caught expected PlanningError on bad JSON format: {cm.exception}")

        def test_create_plan_missing_keys(self):
            """Test handling when the LLM returns JSON with missing keys."""
            goal = "Plan with missing keys"
            self.mock_router_instance.generate.return_value = MOCK_PLAN_JSON_MISSING_KEYS

            with self.assertRaises(PlanningError) as cm:
                 self.run_async(self.planner.create_plan(goal))

            # Check the specific error message related to validation
            self.assertTrue(str(cm.exception).startswith("Invalid plan structure from LLM:"))
            self.assertIsInstance(cm.exception.__cause__, ValueError) # Underlying validation error
            self.mock_router_instance.generate.assert_awaited_once()
            self.mock_memory_instance.store.assert_not_awaited()
            print(f"Caught expected PlanningError on missing keys: {cm.exception}")

        def test_create_plan_with_markdown_fences(self):
            """Test successful parsing when LLM includes markdown fences."""
            goal = "Plan with fences"
            fenced_json = f"```json\n{MOCK_PLAN_JSON_VALID}\n```"
            self.mock_router_instance.generate.return_value = fenced_json

            plan = self.run_async(self.planner.create_plan(goal))

            self.assertEqual(len(plan), 3) # Parsing succeeded
            self.assertEqual(plan[0]['step_id'], 1)
            self.mock_router_instance.generate.assert_awaited_once()
            # --- CORRECTED MEMORY ASSERTION ---
            self.mock_memory_instance.store.assert_awaited_once_with(
                 key=f"plan_{goal[:50]}",
                 value=MOCK_PLAN_LIST_VALID,
                 metadata={"goal": goal}
            )
            # --- END CORRECTION ---
            print("Plan parsing with markdown fences test passed.")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning Planner tests...")
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure super_agent/planner.py and its dependencies (ModelRouter, etc.) exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
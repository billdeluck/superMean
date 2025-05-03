# Test Snippet File: backend/super_agent/meta_planner_test.py
# Description: Verifies the MetaPlanner's reflection and adaptation logic using mocks.
# Command: python -m backend.super_agent.meta_planner_test

import sys
import os
import unittest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.super_agent.meta_planner import MetaPlanner, MetaPlanningError
    from backend.super_agent.planner import Planner # For mocking
    from backend.super_agent.evaluator import Evaluator # For mocking
    from backend.super_agent.tool_creator import ToolCreator # For mocking
    from backend.models.model_router import ModelRouter # For mocking
    print("Imported MetaPlanner components successfully.")

    # --- Mock Data ---
    MOCK_GOAL = "Build a weather dashboard"
    MOCK_PLAN = [{"step_id": 1, "action_description": "Fetch weather data", "suggested_executor": "api.fetch_weather"}]
    MOCK_EXEC_RESULT_SUCCESS = {"status": "success", "step_outputs": {1: {"temp_c": 20}}}
    MOCK_EXEC_RESULT_FAIL = {"status": "failed", "step_id": 1, "error": "API key invalid", "step_outputs": {}}
    MOCK_EVAL_SUCCESS = {"overall_success": True, "score": 0.9, "reasoning": "Looks good", "suggestions": []}
    MOCK_EVAL_NEEDS_TOOL = {"overall_success": False, "score": 0.3, "reasoning": "Cannot display data, needs UI skill", "suggestions": ["Create a UI display tool"]}
    MOCK_EVAL_PLAN_FLAW = {"overall_success": False, "score": 0.2, "reasoning": "Plan missed crucial data formatting step", "suggestions": ["Revise plan to include formatting"]}

    MOCK_DECISION_SUCCESS = "Reasoning: Goal achieved.\nFINAL_SUCCESS"
    MOCK_DECISION_REVISE = "Reasoning: Plan is bad.\nREVISE_PLAN"
    MOCK_DECISION_RETRY = "Reasoning: Transient API error.\n{\"retry_step_id\": 1}"
    MOCK_DECISION_CREATE_TOOL = 'Reasoning: Need a way to display UI.\n{"skill_name": "ui.display_data", "description": "Displays data in UI", "args": ["data"], "returns": "None"}'
    MOCK_DECISION_FAILURE = "Reasoning: Tried 3 times, still failing.\nFINAL_FAILURE"
    MOCK_DECISION_BAD_FORMAT = "This is not a valid decision."


    class TestMetaPlanner(unittest.TestCase):

        def setUp(self):
            self.mock_planner = MagicMock(spec=Planner)
            self.mock_evaluator = MagicMock(spec=Evaluator)
            self.mock_tool_creator = MagicMock(spec=ToolCreator)
            self.mock_model_router = MagicMock(spec=ModelRouter)
            # Configure generate as AsyncMock
            self.mock_model_router.generate = AsyncMock()

            self.meta_planner = MetaPlanner(
                planner=self.mock_planner,
                evaluator=self.mock_evaluator,
                tool_creator=self.mock_tool_creator,
                model_router=self.mock_model_router
            )
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_reflect_eval_success(self):
            """Test reflection when evaluation indicates success."""
            # No LLM call should be needed if evaluation passed
            decision, data = self.run_async(self.meta_planner.reflect_and_adapt(
                goal=MOCK_GOAL, plan=MOCK_PLAN, execution_result=MOCK_EXEC_RESULT_SUCCESS, evaluation=MOCK_EVAL_SUCCESS
            ))
            self.assertEqual(decision, "FINAL_SUCCESS")
            self.assertIsNone(data)
            self.mock_model_router.generate.assert_not_awaited()
            print("Reflection on eval success passed.")

        def test_reflect_exec_success_no_eval(self):
            """Test reflection when execution succeeded but no evaluation provided."""
            # Defaults to success without evaluation
            decision, data = self.run_async(self.meta_planner.reflect_and_adapt(
                goal=MOCK_GOAL, plan=MOCK_PLAN, execution_result=MOCK_EXEC_RESULT_SUCCESS, evaluation=None
            ))
            self.assertEqual(decision, "FINAL_SUCCESS")
            self.assertIsNone(data)
            self.mock_model_router.generate.assert_not_awaited()
            print("Reflection on exec success (no eval) passed.")

        def test_reflect_exec_failure(self):
            """Test reflection when execution failed."""
            self.mock_model_router.generate.return_value = MOCK_DECISION_RETRY # LLM suggests retry

            decision, data = self.run_async(self.meta_planner.reflect_and_adapt(
                goal=MOCK_GOAL, plan=MOCK_PLAN, execution_result=MOCK_EXEC_RESULT_FAIL, evaluation=None
            ))

            self.assertEqual(decision, "RETRY_STEP")
            self.assertIsInstance(data, dict)
            self.assertEqual(data.get("retry_step_id"), 1)
            self.mock_model_router.generate.assert_awaited_once() # LLM called for reflection
            # Check prompt includes failure info
            call_args, call_kwargs = self.mock_model_router.generate.await_args
            self.assertIn("Execution Status: failed", call_kwargs['prompt'])
            self.assertIn("Error: API key invalid", call_kwargs['prompt'])
            print("Reflection on exec failure passed.")

        def test_reflect_eval_needs_tool(self):
            """Test reflection when evaluation suggests creating a tool."""
            self.mock_model_router.generate.return_value = MOCK_DECISION_CREATE_TOOL

            decision, data = self.run_async(self.meta_planner.reflect_and_adapt(
                goal=MOCK_GOAL, plan=MOCK_PLAN, execution_result=MOCK_EXEC_RESULT_SUCCESS, evaluation=MOCK_EVAL_NEEDS_TOOL
            ))

            self.assertEqual(decision, "CREATE_TOOL")
            self.assertIsInstance(data, dict)
            self.assertEqual(data.get("skill_name"), "ui.display_data")
            self.assertEqual(data.get("description"), "Displays data in UI")
            self.assertEqual(data.get("args"), ["data"])
            self.assertEqual(data.get("returns"), "None")
            self.mock_model_router.generate.assert_awaited_once()
            # Check prompt includes evaluation info
            call_args, call_kwargs = self.mock_model_router.generate.await_args
            self.assertIn(f"Evaluation Summary:\n{json.dumps(MOCK_EVAL_NEEDS_TOOL, indent=2)}", call_kwargs['prompt'])
            print("Reflection needing tool creation passed.")

        def test_reflect_eval_plan_flaw(self):
            """Test reflection when evaluation suggests revising the plan."""
            self.mock_model_router.generate.return_value = MOCK_DECISION_REVISE

            decision, data = self.run_async(self.meta_planner.reflect_and_adapt(
                goal=MOCK_GOAL, plan=MOCK_PLAN, execution_result=MOCK_EXEC_RESULT_SUCCESS, evaluation=MOCK_EVAL_PLAN_FLAW
            ))

            self.assertEqual(decision, "REVISE_PLAN")
            self.assertIsNone(data)
            self.mock_model_router.generate.assert_awaited_once()
            call_args, call_kwargs = self.mock_model_router.generate.await_args
            self.assertIn(f"Evaluation Summary:\n{json.dumps(MOCK_EVAL_PLAN_FLAW, indent=2)}", call_kwargs['prompt'])
            print("Reflection needing plan revision passed.")

        def test_reflect_llm_failure(self):
            """Test handling when the reflection LLM call fails."""
            self.mock_model_router.generate.side_effect = MetaPlanningError("LLM Reflection Failed")

            with self.assertRaises(MetaPlanningError) as cm:
                 self.run_async(self.meta_planner.reflect_and_adapt(
                     goal=MOCK_GOAL, plan=MOCK_PLAN, execution_result=MOCK_EXEC_RESULT_FAIL
                 ))
            self.assertIn("LLM interaction failed during meta-planning", str(cm.exception))
            self.mock_model_router.generate.assert_awaited_once()
            print(f"Caught expected MetaPlanningError on LLM failure: {cm.exception}")

        def test_reflect_bad_decision_format(self):
            """Test handling when the LLM returns an invalid decision format."""
            self.mock_model_router.generate.return_value = MOCK_DECISION_BAD_FORMAT

            # Expect it to default to REVISE_PLAN
            decision, data = self.run_async(self.meta_planner.reflect_and_adapt(
                 goal=MOCK_GOAL, plan=MOCK_PLAN, execution_result=MOCK_EXEC_RESULT_FAIL
            ))
            self.assertEqual(decision, "REVISE_PLAN")
            self.assertIsNone(data)
            self.mock_model_router.generate.assert_awaited_once()
            print("Handling of bad decision format passed (defaulted to REVISE_PLAN).")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning MetaPlanner tests...")
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure super_agent/meta_planner.py and its dependencies exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
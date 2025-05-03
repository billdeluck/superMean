# Test Snippet File: backend/super_agent/builder_test.py
# Description: Verifies the Builder's ability to execute plans using mocked components. (Fixed Mock Config)
# Command: python -m backend.super_agent.builder_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call # Import call

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.super_agent.builder import Builder, BuildError
    from backend.agents.base_agent import BaseAgent # For mocking agents
    from backend.skills import SkillError, execute_skill as execute_skill_func # For mocking skill exec
    print("Imported BuilMeander components successfully.")

    # --- Mock Agents ---
    # Create mocks ONCE outside the class for efficiency if state isn't critical between tests
    # OR create fresh mocks in setUp if strict isolation is needed
    MockDevAgent = MagicMock(spec=BaseAgent)
    MockResearchAgent = MagicMock(spec=BaseAgent)
    mock_execute_skill = AsyncMock() # Global mock for the skill executor function

    # --- Test Plan ---
    TEST_PLAN = [
        {
            "step_id": 1,
            "action_description": "Research topic X",
            "required_inputs": ["goal_description"], # From initial context
            "expected_output": "research_summary",
            "suggested_executor": "ResearchAgent"
        },
        {
            "step_id": 2,
            "action_description": "Generate code based on research",
            "required_inputs": ["research_summary"], # Depends on step 1 output
            "expected_output": "generated_code",
            "suggested_executor": "DevAgent"
        },
        {
            "step_id": 3,
            "action_description": "Summarize the generated code",
            "required_inputs": ["generated_code"], # Depends on step 2 output
            "expected_output": "code_summary",
            "suggested_executor": "text.summarize" # Example using a skill
        }
    ]


    class TestBuilder(unittest.TestCase):

        def setUp(self):
            # Reset mocks before EACH test to ensure isolation
            MockDevAgent.reset_mock()
            MockResearchAgent.reset_mock()
            mock_execute_skill.reset_mock()
            # Reset side effects and return values specifically
            mock_execute_skill.side_effect = None
            mock_execute_skill.return_value = "Default Mock Skill Result" # Default success
            MockDevAgent.run = AsyncMock(return_value={"status": "success", "code": "default dev code"}) # Default success
            MockResearchAgent.run = AsyncMock(return_value={"status": "success", "summary": "default research summary"}) # Default success


            # Create a dictionary of mock agent instances
            self.mock_agents = {
                "DevAgent": MockDevAgent,
                "ResearchAgent": MockResearchAgent
            }
            # Instantiate the Builder
            self.builder = Builder(
                agents=self.mock_agents,
                execute_skill_func=mock_execute_skill
            )
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_execute_plan_success(self):
            """Test successful execution of a valid plan."""
            initial_context = {"goal_description": "Build feature Z"}
            # --- CONFIGURE MOCKS FOR *THIS* TEST ---
            research_output = {"status": "success", "research_summary": "Findings about Z"}
            dev_output = {"status": "success", "generated_code": "code_for_z = 1"}
            summary_output = "Summary of code_for_z"
            MockResearchAgent.run.return_value = research_output
            MockDevAgent.run.return_value = dev_output
            mock_execute_skill.return_value = summary_output # Explicitly set success value
            # --- END MOCK CONFIG ---

            result = self.run_async(self.builder.execute_plan(TEST_PLAN, initial_context))

            # Assertions on final result
            self.assertEqual(result["status"], "success")
            self.assertIn(1, result["step_outputs"])
            self.assertIn(2, result["step_outputs"])
            self.assertIn(3, result["step_outputs"])
            # Check the structure and content of stored outputs
            self.assertEqual(result["step_outputs"][1], research_output) # Step 1 output
            self.assertEqual(result["step_outputs"][2], dev_output) # Step 2 output
            self.assertEqual(result["step_outputs"][3], summary_output) # Step 3 output (skill result)
            self.assertEqual(result["final_result"], summary_output) # Final result is output of last step

            # Verify agent/skill calls
            MockResearchAgent.run.assert_awaited_once_with(
                task_description="Research topic X",
                goal_description="Build feature Z"
            )
            # --- CORRECTED INPUT PREPARATION CHECK ---
            # The builder prepares kwargs based on previous outputs. Check that happened.
            MockDevAgent.run.assert_awaited_once_with(
                task_description="Generate code based on research",
                # Input name 'research_summary' matches key in step 1 output dict
                research_summary="Findings about Z"
            )
            mock_execute_skill.assert_awaited_once_with(
                "text.summarize", # Skill name
                 # Input name 'generated_code' matches key in step 2 output dict
                generated_code="code_for_z = 1"
            )
            # --- END CORRECTION ---
            print("Successful plan execution test passed.")

        def test_execute_plan_agent_failure(self):
            """Test plan execution failure when an agent step fails."""
            initial_context = {"goal_description": "Build feature Z"}
            # Make step 1 (ResearchAgent) fail with an error message
            error_msg = "Research API down"
            MockResearchAgent.run.return_value = {"status": "error", "error": error_msg}

            result = self.run_async(self.builder.execute_plan(TEST_PLAN, initial_context))

            self.assertEqual(result["status"], "failed")
            # Check that step 1 is in the failed steps
            failed_step_ids = [step_id for step_id, _ in result["failed_steps"]]
            self.assertIn(1, failed_step_ids)
            # Find the error message for step 1
            step1_error = next(err for step_id, err in result["failed_steps"] if step_id == 1)
            self.assertIn(error_msg, step1_error)
            self.assertEqual(len(result["step_outputs"]), 0)

            # Allow for retries in agent call count
            self.assertGreater(MockResearchAgent.run.await_count, 0)
            MockDevAgent.run.assert_not_awaited()
            mock_execute_skill.assert_not_awaited()
            print("Agent failure handling test passed.")

        def test_execute_plan_skill_failure(self):
            """Test plan execution failure when a skill step fails."""
            initial_context = {"goal_description": "Build feature Z"}
            # Configure success for steps 1 & 2
            research_output = {"status": "success", "research_summary": "Findings about Z"}
            dev_output = {"status": "success", "generated_code": "code_for_z = 1"}
            MockResearchAgent.run.return_value = research_output
            MockDevAgent.run.return_value = dev_output
            # Configure skill to fail on each retry
            error_msg = "Summarizer model unavailable"
            mock_execute_skill.side_effect = SkillError(error_msg)

            result = self.run_async(self.builder.execute_plan(TEST_PLAN, initial_context))

            self.assertEqual(result["status"], "failed")
            # Check that step 3 is in the failed steps
            failed_step_ids = [step_id for step_id, _ in result["failed_steps"]]
            self.assertIn(3, failed_step_ids)
            # Find the error message for step 3
            step3_error = next(err for step_id, err in result["failed_steps"] if step_id == 3)
            self.assertIn(error_msg, step3_error)
            # Verify earlier steps completed
            self.assertIn(1, result["step_outputs"]) # Step 1 output should exist
            self.assertIn(2, result["step_outputs"]) # Step 2 output should exist
            self.assertEqual(result["step_outputs"][1], research_output)
            self.assertEqual(result["step_outputs"][2], dev_output)

            MockResearchAgent.run.assert_awaited_once()
            MockDevAgent.run.assert_awaited_once()
            # Allow for retries in skill call count
            self.assertGreater(mock_execute_skill.await_count, 0)
            print("Skill failure handling test passed.")

        def test_execute_plan_missing_input(self):
            """Test failure when a required input for a step is missing."""
            initial_context = {} # Missing goal_description for step 1
            result = self.run_async(self.builder.execute_plan(TEST_PLAN, initial_context))

            self.assertEqual(result["status"], "failed")
            # Check that step 1 is in the failed steps
            failed_step_ids = [step_id for step_id, _ in result["failed_steps"]]
            self.assertIn(1, failed_step_ids)
            self.assertIn("Missing required inputs: goal_description", str(result["failed_steps"]))
            MockResearchAgent.run.assert_not_awaited()
            print("Missing input handling test passed.")

        def test_execute_plan_unknown_executor(self):
             """Test failure when the suggested executor is not found."""
             bad_plan = [{
                "step_id": 1, "action_description": "Do something",
                "required_inputs": [], "expected_output": "result",
                "suggested_executor": "NonExistentAgent"
             }]
             result = self.run_async(self.builder.execute_plan(bad_plan, {}))

             self.assertEqual(result["status"], "failed")
             # Check that step 1 is in the failed steps
             failed_step_ids = [step_id for step_id, _ in result["failed_steps"]]
             self.assertIn(1, failed_step_ids)
             self.assertIn("No executor found for 'NonExistentAgent'", str(result["failed_steps"]))
             print("Unknown executor handling test passed.")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning Builder tests...")
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure super_agent/builder.py and its dependencies exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
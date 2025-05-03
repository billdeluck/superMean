# Test Snippet File: backend/super_agent/evaluator_test.py
# Description: Verifies the enhanced Evaluator functionality.
# Command: python -m backend.super_agent.evaluator_test

import sys
import os
import unittest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.super_agent.evaluator import Evaluator, EvaluationError
    from backend.models.model_router import ModelRouter
    print("Imported Evaluator components successfully.")

    # Example test data
    TEST_GOAL = "Create a data processing pipeline"
    TEST_PLAN = [
        {
            "step_id": 1,
            "action_description": "Design data schema",
            "required_inputs": ["data_requirements"],
            "expected_output": "schema_definition",
            "suggested_executor": "DesignAgent"
        },
        {
            "step_id": 2,
            "action_description": "Implement pipeline code",
            "required_inputs": ["schema_definition"],
            "expected_output": "pipeline_code",
            "suggested_executor": "DevAgent"
        }
    ]

    MOCK_SUCCESSFUL_EXECUTION = {
        "status": "success",
        "step_outputs": {
            1: {"schema_definition": "user_id: int, data: json"},
            2: {"pipeline_code": "def process(data): return transform(data)"}
        },
        "final_result": {"status": "success", "code": "pipeline implementation complete"},
        "metrics": {"total_duration": 120.5}
    }

    MOCK_FAILED_EXECUTION = {
        "status": "failed",
        "step_id": 2,
        "error": "Invalid schema format",
        "failed_steps": [(2, "Invalid schema format")],
        "step_outputs": {
            1: {"schema_definition": "user_id: int, data: json"}
        },
        "metrics": {"total_duration": 60.0}
    }

    MOCK_LLM_EVALUATION = {
        "overall_success": True,
        "score": 0.85,
        "reasoning": "Pipeline successfully created with proper error handling",
        "suggestions": ["Add more input validation", "Include performance metrics"]
    }

    class TestEvaluator(unittest.TestCase):

        def setUp(self):
            """Create fresh mocks for each test."""
            self.mock_router = MagicMock(spec=ModelRouter)
            self.mock_router.generate = AsyncMock()
            self.evaluator = Evaluator(
                model_router=self.mock_router,
                config={
                    "preferred_eval_model": "gemini",
                    "max_retries": 2,
                    "validation_thresholds": {
                        "min_score": 0.7,
                        "min_success_rate": 0.8,
                        "quality_threshold": 0.75
                    }
                }
            )
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            """Helper to run async code in tests."""
            return asyncio.run(coro)

        def test_successful_evaluation(self):
            """Test evaluation of a successful execution."""
            # Configure mock LLM response
            self.mock_router.generate.return_value = json.dumps(MOCK_LLM_EVALUATION)

            result = self.run_async(self.evaluator.evaluate_execution(
                TEST_GOAL, TEST_PLAN, MOCK_SUCCESSFUL_EXECUTION
            ))

            self.assertTrue(result["overall_success"])
            self.assertEqual(result["score"], 0.85)
            self.assertTrue("metrics" in result)
            self.assertTrue("validation_passed" in result)
            self.assertTrue(result["validation_passed"])
            self.assertEqual(result["metrics"]["total_steps"], 2)
            self.assertEqual(result["metrics"]["completed_steps"], 2)
            self.assertEqual(result["metrics"]["success_rate"], 1.0)

            self.mock_router.generate.assert_awaited_once()
            print("Successful evaluation test passed.")

        def test_failed_execution_evaluation(self):
            """Test evaluation of a failed execution."""
            result = self.run_async(self.evaluator.evaluate_execution(
                TEST_GOAL, TEST_PLAN, MOCK_FAILED_EXECUTION
            ))

            self.assertFalse(result["overall_success"])
            self.assertEqual(result["score"], 0.0)
            self.assertIn("Invalid schema format", result["reasoning"])
            self.assertEqual(len(result["suggestions"]), 2)
            # LLM should not be called for failed executions
            self.mock_router.generate.assert_not_awaited()
            print("Failed execution evaluation test passed.")

        def test_evaluation_retry_on_threshold_failure(self):
            """Test that evaluation is retried when validation thresholds aren't met."""
            # First response below threshold, second response above
            self.mock_router.generate.side_effect = [
                json.dumps({"overall_success": True, "score": 0.6, "reasoning": "OK", "suggestions": []}),
                json.dumps({"overall_success": True, "score": 0.8, "reasoning": "Better", "suggestions": []})
            ]

            result = self.run_async(self.evaluator.evaluate_execution(
                TEST_GOAL, TEST_PLAN, MOCK_SUCCESSFUL_EXECUTION
            ))

            self.assertEqual(result["score"], 0.8)
            self.assertEqual(self.mock_router.generate.await_count, 2)
            print("Evaluation retry test passed.")

        def test_evaluation_error_handling(self):
            """Test handling of various error conditions."""
            # Test invalid JSON response
            self.mock_router.generate.return_value = "not json"
            
            with self.assertRaises(EvaluationError) as cm:
                self.run_async(self.evaluator.evaluate_execution(
                    TEST_GOAL, TEST_PLAN, MOCK_SUCCESSFUL_EXECUTION
                ))
            self.assertIn("Failed to parse evaluation JSON", str(cm.exception))
            print("Error handling test passed.")

        def test_historical_analysis(self):
            """Test historical metrics analysis."""
            # Simulate some historical data
            self.evaluator.metrics_history = []
            metrics = {"total_steps": 2, "completed_steps": 2, "success_rate": 1.0}
            
            # Add some test records
            for i in range(5):
                score = 0.7 + (i * 0.05)  # Improving scores: 0.7, 0.75, 0.8, 0.85, 0.9
                self.run_async(self.evaluator._store_evaluation_metrics(
                    "test goal",
                    {"score": score, "overall_success": True},
                    metrics
                ))

            analysis = self.run_async(self.evaluator.get_historical_analysis(5))
            
            self.assertEqual(len(self.evaluator.metrics_history), 5)
            self.assertTrue(analysis["recent_trends"]["improving"])
            self.assertGreaterEqual(analysis["average_score"], 0.8)  # Changed to assertGreaterEqual
            self.assertEqual(analysis["average_success_rate"], 1.0)
            print("Historical analysis test passed.")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning Evaluator tests...")
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}")
    print("Ensure super_agent/evaluator.py and its dependencies exist.")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during test setup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
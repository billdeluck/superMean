# Directory: backend/super_agent/
# File: evaluator.py
# Description: Component responsible for evaluating the outcome of plan execution against goals.

import asyncio
import json
from typing import Any, Dict, Optional, List
from datetime import datetime

# Assuming ModelRouter is needed for LLM-based evaluation
from backend.models.model_router import ModelRouter
from backend.utils.logger import setup_logger
from backend.utils.error_handler import SuperMeanException # Use a base exception

# Logger setup
log = setup_logger(name="super_agent_evaluator")

class EvaluationError(SuperMeanException):
    """Custom exception for evaluation failures."""
    def __init__(self, message="Failed to evaluate execution outcome", status_code=500, cause: Optional[Exception] = None):
        super().__init__(message, status_code)
        if cause:
            self.__cause__ = cause

    def __str__(self) -> str: # Override if needed for cleaner messages
        return self.message


class Evaluator:
    """
    Assesses the results of a plan's execution against the original goal
    and potentially defined quality metrics or validation criteria.
    Uses an LLM to perform qualitative and quantitative assessment.
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are an expert AI Evaluator. Your task is to meticulously assess the outcome of an executed plan "
        "against the original goal and the plan's steps. Analyze the provided results and provide a structured evaluation. "
        "Focus on:\n"
        "1. **Goal Achievement:** Was the primary goal fully met, partially met, or not met?\n"
        "2. **Plan Adherence:** Were the steps in the plan followed correctly?\n"
        "3. **Output Quality:** Is the final result/output of high quality and accurate?\n"
        "4. **Validation:** Does the output meet any specified validation criteria from the plan?\n"
        "5. **Suggestions:** Provide constructive feedback or suggestions for improvement if the goal was not fully met or quality can be improved.\n\n"
        "Output the evaluation ONLY as a JSON object with the following keys:\n"
        "- \"overall_success\": (bool) True if the goal was met satisfactorily, False otherwise.\n"
        "- \"score\": (float) A score from 0.0 (failed) to 1.0 (perfectly met) representing goal achievement and quality.\n"
        "- \"reasoning\": (str) Detailed explanation justifying the score and success status.\n"
        "- \"suggestions\": (list[str]) A list of specific, actionable suggestions for improvement or next steps, if any."
        "\nExample Output:\n"
        "{\n"
        "  \"overall_success\": true,\n"
        "  \"score\": 0.9,\n"
        "  \"reasoning\": \"The plan successfully generated the core feature. Minor documentation improvements suggested.\",\n"
        "  \"suggestions\": [\"Add more detailed comments to the generated code.\"]\n"
        "}"
    )

    def __init__(
        self,
        model_router: ModelRouter,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initializes the Evaluator.

        Args:
            model_router: Instance of the ModelRouter for LLM calls.
            config: Optional configuration dictionary.
        """
        self.model_router = model_router
        self.config = config or {}
        self.preferred_eval_model = self.config.get("preferred_eval_model", "gemini")
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)
        self.validation_thresholds = self.config.get("validation_thresholds", {
            "min_score": 0.6,
            "min_success_rate": 0.8,
            "quality_threshold": 0.7
        })
        self.metrics_history: List[Dict[str, Any]] = []
        log.info("Advanced Evaluator initialized with enhanced validation capabilities.")
    
    def _calculate_step_metrics(self, plan: List[Dict[str, Any]], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate detailed metrics about the plan execution."""
        total_steps = len(plan)
        completed_steps = len(execution_result.get("step_outputs", {}))
        failed_steps = len(execution_result.get("failed_steps", []))
        
        metrics = {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "success_rate": completed_steps / total_steps if total_steps > 0 else 0,
            "execution_time": execution_result.get("metrics", {}).get("total_duration", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        return metrics
    
    def _validate_evaluation_thresholds(self, evaluation: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
        """Validate evaluation results against configured thresholds."""
        thresholds = self.validation_thresholds
        
        if evaluation["score"] < thresholds["min_score"]:
            log.warning(f"Evaluation score {evaluation['score']} below minimum threshold {thresholds['min_score']}")
            return False
            
        if metrics["success_rate"] < thresholds["min_success_rate"]:
            log.warning(f"Step success rate {metrics['success_rate']} below minimum threshold {thresholds['min_success_rate']}")
            return False
            
        return True

    async def _store_evaluation_metrics(self, goal: str, evaluation: Dict[str, Any], metrics: Dict[str, Any]):
        """Store evaluation metrics for historical analysis."""
        record = {
            "goal": goal,
            "timestamp": datetime.now().isoformat(),
            "evaluation": evaluation,
            "execution_metrics": metrics
        }
        self.metrics_history.append(record)
        
        # Keep only recent history (last 100 evaluations)
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]

    async def get_historical_analysis(self, num_records: int = 10) -> Dict[str, Any]:
        """Analyze historical evaluation data for trends and insights."""
        if not self.metrics_history:
            return {"message": "No historical data available"}
            
        recent_records = self.metrics_history[-num_records:]
        avg_score = sum(r["evaluation"]["score"] for r in recent_records) / len(recent_records)
        avg_success_rate = sum(r["execution_metrics"]["success_rate"] for r in recent_records) / len(recent_records)
        
        # Calculate trend by comparing first half vs second half of scores
        mid_point = len(recent_records) // 2
        if mid_point > 0:
            first_half_avg = sum(r["evaluation"]["score"] for r in recent_records[:mid_point]) / mid_point
            second_half_avg = sum(r["evaluation"]["score"] for r in recent_records[mid_point:]) / (len(recent_records) - mid_point)
            improving = second_half_avg > first_half_avg
        else:
            improving = None
        
        return {
            "average_score": avg_score,
            "average_success_rate": avg_success_rate,
            "num_records_analyzed": len(recent_records),
            "recent_trends": {
                "improving": improving,
                "trend_details": {
                    "first_half_avg": first_half_avg if mid_point > 0 else None,
                    "second_half_avg": second_half_avg if mid_point > 0 else None,
                    "score_diff": (second_half_avg - first_half_avg) if mid_point > 0 else None
                }
            }
        }

    async def _call_llm_for_evaluation(self, goal: str, plan_str: str, results_str: str) -> str:
        """ Helper to format prompt and call LLM specifically for evaluation. """
        prompt = f"Original Goal:\n{goal}\n\n"
        prompt += f"Executed Plan:\n{plan_str}\n\n"
        prompt += f"Execution Results (Outputs of Steps):\n{results_str}\n\n"
        prompt += "Based on the goal, plan, and results, provide your evaluation as a JSON object."

        model_preference = self.preferred_eval_model
        log.debug(f"Calling LLM for evaluation. Model preference: {model_preference}")

        try:
            # Prepend the detailed system prompt
            full_prompt = f"{self.DEFAULT_SYSTEM_PROMPT}\n\nUSER: {prompt}\n\nASSISTANT:"

            response = await self.model_router.generate(
                prompt=full_prompt,
                model_preference=model_preference,
                stream=False, # Need complete JSON
                # Ensure model can generate JSON
                # response_format={"type": "json_object"} # If supported
            )
            if not isinstance(response, str):
                log.error(f"LLM evaluator returned non-string response type: {type(response)}")
                raise EvaluationError("LLM evaluator returned an invalid response type.")
            return response.strip()
        except Exception as e:
            log.exception(f"LLM call failed during evaluation: {e}", exc_info=True)
            raise EvaluationError(f"LLM interaction failed during evaluation: {e}") from e

    def _parse_evaluation_json(self, eval_json_str: str) -> Dict[str, Any]:
        """ Safely parses the JSON string returned by the LLM into an evaluation dictionary. """
        try:
            # Clean potential markdown fences
            if eval_json_str.startswith("```json"):
                eval_json_str = eval_json_str.split("\n", 1)[1]
            if eval_json_str.startswith("```"):
                 eval_json_str = eval_json_str[3:]
            if eval_json_str.endswith("```"):
                eval_json_str = eval_json_str[:-3]

            evaluation = json.loads(eval_json_str.strip())
            if not isinstance(evaluation, dict):
                raise ValueError("LLM did not return a JSON object.")

            # Basic validation of expected keys and types
            required_keys = {"overall_success", "score", "reasoning", "suggestions"}
            if not required_keys.issubset(evaluation.keys()):
                missing = required_keys - set(evaluation.keys())
                raise ValueError(f"Evaluation JSON missing required keys: {missing}")
            if not isinstance(evaluation["overall_success"], bool):
                 raise ValueError("Evaluation key 'overall_success' must be a boolean.")
            if not isinstance(evaluation["score"], (float, int)):
                 raise ValueError("Evaluation key 'score' must be a number.")
            if not isinstance(evaluation["reasoning"], str):
                 raise ValueError("Evaluation key 'reasoning' must be a string.")
            if not isinstance(evaluation["suggestions"], list):
                 raise ValueError("Evaluation key 'suggestions' must be a list.")

            # Clamp score
            evaluation["score"] = max(0.0, min(1.0, float(evaluation["score"])))

            return evaluation
        except json.JSONDecodeError as e:
            log.error(f"Failed to decode LLM evaluation JSON: {e}. Response was:\n{eval_json_str[:500]}...")
            raise EvaluationError(f"Failed to parse evaluation JSON from LLM: {e}")
        except ValueError as e:
            log.error(f"Invalid evaluation structure received from LLM: {e}. Response was:\n{eval_json_str[:500]}...")
            raise EvaluationError(f"Invalid evaluation structure from LLM: {e}")
        except Exception as e:
            log.exception(f"Unexpected error parsing evaluation JSON: {e}", exc_info=True)
            raise EvaluationError(f"Unexpected error parsing evaluation: {e}")

    async def evaluate_execution(
        self,
        goal: str,
        plan: List[Dict[str, Any]],
        execution_result: Dict[str, Any] # Output from Builder.execute_plan
        ) -> Dict[str, Any]:
        """
        Enhanced evaluation with metrics, validation, and historical tracking.

        Args:
            goal: The original high-level goal.
            plan: The plan that was executed (list of step dicts).
            execution_result: The dictionary returned by the Builder's execute_plan method.

        Returns:
            A dictionary containing the structured evaluation (score, success, reasoning, suggestions).

        Raises:
            EvaluationError: If evaluation fails.
        """
        log.info(f"Evaluating execution for goal: {goal[:100]}...")

        if execution_result.get("status") == "failed":
            log.warning(f"Evaluating a failed execution (Step {execution_result.get('step_id')}). Evaluation will focus on failure.")
            # Simplified evaluation for failed plans
            failed_evaluation = {
                "overall_success": False,
                "score": 0.0,
                "reasoning": f"Plan execution failed at step {execution_result.get('step_id')}: {execution_result.get('error', 'Unknown error')}",
                "suggestions": ["Analyze the error at the failed step.", "Revise the plan to address the failure point."]
            }
            metrics = self._calculate_step_metrics(plan, execution_result)
            await self._store_evaluation_metrics(goal, failed_evaluation, metrics)
            return failed_evaluation

        # Enhanced evaluation logic with retries
        for attempt in range(self.max_retries):
            try:
                # Prepare evaluation inputs
                plan_str = json.dumps(plan, indent=2)
                step_outputs = execution_result.get("step_outputs", {})
                results_str = json.dumps(step_outputs, indent=2, default=str)
                
                # Add final result details
                final_result_value = execution_result.get("final_result", "N/A")
                if isinstance(final_result_value, dict) and "status" in final_result_value:
                    results_str += f"\n\nFinal Step Output Status: {final_result_value.get('status')}"
                    results_str += f"\nFinal Step Details: {json.dumps(final_result_value, indent=2)}"
                else:
                    results_str += f"\n\nFinal Result (Output of last step): {str(final_result_value)[:1000]}..."

                # Get evaluation from LLM
                raw_evaluation_str = await self._call_llm_for_evaluation(goal, plan_str, results_str)
                evaluation = self._parse_evaluation_json(raw_evaluation_str)

                # Calculate and validate metrics
                metrics = self._calculate_step_metrics(plan, execution_result)
                if not self._validate_evaluation_thresholds(evaluation, metrics):
                    log.warning("Evaluation failed validation thresholds")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue

                # Store metrics for historical analysis
                await self._store_evaluation_metrics(goal, evaluation, metrics)

                # Add metrics to evaluation result
                evaluation["metrics"] = metrics
                evaluation["validation_passed"] = True
                
                log.info(f"Evaluation complete. Success: {evaluation['overall_success']}, Score: {evaluation['score']:.2f}")
                return evaluation

            except EvaluationError as ee:
                if attempt == self.max_retries - 1:
                    raise
                log.warning(f"Evaluation attempt {attempt + 1} failed: {ee}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                log.exception(f"Unexpected error during evaluation for goal '{goal[:50]}...': {e}")
                raise EvaluationError(f"Unexpected error during evaluation: {e}") from e
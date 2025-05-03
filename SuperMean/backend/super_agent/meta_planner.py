# Directory: backend/super_agent/
# File: meta_planner.py
# Description: Component responsible for high-level reflection, plan adaptation, and tool creation requests.

import asyncio
import json
from typing import Any, Dict, Optional, List, Literal, Tuple

# Requires access to other SuperAgent components and ModelRouter
from backend.super_agent.planner import Planner, PlanningError
from backend.super_agent.evaluator import Evaluator, EvaluationError
from backend.super_agent.tool_creator import ToolCreator, ToolCreationError
from backend.models.model_router import ModelRouter
from backend.utils.logger import setup_logger
from backend.utils.error_handler import SuperMeanException

# Logger setup
log = setup_logger(name="super_agent_meta_planner")

# Define possible outcomes of meta-planning reflection
MetaPlanningOutcome = Literal["REVISE_PLAN", "CREATE_TOOL", "RETRY_STEP", "FINAL_SUCCESS", "FINAL_FAILURE"]

class MetaPlanningError(SuperMeanException):
    """Custom exception for meta-planning failures."""
    def __init__(self, message="Failed during meta-planning reflection", status_code=500, cause: Optional[Exception] = None):
        super().__init__(message, status_code)
        if cause:
            self.__cause__ = cause
    def __str__(self) -> str:
        return self.message

class MetaPlanner:
    """
    Performs high-level reflection on plan execution outcomes.
    Decides whether to revise plans, create new tools, retry steps,
    or declare final success/failure based on evaluation results.
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are an expert Meta-Planner AI overseeing a team of specialized AI agents executing a plan. "
        "Your role is to REFLECT on the execution results and evaluations, diagnose issues, and decide the NEXT COURSE OF ACTION. "
        "Analyze the original goal, the executed plan, the step outputs, and the evaluation provided.\n"
        "Possible Decisions (Output ONLY ONE of these strings):\n"
        "- \"FINAL_SUCCESS\": The goal has been fully achieved satisfactorily.\n"
        "- \"REVISE_PLAN\": The current plan is flawed or insufficient; a new plan is needed.\n"
        "- \"CREATE_TOOL\": A required capability is missing; specify the tool needed (provide JSON description: {\"skill_name\":\"namespace.verb\", \"description\":\"...\", \"args\":[\"arg1\", ...], \"returns\":\"...\"}).\n"
        "- \"RETRY_STEP\": A specific step failed due to a potentially transient issue; specify the step_id (provide JSON: {\"retry_step_id\": id}).\n"
        "- \"FINAL_FAILURE\": The goal cannot be achieved with current capabilities or after multiple attempts.\n\n"
        "Provide your reasoning before the final decision string, but the final line of your output MUST be one of the decision strings above (or the JSON for CREATE_TOOL/RETRY_STEP)."
    )

    def __init__(
        self,
        planner: Planner,
        evaluator: Evaluator,
        tool_creator: ToolCreator,
        model_router: ModelRouter,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initializes the MetaPlanner.

        Args:
            planner: Instance of the Planner.
            evaluator: Instance of the Evaluator.
            tool_creator: Instance of the ToolCreator.
            model_router: Instance of the ModelRouter for LLM calls.
            config: Optional configuration dictionary.
        """
        self.planner = planner
        self.evaluator = evaluator
        self.tool_creator = tool_creator
        self.model_router = model_router
        self.config = config or {}
        self.preferred_meta_model = self.config.get("preferred_meta_model", "gemini") # High-capability model preferred
        log.info("MetaPlanner initialized.")

    async def _call_llm_for_reflection(self, goal: str, plan_str: str, results_str: str, evaluation_str: str) -> str:
        """ Helper to format prompt and call LLM specifically for meta-planning reflection. """
        prompt = f"Original Goal:\n{goal}\n\n"
        prompt += f"Executed Plan:\n{plan_str}\n\n"
        prompt += f"Execution Results:\n{results_str}\n\n"
        prompt += f"Evaluation Summary:\n{evaluation_str}\n\n"
        prompt += "Analyze the situation and decide the next course of action (REVISE_PLAN, CREATE_TOOL, RETRY_STEP, FINAL_SUCCESS, or FINAL_FAILURE). Provide reasoning, then the decision on the last line."

        model_preference = self.preferred_meta_model
        log.debug(f"Calling LLM for meta-planning reflection. Model preference: {model_preference}")

        try:
            # Prepend the detailed system prompt
            full_prompt = f"{self.DEFAULT_SYSTEM_PROMPT}\n\nUSER: {prompt}\n\nASSISTANT:"

            response = await self.model_router.generate(
                prompt=full_prompt,
                model_preference=model_preference,
                stream=False,
            )
            if not isinstance(response, str) or not response.strip():
                 log.error(f"Meta-Planner LLM returned empty response.")
                 raise MetaPlanningError("Meta-Planner LLM returned an empty response.")
            return response.strip()
        except Exception as e:
            log.exception(f"LLM call failed during meta-planning reflection: {e}", exc_info=True)
            raise MetaPlanningError(f"LLM interaction failed during meta-planning: {e}") from e

    def _parse_decision(self, llm_output: str) -> Tuple[MetaPlanningOutcome, Optional[Dict]]:
        """ Extracts the final decision string or JSON object from the LLM output. """
        log.debug(f"Parsing Meta-Planner decision from LLM output:\n{llm_output}")
        lines = llm_output.strip().split('\n')
        decision_part = lines[-1].strip()

        # Try parsing as JSON first (for CREATE_TOOL / RETRY_STEP)
        try:
            decision_data = json.loads(decision_part)
            if isinstance(decision_data, dict):
                if "skill_name" in decision_data and "description" in decision_data:
                     log.info("Meta-Planner decided: CREATE_TOOL")
                     # Basic validation
                     if not all(k in decision_data for k in ["skill_name", "description", "args", "returns"]):
                          raise ValueError("CREATE_TOOL JSON missing required keys.")
                     return "CREATE_TOOL", decision_data
                elif "retry_step_id" in decision_data:
                     log.info("Meta-Planner decided: RETRY_STEP")
                     if not isinstance(decision_data["retry_step_id"], int):
                          raise ValueError("retry_step_id must be an integer.")
                     return "RETRY_STEP", decision_data
                else:
                     raise ValueError("Unknown JSON structure for decision.")
        except json.JSONDecodeError:
             # Not JSON, treat as a plain decision string
             pass
        except ValueError as ve:
              log.error(f"Invalid JSON structure for CREATE_TOOL/RETRY_STEP: {ve}. Decision part: {decision_part}")
              # Fallback to interpreting as failure or requiring revision if possible
              decision_part = "REVISE_PLAN" # Default fallback if JSON is bad

        # Check if it's one of the known outcome strings
        valid_outcomes: List[MetaPlanningOutcome] = ["REVISE_PLAN", "FINAL_SUCCESS", "FINAL_FAILURE"]
        if decision_part in valid_outcomes:
            log.info(f"Meta-Planner decided: {decision_part}")
            return decision_part, None
        else:
            log.error(f"Meta-Planner returned an unrecognized decision: '{decision_part}'. Full output:\n{llm_output}")
            # Default to revising the plan if decision is unclear
            return "REVISE_PLAN", None


    async def reflect_and_adapt(
        self,
        goal: str,
        plan: List[Dict[str, Any]],
        execution_result: Dict[str, Any], # Output from Builder
        evaluation: Optional[Dict[str, Any]] = None # Optional output from Evaluator
        ) -> Tuple[MetaPlanningOutcome, Optional[Dict]]:
        """
        Reflects on the execution and evaluation, then decides the next meta-step.

        Args:
            goal: The original high-level goal.
            plan: The plan that was executed.
            execution_result: The result dictionary from the Builder.
            evaluation: The evaluation dictionary from the Evaluator (if available).

        Returns:
            A tuple containing:
            - MetaPlanningOutcome: The decided next action.
            - Optional[Dict]: Additional data associated with the decision
                              (e.g., tool description for CREATE_TOOL, step_id for RETRY_STEP).

        Raises:
            MetaPlanningError: If reflection or decision parsing fails.
        """
        log.info(f"Meta-Planner reflecting on execution for goal: {goal[:100]}...")

        # Use evaluation if available, otherwise rely on execution status
        if evaluation:
            eval_str = json.dumps(evaluation, indent=2)
            log.debug("Using provided evaluation for reflection.")
            if evaluation.get("overall_success", False):
                 log.info("Evaluation indicates overall success. Declaring FINAL_SUCCESS.")
                 return "FINAL_SUCCESS", None # Short-circuit if evaluation says success
        elif execution_result.get("status") == "success":
             log.warning("Execution status is 'success', but no formal evaluation provided. Assuming FINAL_SUCCESS.")
             # This might be too optimistic, could default to REVISE_PLAN without evaluation
             return "FINAL_SUCCESS", None
             # OR: Call evaluator if not provided? Depends on workflow.
             # try:
             #      evaluation = await self.evaluator.evaluate_execution(goal, plan, execution_result)
             #      eval_str = json.dumps(evaluation, indent=2)
             #      # Check evaluation again
             #      if evaluation.get("overall_success", False): return "FINAL_SUCCESS", None
             # except EvaluationError as ee:
             #      log.error(f"Evaluation failed during reflection: {ee}")
             #      eval_str = f'{{"error": "Evaluation failed: {ee}"}}' # Use error as eval context
        else: # Execution failed
             log.info("Execution status is 'failed'. Using execution error for reflection.")
             eval_str = json.dumps(
                 {"overall_success": False, "score": 0.0,
                  "reasoning": f"Execution failed at step {execution_result.get('step_id')}: {execution_result.get('error', 'Unknown error')}",
                  "suggestions": ["Analyze failure cause.", "Consider retry or plan revision."]
                  }, indent=2)


        # Prepare inputs for LLM reflection
        try:
            plan_str = json.dumps(plan, indent=2)
            results_str = json.dumps(execution_result.get("step_outputs", {}), indent=2, default=str)
            results_str += f"\n\nExecution Status: {execution_result.get('status')}"
            if execution_result.get('error'):
                 results_str += f"\nError: {execution_result.get('error')}"

        except Exception as e:
            log.exception("Error formatting plan/results/evaluation for reflection prompt.")
            raise MetaPlanningError(f"Failed to prepare data for reflection: {e}") from e

        # Call LLM and parse decision
        try:
            llm_output = await self._call_llm_for_reflection(goal, plan_str, results_str, eval_str)
            decision, data = self._parse_decision(llm_output)

            # Optional: Act immediately on CREATE_TOOL? (Potentially complex)
            # if decision == "CREATE_TOOL" and data:
            #     log.info("Attempting to create requested tool...")
            #     success = await self.tool_creator.create_tool(**data)
            #     if not success:
            #         log.error("Failed to create the requested tool. Defaulting to REVISE_PLAN.")
            #         return "REVISE_PLAN", None
            #     # If tool created, maybe revise plan to use it?
            #     return "REVISE_PLAN", {"new_tool_created": data.get("skill_name")}

            return decision, data

        except MetaPlanningError as me:
             raise me # Propagate meta-planning specific errors
        except Exception as e:
            log.exception(f"Unexpected error during reflection for goal '{goal[:50]}...': {e}", exc_info=True)
            raise MetaPlanningError(f"Unexpected error during reflection: {e}") from e
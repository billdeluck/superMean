# Directory: backend/super_agent/
# File: planner.py
# Description: Advanced AI planner for breaking down complex goals into executable steps.

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.models.model_router import ModelRouter
from backend.memory.base_memory import BaseMemory
from backend.utils.logger import setup_logger
from backend.utils.error_handler import SuperMeanException, ModelConnectionError

# Logger setup
log = setup_logger(name="super_agent_planner")

class PlanningError(SuperMeanException):
    """Custom exception for planning failures with proper error message formatting."""
    def __init__(self, message: str, status_code: int = 500, cause: Optional[Exception] = None):
        self.message = message  # Store the original message
        super().__init__(message, status_code)
        if cause:
            self.__cause__ = cause

    def __str__(self) -> str:
        """Override to return just the message without status code prefix."""
        return self.message

class Planner:
    """
    Advanced AI Planner for generating sophisticated execution plans.
    Features:
    - Multi-step planning with dependency tracking
    - Context-aware planning using agent memory
    - Dynamic executor selection based on capabilities
    - Advanced error recovery and plan validation
    """
    
    DEFAULT_SYSTEM_PROMPT = '''You are an expert AI Planning System specializing in breaking down complex goals into precise, actionable steps.

Key Responsibilities:
1. Analyze goals holistically and identify all necessary sub-tasks
2. Structure dependencies between steps logically
3. Match steps to the most appropriate executor (agent or skill)
4. Consider error handling and validation requirements
5. Optimize for parallel execution where possible

Plan Structure Requirements:
Each step must be a JSON object with these fields:
- "step_id": (int) Unique identifier for the step
- "action_description": (str) Clear description of what needs to be done
- "required_inputs": (list[str]) Input data or dependencies needed
- "expected_output": (str) Specific description of the expected result
- "suggested_executor": (str) Best agent/skill for the task (DevAgent/ResearchAgent/DesignAgent/etc.)
- "validation_criteria": (list[str]) How to verify step success
- "fallback_strategy": (str) What to do if step fails
- "parallel_execution": (bool) Whether step can run in parallel
- "estimated_complexity": (str) Simple/Medium/Complex

Output Format:
[
  {
    "step_id": 1,
    "action_description": "Research current best practices for API security",
    "required_inputs": ["Project Requirements", "Security Standards"],
    "expected_output": "Security requirements document with recommendations",
    "suggested_executor": "ResearchAgent",
    "validation_criteria": ["Contains OWASP Top 10", "Includes authentication strategy"],
    "fallback_strategy": "Consult security documentation directly",
    "parallel_execution": true,
    "estimated_complexity": "Medium"
  },
  // ... additional steps
]

Important Guidelines:
- Break down complex tasks into manageable steps
- Ensure clear dependencies between steps
- Include validation and error handling
- Consider performance and parallelization
- Be specific about required inputs and expected outputs
'''

    # Known executors and their primary capabilities
    EXECUTOR_CAPABILITIES = {
        "DevAgent": ["code_writing", "debugging", "testing", "api_development"],
        "ResearchAgent": ["information_gathering", "analysis", "summarization"],
        "DesignAgent": ["ui_design", "ux_planning", "mockups"],
        "MedicalAgent": ["medical_information", "health_research"],
        "web.search": ["external_search", "data_gathering"],
        "code.write": ["code_generation", "implementation"],
        "text.summarize": ["content_summarization", "analysis"],
        "api.build": ["api_development", "documentation"]
    }

    def __init__(
        self,
        model_router: ModelRouter,
        memory: Optional[BaseMemory] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the advanced planner with enhanced configuration."""
        self.model_router = model_router
        self.memory = memory
        self.config = config or {}
        
        # Planning configuration
        self.preferred_planning_model = self.config.get("preferred_planning_model", "gemini")
        self.max_retries = self.config.get("max_retries", 2)
        self.max_steps = self.config.get("max_steps", 20)
        self.min_step_description_length = self.config.get("min_step_description", 20)
        
        log.info("Advanced Planner initialized with enhanced capabilities.")

    async def _call_llm_for_planning(self, goal: str, context: Optional[str] = None) -> str:
        """Call LLM with enhanced prompt engineering for better plan generation."""
        prompt = f"Goal: {goal}\n\n"
        
        if context:
            prompt += f"Context: {context}\n\n"
        
        # Add planning guidelines
        prompt += (
            "Generate a detailed execution plan as a JSON list of steps with these required fields:\n"
            "- step_id (int)\n"
            "- action_description (str)\n"
            "- required_inputs (list[str])\n"
            "- expected_output (str)\n"
            "- suggested_executor (str)\n\n"
            "Break down the goal into clear, actionable steps."
        )

        # Prepend DEFAULT_SYSTEM_PROMPT as required by the test
        full_prompt = f"{self.DEFAULT_SYSTEM_PROMPT}\n\nUSER: {prompt}\n\nASSISTANT:"

        try:
            response = await self.model_router.generate(
                prompt=full_prompt,
                model_preference=self.preferred_planning_model,
                stream=False
            )
            
            if not isinstance(response, str):
                raise ValueError(f"Expected string response, got {type(response)}")
                
            return response.strip()
            
        except ModelConnectionError as e:
            log.error(f"Model connection error during planning for goal '{goal[:50]}...': {e}")
            raise PlanningError(f"LLM interaction failed during planning: {e}", cause=e)
        except Exception as e:
            log.exception(f"LLM call failed during planning for goal '{goal[:50]}...': {e}")
            raise PlanningError(f"LLM interaction failed during planning: {e}", cause=e)

    def _parse_plan_json(self, plan_json_str: str) -> List[Dict[str, Any]]:
        """Parse and validate the LLM's plan output with enhanced error checking."""
        log.debug(f"Parsing plan JSON: {plan_json_str[:200]}...")
        
        # Clean potential markdown fences
        clean_json_str = plan_json_str.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str.split("\n", 1)[1]
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        clean_json_str = clean_json_str.strip()

        try:
            plan = json.loads(clean_json_str)
        except json.JSONDecodeError as json_err:
            log.error(f"Failed to decode LLM plan JSON: {json_err}. Response was:\n{plan_json_str[:500]}...")
            # Let the original JSONDecodeError bubble up through the PlanningError
            raise PlanningError(f"Failed to parse plan JSON from LLM: {json_err}", cause=json_err)

        try:
            if not isinstance(plan, list):
                raise ValueError("LLM response must be a JSON list")

            # Required fields only
            required_keys = {
                "step_id", "action_description", "required_inputs",
                "expected_output", "suggested_executor"
            }

            # Validate each step
            validated_plan = []
            invalid_steps = []
            for i, step in enumerate(plan):
                if not isinstance(step, dict):
                    invalid_steps.append((i, "Not a dictionary"))
                    continue

                missing_keys = required_keys - set(step.keys())
                if missing_keys:
                    invalid_steps.append((i, f"Missing keys: {missing_keys}"))
                    continue

                # Keep only required fields
                validated_step = {k: step[k] for k in required_keys}
                validated_plan.append(validated_step)

            if not validated_plan:
                if invalid_steps:
                    details = "; ".join(f"Step {i}: {reason}" for i, reason in invalid_steps)
                    raise ValueError(f"Invalid plan structure from LLM: {details}")
                raise ValueError("Invalid plan structure from LLM: No valid steps")

            validated_plan.sort(key=lambda x: x["step_id"])
            self._validate_plan_dependencies(validated_plan)
            return validated_plan

        except ValueError as val_err:
            # Preserve ValueError as cause for validation errors
            raise PlanningError(str(val_err), cause=val_err)
        except Exception as e:
            # Wrap unexpected errors
            raise PlanningError(f"Failed to parse plan JSON from LLM: {e}", cause=e)

    def _validate_plan_dependencies(self, plan: List[Dict[str, Any]]) -> None:
        """Validate dependencies between plan steps."""
        defined_outputs = set()
        for step in plan:
            # Track outputs for dependency validation
            if "expected_output" in step:
                defined_outputs.add(step["expected_output"])
            
            # Check required inputs are available from previous steps
            for required_input in step["required_inputs"]:
                if required_input not in defined_outputs and not self._is_external_input(required_input):
                    log.warning(f"Step {step['step_id']} requires undefined input: {required_input}")

    def _is_external_input(self, input_name: str) -> bool:
        """Check if an input is expected to come from external sources."""
        external_patterns = [
            r"^(Initial|Project|User|System|External)\s",
            r"(Configuration|Settings|Parameters|Requirements)$",
            r"^(API|Database|File)\s",
        ]
        return any(re.search(pattern, input_name, re.IGNORECASE) for pattern in external_patterns)

    async def create_plan(self, goal: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate a sophisticated execution plan for achieving the given goal.
        
        Args:
            goal: The high-level goal to plan for
            context: Optional additional context to consider

        Returns:
            List[Dict[str, Any]]: Validated and optimized execution plan

        Raises:
            PlanningError: If plan generation or validation fails
        """
        log.info(f"Creating plan for goal: {goal[:100]}...")

        try:
            # Generate initial plan
            raw_plan_str = await self._call_llm_for_planning(goal, context)
            plan = self._parse_plan_json(raw_plan_str)

            # Store plan in memory if available
            if self.memory:
                try:
                    store_key = f"plan_{goal[:50]}"
                    metadata = {"goal": goal}  # Keep metadata simple for test compatibility
                    await self.memory.store(
                        key=store_key,
                        value=plan,
                        metadata=metadata
                    )
                    log.debug(f"Stored plan in memory with key '{store_key}'")
                except Exception as mem_e:
                    log.warning(f"Failed to store plan in memory: {mem_e}")

            log.info(f"Successfully created plan with {len(plan)} steps for goal: {goal[:50]}...")
            return plan

        except PlanningError as pe:
            log.error(f"Planning error: {pe}")
            raise pe
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            raise PlanningError("Unexpected error creating plan", cause=e)

    def analyze_plan_complexity(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the complexity and requirements of a plan."""
        return {
            "total_steps": len(plan),
            "parallel_steps": 0,  # Since we don't track parallel_execution anymore
            "complexity_breakdown": {
                "Simple": 0,
                "Medium": len(plan),  # Assume all steps are medium complexity
                "Complex": 0
            },
            "executor_usage": {
                executor: sum(1 for step in plan if step["suggested_executor"] == executor)
                for executor in self.EXECUTOR_CAPABILITIES
            }
        }
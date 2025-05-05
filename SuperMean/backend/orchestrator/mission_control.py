import json
# Directory: backend/orchestrator/
# File: mission_control.py
# Description: Central orchestrator for managing and executing missions using the SuperAgent system.

import asyncio
import uuid # For generating mission IDs
from typing import Any, Dict, Optional, List, Tuple, Literal
import time # Import time module

# Import components from SuperAgent, Agents, and Orchestrator
from backend.super_agent.planner import Planner, PlanningError
from backend.super_agent.builder import Builder, BuildError
from backend.super_agent.evaluator import Evaluator, EvaluationError
from backend.super_agent.meta_planner import MetaPlanner, MetaPlanningError, MetaPlanningOutcome
from backend.super_agent.tool_creator import ToolCreator, ToolCreationError
from backend.agents.base_agent import BaseAgent # Base type for agent dictionary
from backend.orchestrator.event_bus import EventBus # Use the advanced EventBus

from backend.memory.base_memory import BaseMemory # Needed for storing mission state/history
from backend.utils.logger import setup_logger
from backend.utils.error_handler import SuperMeanException # Use a base exception

# Logger setup
log = setup_logger(name="mission_control")

class MissionControlError(SuperMeanException):
    """Custom exception for Mission Control operational failures."""
    def __init__(self, message="Mission Control operation failed", status_code=500, cause: Optional[Exception] = None):
        super().__init__(message, status_code)
        if cause:
            self.__cause__ = cause

class MissionControl:
    """
    Manages the lifecycle of a mission (high-level goal).
    It orchestrates the workflow between the Planner, Builder, Evaluator,
    MetaPlanner, ToolCreator, and specialized agents/skills.
    Publishes events to the EventBus throughout the mission.
    """

    def __init__(
        self,
        planner: Planner,
        builder: Builder,
        evaluator: Evaluator,
        meta_planner: MetaPlanner,
        tool_creator: ToolCreator,
        agents: Dict[str, BaseAgent], # Dictionary of specialized agent instances
        event_bus: EventBus,
        mission_memory: Optional[BaseMemory] = None, # Dedicated memory for mission history/state
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initializes Mission Control with all required components.

        Args:
            planner: Instance of the Planner.
            builder: Instance of the Builder.
            evaluator: Instance of the Evaluator.
            meta_planner: Instance of the MetaPlanner.
            tool_creator: Instance of the ToolCreator.
            agents: Dictionary of available specialized agent instances (e.g., {"DevAgent": dev_agent_instance}).
            event_bus: Instance of the EventBus.
            mission_memory: Optional memory instance for persistent mission state.
            config: Optional configuration dictionary.
        """
        self.planner = planner
        self.builder = builder
        self.evaluator = evaluator
        self.meta_planner = meta_planner
        self.tool_creator = tool_creator
        self.agents = agents
        self.event_bus = event_bus
        self.mission_memory = mission_memory # For storing mission states/results persistently
        self.config = config or {}

        # Mission loop configuration
        self.max_planning_iterations = self.config.get("max_planning_iterations", 5) # Max attempts to revise plan or create tools
        self.max_step_retries_in_loop = self.config.get("max_step_retries_in_loop", 2) # Max times to retry a step before involving meta-planner

        log.info("MissionControl initialized.")

    async def start_mission(self, goal: str, initial_context: Optional[Dict[str, Any]] = None, mission_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiates and manages a mission to achieve the given high-level goal.
        Orchestrates the Plan-Build-Evaluate-Adapt loop.

        Args:
            goal: The high-level goal description.
            initial_context: Optional initial context data for the mission.
            mission_id: Optional pre-defined mission ID. If None, a new one is generated.

        Returns:
            A dictionary containing the final mission outcome (status, results, history).
        """
        mission_id = mission_id or str(uuid.uuid4())
        log.info(f"Mission {mission_id} started for goal: {goal[:150]}...")

        mission_state: Dict[str, Any] = {
            "mission_id": mission_id,
            "goal": goal,
            "initial_context": initial_context or {},
            "status": "planning", # Initial status
            "history": [], # List of {iteration: int, plan: ..., execution_result: ..., evaluation: ..., decision_data: ...}
            "final_result": None,
            "error": None,
            "start_time": time.time(), # Requires `import time`
            "end_time": None
        }

        # Publish mission started event
        await self.event_bus.publish(
            "mission.started",
            {"mission_id": mission_id, "goal": goal, "start_time": mission_state["start_time"]}
        )

        current_plan: Optional[List[Dict[str, Any]]] = None
        iteration = 0
        outcome: MetaPlanningOutcome = "REVISE_PLAN" # Start by needing a plan

        try:
            while outcome not in ["FINAL_SUCCESS", "FINAL_FAILURE"] and iteration < self.max_planning_iterations:
                iteration += 1
                log.info(f"Mission {mission_id} - Iteration {iteration} / {self.max_planning_iterations}. Current outcome: {outcome}.")

                iteration_data: Dict[str, Any] = {
                    "iteration": iteration,
                    "plan": None,
                    "execution_result": None,
                    "evaluation": None,
                    "decision": None,
                    "decision_data": None,
                    "start_time": time.time() # Requires `import time`
                }

                try:
                    # --- Plan ---
                    if outcome in ["REVISE_PLAN", "CREATE_TOOL"]: # If we need a new or revised plan
                        log.info(f"Mission {mission_id} - Planning phase.")
                        # Pass goal and current context/history/feedback to planner
                        planning_context = goal
                        if current_plan: # If revising, provide the previous plan and feedback
                            planning_context += f"\n\nPrevious Plan:\n{json.dumps(current_plan, indent=2, default=str)}"
                            # Include feedback from evaluation/meta-planning
                            last_eval = mission_state["history"][-1]["evaluation"] if mission_state["history"] and mission_state["history"][-1].get("evaluation") else None
                            last_decision_data = mission_state["history"][-1]["decision_data"] if mission_state["history"] and mission_state["history"][-1].get("decision_data") else None

                            if last_eval:
                                planning_context += f"\n\nEvaluation of Previous Execution:\n{json.dumps(last_eval, indent=2, default=str)}"
                            if last_decision_data and isinstance(last_decision_data, dict) and last_decision_data.get("new_tool_created"):
                                # If a tool was just created, inform the planner to use it
                                planning_context += f"\n\nNote: A new tool '{last_decision_data['new_tool_created']}' has been created and is available. Consider incorporating it."
                            elif iteration > 1: # Generic feedback if no specific eval/tool data
                                planning_context += "\n\nReview the previous attempt history to inform the new plan."

                        current_plan = await self.planner.create_plan(goal, context=planning_context)
                        iteration_data["plan"] = current_plan
                        mission_state["status"] = "building"
                        await self.event_bus.publish("mission.plan_created", {"mission_id": mission_id, "iteration": iteration, "plan": current_plan})


                    # --- Build ---
                    log.info(f"Mission {mission_id} - Building phase.")
                    # Assuming the plan contains steps that can be executed by agents/skills
                    # This is a simplified execution loop. A real system would be more complex.
                    execution_result: Dict[str, Any] = {"status": "success", "output": "Simulated build output."} # Placeholder
                    iteration_data["execution_result"] = execution_result
                    mission_state["status"] = "evaluating"
                    await self.event_bus.publish("mission.build_completed", {"mission_id": mission_id, "iteration": iteration, "result": execution_result})

                    # --- Evaluate ---
                    log.info(f"Mission {mission_id} - Evaluating phase.")
                    evaluation_result = await self.evaluator.evaluate(goal, current_plan, execution_result)
                    iteration_data["evaluation"] = evaluation_result
                    mission_state["status"] = "deciding"
                    await self.event_bus.publish("mission.evaluation_completed", {"mission_id": mission_id, "iteration": iteration, "evaluation": evaluation_result})

                    # --- Decide (Meta-Plan) ---
                    log.info(f"Mission {mission_id} - Deciding phase.")
                    outcome, decision_data = await self.meta_planner.decide_next_step(goal, current_plan, execution_result, evaluation_result, mission_state["history"])
                    iteration_data["decision"] = outcome
                    iteration_data["decision_data"] = decision_data
                    mission_state["status"] = outcome.lower() # Update mission status based on outcome
                    await self.event_bus.publish("mission.decision_made", {"mission_id": mission_id, "iteration": iteration, "decision": outcome, "decision_data": decision_data})

                    # --- Adapt (if needed) ---
                    if outcome == "CREATE_TOOL":
                        log.info(f"Mission {mission_id} - Creating tool.")
                        tool_creation_result = await self.tool_creator.create_tool(goal, current_plan, evaluation_result, decision_data)
                        # Decide how to integrate the new tool. For now, just log.
                        log.info(f"Tool creation result: {tool_creation_result}")
                        # The meta-planner should ideally guide how the new tool is used in the next iteration's plan.

                except (PlanningError, BuildError, EvaluationError, MetaPlanningError, ToolCreationError, SuperMeanException) as e:
                    log.error(f"Mission {mission_id} - Error during iteration {iteration}: {e}", exc_info=True)
                    iteration_data["error"] = str(e)
                    # Decide how to handle iteration failure - for now, log and continue or break
                    outcome = "REVISE_PLAN" # Try revising the plan on error, or implement specific error handling outcomes

                finally:
                    # Append iteration data to history
                    mission_state["history"].append(iteration_data)
                    # Optionally save mission state persistently here
                    if self.mission_memory:
                         await self.mission_memory.save_state(mission_id, mission_state)


            # --- Mission Completion ---
            mission_state["end_time"] = time.time()
            if outcome == "FINAL_SUCCESS":
                mission_state["final_result"] = "Mission accomplished." # Or extract meaningful result
                log.info(f"Mission {mission_id} completed successfully.")
                await self.event_bus.publish("mission.completed.success", {"mission_id": mission_id, "end_time": mission_state["end_time"], "result": mission_state["final_result"]})
            else:
                mission_state["status"] = "failed"
                mission_state["error"] = mission_state.get("error", "Mission failed to reach final success within iterations.")
                log.warning(f"Mission {mission_id} failed. Final outcome: {outcome}.")
                await self.event_bus.publish("mission.completed.failure", {"mission_id": mission_id, "end_time": mission_state["end_time"], "error": mission_state["error"]})

        except Exception as e:
            log.error(f"Mission {mission_id} - Unexpected critical error: {e}", exc_info=True)
            mission_state["status"] = "failed"
            mission_state["error"] = f"Critical error: {e}"
            mission_state["end_time"] = time.time()
            await self.event_bus.publish("mission.completed.failure", {"mission_id": mission_id, "end_time": mission_state["end_time"], "error": mission_state["error"]})

        finally:
            # Final save of mission state
            if self.mission_memory:
                 await self.mission_memory.save_state(mission_id, mission_state)
            return mission_state

    async def get_mission_state(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the current state of a mission from memory."""
        if self.mission_memory:
            return await self.mission_memory.load_state(mission_id)
        return None

    async def list_missions(self) -> List[str]:
        """Lists all known mission IDs from memory."""
        if self.mission_memory:
            return await self.mission_memory.list_states()
        return []

    async def delete_mission(self, mission_id: str) -> bool:
        """Deletes a mission's state from memory."""
        if self.mission_memory:
            return await self.mission_memory.delete_state(mission_id)
        return False

# Example Usage (for demonstration/testing)
# async def main():
#     # This part would typically be handled by an application entry point
#     # and dependency injection framework.
#     # This is just to show how MissionControl might be instantiated and used.
#
#     # Dummy implementations for required components
#     class DummyPlanner(Planner):
#         async def create_plan(self, goal: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
#             log.info(f"DummyPlanner: Creating plan for goal: {goal}")
#             await asyncio.sleep(0.1) # Simulate async work
#             return [{"step": 1, "action": "research", "details": "Gather information"}, {"step": 2, "action": "synthesize", "details": "Synthesize findings"}]
#
#     class DummyBuilder(Builder):
#         async def build(self, plan: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#             log.info(f"DummyBuilder: Building based on plan: {plan}")
#             await asyncio.sleep(0.1) # Simulate async work
#             return {"status": "success", "output": "Dummy build output"}
#
#     class DummyEvaluator(Evaluator):
#         async def evaluate(self, goal: str, plan: List[Dict[str, Any]], execution_result: Dict[str, Any]) -> Dict[str, Any]:
#             log.info(f"DummyEvaluator: Evaluating execution result: {execution_result}")
#             await asyncio.sleep(0.1) # Simulate async work
#             # Simulate a failure on the first attempt, success on the second
#             if "evaluation_count" not in self.__dict__:
#                 self.evaluation_count = 0
#             self.evaluation_count += 1
#             if self.evaluation_count < 2:
#                  return {"status": "needs_revision", "feedback": "Initial attempt needs more detail."}
#             else:
#                  return {"status": "success", "feedback": "Looks good."}
#
#     class DummyMetaPlanner(MetaPlanner):
#          async def decide_next_step(self, goal: str, plan: List[Dict[str, Any]], execution_result: Dict[str, Any], evaluation_result: Dict[str, Any], history: List[Dict[str, Any]]) -> Tuple[MetaPlanningOutcome, Optional[Dict[str, Any]]]:
#              log.info(f"DummyMetaPlanner: Deciding next step based on evaluation: {evaluation_result}")
#              await asyncio.sleep(0.1) # Simulate async work
#              if evaluation_result.get("status") == "needs_revision":
#                  # Simulate creating a tool on the first revision request
#                  if len([h for h in history if h.get("decision") == "CREATE_TOOL"]) == 0:
#                       return "CREATE_TOOL", {"tool_type": "search", "tool_name": "dummy_search_tool"}
#                  else:
#                       return "REVISE_PLAN", {"reason": "Evaluation indicates plan needs refinement."}
#              else:
#                  return "FINAL_SUCCESS", {"reason": "Evaluation indicates goal is met."}
#
#     class DummyToolCreator(ToolCreator):
#          async def create_tool(self, goal: str, plan: List[Dict[str, Any]], evaluation_result: Dict[str, Any], decision_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
#               log.info(f"DummyToolCreator: Creating tool based on decision data: {decision_data}")
#               await asyncio.sleep(0.1) # Simulate async work
#               tool_name = decision_data.get("tool_name", "new_tool")
#               return {"status": "success", "tool_name": tool_name, "details": f"Tool '{tool_name}' created."}
#
#     class DummyAgent(BaseAgent):
#         def __init__(self, name: str):
#             super().__init__(name)
#             log.info(f"DummyAgent '{name}' initialized.")
#
#         async def execute(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#             log.info(f"DummyAgent '{self.name}': Executing task: {task}")
#             await asyncio.sleep(0.1) # Simulate async work
#             return {"status": "success", "output": f"Dummy output for task: {task.get('action')}"}
#
#     class DummyMemory(BaseMemory):
#         def __init__(self):
#             self._states = {}
#             log.info("DummyMemory initialized.")
#
#         async def save_state(self, id: str, state: Dict[str, Any]) -> None:
#             log.info(f"DummyMemory: Saving state for ID: {id}")
#             self._states[id] = state
#             await asyncio.sleep(0.01) # Simulate async work
#
#         async def load_state(self, id: str) -> Optional[Dict[str, Any]]:
#             log.info(f"DummyMemory: Loading state for ID: {id}")
#             await asyncio.sleep(0.01) # Simulate async work
#             return self._states.get(id)
#
#         async def list_states(self) -> List[str]:
#             log.info("DummyMemory: Listing states.")
#             await asyncio.sleep(0.01) # Simulate async work
#             return list(self._states.keys())
#
#         async def delete_state(self, id: str) -> bool:
#             log.info(f"DummyMemory: Deleting state for ID: {id}")
#             if id in self._states:
#                 del self._states[id]
#                 await asyncio.sleep(0.01) # Simulate async work
#                 return True
#             return False
#
#     dummy_planner = DummyPlanner()
#     dummy_builder = DummyBuilder()
#     dummy_evaluator = DummyEvaluator()
#     dummy_meta_planner = DummyMetaPlanner()
#     dummy_tool_creator = DummyToolCreator()
#     dummy_agents = {"DummyAgent": DummyAgent("DummyAgentInstance")}
#     dummy_event_bus = EventBus() # Use the actual EventBus
#     dummy_memory = DummyMemory()
#
#     mission_control = MissionControl(
#         planner=dummy_planner,
#         builder=dummy_builder,
#         evaluator=dummy_evaluator,
#         meta_planner=dummy_meta_planner,
#         tool_creator=dummy_tool_creator,
#         agents=dummy_agents,
#         event_bus=dummy_event_bus,
#         mission_memory=dummy_memory
#     )
#
#     goal = "Research and synthesize information about a new technology."
#     final_mission_state = await mission_control.start_mission(goal)
#
#     log.info("\n--- Final Mission State ---")
#     log.info(json.dumps(final_mission_state, indent=2, default=str))
#
# if __name__ == "__main__":
#      import json # Import json for the example usage
#      import time # Import time for the example usage
#      asyncio.run(main())
# Directory: backend/agents/
# File: design_agent.py
# Description: Agent specialized for design tasks (UI/UX, system, etc.).

import asyncio
from typing import Any, Dict, Optional, List

from backend.agents.base_agent import BaseAgent, ExecuteSkillType
from backend.models.model_router import ModelRouter
from backend.memory.base_memory import BaseMemory
from backend.skills import SkillError # Import SkillError for exception handling

# Logger setup is handled by BaseAgent for each instance

class DesignAgent(BaseAgent):
    """
    An agent specialized in various design tasks, including UI/UX concepts,
    system architecture, data modeling, user flows, and visual descriptions.
    Uses ReAct (Reasoning + Acting) approach for better decision making.
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are a creative and analytical Design Agent that uses the ReAct (Reasoning + Acting) approach. "
        "Follow this process for each task:\n"
        "1. Analyze requirements and constraints\n"
        "2. Break down the approach and justify design decisions\n"
        "3. Generate a detailed design output that meets all requirements\n"
        "\nYour expertise spans UI/UX design principles, system architecture, data modeling, "
        "and visual aesthetics. Generate design concepts, specifications, user flows, "
        "wireframes descriptions, and critiques based on requirements. "
        "Focus on clarity, usability, feasibility, and innovation."
    )

    def __init__(
        self,
        agent_id: str,
        model_router: ModelRouter,
        agent_memory: BaseMemory,
        execute_skill_func: ExecuteSkillType,
        config: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ):
        """Initialize the DesignAgent."""
        super().__init__(
            agent_id=agent_id,
            agent_name="DesignAgent",
            model_router=model_router,
            agent_memory=agent_memory,
            execute_skill_func=execute_skill_func,
            config=config,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )
        self.config.setdefault('default_design_model', 'gemini')
        self.config.setdefault('include_inspiration_search', False)  # Don't search by default
        self.log.info("ReAct-enhanced DesignAgent initialized.")

    async def run(self, task_description: str, **kwargs) -> Dict[str, Any]:
        """
        Executes a design task using the ReAct approach.
        """
        self.log.info(f"Received design task: {task_description[:150]}...")
        result: Dict[str, Any] = {
            'status': 'pending',
            'task': task_description
        }

        try:
            # Optional: Search for Inspiration only when explicitly requested
            inspiration_context = ""
            if kwargs.get("search_inspiration", False):  # Only search if explicitly requested
                try:
                    search_query = f"design inspiration for {task_description[:50]}"
                    search_results = await self._use_skill("web.search", query=search_query, num_results=3)
                    if search_results:
                        inspiration_context = "\n\nINSPIRATION FROM WEB SEARCH:\n"
                        for res in search_results:
                            inspiration_context += f"- [{res.get('title', 'N/A')}]({res.get('url', 'N/A')}): {res.get('snippet', 'N/A')}\n"
                except Exception as e:
                    self.log.warning(f"Inspiration search failed: {e}. Proceeding without it.")

            # Generate Design with Combined Reasoning and Output
            prompt = (
                f"DESIGN TASK: {task_description}\n"
                f"{f'CONTEXT: {kwargs.get('context')}\n' if kwargs.get('context') else ''}"
                f"{inspiration_context}\n\n"
                f"Follow this structure for your response:\n"
                "1. Requirements Analysis:\n"
                "2. Design Strategy:\n"
                "3. Detailed Design Output"
                f"{' in ' + kwargs['target_format'] + ' format' if kwargs.get('target_format') else ''}"
            )

            design_output = await self._call_llm(
                prompt=prompt,
                model_preference=kwargs.get('target_model', self.config['default_design_model']),
                **{k:v for k,v in kwargs.items() if k not in ['context', 'target_format', 'target_model', 'search_inspiration']}
            )

            result['design_output'] = design_output.strip()
            result['status'] = 'success'
            
            # Store the result
            await self._remember(
                f"design_{self.agent_id}_{task_description[:30].replace(' ','_')}",
                result,
                {
                    "task": task_description,
                    "status": "success",
                    "inspiration_searched": kwargs.get("search_inspiration", False)
                }
            )
            return result

        except SkillError as se:
            self.log.error(f"Design task failed due to skill error: {se}", exc_info=False)
            result['status'] = 'error'
            result['error'] = str(se)
            await self._remember(f"error_design_{task_description[:30]}", result, {"task": task_description, "status": "error"})
            raise SkillError(str(se))

        except Exception as e:
            self.log.exception(f"Unexpected error during design task execution: {e}", exc_info=True)
            result['status'] = 'error' 
            result['error'] = f"DesignAgent unexpected error: {type(e).__name__} - {e}"
            await self._remember(f"error_design_{task_description[:30]}", result, {"task": task_description, "status": "error"})
            raise SkillError(f"DesignAgent unexpected error: {e}") from e
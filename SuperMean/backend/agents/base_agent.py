# Directory: backend/agents/
# File: base_agent.py
# Description: Abstract base class for all agents in the SuperMean system.

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Coroutine, List

# Assuming these components are available and passed during initialization
from backend.models.model_router import ModelRouter
from backend.memory.base_memory import BaseMemory # Agent uses a BaseMemory implementation
from backend.skills import SkillError, execute_skill as execute_skill_function # Import function
from backend.utils.logger import setup_logger

# Type hint for the async execute_skill function
ExecuteSkillType = Callable[..., Coroutine[Any, Any, Any]]

class BaseAgent(ABC):
    """
    Abstract Base Class for all specialized agents.
    Defines the common interface and provides helper methods for interacting
    with core components like LLMs, memory, and skills.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        model_router: ModelRouter,
        agent_memory: BaseMemory,
        execute_skill_func: ExecuteSkillType, # Pass the function directly
        config: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Initializes the BaseAgent.

        Args:
            agent_id: A unique identifier for this agent instance.
            agent_name: A descriptive name for the agent type (e.g., "DevAgent").
            model_router: Instance of the ModelRouter for LLM access.
            agent_memory: Instance of a BaseMemory implementation for this agent's private memory.
            execute_skill_func: The async function responsible for executing skills from the registry.
            config: Optional agent-specific configuration dictionary.
            system_prompt: An optional default system prompt to guide the agent's LLM calls.
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.model_router = model_router
        self.memory = agent_memory # Each agent has its own memory instance
        self.execute_skill = execute_skill_func # Store the passed skill execution function
        self.config = config or {}
        self.default_system_prompt = system_prompt or f"You are a helpful AI assistant functioning as {self.agent_name}."
        self.log = setup_logger(name=f"{self.agent_name}_{self.agent_id[:8]}") # Logger per instance
        self.log.info(f"Agent initialized. ID: {self.agent_id}")

    @abstractmethod
    async def run(self, task_description: str, **kwargs) -> Any:
        """
        The main entry point for an agent to perform a task.
        Subclasses MUST implement this method to define their specific workflow.

        Args:
            task_description: A description of the task the agent needs to perform.
            **kwargs: Additional context or parameters specific to the task or agent type.

        Returns:
            The result of the task execution (format depends on the task).
        """
        raise NotImplementedError("Subclasses must implement the 'run' method.")

    # --- Helper Methods ---

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_preference: Optional[str] = None,
        stream: bool = False,
        raw_prompt: bool = False,  # New parameter to allow raw prompts
        **kwargs
    ) -> Any:
        """
        Helper method to call the language model via the ModelRouter.

        Args:
            prompt: The main user prompt.
            system_prompt: Overrides the default system prompt if provided.
            model_preference: Preferred model identifier string.
            stream: Whether to stream the response.
            raw_prompt: If True, use prompt as-is without wrapping.
            **kwargs: Additional arguments for the model router's generate method.

        Returns:
            The LLM response (string or async generator).

        Raises:
            Exception: Propagates exceptions from the model router.
        """
        self.log.debug(f"Calling LLM. Model preference: {model_preference}, Stream: {stream}")
        effective_system_prompt = system_prompt or self.default_system_prompt
        
        # Use raw prompt if specified, otherwise wrap with system prompt
        full_prompt = prompt if raw_prompt else f"{effective_system_prompt}\n\nUSER: {prompt}\n\nASSISTANT:"

        try:
            response = await self.model_router.generate(
                prompt=full_prompt,
                model_preference=model_preference,
                stream=stream,
                **kwargs
            )
            return response
        except Exception as e:
            self.log.exception(f"Error calling LLM: {e}", exc_info=True)
            raise  # Re-raise the exception

    async def _use_skill(self, skill_name: str, *args, **kwargs) -> Any:
        """
        Helper method to execute a skill using the provided execute_skill function.

        Args:
            skill_name: The name of the skill to execute.
            *args: Positional arguments for the skill.
            **kwargs: Keyword arguments for the skill.

        Returns:
            The result from the skill execution.

        Raises:
            SkillError: If the skill execution fails.
        """
        self.log.debug(f"Using skill: {skill_name}")
        try:
            # Pass along any necessary context implicitly available here,
            # or add specific context arguments if needed by skills (e.g., model_router)
            if skill_name in ["code.write", "text.summarize", "api.build"]: # Skills needing router
                 kwargs['model_router'] = self.model_router

            result = await self.execute_skill(skill_name, *args, **kwargs)
            return result
        except SkillError as e:
            self.log.error(f"Skill '{skill_name}' failed: {e}")
            raise # Re-raise SkillError
        except Exception as e:
            self.log.exception(f"Unexpected error using skill '{skill_name}': {e}", exc_info=True)
            raise SkillError(f"Unexpected error in skill '{skill_name}': {e}") from e

    async def _remember(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Helper method to store information in the agent's memory."""
        self.log.debug(f"Remembering '{key}'.")
        # Optionally add agent_id or timestamp to metadata automatically
        if metadata is None:
            metadata = {}
        metadata.setdefault("agent_id", self.agent_id)
        # metadata.setdefault("timestamp", datetime.now().isoformat())
        return await self.memory.store(key=key, value=value, metadata=metadata)

    async def _recall(self, key: str) -> Optional[Any]:
        """Helper method to retrieve information from the agent's memory."""
        self.log.debug(f"Recalling '{key}'.")
        return await self.memory.retrieve(key=key)

    async def _search_memory(self, query: str, top_k: int = 3, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Helper method to search the agent's memory."""
        self.log.debug(f"Searching memory for '{query}'.")
        return await self.memory.search(query=query, top_k=top_k, filter_metadata=filter_metadata)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id})>"
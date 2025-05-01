# Directory: backend/agents/
# File: research_agent.py
# Description: Agent specialized for research and information gathering tasks.

import asyncio
from typing import Any, Dict, Optional, List

from backend.agents.base_agent import BaseAgent, ExecuteSkillType
from backend.models.model_router import ModelRouter
from backend.memory.base_memory import BaseMemory
from backend.skills import SkillError # Import SkillError for exception handling

# Logger setup is handled by BaseAgent for each instance

class ResearchAgent(BaseAgent):
    """
    An agent specialized in researching topics, gathering information from the web,
    summarizing findings, and synthesizing knowledge.
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are a meticulous and resourceful Research Agent. Your primary goal is to "
        "find accurate and relevant information on given topics using available tools, "
        "summarize key findings clearly, and cite sources where possible. "
        "Be objective and thorough in your research."
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
        """
        Initializes the ResearchAgent.
        """
        super().__init__(
            agent_id=agent_id,
            agent_name="ResearchAgent", # Specific name
            model_router=model_router,
            agent_memory=agent_memory,
            execute_skill_func=execute_skill_func,
            config=config,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )
        # Research-specific config could go here
        self.config.setdefault('default_search_results', 5)
        self.config.setdefault('summarize_results', True)
        self.config.setdefault('max_summary_sources', 3) # Max sources to use for summary
        self.log.info("ResearchAgent initialized.")

    async def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Executes a research task for the given query.

        Args:
            query: The research topic or question.
            **kwargs: Additional context:
                - num_results (int): Number of search results to fetch.
                - summarize (bool): Whether to summarize the findings.
                - target_search_model: Specific settings for search (e.g., location).
                - target_summary_model (Optional[str]): Preferred model for summarization.
                - Other LLM params (e.g., temperature).

        Returns:
            A dictionary containing the research results, e.g.,
            {"status": "success", "query": query, "results": [...], "summary": "..."}
            or {"status": "error", "message": "error details"}.
        """
        self.log.info(f"Received research task for query: {query[:150]}...")
        result: Dict[str, Any] = {'status': 'pending', 'query': query}
        search_results: List[Dict[str, Any]] = []
        summary: Optional[str] = None

        num_search = kwargs.get('num_results', self.config['default_search_results'])
        should_summarize = kwargs.get('summarize', self.config['summarize_results'])
        summary_model = kwargs.get('target_summary_model', 'gemini') # Default summary model
        search_kwargs = kwargs.get('target_search_model', {}) # Pass dict for search params
        llm_kwargs = {k:v for k,v in kwargs.items() if k not in ['num_results', 'summarize', 'target_summary_model', 'target_search_model']}


        try:
            # 1. Perform Web Search
            self.log.debug(f"Calling web.search skill for query '{query}' (num_results={num_search}).")
            search_results = await self._use_skill(
                skill_name="web.search",
                query=query,
                num_results=num_search,
                **search_kwargs
            )
            result['search_results'] = search_results
            await self._remember(f"search_{query[:30]}", search_results, {"query": query})

            # 2. Optional: Summarize Findings
            if should_summarize and search_results:
                self.log.debug(f"Calling text.summarize skill using top {self.config['max_summary_sources']} results.")
                # Create text input from top N search results
                text_to_summarize = ""
                source_urls = []
                for i, res in enumerate(search_results[:self.config['max_summary_sources']]):
                    text_to_summarize += f"Source {i+1} ({res.get('url', 'N/A')}):\nTitle: {res.get('title', 'N/A')}\nSnippet: {res.get('snippet', 'N/A')}\n\n"
                    if res.get('url'): source_urls.append(res['url'])

                if text_to_summarize:
                    summary = await self._use_skill(
                        skill_name="text.summarize",
                        text=text_to_summarize,
                        summary_length="detailed paragraph", # Request a good summary
                        target_model=summary_model,
                        # Pass model_router implicitly via _use_skill helper
                        **llm_kwargs
                    )
                    result['summary'] = summary
                    await self._remember(f"summary_{query[:30]}", summary, {"query": query, "sources": source_urls})
                else:
                    self.log.warning("No text content found in search results to summarize.")
                    result['summary'] = "Could not generate summary: No content found in search results."

            elif should_summarize:
                 self.log.warning("Summarization requested but no search results found.")
                 result['summary'] = "Could not generate summary: No search results found."


            # --- Finalization ---
            result['status'] = 'success'
            self.log.info(f"Research task for '{query[:50]}...' completed successfully.")
            # Store the final combined result
            await self._remember(f"research_{query[:30]}", result, {"query": query, "status": "success", "summary_generated": should_summarize})
            return result

        # --- Error Handling ---
        except SkillError as se:
            self.log.error(f"Research task failed due to skill error: {se}", exc_info=False)
            result['status'] = 'error'
            result['error'] = f"Skill Error: {se}"
            await self._remember(f"error_research_{query[:30]}", result, {"query": query, "status": "error"})
            # Decide whether to return the error dict or raise
            # return result
            raise se # Re-raise skill errors for now

        except Exception as e:
            self.log.exception(f"Unexpected error during research task execution: {e}", exc_info=True)
            result['status'] = 'error'
            result['error'] = f"Unexpected Agent Error: {type(e).__name__} - {e}"
            await self._remember(f"error_research_{query[:30]}", result, {"query": query, "status": "error"})
            raise SkillError(f"ResearchAgent unexpected error: {e}") from e
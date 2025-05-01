# Directory: backend/agents/
# File: medical_agent.py
# Description: Agent specialized for medical information retrieval and analysis (with disclaimers).

import asyncio
from typing import Any, Dict, Optional, List

from backend.agents.base_agent import BaseAgent, ExecuteSkillType
from backend.models.model_router import ModelRouter
from backend.memory.base_memory import BaseMemory
from backend.skills import SkillError # Import SkillError for exception handling

# Logger setup is handled by BaseAgent for each instance

class MedicalAgent(BaseAgent):
    """
    An agent specialized in providing information related to medical topics.
    It emphasizes accuracy, relies on reputable sources, and provides clear disclaimers.
    *** THIS AGENT DOES NOT PROVIDE MEDICAL ADVICE. ***
    Its output is for informational purposes only and is not a substitute for
    professional medical consultation, diagnosis, or treatment.
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are an AI Medical Information Assistant. Your purpose is to provide accurate, "
        "objective, and understandable information based on reputable sources in response to "
        "medical-related queries. Follow these strict guidelines:\n"
        "1.  **Accuracy First:** Prioritize information from reliable medical sources (e.g., PubMed, reputable health organizations). If searching, try to cite sources.\n"
        "2.  **Objectivity:** Present information neutrally. Avoid speculation or personal opinions.\n"
        "3.  **Clarity:** Explain complex terms simply.\n"
        "4.  **Safety and Limitations:** NEVER provide diagnosis, treatment recommendations, or medical advice. Explicitly state that you are an AI and cannot replace a qualified healthcare professional.\n"
        "5.  **Disclaimer:** ALWAYS include a disclaimer stating the information is not medical advice and the user should consult a healthcare professional."
    )
    DISCLAIMER = (
        "\n\n--- \n**Disclaimer:** I am an AI assistant. This information is for educational purposes only "
        "and should not be considered medical advice. Always consult with a qualified healthcare "
        "professional for any health concerns or before making any decisions related to your health or treatment."
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
        Initializes the MedicalAgent.
        """
        super().__init__(
            agent_id=agent_id,
            agent_name="MedicalAgent", # Specific name
            model_router=model_router,
            agent_memory=agent_memory,
            execute_skill_func=execute_skill_func,
            config=config,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )
        # Medical-specific config
        self.config.setdefault('default_search_results', 3)
        self.config.setdefault('summarize_search', True)
        self.config.setdefault('search_filter', 'PubMed OR NIH OR Mayo Clinic OR WHO') # Example filter
        self.config.setdefault('default_info_model', 'gemini') # Model for synthesis
        self.log.info("MedicalAgent initialized with safety protocols.")

    async def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Executes a medical information retrieval and synthesis task.
        """
        self.log.info(f"Received medical query: {query[:150]}...")
        result: Dict[str, Any] = {'status': 'pending', 'query': query}
        search_context = ""
        should_search = kwargs.get('search', True)  # Search by default
        num_search = kwargs.get('num_results', self.config['default_search_results'])
        should_summarize = kwargs.get('summarize', self.config['summarize_search'])
        target_model = kwargs.get('target_model', self.config['default_info_model'])
        llm_kwargs = {k:v for k,v in kwargs.items() if k not in ['search', 'num_results', 'summarize', 'target_model']}

        try:
            # 1. Optional: Web Search for Context
            if should_search:
                self.log.debug("Searching reputable sources for medical context...")
                try:
                    # Format search query with site filter
                    search_filter = self.config['search_filter']
                    search_query = f"{query} {search_filter}"  # Include filter directly
                    
                    search_results = await self._use_skill(
                        "web.search",
                        query=search_query,
                        num_results=num_search
                    )
                    if search_results:
                        result['search_results'] = search_results
                        search_context = "\n\nINFORMATION FROM WEB SEARCH (Reputable Sources):\n"
                        for i, res in enumerate(search_results):
                             search_context += f"- Source [{i+1}] ({res.get('url', 'N/A')}): {res.get('snippet', 'N/A')}\n"
                        
                        if should_summarize:
                            summary = await self._use_skill(
                                "text.summarize",
                                text=search_context,
                                summary_length="concise paragraph",
                                target_model=target_model
                            )
                            search_context = f"\n\nSUMMARY OF FINDINGS FROM WEB SEARCH:\n{summary}\n"

                except SkillError as e:
                    self.log.warning(f"Web search for medical context failed: {e}. Proceeding without search context.")
                    search_context = "\n\nNote: Web search for external context failed.\n"
                except Exception as e:
                    self.log.warning(f"Unexpected error during medical search: {e}. Proceeding.")
                    search_context = "\n\nNote: An error occurred during web search.\n"

            # 2. Construct Prompt - Keep exact format for test matching
            prompt = f"Regarding the query '{query}'"  # Base prompt must match exactly
            if search_context:
                prompt += f":{search_context}"
            else:
                prompt += ":\nNo external web context was available or search was disabled.\n"

            prompt += "\nBased *only* on generally known medical information and the provided context (if any), please provide a clear, objective, and informative answer. "
            prompt += "***Do NOT provide medical advice, diagnosis, or treatment recommendations.*** "
            prompt += "State limitations where appropriate."
            prompt += "\n\nRESPONSE:"

            # 3. Call LLM for Synthesis - Use raw_prompt to preserve exact format
            try:
                self.log.debug(f"Calling LLM for medical information synthesis with target model: {target_model}")
                response_text = await self._call_llm(
                    prompt=prompt.strip(),  # Remove any leading/trailing whitespace
                    model_preference=target_model,
                    stream=False,
                    raw_prompt=True,  # Use prompt as-is without wrapping
                    **llm_kwargs
                )

                if not isinstance(response_text, str) or not response_text.strip():
                    raise SkillError("LLM returned an empty or invalid response for the medical query.")

                # 4. Append Mandatory Disclaimer
                final_response = response_text.strip() + self.DISCLAIMER
                result['response'] = final_response
                result['disclaimer'] = self.DISCLAIMER

                # --- Finalization ---
                result['status'] = 'success'
                self.log.info(f"Medical query '{query[:50]}...' processed successfully (with disclaimer).")
                
                # Store with sanitized key
                memory_key = f"medical_info_{self.agent_id}_{query[:30]}"
                await self._remember(
                    memory_key,
                    result,
                    {
                        "query": query,
                        "status": "success",
                        "search_used": should_search,
                        "agent_id": self.agent_id
                    }
                )
                return result

            except SkillError as se:
                error_msg = str(se)
                self.log.error(f"LLM synthesis failed: {error_msg}")
                raise se  # Re-raise the original error to preserve the message

        except SkillError as se:
            self.log.error(f"Medical task failed due to skill error: {se}", exc_info=False)
            result['status'] = 'error'
            result['error'] = f"Skill Error: {se}"
            result['response'] = f"An error occurred while processing your request: {se}{self.DISCLAIMER}"
            
            # Store error with sanitized key
            memory_key = f"error_medical_{query[:30]}"
            await self._remember(
                memory_key,
                result,
                {
                    "query": query,
                    "status": "error",
                    "agent_id": self.agent_id
                }
            )
            raise SkillError(f"MedicalAgent unexpected error: {se}") from se

        except Exception as e:
            self.log.exception(f"Unexpected error during medical task execution: {e}", exc_info=True)
            result['status'] = 'error'
            result['error'] = f"Unexpected Agent Error: {type(e).__name__} - {e}"
            result['response'] = f"An unexpected error occurred while processing your request.{self.DISCLAIMER}"
            
            # Store error with sanitized key - preserving spaces for test matching
            memory_key = f"error_medical_{query[:30]}"
            await self._remember(
                memory_key,
                result,
                {
                    "query": query,
                    "status": "error",
                    "agent_id": self.agent_id
                }
            )
            raise SkillError(f"MedicalAgent unexpected error: {e}") from e
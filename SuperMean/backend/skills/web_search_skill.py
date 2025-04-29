# Directory: backend/skills/
# File: web_search_skill.py
# Description: Skill for performing web searches using SerpApi.

import os
from typing import List, Dict, Any, Optional
import asyncio

# Import the registry and decorator, and SkillError
from backend.skills import register_skill, SkillError
from backend.utils.config_loader import get_settings
from backend.utils.logger import setup_logger

# Attempt to import the search library
try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None # Handle missing dependency gracefully

log = setup_logger(name="web_search_skill")

@register_skill(
    name="web.search",
    description="Performs a web search using SerpApi and returns relevant results.",
    category="web"
)
async def web_search(
    query: str,
    num_results: int = 5,
    api_key: Optional[str] = None,
    # Add other potential SerpApi params like location, hl, gl, etc. as needed
    **kwargs: Any
) -> List[Dict[str, Any]]:
    """
    Performs a web search using the SerpApi service.

    Args:
        query: The search query string.
        num_results: The desired number of results (default: 5). SerpApi might return slightly more or less.
        api_key: Optional SerpApi API key. If None, uses SERPAPI_KEY from settings/environment.
        **kwargs: Additional parameters to pass to the SerpApi GoogleSearch (e.g., location, hl, gl).

    Returns:
        A list of dictionaries, each representing a search result with
        'title', 'url', 'snippet', and potentially 'position'.

    Raises:
        SkillError: If the SerpApi library is not installed or if the search fails.
        ValueError: If the API key is missing.
    """
    if GoogleSearch is None:
        log.error("SerpApi library not installed. Please run 'pip install google-search-results'.")
        raise SkillError("Required library 'google-search-results' is not installed.")

    log.info(f"Performing web search for: '{query[:100]}...', requesting {num_results} results.")

    # Get API key
    resolved_api_key = api_key
    if not resolved_api_key:
        settings = get_settings()
        resolved_api_key = settings.SERPAPI_KEY
        log.debug("Loaded SerpApi key from settings.")

    if not resolved_api_key:
        log.error("SerpApi API key is missing.")
        raise ValueError("SerpApi key not found in arguments or environment settings (SERPAPI_KEY).")

    # Prepare search parameters
    search_params = {
        "q": query,
        "api_key": resolved_api_key,
        "num": str(num_results), # SerpApi expects num as string
        **kwargs # Include any extra parameters passed
    }
    log.debug(f"SerpApi search parameters: { {k:v for k,v in search_params.items() if k != 'api_key'} }") # Don't log key

    try:
        # SerpApi client library is synchronous, run in executor for async context
        loop = asyncio.get_running_loop()
        search = GoogleSearch(search_params)
        # Run the synchronous get_dict() method in an executor
        results_dict = await loop.run_in_executor(None, search.get_dict)

        # Process results
        processed_results = []
        # Handle potential errors returned in the dictionary
        if "error" in results_dict:
             log.error(f"SerpApi returned an error: {results_dict['error']}")
             raise SkillError(f"SerpApi search failed: {results_dict['error']}")

        organic_results = results_dict.get("organic_results", [])

        for result in organic_results:
            processed_results.append({
                "title": result.get("title", ""),
                "url": result.get("link", ""), # Use 'link' for the URL
                "snippet": result.get("snippet", ""),
                "position": result.get("position"),
                "source": "web_search" # Indicate source
            })
            if len(processed_results) >= num_results:
                 break # Stop if we have enough results

        # Include answer box if present and no organic results found
        if not processed_results and "answer_box" in results_dict:
            log.debug("No organic results, using answer box.")
            answer = results_dict["answer_box"]
            answer_snippet = answer.get("snippet", answer.get("answer"))
            if isinstance(answer_snippet, list): # Sometimes snippet is a list
                answer_snippet = " ".join(answer_snippet)

            processed_results.append({
                "title": answer.get("title", "Featured Answer"),
                "url": answer.get("link"), # Might be None
                "snippet": answer_snippet,
                "position": 0, # Indicate it's a top answer/featured snippet
                "source": "featured_snippet"
            })

        log.info(f"Web search for '{query[:50]}...' returned {len(processed_results)} results.")
        return processed_results

    except Exception as e:
        log.exception(f"Error during SerpApi web search for '{query[:50]}...': {e}", exc_info=True)
        raise SkillError(f"Web search failed: {e}") from e
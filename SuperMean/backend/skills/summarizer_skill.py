# Directory: backend/skills/
# File: summarizer_skill.py
# Description: Skill for summarizing text using an LLM.

import asyncio
from typing import Optional, Dict, Any

# Import the registry and decorator
from backend.skills import register_skill, SkillError
from backend.models.model_router import ModelRouter # Assuming ModelRouter is accessible
from backend.utils.logger import setup_logger

log = setup_logger(name="summarizer_skill")

@register_skill(
    name="text.summarize",
    description="Summarizes a given piece of text.",
    category="text"
)
async def summarize_text(
    text: str,
    model_router: ModelRouter, # Pass router as argument
    summary_length: str = "concise", # e.g., "concise", "medium", "detailed paragraph"
    target_model: Optional[str] = "gemini", # Default to a suitable model like Gemini
    **model_kwargs: Any # Pass extra args to the model (temperature, etc.)
) -> str:
    """
    Uses an LLM via the ModelRouter to summarize the input text.

    Args:
        text: The text content to be summarized.
        model_router: An instance of the ModelRouter to interact with LLMs.
        summary_length: A hint for the desired length/style of the summary.
        target_model: The preferred model/connector key for the ModelRouter (e.g., "gemini", "aimlapi:gpt-3.5-turbo").
        **model_kwargs: Additional keyword arguments for the LLM generation.

    Returns:
        The generated summary as a string.

    Raises:
        SkillError: If summarization fails.
    """
    if not text or not text.strip():
         log.warning("Summarization skill called with empty text.")
         return "" # Return empty string for empty input

    log.info(f"Summarizing text (length hint: {summary_length}). First 100 chars: {text[:100]}...")

    # Construct a prompt for summarization
    prompt = f"Please provide a {summary_length} summary of the following text:\n\n"
    prompt += f"TEXT:\n```\n{text}\n```\n\n"
    prompt += f"SUMMARY ({summary_length}):"

    model_preference = target_model

    try:
        log.debug(f"Calling model router with preference: {model_preference}")
        summary = await model_router.generate(
            prompt=prompt,
            model_preference=model_preference,
            stream=False, # Summarization usually better non-streamed
            **model_kwargs
        )

        if not isinstance(summary, str) or not summary.strip():
            log.warning(f"Summarization returned empty or non-string result for text starting with '{text[:50]}...'")
            raise SkillError("LLM returned an empty or invalid response for summarization.")

        log.info(f"Successfully generated summary.")
        return summary.strip()

    except Exception as e:
        log.exception(f"Summarization failed for text starting with '{text[:50]}...': {e}", exc_info=True)
        # Re-raise as SkillError for consistent handling
        raise SkillError(f"Summarization failed: {e}") from e
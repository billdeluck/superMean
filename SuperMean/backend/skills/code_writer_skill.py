# Directory: backend/skills/
# File: code_writer_skill.py
# Description: Skill for generating code based on descriptions using an LLM.

import asyncio
from typing import Optional, Dict, Any

# Import the registry and decorator
from backend.skills import register_skill, SkillError
from backend.models.model_router import ModelRouter # Assuming ModelRouter is accessible
from backend.utils.logger import setup_logger

log = setup_logger(name="code_writer_skill")

# --- Dependency: Model Router Instance ---
# In a real application, the router would likely be injected or accessed via a context.
# For now, we might instantiate it here or assume it's passed as an argument.
# Let's design the skill to accept it as an argument for better testability.

@register_skill(
    name="code.write",
    description="Generates code based on a natural language description, language specification, and optional context.",
    category="code"
)
async def generate_code(
    description: str,
    language: str,
    model_router: ModelRouter, # Pass router as argument
    context: Optional[str] = None,
    target_model: Optional[str] = "deepseek", # Default to deepseek-coder or other preferred model via router
    **model_kwargs: Any # Pass extra args to the model (temperature, etc.)
) -> str:
    """
    Uses an LLM via the ModelRouter to generate code.

    Args:
        description: Natural language description of the code's purpose.
        language: The programming language for the code (e.g., "python", "javascript").
        model_router: An instance of the ModelRouter to interact with LLMs.
        context: Optional existing code or context to modify or build upon.
        target_model: The preferred model/connector key for the ModelRouter
                      (e.g., "deepseek", "aimlapi:gpt-4o"). Should ideally be a coder model.
        **model_kwargs: Additional keyword arguments for the LLM generation (e.g., temperature).

    Returns:
        The generated code block as a string.

    Raises:
        SkillError: If code generation fails.
    """
    log.info(f"Generating {language} code for: {description[:100]}...")

    # Construct a detailed prompt for the LLM
    prompt = f"You are an expert {language} programmer. Generate clean, efficient, and well-commented {language} code that performs the following task:\n\n"
    prompt += f"TASK DESCRIPTION:\n{description}\n\n"
    if context:
        prompt += f"EXISTING CODE CONTEXT / TO BE MODIFIED:\n```\n{context}\n```\n\n"
    prompt += f"LANGUAGE: {language}\n\n"
    prompt += f"Please provide only the generated {language} code block, without any introductory phrases, explanations, or markdown formatting outside the code block itself."
    # Add constraints if needed: e.g., "Ensure the code is compatible with Python 3.9+."

    # Define preferred coder model via target_model parameter
    # Example: "deepseek" (if deepseek connector uses deepseek-coder by default)
    # Or "aimlapi:deepseek-coder" or "aimlapi:gpt-4o" etc.
    model_preference = target_model

    try:
        log.debug(f"Calling model router with preference: {model_preference}")
        generated_code = await model_router.generate(
            prompt=prompt,
            model_preference=model_preference,
            stream=False, # Code generation usually better non-streamed
            **model_kwargs
        )

        if not isinstance(generated_code, str) or not generated_code.strip():
            log.warning(f"Code generation returned empty or non-string result for '{description[:50]}...'")
            raise SkillError("LLM returned an empty or invalid response for code generation.")

        # Basic cleanup (remove potential markdown fences sometimes added by models)
        if generated_code.strip().startswith(f"```{language}"):
             generated_code = generated_code.split("\n", 1)[1]
        if generated_code.strip().startswith("```"):
             generated_code = generated_code.strip()[3:]
        if generated_code.strip().endswith("```"):
             generated_code = generated_code.strip()[:-3]

        log.info(f"Successfully generated {language} code snippet.")
        return generated_code.strip()

    except Exception as e:
        log.exception(f"Code generation failed for '{description[:50]}...': {e}", exc_info=True)
        # Re-raise as SkillError for consistent handling
        raise SkillError(f"Code generation failed: {e}") from e
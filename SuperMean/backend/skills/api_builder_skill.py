# Directory: backend/skills/
# File: api_builder_skill.py
# Description: Skill for generating basic FastAPI endpoints based on descriptions.

import asyncio
from typing import Optional, Dict, Any

# Import the registry and decorator
from backend.skills import register_skill, SkillError
from backend.models.model_router import ModelRouter # Assuming ModelRouter is accessible
from backend.utils.logger import setup_logger

log = setup_logger(name="api_builder_skill")

@register_skill(
    name="api.build",
    description="Generates basic FastAPI code (schemas, router, CRUD endpoints) based on a description.",
    category="code"
)
async def build_fastapi_endpoint(
    description: str,
    resource_name: str, # e.g., "product", "user", "task"
    fields: Dict[str, str], # e.g., {"name": "str", "price": "float", "is_available": "bool"}
    model_router: ModelRouter, # Pass router as argument
    target_model: Optional[str] = "deepseek", # Default to a coder model if available
    **model_kwargs: Any # Pass extra args to the model (temperature, etc.)
) -> str:
    """
    Uses an LLM via the ModelRouter to generate basic FastAPI code for a resource.

    Args:
        description: Natural language description of the API's purpose and the resource.
        resource_name: The singular name of the resource (e.g., "product").
        fields: A dictionary defining the fields and their types for the resource's schema.
                Types should be simple Python types (str, int, float, bool) or Pydantic types.
        model_router: An instance of the ModelRouter to interact with LLMs.
        target_model: The preferred model/connector key for the ModelRouter (e.g., "deepseek", "aimlapi:gpt-4o").
        **model_kwargs: Additional keyword arguments for the LLM generation.

    Returns:
        The generated FastAPI code (schemas, router, basic endpoints) as a single string.

    Raises:
        SkillError: If API code generation fails.
    """
    log.info(f"Generating FastAPI code for resource '{resource_name}' described as: {description[:100]}...")

    # Construct a detailed prompt for the LLM
    field_definitions = "\n".join([f"    {name}: {type_hint}" for name, type_hint in fields.items()])
    resource_class_name = resource_name.capitalize()
    router_tag = resource_name.lower() + "s" # e.g., "products"

    prompt = f"""
You are an expert FastAPI developer using modern Python practices (Python 3.9+, Pydantic v2).
Generate the necessary Python code for a basic CRUD API endpoint for a resource named '{resource_name}'.

TASK DESCRIPTION:
{description}

RESOURCE DETAILS:
- Resource Name (singular): {resource_name}
- Resource Class Name: {resource_class_name}
- Fields and Types:
{field_definitions}

REQUIREMENTS:
1.  **Schemas:** Create Pydantic models (using `from pydantic import BaseModel, Field`) for:
    - `{resource_class_name}Base`: Contains all common fields.
    - `{resource_class_name}Create`: Inherits from Base, used for creating new resources.
    - `{resource_class_name}` (Read): Inherits from Base, includes an 'id' field (e.g., `id: int | str`).
2.  **Router:** Create a FastAPI `APIRouter` (using `from fastapi import APIRouter, Depends, HTTPException`).
    - Use the tag '{router_tag}'.
    - Define a simple in-memory dictionary storage for this example (e.g., `db_{router_tag}: Dict[int, Any] = {{}}`). Add a simple ID counter.
3.  **Endpoints:** Implement basic CRUD endpoints within the router:
    - `POST /{router_tag}/`: Creates a new {resource_name}. Takes `{resource_class_name}Create` as input, returns the created `{resource_class_name}` with an ID.
    - `GET /{router_tag}/`: Returns a list of all {resource_name}s (returns `List[{resource_class_name}]`). Add optional `skip` and `limit` query parameters.
    - `GET /{router_tag}/{{item_id}}`: Returns a specific {resource_name} by ID (returns `{resource_class_name}`). Handle 404 errors.
    - `PUT /{router_tag}/{{item_id}}`: Updates a specific {resource_name}. Takes `{resource_class_name}Create` as input (or a dedicated Update schema), returns the updated `{resource_class_name}`. Handle 404 errors.
    - `DELETE /{router_tag}/{{item_id}}`: Deletes a specific {resource_name}. Returns a confirmation message. Handle 404 errors.
4.  **Imports:** Include all necessary imports from `fastapi`, `pydantic`, and `typing`.
5.  **Code Only:** Provide only the complete Python code block. Do not include explanations, introductions, or markdown formatting outside the code. Ensure the code is fully functional and runnable.
"""

    model_preference = target_model

    try:
        log.debug(f"Calling model router with preference: {model_preference}")
        generated_code = await model_router.generate(
            prompt=prompt,
            model_preference=model_preference,
            stream=False,
            **model_kwargs
        )

        if not isinstance(generated_code, str) or not generated_code.strip():
            log.warning(f"API Builder returned empty or non-string result for '{resource_name}'")
            raise SkillError("LLM returned an empty or invalid response for API generation.")

        # Basic cleanup (remove potential markdown fences sometimes added by models)
        if generated_code.strip().startswith("```python"):
             generated_code = generated_code.split("\n", 1)[1]
        if generated_code.strip().startswith("```"):
             generated_code = generated_code.strip()[3:]
        if generated_code.strip().endswith("```"):
             generated_code = generated_code.strip()[:-3]

        log.info(f"Successfully generated FastAPI code for resource '{resource_name}'.")
        return generated_code.strip()

    except Exception as e:
        log.exception(f"API Builder failed for resource '{resource_name}': {e}", exc_info=True)
        # Re-raise as SkillError for consistent handling
        raise SkillError(f"API Builder skill failed: {e}") from e
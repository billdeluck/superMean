# Directory: backend/skills/
# File: __init__.py
# Description: Initializes the skill system, registry, and core functions. (Parameter Rename Fix)

import asyncio
import functools
import importlib
import inspect
import pkgutil
import typing
from typing import Any, Callable, Dict, List, Optional, Union

from backend.utils.logger import setup_logger

log = setup_logger(name="skills_registry")

# Central registry for skills
# Format: {"skill_name": {"function": callable (original), "wrapper": awaitable, "metadata": dict}}
_skills_registry: Dict[str, Dict[str, Any]] = {}


class SkillError(Exception):
    """Custom exception for skill-related errors."""
    pass


def _get_type_name(annotation: Any) -> str:
    """Helper to get a clean string representation of a type hint."""
    if annotation == inspect.Parameter.empty or annotation == inspect.Signature.empty:
        return "Any"

    if getattr(annotation, "__origin__", None) is Union:
        args = getattr(annotation, "__args__", ())
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1 and type(None) in args:
            return f"Optional[{_get_type_name(non_none_args[0])}]"
        return f"Union[{', '.join(_get_type_name(arg) for arg in args)}]"

    origin = getattr(annotation, "__origin__", None)
    if origin:
        args = getattr(annotation, "__args__", [])
        args_repr = ", ".join([_get_type_name(arg) for arg in args])
        origin_name = getattr(origin, "__name__", None) or getattr(origin, "_name", None) or str(origin)
        return f"{origin_name}[{args_repr}]"

    if hasattr(annotation, "__name__"):
        return annotation.__name__

    return str(annotation).replace("typing.", "")


def register_skill(name: Optional[str] = None, description: str = "", category: str = "general", **kwargs):
    """
    Decorator to register a function as a skill. Wraps both sync and async functions
    into an awaitable wrapper for consistent calling via execute_skill.
    """
    def decorator(func: Callable):
        skill_name = name or func.__name__
        if skill_name in _skills_registry:
            log.warning(f"Skill '{skill_name}' is being redefined.")

        is_async = asyncio.iscoroutinefunction(func)

        sig = inspect.signature(func)
        params = []
        for param_name, param in sig.parameters.items():
            param_info = {
                "name": param_name,
                "type": _get_type_name(param.annotation),
                "required": param.default == inspect.Parameter.empty
            }
            if param.default != inspect.Parameter.empty:
                 param_info["default"] = param.default # Store actual default value
            params.append(param_info)

        metadata = {
            "description": description or inspect.getdoc(func) or "No description provided.",
            "category": category,
            "parameters": params,
            "return_type": _get_type_name(sig.return_annotation),
            "is_async": is_async,
            **kwargs
        }

        @functools.wraps(func)
        async def wrapper(*w_args, **w_kwargs):
            # This wrapper receives arguments intended for the original function 'func'
            log.debug(f"Executing skill '{skill_name}' via wrapper with args: {w_args}, kwargs: {w_kwargs}")
            try:
                if is_async:
                    result = await func(*w_args, **w_kwargs)
                else:
                    loop = asyncio.get_running_loop()
                    sync_call = functools.partial(func, *w_args, **w_kwargs)
                    result = await loop.run_in_executor(None, sync_call)
                log.debug(f"Skill '{skill_name}' execution finished.")
                return result
            except Exception as e:
                 log.exception(f"Error during execution of skill '{skill_name}': {e}", exc_info=True)
                 raise e

        _skills_registry[skill_name] = {
            "function": func,
            "wrapper": wrapper,
            "metadata": metadata
        }
        log.debug(f"Registered skill: '{skill_name}'")
        return func
    return decorator

# --- RENAMED first parameter from 'name' to 'skill_name' ---
async def execute_skill(skill_name: str, *args, **kwargs) -> Any:
    """
    Retrieves and executes the awaitable wrapper for a registered skill.

    Args:
        skill_name: The name of the skill to call (e.g., "test.greet").
        *args: Positional arguments for the skill function.
        **kwargs: Keyword arguments for the skill function (e.g., name="Tester").

    Returns:
        The result of the skill function execution.

    Raises:
        SkillError: If the skill is not found or if execution fails.
    """
    # Use the renamed parameter 'skill_name' internally
    log.debug(f"Attempting to execute skill: '{skill_name}' with args: {args}, kwargs: {kwargs}")
    if skill_name not in _skills_registry:
        log.error(f"Skill '{skill_name}' not found in registry.")
        raise SkillError(f"Skill '{skill_name}' not found.")

    skill_info = _skills_registry[skill_name]
    wrapper_func = skill_info["wrapper"] # Get the awaitable wrapper

    try:
        # Await the wrapper, passing the arguments (*args, **kwargs) intended for the *target* skill.
        # The variable 'skill_name' from this function's scope is distinct now.
        result = await wrapper_func(*args, **kwargs)
        return result
    except Exception as e:
        # Catch errors from the wrapper's execution
        raise SkillError(f"Execution failed for skill '{skill_name}': {e}") from e

def list_skills(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists available skills, optionally filtered by category."""
    results = []
    for name, info in _skills_registry.items():
        if category is None or info["metadata"].get("category") == category:
            results.append({
                "name": name,
                "metadata": info["metadata"]
            })
    return results

def get_skill_metadata(name: str) -> Optional[Dict[str, Any]]:
    """Retrieves the metadata for a specific skill."""
    skill_info = _skills_registry.get(name)
    return skill_info["metadata"] if skill_info else None

def load_skills(package_path: str = __name__, reload: bool = False):
    """Automatically discovers and loads skills from modules within a package."""
    log.info(f"Autoloading skills from package: {package_path}")
    try:
        package = importlib.import_module(package_path)
    except ImportError as e:
        log.error(f"Could not import package '{package_path}' for skill loading: {e}")
        return

    prefix = package.__name__ + "."
    module_paths = getattr(package, "__path__", [])
    if not isinstance(module_paths, list):
        log.warning(f"Package path for {package_path} is not a standard list. Skipping skill loading.")
        return

    for _, module_name, is_pkg in pkgutil.walk_packages(module_paths, prefix):
        if not is_pkg:
            try:
                module = importlib.import_module(module_name)
                if reload:
                    importlib.reload(module)
                log.debug(f"Loaded module for skills: {module_name}")
            except ImportError as e:
                log.error(f"Failed to import skill module '{module_name}': {e}")
            except Exception as e:
                 log.exception(f"Error loading module {module_name}: {e}", exc_info=True)
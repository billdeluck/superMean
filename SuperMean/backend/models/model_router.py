# Directory: backend/models/
# File: model_router.py
# Description: Routes generation requests to the appropriate model connector.

import asyncio
from typing import Any, Dict, Optional, List, AsyncGenerator

from backend.models.base_model import BaseModelConnector
from backend.models.gemini_connector import GeminiConnector
from backend.models.deepseek_connector import DeepSeekConnector
from backend.models.aimlapi_connector import RouterApiConnector as AimlApiConnector # Rename import
from backend.models.router_api_connector import RouterApiConnector # Placeholder

from backend.utils.config_loader import get_settings, Settings
from backend.utils.logger import setup_logger
from backend.utils.error_handler import ModelConnectionError, ConfigurationError

log = setup_logger(name="model_router")

class ModelRouter:
    """
    Manages multiple model connectors and routes generation requests.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initializes the ModelRouter and loads configured connectors.

        Args:
            settings: Optional pre-loaded settings object. If None, loads settings internally.
        """
        self.settings = settings or get_settings()
        self.connectors: Dict[str, BaseModelConnector] = {}
        self._initialize_connectors()

        # Define fallback chain from settings or use a default
        # Example setting: MODEL_FALLBACK_CHAIN="gemini,aimlapi:gpt-4o,deepseek"
        fallback_setting = getattr(self.settings, 'MODEL_FALLBACK_CHAIN', "gemini,deepseek") # Default if not set
        self.fallback_chain: List[str] = [m.strip() for m in fallback_setting.split(',') if m.strip()]
        log.info(f"Model fallback chain configured: {self.fallback_chain}")


    def _initialize_connectors(self):
        """Initializes connectors based on available API keys in settings."""
        log.info("Initializing available model connectors...")

        # Gemini
        if self.settings.GEMINI_API_KEY:
            try:
                self.connectors["gemini"] = GeminiConnector(settings=self.settings)
                log.info("GeminiConnector initialized.")
            except Exception as e:
                log.error(f"Failed to initialize GeminiConnector: {e}", exc_info=True)
        else:
            log.warning("Skipping GeminiConnector initialization: GEMINI_API_KEY not found.")

        # DeepSeek
        if self.settings.DEEPSEEK_API_KEY:
            try:
                self.connectors["deepseek"] = DeepSeekConnector(settings=self.settings)
                log.info("DeepSeekConnector initialized.")
            except Exception as e:
                log.error(f"Failed to initialize DeepSeekConnector: {e}", exc_info=True)
        else:
             log.warning("Skipping DeepSeekConnector initialization: DEEPSEEK_API_KEY not found.")

        # AIMLAPI (as a specific router implementation)
        if self.settings.AIMLAPI_KEY:
            try:
                # Use a key like 'aimlapi' to distinguish it
                self.connectors["aimlapi"] = AimlApiConnector(settings=self.settings)
                log.info("AimlApiConnector initialized.")
            except Exception as e:
                log.error(f"Failed to initialize AimlApiConnector: {e}", exc_info=True)
        else:
            log.warning("Skipping AimlApiConnector initialization: AIMLAPI_KEY not found.")

        # Generic RouterAPI Placeholder
        if self.settings.ROUTERAPI_KEY:
            try:
                 # Use a key like 'routerapi'
                self.connectors["routerapi"] = RouterApiConnector(settings=self.settings)
                log.info("RouterApiConnector (placeholder) initialized.")
            except Exception as e:
                log.error(f"Failed to initialize RouterApiConnector placeholder: {e}", exc_info=True)
        else:
             log.warning("Skipping RouterApiConnector placeholder initialization: ROUTERAPI_KEY not found.")

        if not self.connectors:
            log.error("No model connectors were successfully initialized. Check API keys and configurations.")
            # Depending on requirements, either raise an error or allow operation without models
            # raise ConfigurationError("No LLM connectors could be initialized.")

        log.info(f"Initialized connectors: {list(self.connectors.keys())}")

    def get_available_models(self) -> List[str]:
        """Returns a list of keys for the initialized connectors."""
        return list(self.connectors.keys())

    async def generate(
        self,
        prompt: str,
        model_preference: Optional[str] = None, # e.g., "gemini", "deepseek", "aimlapi:gpt-4o"
        stream: bool = False,
        **kwargs
    ) -> str | AsyncGenerator[str, None]:
        """
        Routes the generation request to the preferred or fallback model connector.

        Args:
            prompt: The input prompt.
            model_preference: The preferred model/connector key. Can include specific sub-model
                              after a colon (e.g., "aimlapi:gpt-4o").
            stream: Whether to stream the response.
            **kwargs: Additional arguments for the specific model connector's generate method.

        Returns:
            The generated string or an async generator for streaming responses.

        Raises:
            ModelConnectionError: If no suitable model could generate a response after trying fallbacks.
            ValueError: If the preferred model format is invalid or the connector is not found.
        """
        target_connector: Optional[BaseModelConnector] = None
        connector_key: Optional[str] = None
        model_override: Optional[str] = None # For routers like AIMLAPI

        if model_preference:
            log.info(f"Attempting generation with preference: {model_preference}")
            if ":" in model_preference:
                connector_key, model_override = model_preference.split(":", 1)
            else:
                connector_key = model_preference

            if connector_key in self.connectors:
                target_connector = self.connectors[connector_key]
                # Pass the specific model if needed (for routers)
                if model_override and connector_key in ["aimlapi", "routerapi"]: # Add other router keys if needed
                    kwargs["model"] = model_override
            else:
                log.warning(f"Preferred connector '{connector_key}' not available or initialized.")
                # Proceed to fallback chain

        # If no preference or preferred connector failed/unavailable, try fallback chain
        if not target_connector:
            log.info(f"No valid preference or preferred connector unavailable. Trying fallback chain: {self.fallback_chain}")
            for fallback_key_pref in self.fallback_chain:
                connector_key_fallback: Optional[str] = None
                model_override_fallback: Optional[str] = None
                if ":" in fallback_key_pref:
                    connector_key_fallback, model_override_fallback = fallback_key_pref.split(":", 1)
                else:
                    connector_key_fallback = fallback_key_pref

                if connector_key_fallback in self.connectors:
                    log.debug(f"Trying fallback connector: {connector_key_fallback}")
                    target_connector = self.connectors[connector_key_fallback]
                    # Apply model override if specified in fallback and applicable
                    if model_override_fallback and connector_key_fallback in ["aimlapi", "routerapi"]:
                         kwargs["model"] = model_override_fallback
                    elif "model" in kwargs and connector_key_fallback not in ["aimlapi", "routerapi"]:
                         # Remove model kwarg if the fallback connector doesn't need it
                         del kwargs["model"]

                    try:
                        # Attempt generation with the fallback connector
                        log.info(f"Generating response using fallback connector: {connector_key_fallback} (Model Override: {kwargs.get('model')})")
                        return await target_connector.generate(prompt=prompt, stream=stream, **kwargs)
                    except NotImplementedError as e:
                        log.warning(f"Fallback connector '{connector_key_fallback}' is not implemented: {e}. Trying next fallback.")
                        target_connector = None # Reset to try next fallback
                        continue # Try next in fallback chain
                    except ModelConnectionError as e:
                        log.warning(f"Fallback connector '{connector_key_fallback}' failed: {e}. Trying next fallback.")
                        target_connector = None # Reset to try next fallback
                        continue # Try next in fallback chain
                    except Exception as e:
                        log.exception(f"Unexpected error with fallback connector '{connector_key_fallback}': {e}", exc_info=True)
                        target_connector = None # Reset to try next fallback
                        continue # Try next in fallback chain
                else:
                    log.warning(f"Fallback connector key '{connector_key_fallback}' not available or initialized.")

        # If preferred connector was found initially, try it now
        if target_connector and connector_key:
             try:
                log.info(f"Generating response using preferred connector: {connector_key} (Model Override: {kwargs.get('model')})")
                return await target_connector.generate(prompt=prompt, stream=stream, **kwargs)
             except NotImplementedError as e:
                 log.error(f"Preferred connector '{connector_key}' is not implemented: {e}")
                 # This case shouldn't happen if initialization checks work, but handle defensively
                 raise ModelConnectionError(model_name=connector_key, message=f"Connector not implemented, cannot generate.") from e
             except ModelConnectionError as e:
                log.error(f"Preferred connector '{connector_key}' failed: {e}")
                # Depending on desired behavior, we could try fallbacks even if preference failed,
                # but current logic tries fallbacks *only if preference wasn't found initially*.
                # For simplicity, we raise if the chosen preference fails.
                raise e # Re-raise the specific error
             except Exception as e:
                log.exception(f"Unexpected error with preferred connector '{connector_key}': {e}", exc_info=True)
                raise ModelConnectionError(model_name=connector_key, message=f"Unexpected error: {e}") from e


        # If we reach here, no connector succeeded or was available
        log.error("Failed to generate response: No available or successful model connector found after checking preference and fallbacks.")
        raise ModelConnectionError(model_name="ModelRouter", message="No available model connector succeeded.")
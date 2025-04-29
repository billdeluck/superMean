# Directory: backend/models/
# File: gemini_connector.py
# Description: Connector for Google Gemini models.

import google.generativeai as genai
from typing import Any, Dict, Optional, AsyncGenerator

from backend.models.base_model import BaseModelConnector
from backend.utils.config_loader import get_settings
from backend.utils.logger import setup_logger
from backend.utils.error_handler import ModelConnectionError

log = setup_logger(name="gemini_connector")

class GeminiConnector(BaseModelConnector):
    """
    Connector for interacting with Google Gemini models.
    """

    DEFAULT_MODEL = "gemini-1.5-flash-latest" # Or "gemini-pro" etc.

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, timeout: int = 120, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the Gemini connector.

        Args:
            api_key: Google AI API key. Loaded from settings if not provided.
            model_name: Specific Gemini model to use (e.g., "gemini-1.5-flash-latest", "gemini-pro"). Defaults to DEFAULT_MODEL.
            timeout: Request timeout in seconds (Note: SDK might handle timeouts differently).
            config: Additional configuration for the generative model (e.g., safety_settings).
        """
        super().__init__(api_key=api_key, timeout=timeout, config=config) # Pass timeout, though SDK manages it

        if not self.api_key:
            settings = get_settings()
            self._load_api_key_from_settings(settings, "GEMINI_API_KEY")

        if not self.api_key:
            raise ModelConnectionError(
                model_name="Gemini",
                message="API key for Gemini not found in environment variables (GEMINI_API_KEY) or direct input."
            )

        try:
            genai.configure(api_key=self.api_key)
            self.model_name = model_name or self.DEFAULT_MODEL
            # Apply generation config if provided in the main config dict
            generation_config_dict = self.config.get("generation_config", {})
            safety_settings_dict = self.config.get("safety_settings", None) # Use None for default safety

            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config_dict,
                safety_settings=safety_settings_dict
            )
            log.info(f"Gemini client configured for model: {self.model_name}")
            log.debug(f"Gemini Generation Config: {generation_config_dict}")
            log.debug(f"Gemini Safety Settings: {safety_settings_dict}")

        except Exception as e:
            log.exception(f"Failed to configure Gemini client: {e}", exc_info=True)
            raise ModelConnectionError(model_name="Gemini", message=f"Configuration failed: {e}")

    async def generate(self, prompt: str, stream: bool = False, **kwargs) -> str | AsyncGenerator[str, None]:
        """
        Generates a response from the Gemini model.

        Args:
            prompt: The input text prompt for the model.
            stream: If True, returns an async generator yielding chunks of the response.
                    If False (default), returns the complete response string.
            **kwargs: Additional parameters passed directly to the Gemini API's
                      generate_content method (overrides generation_config).

        Returns:
            If stream=False: The generated response string.
            If stream=True: An async generator yielding response chunks.

        Raises:
            ModelConnectionError: If there's an issue during generation.
        """
        log.debug(f"Generating content with Gemini model: {self.model_name}. Stream={stream}")
        log.debug(f"Prompt (first 100 chars): {prompt[:100]}...")
        log.debug(f"Additional kwargs: {kwargs}")

        # Combine kwargs with model's generation_config, kwargs take precedence
        final_generation_config = self.model.generation_config.to_dict()
        final_generation_config.update(kwargs)
        log.debug(f"Final Generation Config: {final_generation_config}")

        try:
            if stream:
                log.debug("Using streaming generation.")
                async def stream_generator():
                    try:
                        response_stream = await self.model.generate_content_async(
                            prompt,
                            stream=True,
                            generation_config=genai.types.GenerationConfig(**final_generation_config)
                            # safety_settings are part of the model instance
                        )
                        async for chunk in response_stream:
                            if chunk.parts:
                                yield chunk.text
                            # Handle potential errors or empty chunks if necessary
                    except Exception as e:
                        log.exception(f"Error during Gemini streaming generation: {e}", exc_info=True)
                        # Option 1: Raise error within generator
                        raise ModelConnectionError(model_name=self.model_name, message=f"Streaming error: {e}")
                        # Option 2: Yield an error message (less ideal)
                        # yield f"[ERROR: {e}]"
                return stream_generator()
            else:
                log.debug("Using non-streaming generation.")
                response = await self.model.generate_content_async(
                    prompt,
                    stream=False,
                    generation_config=genai.types.GenerationConfig(**final_generation_config)
                    # safety_settings are part of the model instance
                )
                # Handle potential safety blocks or empty responses
                if not response.parts:
                     if response.prompt_feedback.block_reason:
                         msg = f"Gemini generation blocked. Reason: {response.prompt_feedback.block_reason}. Safety Ratings: {response.prompt_feedback.safety_ratings}"
                         log.warning(msg)
                         raise ModelConnectionError(model_name=self.model_name, message=msg)
                     else:
                         msg = "Gemini returned an empty response with no block reason."
                         log.warning(msg)
                         # Decide whether to raise or return empty string
                         # raise ModelConnectionError(model_name=self.model_name, message=msg)
                         return "" # Return empty for now

                log.debug(f"Received non-streaming response from Gemini.")
                return response.text

        except Exception as e:
            # Catch potential API errors, configuration errors, etc.
            log.exception(f"Error during Gemini generation: {e}", exc_info=True)
            raise ModelConnectionError(model_name=self.model_name, message=f"Generation failed: {e}")
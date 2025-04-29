# Directory: backend/models/
# File: aimlapi_connector.py
# Description: Connector for AIMLAPI (api.aimlapi.com/v1) - Logger Init Moved.

import openai # Use the official openai library
from openai import OpenAI, AsyncOpenAI # Import AsyncOpenAI for async operations
from typing import Any, Dict, Optional, AsyncGenerator, List

from backend.models.base_model import BaseModelConnector
from backend.utils.config_loader import get_settings
from backend.utils.logger import setup_logger # Keep the import
from backend.utils.error_handler import ModelConnectionError

# --- Logger initialization MOVED from global scope ---
# log = setup_logger(name="aimlapi_connector") # REMOVED FROM HERE

class AimlApiConnector(BaseModelConnector):
    """
    Connector for interacting with models via the AIMLAPI endpoint (https://api.aimlapi.com/v1),
    which uses an OpenAI-compatible API structure.
    """

    API_BASE_URL = "https://api.aimlapi.com/v1"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 120, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the AIMLAPI connector using the OpenAI client library.
        """
        super().__init__(api_key=api_key, timeout=timeout, config=config)
        self.model_name = "AIMLAPI Router"

        # --- Initialize logger INSTANCE HERE ---
        self.log = setup_logger(name=f"aimlapi_connector.{id(self)}") # Use instance ID for potential uniqueness if needed

        if not self.api_key:
            settings = get_settings()
            self._load_api_key_from_settings(settings, "AIMLAPI_KEY")

        if not self.api_key:
            raise ModelConnectionError(
                model_name=self.model_name,
                message="API key for AIMLAPI not found in environment variables (AIMLAPI_KEY) or direct input."
            )

        try:
            self.client = AsyncOpenAI(
                base_url=self.API_BASE_URL,
                api_key=self.api_key,
                timeout=self.timeout
            )
            self.log.info(f"{self.model_name} connector initialized, using OpenAI client pointed to {self.API_BASE_URL}")

        except Exception as e:
            self.log.exception(f"Failed to configure {self.model_name} client: {e}", exc_info=True)
            raise ModelConnectionError(model_name=self.model_name, message=f"Configuration failed: {e}")

    async def generate(self, prompt: str, model: str, stream: bool = False, system_prompt: Optional[str] = None, **kwargs) -> str | AsyncGenerator[str, None]:
        """
        Generates a response via the AIMLAPI router, specifying the target model.
        """
        # --- Use self.log instead of global log ---
        if not model:
            raise ValueError("The 'model' argument (specifying the target model like 'gpt-4o') is required for RouterApiConnector.")

        self.log.debug(f"Generating content via {self.model_name} targeting model: {model}. Stream={stream}")
        self.log.debug(f"Prompt: {prompt[:100]}...")
        # ... (rest of the method uses self.log)

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                **kwargs
            )

            if stream:
                self.log.debug("Handling streaming response.")
                async def stream_generator():
                    try:
                        async for chunk in response:
                            content = chunk.choices[0].delta.content
                            if content is not None:
                                yield content
                    except Exception as e:
                        self.log.exception(f"Error during {self.model_name} streaming: {e}", exc_info=True)
                        raise ModelConnectionError(model_name=f"{self.model_name}/{model}", message=f"Streaming error: {e}")
                return stream_generator()
            else:
                self.log.debug(f"Handling non-streaming response.")
                if not response.choices:
                    msg = f"{self.model_name}/{model} returned no choices in the response."
                    self.log.warning(msg)
                    if hasattr(response, 'choices') and len(response.choices) > 0 and response.choices[0].finish_reason:
                         msg += f" Finish Reason: {response.choices[0].finish_reason}"
                    return ""

                content = response.choices[0].message.content
                if content is None:
                     self.log.warning(f"{self.model_name}/{model} returned a message with null content.")
                     return ""

                self.log.debug(f"Successfully extracted content from {self.model_name}/{model} response.")
                return content.strip()

        except openai.APIConnectionError as e:
            self.log.error(f"Connection error with {self.API_BASE_URL}: {e}")
            raise ModelConnectionError(model_name=self.model_name, message=f"API connection error: {e}")
        except openai.RateLimitError as e:
            self.log.error(f"Rate limit exceeded for {self.API_BASE_URL}: {e}")
            raise ModelConnectionError(model_name=self.model_name, message=f"Rate limit exceeded: {e}")
        except openai.APIStatusError as e:
            self.log.exception(f"API Error status {e.status_code} from {self.API_BASE_URL}: {e.response.text}", exc_info=True)
            raise ModelConnectionError(model_name=self.model_name, message=f"API error {e.status_code}: {e}")
        except Exception as e:
            self.log.exception(f"Unexpected error during {self.model_name} generation: {e}", exc_info=True)
            raise ModelConnectionError(model_name=self.model_name, message=f"Unexpected error: {e}")



''' # Directory: backend/models/
# File: aimlapi_connector.py
# Description: Connector for AIMLAPI (api.aimlapi.com/v1) acting as a router to various models, using the OpenAI library format.

import openai # Use the official openai library
from openai import OpenAI, AsyncOpenAI # Import AsyncOpenAI for async operations
from typing import Any, Dict, Optional, AsyncGenerator, List

from backend.models.base_model import BaseModelConnector
from backend.utils.config_loader import get_settings
from backend.utils.logger import setup_logger
from backend.utils.error_handler import ModelConnectionError

log = setup_logger(name="aimlapi_connector")

class AimlApiConnector(BaseModelConnector):
    """
    Connector for interacting with models via the AIMLAPI endpoint (https://api.aimlapi.com/v1),
    which uses an OpenAI-compatible API structure.
    """

    API_BASE_URL = "https://api.aimlapi.com/v1"
    # No default model here, as it must be specified per request

    def __init__(self, api_key: Optional[str] = None, timeout: int = 120, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the AIMLAPI connector using the OpenAI client library.

        Args:
            api_key: AIMLAPI key. Loaded from settings if not provided.
            timeout: Request timeout in seconds for the HTTP client.
            config: Additional configuration (currently unused but kept for consistency).
        """
        # Note: We pass timeout here, but it's applied to the client instance below
        super().__init__(api_key=api_key, timeout=timeout, config=config)
        self.model_name = "AIMLAPI Router" # Generic name for the connector itself

        if not self.api_key:
            settings = get_settings()
            self._load_api_key_from_settings(settings, "AIMLAPI_KEY")

        if not self.api_key:
            raise ModelConnectionError(
                model_name=self.model_name,
                message="API key for AIMLAPI not found in environment variables (AIMLAPI_KEY) or direct input."
            )

        try:
            # Initialize the AsyncOpenAI client pointed to the AIMLAPI endpoint
            self.client = AsyncOpenAI(
                base_url=self.API_BASE_URL,
                api_key=self.api_key,
                timeout=self.timeout # Apply timeout here
            )
            log.info(f"{self.model_name} connector initialized, using OpenAI client pointed to {self.API_BASE_URL}")

        except Exception as e:
            log.exception(f"Failed to configure {self.model_name} client: {e}", exc_info=True)
            raise ModelConnectionError(model_name=self.model_name, message=f"Configuration failed: {e}")

    async def generate(self, prompt: str, model: str, stream: bool = False, system_prompt: Optional[str] = None, **kwargs) -> str | AsyncGenerator[str, None]:
        """
        Generates a response via the AIMLAPI router, specifying the target model.

        Args:
            prompt: The user's input prompt.
            model: The specific underlying model to use via AIMLAPI (e.g., "gpt-4o", "mistralai/Mistral-7B-Instruct-v0.2"). This is REQUIRED.
            stream: If True, returns an async generator yielding response chunks.
            system_prompt: An optional system message.
            **kwargs: Additional parameters passed to the OpenAI chat completions create method
                      (e.g., temperature, max_tokens, top_p).

        Returns:
            If stream=False: The generated response string (content of the assistant's message).
            If stream=True: An async generator yielding response chunks.

        Raises:
            ModelConnectionError: If there's an issue during the API call or processing the response.
            ValueError: If the 'model' argument is missing.
        """
        if not model:
            raise ValueError("The 'model' argument (specifying the target model like 'gpt-4o') is required for RouterApiConnector.")

        log.debug(f"Generating content via {self.model_name} targeting model: {model}. Stream={stream}")
        log.debug(f"Prompt: {prompt[:100]}...")
        log.debug(f"System Prompt: {system_prompt[:100] if system_prompt else 'None'}...")
        log.debug(f"Additional kwargs: {kwargs}")

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                **kwargs
            )

            if stream:
                log.debug("Handling streaming response.")
                async def stream_generator():
                    try:
                        async for chunk in response:
                            content = chunk.choices[0].delta.content
                            if content is not None:
                                yield content
                    except Exception as e:
                        log.exception(f"Error during {self.model_name} streaming: {e}", exc_info=True)
                        raise ModelConnectionError(model_name=f"{self.model_name}/{model}", message=f"Streaming error: {e}")
                return stream_generator()
            else:
                log.debug(f"Handling non-streaming response.")
                # Handle potential non-streaming errors or empty choices
                if not response.choices:
                    msg = f"{self.model_name}/{model} returned no choices in the response."
                    log.warning(msg)
                    # Check for finish reason if available (e.g., content filter)
                    if hasattr(response, 'choices') and len(response.choices) > 0 and response.choices[0].finish_reason:
                         msg += f" Finish Reason: {response.choices[0].finish_reason}"
                    # Decide whether to raise or return empty
                    # raise ModelConnectionError(model_name=f"{self.model_name}/{model}", message=msg)
                    return "" # Return empty for now

                content = response.choices[0].message.content
                if content is None:
                     log.warning(f"{self.model_name}/{model} returned a message with null content.")
                     return ""

                log.debug(f"Successfully extracted content from {self.model_name}/{model} response.")
                return content.strip()

        except openai.APIConnectionError as e:
            log.error(f"Connection error with {self.API_BASE_URL}: {e}")
            raise ModelConnectionError(model_name=self.model_name, message=f"API connection error: {e}")
        except openai.RateLimitError as e:
            log.error(f"Rate limit exceeded for {self.API_BASE_URL}: {e}")
            raise ModelConnectionError(model_name=self.model_name, message=f"Rate limit exceeded: {e}")
        except openai.APIStatusError as e:
            log.exception(f"API Error status {e.status_code} from {self.API_BASE_URL}: {e.response.text}", exc_info=True)
            raise ModelConnectionError(model_name=self.model_name, message=f"API error {e.status_code}: {e}")
        except Exception as e:
            log.exception(f"Unexpected error during {self.model_name} generation: {e}", exc_info=True)
            raise ModelConnectionError(model_name=self.model_name, message=f"Unexpected error: {e}")

            '''
# Directory: backend/models/
# File: deepseek_connector.py
# Description: Connector for DeepSeek models via their REST API.

import requests
import json
from typing import Any, Dict, Optional, AsyncGenerator, List
import asyncio

from backend.models.base_model import BaseModelConnector
from backend.utils.config_loader import get_settings
from backend.utils.logger import setup_logger
from backend.utils.error_handler import ModelConnectionError

log = setup_logger(name="deepseek_connector")

class DeepSeekConnector(BaseModelConnector):
    """
    Connector for interacting with DeepSeek models via their REST API.
    Ref: https://platform.deepseek.com/api-docs/chat-completions/create-chat-completions
    """

    DEFAULT_MODEL = "deepseek-chat" # Or "deepseek-coder"
    API_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, timeout: int = 120, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the DeepSeek connector.

        Args:
            api_key: DeepSeek API key. Loaded from settings if not provided.
            model_name: Specific DeepSeek model to use (e.g., "deepseek-chat", "deepseek-coder"). Defaults to DEFAULT_MODEL.
            timeout: Request timeout in seconds for the HTTP request.
            config: Additional configuration (currently unused but kept for consistency).
        """
        super().__init__(api_key=api_key, timeout=timeout, config=config)

        if not self.api_key:
            settings = get_settings()
            self._load_api_key_from_settings(settings, "DEEPSEEK_API_KEY")

        if not self.api_key:
            raise ModelConnectionError(
                model_name="DeepSeek",
                message="API key for DeepSeek not found in environment variables (DEEPSEEK_API_KEY) or direct input."
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        log.info(f"DeepSeek client configured for model: {self.model_name}")


    # Note: DeepSeek API uses standard HTTP requests, which are blocking by default.
    # To make this truly async without an async HTTP client (like httpx or aiohttp),
    # we'd need to run the requests in a thread pool executor.
    # For simplicity here, we'll use synchronous requests but keep the async signature
    # for compatibility with the base class and potential future refactoring.
    # Consider adding httpx to requirements.txt if true async is needed.
    async def generate(self, prompt: str, stream: bool = False, system_prompt: Optional[str] = None, **kwargs) -> str | AsyncGenerator[str, None]:
        """
        Generates a response from the DeepSeek model using their Chat Completions API.

        Args:
            prompt: The user's input prompt.
            stream: If True, attempts streaming response (if API supports and implemented). Currently NOT fully implemented.
            system_prompt: An optional system message to guide the model's behavior.
            **kwargs: Additional parameters mapped to the DeepSeek API request body
                      (e.g., temperature, max_tokens, top_p).

        Returns:
            If stream=False: The generated response string (content of the assistant's message).
            If stream=True: An async generator yielding response chunks (NOT fully implemented).

        Raises:
            ModelConnectionError: If there's an issue during the API call or processing the response.
        """
        log.debug(f"Generating content with DeepSeek model: {self.model_name}. Stream={stream}")
        log.debug(f"Prompt: {prompt[:100]}...")
        log.debug(f"System Prompt: {system_prompt[:100] if system_prompt else 'None'}...")
        log.debug(f"Additional kwargs: {kwargs}")

        api_url = f"{self.API_BASE_URL}/chat/completions"

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            **kwargs # Add other parameters like temperature, max_tokens etc.
        }
        log.debug(f"Request payload: {payload}")

        if stream:
            # Streaming requires handling Server-Sent Events (SSE)
            # This needs an async HTTP client like httpx and custom parsing logic.
            # Placeholder for now.
            log.warning("Streaming not fully implemented for DeepSeekConnector yet.")
            async def stream_generator():
                 # Replace with actual async SSE handling using httpx or aiohttp
                yield "[Streaming Placeholder]"
                await asyncio.sleep(0) # Yield control
                raise NotImplementedError("DeepSeek streaming requires an async HTTP client and SSE parsing.")
            return stream_generator()
        else:
            # Non-streaming request
            try:
                response = requests.post(
                    api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                data = response.json()
                log.debug(f"Received response data: {data}")

                # Extract the content from the first choice's message
                if data.get("choices") and len(data["choices"]) > 0:
                    message = data["choices"][0].get("message")
                    if message and message.get("role") == "assistant":
                        content = message.get("content")
                        if content:
                            log.debug("Successfully extracted content from DeepSeek response.")
                            return content.strip()

                # Handle cases where response format is unexpected
                log.warning(f"Could not extract assistant content from DeepSeek response: {data}")
                raise ModelConnectionError(model_name=self.model_name, message="Unexpected response format from API.")

            except requests.exceptions.Timeout as e:
                log.error(f"Request timed out after {self.timeout}s: {e}")
                raise ModelConnectionError(model_name=self.model_name, message=f"Request timed out: {e}")
            except requests.exceptions.RequestException as e:
                log.exception(f"Error during DeepSeek API request: {e}", exc_info=True)
                status_code = e.response.status_code if e.response is not None else "N/A"
                error_text = e.response.text if e.response is not None else "No response body"
                msg = f"API request failed with status {status_code}. Error: {e}. Response: {error_text[:200]}"
                raise ModelConnectionError(model_name=self.model_name, message=msg)
            except Exception as e:
                 log.exception(f"Unexpected error during DeepSeek generation: {e}", exc_info=True)
                 raise ModelConnectionError(model_name=self.model_name, message=f"Unexpected error: {e}")
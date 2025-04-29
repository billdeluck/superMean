# Directory: backend/models/
# File: base_model.py
# Description: Abstract base class for all large language model connectors.

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from backend.utils.config_loader import Settings
from backend.utils.logger import setup_logger

log = setup_logger(name="base_model")

class BaseModelConnector(ABC):
    """
    Abstract base class for connecting to and interacting with
    various large language models (LLMs).
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 60, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the base connector.

        Args:
            api_key: The API key for the specific model provider. Can be loaded from settings if not provided.
            timeout: Request timeout in seconds.
            config: Additional model-specific configuration parameters.
        """
        self.api_key = api_key
        self.timeout = timeout
        self.config = config or {}
        self.model_name = self.__class__.__name__.replace("Connector", "") # e.g., "Gemini", "DeepSeek"

        if not self.api_key:
            log.warning(f"API key not directly provided for {self.model_name}. Attempting to load from settings.")
            # Attempt to load from settings if not provided - specific logic in subclasses
            # self._load_api_key_from_settings()

        log.info(f"{self.model_name} connector initialized.")

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Any:
        """
        Generates a response from the language model based on the prompt.

        Args:
            prompt: The input text prompt for the model.
            **kwargs: Additional model-specific parameters (e.g., temperature, max_tokens).

        Returns:
            The generated response from the model. The specific format may vary
            depending on the implementation (e.g., string, dict).

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
            ModelConnectionError: If there's an issue connecting to or processing the request.
        """
        raise NotImplementedError("Subclasses must implement the 'generate' method.")

    def _load_api_key_from_settings(self, settings: Settings, key_attribute_name: str):
        """
        Helper method for subclasses to load API key from the global settings.

        Args:
            settings: The loaded Settings object.
            key_attribute_name: The name of the attribute holding the API key in Settings (e.g., "GEMINI_API_KEY").
        """
        if hasattr(settings, key_attribute_name):
            self.api_key = getattr(settings, key_attribute_name)
            if not self.api_key:
                log.error(f"API key '{key_attribute_name}' found in settings but is empty for {self.model_name}.")
                # Raise error or handle as appropriate
            else:
                 log.info(f"Loaded API key for {self.model_name} from settings.")
        else:
            log.error(f"API key attribute '{key_attribute_name}' not found in settings for {self.model_name}.")
            # Raise error or handle as appropriate

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(api_key_set={bool(self.api_key)}, timeout={self.timeout})>"
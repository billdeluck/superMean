# Directory: backend/memory/
# File: base_memory.py
# Description: Abstract base class for all memory modules.

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.utils.logger import setup_logger

log = setup_logger(name="base_memory") # Ok to init logger at module level for ABC

class BaseMemory(ABC):
    """
    Abstract base class for different types of memory storage used by agents.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the base memory module.

        Args:
            config: Optional configuration dictionary for the specific memory implementation.
        """
        self.config = config or {}
        self.memory_type = self.__class__.__name__
        log.info(f"{self.memory_type} initialized.")

    @abstractmethod
    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Stores a value associated with a key, optionally with metadata.

        Args:
            key: The unique identifier for the memory entry.
            value: The data to be stored.
            metadata: Optional dictionary containing metadata about the entry
                      (e.g., timestamp, source agent, type, relevance score).

        Returns:
            True if storage was successful, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement the 'store' method.")

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieves the value associated with a specific key.

        Args:
            key: The unique identifier for the memory entry.

        Returns:
            The stored value if found, otherwise None.
        """
        raise NotImplementedError("Subclasses must implement the 'retrieve' method.")

    @abstractmethod
    async def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Searches the memory for entries relevant to the query.
        This might involve semantic search (vector dbs) or keyword search.

        Args:
            query: The search query (can be text, or potentially a vector).
            top_k: The maximum number of relevant results to return.
            filter_metadata: Optional dictionary to filter results based on metadata fields.

        Returns:
            A list of relevant memory entries (e.g., list of dicts, each containing
            key, value, metadata, and potentially a relevance score).
            Format can vary based on implementation.
        """
        raise NotImplementedError("Subclasses must implement the 'search' method.")

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Deletes the memory entry associated with the given key.

        Args:
            key: The unique identifier for the memory entry to delete.

        Returns:
            True if deletion was successful or key didn't exist, False on error.
        """
        raise NotImplementedError("Subclasses must implement the 'delete' method.")

    # Optional: Add methods for listing keys, clearing memory, etc. if needed universally
    # async def list_keys(self) -> List[str]: ...
    # async def clear(self) -> bool: ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(config={self.config})>"
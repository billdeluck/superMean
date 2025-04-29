# Directory: backend/memory/
# File: agent_memory.py
# Description: Simple in-memory implementation for agent-specific memory.

import asyncio
from typing import Any, Dict, List, Optional

from backend.memory.base_memory import BaseMemory
from backend.utils.logger import setup_logger

# Initialize logger specific to this module
log = setup_logger(name="agent_memory")

class AgentMemory(BaseMemory):
    """
    A simple in-memory implementation of BaseMemory, suitable for single agent instances
    or testing purposes. Data is lost when the process ends.
    """

    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the in-memory agent memory.

        Args:
            agent_id: The unique identifier for the agent this memory belongs to.
            config: Optional configuration dictionary (currently unused).
        """
        super().__init__(config=config)
        self.agent_id = agent_id
        self._data: Dict[str, Dict[str, Any]] = {} # Store as {"key": {"value": ..., "metadata": ...}}
        log.info(f"In-memory AgentMemory initialized for agent_id: {self.agent_id}")

    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Stores or updates a value and metadata associated with a key in the dictionary.

        Args:
            key: The unique identifier for the memory entry.
            value: The data to be stored.
            metadata: Optional dictionary containing metadata.

        Returns:
            True (in-memory storage is generally considered successful unless an error occurs).
        """
        if not isinstance(key, str) or not key:
             log.error(f"Invalid key provided for store: {key}. Key must be a non-empty string.")
             return False
        try:
            self._data[key] = {
                "value": value,
                "metadata": metadata or {} # Ensure metadata is always a dict
            }
            log.debug(f"Stored key '{key}' for agent '{self.agent_id}'.")
            # Optionally add timestamp to metadata here if not provided
            # if 'timestamp' not in self._data[key]['metadata']:
            #     self._data[key]['metadata']['timestamp'] = datetime.now().isoformat()
            return True
        except Exception as e:
            log.exception(f"Error storing key '{key}' for agent '{self.agent_id}': {e}", exc_info=True)
            return False

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieves the value associated with a specific key from the dictionary.

        Args:
            key: The unique identifier for the memory entry.

        Returns:
            The stored value if the key exists, otherwise None.
        """
        entry = self._data.get(key)
        if entry is not None:
            log.debug(f"Retrieved key '{key}' for agent '{self.agent_id}'.")
            return entry.get("value")
        else:
            log.debug(f"Key '{key}' not found for agent '{self.agent_id}'.")
            return None

    async def retrieve_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves both the value and metadata associated with a specific key.

        Args:
            key: The unique identifier for the memory entry.

        Returns:
            A dictionary containing 'value' and 'metadata' if the key exists, otherwise None.
        """
        entry = self._data.get(key)
        if entry is not None:
             log.debug(f"Retrieved key '{key}' with metadata for agent '{self.agent_id}'.")
             return entry
        else:
            log.debug(f"Key '{key}' not found for agent '{self.agent_id}'.")
            return None

    async def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Performs a simple case-insensitive substring search on keys and stringified values.
        Optionally filters results based on exact matches in metadata.

        Args:
            query: The search query string.
            top_k: The maximum number of results to return.
            filter_metadata: Dictionary to filter results based on metadata key-value pairs.

        Returns:
            A list of matching entries (up to top_k), each containing 'key', 'value', and 'metadata'.
        """
        query_lower = query.lower()
        results = []
        log.debug(f"Searching memory for '{query}' with filter {filter_metadata} for agent '{self.agent_id}'.")

        for key, entry in self._data.items():
            # Check metadata filter first
            if filter_metadata:
                match_filter = True
                for meta_key, meta_value in filter_metadata.items():
                    if entry["metadata"].get(meta_key) != meta_value:
                        match_filter = False
                        break
                if not match_filter:
                    continue # Skip if metadata doesn't match

            # Perform substring search on key and value
            value_str = str(entry.get("value", "")).lower()
            key_lower = key.lower()

            if query_lower in key_lower or query_lower in value_str:
                # Add score (simple relevance = 1.0 for basic match)
                 result_entry = {
                     "key": key,
                     "value": entry["value"],
                     "metadata": entry["metadata"],
                     "score": 1.0 # Simple score for basic match
                 }
                 results.append(result_entry)

        # Sort by score (though all are 1.0 here, useful for other implementations)
        # results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        log.debug(f"Found {len(results)} potential matches before limiting to top_k={top_k}.")
        return results[:top_k]

    async def delete(self, key: str) -> bool:
        """
        Deletes an entry from the dictionary based on its key.

        Args:
            key: The unique identifier for the memory entry to delete.

        Returns:
            True if the key was found and deleted, False otherwise.
        """
        if key in self._data:
            try:
                del self._data[key]
                log.debug(f"Deleted key '{key}' for agent '{self.agent_id}'.")
                return True
            except Exception as e:
                 log.exception(f"Error deleting key '{key}' for agent '{self.agent_id}': {e}", exc_info=True)
                 return False
        else:
            log.debug(f"Key '{key}' not found for deletion for agent '{self.agent_id}'.")
            return False # Or True if "delete if exists" behavior is preferred

    async def list_keys(self) -> List[str]:
        """Returns a list of all keys stored in the memory."""
        return list(self._data.keys())

    async def clear(self) -> bool:
        """Removes all entries from the memory."""
        self._data.clear()
        log.info(f"Cleared all memory for agent '{self.agent_id}'.")
        return True
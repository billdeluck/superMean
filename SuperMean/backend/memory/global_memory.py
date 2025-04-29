# Directory: backend/memory/
# File: global_memory.py
# Description: Advanced persistent global memory using ChromaDB. (Updated Search Filter Logic)

# --- START SQLITE OVERRIDE ---
# Add this block to force ChromaDB use the pysqlite3-binary
# See: https://docs.trychroma.com/troubleshooting#sqlite
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    print("Successfully overrode sqlite3 with pysqlite3.")
except ImportError:
    print("pysqlite3-binary not found, using system sqlite3.")
# --- END SQLITE OVERRIDE ---

import asyncio
import chromadb
import json
import os
from typing import Any, Dict, List, Optional, ClassVar

from backend.memory.base_memory import BaseMemory
from backend.utils.logger import setup_logger
from backend.utils.config_loader import get_settings
from backend.utils.error_handler import MemoryError

# Initialize logger specific to this module
log = setup_logger(name="global_memory_chroma")

# Default path - can be overridden via config in a real app
DEFAULT_CHROMA_PATH = "./global_memory_db"
DEFAULT_COLLECTION_NAME = "supermean_global_store"
# Key within metadata dict used to store the serialized original value
VALUE_METADATA_KEY = "_original_value_json"

class GlobalMemory(BaseMemory):
    """
    Persistent global memory implementation using ChromaDB.

    Stores data locally in the specified path. Handles basic storage,
    retrieval, metadata filtering, and deletion. Does NOT implement
    vector/semantic search yet, but uses ChromaDB structure.
    """
    _client: Optional[chromadb.PersistentClient] = None
    _collection: Optional[chromadb.Collection] = None
    _lock: ClassVar[Optional[asyncio.Lock]] = None # Use lock for async safety on class var access if needed

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the ChromaDB client and collection for global memory.

        Args:
            config: Optional configuration dictionary. Can include 'chroma_path'
                    and 'collection_name'.
        """
        super().__init__(config=config)
        self.chroma_path = self.config.get("chroma_path", DEFAULT_CHROMA_PATH)
        self.collection_name = self.config.get("collection_name", DEFAULT_COLLECTION_NAME)

        # Initialize lock if not already done (relevant if instances share state beyond ChromaDB)
        if GlobalMemory._lock is None:
             GlobalMemory._lock = asyncio.Lock()

        try:
            # Ensure directory exists
            if not os.path.exists(self.chroma_path):
                 os.makedirs(self.chroma_path, exist_ok=True)
                 log.info(f"Created ChromaDB storage directory: {self.chroma_path}")

            # Initialize client
            self._client = chromadb.PersistentClient(path=self.chroma_path)

            # Get or create the collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
            )
            log.info(f"ChromaDB GlobalMemory initialized. Path: '{self.chroma_path}', Collection: '{self.collection_name}'. Collection size: {self._collection.count()}")

        except Exception as e:
            log.exception(f"Failed to initialize ChromaDB client/collection: {e}", exc_info=True)
            self._client = None
            self._collection = None
            raise MemoryError(operation="initialize", message=f"ChromaDB init failed: {e}")

    def _ensure_collection(self) -> chromadb.Collection:
        """Helper to check if collection is available."""
        if self._collection is None:
             log.error("ChromaDB collection is not available.")
             raise MemoryError(operation="access", message="ChromaDB collection not initialized.")
        return self._collection

    def _serialize_value(self, value: Any) -> str:
        """Serialize complex values to JSON strings for metadata storage."""
        try:
            return json.dumps(value)
        except TypeError as e:
            log.warning(f"Could not JSON serialize value of type {type(value)}. Storing string representation. Error: {e}")
            return str(value) # Fallback to string representation

    def _deserialize_value(self, value_str: Optional[str]) -> Any:
         """Deserialize value from JSON string stored in metadata."""
         if value_str is None: return None
         try:
             return json.loads(value_str)
         except (json.JSONDecodeError, TypeError):
             log.warning(f"Could not JSON deserialize value, returning as raw string: {value_str[:100]}...")
             return value_str # Return the raw string if deserialization fails

    # --- BaseMemory Implementation ---

    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Stores or updates an entry in the ChromaDB collection.
        The key becomes the document ID. The value is serialized and stored in metadata.
        The string representation of the value is stored as the document content.

        Args:
            key: The unique identifier (document ID).
            value: The data to store.
            metadata: Optional dictionary of metadata (must contain JSON-serializable values).

        Returns:
            True if storage was successful, False otherwise.
        """
        collection = self._ensure_collection()
        if not isinstance(key, str) or not key:
             log.error(f"Invalid key provided for store: {key}. Key must be a non-empty string.")
             return False

        metadata = metadata or {}
        # Ensure metadata values are simple types or serializable
        clean_metadata = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool, list, dict)): # Allow list/dict if serializable
                try:
                    json.dumps(v) # Check if serializable
                    clean_metadata[k] = v # Store original if serializable (Chroma handles internal types)
                except TypeError:
                    log.warning(f"Metadata value for key '{k}' is not JSON-serializable type ({type(v)}), skipping.")
            else:
                 log.warning(f"Metadata value for key '{k}' is not simple/dict/list type ({type(v)}), skipping.")


        # Store serialized original value in metadata
        clean_metadata[VALUE_METADATA_KEY] = self._serialize_value(value)
        # Use string representation as the 'document'
        document_content = str(value)

        try:
            # Use upsert to handle both insert and update
            # Note: ChromaDB client operations are synchronous internally
            collection.upsert(
                ids=[key],
                documents=[document_content], # Store string representation
                metadatas=[clean_metadata]
            )
            log.debug(f"Stored/Updated global key '{key}' in ChromaDB.")
            await asyncio.sleep(0) # Yield control to async loop
            return True
        except Exception as e:
            log.exception(f"Error storing key '{key}' in ChromaDB: {e}", exc_info=True)
            return False

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieves an entry by its key (ID) from ChromaDB and deserializes the original value.

        Args:
            key: The unique identifier (document ID).

        Returns:
            The original deserialized value if found, otherwise None.
        """
        entry_data = await self.retrieve_with_metadata(key)
        return entry_data.get("value") if entry_data else None

    async def retrieve_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the full entry (ID, document, metadata including original value) by key.

        Args:
            key: The unique identifier (document ID).

        Returns:
            A dictionary containing 'key', 'value' (deserialized), 'document' (string rep),
            and 'metadata' if found, otherwise None.
        """
        collection = self._ensure_collection()
        try:
            # Note: ChromaDB client operations are synchronous internally
            results = collection.get(ids=[key], include=['metadatas', 'documents'])
            await asyncio.sleep(0) # Yield control

            if results and results['ids']:
                retrieved_id = results['ids'][0]
                metadata = results['metadatas'][0] if results['metadatas'] else {}
                document = results['documents'][0] if results['documents'] else None

                # Extract and deserialize original value
                serialized_value = metadata.pop(VALUE_METADATA_KEY, None) # Remove from exposed metadata
                original_value = self._deserialize_value(serialized_value)

                log.debug(f"Retrieved global key '{retrieved_id}' with metadata from ChromaDB.")
                return {
                    "key": retrieved_id,
                    "value": original_value,
                    "document": document, # String representation
                    "metadata": metadata # User-provided metadata
                }
            else:
                log.debug(f"Global key '{key}' not found in ChromaDB.")
                return None
        except Exception as e:
            log.exception(f"Error retrieving key '{key}' from ChromaDB: {e}", exc_info=True)
            return None

    async def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Searches ChromaDB based primarily on metadata filters using the 'where' clause.
        NOTE: The 'query' text is currently IGNORED as no embedding function is configured.

        Args:
            query: The search query text (IGNORED).
            top_k: The maximum number of results to return.
            filter_metadata: Dictionary to filter results.
                             Example: {"type": "task", "priority": 2} -> becomes $and condition
                             For complex filters use Chroma operators directly:
                             {"$or": [{"priority": {"$gte": 2}}, {"status": "urgent"}]}

        Returns:
            A list of matching entries (up to top_k), formatted consistently.
        """
        collection = self._ensure_collection()
        where_clause = {}

        if filter_metadata:
            # Check if the filter already contains Chroma operators like $or, $and
            if any(key.startswith('$') for key in filter_metadata.keys()):
                 # Assume it's already a valid ChromaDB 'Where' structure
                 where_clause = filter_metadata
                 log.debug("Using provided complex ChromaDB 'where' clause.")
            elif len(filter_metadata) == 1:
                 # Single key-value pair, pass directly (implicit $eq)
                 where_clause = filter_metadata
                 log.debug("Using single-key implicit equality 'where' clause.")
            elif len(filter_metadata) > 1:
                 # Multiple key-value pairs -> construct explicit $and
                 where_clause = {
                     "$and": [
                         {k: {"$eq": v}} for k, v in filter_metadata.items()
                         # Note: Using explicit $eq here for clarity, often optional
                     ]
                 }
                 log.debug("Constructed multi-key explicit '$and' 'where' clause.")
            else: # Empty filter dictionary
                pass # No filter

        # If no filter was provided, we cannot efficiently query all items without vectors/ids.
        if not where_clause:
             log.warning("GlobalMemory search called without filter_metadata. Returning empty list as metadata filtering is the primary supported mode.")
             return []

        log.debug(f"Searching ChromaDB with where clause: {where_clause}, limit: {top_k}. Query text '{query}' is ignored.")

        try:
            # Note: ChromaDB client operations are synchronous internally
            results = collection.get(
                where=where_clause, # Pass the constructed filter
                limit=top_k,
                include=['metadatas', 'documents']
            )
            await asyncio.sleep(0) # Yield control

            output_results = []
            if results and results['ids']:
                 for i, doc_id in enumerate(results['ids']):
                     metadata = results['metadatas'][i] if results['metadatas'] else {}
                     document = results['documents'][i] if results['documents'] else None
                     serialized_value = metadata.pop(VALUE_METADATA_KEY, None)
                     original_value = self._deserialize_value(serialized_value)

                     output_results.append({
                         "key": doc_id,
                         "value": original_value,
                         "document": document,
                         "metadata": metadata,
                         "score": 1.0 # No relevance score without vector search
                     })
            log.debug(f"ChromaDB metadata search found {len(output_results)} results.")
            return output_results

        except ValueError as ve:
            # Catch potential errors from invalid where clauses
            log.error(f"Invalid 'where' clause format for ChromaDB search: {where_clause}. Error: {ve}")
            return [] # Return empty on query format error
        except Exception as e:
             log.exception(f"Error searching ChromaDB with filter {where_clause}: {e}", exc_info=True)
             return []


    async def delete(self, key: str) -> bool:
        """
        Deletes an entry from the ChromaDB collection by its ID (key).

        Args:
            key: The unique identifier (document ID) to delete.

        Returns:
            True if deletion was successful (or key didn't exist), False on error.
        """
        collection = self._ensure_collection()
        try:
            # Note: ChromaDB client operations are synchronous internally
            collection.delete(ids=[key])
            log.debug(f"Deleted global key '{key}' from ChromaDB.")
            await asyncio.sleep(0) # Yield control
            return True
        except Exception as e:
            # ChromaDB delete might not raise error if ID doesn't exist, log potential issues
            log.exception(f"Error deleting key '{key}' from ChromaDB: {e}", exc_info=True)
            return False # Indicate potential failure

    async def list_keys(self) -> List[str]:
        """Returns a list of all keys (IDs) stored in the collection."""
        collection = self._ensure_collection()
        try:
            # Note: ChromaDB client operations are synchronous internally
            # Getting all items might be slow for very large collections.
            results = collection.get(include=[]) # Only need IDs
            await asyncio.sleep(0) # Yield control
            return results.get('ids', [])
        except Exception as e:
            log.exception(f"Error listing keys from ChromaDB: {e}", exc_info=True)
            return []

    async def clear(self) -> bool:
        """
        Removes all entries from the ChromaDB collection.
        NOTE: This deletes data! Use with caution. Can be slow for large collections.
        """
        collection = self._ensure_collection()
        try:
            # Get all IDs and delete them
            # For very large collections, consider deleting and recreating the collection
            all_ids = await self.list_keys() # This itself can be slow
            if all_ids:
                 log.warning(f"Clearing {len(all_ids)} items from ChromaDB collection '{self.collection_name}'...")
                 collection.delete(ids=all_ids) # This can also be slow
                 log.info(f"Cleared all {len(all_ids)} items from ChromaDB collection '{self.collection_name}'.")
            else:
                 log.info(f"ChromaDB collection '{self.collection_name}' is already empty.")
            await asyncio.sleep(0) # Yield control
            return True
        except Exception as e:
            log.exception(f"Error clearing ChromaDB collection '{self.collection_name}': {e}", exc_info=True)
            return False
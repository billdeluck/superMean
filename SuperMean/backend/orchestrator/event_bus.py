# Directory: backend/orchestrator/
# File: event_bus.py
# Description: An asynchronous event bus with file-based persistence and basic retries.

import asyncio
import json
import os
import aiofiles # Need aiofiles for async file operations
from typing import Any, Dict, List, Callable, Coroutine, Tuple, Optional
import time

from backend.utils.logger import setup_logger
from backend.utils.error_handler import SuperMeanException # Use base exception if needed

# Logger setup
log = setup_logger(name="event_bus")

# Define a type for asynchronous event handlers (coroutines)
EventHandler = Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]

# --- Constants for Persistence and Retries ---
PERSISTENCE_FILE = "./event_bus_events.log"
DLQ_FILE = "./event_bus_dlq.log"
MAX_RETRIES_PER_EVENT = 3 # Max attempts to process a single event
RETRY_DELAY_SECONDS = 1 # Initial delay before retrying

# --- Event Data Structure for Persistence ---
# { "event_type": "...", "event_data": {...}, "retries": 0, "timestamp": "..." }
# (Timestamp could be added)

class EventBusError(SuperMeanException):
    """Custom exception for EventBus operational failures."""
    pass


class EventBus:
    """
    An asynchronous event bus with file-based persistence for durability
    and basic retry logic for handler failures.
    Events are logged to a file before dispatch and retried on failure.
    Failed events move to a Dead Letter Queue file after max retries.
    """

    def __init__(self, persistence_file: str = PERSISTENCE_FILE, dlq_file: str = DLQ_FILE):
        # Dictionary to store handlers: {"event_type": [handler1, handler2, ...]}
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._persistence_file = persistence_file
        self._dlq_file = dlq_file
        self._processing_lock = asyncio.Lock() # Prevent concurrent processing of the persistence file
        self._dlq_lock = asyncio.Lock() # Protect DLQ file

        log.info("EventBus initialized with persistence and retries.")

        # --- Load pending events from persistence file on startup ---
        # This is typically done once during application startup, not on every instance init
        # For demonstration, we'll add a method to load and process on demand.
        # In a real app, this would be part of the application startup sequence.
        # asyncio.create_task(self._load_and_process_pending_events()) # Example startup call

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Registers an asynchronous handler function for a specific event type.
        """
        if not asyncio.iscoroutinefunction(handler):
            log.warning(f"Attempted to subscribe non-async handler for event '{event_type}'. Handler ignored.")
            return

        if event_type not in self._handlers:
            self._handlers[event_type] = []
            log.debug(f"Created new event type '{event_type}' in bus.")

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            log.info(f"Handler {handler.__name__} subscribed to event '{event_type}'.")
        else:
            log.debug(f"Handler {handler.__name__} already subscribed to event '{event_type}'.")


    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Unregisters a handler function from a specific event type.
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            if not self._handlers[event_type]:
                 del self._handlers[event_type] # Remove event type if no handlers left
                 log.debug(f"Removed event type '{event_type}' from bus (no handlers left).")
            log.info(f"Handler {handler.__name__} unsubscribed from event '{event_type}'.")
        else:
            log.warning(f"Attempted to unsubscribe handler {handler.__name__} from '{event_type}', but it was not found.")

    async def _log_event(self, event_data: Dict[str, Any]) -> None:
        """Logs an event to the persistence file."""
        try:
            async with aiofiles.open(self._persistence_file, mode='a') as f:
                await f.write(json.dumps(event_data) + '\n')
            log.debug(f"Logged event to persistence file: {event_data.get('event_type')}")
        except Exception as e:
            log.error(f"Failed to log event {event_data.get('event_type')} to persistence file: {e}")
            # Decide how to handle logging failure (e.g., raise, log to stderr, etc.)

    async def _remove_event_from_persistence(self, event_to_remove: Dict[str, Any]) -> None:
         """Removes a specific event from the persistence file."""
         async with self._processing_lock: # Ensure exclusive file access during read/write
             try:
                 async with aiofiles.open(self._persistence_file, mode='r+') as f:
                     lines = await f.readlines()
                     await f.seek(0) # Go back to start of file
                     await f.truncate() # Clear file content
                     for line in lines:
                         try:
                             event = json.loads(line.strip())
                             # Use a robust check to match the event, not just reference equality
                             # Comparing dicts might be tricky with complex types or order
                             # For simplicity, compare type, data, and retries
                             # Compare based on event type and data, excluding retry count
                             if not (event.get("event_type") == event_to_remove.get("event_type") and
                                     event.get("event_data") == event_to_remove.get("event_data")):
                                 await f.write(line) # Write back lines that are NOT the one to remove
                             else:
                                 log.debug(f"Removed event from persistence file: {event.get('event_type')}")
                         except json.JSONDecodeError:
                             log.warning(f"Skipping invalid JSON line in persistence file during removal: {line.strip()}")
                             await f.write(line) # Keep invalid lines? Or discard? Discarding might lose data.

             except FileNotFoundError:
                 log.debug(f"Persistence file {self._persistence_file} not found during removal.")
             except Exception as e:
                 log.error(f"Failed to remove event from persistence file: {e}")

    async def _move_event_to_dlq(self, event_data: Dict[str, Any]) -> None:
        """Logs an event to the Dead Letter Queue file."""
        try:
            async with aiofiles.open(self._dlq_file, mode='a') as f:
                await f.write(json.dumps(event_data) + '\n')
            log.warning(f"Moved event {event_data.get('event_type')} to DLQ after {event_data.get('retries')} retries.")
        except Exception as e:
            log.error(f"Failed to log event {event_data.get('event_type')} to DLQ file: {e}")


    async def _dispatch_event(self, event_type: str, event_data: Dict[str, Any], retries: int) -> bool:
        """Internal method to dispatch an event to handlers and handle results."""
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            log.debug(f"No handlers registered for event '{event_type}'. Event considered processed.")
            return True # Handled successfully if no handlers are interested

        log.debug(f"Dispatching event '{event_type}' (Attempt {retries + 1})...")
        tasks = [handler(event_type, event_data) for handler in handlers]
        success = True

        try:
            # Run handlers concurrently, catching exceptions
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    handler_name = handlers[i].__name__ if hasattr(handlers[i], '__name__') else str(handlers[i])
                    log.error(f"Handler {handler_name} for event '{event_type}' (Attempt {retries + 1}) raised an exception: {result}", exc_info=True)
                    success = False # Mark event as failed if *any* handler failed
                # else: Handler completed successfully

        except asyncio.CancelledError:
             log.warning(f"Event dispatch for '{event_type}' (Attempt {retries + 1}) was cancelled.")
             success = False # Treat cancellation as failure for retry logic
             # Re-raise if the cancellation should propagate immediately
             # raise
        except Exception as e:
            # Catch unexpected errors during gather itself
            log.exception(f"Unexpected error during async.gather for event '{event_type}' (Attempt {retries + 1}): {e}", exc_info=True)
            success = False # Treat unexpected gather error as failure
            # Re-raise if the error should be critical
            # raise

        if success:
            log.debug(f"Event '{event_type}' processed successfully by all handlers.")
            return True
        else:
            log.warning(f"Event '{event_type}' failed processing by one or more handlers (Attempt {retries + 1}).")
            return False # Indicate failure


    async def publish(self, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Publishes an event, logs it for persistence, and dispatches it.
        """
        log.info(f"Publishing event: '{event_type}'")
        data_to_log = {
            "event_type": event_type,
            "event_data": event_data or {},
            "retries": 0, # Initial attempt count
            "timestamp": time.time() # Add timestamp
        }

        # 1. Log event for persistence BEFORE attempting dispatch
        await self._log_event(data_to_log)

        # 2. Attempt immediate dispatch
        success = await self._dispatch_event(
            data_to_log["event_type"],
            data_to_log["event_data"],
            data_to_log["retries"]
        )

        # 3. Handle dispatch result
        if success:
            # If successful, remove from persistence log
            await self._remove_event_from_persistence(data_to_log)
        else:
            # If failed, increment retry count in persistence log (requires re-writing file)
            # Or, simpler: just leave it in the log; _load_and_process_pending_events
            # will pick it up later and handle retries/DLQ.
            log.warning(f"Event '{event_type}' failed initial dispatch. It remains in the persistence log for retry.")


    async def _load_and_process_pending_events(self) -> None:
         """
         Loads events from the persistence file and attempts to process them.
         Handles retries and moves failed events to the DLQ.
         Intended to be run once on application startup.
         """
         await asyncio.sleep(1) # Give system a moment to initialize other components
         log.info("Starting processing of pending events from persistence file.")

         pending_events: List[Dict[str, Any]] = []
         async with self._processing_lock: # Exclusive access to read the file
             try:
                 async with aiofiles.open(self._persistence_file, mode='r') as f:
                     async for line in f:
                         try:
                             event = json.loads(line.strip())
                             if isinstance(event, dict) and "event_type" in event and "retries" in event:
                                 pending_events.append(event)
                             else:
                                  log.warning(f"Skipping invalid event format in persistence file: {line.strip()}")
                         except json.JSONDecodeError:
                             log.warning(f"Skipping invalid JSON line in persistence file: {line.strip()}")

             except FileNotFoundError:
                 log.info("No event persistence file found. No pending events to process.")
                 return
             except Exception as e:
                 log.error(f"Failed to read persistence file {self._persistence_file}: {e}")
                 # In a real app, you might stop startup or alert here.
                 return

         if not pending_events:
             log.info("Persistence file found but empty or contained no valid events.")
             # Optionally, clear the file if it had invalid lines but no valid events
             # async with aiofiles.open(self._persistence_file, mode='w') as f: await f.write("")
             return

         log.info(f"Found {len(pending_events)} pending events in persistence file. Starting retry processing.")

         # Create a queue or process sequentially/in limited concurrency
         # Processing them sequentially is simpler to manage state/file writes
         for event in pending_events:
             event_type = event["event_type"]
             event_data = event["event_data"]
             retries = event.get("retries", 0)

             # Retry loop for this event
             for attempt in range(retries, MAX_RETRIES_PER_EVENT + 1):
                 success = await self._dispatch_event(event_type, event_data, attempt)

                 if success:
                     log.debug(f"Pending event '{event_type}' processed successfully after {attempt} retries.")
                     # Remove from persistence log after success
                     await self._remove_event_from_persistence(event)
                     break # Exit retry loop for this event
                 else:
                     log.warning(f"Pending event '{event_type}' failed processing on attempt {attempt + 1}.")
                     if attempt >= MAX_RETRIES_PER_EVENT:
                         log.error(f"Pending event '{event_type}' exhausted retries.")
                         # Move to DLQ and remove from persistence log
                         event["retries"] = attempt + 1 # Update final retry count
                         await self._move_event_to_dlq(event)
                         await self._remove_event_from_persistence(event)
                     else:
                         # Increment retry count in the event object (in memory)
                         event["retries"] = attempt + 1
                         # Wait before the next retry (exponential backoff could be added)
                         retry_delay = RETRY_DELAY_SECONDS * (2 ** attempt) # Simple exponential backoff
                         log.info(f"Retrying pending event '{event_type}' in {retry_delay:.2f} seconds...")
                         await asyncio.sleep(retry_delay)

         log.info("Finished processing pending events from persistence file.")
         # After processing all, rewrite the persistence file with any remaining (e.g., failed intermediate steps)
         # Or ensure _remove_event_from_persistence is robust enough.

    # Method to initiate pending event processing (call this during app startup)
    def start_pending_event_processing(self):
        """Starts the background task to process pending events from the persistence file."""
        log.info("Starting background task for pending event processing.")
        asyncio.create_task(self._load_and_process_pending_events())
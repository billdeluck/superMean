# Directory: backend/orchestrator/
# File: event_bus.py
# Description: An asynchronous in-memory event bus for the system.

import asyncio
from typing import Any, Dict, List, Callable, Coroutine

from backend.utils.logger import setup_logger
from backend.utils.error_handler import SuperMeanException # Use base exception if needed

# Logger setup
log = setup_logger(name="event_bus")

# Define a type for asynchronous event handlers (coroutines)
EventHandler = Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]

class EventBus:
    """
    An asynchronous in-memory event bus.
    Allows components to subscribe to specific event types and publish events.
    Handlers are executed concurrently when an event is published.
    """

    def __init__(self):
        # Dictionary to store handlers: {"event_type": [handler1, handler2, ...]}
        self._handlers: Dict[str, List[EventHandler]] = {}
        log.info("EventBus initialized.")

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Registers an asynchronous handler function for a specific event type.

        Args:
            event_type: The string identifier for the event (e.g., "mission.started").
            handler: The async function (coroutine) to call when the event occurs.
                     It should accept the event type (str) and event data (dict) as arguments.
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

        Args:
            event_type: The string identifier for the event.
            handler: The async function to unregister.
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            if not self._handlers[event_type]:
                 del self._handlers[event_type] # Remove event type if no handlers left
                 log.debug(f"Removed event type '{event_type}' from bus (no handlers left).")
            log.info(f"Handler {handler.__name__} unsubscribed from event '{event_type}'.")
        else:
            log.warning(f"Attempted to unsubscribe handler {handler.__name__} from '{event_type}', but it was not found.")

    async def publish(self, event_type: str, event_data: Dict[str, Any] | None = None) -> None:
        """
        Publishes an event to the bus, triggering all registered handlers.

        Args:
            event_type: The string identifier for the event.
            event_data: Optional dictionary containing data relevant to the event.
        """
        log.info(f"Publishing event: '{event_type}'")
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            log.debug(f"No handlers registered for event '{event_type}'.")
            return

        log.debug(f"Invoking {len(handlers)} handlers for event '{event_type}'.")
        event_data = event_data or {}

        # Gather all handler coroutines
        tasks = [handler(event_type, event_data) for handler in handlers]

        # Run handlers concurrently. Use shield to prevent cancellation issues if needed,
        # and gather with return_exceptions=True to ensure all run even if one fails.
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    handler_name = handlers[i].__name__ if hasattr(handlers[i], '__name__') else str(handlers[i])
                    log.error(f"Handler {handler_name} for event '{event_type}' raised an exception: {result}", exc_info=True)
                    # Depending on system requirements, you might want to stop processing,
                    # notify other components, or just log and continue. Logging is done.

        except asyncio.CancelledError:
             log.warning(f"EventBus publish for '{event_type}' was cancelled.")
             raise # Re-raise cancellation
        except Exception as e:
            # Catch unexpected errors during gather itself (less common)
            log.exception(f"Unexpected error during async.gather for event '{event_type}': {e}", exc_info=True)
            raise # Re-raise
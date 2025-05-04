# Directory: backend/orchestrator/
# File: event_bus_test.py
# Description: Verifies the asynchronous EventBus functionality. (Fixed patch import)
# Command: python -m backend.orchestrator.event_bus_test

import sys
import os
import unittest
import asyncio
from unittest.mock import AsyncMock, call, MagicMock, patch # <-- ADDED 'patch' IMPORT
import textwrap # <-- ADDED textwrap IMPORT (useful for multiline strings)
from typing import Dict, Any

# Adjust path to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.orchestrator.event_bus import EventBus, EventHandler
    print("Imported EventBus successfully.")

    # Define mock async handlers
    async def handler1(event_type: str, data: Dict[str, Any]):
        print(f"Handler 1 received event: {event_type} with data {data}")
        await asyncio.sleep(0.01) # Simulate async work
        # Note: Using attributes on the function object like handler1.called is simple
        # but less clean than using mocks for the handlers themselves.
        # For robustness in a real project, handlers would ideally be mock objects.
        if not hasattr(handler1, 'called_with'): handler1.called_with = []
        handler1.called_with.append((event_type, data))


    async def handler2(event_type: str, data: Dict[str, Any]):
        print(f"Handler 2 received event: {event_type} with data {data}")
        await asyncio.sleep(0.02) # Simulate async work
        if not hasattr(handler2, 'called_with'): handler2.called_with = []
        handler2.called_with.append((event_type, data))

    # Handler that raises an exception
    async def failing_handler(event_type: str, data: Dict[str, Any]):
        print(f"Failing Handler received event: {event_type} with data {data}")
        await asyncio.sleep(0.01)
        # To track if it was attempted, could use a flag before raising
        if not hasattr(failing_handler, 'attempted'): failing_handler.attempted = True
        raise ValueError("Something went wrong in handler")


    class TestEventBus(unittest.IsolatedAsyncioTestCase): # Use IsolatedAsyncioTestCase

        def setUp(self):
            self.event_bus = EventBus()
            # Reset handler flags/mocks before each test
            if hasattr(handler1, 'called_with'): del handler1.called_with
            if hasattr(handler2, 'called_with'): del handler2.called_with
            if hasattr(failing_handler, 'attempted'): del failing_handler.attempted


            # Patch logging.error to check if exceptions are logged
            # This patch needs to be started/stopped
            self.mock_log_error = MagicMock()
            # --- PATCH IMPORT FIXED ---
            self.log_patch = patch('backend.orchestrator.event_bus.log.error', self.mock_log_error)
            # --- END FIX ---
            self.log_patch.start() # Start the patcher

            print(f"\n--- Starting test: {self._testMethodName} ---")

        def tearDown(self):
            self.log_patch.stop() # Stop the patcher
            print(f"--- Finished test: {self._testMethodName} ---")


        async def test_subscribe_and_publish(self):
            """Test basic event subscription and publishing."""
            event_type = "user.created"
            event_data = {"user_id": 123, "username": "test_user"}

            # Subscribe handlers
            self.event_bus.subscribe(event_type, handler1)
            self.event_bus.subscribe(event_type, handler2)

            # Publish event
            await self.event_bus.publish(event_type, event_data)

            # Assert handlers were called with correct data
            self.assertIn((event_type, event_data), handler1.called_with)
            self.assertIn((event_type, event_data), handler2.called_with)

            # Publish an event with no handlers
            await self.event_bus.publish("nonexistent.event", {"data": "abc"})
            # Handlers should not have been called again for the second event type
            self.assertEqual(len(handler1.called_with), 1)
            self.assertEqual(len(handler2.called_with), 1)
            print("Subscribe and publish test passed.")

        async def test_unsubscribe(self):
            """Test unsubscribing handlers."""
            event_type = "data.updated"
            event_data = {"id": "xyz"}

            self.event_bus.subscribe(event_type, handler1)
            self.event_bus.subscribe(event_type, handler2)
            self.assertEqual(len(self.event_bus._handlers[event_type]), 2)

            # Unsubscribe handler1
            self.event_bus.unsubscribe(event_type, handler1)
            self.assertEqual(len(self.event_bus._handlers[event_type]), 1)
            self.assertIn(handler2, self.event_bus._handlers[event_type])
            self.assertNotIn(handler1, self.event_bus._handlers[event_type])

            # Publish - only handler2 should be called
            await self.event_bus.publish(event_type, event_data)
            # Handler1 should not have been called at all for this event
            self.assertFalse(hasattr(handler1, 'called_with'))
            self.assertIn((event_type, event_data), handler2.called_with)


            # Unsubscribe handler2 - event type should be removed
            self.event_bus.unsubscribe(event_type, handler2)
            self.assertNotIn(event_type, self.event_bus._handlers)
            print("Unsubscribe test passed.")

        async def test_publish_no_handlers(self):
            """Test publishing when no handlers are subscribed for an event type."""
            event_type = "empty.event"
            # No subscription
            await self.event_bus.publish(event_type, {"data": "empty"})
            # No errors should occur, no handlers should be called (obvious but good to verify behavior)
            self.assertFalse(hasattr(handler1, 'called_with'))
            self.assertFalse(hasattr(handler2, 'called_with'))
            print("Publish no handlers test passed.")

        async def test_handler_raises_exception(self):
            """Test that publishing still proceeds if one handler raises an exception."""
            event_type = "error.event"
            event_data = {"problem": True}

            self.event_bus.subscribe(event_type, handler1) # Will pass
            self.event_bus.subscribe(event_type, failing_handler) # Will fail
            self.event_bus.subscribe(event_type, handler2) # Will pass

            # Publish event
            await self.event_bus.publish(event_type, event_data)

            # Assert that all handlers were attempted (check flags or logging if they fail before setting flag)
            self.assertIn((event_type, event_data), handler1.called_with)
            # The failing handler's print statement should appear
            self.assertTrue(hasattr(failing_handler, 'attempted'))
            self.assertIn((event_type, event_data), handler2.called_with)


            # Assert that the exception was caught and logged
            # The mock_log_error should have been called
            self.mock_log_error.assert_called_once()
            # Check the error message contains details about the handler and the exception
            call_args, call_kwargs = self.mock_log_error.call_args
            error_message = call_args[0]
            self.assertIn("Handler failing_handler", error_message) # Check handler name
            self.assertIn("raised an exception", error_message)
            self.assertIn("ValueError: Something went wrong", error_message) # Check exception type/message
            # exc_info should be True (checked by mock call's kwargs)
            self.assertTrue(call_kwargs['exc_info'])
            print("Handler raises exception test passed (check log output).")


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning EventBus tests...")
        # Use default test runner with verbosity
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure orchestrator/event_bus.py and its dependencies exist.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
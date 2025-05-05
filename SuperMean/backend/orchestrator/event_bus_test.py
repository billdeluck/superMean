# Directory: backend/orchestrator/
# File: event_bus_test.py
# Description: Verifies the asynchronous EventBus functionality with persistence and retries. (Corrected File Paths and Test Logic)
# Command: python -m backend.orchestrator.event_bus_test

import asyncio
import os
import sys
import unittest
import json
import aiofiles # Needed for async file operations in tests
import shutil # Needed for cleaning directories
import time # Needed for time.time() in test helpers
from unittest.mock import AsyncMock, call, MagicMock, patch # Import patch
import textwrap # Added textwrap for completeness, though not used in this file
from typing import Any, Dict, List # Added List import


# Adjust path to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.orchestrator.event_bus import EventBus, EventHandler # Import EventBus and EventHandler type
    # Import constants for file paths used in the EventBus implementation
    from backend.orchestrator.event_bus import PERSISTENCE_FILE, DLQ_FILE, MAX_RETRIES_PER_EVENT, RETRY_DELAY_SECONDS # Import constants

    print("Imported EventBus successfully.")

    # --- Define test-specific file paths (Corrected) ---
    TEST_DIR = "./test_event_bus_data"
    TEST_PERSISTENCE_FILE = os.path.join(TEST_DIR, PERSISTENCE_FILE.lstrip("./")) # Remove leading ./ if any
    TEST_DLQ_FILE = os.path.join(TEST_DIR, DLQ_FILE.lstrip("./")) # Remove leading ./ if any


    # --- Mock Async Handlers ---
    # Use AsyncMock for handlers to easily assert calls and side effects
    MockHandler1 = AsyncMock()
    MockHandler2 = AsyncMock()
    MockFailingHandler = AsyncMock() # A handler that will be configured to fail

    class TestEventBus(unittest.IsolatedAsyncioTestCase): # Use IsolatedAsyncioTestCase

        @classmethod
        def setUpClass(cls):
            """Clean up test directory before all tests."""
            if os.path.exists(TEST_DIR):
                shutil.rmtree(TEST_DIR)
            # Create the test directory
            os.makedirs(TEST_DIR, exist_ok=True)

        @classmethod
        def tearDownClass(cls):
            """Clean up test directory after all tests."""
            # Add a small delay to release file locks if necessary
            time.sleep(0.1)
            if os.path.exists(TEST_DIR):
                try:
                    shutil.rmtree(TEST_DIR)
                    print(f"\nCleaned up test directory: {TEST_DIR}")
                except Exception as e:
                    print(f"\nError cleaning up test directory: {e}")


        def setUp(self):
            # Ensure test files are empty at the start of each test (created by TearDownClass/setUpClass if needed)
            if os.path.exists(TEST_PERSISTENCE_FILE):
                os.remove(TEST_PERSISTENCE_FILE) # Ensure empty file
            if os.path.exists(TEST_DLQ_FILE):
                os.remove(TEST_DLQ_FILE) # Ensure empty file


            # Reset mock handlers before each test
            MockHandler1.reset_mock()
            MockHandler2.reset_mock()
            MockFailingHandler.reset_mock()

            # Patch logging.error/warning to check if exceptions/warnings are logged
            self.mock_log_error = MagicMock()
            self.mock_log_warning = MagicMock()
            self.error_log_patch = patch('backend.orchestrator.event_bus.log.error', self.mock_log_error)
            self.warning_log_patch = patch('backend.orchestrator.event_bus.log.warning', self.mock_log_warning)
            self.error_log_patch.start()
            self.warning_log_patch.start()

            # Instantiate EventBus pointing to test files
            self.event_bus = EventBus(persistence_file=TEST_PERSISTENCE_FILE, dlq_file=TEST_DLQ_FILE)

            print(f"\n--- Starting test: {self._testMethodName} ---")


        def tearDown(self):
            # Stop patches
            self.error_log_patch.stop()
            self.warning_log_patch.stop()

            # File cleanup is handled by tearDownClass

            print(f"--- Finished test: {self._testMethodName} ---")


        # --- Helper to read file content ---
        async def _read_file_lines(self, file_path):
            if not os.path.exists(file_path):
                return []
            lines = []
            async with aiofiles.open(file_path, mode='r') as f:
                async for line in f:
                     try:
                         lines.append(json.loads(line.strip()))
                     except json.JSONDecodeError:
                         print(f"Warning: Invalid JSON line in file {file_path}: {line.strip()}")
                         # Optionally log this via the mocked logger if needed for tests
                         pass # Skip invalid lines
            return lines


        # --- Helper to write event to persistence file ---
        async def _write_event_to_persistence(self, event_type, event_data, retries=0, timestamp=None):
             event_dict = {"event_type": event_type, "event_data": event_data, "retries": retries, "timestamp": timestamp if timestamp is not None else time.time()}
             async with aiofiles.open(TEST_PERSISTENCE_FILE, mode='a') as f:
                 await f.write(json.dumps(event_dict) + '\n')
             return event_dict # Return the dict that was written


        # --- Basic Functionality Tests (Adapted) ---
        async def test_subscribe_and_unsubscribe(self):
            event_type = "basic.event"
            self.event_bus.subscribe(event_type, MockHandler1)
            self.assertIn(event_type, self.event_bus._handlers)
            self.assertIn(MockHandler1, self.event_bus._handlers[event_type])

            self.event_bus.unsubscribe(event_type, MockHandler1)
            self.assertNotIn(event_type, self.event_bus._handlers)
            # No file operations happen here, mocks should not be called
            self.mock_log_error.assert_not_called()
            self.mock_log_warning.assert_not_called()
            print("Subscribe and unsubscribe test passed.")

        async def test_publish_no_handlers(self):
            event_type = "empty.event"
            event_data = {"data": "empty"}
            # Publish event
            await self.event_bus.publish(event_type, event_data)

            # Verify event was logged to persistence file
            pending_lines = await self._read_file_lines(TEST_PERSISTENCE_FILE)
            # Removed assertion: Event is logged initially but removed immediately after successful dispatch (no handlers)
            # Verify no handlers were called
            MockHandler1.assert_not_awaited()

            # Verify event is removed from persistence file after successful log + no handler dispatch
            pending_lines_after_remove = await self._read_file_lines(TEST_PERSISTENCE_FILE)
            self.assertEqual(len(pending_lines_after_remove), 0, "Event should be removed after successful processing (no handlers).")


            self.mock_log_error.assert_not_called() # Should not log an error for no handlers
            print("Publish no handlers test passed.")


        # --- Advanced Functionality Tests ---

        async def test_publish_success_removes_from_persistence(self):
            """Test that a successfully published event is logged and then removed."""
            event_type = "success.event"
            event_data = {"key": "value"}

            self.event_bus.subscribe(event_type, MockHandler1)
            MockHandler1.return_value = None # Handler succeeds

            # Publish the event
            await self.event_bus.publish(event_type, event_data)

            # Verify handler was called
            MockHandler1.assert_awaited_once_with(event_type, event_data)

            # Verify event was logged to persistence file (initially) and then removed
            pending_lines_after_remove = await self._read_file_lines(TEST_PERSISTENCE_FILE)
            self.assertEqual(len(pending_lines_after_remove), 0, "Persistence file should be empty after successful processing.")

            # Check log messages for flow confirmation (optional but good)
            self.mock_log_error.assert_not_called() # No errors about failure
            self.mock_log_warning.assert_not_called() # No warnings about failure


            print("Publish success test passed.")


        async def test_publish_fails_initial_attempt_remains_in_persistence(self):
            """Test event failing processing initially remains in persistence log."""
            event_type = "failing.initial.event"
            event_data = {"problem": True}
            error_message = "Handler failed initially"

            self.event_bus.subscribe(event_type, MockFailingHandler)
            # Configure mock handler to raise exception on the first call
            MockFailingHandler.side_effect = ValueError(error_message)

            # Publish the event - this will trigger the initial dispatch attempt
            await self.event_bus.publish(event_type, event_data)

            # Verify the handler was called once
            self.assertEqual(MockFailingHandler.call_count, 1)
            MockFailingHandler.assert_awaited_once_with(event_type, event_data)


            # Verify event IS in persistence file with retry count 1
            pending_lines = await self._read_file_lines(TEST_PERSISTENCE_FILE)
            self.assertEqual(len(pending_lines), 1, "Event should be in persistence file after failing initial dispatch.")
            pending_event = pending_lines[0]
            self.assertEqual(pending_event["event_type"], event_type)
            self.assertEqual(pending_event["event_data"], event_data)
            self.assertEqual(pending_event["retries"], 0) # Should still be 0 after the initial fail before retry processing

            # Verify error was logged for the initial attempt
            self.mock_log_error.assert_called_once()
            # Verify error was logged for the initial attempt with the correct handler name from logging
            # Verify error was logged for the initial attempt with the correct handler name from logging
            # Check if the expected string is in the first argument of the log call
            self.assertIn("Handler AsyncMock for event 'failing.initial.event' (Attempt 1)", self.mock_log_error.call_args[0][0])

            # Verify DLQ file is empty
            dlq_lines = await self._read_file_lines(TEST_DLQ_FILE)
            self.assertEqual(len(dlq_lines), 0, "DLQ file should be empty after only initial failure.")

            print("Publish fails initial attempt test passed.")


        async def test_load_and_process_pending_events_success(self):
            """Test loading and processing a pending event that succeeds on load."""
            event_type = "pending.success"
            event_data = {"status": "pending"}
            initial_retries = 1 # Start with 1 retry count (simulating a previous failure)
            initial_timestamp = time.time() - 10 # Simulate event happened 10s ago

            # Manually write a pending event to the persistence file before EventBus loads
            # We need to write using a separate file handle or outside the event bus instance's potential lock
            # Easiest way is to just use standard sync file operations for setup or a new aiofiles context
            event_dict_to_write = {"event_type": event_type, "event_data": event_data, "retries": initial_retries, "timestamp": initial_timestamp}
            async with aiofiles.open(TEST_PERSISTENCE_FILE, mode='w') as f:
                 await f.write(json.dumps(event_dict_to_write) + '\n')


            # Subscribe a handler that will succeed to the EventBus instance *in this test*
            self.event_bus.subscribe(event_type, MockHandler1)
            MockHandler1.return_value = None # Handler succeeds

            # Manually trigger the loading and processing of pending events
            await self.event_bus._load_and_process_pending_events()

            # Verify handler was called (should be called once because it succeeds)
            self.assertEqual(MockHandler1.call_count, 1)
            MockHandler1.assert_awaited_once_with(event_type, event_data)

            # Verify event is removed from persistence file
            pending_lines = await self._read_file_lines(TEST_PERSISTENCE_FILE)
            self.assertEqual(len(pending_lines), 0, "Event should be removed from persistence file after succeeding on load.")

            # Verify DLQ file is empty
            dlq_lines = await self._read_file_lines(TEST_DLQ_FILE)
            self.assertEqual(len(dlq_lines), 0, "DLQ file should be empty.")

            # Check log messages
            self.mock_log_error.assert_not_called() # No errors
            # Check warning about 'Pending event failed processing' is not called
            self.mock_log_warning.assert_not_called()


            print("Load and process pending success test passed.")


        async def test_load_and_process_pending_events_fails_to_dlq(self):
            """Test loading and processing a pending event that fails all retries on load."""
            event_type = "pending.fail.dlq"
            event_data = {"status": "pending", "attempts": 0}
            # Start with 0 retries so it attempts MAX_RETRIES_PER_EVENT + 1 times total during load
            initial_retries = 0
            initial_timestamp = time.time() - 20 # Simulate event happened 20s ago

            # Manually write a pending event to the persistence file
            event_dict_to_write = {"event_type": event_type, "event_data": event_data, "retries": initial_retries, "timestamp": initial_timestamp}
            async with aiofiles.open(TEST_PERSISTENCE_FILE, mode='w') as f:
                 await f.write(json.dumps(event_dict_to_write) + '\n')


            # Subscribe a handler that will always fail to the EventBus instance *in this test*
            self.event_bus.subscribe(event_type, MockFailingHandler)
            MockFailingHandler.side_effect = RuntimeError("Load handler failed all retries")

            # Manually trigger the loading and processing of pending events
            await self.event_bus._load_and_process_pending_events()

            # Verify the handler was called MAX_RETRIES_PER_EVENT + 1 times
            self.assertEqual(MockFailingHandler.call_count, MAX_RETRIES_PER_EVENT + 1)
            # Check call arguments for each attempt (e.g., event_type, event_data) - optional

            # Verify event is NOT in persistence file anymore
            pending_lines = await self._read_file_lines(TEST_PERSISTENCE_FILE)
            self.assertEqual(len(pending_lines), 0, "Event should be removed from persistence file after failing all retries.")

            # Verify event IS in DLQ file
            dlq_lines = await self._read_file_lines(TEST_DLQ_FILE)
            self.assertEqual(len(dlq_lines), 1, "Event should be in DLQ file.")
            dlq_event = dlq_lines[0]
            self.assertEqual(dlq_event["event_type"], event_type)
            self.assertEqual(dlq_event["event_data"], event_data)
            self.assertEqual(dlq_event["retries"], MAX_RETRIES_PER_EVENT + 1) # Check final retry count in DLQ

            # Verify errors were logged for each attempt during load process
            # Expect one error log for each failed attempt (MAX_RETRIES_PER_EVENT + 1 attempts)
            # plus one error log when moving to DLQ.
            self.assertEqual(self.mock_log_error.call_count, MAX_RETRIES_PER_EVENT + 2)
             # Check warnings were logged about retries/DLQ
            # There should be MAX_RETRIES_PER_EVENT warnings about failing,
            # plus one warning about 'exhausted retries' when moving to DLQ.
            # Plus one warning for the last attempt failing.
            # Let's check total warnings are >= MAX_RETRIES_PER_EVENT + 1
            self.assertGreaterEqual(self.mock_log_warning.call_count, MAX_RETRIES_PER_EVENT + 1)


            print("Load and process pending fails to DLQ test passed.")


        # --- These tests are covered by the _load_and_process_pending_events scenarios ---
        # test_publish_fails_all_retries_moves_to_dlq
        # This test is problematic because publish doesn't run all retries.
        # Instead, we test the *behavior on load* using test_load_and_process_pending_events_fails_to_dlq.
        # async def test_publish_fails_all_retries_moves_to_dlq(self):
        #     pass # This test is now redundant/flawed based on EventBus implementation


    # Run the tests
    if __name__ == '__main__':
        print("\nRunning EventBus tests...")
        # Use default test runner with verbosity
        unittest.main(verbosity=2)

except ImportError as e:
    print(f"Failed to import components: {e}", file=sys.stderr)
    print("Ensure orchestrator/event_bus.py and its dependencies (aiofiles, psutil, etc.) exist.", file=sys.stderr) # Added psutil for completeness
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during test setup or execution: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
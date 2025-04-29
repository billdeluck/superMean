# Test Snippet File: backend/utils/logger_test.py
# Description: Verifies that the standard Python logger can be set up and used.
# Command: python -m backend.utils.logger_test

import sys
import os
import logging
import time
# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Set environment for testing to ensure console output
os.environ["ENVIRONMENT"] = "testing"
test_log_file = "logs/test_snippet.log"
# Store the logger instance to properly close handlers later
test_logger = None

try:
    from backend.utils.logger import setup_logger

    print("Imported setup_logger successfully.")

    # Setup a logger instance for testing
    test_logger = setup_logger(
        name="snippet_test_logger",
        log_level_str="DEBUG",
        log_file=test_log_file
    )
    print(f"Logger instance '{test_logger.name}' created.")
    print(f"Log level set to: {logging.getLevelName(test_logger.level)}")
    print(f"Handlers attached: {test_logger.handlers}")

    # Log messages
    test_logger.debug("Test debug message from snippet.")
    test_logger.info("Test info message from snippet.")
    test_logger.warning("Test warning message from snippet.")
    test_logger.error("Test error message from snippet.")

    print(f"Log messages sent. Check console output and the file '{test_log_file}'.")

    # Verify file creation and content (basic check)
    time.sleep(0.1) # Give a moment for logs to flush
    if os.path.exists(test_log_file):
        print(f"Log file '{test_log_file}' exists.")
        with open(test_log_file, 'r') as f:
            content = f.read()
            if "Test info message from snippet." in content:
                print("Log file content verified successfully.")
            else:
                print("Warning: Could not verify expected content in log file.")
    else:
        print(f"Warning: Log file '{test_log_file}' was not created.")

    print("Logger test snippet finished.")

except ImportError as e:
    print(f"Failed to import setup_logger: {e}")
    print("Ensure backend/utils/logger.py exists and has no syntax errors.")
except Exception as e:
    print(f"An error occurred during logger test: {e}")
finally:
    # Clean up the test log file and directory
    log_dir = os.path.dirname(test_log_file)
    if os.path.exists(test_log_file):
        try:
            # Close handlers to release file lock on Windows
            if test_logger and test_logger.handlers:
                for handler in list(test_logger.handlers): # Iterate over a copy
                    handler.close()
                    test_logger.removeHandler(handler)
            else:
                 # If logger wasn't created, try opening/closing file handler directly if possible
                 # This part is tricky without knowing if setup_logger failed before/after creating the handler
                 print("Logger instance not available for handler closing.")

            # Attempt removal after closing handlers
            os.remove(test_log_file)
            print(f"Cleaned up test log file: {test_log_file}")
            # Try removing the directory if empty
            if os.path.exists(log_dir) and not os.listdir(log_dir):
                 os.rmdir(log_dir)
                 print(f"Cleaned up test log directory: {log_dir}")
        except Exception as cleanup_error:
            print(f"Warning: Could not fully clean up test logs: {cleanup_error}")
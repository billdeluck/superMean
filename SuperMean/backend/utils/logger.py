# Directory: backend/utils/
# File: logger.py
# Description: Configures the application logger using standard Python logging.

import logging
import os
from logging.handlers import RotatingFileHandler
import sys  # Required for StreamHandler
# If you want to configure via settings, uncomment the next line
# from backend.utils.config_loader import get_settings

# Define log levels mapping
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# --- Logger Setup Function ---
def setup_logger(
    name: str = "supermean_logger",
    log_level_str: str = "INFO", # Default log level string
    log_file: str = "logs/backend.log", # Default log file path
    max_bytes: int = 10*1024*1024, # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Sets up a rotating file logger.

    Args:
        name: The name of the logger.
        log_level_str: The minimum logging level (e.g., 'INFO', 'DEBUG').
        log_file: The path to the log file.
        max_bytes: The maximum size of the log file before rotation.
        backup_count: The number of backup log files to keep.

    Returns:
        A configured logging.Logger instance.
    """
    # --- Optional: Load from settings ---
    # settings = get_settings()
    # log_level_str = settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else log_level_str
    # log_file = settings.LOG_FILE_PATH if hasattr(settings, 'LOG_FILE_PATH') else log_file
    # --- End Optional ---

    # Get the logger
    logger = logging.getLogger(name)

    # Prevent adding multiple handlers if the logger already exists
    if logger.handlers:
        # Clear existing handlers if reconfiguration is needed, or just return
        # For simplicity, we'll just return the existing logger if handlers exist
        return logger

    # Set the logging level
    log_level = LOG_LEVELS.get(log_level_str.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create a rotating file handler
    # Ensure the directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"Warning: Could not create log directory {log_dir}. Error: {e}")
            # Fallback to current directory if needed, or handle error
            log_file = os.path.basename(log_file)


    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        # Add the file handler to the logger
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file handler for {log_file}. Error: {e}")
        # Continue without file logging or raise an error


    # Optionally add a console handler for easier debugging during development
    # Check environment variable or config setting
    is_production = os.environ.get("ENVIRONMENT", "").lower() == "production"
    # Or use settings: is_production = settings.ENVIRONMENT == "production"

    if not is_production:
        console_handler = logging.StreamHandler(sys.stdout) # Use stdout or stderr
        console_handler.setFormatter(formatter)
        # Set console level potentially higher or lower than file level if needed
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)

    # Prevent log messages from propagating to the root logger if needed
    # logger.propagate = False

    return logger

# --- Pre-configured Logger Instance (optional but convenient) ---
# You can export a ready-to-use logger instance configured with defaults
# log = setup_logger()

# --- Example Usage (for direct execution) ---
if __name__ == "__main__":
    # Example of setting up and using the logger
    # Set ENVIRONMENT=development or remove the check above to see console output
    os.environ["ENVIRONMENT"] = "development"

    main_logger = setup_logger(name="main_test", log_level_str="DEBUG", log_file="logs/test_main.log")
    main_logger.info("Logger setup complete via __main__.")
    main_logger.debug("This is a debug message.")
    main_logger.warning("This is a warning message.")
    main_logger.error("This is an error message.")
    try:
        1 / 0
    except ZeroDivisionError:
        main_logger.exception("Caught an exception!")

    # Example of getting the same logger instance elsewhere
    another_logger = logging.getLogger("main_test")
    another_logger.info("Accessed the logger again.")
"""
This module configures and sets up logging for the CLASSIC application.

The module is responsible for setting up a logger with file and console handlers,
applying appropriate log levels, and formatting. File logging includes a timestamped
log file stored in a designated directory. Console logging provides messages for
warnings and higher severity levels. If the file logging setup fails, the system
falls back to console logging only.

By default, file logging is set to INFO level. Debug logging can be enabled via
the 'Debug Messages' setting in CLASSIC Settings.yaml, which is activated after
application initialization.

Functions:
    configure_logging: Configures the provided logger for application use.
    enable_debug_logging: Enables DEBUG level logging on file handlers.
"""

import datetime
import logging
import sys
from logging import Logger
from pathlib import Path


def configure_logging(classic_logger: Logger) -> None:
    """
    Configure logging for the given logger instance with file and console handlers.

    Sets up file-based logging at INFO level by default (can be changed to DEBUG via
    the 'Debug Messages' setting using enable_debug_logging()). Console logging is
    set to WARNING level for user-visible messages.

    This function also configures the root logger to ensure all child loggers (created
    with logging.getLogger(__name__)) properly propagate their messages to the log file.

    Args:
        classic_logger: The logger instance to configure, typically an instance of `logging.Logger`.

    Note:
        To enable DEBUG level logging, call enable_debug_logging() after loading settings
        if the 'Debug Messages' setting is enabled.
    """
    # Configure log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Remove any existing handlers from both the specific logger and root logger
    classic_logger.handlers = []
    logging.root.handlers = []

    # Set base log level for both specific and root logger
    classic_logger.setLevel(logging.DEBUG)
    logging.root.setLevel(logging.DEBUG)

    # Disable propagation for the CLASSIC logger to avoid duplicate messages
    # (since it has its own handlers and doesn't need to propagate to root)
    classic_logger.propagate = False

    # Create file handler for debug logs
    try:
        from ClassicLib import GlobalRegistry

        log_dir = Path(GlobalRegistry.get_local_dir()) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped log file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"classic_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)  # Default to INFO; use enable_debug_logging() for DEBUG
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)

        # Add handler to both specific logger and root logger
        # This ensures all child loggers (created with getLogger(__name__)) also log to file
        classic_logger.addHandler(file_handler)
        logging.root.addHandler(file_handler)
    except Exception as e:  # noqa: BLE001
        # If file logging fails, continue with console only
        print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)

    # Create console handler for warnings and above
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    # Add console handler to both specific logger and root logger
    classic_logger.addHandler(console_handler)
    logging.root.addHandler(console_handler)

    # Log initial message
    classic_logger.info("Logging configured successfully (INFO level)")
    logging.root.debug("Root logger configured successfully")


def enable_debug_logging(classic_logger: Logger) -> None:
    """
    Enable DEBUG level logging on file handlers.

    This function should be called after settings are loaded if the
    'Debug Messages' setting is enabled in CLASSIC Settings.yaml.
    It switches file handlers from INFO to DEBUG level, allowing
    detailed diagnostic messages to be recorded.

    Args:
        classic_logger: The logger instance to modify.

    Example:
        >>> from ClassicLib.Logger import logger
        >>> from ClassicLib.Utils.logging_utils import enable_debug_logging
        >>> # After loading settings and determining debug mode is enabled:
        >>> enable_debug_logging(logger)
    """
    debug_enabled = False
    for handler in classic_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(logging.DEBUG)
            debug_enabled = True

    # Also update root logger file handlers
    for handler in logging.root.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(logging.DEBUG)
            debug_enabled = True

    if debug_enabled:
        classic_logger.debug("Debug logging enabled via settings")

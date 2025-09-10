"""Logging configuration utilities."""

import datetime
import logging
import sys
from logging import Logger
from pathlib import Path


def configure_logging(classic_logger: Logger) -> None:
    """
    Configures logging settings for the CLASSIC application.

    Sets up file and console handlers with appropriate formatting and
    log levels based on application state.

    Args:
        classic_logger: The logger instance to configure

    Returns:
        None
    """
    # Configure log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Remove any existing handlers
    classic_logger.handlers = []

    # Set base log level
    classic_logger.setLevel(logging.DEBUG)

    # Create file handler for debug logs
    try:
        from ClassicLib import GlobalRegistry

        log_dir = Path(GlobalRegistry.get_local_dir()) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped log file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"classic_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        classic_logger.addHandler(file_handler)
    except Exception as e:  # noqa: BLE001
        # If file logging fails, continue with console only
        print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)

    # Create console handler for warnings and above
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    classic_logger.addHandler(console_handler)

    # Log initial message
    classic_logger.debug("Logging configured successfully")

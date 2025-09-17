"""
Provides a logger instance for centralized logging functionality.

This module initializes and provides a configured instance of a logger
using Python's built-in `logging` module. The logger instance is named
'CLASSIC' and can be used across different parts of the application to
log messages consistently and adhere to centralized logging practices.

Attributes:
    logger (logging.Logger): A configured logger instance named 'CLASSIC'.
"""

import logging

logger: logging.Logger = logging.getLogger("CLASSIC")

"""CLASSIC Terminal User Interface Package."""

from .app import CLASSICTuiApp
from .constants import UNICODE_TERMINAL_TYPES
from .input_validator import InputValidator

__version__ = "1.0.0"

__all__ = [
    "UNICODE_TERMINAL_TYPES",
    "CLASSICTuiApp",
    "InputValidator",
]

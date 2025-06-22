"""Compatibility module for handling optional dependencies.

This module provides utilities for checking and working with optional
dependencies like PySide6, making ClassicLib usable in both GUI and CLI modes.
"""

from typing import TYPE_CHECKING, Any

# Check for PySide6 availability
try:
    # noinspection PyUnresolvedReferences
    import importlib.util

    import PySide6

    HAS_PYSIDE6 = importlib.util.find_spec("PySide6.QtCore") is not None
    PYSIDE6_VERSION = PySide6.__version__ if HAS_PYSIDE6 else None
except ImportError:
    HAS_PYSIDE6 = False
    PYSIDE6_VERSION = None

# Check for tqdm availability
try:
    # noinspection PyUnresolvedReferences
    import tqdm

    HAS_TQDM = True
    TQDM_VERSION = tqdm.__version__
except ImportError:
    HAS_TQDM = False
    TQDM_VERSION = None


def check_gui_requirements() -> tuple[bool, str]:
    """Check if all GUI requirements are met.

    Returns:
        Tuple of (requirements_met, error_message)
        If requirements are met, error_message will be empty string.
    """
    if not HAS_PYSIDE6:
        return False, "PySide6 is not installed. Install with: pip install PySide6"

    # Check for minimum PySide6 version if needed
    # Example: if version < "6.0.0": return False, "PySide6 version 6.0.0+ required"

    return True, ""


def import_gui_component(component_name: str) -> Any:
    """Safely import a GUI component.

    Args:
        component_name: Name of the component to import from ClassicLib.gui

    Returns:
        The imported component or None if PySide6 is not available

    Raises:
        ImportError: If component doesn't exist in ClassicLib.gui
    """
    if not HAS_PYSIDE6:
        return None

    from ClassicLib import gui

    return getattr(gui, component_name, None)


# Type stubs for when PySide6 is not available
if TYPE_CHECKING or not HAS_PYSIDE6:

    class QObject:
        """Stub for PySide6.QtCore.QObject when PySide6 is not available."""

    class QWidget:
        """Stub for PySide6.QtWidgets.QWidget when PySide6 is not available."""

    class Signal:
        """Stub for PySide6.QtCore.Signal when PySide6 is not available."""

        def __init__(self, *args: Any) -> None:
            pass

        def emit(self, *args: Any) -> None:
            pass

        def connect(self, func: Any) -> None:
            pass

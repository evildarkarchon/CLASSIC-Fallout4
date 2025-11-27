"""Qt compatibility layer for environments without PySide6.

This module provides Qt type stubs and the HAS_QT flag to allow code
to work in environments without PySide6 installed.

Note: This module is kept for backward compatibility. The GUIBackend
and QtProgressHandler now handle Qt integration directly.
"""

from typing import Any

# Try to import PySide6 for GUI mode
try:
    from PySide6.QtCore import QObject, QThread, Signal  # pyright: ignore[reportAssignmentType]
    from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget  # pyright: ignore[reportAssignmentType]

    HAS_QT = True
except ImportError:
    HAS_QT = False

    # Define stub classes for type checking when Qt is not available
    class QObject:
        """Stub for QObject when PySide6 is not available."""

    class QWidget:
        """Stub for QWidget when PySide6 is not available."""

    class QThread:
        """Stub for QThread when PySide6 is not available."""

        @staticmethod
        def currentThread() -> "QThread":  # pyright: ignore[reportReturnType]
            """Return the current thread (stub)."""

    class QMessageBox:
        """Stub for QMessageBox when PySide6 is not available."""

        class Icon:
            """Message box icon types."""

            Information = 0
            Warning = 1
            Critical = 2

        def __init__(
            self,
            icon: Any = None,
            title: str = "",
            text: str = "",
            parent: QWidget | None = None,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            """Initialize stub message box."""

        def setDetailedText(self, text: str) -> None:
            """Set detailed text (stub)."""

        def setWindowTitle(self, title: str) -> None:
            """Set window title (stub)."""

        def exec(self) -> int:  # noqa: PLR6301
            """Execute dialog (stub)."""
            return 0

    class QProgressDialog:
        """Stub for QProgressDialog when PySide6 is not available."""

        def __init__(
            self,
            labelText: str = "",
            cancelButtonText: str = "",
            minimum: int = 0,
            maximum: int = 0,
            parent: QWidget | None = None,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            """Initialize stub progress dialog."""

        def setWindowTitle(self, title: str) -> None:
            """Set window title (stub)."""

        def setAutoClose(self, close: bool) -> None:
            """Set auto close (stub)."""

        def setAutoReset(self, reset: bool) -> None:
            """Set auto reset (stub)."""

        def setRange(self, minimum: int, maximum: int) -> None:
            """Set range (stub)."""

        def show(self) -> None:
            """Show dialog (stub)."""

        def hide(self) -> None:
            """Hide dialog (stub)."""

        def setValue(self, value: int) -> None:
            """Set value (stub)."""

        def setLabelText(self, text: str) -> None:
            """Set label text (stub)."""

        def wasCanceled(self) -> bool:  # noqa: PLR6301
            """Check if canceled (stub)."""
            return False

    class Signal:
        """Stub for Signal when PySide6 is not available."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize stub signal."""

        def emit(self, *args: Any) -> None:
            """Emit signal (stub)."""

        def connect(self, func: Any) -> None:
            """Connect signal (stub)."""


__all__ = [
    "HAS_QT",
    "QMessageBox",
    "QObject",
    "QProgressDialog",
    "QThread",
    "QWidget",
    "Signal",
]

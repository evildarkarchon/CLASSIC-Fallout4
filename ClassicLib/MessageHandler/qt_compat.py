"""Qt compatibility layer for environments without PySide6."""

from typing import Any

# Try to import PySide6 for GUI mode
try:
    from PySide6.QtCore import QObject, QThread, Signal
    from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget

    HAS_QT = True
except ImportError:
    HAS_QT = False

    # Define dummy classes for type checking when Qt is not available
    class QObject:
        pass

    class QWidget:
        pass

    class QThread:
        # noinspection PyPep8Naming
        @staticmethod
        def currentThread() -> QThread:
            pass

    # noinspection PyUnusedLocal,PyPep8Naming
    class QMessageBox:
        class Icon:
            Information = 0
            Warning = 1
            Critical = 2

        def __init__(
            self, icon: Any = None, title: str = "", text: str = "", parent: QWidget | None = None, *args: Any, **kwargs: Any
        ) -> None:
            pass

        def setDetailedText(self, text: str) -> None:
            pass

        def setWindowTitle(self, title: str) -> None:
            pass

        # noinspection PyMethodMayBeStatic
        def exec(self) -> int:
            return 0

    # noinspection PyPep8Naming,PyUnusedLocal
    class QProgressDialog:
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
            pass

        def setWindowTitle(self, title: str) -> None:
            pass

        def setAutoClose(self, close: bool) -> None:
            pass

        def setAutoReset(self, reset: bool) -> None:
            pass

        def setRange(self, minimum: int, maximum: int) -> None:
            pass

        def show(self) -> None:
            pass

        def hide(self) -> None:
            pass

        def setValue(self, value: int) -> None:
            pass

        def setLabelText(self, text: str) -> None:
            pass

    class Signal:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def emit(self, *args: Any) -> None:
            pass

        def connect(self, func: Any) -> None:
            pass


__all__ = [
    "HAS_QT",
    "QObject",
    "QWidget",
    "QThread",
    "QMessageBox",
    "QProgressDialog",
    "Signal",
]

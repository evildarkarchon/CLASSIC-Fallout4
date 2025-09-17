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
    class QObject:  # noqa: D101
        pass

    class QWidget:  # noqa: D101
        pass

    class QThread:  # noqa: D101
        # noinspection PyPep8Naming
        @staticmethod
        def currentThread() -> "QThread":  # noqa: D102
            pass

    # noinspection PyUnusedLocal,PyPep8Naming
    class QMessageBox:  # noqa: D101
        class Icon:  # noqa: D106
            Information = 0
            Warning = 1
            Critical = 2

        def __init__(  # noqa: D107
            self, icon: Any = None, title: str = "", text: str = "", parent: QWidget | None = None, *args: Any, **kwargs: Any
        ) -> None:
            pass

        def setDetailedText(self, text: str) -> None:  # noqa: D102
            pass

        def setWindowTitle(self, title: str) -> None:  # noqa: D102
            pass

        # noinspection PyMethodMayBeStatic
        def exec(self) -> int:  # noqa: D102, PLR6301
            return 0

    # noinspection PyPep8Naming,PyUnusedLocal
    class QProgressDialog:  # noqa: D101
        def __init__(  # noqa: D107
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

        def setWindowTitle(self, title: str) -> None:  # noqa: D102
            pass

        def setAutoClose(self, close: bool) -> None:  # noqa: D102
            pass

        def setAutoReset(self, reset: bool) -> None:  # noqa: D102
            pass

        def setRange(self, minimum: int, maximum: int) -> None:  # noqa: D102
            pass

        def show(self) -> None:  # noqa: D102
            pass

        def hide(self) -> None:  # noqa: D102
            pass

        def setValue(self, value: int) -> None:  # noqa: D102
            pass

        def setLabelText(self, text: str) -> None:  # noqa: D102
            pass

    class Signal:  # noqa: D101
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
            pass

        def emit(self, *args: Any) -> None:  # noqa: D102
            pass

        def connect(self, func: Any) -> None:  # noqa: D102
            pass


__all__ = [
    "HAS_QT",
    "QMessageBox",
    "QObject",
    "QProgressDialog",
    "QThread",
    "QWidget",
    "Signal",
]

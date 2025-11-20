"""Qt compatibility layer for environments without PySide6."""

from typing import Any

# Try to import PySide6 for GUI mode
try:
    from PySide6.QtCore import QObject, QThread, Signal  # pyright: ignore[reportAssignmentType]
    from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget  # pyright: ignore[reportAssignmentType]

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
        def currentThread() -> "QThread":  # pyright: ignore[reportReturnType]
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
        def exec(self) -> int:  # noqa: PLR6301
            return 0

    # noinspection PyPep8Naming,PyUnusedLocal
    class QProgressDialog:
        """Provides a dialog that displays the progress of an ongoing operation.

        The QProgressDialog class represents a modal or non-modal dialog that can be
        used to show the progress of a lengthy operation. It includes a progress bar,
        a descriptive label, and an optional cancel button. The progress dialog can be
        configured with custom ranges, text, and behavior properties, making it
        suitable for varied user interface requirements.
        """

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
            """
            Initializes an instance of the class with the given parameters.

            This constructor sets up the class with default or specified values for its
            configuration. The provided parameters enable customization of the instance's
            behavior and appearance. All optional arguments have appropriate default
            values.

            Args:
                labelText: A string to specify the initial text label to display.
                cancelButtonText: A string to set the text of the cancel button.
                minimum: An integer value for the minimum allowable value in the range.
                maximum: An integer value for the maximum allowable value in the range.
                parent: A QWidget or None, indicating the parent of this widget.
                *args: Additional positional arguments for further customization.
                **kwargs: Additional keyword arguments for further customization.
            """

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
    "QMessageBox",
    "QObject",
    "QProgressDialog",
    "QThread",
    "QWidget",
    "Signal",
]

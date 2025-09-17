"""
Context manager for progress tracking that works in both GUI and CLI modes.

This module provides a context manager that adapts to either GUI (Qt-based)
or CLI environments, displaying appropriate progress indicators based on
the runtime conditions and the environment's capabilities. It supports
configurable progress bars and provides compatibility with both thread-safe
Qt progress dialogs and CLI text-based progress bars, with the optional
use of the tqdm library for enhanced CLI support.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from ClassicLib.MessageHandler.cli_progress import CLIProgressBar
from ClassicLib.MessageHandler.qt_compat import HAS_QT, QProgressDialog, QThread

if TYPE_CHECKING:
    from ClassicLib.MessageHandler.handler import MessageHandler

# Try to import tqdm for enhanced CLI progress bars
try:
    # noinspection PyUnresolvedReferences
    from tqdm import tqdm as TqdmProgress

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

    # Define dummy tqdm for type checking when not available
    class TqdmProgress:  # noqa: D101
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
            pass

        def update(self, n: int = 1) -> None:  # noqa: D102
            pass

        def set_description(self, desc: str) -> None:  # noqa: D102
            pass

        def close(self) -> None:  # noqa: D102
            pass


class ProgressContext:
    """Manage progress indicators in GUI or CLI environments.

    This class provides context management for displaying a progress bar,
    handling both GUI and CLI environments. Depending on the environment,
    it creates and updates the relevant progress bar type. In GUI mode and
    when using PySide6, it initializes a `QProgressDialog`. For CLI mode, it
    creates a progress bar using `tqdm` or falls back to a basic CLI progress
    bar.

    Attributes:
        handler (MessageHandler): The message handler instance managing
            communication between the context and other systems.
        description (str): A textual description of the operation being
            performed.
        total (int | None): The total number of items to process, or `None`
            for an indeterminate progress bar.
        current (int): The current progress state, updated as items are
            processed.
    """

    def __init__(self, handler: MessageHandler, description: str, total: int | None = None) -> None:
        """
        Initializes an object with attributes for managing progress tracking and display.

        Args:
            handler (MessageHandler): The handler to manage messages or tasks related to progress.
            description (str): A textual description for the operation or task.
            total (int | None): The total number of steps for the progress, or None if unspecified.
        """
        self.handler = handler
        self.description = description
        self.total = total
        self.current = 0
        self._progress_bar: TqdmProgress | CLIProgressBar | QProgressDialog | None = None
        self._using_qt_signals = False

    def __enter__(self) -> ProgressContext:
        """
        Context manager for establishing and managing a progress interface.

        When invoked, this method creates a progress interface suitable for the current environment,
        determined by whether the application is running in GUI or CLI mode. Depending on availability
        and requirements, progress can be shown via a GUI progress dialog (Qt-based) or in the CLI
        (using text-based progress bars). The method also accounts for settings enabled or disabled
        within the application and manages worker thread interactions if necessary.

        Returns:
            ProgressContext: The current instance of the progress context manager, allowing
            for chaining or further interaction within the context block.

        Raises:
            ImportError: If required dependencies or modules for specific environments are missing.
            RuntimeError: If GUI operations fail in a context where GUI mode is active.
        """
        # Check if CLI progress is disabled
        try:
            from ClassicLib.YamlSettingsCache import classic_settings

            disable_cli_progress = classic_settings(bool, "Disable CLI Progress") or False
        except (ImportError, FileNotFoundError, KeyError, TypeError):
            # If we can't load settings, default to showing progress
            disable_cli_progress = False

        if self.handler.is_gui_mode and HAS_QT:
            # Check if we're in the main thread and QApplication exists
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                is_main_thread = QThread.currentThread() == self.handler.main_thread

                if app is not None and is_main_thread:
                    # Create Qt progress dialog in main thread with QApplication available
                    self._progress_bar = QProgressDialog(self.description, "Cancel", 0, self.total or 0, self.handler.parent_widget)
                    self._progress_bar.setWindowTitle("Progress")
                    self._progress_bar.setAutoClose(True)
                    self._progress_bar.setAutoReset(True)
                    if self.total is None:
                        self._progress_bar.setRange(0, 0)  # Indeterminate
                    self._progress_bar.show()
                else:
                    # We're in a worker thread - use signals to create progress dialog in main thread
                    self.handler.progress_create_signal.emit(self.description, self.total or 0)
                    self._using_qt_signals = True
            except (ImportError, RuntimeError):
                # Fallback to CLI progress if Qt is not available or has issues
                # Suppress progress in GUI mode even if Qt fails
                self._progress_bar = None
        # CLI mode - only create progress bars if not disabled
        elif not disable_cli_progress:
            if HAS_TQDM:
                self._progress_bar = TqdmProgress(total=self.total, desc=self.description, file=sys.stdout)
            else:
                self._progress_bar = CLIProgressBar(self.description, self.total)

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Handles cleanup actions for the context manager, ensuring proper resource management
        depending on the attribute states and type of progress bar used.

        Args:
            exc_type: Any: The exception type, if an exception occurred during the context
                execution.
            exc_val: Any: The exception value, if an exception occurred during the context
                execution.
            exc_tb: Any: The traceback object, if an exception occurred during the context
                execution.

        """
        if self._using_qt_signals:
            self.handler.progress_close_signal.emit()
        elif self._progress_bar is not None:
            if HAS_QT and isinstance(self._progress_bar, QProgressDialog):
                self._progress_bar.hide()
            elif hasattr(self._progress_bar, "close"):
                self._progress_bar.close()  # type: ignore[reportAttributeAccessIssue]

    def update(self, n: int = 1, description: str | None = None) -> None:
        """
        Updates the progress value by a specified amount and optionally updates
        the description. This method handles the progress bar and Qt signals
        depending on the configuration of the object.

        Args:
            n (int): The number by which the current progress should be incremented.
                Defaults to 1.
            description (str | None): An optional description to update alongside
                the progress. If None, no description is updated.
        """
        self.current += n

        if self._using_qt_signals:
            self.handler.progress_signal.emit(self.current, description or "")
        elif self._progress_bar is not None:
            if HAS_QT and isinstance(self._progress_bar, QProgressDialog):
                self._progress_bar.setValue(self.current)
                if description:
                    self._progress_bar.setLabelText(description)
            elif hasattr(self._progress_bar, "update"):
                self._progress_bar.update(n)  # type: ignore
                if description and hasattr(self._progress_bar, "set_description"):
                    self._progress_bar.set_description(description)  # type: ignore[attr-defined]

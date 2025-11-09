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

# Try to import tqdm for enhanced CLI progress bars
try:
    # noinspection PyUnresolvedReferences
    from tqdm import tqdm as TqdmProgress  # type: ignore[assignment]

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

    # Define dummy tqdm for runtime when not available
    class TqdmProgress:  # type: ignore[no-redef]  # noqa: D101
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
            pass

        def update(self, n: int = 1) -> None:  # noqa: D102
            pass

        def set_description(self, desc: str) -> None:  # noqa: D102
            pass

        def close(self) -> None:  # noqa: D102
            pass


if TYPE_CHECKING:
    from ClassicLib.MessageHandler.handler import MessageHandler


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
        Initializes an instance of the class with the specified handler, description, and optional
        total value. Tracks current progress and manages optional progress visualization.

        Args:
            handler (MessageHandler): The handler responsible for managing messages during execution.
            description (str): A descriptive text for the operation, typically displayed in the
                progress visualization.
            total (int | None): The total number of units of work to be completed. Defaults to None,
                indicating that the total is unknown or undefined.
        """
        self.handler = handler
        self.description = description
        self.total = total
        self.current = 0
        self._progress_bar: TqdmProgress | CLIProgressBar | QProgressDialog | None = None
        self._using_qt_signals = False

        # Throttling for Qt signals to reduce cross-thread overhead
        self._last_update_time = 0.0
        self._update_interval = 0.05  # 50ms between updates (20 updates/sec max)

    def __enter__(self) -> ProgressContext:
        """
        Enters the progress context, initializing an appropriate progress tracking mechanism based
        on the environment (GUI or CLI). It handles GUI progress dialog creation for GUI environments
        and relies on CLI-based progress tracking (e.g., TQDM or custom CLI progress bar) for CLI environments,
        with fallback mechanisms in case of missing dependencies or errors.

        Raises:
            ImportError: If necessary modules are missing.
            RuntimeError: If there is an issue with threading or GUI initialization.
            FileNotFoundError: If the configuration file for CLI progress settings is missing.
            KeyError: If the relevant settings key is not found in the configuration file.
            TypeError: If the expected data type for a setting does not match.
            Exception: For general unexpected behaviors during initialization.

        Returns:
            ProgressContext: An initialized instance of the progress context ready for tracking progress.
        """
        # Check if CLI progress is disabled
        try:
            from ClassicLib.YamlSettingsCache import classic_settings

            disable_cli_progress = classic_settings(bool, "Disable CLI Progress") or False
        except (ImportError, FileNotFoundError, KeyError, TypeError, RuntimeError):
            # If we can't load settings, default to showing progress
            # RuntimeError can occur if called from async context
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
        Handles the cleanup process upon exiting a context managed block. Ensures proper closure
        of progress indicators or signals based on the situation when the context is exited.

        Args:
            exc_type (Any): The exception type, if any, raised within the context block.
            exc_val (Any): The exception value, providing details about the exception.
            exc_tb (Any): The traceback object associated with the exception.
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
        Updates the current progress and optionally emits signals or updates a progress bar
        based on the current state. Handles throttling for Qt signals to reduce overhead
        and updates graphical progress bars if available. Emits a description if provided.

        Args:
            n (int): The amount by which to increment the current progress. Defaults to 1.
            description (str | None): Optional description to accompany the update in cases
                where a description mechanism is provided (e.g., GUI progress bars or signals).
        """
        self.current += n

        if self._using_qt_signals:
            # Throttle Qt signals to reduce overhead - only emit at most every 50ms
            import time

            current_time = time.time()
            time_since_last = current_time - self._last_update_time

            # Always emit for last item or if enough time has passed
            is_last_item = self.total is not None and self.current >= self.total
            should_emit = is_last_item or time_since_last >= self._update_interval

            if should_emit:
                self.handler.progress_signal.emit(self.current, description or "")
                self._last_update_time = current_time
        elif self._progress_bar is not None:
            if HAS_QT and isinstance(self._progress_bar, QProgressDialog):
                self._progress_bar.setValue(self.current)
                if description:
                    self._progress_bar.setLabelText(description)
            elif hasattr(self._progress_bar, "update"):
                self._progress_bar.update(n)  # type: ignore
                if description and hasattr(self._progress_bar, "set_description"):
                    self._progress_bar.set_description(description)  # type: ignore[attr-defined]

    def was_cancelled(self) -> bool:
        """
        Check if the progress operation was cancelled by the user.

        Returns:
            bool: True if cancelled, False otherwise.
        """
        # When using Qt signals (worker thread), check handler's state
        if self._using_qt_signals:
            return self.handler.is_cancelled()

        # When in main thread with direct progress bar access
        if self._progress_bar is not None and HAS_QT and isinstance(self._progress_bar, QProgressDialog):
            return self._progress_bar.wasCanceled()

        return False

"""Progress context manager for both GUI and CLI modes."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from .cli_progress import CLIProgressBar
from .qt_compat import HAS_QT, QProgressDialog, QThread

if TYPE_CHECKING:
    from .handler import MessageHandler

# Try to import tqdm for enhanced CLI progress bars
try:
    # noinspection PyUnresolvedReferences
    from tqdm import tqdm as TqdmProgress

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

    # Define dummy tqdm for type checking when not available
    class TqdmProgress:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def update(self, n: int = 1) -> None:
            pass

        def set_description(self, desc: str) -> None:
            pass

        def close(self) -> None:
            pass


class ProgressContext:
    """Context manager for progress tracking that works in both GUI and CLI modes."""

    def __init__(self, handler: MessageHandler, description: str, total: int | None = None) -> None:
        """Initialize progress context.

        Args:
            handler: The message handler instance
            description: Description of the operation
            total: Total number of items to process
        """
        self.handler = handler
        self.description = description
        self.total = total
        self.current = 0
        self._progress_bar: TqdmProgress | CLIProgressBar | QProgressDialog | None = None
        self._using_qt_signals = False

    def __enter__(self) -> ProgressContext:
        """Enter the context and create appropriate progress indicator."""
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
        """Exit the context and clean up progress indicator."""
        if self._using_qt_signals:
            self.handler.progress_close_signal.emit()
        elif self._progress_bar is not None:
            if HAS_QT and isinstance(self._progress_bar, QProgressDialog):
                self._progress_bar.hide()
            elif hasattr(self._progress_bar, "close"):
                self._progress_bar.close()  # type: ignore[reportAttributeAccessIssue]

    def update(self, n: int = 1, description: str | None = None) -> None:
        """Update progress by n steps.

        Args:
            n: Number of steps to advance
            description: Optional new description
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

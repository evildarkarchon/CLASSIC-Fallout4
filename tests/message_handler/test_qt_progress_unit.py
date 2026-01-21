"""Unit tests for QtProgressHandler in Qt progress handling.

This module tests the QtProgressHandler class which provides
thread-safe progress dialogs using Qt signals and QProgressDialog.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


# --- QtProgressHandler Initialization Tests ---


class TestQtProgressHandlerInit:
    """Tests for QtProgressHandler initialization."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_initializes_with_no_parent(self, qt_application) -> None:
        """QtProgressHandler should initialize without a parent widget."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        assert handler._parent is None
        assert handler._progress_dialog is None
        assert handler._cancelled is False
        assert handler._current == 0
        assert handler._total is None

    @pytest.mark.unit
    @pytest.mark.gui
    def test_initializes_with_parent_widget(self, qt_parent_widget) -> None:
        """QtProgressHandler should store parent widget reference."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)

        assert handler._parent is qt_parent_widget

    @pytest.mark.unit
    @pytest.mark.gui
    def test_connects_signals_on_init(self, qt_application) -> None:
        """QtProgressHandler should connect signals to slots on init."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        # Verify signals exist and are properly configured
        # In PySide6, we can verify by checking the signal is callable
        # and that the slots are methods on the handler
        assert hasattr(handler, "progress_create_signal")
        assert hasattr(handler, "progress_update_signal")
        assert hasattr(handler, "progress_close_signal")
        assert hasattr(handler, "_create_dialog")
        assert hasattr(handler, "_update_dialog")
        assert hasattr(handler, "_close_dialog")


# --- QtProgressHandler._is_main_thread Tests ---


class TestQtProgressHandlerIsMainThread:
    """Tests for QtProgressHandler._is_main_thread() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_returns_true_on_main_thread(self, qt_application) -> None:
        """_is_main_thread should return True when on main Qt thread."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        # In tests, we run on the main thread
        assert handler._is_main_thread() is True

    @pytest.mark.unit
    @pytest.mark.gui
    def test_returns_false_when_no_app(self, qt_application) -> None:
        """_is_main_thread should return False when QApplication is None."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        with patch("PySide6.QtWidgets.QApplication.instance", return_value=None):
            assert handler._is_main_thread() is False

    @pytest.mark.unit
    @pytest.mark.gui
    def test_handles_import_error(self, qt_application) -> None:
        """_is_main_thread should return False on ImportError."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        with patch(
            "PySide6.QtWidgets.QApplication.instance",
            side_effect=ImportError("No module"),
        ):
            assert handler._is_main_thread() is False

    @pytest.mark.unit
    @pytest.mark.gui
    def test_handles_runtime_error(self, qt_application) -> None:
        """_is_main_thread should return False on RuntimeError."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        with patch(
            "PySide6.QtWidgets.QApplication.instance",
            side_effect=RuntimeError("Qt error"),
        ):
            assert handler._is_main_thread() is False


# --- QtProgressHandler.start Tests ---


class TestQtProgressHandlerStart:
    """Tests for QtProgressHandler.start() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_start_resets_cancelled_flag(self, qt_application) -> None:
        """start should reset the cancelled flag."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._cancelled = True

        handler.start("Processing")

        assert handler._cancelled is False

    @pytest.mark.unit
    @pytest.mark.gui
    def test_start_resets_current_to_zero(self, qt_application) -> None:
        """start should reset current counter to zero."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._current = 50

        handler.start("Processing")

        assert handler._current == 0

    @pytest.mark.unit
    @pytest.mark.gui
    def test_start_stores_total(self, qt_application) -> None:
        """start should store the total value."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        handler.start("Processing", total=100)

        assert handler._total == 100

    @pytest.mark.unit
    @pytest.mark.gui
    def test_start_handles_none_total_for_indeterminate(self, qt_application) -> None:
        """start should handle None total for indeterminate progress."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        handler.start("Scanning", total=None)

        assert handler._total is None

    @pytest.mark.unit
    @pytest.mark.gui
    def test_start_emits_create_signal(self, qt_application) -> None:
        """start should emit progress_create_signal."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        signal_spy = MagicMock()
        handler.progress_create_signal.connect(signal_spy)

        handler.start("Processing", total=50)

        # Process events to ensure signal is delivered
        qt_application.processEvents()

        signal_spy.assert_called_once_with("Processing", 50)


# --- QtProgressHandler._create_dialog Tests ---


class TestQtProgressHandlerCreateDialog:
    """Tests for QtProgressHandler._create_dialog() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_create_dialog_creates_progress_dialog(self, qt_parent_widget) -> None:
        """_create_dialog should create a QProgressDialog."""
        from PySide6.QtWidgets import QProgressDialog

        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Test Operation", 100)

        assert handler._progress_dialog is not None
        assert isinstance(handler._progress_dialog, QProgressDialog)

        # Cleanup
        handler._progress_dialog.close()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_create_dialog_resets_cancelled_flag(self, qt_parent_widget) -> None:
        """_create_dialog should reset cancelled flag."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._cancelled = True

        handler._create_dialog("Test", 50)

        assert handler._cancelled is False

        # Cleanup
        handler._progress_dialog.close()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_create_dialog_sets_indeterminate_for_zero_total(
        self, qt_parent_widget
    ) -> None:
        """_create_dialog should set indeterminate mode when total is 0."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Scanning", 0)

        assert handler._progress_dialog is not None
        # Indeterminate mode: both min and max are 0
        assert handler._progress_dialog.minimum() == 0
        assert handler._progress_dialog.maximum() == 0

        # Cleanup
        handler._progress_dialog.close()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_create_dialog_sets_window_title(self, qt_parent_widget) -> None:
        """_create_dialog should set window title to 'Progress'."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Test", 100)

        assert handler._progress_dialog.windowTitle() == "Progress"

        # Cleanup
        handler._progress_dialog.close()


# --- QtProgressHandler.update Tests ---


class TestQtProgressHandlerUpdate:
    """Tests for QtProgressHandler.update() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_increments_current(self, qt_application) -> None:
        """update should increment current by n."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._total = 100
        handler._last_update_time = 0  # Bypass throttling

        handler.update(5)

        assert handler._current == 5

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_increments_by_one_by_default(self, qt_application) -> None:
        """update should increment by 1 when n not specified."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._total = 100
        handler._last_update_time = 0

        handler.update()

        assert handler._current == 1

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_throttles_signal_emission(self, qt_application) -> None:
        """update should throttle signal emission for performance."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._total = 1000

        signal_spy = MagicMock()
        handler.progress_update_signal.connect(signal_spy)

        # Set last update time to now so first updates get throttled
        handler._last_update_time = time.time()

        # Multiple rapid updates - should be throttled
        for _ in range(10):
            handler.update(1)

        qt_application.processEvents()

        # Not all updates should have triggered signal emission
        # (only those after throttle interval or final)
        assert signal_spy.call_count < 10

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_always_emits_for_final_item(self, qt_application) -> None:
        """update should always emit signal for final item."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._total = 10
        handler._current = 9
        handler._last_update_time = time.time()  # Recent update

        signal_spy = MagicMock()
        handler.progress_update_signal.connect(signal_spy)

        # Final item should always emit
        handler.update(1)

        qt_application.processEvents()

        signal_spy.assert_called()


# --- QtProgressHandler._update_dialog Tests ---


class TestQtProgressHandlerUpdateDialog:
    """Tests for QtProgressHandler._update_dialog() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_dialog_does_nothing_when_no_dialog(self, qt_application) -> None:
        """_update_dialog should do nothing when dialog is None."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        # Should not raise
        handler._update_dialog(50, "Test")

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_dialog_sets_value(self, qt_parent_widget) -> None:
        """_update_dialog should set dialog value."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Test", 100)

        handler._update_dialog(50, "")

        assert handler._progress_dialog.value() == 50

        # Cleanup
        handler._progress_dialog.close()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_dialog_sets_label_text_when_provided(
        self, qt_parent_widget
    ) -> None:
        """_update_dialog should set label text when description provided."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Initial", 100)

        handler._update_dialog(25, "Updated Description")

        assert handler._progress_dialog.labelText() == "Updated Description"

        # Cleanup
        handler._progress_dialog.close()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_update_dialog_detects_cancellation(self, qt_parent_widget) -> None:
        """_update_dialog should detect user cancellation."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Test", 100)

        # Simulate cancellation
        handler._progress_dialog.cancel()

        handler._update_dialog(50, "")

        assert handler._cancelled is True

        # Cleanup
        handler._progress_dialog.close()


# --- QtProgressHandler.close Tests ---


class TestQtProgressHandlerClose:
    """Tests for QtProgressHandler.close() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_close_emits_close_signal(self, qt_application) -> None:
        """close should emit progress_close_signal."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        signal_spy = MagicMock()
        handler.progress_close_signal.connect(signal_spy)

        handler.close()

        qt_application.processEvents()

        signal_spy.assert_called_once()


# --- QtProgressHandler._close_dialog Tests ---


class TestQtProgressHandlerCloseDialog:
    """Tests for QtProgressHandler._close_dialog() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_close_dialog_hides_and_clears_dialog(self, qt_parent_widget) -> None:
        """_close_dialog should hide and clear the dialog."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Test", 100)

        handler._close_dialog()

        assert handler._progress_dialog is None

    @pytest.mark.unit
    @pytest.mark.gui
    def test_close_dialog_resets_state(self, qt_parent_widget) -> None:
        """_close_dialog should reset cancelled and current state."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Test", 100)
        handler._cancelled = True
        handler._current = 50

        handler._close_dialog()

        assert handler._cancelled is False
        assert handler._current == 0

    @pytest.mark.unit
    @pytest.mark.gui
    def test_close_dialog_does_nothing_when_no_dialog(self, qt_application) -> None:
        """_close_dialog should do nothing when dialog is None."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        # Should not raise
        handler._close_dialog()

        assert handler._progress_dialog is None


# --- QtProgressHandler.was_cancelled Tests ---


class TestQtProgressHandlerWasCancelled:
    """Tests for QtProgressHandler.was_cancelled() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_was_cancelled_returns_false_by_default(self, qt_application) -> None:
        """was_cancelled should return False by default."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        assert handler.was_cancelled() is False

    @pytest.mark.unit
    @pytest.mark.gui
    def test_was_cancelled_returns_internal_flag(self, qt_application) -> None:
        """was_cancelled should return the internal cancelled flag."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._cancelled = True

        assert handler.was_cancelled() is True

    @pytest.mark.unit
    @pytest.mark.gui
    def test_was_cancelled_checks_dialog_on_main_thread(
        self, qt_parent_widget
    ) -> None:
        """was_cancelled should check dialog directly on main thread."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler(parent=qt_parent_widget)
        handler._create_dialog("Test", 100)

        # Simulate cancellation via dialog
        handler._progress_dialog.cancel()

        result = handler.was_cancelled()

        assert result is True

        # Cleanup
        handler._progress_dialog.close()


# --- QtProgressHandler.is_available Tests ---


class TestQtProgressHandlerIsAvailable:
    """Tests for QtProgressHandler.is_available() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_is_available_returns_true_with_app(self, qt_application) -> None:
        """is_available should return True when QApplication exists."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        assert handler.is_available() is True

    @pytest.mark.unit
    @pytest.mark.gui
    def test_is_available_returns_false_without_app(self, qt_application) -> None:
        """is_available should return False when QApplication is None."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        with patch("PySide6.QtWidgets.QApplication.instance", return_value=None):
            assert handler.is_available() is False

    @pytest.mark.unit
    @pytest.mark.gui
    def test_is_available_handles_import_error(self, qt_application) -> None:
        """is_available should return False on ImportError."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        with patch(
            "PySide6.QtWidgets.QApplication.instance",
            side_effect=ImportError("No module"),
        ):
            assert handler.is_available() is False


# --- QtProgressHandler.set_parent Tests ---


class TestQtProgressHandlerSetParent:
    """Tests for QtProgressHandler.set_parent() method."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_set_parent_updates_parent_widget(self, qt_parent_widget) -> None:
        """set_parent should update the parent widget."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        assert handler._parent is None

        handler.set_parent(qt_parent_widget)

        assert handler._parent is qt_parent_widget

    @pytest.mark.unit
    @pytest.mark.gui
    def test_set_parent_accepts_none(self, qt_application) -> None:
        """set_parent should accept None."""
        from PySide6.QtWidgets import QWidget

        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        widget = QWidget()
        handler = QtProgressHandler(parent=widget)

        handler.set_parent(None)

        assert handler._parent is None

        # Cleanup
        widget.close()
        widget.deleteLater()


# --- QtProgressHandler Protocol Compliance Tests ---


class TestQtProgressHandlerProtocol:
    """Tests for QtProgressHandler ProgressHandler protocol compliance."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_implements_progress_handler_protocol(self, qt_application) -> None:
        """QtProgressHandler should implement ProgressHandler protocol."""
        from ClassicLib.MessageHandler.progress.base import ProgressHandler
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        # Check that it satisfies the protocol
        assert isinstance(handler, ProgressHandler)

    @pytest.mark.unit
    @pytest.mark.gui
    def test_has_required_methods(self, qt_application) -> None:
        """QtProgressHandler should have all required protocol methods."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        assert hasattr(handler, "start")
        assert hasattr(handler, "update")
        assert hasattr(handler, "close")
        assert hasattr(handler, "was_cancelled")
        assert hasattr(handler, "is_available")
        assert callable(handler.start)
        assert callable(handler.update)
        assert callable(handler.close)
        assert callable(handler.was_cancelled)
        assert callable(handler.is_available)


# --- QtProgressHandler Throttling Tests ---


class TestQtProgressHandlerThrottling:
    """Tests for QtProgressHandler update throttling."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_throttle_interval_is_configured(self, qt_application) -> None:
        """QtProgressHandler should have configurable throttle interval."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()

        assert hasattr(handler, "_THROTTLE_INTERVAL")
        assert handler._THROTTLE_INTERVAL == 0.05  # 50ms

    @pytest.mark.unit
    @pytest.mark.gui
    def test_updates_last_update_time(self, qt_application) -> None:
        """update should update last_update_time when emitting."""
        from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

        handler = QtProgressHandler()
        handler._total = 100
        handler._last_update_time = 0  # Force emit

        before_time = time.time()
        handler.update(1)

        assert handler._last_update_time >= before_time

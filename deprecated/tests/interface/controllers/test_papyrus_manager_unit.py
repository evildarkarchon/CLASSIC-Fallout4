"""Unit tests for PapyrusManager controller.

This module tests the PapyrusManager class that handles the lifecycle
of Papyrus log monitoring.

All tests in this module require Qt and cannot run in parallel workers.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


class TestPapyrusManager:
    """Tests for PapyrusManager class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.thread_manager = MagicMock()
        context.thread_manager.is_thread_running.return_value = False
        context.thread_manager.register_thread.return_value = True
        context.signal_hub = MagicMock()
        context.signal_hub.start_papyrus_monitoring = MagicMock()
        context.signal_hub.start_papyrus_monitoring.connect = MagicMock()
        context.signal_hub.stop_papyrus_monitoring = MagicMock()
        context.signal_hub.stop_papyrus_monitoring.connect = MagicMock()
        context.signal_hub.papyrus_monitoring_state_changed = MagicMock()
        context.signal_hub.papyrus_button_style_update = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.papyrus_button = None
        return context

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test PapyrusManager can be created with proper initialization."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        manager = PapyrusManager(mock_context)

        assert manager is not None
        assert manager._ctx is mock_context
        assert manager._monitor_thread is None
        assert manager._monitor_worker is None
        assert manager._monitor_dialog is None

    @pytest.mark.unit
    def test_signal_connections(self, mock_context):
        """Test that controller connects to SignalHub signals."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        PapyrusManager(mock_context)

        mock_context.signal_hub.start_papyrus_monitoring.connect.assert_called_once()
        mock_context.signal_hub.stop_papyrus_monitoring.connect.assert_called_once()

    @pytest.mark.unit
    def test_toggle_monitoring_starts_when_checked(self, mock_context):
        """Test toggle_monitoring starts monitoring when button checked."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_button = MagicMock()
        mock_button.isChecked.return_value = True
        mock_context.ui_widgets.papyrus_button = mock_button

        manager = PapyrusManager(mock_context)
        manager.start_monitoring = MagicMock()
        manager.stop_monitoring = MagicMock()

        manager.toggle_monitoring()

        manager.start_monitoring.assert_called_once()
        manager.stop_monitoring.assert_not_called()

    @pytest.mark.unit
    def test_toggle_monitoring_stops_when_unchecked(self, mock_context):
        """Test toggle_monitoring stops monitoring when button unchecked."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_button = MagicMock()
        mock_button.isChecked.return_value = False
        mock_context.ui_widgets.papyrus_button = mock_button

        manager = PapyrusManager(mock_context)
        manager.start_monitoring = MagicMock()
        manager.stop_monitoring = MagicMock()

        manager.toggle_monitoring()

        manager.stop_monitoring.assert_called_once()
        manager.start_monitoring.assert_not_called()

    @pytest.mark.unit
    def test_toggle_monitoring_no_button(self, mock_context):
        """Test toggle_monitoring handles missing button."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_context.ui_widgets.papyrus_button = None

        manager = PapyrusManager(mock_context)
        manager.start_monitoring = MagicMock()
        manager.stop_monitoring = MagicMock()

        manager.toggle_monitoring()

        # Should call stop since button is falsy
        manager.stop_monitoring.assert_called_once()

    @pytest.mark.unit
    def test_start_monitoring_skips_if_already_running(self, mock_context):
        """Test start_monitoring does nothing if already running."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_context.thread_manager.is_thread_running.return_value = True

        manager = PapyrusManager(mock_context)

        manager.start_monitoring()

        mock_context.thread_manager.register_thread.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.papyrus_manager.PapyrusMonitorDialog")
    @patch("ClassicLib.Interface.controllers.papyrus_manager.PapyrusMonitorWorker")
    @patch("ClassicLib.Interface.controllers.papyrus_manager.QThread")
    def test_start_monitoring_creates_thread(self, mock_qthread, mock_worker, mock_dialog, mock_context):
        """Test start_monitoring creates and starts worker thread."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance
        mock_dialog_instance = MagicMock()
        mock_dialog.return_value = mock_dialog_instance

        manager = PapyrusManager(mock_context)
        manager._update_button_style = MagicMock()

        manager.start_monitoring()

        mock_qthread.assert_called_once()
        mock_worker.assert_called_once()
        mock_worker_instance.moveToThread.assert_called_once_with(mock_thread_instance)
        mock_context.thread_manager.register_thread.assert_called_once()
        mock_context.thread_manager.start_thread.assert_called_once()
        mock_dialog_instance.show.assert_called_once()
        mock_context.signal_hub.papyrus_monitoring_state_changed.emit.assert_called_once_with(True)

    @pytest.mark.unit
    def test_start_monitoring_fails_registration(self, mock_context):
        """Test start_monitoring handles failed thread registration."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_context.thread_manager.register_thread.return_value = False

        manager = PapyrusManager(mock_context)

        with patch("ClassicLib.Interface.controllers.papyrus_manager.QThread"):
            with patch("ClassicLib.Interface.controllers.papyrus_manager.PapyrusMonitorWorker"):
                manager.start_monitoring()

        mock_context.thread_manager.start_thread.assert_not_called()

    @pytest.mark.unit
    def test_stop_monitoring_cleanup(self, mock_context):
        """Test stop_monitoring cleans up properly."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        manager = PapyrusManager(mock_context)

        # Create mocks and capture references before they get set to None
        mock_thread = MagicMock()
        mock_worker = MagicMock()
        mock_dialog = MagicMock()

        manager._monitor_thread = mock_thread
        manager._monitor_worker = mock_worker
        manager._monitor_dialog = mock_dialog
        manager._update_button_style = MagicMock()

        manager.stop_monitoring()

        # Verify the worker's stop was called (using captured reference)
        mock_worker.stop.assert_called_once()
        mock_context.thread_manager.stop_thread.assert_called_once()
        mock_dialog.close.assert_called_once()
        # Verify references are now None
        assert manager._monitor_thread is None
        assert manager._monitor_worker is None
        assert manager._monitor_dialog is None
        mock_context.signal_hub.papyrus_monitoring_state_changed.emit.assert_called_once_with(False)

    @pytest.mark.unit
    def test_stop_monitoring_no_worker(self, mock_context):
        """Test stop_monitoring handles missing worker."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        manager = PapyrusManager(mock_context)
        manager._monitor_thread = None
        manager._monitor_worker = None
        manager._monitor_dialog = None
        manager._update_button_style = MagicMock()

        # Should not raise
        manager.stop_monitoring()

    @pytest.mark.unit
    def test_update_button_style_monitoring_true(self, mock_context):
        """Test _update_button_style sets stop style when monitoring."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_button = MagicMock()
        mock_context.ui_widgets.papyrus_button = mock_button

        manager = PapyrusManager(mock_context)
        manager._update_button_style(True)

        mock_button.setText.assert_called_once_with("STOP PAPYRUS MONITORING")
        mock_button.setStyleSheet.assert_called_once()
        mock_context.signal_hub.papyrus_button_style_update.emit.assert_called_once_with(True)

    @pytest.mark.unit
    def test_update_button_style_monitoring_false(self, mock_context):
        """Test _update_button_style sets start style when not monitoring."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_button = MagicMock()
        mock_context.ui_widgets.papyrus_button = mock_button

        manager = PapyrusManager(mock_context)
        manager._update_button_style(False)

        mock_button.setText.assert_called_once_with("START PAPYRUS MONITORING")
        mock_button.setChecked.assert_called_once_with(False)
        mock_context.signal_hub.papyrus_button_style_update.emit.assert_called_once_with(False)

    @pytest.mark.unit
    def test_update_button_style_no_button(self, mock_context):
        """Test _update_button_style handles missing button."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_context.ui_widgets.papyrus_button = None

        manager = PapyrusManager(mock_context)
        # Should not raise
        manager._update_button_style(True)

    @pytest.mark.unit
    def test_is_monitoring(self, mock_context):
        """Test is_monitoring returns correct state."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        mock_context.thread_manager.is_thread_running.return_value = False

        manager = PapyrusManager(mock_context)

        assert manager.is_monitoring() is False

        mock_context.thread_manager.is_thread_running.return_value = True
        assert manager.is_monitoring() is True

    @pytest.mark.unit
    def test_button_styles_defined(self, mock_context):
        """Test START_STYLE and STOP_STYLE constants are defined."""
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager

        assert PapyrusManager.START_STYLE is not None
        assert "green" in PapyrusManager.START_STYLE.lower() or "45, 237, 138" in PapyrusManager.START_STYLE
        assert PapyrusManager.STOP_STYLE is not None
        assert "red" in PapyrusManager.STOP_STYLE.lower() or "237, 45, 45" in PapyrusManager.STOP_STYLE

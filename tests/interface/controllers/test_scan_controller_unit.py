"""Unit tests for ScanController.

This module tests the ScanController class that handles crash logs and
game files scanning operations with thread-safe execution.

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


class TestScanController:
    """Tests for ScanController class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.thread_manager = MagicMock()
        context.thread_manager.is_thread_running.return_value = False
        context.thread_manager.register_thread.return_value = True
        context.signal_hub = MagicMock()
        context.signal_hub.scan_buttons_enable = MagicMock()
        context.signal_hub.scan_buttons_enable.connect = MagicMock()
        context.signal_hub.pause_file_watching = MagicMock()
        context.signal_hub.resume_file_watching = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        context.signal_hub.scan_started = MagicMock()
        context.signal_hub.scan_completed = MagicMock()
        context.signal_hub.scan_failed = MagicMock()
        context.signal_hub.start_papyrus_monitoring = MagicMock()
        context.signal_hub.stop_papyrus_monitoring = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.scan_button_group = None
        context.ui_widgets.tab_widget = None
        context.ui_widgets.results_tab = None
        context.ui_widgets.papyrus_button = None
        return context

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test ScanController can be created with proper initialization."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)

        assert controller is not None
        assert controller._ctx is mock_context
        assert controller._running_scans == set()
        assert controller._crash_logs_thread is None
        assert controller._crash_logs_worker is None
        assert controller._game_files_thread is None
        assert controller._game_files_worker is None

    @pytest.mark.unit
    def test_controller_signal_connection(self, mock_context):
        """Test that controller connects to SignalHub signals."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        ScanController(mock_context)

        mock_context.signal_hub.scan_buttons_enable.connect.assert_called_once()

    @pytest.mark.unit
    def test_is_scan_running_none_type(self, mock_context):
        """Test is_scan_running returns False when no scans running."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)

        assert controller.is_scan_running() is False
        assert controller.is_scan_running("crash_logs") is False
        assert controller.is_scan_running("game_files") is False

    @pytest.mark.unit
    def test_is_scan_running_with_running_scan(self, mock_context):
        """Test is_scan_running returns True when scan is running."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)
        controller._running_scans.add("crash_logs")

        assert controller.is_scan_running() is True
        assert controller.is_scan_running("crash_logs") is True
        assert controller.is_scan_running("game_files") is False

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.scan_controller.QMessageBox")
    def test_crash_logs_scan_already_running(self, mock_msgbox, mock_context):
        """Test crash_logs_scan shows warning if already running."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)
        controller._running_scans.add("crash_logs")

        controller.crash_logs_scan()

        mock_msgbox.warning.assert_called_once()
        # Verify scan was not started
        mock_context.thread_manager.start_thread.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.scan_controller.QMessageBox")
    def test_game_files_scan_already_running(self, mock_msgbox, mock_context):
        """Test game_files_scan shows warning if already running."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)
        controller._running_scans.add("game_files")

        controller.game_files_scan()

        mock_msgbox.warning.assert_called_once()
        mock_context.thread_manager.start_thread.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.scan_controller.CrashLogsScanWorker")
    @patch("ClassicLib.Interface.controllers.scan_controller.QThread")
    def test_crash_logs_scan_starts_thread(self, mock_qthread, mock_worker, mock_context):
        """Test crash_logs_scan creates and starts worker thread."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        controller = ScanController(mock_context)
        controller.crash_logs_scan()

        # Verify thread and worker were created
        mock_qthread.assert_called_once()
        mock_worker.assert_called_once()
        mock_worker_instance.moveToThread.assert_called_once_with(mock_thread_instance)

        # Verify thread manager interactions
        mock_context.thread_manager.register_thread.assert_called_once()
        mock_context.thread_manager.start_thread.assert_called_once()

        # Verify scan started signal
        mock_context.signal_hub.scan_started.emit.assert_called_once_with("crash_logs")

        # Verify file watching was paused
        mock_context.signal_hub.pause_file_watching.emit.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.scan_controller.GameFilesScanWorker")
    @patch("ClassicLib.Interface.controllers.scan_controller.QThread")
    def test_game_files_scan_starts_thread(self, mock_qthread, mock_worker, mock_context):
        """Test game_files_scan creates and starts worker thread."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        controller = ScanController(mock_context)
        controller.game_files_scan()

        # Verify thread and worker were created
        mock_qthread.assert_called_once()
        mock_worker.assert_called_once()
        mock_worker_instance.moveToThread.assert_called_once_with(mock_thread_instance)

        # Verify thread manager interactions
        mock_context.thread_manager.register_thread.assert_called_once()
        mock_context.thread_manager.start_thread.assert_called_once()

        # Verify scan started signal
        mock_context.signal_hub.scan_started.emit.assert_called_once_with("game_files")

    @pytest.mark.unit
    def test_crash_logs_scan_fails_registration(self, mock_context):
        """Test crash_logs_scan handles failed thread registration."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_context.thread_manager.register_thread.return_value = False

        controller = ScanController(mock_context)

        with patch("ClassicLib.Interface.controllers.scan_controller.QThread"):
            with patch("ClassicLib.Interface.controllers.scan_controller.CrashLogsScanWorker"):
                controller.crash_logs_scan()

        # Verify scan was not added to running scans
        assert "crash_logs" not in controller._running_scans
        mock_context.thread_manager.start_thread.assert_not_called()

    @pytest.mark.unit
    def test_disable_scan_buttons(self, mock_context):
        """Test _disable_scan_buttons disables all buttons in group."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_button1 = MagicMock()
        mock_button2 = MagicMock()
        mock_button_group = MagicMock()
        mock_button_group.buttons.return_value = [mock_button1, mock_button2]
        mock_context.ui_widgets.scan_button_group = mock_button_group

        controller = ScanController(mock_context)
        controller._disable_scan_buttons()

        mock_button1.setEnabled.assert_called_once_with(False)
        mock_button2.setEnabled.assert_called_once_with(False)

    @pytest.mark.unit
    def test_enable_scan_buttons_when_no_scans(self, mock_context):
        """Test _enable_scan_buttons enables buttons when no scans running."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_button1 = MagicMock()
        mock_button2 = MagicMock()
        mock_button_group = MagicMock()
        mock_button_group.buttons.return_value = [mock_button1, mock_button2]
        mock_context.ui_widgets.scan_button_group = mock_button_group

        controller = ScanController(mock_context)
        controller._enable_scan_buttons()

        mock_button1.setEnabled.assert_called_once_with(True)
        mock_button2.setEnabled.assert_called_once_with(True)

    @pytest.mark.unit
    def test_enable_scan_buttons_skipped_when_scans_running(self, mock_context):
        """Test _enable_scan_buttons does nothing when scans are running."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_button1 = MagicMock()
        mock_button_group = MagicMock()
        mock_button_group.buttons.return_value = [mock_button1]
        mock_context.ui_widgets.scan_button_group = mock_button_group

        controller = ScanController(mock_context)
        controller._running_scans.add("crash_logs")
        controller._enable_scan_buttons()

        mock_button1.setEnabled.assert_not_called()

    @pytest.mark.unit
    def test_set_buttons_enabled_true(self, mock_context):
        """Test _set_buttons_enabled with enabled=True calls enable."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)
        controller._enable_scan_buttons = MagicMock()
        controller._disable_scan_buttons = MagicMock()

        controller._set_buttons_enabled(True)

        controller._enable_scan_buttons.assert_called_once()
        controller._disable_scan_buttons.assert_not_called()

    @pytest.mark.unit
    def test_set_buttons_enabled_false(self, mock_context):
        """Test _set_buttons_enabled with enabled=False calls disable."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)
        controller._enable_scan_buttons = MagicMock()
        controller._disable_scan_buttons = MagicMock()

        controller._set_buttons_enabled(False)

        controller._disable_scan_buttons.assert_called_once()
        controller._enable_scan_buttons.assert_not_called()

    @pytest.mark.unit
    def test_crash_logs_scan_finished_cleanup(self, mock_context):
        """Test _crash_logs_scan_finished cleans up and emits signals."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)
        controller._crash_logs_thread = MagicMock()
        controller._crash_logs_worker = MagicMock()
        controller._running_scans.add("crash_logs")
        controller._enable_scan_buttons = MagicMock()
        controller._switch_to_results_tab_if_enabled = MagicMock()

        controller._crash_logs_scan_finished()

        assert controller._crash_logs_thread is None
        assert controller._crash_logs_worker is None
        assert "crash_logs" not in controller._running_scans
        controller._enable_scan_buttons.assert_called_once()
        mock_context.signal_hub.resume_file_watching.emit.assert_called_once()
        mock_context.signal_hub.refresh_reports_requested.emit.assert_called_once()
        mock_context.signal_hub.scan_completed.emit.assert_called_once_with("crash_logs")

    @pytest.mark.unit
    def test_game_files_scan_finished_cleanup(self, mock_context):
        """Test _game_files_scan_finished cleans up and handles papyrus."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        controller = ScanController(mock_context)
        controller._game_files_thread = MagicMock()
        controller._game_files_worker = MagicMock()
        controller._running_scans.add("game_files")
        controller._enable_scan_buttons = MagicMock()

        # No papyrus button
        mock_context.ui_widgets.papyrus_button = None

        controller._game_files_scan_finished()

        assert controller._game_files_thread is None
        assert controller._game_files_worker is None
        assert "game_files" not in controller._running_scans
        controller._enable_scan_buttons.assert_called_once()
        mock_context.signal_hub.scan_completed.emit.assert_called_once_with("game_files")
        mock_context.signal_hub.stop_papyrus_monitoring.emit.assert_called_once()

    @pytest.mark.unit
    def test_game_files_scan_finished_starts_papyrus(self, mock_context):
        """Test _game_files_scan_finished starts papyrus if button checked."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_papyrus_button = MagicMock()
        mock_papyrus_button.isChecked.return_value = True
        mock_context.ui_widgets.papyrus_button = mock_papyrus_button

        controller = ScanController(mock_context)
        controller._running_scans.add("game_files")
        controller._enable_scan_buttons = MagicMock()

        controller._game_files_scan_finished()

        mock_context.signal_hub.start_papyrus_monitoring.emit.assert_called_once()
        mock_context.signal_hub.stop_papyrus_monitoring.emit.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.scan_controller.yaml_settings")
    def test_switch_to_results_tab_if_enabled(self, mock_yaml_settings, mock_context):
        """Test _switch_to_results_tab_if_enabled switches tab when enabled."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_yaml_settings.return_value = True
        mock_tab_widget = MagicMock()
        mock_results_tab = MagicMock()
        mock_tab_widget.count.return_value = 3
        mock_tab_widget.widget.side_effect = lambda i: mock_results_tab if i == 2 else MagicMock()
        mock_context.ui_widgets.tab_widget = mock_tab_widget
        mock_context.ui_widgets.results_tab = mock_results_tab

        controller = ScanController(mock_context)
        controller._switch_to_results_tab_if_enabled()

        mock_tab_widget.setCurrentIndex.assert_called_once_with(2)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.scan_controller.yaml_settings")
    def test_switch_to_results_tab_disabled(self, mock_yaml_settings, mock_context):
        """Test _switch_to_results_tab_if_enabled does nothing when disabled."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController

        mock_yaml_settings.return_value = False
        mock_tab_widget = MagicMock()
        mock_context.ui_widgets.tab_widget = mock_tab_widget

        controller = ScanController(mock_context)
        controller._switch_to_results_tab_if_enabled()

        mock_tab_widget.setCurrentIndex.assert_not_called()

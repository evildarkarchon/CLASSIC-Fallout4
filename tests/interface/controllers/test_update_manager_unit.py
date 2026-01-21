"""Unit tests for UpdateManager controller.

This module tests the UpdateManager class that handles checking for
application updates and notifying users of available updates.

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


class TestUpdateManager:
    """Tests for UpdateManager class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.thread_manager = MagicMock()
        context.thread_manager.is_thread_running.return_value = False
        context.thread_manager.register_thread.return_value = True
        context.signal_hub = MagicMock()
        return context

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test UpdateManager can be created with proper initialization."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)

        assert manager is not None
        assert manager._ctx is mock_context
        assert manager._is_update_check_running is False
        assert manager._update_check_thread is None
        assert manager._update_check_worker is None
        assert manager._pending_update_result is None
        assert manager._pending_error_message is None

    @pytest.mark.unit
    def test_update_popup_sets_running_flag(self, mock_context, qtbot):
        """Test update_popup sets the running flag and starts timer."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        manager.update_popup()

        assert manager._is_update_check_running is True
        manager._update_check_timer.start.assert_called_once_with(0)

    @pytest.mark.unit
    def test_update_popup_skips_when_running(self, mock_context):
        """Test update_popup does nothing if already running."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()
        manager._is_update_check_running = True

        manager.update_popup()

        manager._update_check_timer.start.assert_not_called()

    @pytest.mark.unit
    def test_update_popup_explicit_switches_timer(self, mock_context, qtbot):
        """Test update_popup_explicit switches timer to force check."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        manager.update_popup_explicit()

        assert manager._is_update_check_running is True
        manager._update_check_timer.timeout.disconnect.assert_called()
        manager._update_check_timer.timeout.connect.assert_called()
        manager._update_check_timer.start.assert_called_once_with(0)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.update_manager.QMessageBox")
    def test_force_update_check_shows_message_when_running(self, mock_msgbox, mock_context):
        """Test force_update_check shows message if already running."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        mock_context.thread_manager.is_thread_running.return_value = True

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        manager.force_update_check()

        mock_msgbox.information.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.update_manager.UpdateCheckWorker")
    @patch("ClassicLib.Interface.controllers.update_manager.QThread")
    def test_perform_update_check_starts_thread(self, mock_qthread, mock_worker, mock_context):
        """Test perform_update_check creates and starts worker thread."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        manager.perform_update_check()

        mock_qthread.assert_called_once()
        mock_worker.assert_called_once_with(explicit=False)
        mock_worker_instance.moveToThread.assert_called_once_with(mock_thread_instance)
        mock_context.thread_manager.register_thread.assert_called_once()
        mock_context.thread_manager.start_thread.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.update_manager.UpdateCheckWorker")
    @patch("ClassicLib.Interface.controllers.update_manager.QThread")
    def test_force_update_check_starts_with_explicit(self, mock_qthread, mock_worker, mock_context):
        """Test force_update_check passes explicit=True to worker."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        manager.force_update_check()

        mock_worker.assert_called_once_with(explicit=True)

    @pytest.mark.unit
    def test_perform_update_check_skips_when_running(self, mock_context):
        """Test perform_update_check does nothing if already running."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        mock_context.thread_manager.is_thread_running.return_value = True

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        manager.perform_update_check()

        mock_context.thread_manager.register_thread.assert_not_called()

    @pytest.mark.unit
    def test_perform_update_check_fails_registration(self, mock_context):
        """Test perform_update_check handles failed thread registration."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        mock_context.thread_manager.register_thread.return_value = False

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        with patch("ClassicLib.Interface.controllers.update_manager.QThread"):
            with patch("ClassicLib.Interface.controllers.update_manager.UpdateCheckWorker"):
                manager.perform_update_check()

        mock_context.thread_manager.start_thread.assert_not_called()

    @pytest.mark.unit
    def test_update_check_finished_cleanup(self, mock_context):
        """Test _update_check_finished cleans up properly."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)
        manager._is_update_check_running = True
        manager._update_check_thread = MagicMock()
        manager._update_check_worker = MagicMock()

        manager._update_check_finished()

        assert manager._is_update_check_running is False
        assert manager._update_check_thread is None
        assert manager._update_check_worker is None

    @pytest.mark.unit
    def test_on_update_result_stores_result(self, mock_context):
        """Test _on_update_result stores result for later display."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)

        # Signal sends True if update IS available, we invert for show_update_result
        manager._on_update_result(True)

        # The result should be inverted (True means update available, so is_up_to_date is False)
        assert manager._pending_update_result is False

    @pytest.mark.unit
    def test_on_update_result_inverts_correctly(self, mock_context):
        """Test _on_update_result correctly inverts the value."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)

        manager._on_update_result(False)  # No update available

        # False means no update available, so is_up_to_date is True
        assert manager._pending_update_result is True

    @pytest.mark.unit
    def test_on_update_error_stores_message(self, mock_context):
        """Test _on_update_error stores error message."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)

        manager._on_update_error("Network error")

        assert manager._pending_error_message == "Network error"

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.update_manager.QMessageBox")
    def test_show_update_result_up_to_date(self, mock_msgbox, mock_context):
        """Test show_update_result shows info when up to date."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)

        manager.show_update_result(True)

        mock_msgbox.information.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.update_manager.yaml_settings")
    @patch("ClassicLib.Interface.controllers.update_manager.QMessageBox")
    def test_show_update_result_update_available(self, mock_msgbox, mock_yaml, mock_context):
        """Test show_update_result shows question when update available."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        mock_yaml.return_value = "New version available!"
        mock_msgbox.StandardButton.Yes = 1
        mock_msgbox.StandardButton.No = 0
        mock_msgbox.question.return_value = 0  # User clicks No

        manager = UpdateManager(mock_context)

        manager.show_update_result(False)

        mock_msgbox.question.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.update_manager.QDesktopServices")
    @patch("ClassicLib.Interface.controllers.update_manager.yaml_settings")
    @patch("ClassicLib.Interface.controllers.update_manager.QMessageBox")
    def test_show_update_result_opens_url(self, mock_msgbox, mock_yaml, mock_desktop, mock_context):
        """Test show_update_result opens URL when user clicks Yes."""
        from PySide6.QtWidgets import QMessageBox as RealQMessageBox

        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        mock_yaml.return_value = "New version available!"
        mock_msgbox.StandardButton = RealQMessageBox.StandardButton
        mock_msgbox.question.return_value = RealQMessageBox.StandardButton.Yes

        manager = UpdateManager(mock_context)

        manager.show_update_result(False)

        mock_desktop.openUrl.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.update_manager.QMessageBox")
    def test_show_update_error(self, mock_msgbox, mock_context):
        """Test show_update_error displays warning."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)

        manager.show_update_error("Connection timeout")

        mock_msgbox.warning.assert_called_once()
        call_args = mock_msgbox.warning.call_args
        assert "Connection timeout" in call_args[0][2]

    @pytest.mark.unit
    def test_stop_timer(self, mock_context):
        """Test stop_timer stops the update timer."""
        from ClassicLib.Interface.controllers.update_manager import UpdateManager

        manager = UpdateManager(mock_context)
        manager._update_check_timer = MagicMock()

        manager.stop_timer()

        manager._update_check_timer.stop.assert_called_once()

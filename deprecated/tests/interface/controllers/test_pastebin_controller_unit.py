"""Unit tests for PastebinController.

This module tests the PastebinController class that handles fetching
crash logs from Pastebin URLs.

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


class TestPastebinController:
    """Tests for PastebinController class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.thread_manager = MagicMock()
        context.thread_manager.is_thread_running.return_value = False
        context.thread_manager.register_thread.return_value = True
        context.signal_hub = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.pastebin_id_input = MagicMock()
        context.ui_widgets.pastebin_fetch_button = None
        context.ui_widgets.pastebin_label = None
        return context

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test PastebinController can be created with proper initialization."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        controller = PastebinController(mock_context)

        assert controller is not None
        assert controller._ctx is mock_context
        assert controller._pastebin_thread is None
        assert controller._pastebin_worker is None
        assert controller._pastebin_url_regex is not None

    @pytest.mark.unit
    def test_url_regex_matches_valid_url(self, mock_context):
        """Test URL regex matches valid Pastebin URLs."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        controller = PastebinController(mock_context)

        # Valid URLs
        assert controller._pastebin_url_regex.match("https://pastebin.com/abc123")
        assert controller._pastebin_url_regex.match("http://pastebin.com/XYZ789")

    @pytest.mark.unit
    def test_url_regex_rejects_invalid_url(self, mock_context):
        """Test URL regex rejects invalid URLs."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        controller = PastebinController(mock_context)

        # Invalid URLs
        assert controller._pastebin_url_regex.match("https://pastebin.org/abc123") is None
        assert controller._pastebin_url_regex.match("https://example.com/abc") is None
        assert controller._pastebin_url_regex.match("abc123") is None

    @pytest.mark.unit
    def test_fetch_pastebin_log_empty_input(self, mock_context):
        """Test fetch_pastebin_log does nothing with empty input."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        mock_context.ui_widgets.pastebin_id_input.text.return_value = ""

        controller = PastebinController(mock_context)
        controller.fetch_pastebin_log()

        mock_context.thread_manager.is_thread_running.assert_not_called()

    @pytest.mark.unit
    def test_fetch_pastebin_log_no_input_widget(self, mock_context):
        """Test fetch_pastebin_log handles missing input widget."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        mock_context.ui_widgets.pastebin_id_input = None

        controller = PastebinController(mock_context)
        # Should not raise
        controller.fetch_pastebin_log()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.pastebin_controller.QMessageBox")
    def test_fetch_pastebin_log_already_running(self, mock_msgbox, mock_context):
        """Test fetch_pastebin_log shows warning if already running."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        mock_context.ui_widgets.pastebin_id_input.text.return_value = "abc123"
        mock_context.thread_manager.is_thread_running.return_value = True

        controller = PastebinController(mock_context)
        controller.fetch_pastebin_log()

        mock_msgbox.warning.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.pastebin_controller.PastebinFetchWorker")
    @patch("ClassicLib.Interface.controllers.pastebin_controller.QThread")
    def test_fetch_pastebin_log_with_id(self, mock_qthread, mock_worker, mock_context):
        """Test fetch_pastebin_log constructs URL from ID."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        mock_context.ui_widgets.pastebin_id_input.text.return_value = "abc123"

        controller = PastebinController(mock_context)
        controller.fetch_pastebin_log()

        # Verify URL was constructed
        mock_worker.assert_called_once_with("https://pastebin.com/abc123")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.pastebin_controller.PastebinFetchWorker")
    @patch("ClassicLib.Interface.controllers.pastebin_controller.QThread")
    def test_fetch_pastebin_log_with_full_url(self, mock_qthread, mock_worker, mock_context):
        """Test fetch_pastebin_log uses provided full URL."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        mock_context.ui_widgets.pastebin_id_input.text.return_value = "https://pastebin.com/xyz789"

        controller = PastebinController(mock_context)
        controller.fetch_pastebin_log()

        # Verify full URL was used directly
        mock_worker.assert_called_once_with("https://pastebin.com/xyz789")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.pastebin_controller.PastebinFetchWorker")
    @patch("ClassicLib.Interface.controllers.pastebin_controller.QThread")
    def test_fetch_pastebin_log_starts_thread(self, mock_qthread, mock_worker, mock_context):
        """Test fetch_pastebin_log creates and starts worker thread."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        mock_thread_instance = MagicMock()
        mock_qthread.return_value = mock_thread_instance
        mock_worker_instance = MagicMock()
        mock_worker.return_value = mock_worker_instance

        mock_context.ui_widgets.pastebin_id_input.text.return_value = "abc123"

        controller = PastebinController(mock_context)
        controller.fetch_pastebin_log()

        mock_qthread.assert_called_once()
        mock_worker_instance.moveToThread.assert_called_once_with(mock_thread_instance)
        mock_context.thread_manager.register_thread.assert_called_once()
        mock_context.thread_manager.start_thread.assert_called_once()

    @pytest.mark.unit
    def test_fetch_pastebin_log_fails_registration(self, mock_context):
        """Test fetch_pastebin_log handles failed thread registration."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        mock_context.thread_manager.register_thread.return_value = False
        mock_context.ui_widgets.pastebin_id_input.text.return_value = "abc123"

        controller = PastebinController(mock_context)

        with patch("ClassicLib.Interface.controllers.pastebin_controller.QThread"):
            with patch("ClassicLib.Interface.controllers.pastebin_controller.PastebinFetchWorker"):
                controller.fetch_pastebin_log()

        mock_context.thread_manager.start_thread.assert_not_called()

    @pytest.mark.unit
    def test_cleanup_thread_refs(self, mock_context):
        """Test _cleanup_thread_refs clears references."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        controller = PastebinController(mock_context)
        controller._pastebin_thread = MagicMock()
        controller._pastebin_worker = MagicMock()

        controller._cleanup_thread_refs()

        assert controller._pastebin_thread is None
        assert controller._pastebin_worker is None

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.pastebin_controller.QMessageBox")
    def test_on_fetch_success(self, mock_msgbox, mock_context):
        """Test _on_fetch_success shows success message."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        controller = PastebinController(mock_context)

        controller._on_fetch_success("https://pastebin.com/abc123")

        mock_msgbox.information.assert_called_once()
        call_args = mock_msgbox.information.call_args
        assert "abc123" in call_args[0][2]

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.pastebin_controller.QMessageBox")
    def test_on_fetch_error(self, mock_msgbox, mock_context):
        """Test _on_fetch_error shows error message."""
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        controller = PastebinController(mock_context)

        controller._on_fetch_error("Network timeout")

        mock_msgbox.warning.assert_called_once()
        call_args = mock_msgbox.warning.call_args
        assert "Network timeout" in call_args[0][2]

    @pytest.mark.unit
    def test_setup_pastebin_elements(self, mock_context, qtbot):
        """Test setup_pastebin_elements creates UI widgets."""
        from PySide6.QtWidgets import QVBoxLayout, QWidget

        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController

        controller = PastebinController(mock_context)

        parent_widget = QWidget()
        layout = QVBoxLayout(parent_widget)

        controller.setup_pastebin_elements(layout)

        # Verify widgets were registered
        assert mock_context.ui_widgets.pastebin_label is not None
        assert mock_context.ui_widgets.pastebin_id_input is not None
        assert mock_context.ui_widgets.pastebin_fetch_button is not None

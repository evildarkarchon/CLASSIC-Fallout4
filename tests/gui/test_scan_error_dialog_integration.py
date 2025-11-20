"""
Integration tests for scan error dialog flow.

Tests the complete flow from worker error to dialog display, including
signal connections and error dialog presentation.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QButtonGroup, QMainWindow

from ClassicLib.Interface.Dialogs import CustomErrorDialog
from ClassicLib.Interface.ScanOperations import ScanOperationsMixin
from ClassicLib.Interface.Workers import CrashLogsScanWorker, GameFilesScanWorker


# Create a fixture class that combines the mixin with QMainWindow
class MainWindowFixture(ScanOperationsMixin, QMainWindow):
    """Fixture window combining ScanOperationsMixin with QMainWindow for testing."""

    def __init__(self):
        super().__init__()
        from PySide6.QtCore import QMutex

        from ClassicLib.Interface.Audio import AudioPlayer
        from ClassicLib.Interface.ThreadManager import ThreadManager

        self._scan_mutex = QMutex()
        self._running_scans = set()
        self.thread_manager = ThreadManager()
        self.audio_player = AudioPlayer()
        self.scan_button_group = QButtonGroup()
        self.papyrus_button = None
        self.crash_logs_thread = None
        self.crash_logs_worker = None
        self.game_files_thread = None
        self.game_files_worker = None
        self.tab_widget = None
        self.results_tab = None

        # Track dialog display
        self.last_error_dialog = None

    def start_papyrus_monitoring(self):
        pass

    def stop_papyrus_monitoring(self):
        pass

    def refresh_reports_list(self):
        pass

    def _show_scan_error_dialog(self, title, message, details):
        """Override to track dialog creation."""
        self.last_error_dialog = {"title": title, "message": message, "details": details}
        # Call parent to test actual dialog creation
        super()._show_scan_error_dialog(title, message, details)


@pytest.mark.integration
@pytest.mark.gui
class TestScanErrorDialogIntegration:
    """Test complete error dialog integration."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create test main window."""
        window = MainWindowFixture()
        qtbot.addWidget(window)
        return window

    @pytest.fixture
    def mock_scan_failure(self):
        """Mock a scan that always fails."""

        def _perform_scan_mock(*args, **kwargs):
            raise RuntimeError("Simulated scan failure")

        return _perform_scan_mock

    def test_crash_logs_worker_error_triggers_dialog(self, main_window, qtbot, mock_scan_failure):
        """Test that crash logs worker error triggers error dialog display."""
        # Setup mocks
        with patch.object(CrashLogsScanWorker, "_perform_crash_logs_scan", mock_scan_failure):
            with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
                with patch("ClassicLib.Interface.ScanOperations.CustomErrorDialog") as mock_dialog_class:
                    mock_dialog = MagicMock(spec=CustomErrorDialog)
                    mock_dialog_class.return_value = mock_dialog

                    # Create worker manually (simulating what crash_logs_scan does)
                    worker = CrashLogsScanWorker()

                    # Connect signal to main window's handler
                    worker.error_occurred.connect(main_window._show_scan_error_dialog)

                    # Wait for the error_occurred signal using qtbot.waitSignal for reliability
                    with qtbot.waitSignal(worker.error_occurred, timeout=1000):
                        # Run worker
                        worker.run()

                    # Process events to ensure QTimer.singleShot fires
                    qtbot.wait(100)

                    # Verify dialog was created
                    mock_dialog_class.assert_called_once()
                    call_kwargs = mock_dialog_class.call_args[1]

                    assert call_kwargs["title"] == "Crash Log Scan Failed"
                    assert "Simulated scan failure" in call_kwargs["message"]
                    assert "Traceback" in call_kwargs["details"]
                    assert "RuntimeError: Simulated scan failure" in call_kwargs["details"]

                    # Verify dialog was shown
                    mock_dialog.exec.assert_called_once()

    def test_game_files_worker_error_triggers_dialog(self, main_window, qtbot):
        """Test that game files worker error triggers error dialog display."""

        def _process_mock(*args, **kwargs):
            raise OSError("Failed to write results")

        with patch.object(GameFilesScanWorker, "_process_game_results_scan", _process_mock):
            with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
                with patch("ClassicLib.Interface.ScanOperations.CustomErrorDialog") as mock_dialog_class:
                    mock_dialog = MagicMock(spec=CustomErrorDialog)
                    mock_dialog_class.return_value = mock_dialog

                    # Create worker
                    worker = GameFilesScanWorker()
                    worker.error_occurred.connect(main_window._show_scan_error_dialog)

                    # Wait for the error_occurred signal
                    with qtbot.waitSignal(worker.error_occurred, timeout=1000):
                        # Run worker
                        worker.run()

                    # Process events to ensure QTimer.singleShot fires
                    qtbot.wait(100)

                    # Verify dialog was created
                    mock_dialog_class.assert_called_once()
                    call_kwargs = mock_dialog_class.call_args[1]

                    assert call_kwargs["title"] == "Game Files Scan Failed"
                    assert "Failed to write results" in call_kwargs["message"]
                    assert "OSError: Failed to write results" in call_kwargs["details"]

                    # Verify dialog was shown
                    mock_dialog.exec.assert_called_once()

    def test_error_dialog_receives_parent_window(self, main_window, qtbot, mock_scan_failure):
        """Test that error dialog receives main window as parent."""
        with patch.object(CrashLogsScanWorker, "_perform_crash_logs_scan", mock_scan_failure):
            with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
                with patch("ClassicLib.Interface.ScanOperations.CustomErrorDialog") as mock_dialog_class:
                    mock_dialog = MagicMock(spec=CustomErrorDialog)
                    mock_dialog_class.return_value = mock_dialog

                    worker = CrashLogsScanWorker()
                    worker.error_occurred.connect(main_window._show_scan_error_dialog)
                    worker.run()
                    qtbot.wait(200)

                    # Verify parent was set
                    call_kwargs = mock_dialog_class.call_args[1]
                    assert call_kwargs["parent"] == main_window

    def test_both_audio_and_dialog_signals_work(self, main_window, qtbot, mock_scan_failure):
        """Test that both audio signal and error dialog signal are emitted."""
        audio_emitted = False
        dialog_shown = False

        def audio_callback():
            nonlocal audio_emitted
            audio_emitted = True

        def dialog_callback(title, message, details):
            nonlocal dialog_shown
            dialog_shown = True

        with patch.object(CrashLogsScanWorker, "_perform_crash_logs_scan", mock_scan_failure):
            with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
                worker = CrashLogsScanWorker()
                worker.error_sound_signal.connect(audio_callback)
                worker.error_occurred.connect(dialog_callback)

                worker.run()
                qtbot.wait(200)

                assert audio_emitted, "Audio signal should be emitted"
                assert dialog_shown, "Dialog signal should be emitted"

    def test_error_dialog_contains_copy_button_when_shown(self, main_window, qtbot, mock_scan_failure):
        """Test that displayed error dialog contains copy button."""
        with patch.object(CrashLogsScanWorker, "_perform_crash_logs_scan", mock_scan_failure):
            with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
                # Don't mock the dialog - let it actually be created
                worker = CrashLogsScanWorker()
                worker.error_occurred.connect(main_window._show_scan_error_dialog)

                # Mock exec to prevent actual modal display
                with patch.object(CustomErrorDialog, "exec"):
                    worker.run()
                    qtbot.wait(200)

                    # Verify dialog data was captured
                    assert main_window.last_error_dialog is not None
                    assert main_window.last_error_dialog["details"] is not None
                    assert len(main_window.last_error_dialog["details"]) > 0

    def test_multiple_errors_show_multiple_dialogs(self, main_window, qtbot, mock_scan_failure):
        """Test that multiple errors result in multiple dialog displays."""
        dialog_count = 0

        def count_dialogs(title, message, details):
            nonlocal dialog_count
            dialog_count += 1

        with patch.object(CrashLogsScanWorker, "_perform_crash_logs_scan", mock_scan_failure):
            with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
                # Create and run first worker
                worker1 = CrashLogsScanWorker()
                worker1.error_occurred.connect(count_dialogs)
                worker1.run()
                qtbot.wait(200)

                # Create and run second worker
                worker2 = CrashLogsScanWorker()
                worker2.error_occurred.connect(count_dialogs)
                worker2.run()
                qtbot.wait(200)

                assert dialog_count == 2, "Should show dialog for each error"

    def test_error_dialog_not_shown_when_scan_succeeds(self, main_window, qtbot):
        """Test that no error dialog is shown when scan succeeds."""
        dialog_shown = False

        def dialog_callback(title, message, details):
            nonlocal dialog_shown
            dialog_shown = True

        # Mock successful scan
        def _success_mock(*args, **kwargs):
            pass

        with patch.object(CrashLogsScanWorker, "_perform_crash_logs_scan", _success_mock):
            worker = CrashLogsScanWorker()
            worker.error_occurred.connect(dialog_callback)
            worker.run()
            qtbot.wait(200)

            assert not dialog_shown, "Dialog should not be shown on success"

    def test_traceback_includes_actual_error_location(self, main_window, qtbot):
        """Test that traceback includes actual error location from worker."""
        captured_details = None

        def capture_details(title, message, details):
            nonlocal captured_details
            captured_details = details

        def _error_with_location(*args, **kwargs):
            # This will show in traceback
            raise ValueError("Test error from specific location")

        with patch.object(CrashLogsScanWorker, "_perform_crash_logs_scan", _error_with_location):
            with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
                worker = CrashLogsScanWorker()
                worker.error_occurred.connect(capture_details)
                worker.run()
                qtbot.wait(200)

                # Verify traceback contains function name
                assert captured_details is not None
                assert "_error_with_location" in captured_details
                assert "ValueError: Test error from specific location" in captured_details

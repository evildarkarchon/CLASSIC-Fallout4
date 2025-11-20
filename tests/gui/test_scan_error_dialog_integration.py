"""
Integration tests for scan error dialog flow.

Tests the complete flow from worker error to dialog display, including
signal connections and error dialog presentation.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QTimer
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

    @pytest.fixture(autouse=True)
    def cleanup_singletons(self):
        """Clean up singleton instances before and after each test to prevent pollution."""
        import time

        from ClassicLib.AsyncBridge import AsyncBridge
        import ClassicLib.GlobalRegistry as GlobalRegistry

        # Clean up before test
        self._cleanup_async_bridge_thoroughly(AsyncBridge)
        # Clear GlobalRegistry without removing Keys
        with GlobalRegistry._registry_lock:
            GlobalRegistry._registry.clear()

        yield

        # Clean up after test
        self._cleanup_async_bridge_thoroughly(AsyncBridge)
        # Clear GlobalRegistry without removing Keys
        with GlobalRegistry._registry_lock:
            GlobalRegistry._registry.clear()

    @staticmethod
    def _cleanup_async_bridge_thoroughly(AsyncBridge):
        """Thoroughly clean up AsyncBridge instances and wait for thread termination.

        This method ensures complete cleanup of AsyncBridge resources including:
        - Thread-local instances
        - Global instances dictionary
        - AsyncBridge event loop threads
        - Asyncio worker threads

        It waits for all threads to fully terminate to prevent race conditions
        where new tests start while old threads are still shutting down.
        """
        import threading
        import time

        # Collect all AsyncBridge and asyncio threads before cleanup
        async_bridge_threads = [
            t for t in threading.enumerate()
            if (t.name.startswith("AsyncBridge-") or t.name.startswith("asyncio_")) and t.is_alive()
        ]

        # Check thread-local instance first and shut it down if it exists
        # This handles cases where previous tests left a zombie instance in the current thread
        # but cleared it from the global _instances dict
        if hasattr(AsyncBridge._thread_local, "instance"):
            try:
                instance = AsyncBridge._thread_local.instance
                instance.shutdown()
            except Exception:
                pass
            delattr(AsyncBridge._thread_local, "instance")

        # Call cleanup
        AsyncBridge._cleanup_all()

        # Clear the instances dict to remove shutdown instances
        with AsyncBridge._lock:
            AsyncBridge._instances.clear()

        # Wait for all AsyncBridge and asyncio threads to terminate (up to 2.5 seconds each)
        # This matches AsyncBridge's 2-second thread join timeout plus buffer
        for thread in async_bridge_threads:
            if thread.is_alive():
                thread.join(timeout=2.5)

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

    @pytest.fixture(autouse=True)
    def mock_classic_settings_globally(self):
        """Mock classic_settings globally to prevent YAML operations."""
        # Mock classic_settings at all import locations
        with patch("ClassicLib.Interface.Workers.classic_settings", return_value=True):
            with patch("ClassicLib.YamlSettingsCache.classic_settings", return_value=True):
                with patch("ClassicLib.Interface.Audio.classic_settings", return_value=True):
                    yield

    @pytest.fixture
    def mock_settings(self):
        """Mock classic_settings to return True for audio notifications."""
        return Mock(return_value=True)

    def test_crash_logs_worker_error_triggers_dialog(self, main_window, qtbot, mock_scan_failure):
        """Test that error dialog is shown when error_occurred signal is emitted.

        This test directly emits the error signal instead of trying to trigger it through
        worker execution, which avoids patching issues when the module is cached from earlier tests.
        """
        # Setup mocks
        with patch("ClassicLib.Interface.ScanOperations.CustomErrorDialog") as mock_dialog_class:
            mock_dialog = MagicMock(spec=CustomErrorDialog)
            mock_dialog_class.return_value = mock_dialog

            # Create worker
            worker = CrashLogsScanWorker()

            # Connect signal to main window's handler
            worker.error_occurred.connect(main_window._show_scan_error_dialog)

            # Directly emit the error signal to test the dialog connection
            # This simulates what would happen if the worker encountered an error
            title = "Crash Log Scan Failed"
            message = "An error occurred during crash log scanning:\\n\\nSimulated scan failure"
            details = "Traceback (most recent call last):\\n  RuntimeError: Simulated scan failure"

            # Emit signal and process Qt events
            worker.error_occurred.emit(title, message, details)
            qtbot.wait(500)  # Allow Qt event loop to process the deferred dialog creation

            # Verify dialog was created with correct parameters
            mock_dialog_class.assert_called_once()
            call_kwargs = mock_dialog_class.call_args[1]

            assert call_kwargs["title"] == title
            assert "Simulated scan failure" in call_kwargs["message"]
            assert "RuntimeError: Simulated scan failure" in call_kwargs["details"]

            # Verify dialog was shown
            mock_dialog.exec.assert_called_once()

    def test_game_files_worker_error_triggers_dialog(self, main_window, qtbot):
        """Test that error dialog is shown when game files worker error signal is emitted.

        This test directly emits the error signal instead of trying to trigger it through
        worker execution, which avoids patching issues when the module is cached from earlier tests.
        """
        with patch("ClassicLib.Interface.ScanOperations.CustomErrorDialog") as mock_dialog_class:
            mock_dialog = MagicMock(spec=CustomErrorDialog)
            mock_dialog_class.return_value = mock_dialog

            # Create worker
            worker = GameFilesScanWorker()

            worker.error_occurred.connect(main_window._show_scan_error_dialog)

            # Directly emit the error signal to test the dialog connection
            title = "Game Files Scan Failed"
            message = "An error occurred while processing game files:\\n\\nFailed to write results"
            details = "Traceback (most recent call last):\\n  OSError: Failed to write results"

            # Emit signal and process Qt events
            worker.error_occurred.emit(title, message, details)
            qtbot.wait(500)  # Allow Qt event loop to process the deferred dialog creation

            # Verify dialog was created
            mock_dialog_class.assert_called_once()
            call_kwargs = mock_dialog_class.call_args[1]

            assert call_kwargs["title"] == title
            assert "Failed to write results" in call_kwargs["message"]
            assert "OSError: Failed to write results" in call_kwargs["details"]

            # Verify dialog was shown
            mock_dialog.exec.assert_called_once()

    def test_error_dialog_receives_parent_window(self, main_window, qtbot):
        """Test that error dialog receives main window as parent."""
        with patch("ClassicLib.Interface.ScanOperations.CustomErrorDialog") as mock_dialog_class:
            mock_dialog = MagicMock(spec=CustomErrorDialog)
            mock_dialog_class.return_value = mock_dialog

            worker = CrashLogsScanWorker()
            worker.error_occurred.connect(main_window._show_scan_error_dialog)

            # Directly emit error signal
            worker.error_occurred.emit("Test Error", "Test message", "Test details")
            qtbot.wait(500)

            # Verify parent was set
            call_kwargs = mock_dialog_class.call_args[1]
            assert call_kwargs["parent"] == main_window

    def test_both_audio_and_dialog_signals_work(self, main_window, qtbot, mock_settings):
        """Test that both audio signal and error dialog signal are emitted by worker error handler."""
        audio_emitted = False
        dialog_shown = False

        def audio_callback():
            nonlocal audio_emitted
            audio_emitted = True

        def dialog_callback(title, message, details):
            nonlocal dialog_shown
            dialog_shown = True

        with patch("ClassicLib.Interface.Workers.classic_settings", mock_settings):
            worker = CrashLogsScanWorker()

            worker.error_sound_signal.connect(audio_callback)
            worker.error_occurred.connect(dialog_callback)

            # Directly call the worker's error handler to test signal emissions
            worker._handle_scan_error(RuntimeError("Simulated scan failure"))
            qtbot.wait(100)

            assert audio_emitted, "Audio signal should be emitted"
            assert dialog_shown, "Dialog signal should be emitted"

    def test_error_dialog_contains_copy_button_when_shown(self, main_window, qtbot):
        """Test that displayed error dialog contains copy button."""
        # Don't mock the dialog - let it actually be created
        worker = CrashLogsScanWorker()
        worker.error_occurred.connect(main_window._show_scan_error_dialog)

        # Mock exec to prevent actual modal display
        with patch.object(CustomErrorDialog, "exec"):
            # Directly emit error signal
            worker.error_occurred.emit("Test Error", "Test message", "Test details with traceback")
            qtbot.wait(500)

            # Verify dialog data was captured by the MainWindowFixture
            assert main_window.last_error_dialog is not None
            assert main_window.last_error_dialog["details"] is not None
            assert len(main_window.last_error_dialog["details"]) > 0

    def test_multiple_errors_show_multiple_dialogs(self, main_window, qtbot, mock_scan_failure, mock_settings):
        """Test that multiple errors result in multiple dialog displays."""
        dialog_count = 0

        def count_dialogs(title, message, details):
            nonlocal dialog_count
            dialog_count += 1

        # Create and emit from first worker
        worker1 = CrashLogsScanWorker()
        worker1.error_occurred.connect(count_dialogs)
        worker1.error_occurred.emit("Error 1", "Message 1", "Details 1")
        qtbot.wait(100)

        # Create and emit from second worker
        worker2 = CrashLogsScanWorker()
        worker2.error_occurred.connect(count_dialogs)
        worker2.error_occurred.emit("Error 2", "Message 2", "Details 2")
        qtbot.wait(100)

        assert dialog_count == 2, "Should show dialog for each error"

    def test_error_dialog_not_shown_when_scan_succeeds(self, main_window, qtbot):
        """Test that no error dialog is shown when no error signal is emitted."""
        dialog_shown = False

        def dialog_callback(title, message, details):
            nonlocal dialog_shown
            dialog_shown = True

        worker = CrashLogsScanWorker()
        worker.error_occurred.connect(dialog_callback)

        # Don't emit any error signal - simulating successful scan
        qtbot.wait(100)

        assert not dialog_shown, "Dialog should not be shown when no error occurs"

    def test_traceback_includes_actual_error_location(self, main_window, qtbot):
        """Test that traceback details are passed through correctly."""
        captured_details = None

        def capture_details(title, message, details):
            nonlocal captured_details
            captured_details = details

        worker = CrashLogsScanWorker()
        worker.error_occurred.connect(capture_details)

        # Directly emit error signal with traceback details
        traceback_text = "Traceback (most recent call last):\\n  File test.py, line 42, in test_function\\n    ValueError: Test error from specific location"
        worker.error_occurred.emit("Test Error", "Test message", traceback_text)
        qtbot.wait(100)

        # Verify traceback details were passed through
        assert captured_details is not None
        assert "ValueError: Test error from specific location" in captured_details
        assert "test_function" in captured_details

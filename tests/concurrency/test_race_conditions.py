"""Tests for race condition prevention in button state management."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import os
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import QMutex, QThread
from PySide6.QtWidgets import QApplication, QWidget

from ClassicLib.Interface.ThreadManager import ThreadManager, ThreadType, get_thread_manager


class TestRaceConditionPrevention:
    """Test race condition prevention in button state management."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_scan_mutex_protection(self, app: QApplication) -> None:
        """Test that scan operations are protected by mutex."""
        # Test the ScanOperationsMixin directly instead of full MainWindow
        from ClassicLib.Interface.ScanOperations import ScanOperationsMixin

        # Create a test class that uses the mixin and inherits from QWidget
        class TestScanClass(QWidget, ScanOperationsMixin):
            def __init__(self):
                super().__init__()
                self._scan_mutex = QMutex()
                self._running_scans = set()
                self.thread_manager = get_thread_manager()
                self.crash_logs_thread = None
                self.crash_logs_worker = None
                self.game_files_thread = None
                self.game_files_worker = None
                self.scan_button_group = MagicMock()
                self.papyrus_button = None

        # Create instance and test
        test_obj = TestScanClass()

        # Simulate concurrent scan attempts
        test_obj._running_scans.add("crash_logs")

        # Try to start another crash logs scan
        # Should be prevented by mutex check
        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            test_obj.crash_logs_scan()
            # Should show warning about scan in progress
            mock_warning.assert_called_once_with(test_obj, "Scan in Progress", "A crash logs scan is already in progress.")


class TestThreadReusePrevention:
    """Test that threads are not reused."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_pastebin_thread_not_reused(self, app: QApplication) -> None:
        """Test that Pastebin fetch creates new thread each time."""
        # Test pastebin thread handling
        thread_manager = ThreadManager()

        # Create mock thread and worker
        mock_thread = MagicMock(spec=QThread)
        mock_worker = MagicMock()

        # Register thread
        thread_type = ThreadType.PASTEBIN_FETCH
        assert thread_manager.register_thread(thread_type, mock_thread, mock_worker)

        # Should not be able to register same type again while running
        mock_thread.isRunning.return_value = True
        assert not thread_manager.register_thread(thread_type, MagicMock(), MagicMock())

        # After thread finishes, manager should detect it's not running
        mock_thread.isRunning.return_value = False
        # Remove from internal dict to simulate cleanup
        thread_manager._threads.pop(thread_type, None)
        assert thread_manager.register_thread(thread_type, MagicMock(), MagicMock())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

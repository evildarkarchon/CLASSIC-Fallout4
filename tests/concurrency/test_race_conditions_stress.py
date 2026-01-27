"""Tests for race condition prevention in button state management."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import os
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers"),
]

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QMainWindow

from ClassicLib.Interface.workers.ThreadManager import ThreadManager, ThreadType


class TestRaceConditionPrevention:
    """Test race condition prevention in button state management."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app  # pyright: ignore[reportReturnType]

    def test_scan_mutex_protection(self, app: QApplication) -> None:
        """Test that scan operations are protected by mutex in ScanController."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController
        from ClassicLib.Interface.shared.context import FeatureContext
        from ClassicLib.Interface.shared.signal_hub import SignalHub
        from ClassicLib.Interface.workers.ThreadManager import get_thread_manager

        # Create a minimal main window for the context
        main_window = QMainWindow()

        # Create the context infrastructure
        thread_manager = get_thread_manager()
        signal_hub = SignalHub(main_window)
        context = FeatureContext(
            main_window=main_window,
            thread_manager=thread_manager,
            signal_hub=signal_hub,
        )

        # Create ScanController instance
        scan_controller = ScanController(context)

        # Simulate concurrent scan attempts by adding crash_logs to running scans
        scan_controller._running_scans.add("crash_logs")

        # Try to start another crash logs scan - should be prevented by mutex check
        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            scan_controller.crash_logs_scan()
            # Should show warning about scan in progress
            mock_warning.assert_called_once_with(main_window, "Scan in Progress", "A crash logs scan is already in progress.")

    def test_game_files_mutex_protection(self, app: QApplication) -> None:
        """Test that game files scan operations are protected by mutex."""
        from ClassicLib.Interface.controllers.scan_controller import ScanController
        from ClassicLib.Interface.shared.context import FeatureContext
        from ClassicLib.Interface.shared.signal_hub import SignalHub
        from ClassicLib.Interface.workers.ThreadManager import get_thread_manager

        # Create a minimal main window for the context
        main_window = QMainWindow()

        # Create the context infrastructure
        thread_manager = get_thread_manager()
        signal_hub = SignalHub(main_window)
        context = FeatureContext(
            main_window=main_window,
            thread_manager=thread_manager,
            signal_hub=signal_hub,
        )

        # Create ScanController instance
        scan_controller = ScanController(context)

        # Simulate concurrent scan attempts by adding game_files to running scans
        scan_controller._running_scans.add("game_files")

        # Try to start another game files scan - should be prevented by mutex check
        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            scan_controller.game_files_scan()
            # Should show warning about scan in progress
            mock_warning.assert_called_once_with(main_window, "Scan in Progress", "A game files scan is already in progress.")


class TestThreadReusePrevention:
    """Test that threads are not reused."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app  # pyright: ignore[reportReturnType]

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

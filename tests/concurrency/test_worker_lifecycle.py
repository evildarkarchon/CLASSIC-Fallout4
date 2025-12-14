"""Tests for worker thread lifecycle management."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import os
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")
]

from PySide6.QtWidgets import QApplication

from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker


class TestPapyrusMonitorThreadSafety:
    """Test thread safety in PapyrusMonitorWorker."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app  # pyright: ignore[reportReturnType]

    def test_papyrus_monitor_stop(self) -> None:
        """Test thread-safe stop method."""
        worker = PapyrusMonitorWorker()

        # Initial state
        assert worker._should_run is True

        # Stop should be thread-safe
        worker.stop()
        assert worker._should_run is False

    @patch("ClassicLib.Interface.Papyrus.papyrus_logging")
    def test_papyrus_monitor_run_loop(self, mock_logging: MagicMock, app: QApplication) -> None:
        """Test the run loop respects thread-safe stop."""
        # Create a mock that simulates papyrus_logging and allows controlled stopping
        call_count = [0]

        def mock_logging_func():
            call_count[0] += 1
            # Return different data to trigger stats update
            if call_count[0] == 1:
                return ("NUMBER OF DUMPS    : 5\nNUMBER OF STACKS   : 10\n", 5)
            # Raise exception to exit the loop after first iteration
            raise OSError("Test controlled exit")

        mock_logging.side_effect = mock_logging_func

        # Test 1: Worker stops immediately when _should_run is False
        worker = PapyrusMonitorWorker()
        stats_received = []
        error_received = []

        worker.statsUpdated.connect(lambda stats: stats_received.append(stats))
        worker.error.connect(lambda err: error_received.append(err))

        # Stop before running
        worker.stop()
        worker.run()

        # Should not have received any stats since it was stopped
        assert len(stats_received) == 0
        assert call_count[0] == 0  # Should not have called papyrus_logging

        # Test 2: Worker processes stats and exits on error
        worker2 = PapyrusMonitorWorker()
        stats_received2 = []
        error_received2 = []
        call_count[0] = 0  # Reset counter

        worker2.statsUpdated.connect(lambda stats: stats_received2.append(stats))
        worker2.error.connect(lambda err: error_received2.append(err))

        # Run the worker (will exit after one iteration due to mock)
        worker2.run()

        # Should have received exactly one stats update before the error
        assert len(stats_received2) == 1
        assert stats_received2[0].dumps == 5
        assert stats_received2[0].stacks == 10
        assert len(error_received2) == 1
        assert "Test controlled exit" in error_received2[0]


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app  # pyright: ignore[reportReturnType]

    def test_close_event_cleanup(self, app: QApplication) -> None:
        """Test that closeEvent properly cleans up all threads."""
        # Test thread cleanup on close
        from PySide6.QtCore import QThread

        from ClassicLib.Interface.ThreadManager import ThreadManager, ThreadType

        thread_manager = ThreadManager()

        # Register multiple mock threads
        threads = []
        workers = []
        for thread_type in [ThreadType.UPDATE_CHECK, ThreadType.PASTEBIN_FETCH]:
            mock_thread = MagicMock(spec=QThread)
            mock_worker = MagicMock()
            # Add stop method to worker mock
            mock_worker.stop = MagicMock()
            mock_thread.isRunning.return_value = True
            threads.append(mock_thread)
            workers.append(mock_worker)
            thread_manager.register_thread(thread_type, mock_thread, mock_worker)

        # Stop all threads
        thread_manager.stop_all_threads(wait_ms=100)

        # Verify all threads were asked to quit
        for thread in threads:
            thread.quit.assert_called()

        # Verify all workers were asked to stop (if they have stop method)
        for worker in workers:
            worker.stop.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

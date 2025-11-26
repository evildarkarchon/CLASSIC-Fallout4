"""Tests for ThreadManager class functionality."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import os

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from ClassicLib.Interface.ThreadManager import ThreadManager, ThreadType
from tests.concurrency.conftest import ThreadTestWorker


class TestThreadManager:
    """Test cases for ThreadManager class."""

    @pytest.fixture
    def thread_manager(self) -> ThreadManager:
        """Create a fresh ThreadManager instance."""
        return ThreadManager()

    def test_register_thread(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test thread registration."""
        thread = QThread()
        worker = ThreadTestWorker()

        # Should successfully register
        assert thread_manager.register_thread(ThreadType.UPDATE_CHECK, thread, worker)

        # Should fail to register same type while running
        thread.start()
        assert not thread_manager.register_thread(ThreadType.UPDATE_CHECK, QThread(), ThreadTestWorker())

        # Cleanup
        thread.quit()
        thread.wait()

    def test_start_thread(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test thread starting."""
        thread = QThread()
        worker = ThreadTestWorker()

        # Register thread
        thread_manager.register_thread(ThreadType.PAPYRUS_MONITOR, thread, worker)

        # Connect worker
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)

        # Start should succeed
        assert thread_manager.start_thread(ThreadType.PAPYRUS_MONITOR)

        # Should not start again while running
        assert not thread_manager.start_thread(ThreadType.PAPYRUS_MONITOR)

        # Wait for completion
        thread.wait(1000)

    def test_stop_thread(self, thread_manager: ThreadManager, app: QApplication, test_worker_long: ThreadTestWorker) -> None:
        """Test thread stopping."""
        thread = QThread()
        worker = test_worker_long

        # Setup thread
        thread_manager.register_thread(ThreadType.CRASH_LOGS_SCAN, thread, worker)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)

        # Start thread
        thread_manager.start_thread(ThreadType.CRASH_LOGS_SCAN)

        # Thread should be running
        assert thread_manager.is_thread_running(ThreadType.CRASH_LOGS_SCAN)

        # Stop thread
        worker.stop()
        assert thread_manager.stop_thread(ThreadType.CRASH_LOGS_SCAN, wait_ms=2000)

        # Thread should not be running
        assert not thread_manager.is_thread_running(ThreadType.CRASH_LOGS_SCAN)

    def test_get_running_threads(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test getting running threads."""
        # No threads initially
        assert len(thread_manager.get_running_threads()) == 0

        # Add and start multiple threads
        threads = []
        workers = []
        thread_types = [ThreadType.UPDATE_CHECK, ThreadType.PAPYRUS_MONITOR]

        for thread_type in thread_types:
            thread = QThread()
            worker = ThreadTestWorker()
            threads.append(thread)
            workers.append(worker)

            thread_manager.register_thread(thread_type, thread, worker)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            thread_manager.start_thread(thread_type)

        # Should have 2 running threads
        running = thread_manager.get_running_threads()
        assert len(running) == 2
        assert ThreadType.UPDATE_CHECK in running
        assert ThreadType.PAPYRUS_MONITOR in running

        # Stop threads
        for worker in workers:
            worker.stop()

        for thread in threads:
            thread.quit()
            thread.wait(1000)

    def test_stop_all_threads(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test stopping all threads."""
        # Start multiple threads
        thread_types = [ThreadType.UPDATE_CHECK, ThreadType.PAPYRUS_MONITOR, ThreadType.PASTEBIN_FETCH]

        threads = []
        workers = []

        for thread_type in thread_types:
            thread = QThread()
            worker = ThreadTestWorker(work_time=0.3)
            threads.append(thread)
            workers.append(worker)

            thread_manager.register_thread(thread_type, thread, worker)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            thread_manager.start_thread(thread_type)

        # All threads should be running
        assert len(thread_manager.get_running_threads()) == 3

        # Stop all threads
        for worker in workers:
            worker.stop()
        thread_manager.stop_all_threads(wait_ms=2000)

        # No threads should be running
        assert len(thread_manager.get_running_threads()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

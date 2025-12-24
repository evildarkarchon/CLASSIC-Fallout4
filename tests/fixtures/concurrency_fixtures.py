"""
Concurrency and thread safety fixtures for CLASSIC-Fallout4 test suite.

This module provides fixtures for testing thread safety, concurrency patterns,
and parallel execution scenarios.

Consolidated from:
- tests/concurrency/conftest.py
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QThread, Signal, Slot


class ThreadTestWorker(QObject):
    """Simple test worker for thread testing.

    This worker simulates work that takes time to complete,
    useful for testing threading patterns and synchronization.

    Attributes:
        finished: Signal emitted when work is completed.
        result: Signal emitted with the result string.
    """

    finished = Signal()
    result = Signal(str)

    def __init__(self, work_time: float = 0.1) -> None:
        """Initialize the test worker.

        Args:
            work_time: Duration in seconds to simulate work.
        """
        super().__init__()
        self._work_time = work_time
        self._should_run = True

    @Slot()
    def run(self) -> None:
        """Simulate some work.

        Runs in a loop until work_time expires or stop() is called.
        Emits result and finished signals when complete.
        """
        import time

        start_time = time.time()
        while self._should_run and (time.time() - start_time) < self._work_time:
            QThread.msleep(10)
        self.result.emit("Work completed")
        self.finished.emit()

    def stop(self) -> None:
        """Stop the worker."""
        self._should_run = False


@pytest.fixture
def concurrency_test_worker() -> ThreadTestWorker:
    """Create a test worker instance.

    Returns:
        A ThreadTestWorker with default work time (0.1s).
    """
    return ThreadTestWorker()


@pytest.fixture
def concurrency_test_worker_long() -> ThreadTestWorker:
    """Create a test worker with longer work time.

    Returns:
        A ThreadTestWorker with 0.5s work time.
    """
    return ThreadTestWorker(work_time=0.5)


@pytest.fixture
def concurrency_create_test_logs(tmp_path: Path) -> list[Path]:
    """Create test log files for concurrency testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        List of paths to test log files.
    """
    logs = []
    for i in range(5):
        log_file = tmp_path / f"test_log_{i}.log"
        # Format expected by the tests: first line starts with "Log file ", exactly 3 lines
        log_file.write_text(f"Log file {i} crash data\nLine 2\nLine 3")
        logs.append(log_file)
    return logs


# Backward compatibility aliases (deprecated - use prefixed names)
test_worker = concurrency_test_worker
test_worker_long = concurrency_test_worker_long
create_test_logs = concurrency_create_test_logs

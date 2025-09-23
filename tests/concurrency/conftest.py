"""
Shared fixtures for concurrency and thread safety tests.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication


@pytest.fixture
def app() -> QApplication:
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class ThreadTestWorker(QObject):
    """Simple test worker for thread testing."""

    finished = Signal()
    result = Signal(str)

    def __init__(self, work_time: float = 0.1) -> None:
        super().__init__()
        self._work_time = work_time
        self._should_run = True

    @Slot()
    def run(self) -> None:
        """Simulate some work."""
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
def test_worker() -> ThreadTestWorker:
    """Create a test worker instance."""
    return ThreadTestWorker()


@pytest.fixture
def test_worker_long() -> ThreadTestWorker:
    """Create a test worker with longer work time."""
    return ThreadTestWorker(work_time=0.5)


@pytest.fixture
def create_test_logs(tmp_path: Path) -> list[Path]:
    """Create test log files for concurrency testing."""
    logs = []
    for i in range(5):
        log_file = tmp_path / f"test_log_{i}.log"
        # Format expected by the tests: first line starts with "Log file ", exactly 3 lines
        log_file.write_text(f"Log file {i} crash data\nLine 2\nLine 3")
        logs.append(log_file)
    return logs

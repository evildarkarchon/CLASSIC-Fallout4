"""
Unit tests for Worker error signal emissions.

Tests that CrashLogsScanWorker and GameFilesScanWorker emit error_occurred signals
with correct parameters when errors occur during scanning operations.
"""
# ruff: noqa: ANN201, ANN001, ARG001, PLR6301, ARG002, ANN202

import os
from unittest.mock import patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker, GameFilesScanWorker


@pytest.mark.unit
@pytest.mark.gui
class TestCrashLogsScanWorkerErrorSignals:
    """Test error signal emissions from CrashLogsScanWorker."""

    @pytest.fixture
    def worker(self, qtbot):
        """Create a CrashLogsScanWorker instance."""
        return CrashLogsScanWorker()

    def test_error_occurred_signal_emitted_on_scan_failure(self, worker, qtbot):
        """Test that error_occurred signal is emitted when scan fails."""
        # Track signal emissions
        error_occurred_spy = []

        def capture_error(title, message, details):
            error_occurred_spy.append((title, message, details))

        worker.error_occurred.connect(capture_error)

        # Mock the scan to raise an exception
        test_error = RuntimeError("Test scan failure")
        with patch.object(worker, "_perform_crash_logs_scan", side_effect=test_error):
            # Run the worker
            worker.run()

            # Wait for signals to be processed
            # qtbot.wait(100)

        # Verify error_occurred signal was emitted
        assert len(error_occurred_spy) == 1
        title, message, details = error_occurred_spy[0]

        # Verify signal content
        assert title == "Crash Log Scan Failed"
        assert "Test scan failure" in message
        assert "RuntimeError: Test scan failure" in details
        assert "Traceback" in details

    def test_error_occurred_contains_traceback(self, worker, qtbot):
        """Test that error_occurred signal includes full traceback."""
        error_details = None

        def capture_details(title, message, details):
            nonlocal error_details
            error_details = details

        worker.error_occurred.connect(capture_details)

        # Mock scan with exception
        with patch.object(worker, "_perform_crash_logs_scan", side_effect=ValueError("Bad value")):
            worker.run()
            # qtbot.wait(100)

        # Verify traceback is present
        assert error_details is not None
        assert "Traceback" in error_details
        assert "ValueError: Bad value" in error_details
        assert "_perform_crash_logs_scan" in error_details  # Function name in traceback


@pytest.mark.unit
@pytest.mark.gui
class TestGameFilesScanWorkerErrorSignals:
    """Test error signal emissions from GameFilesScanWorker."""

    @pytest.fixture
    def worker(self, qtbot):
        """Create a GameFilesScanWorker instance."""
        return GameFilesScanWorker()

    def test_error_occurred_signal_emitted_on_game_scan_failure(self, worker, qtbot):
        """Test that error_occurred signal is emitted when game scan fails."""
        error_occurred_spy = []

        def capture_error(title, message, details):
            error_occurred_spy.append((title, message, details))

        worker.error_occurred.connect(capture_error)

        # Mock the scan to raise an exception
        test_error = OSError("Failed to read game files")
        with patch.object(worker, "_process_game_results_scan", side_effect=test_error):
            worker.run()
            # qtbot.wait(100)

        # Verify error_occurred signal was emitted
        assert len(error_occurred_spy) == 1
        title, message, details = error_occurred_spy[0]

        # Verify signal content
        assert title == "Game Files Scan Failed"
        assert "Failed to read game files" in message
        assert "OSError: Failed to read game files" in details

    def test_error_message_format(self, worker, qtbot):
        """Test that error message has the correct format."""
        captured_message = None

        def capture_message(title, message, details):
            nonlocal captured_message
            captured_message = message

        worker.error_occurred.connect(capture_message)

        # Mock scan with specific error
        error_msg = "Permission denied"
        with patch.object(worker, "_process_game_results_scan", side_effect=PermissionError(error_msg)):
            worker.run()
            # qtbot.wait(100)

        # Verify message format
        assert captured_message is not None
        assert captured_message.startswith("An error occurred while processing game files:")
        assert error_msg in captured_message

    def test_finished_signal_emitted_after_error(self, worker, qtbot):
        """Test that finished signal is emitted even after error."""
        finished_emitted = False
        error_emitted = False

        def capture_finished():
            nonlocal finished_emitted
            finished_emitted = True

        def capture_error(title, message, details):
            nonlocal error_emitted
            error_emitted = True

        worker.scan_finished.connect(capture_finished)
        worker.error_occurred.connect(capture_error)

        # Mock scan with exception
        with patch.object(worker, "_process_game_results_scan", side_effect=RuntimeError("Error")):
            worker.run()
            # qtbot.wait(100)

        # Both signals should be emitted
        assert error_emitted, "Error signal should be emitted"
        assert finished_emitted, "Finished signal should be emitted in finally block"

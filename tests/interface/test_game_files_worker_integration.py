"""
Unit tests for GameFilesScanWorker with asyncio.run() thread-safe execution.

This test module verifies that:
1. GameFilesScanWorker uses asyncio.run() for thread-safe async execution
2. Rust acceleration is checked and logged (preparing for future classic_scangame)
3. Worker signals are emitted correctly
4. Error handling works properly
5. Performance metrics are logged

Note: Workers use asyncio.run() directly instead of AsyncBridge because AsyncBridge
is a main-thread singleton. Using it from worker threads causes cross-thread
QObject parenting errors.
"""

import os
from unittest.mock import patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import QObject, QThread

# Test worker initialization


@pytest.mark.unit
def test_game_files_worker_exists():
    """Test that GameFilesScanWorker can be imported."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    assert GameFilesScanWorker is not None, "GameFilesScanWorker should be importable"
    assert hasattr(GameFilesScanWorker, "run"), "Should have run method"
    assert hasattr(GameFilesScanWorker, "scan_finished"), "Should have scan_finished signal"


@pytest.mark.unit
def test_worker_signals():
    """Test that worker has all required signals."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    worker = GameFilesScanWorker()

    # Verify signals exist
    assert hasattr(worker, "scan_finished"), "Should have scan_finished signal"
    assert hasattr(worker, "error_occurred"), "Should have error occurred signal"


# Test asyncio.run() usage for thread-safe async execution


@pytest.mark.unit
def test_worker_uses_asyncio_run():
    """Test that worker uses asyncio.run() for thread-safe async execution.

    Workers run in separate QThreads and must use asyncio.run() directly.
    AsyncBridge is a main-thread singleton and cannot be used from worker threads
    without causing cross-thread QObject parenting errors.
    """
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    # Create worker
    worker = GameFilesScanWorker()

    # Mock asyncio.run() to capture calls
    with patch("asyncio.run") as mock_asyncio_run:
        with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
            # Run the scan
            worker._process_game_results_scan()

            # Verify asyncio.run() was called
            assert mock_asyncio_run.called, "Should call asyncio.run() for thread-safe execution"
            assert mock_asyncio_run.call_count == 1, "Should call asyncio.run() exactly once"


@pytest.mark.unit
def test_no_manual_event_loop_creation():
    """Test that worker doesn't create manual event loops.

    Workers should use asyncio.run() which manages its own event loop internally.
    They should NOT manually call asyncio.new_event_loop() or asyncio.set_event_loop().
    """
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    worker = GameFilesScanWorker()

    # Mock asyncio.run() to prevent actual execution
    with patch("asyncio.run"):
        with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
            with patch("asyncio.new_event_loop") as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    worker._process_game_results_scan()

                    # Verify manual event loop creation was NOT used
                    assert not mock_new_loop.called, "Should NOT create manual event loop"
                    assert not mock_set_loop.called, "Should NOT manually set event loop"


# Test Rust acceleration detection


@pytest.mark.unit
@pytest.mark.rust
def test_rust_acceleration_detection():
    """Test that Rust acceleration is detected and logged (preparing for future)."""
    from ClassicLib.integration.status import is_rust_accelerated

    # Check if Rust is available (currently False, but preparing for future)
    rust_available = is_rust_accelerated("scangame")

    # Currently we expect False, but this prepares for future classic_scangame module
    assert not rust_available, "classic_scangame not yet implemented (expected)"


@pytest.mark.unit
def test_rust_status_logging():
    """Test that Rust acceleration status is logged."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker
    from ClassicLib.Logger import logger

    worker = GameFilesScanWorker()

    # Mock asyncio.run() to prevent actual async execution
    with patch("asyncio.run"):
        with patch("ClassicLib.integration.status.is_rust_accelerated") as mock_rust_check:
            with patch.object(logger, "info") as mock_log_info:
                with patch.object(logger, "debug"):
                    # Test with Rust available (future scenario)
                    mock_rust_check.return_value = True

                    worker._process_game_results_scan()

                    # Check if Rust acceleration was logged
                    info_calls = [str(call) for call in mock_log_info.call_args_list]
                    rust_logged = any("Rust acceleration" in str(call) for call in info_calls)

                    assert rust_logged, "Should log Rust acceleration status when available"


# Test signal emissions


@pytest.mark.unit
def test_success_signal_emission():
    """Test that finished signal is emitted on successful scan."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    worker = GameFilesScanWorker()

    # Track signal emissions
    finished_emitted = []

    worker.scan_finished.connect(lambda: finished_emitted.append(True))

    # Mock successful scan
    with patch.object(worker, "_process_game_results_scan"):
        worker.run()

    # Verify signals
    assert len(finished_emitted) == 1, "Should emit finished signal"


@pytest.mark.unit
def test_error_signal_emission():
    """Test that error signals are emitted on scan failure."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    worker = GameFilesScanWorker()

    # Track signal emissions
    finished_emitted = []
    error_emitted = []

    worker.scan_finished.connect(lambda: finished_emitted.append(True))
    worker.error_occurred.connect(lambda title, msg, details: error_emitted.append((title, msg, details)))

    # Mock scan failure
    with patch.object(worker, "_process_game_results_scan", side_effect=RuntimeError("Test error")):
        worker.run()

    # Verify signals
    assert len(finished_emitted) == 1, "Should emit finished signal even on error"
    assert len(error_emitted) == 1, "Should emit error occurred signal"

    # Verify error details
    title, msg, details = error_emitted[0]
    assert "Failed" in title, "Error title should indicate failure"
    assert "Test error" in msg, "Error message should contain exception message"


# Test error handling


@pytest.mark.unit
def test_finished_signal_always_emitted():
    """Test that finished signal is always emitted, even on error."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    worker = GameFilesScanWorker()

    finished_emitted = []
    worker.scan_finished.connect(lambda: finished_emitted.append(True))

    # Test with success
    with patch.object(worker, "_process_game_results_scan"):
        worker.run()

    assert len(finished_emitted) == 1, "Should emit finished on success"

    # Test with error
    finished_emitted.clear()
    with patch.object(worker, "_process_game_results_scan", side_effect=RuntimeError("Error")):
        worker.run()

    assert len(finished_emitted) == 1, "Should emit finished on error too"


# Test performance logging


@pytest.mark.unit
def test_performance_metrics_logged():
    """Test that performance metrics are logged."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker
    from ClassicLib.Logger import logger

    worker = GameFilesScanWorker()

    # Mock asyncio.run() to prevent actual async execution
    with patch("asyncio.run"):
        with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
            with patch.object(logger, "info") as mock_log_info:
                with patch.object(logger, "debug") as mock_log_debug:
                    worker._process_game_results_scan()

                    # Check for performance logging
                    info_calls = [str(call) for call in mock_log_info.call_args_list]
                    debug_calls = [str(call) for call in mock_log_debug.call_args_list]

                    # Should log scan completion with timing
                    timing_logged = any("Game files scan completed" in str(call) for call in info_calls)
                    assert timing_logged, "Should log scan completion with timing metrics"

                    # Should log start time
                    start_logged = any("Starting game files scan" in str(call) for call in debug_calls)
                    assert start_logged, "Should log scan start time"


# Test thread safety


@pytest.mark.unit
def test_worker_is_qobject():
    """Test that worker is a QObject and can be moved to thread."""
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    worker = GameFilesScanWorker()

    # Should be a QObject
    assert isinstance(worker, QObject), "Worker should be a QObject"

    # Should be movable to thread (basic check)
    thread = QThread()
    worker.moveToThread(thread)

    # Cleanup
    thread.quit()
    thread.wait()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

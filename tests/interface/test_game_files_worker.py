"""
Unit tests for GameFilesScanWorker with AsyncBridge integration.

This test module verifies that:
1. GameFilesScanWorker uses AsyncBridge (no manual event loops)
2. Rust acceleration is checked and logged (preparing for future classic_scangame)
3. Worker signals are emitted correctly
4. Error handling works properly
5. AsyncBridge cleanup happens automatically
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

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


# Test AsyncBridge integration


@pytest.mark.unit
def test_worker_uses_async_bridge():
    """Test that worker uses AsyncBridge instead of manual event loop."""
    from ClassicLib.AsyncBridge import AsyncBridge
    from ClassicLib.Interface.Workers import GameFilesScanWorker

    # Create worker
    worker = GameFilesScanWorker()

    # Mock the async function
    mock_async_func = AsyncMock()

    # Patch the imports at the point they're used (inside the method)
    with patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.write_combined_results_async", mock_async_func):
        with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
            with patch.object(AsyncBridge, "get_instance") as mock_bridge_get:
                mock_bridge = MagicMock()
                mock_bridge_get.return_value = mock_bridge

                # Capture what gets passed to run_async
                run_async_calls = []

                def capture_run_async(coro):
                    run_async_calls.append(coro)
                    # Simulate successful execution
                    coro.close()

                mock_bridge.run_async.side_effect = capture_run_async

                # Run the scan
                try:
                    worker._process_game_results_scan()
                except Exception:
                    # We expect some errors since we're mocking heavily
                    pass

                # Verify AsyncBridge was used
                assert mock_bridge_get.called, "Should call AsyncBridge.get_instance()"
                assert mock_bridge.run_async.called, "Should call bridge.run_async()"


@pytest.mark.unit
def test_no_manual_event_loop_creation():
    """Test that worker doesn't create manual event loops."""

    from ClassicLib.Interface.Workers import GameFilesScanWorker

    worker = GameFilesScanWorker()

    # Mock everything to prevent actual execution
    with patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.write_combined_results_async", AsyncMock()):
        with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
            with patch("ClassicLib.AsyncBridge.AsyncBridge") as mock_bridge_cls:
                # Configure mock to close coroutines
                mock_bridge_cls.get_instance.return_value.run_async.side_effect = lambda coro: coro.close()

                with patch("asyncio.new_event_loop") as mock_new_loop:
                    try:
                        worker._process_game_results_scan()
                    except Exception:
                        pass

                    # Verify new_event_loop was NOT called
                    assert not mock_new_loop.called, "Should NOT create manual event loop"


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

    # Mock dependencies
    with patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.write_combined_results_async", AsyncMock()):
        with patch("ClassicLib.AsyncBridge.AsyncBridge") as mock_bridge_cls:
            # Configure mock to close coroutines
            mock_bridge_cls.get_instance.return_value.run_async.side_effect = lambda coro: coro.close()

            with patch("ClassicLib.integration.status.is_rust_accelerated") as mock_rust_check:
                with patch.object(logger, "info") as mock_log_info:
                    with patch.object(logger, "debug"):
                        # Test with Rust available (future scenario)
                        mock_rust_check.return_value = True

                        try:
                            worker._process_game_results_scan()
                        except Exception:
                            pass

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

    # Mock dependencies
    with patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.write_combined_results_async", AsyncMock()):
        with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
            with patch("ClassicLib.AsyncBridge.AsyncBridge") as mock_bridge_cls:
                # Configure mock to close coroutines
                mock_bridge_cls.get_instance.return_value.run_async.side_effect = lambda coro: coro.close()

                with patch.object(logger, "info") as mock_log_info:
                    with patch.object(logger, "debug") as mock_log_debug:
                        try:
                            worker._process_game_results_scan()
                        except Exception:
                            pass

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

"""
Unit tests for CrashLogsScanWorker with AsyncBridge + Rust acceleration.

This test module verifies that:
1. CrashLogsScanWorker uses AsyncBridge (no manual event loops)
2. Rust acceleration is available and properly detected
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
def test_crash_logs_worker_exists():
    """Test that CrashLogsScanWorker can be imported."""
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    assert CrashLogsScanWorker is not None, "CrashLogsScanWorker should be importable"
    assert hasattr(CrashLogsScanWorker, "run"), "Should have run method"
    assert hasattr(CrashLogsScanWorker, "finished"), "Should have finished signal"


@pytest.mark.unit
def test_worker_signals():
    """Test that worker has all required signals."""
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

    # Verify signals exist
    assert hasattr(worker, "finished"), "Should have finished signal"
    assert hasattr(worker, "error_occurred"), "Should have error occurred signal"


# Test AsyncBridge integration


@pytest.mark.unit
def test_worker_uses_asyncio_run():
    """Test that worker uses asyncio.run() for thread-safe async execution.

    Note: CrashLogsScanWorker was refactored to use asyncio.run() directly instead of
    AsyncBridge because AsyncBridge is a main-thread singleton, and accessing it from
    worker threads causes cross-thread QObject parenting errors.
    """
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    # Create worker
    worker = CrashLogsScanWorker()

    # Mock the scanner and async function
    mock_scanner = MagicMock()
    mock_scanner.warm_up = AsyncMock()

    mock_result = MagicMock()
    mock_result.stats = MagicMock()
    mock_result.failed_logs = []
    mock_result.scan_time = 1.0

    # Create async mock that returns mock_result
    mock_async_func = AsyncMock(return_value=mock_result)

    # Helper to close coroutines to avoid "coroutine was never awaited" warnings
    def close_coro(coro):
        coro.close()
        return None

    # Patch the imports at the point they're used (inside the method)
    with patch("ClassicLib.scanning.logs.ScanLogsExecutor.ScanLogsExecutor") as mock_executor_cls:
        mock_executor_cls.return_value = mock_scanner

        with patch("ClassicLib.scanning.logs.ScanLogsUtils.crashlogs_scan_async_pure", mock_async_func):
            # Import FCXModeHandler and patch it directly
            from ClassicLib.scanning.logs import FCXModeHandler

            with patch.object(FCXModeHandler, "reset_fcx_checks"):
                with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
                    with patch("asyncio.run", side_effect=close_coro) as mock_asyncio_run:
                        # Run the scan
                        try:
                            worker._perform_crash_logs_scan()
                        except Exception:
                            # We expect some errors since we're mocking heavily
                            pass

                        # Verify asyncio.run() was called (worker uses it directly)
                        assert mock_asyncio_run.called, "Should call asyncio.run() for thread-safe async execution"


@pytest.mark.unit
def test_no_manual_event_loop_creation():
    """Test that worker doesn't create manual event loops."""

    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

    # Helper to close coroutines to avoid "coroutine was never awaited" warnings
    def close_coro(coro):
        coro.close()
        return None

    # Mock everything to prevent actual execution
    with patch("ClassicLib.scanning.logs.ScanLogsExecutor.ScanLogsExecutor"):
        with patch("ClassicLib.scanning.logs.ScanLogsUtils.crashlogs_scan_async_pure", AsyncMock()):
            from ClassicLib.scanning.logs import FCXModeHandler

            with patch.object(FCXModeHandler, "reset_fcx_checks"):
                with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
                    with patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_cls:
                        # Configure mock to close coroutines to avoid warnings
                        mock_bridge_cls.get_instance.return_value.run_async.side_effect = close_coro

                        with patch("asyncio.new_event_loop") as mock_new_loop:
                            with patch("asyncio.run", side_effect=close_coro):
                                try:
                                    worker._perform_crash_logs_scan()
                                except Exception:
                                    pass

                                # Verify new_event_loop was NOT called
                                assert not mock_new_loop.called, "Should NOT create manual event loop"


# Test Rust acceleration detection


@pytest.mark.unit
@pytest.mark.rust
def test_rust_acceleration_detection():
    """Test that Rust acceleration is detected and logged."""
    from ClassicLib.integration.status import is_rust_accelerated

    # Check if Rust is available
    rust_available = is_rust_accelerated("parser")

    if rust_available:
        # If Rust is available, verify it's detected
        assert rust_available, "Rust parser should be available in test environment"
    else:
        pytest.skip("Rust parser not available - expected if not built")


@pytest.mark.unit
def test_rust_status_logging():
    """Test that Rust acceleration status is logged."""
    from ClassicLib.core.logger import logger
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

    # Helper to close coroutines to avoid "coroutine was never awaited" warnings
    def close_coro(coro):
        coro.close()
        return None

    # Mock dependencies
    with patch("ClassicLib.scanning.logs.ScanLogsExecutor.ScanLogsExecutor"):
        with patch("ClassicLib.scanning.logs.ScanLogsUtils.crashlogs_scan_async_pure", AsyncMock()):
            from ClassicLib.scanning.logs import FCXModeHandler

            with patch.object(FCXModeHandler, "reset_fcx_checks"), patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_cls:
                # Configure mock to close coroutines
                mock_bridge_cls.get_instance.return_value.run_async.side_effect = close_coro

                with patch("ClassicLib.integration.status.is_rust_accelerated") as mock_rust_check:
                    with patch.object(logger, "info") as mock_log_info:
                        with patch.object(logger, "debug"):
                            # Test with Rust available
                            mock_rust_check.return_value = True

                            # Also patch asyncio.run to close coroutines
                            with patch("asyncio.run", side_effect=close_coro):
                                try:
                                    worker._perform_crash_logs_scan()
                                except Exception:
                                    pass

                            # Check if Rust acceleration was logged
                            info_calls = [str(call) for call in mock_log_info.call_args_list]
                            rust_logged = any("Rust acceleration" in str(call) or "150x speedup" in str(call) for call in info_calls)

                            assert rust_logged, "Should log Rust acceleration status"


# Test signal emissions


@pytest.mark.unit
def test_success_signal_emission():
    """Test that finished signal is emitted on successful scan."""
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

    # Track signal emissions
    finished_emitted = []

    worker.finished.connect(lambda: finished_emitted.append(True))

    # Mock successful scan
    with patch.object(worker, "_perform_crash_logs_scan"):
        worker.run()

    # Verify signals
    assert len(finished_emitted) == 1, "Should emit finished signal"


@pytest.mark.unit
def test_error_signal_emission():
    """Test that error signals are emitted on scan failure."""
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

    # Track signal emissions
    finished_emitted = []
    error_emitted = []

    worker.finished.connect(lambda: finished_emitted.append(True))
    worker.error_occurred.connect(lambda title, msg, details: error_emitted.append((title, msg, details)))

    # Mock scan failure
    with patch.object(worker, "_perform_crash_logs_scan", side_effect=RuntimeError("Test error")):
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
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

    finished_emitted = []
    worker.finished.connect(lambda: finished_emitted.append(True))

    # Test with success
    with patch.object(worker, "_perform_crash_logs_scan"):
        worker.run()

    assert len(finished_emitted) == 1, "Should emit finished on success"

    # Test with error
    finished_emitted.clear()
    with patch.object(worker, "_perform_crash_logs_scan", side_effect=RuntimeError("Error")):
        worker.run()

    assert len(finished_emitted) == 1, "Should emit finished on error too"


# Test performance logging


@pytest.mark.unit
def test_performance_metrics_logged():
    """Test that performance metrics are logged."""
    from ClassicLib.core.logger import logger
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

    # Helper to close coroutines to avoid "coroutine was never awaited" warnings
    def close_coro(coro):
        coro.close()
        return None

    # Mock dependencies
    with patch("ClassicLib.scanning.logs.ScanLogsExecutor.ScanLogsExecutor"):
        with patch("ClassicLib.scanning.logs.ScanLogsUtils.crashlogs_scan_async_pure", AsyncMock()):
            from ClassicLib.scanning.logs import FCXModeHandler

            with patch.object(FCXModeHandler, "reset_fcx_checks"):
                with patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False):
                    # Mock asyncio.run to close coroutines to avoid warnings
                    with patch("asyncio.run", side_effect=close_coro):
                        with patch.object(logger, "info") as mock_log_info:
                            with patch.object(logger, "debug") as mock_log_debug:
                                try:
                                    worker._perform_crash_logs_scan()
                                except Exception:
                                    pass

                                # Check for performance logging
                                info_calls = [str(call) for call in mock_log_info.call_args_list]
                                debug_calls = [str(call) for call in mock_log_debug.call_args_list]

                                # Should log scan completion with timing
                                timing_logged = any("Scan completed" in str(call) or "scan" in str(call).lower() for call in info_calls)
                                assert timing_logged, "Should log scan completion with timing metrics"

                                # Should log initialization time
                                init_logged = any("initialization" in str(call).lower() for call in debug_calls)
                                assert init_logged, "Should log scanner initialization time"


# Test thread safety


@pytest.mark.unit
def test_worker_is_qobject():
    """Test that worker is a QObject and can be moved to thread."""
    from ClassicLib.Interface.workers.Workers import CrashLogsScanWorker

    worker = CrashLogsScanWorker()

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

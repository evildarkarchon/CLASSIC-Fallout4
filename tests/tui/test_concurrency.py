"""Concurrency and thread-safety tests for TUI components."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.TUI.handlers.papyrus_handler import TuiPapyrusHandler
from ClassicLib.TUI.handlers.scan_handler import TuiScanHandler
from ClassicLib.TUI.widgets.output_viewer import OutputViewer


class TestConcurrencySafety:
    """Test suite for verifying thread-safety and concurrency fixes."""

    @pytest.mark.asyncio
    async def test_concurrent_scan_protection(self):
        """Test that concurrent scans are properly prevented."""
        handler = TuiScanHandler()
        call_count = 0

        async def mock_scan_delay(*args, **kwargs):
            """Simulate a scan that takes some time."""
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate scan time
            # Return 4-item tuple as expected by scan_handler line 119
            return ("test.log", "Scan report", False, {"stats": "test"})

        # Mock the scanner to simulate a long-running scan
        # Patch where ClassicScanLogs is used (in scan_handler's namespace)
        from pathlib import Path

        with patch("ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs") as mock_cls:
            mock_scanner = MagicMock()
            # Set up attributes that the handler expects
            mock_scanner.yamldata = MagicMock()
            mock_scanner.crashlogs = []
            mock_scanner.fcx_mode = False
            mock_scanner.show_formid_values = False
            mock_scanner.formid_db_exists = False
            mock_scanner.crashlog_list = [Path("test.log")]  # Use Path object
            mock_scanner.process_crashlog_async = mock_scan_delay
            mock_cls.return_value = mock_scanner

            # Mock OrchestratorCore as a context manager (patch where it's imported from)
            from unittest.mock import AsyncMock

            with patch("ClassicLib.ScanLog.OrchestratorCore.OrchestratorCore") as mock_orchestrator_cls:
                mock_orchestrator = AsyncMock()
                mock_orchestrator.__aenter__ = AsyncMock(return_value=mock_orchestrator)
                mock_orchestrator.__aexit__ = AsyncMock(return_value=None)
                mock_orchestrator_cls.return_value = mock_orchestrator

                # Mock write_report_to_file_async (imported locally in the function)
                with patch("CLASSIC_ScanLogs.write_report_to_file_async", AsyncMock()), patch(
                    "ClassicLib.TUI.handlers.scan_handler.init_message_handler"
                ):
                    # Try to start multiple scans concurrently
                    results = await asyncio.gather(
                        handler.perform_crash_scan(), handler.perform_crash_scan(), handler.perform_crash_scan(), return_exceptions=True
                    )

                    # Count successes and failures
                    success_count = sum(1 for r in results if r is True)
                    failure_count = sum(1 for r in results if r is False)

                    # Only one scan should actually run
                    assert call_count == 1, f"Expected 1 scan to run, but {call_count} ran"
                    assert success_count == 1, f"Expected 1 success, got {success_count}"
                    assert failure_count == 2, f"Expected 2 blocked scans, got {failure_count}"

    @pytest.mark.asyncio
    async def test_papyrus_monitoring_cleanup(self):
        """Test proper cleanup of monitoring tasks."""
        handler = TuiPapyrusHandler()

        # Patch where papyrus_logging is imported in the actual handler
        with patch("ClassicLib.TUI.handlers.papyrus.tui_papyrus_handler.papyrus_logging") as mock_logging:
            mock_logging.return_value = ("Test output", 0)

            # Start monitoring
            await handler.start_monitoring()
            assert handler.is_monitoring is True
            assert handler.monitor_task is not None

            # Store task reference
            task = handler.monitor_task

            # Stop monitoring
            await handler.stop_monitoring()

            # Verify cleanup
            assert handler.is_monitoring is False
            assert handler.monitor_task is None
            assert task.done() or task.cancelled()

    @pytest.mark.asyncio
    async def test_rapid_start_stop_monitoring(self):
        """Test rapid start/stop cycles don't cause issues."""
        handler = TuiPapyrusHandler()

        # Patch where papyrus_logging is imported in the actual handler
        with patch("ClassicLib.TUI.handlers.papyrus.tui_papyrus_handler.papyrus_logging") as mock_logging:
            mock_logging.return_value = ("Test output", 0)

            # Rapid start/stop cycles
            for _ in range(5):
                await handler.start_monitoring()
                assert handler.is_monitoring is True
                await handler.stop_monitoring()
                assert handler.is_monitoring is False

    def test_output_buffer_thread_safety(self):
        """Test thread-safe operations on output buffer."""
        viewer = OutputViewer()

        # Simulate concurrent writes from multiple threads
        import threading

        errors = []

        def write_messages(start_idx):
            try:
                for i in range(100):
                    viewer.append_output(f"Message {start_idx + i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=write_messages, args=(i * 100,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Buffer should contain messages (exact count may vary due to maxlen)
        assert len(viewer._output_buffer) > 0

    def test_concurrent_buffer_operations(self):
        """Test concurrent clear and append operations."""
        viewer = OutputViewer()

        import threading
        import time

        def writer():
            for _ in range(50):
                viewer.append_output("Test message")
                time.sleep(0.001)

        def clearer():
            for _ in range(10):
                viewer.clear()
                time.sleep(0.005)

        def searcher():
            for _ in range(20):
                with viewer._buffer_lock:
                    _ = list(viewer._output_buffer)
                # Simulate search operation
                time.sleep(0.002)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=clearer),
            threading.Thread(target=searcher),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Test passes if no deadlock or crash occurred
        assert True

    @pytest.mark.asyncio
    async def test_settings_operations_non_blocking(self):
        """Test that settings operations don't block the event loop."""
        handler = TuiScanHandler()

        with (
            patch("ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs"),
            patch("ClassicLib.TUI.handlers.scan_handler.init_message_handler"),
            patch("ClassicLib.TUI.handlers.scan_handler.classic_settings") as mock_settings,
        ):
            mock_settings.return_value = "/old/path"
            mock_settings.set_value = MagicMock()

            # This should complete quickly without blocking
            start_time = asyncio.get_event_loop().time()
            await handler.perform_crash_scan("/custom/folder")
            end_time = asyncio.get_event_loop().time()

            # Should complete in reasonable time (not blocked)
            assert (end_time - start_time) < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_monitoring_requests(self):
        """Test handling of concurrent monitoring start requests."""
        handler = TuiPapyrusHandler()

        # Patch where papyrus_logging is imported in the actual handler
        with patch("ClassicLib.TUI.handlers.papyrus.tui_papyrus_handler.papyrus_logging") as mock_logging:
            mock_logging.return_value = ("Test output", 0)

            # Try to start monitoring multiple times concurrently
            results = await asyncio.gather(
                handler.start_monitoring(), handler.start_monitoring(), handler.start_monitoring(), return_exceptions=True
            )

            # Only first should succeed
            success_count = sum(1 for r in results if r is True)
            assert success_count == 1

            # Clean up
            await handler.stop_monitoring()

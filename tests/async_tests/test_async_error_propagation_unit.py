"""
Unit tests for AsyncIntegration error propagation patterns.

This module tests error handling, exception propagation,
and edge cases in the AsyncIntegration module.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncIntegration import async_crashlogs_scan, run_async_scan


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncErrorPropagation:
    """Unit tests for error propagation in AsyncIntegration."""

    @pytest.fixture
    def mock_base_dependencies(self):
        """Base mock setup for error testing."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files") as mock_get_files, \
             patch("ClassicLib.ScanLog.AsyncIntegration.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info") as mock_msg_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress_ctx, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo") as mock_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.DB_PATHS", []):

            # Configure basic mocks
            mock_yaml_cache.batch_get_settings.return_value = [(), False, False, False]

            # Setup progress context mock
            mock_progress = MagicMock()
            mock_progress.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.__exit__ = MagicMock()
            mock_progress.update = MagicMock()
            mock_progress_ctx.return_value = mock_progress

            yield {
                "get_files": mock_get_files,
                "yaml_cache": mock_yaml_cache,
                "msg_info": mock_msg_info,
                "progress_ctx": mock_progress_ctx,
                "progress": mock_progress,
                "info": mock_info
            }

    @pytest.mark.asyncio
    async def test_async_error_propagation_from_reformat(self, mock_base_dependencies):
        """Test error propagation when async reformatting fails."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        reformat_error = asyncio.TimeoutError("Reformat operation timed out")

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat:
            mock_reformat.side_effect = reformat_error

            # Should propagate the timeout error
            with pytest.raises(asyncio.TimeoutError, match="Reformat operation timed out"):
                await async_crashlogs_scan()

            # Verify reformat was attempted
            mock_reformat.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_error_propagation_from_cache_loading(self, mock_base_dependencies):
        """Test error propagation when cache loading fails."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        cache_error = MemoryError("Insufficient memory for cache loading")

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load:

            mock_reformat.return_value = None
            mock_load.side_effect = cache_error

            # Should propagate the memory error
            with pytest.raises(MemoryError, match="Insufficient memory for cache loading"):
                await async_crashlogs_scan()

            # Verify both operations were attempted in order
            mock_reformat.assert_called_once()
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_context_manager_error_propagation(self, mock_base_dependencies):
        """Test error propagation from OrchestratorCore context manager."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        orchestrator_error = RuntimeError("Failed to initialize orchestrator")

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            mock_reformat.return_value = None
            mock_load.return_value = {"test": ["data"]}

            # Make the context manager entry fail
            mock_orchestrator.return_value.__aenter__ = AsyncMock(side_effect=orchestrator_error)

            # Should propagate the orchestrator error
            with pytest.raises(RuntimeError, match="Failed to initialize orchestrator"):
                await async_crashlogs_scan()

    @pytest.mark.asyncio
    async def test_batch_processing_with_partial_failures(self, mock_base_dependencies):
        """Test handling of partial failures during batch processing."""
        mock_logs = [Path(f"log_{i}.txt") for i in range(10)]
        mock_base_dependencies["get_files"].return_value = mock_logs

        # Create mixed success/failure results
        mixed_results = []
        for i, log in enumerate(mock_logs):
            # Every 3rd log fails
            failed = (i % 3 == 0)
            mixed_results.append((log, f"report_{i}", failed, {"processed": True}))

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            mock_reformat.return_value = None
            mock_load.return_value = {f"log_{i}": [f"data_{i}"] for i in range(10)}

            # Configure orchestrator
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=mixed_results)
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Should complete without raising an error
            await async_crashlogs_scan()

            # Verify all logs were processed
            mock_orchestrator_instance.process_crash_logs_batch_async.assert_called_once_with(mock_logs)

            # Verify progress was updated for each log
            assert mock_base_dependencies["progress"].update.call_count == 10

            # Verify batch writing was called
            mock_orchestrator_instance.write_reports_batch.assert_called_once()

            # Check that failed logs were reported
            error_calls = [call for call in mock_base_dependencies["msg_info"].call_args_list
                          if "UNABLE TO PROPERLY SCAN" in str(call)]
            assert len(error_calls) == 1

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_cancellation(self, mock_base_dependencies):
        """Test proper resource cleanup when async operation is cancelled."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        cleanup_called = False

        async def cleanup_tracker(*args):
            """Track if cleanup was called."""
            nonlocal cleanup_called
            cleanup_called = True

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            mock_reformat.return_value = None
            mock_load.return_value = {"test": ["data"]}

            # Configure orchestrator with cleanup tracking
            mock_orchestrator_instance = AsyncMock()

            # Make processing take a long time so we can cancel it
            async def long_processing(*args):
                await asyncio.sleep(10)  # Long delay
                return [(Path("test.log"), "report", False, {})]

            mock_orchestrator_instance.process_crash_logs_batch_async = long_processing
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock(side_effect=cleanup_tracker)

            # Start the task and then cancel it
            task = asyncio.create_task(async_crashlogs_scan())
            await asyncio.sleep(0.01)  # Let it start
            task.cancel()

            # Should raise CancelledError
            with pytest.raises(asyncio.CancelledError):
                await task

            # Verify cleanup was called even though cancelled
            assert cleanup_called, "Orchestrator cleanup (__aexit__) was not called on cancellation"

    @pytest.mark.asyncio
    async def test_chained_error_propagation(self, mock_base_dependencies):
        """Test that errors are properly chained through async operations."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        original_error = ValueError("Original error from deep operation")

        # Chain: reformat -> load -> orchestrator -> process -> write
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load:

            mock_reformat.return_value = None

            # Make load_crash_logs_async raise the original error
            mock_load.side_effect = original_error

            # The original error should be propagated up
            with pytest.raises(ValueError, match="Original error from deep operation"):
                await async_crashlogs_scan()

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, mock_base_dependencies):
        """Test handling of asyncio.TimeoutError in various components."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        timeout_error = asyncio.TimeoutError("Operation timed out")

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            mock_reformat.return_value = None
            mock_load.return_value = {"test": ["data"]}

            # Make orchestrator processing timeout
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async.side_effect = timeout_error

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()

            # Timeout error should be propagated
            with pytest.raises(asyncio.TimeoutError, match="Operation timed out"):
                await async_crashlogs_scan()

    @pytest.mark.asyncio
    async def test_system_resource_errors(self, mock_base_dependencies):
        """Test handling of system resource-related errors."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        resource_errors = [
            MemoryError("Out of memory"),
            PermissionError("Access denied"),
            OSError("Disk full"),
            FileNotFoundError("Required file missing")
        ]

        for error in resource_errors:
            with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat:
                mock_reformat.side_effect = error

                # Each error should be propagated without modification
                with pytest.raises(type(error), match=str(error)):
                    await async_crashlogs_scan()

    @pytest.mark.asyncio
    async def test_nested_context_manager_errors(self, mock_base_dependencies):
        """Test error handling in nested context managers."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            mock_reformat.return_value = None
            mock_load.return_value = {"test": ["data"]}

            # Track cleanup calls
            enter_called = False
            exit_called = False

            async def track_enter():
                nonlocal enter_called
                enter_called = True
                raise RuntimeError("Failed during enter")

            async def track_exit(*args):
                nonlocal exit_called
                exit_called = True

            mock_orchestrator.return_value.__aenter__ = track_enter
            mock_orchestrator.return_value.__aexit__ = track_exit

            # Should get the enter error
            with pytest.raises(RuntimeError, match="Failed during enter"):
                await async_crashlogs_scan()

            # Enter was called but exit should not be called if enter fails
            assert enter_called
            assert not exit_called  # __aexit__ not called if __aenter__ fails

    @pytest.mark.asyncio
    async def test_partial_success_error_aggregation(self, mock_base_dependencies):
        """Test error reporting when some operations succeed and others fail."""
        mock_logs = [Path(f"log_{i}.txt") for i in range(5)]
        mock_base_dependencies["get_files"].return_value = mock_logs

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info") as mock_msg_info:

            mock_reformat.return_value = None
            mock_load.return_value = {f"log_{i}": [f"data_{i}"] for i in range(5)}

            # Mix of successful and failed results - test aggregation
            mixed_results = [
                (mock_logs[0], "report_0", False, {}),  # Success
                (mock_logs[1], "report_1", True, {}),   # Failed
                (mock_logs[2], "report_2", False, {}),  # Success
                (mock_logs[3], "report_3", True, {}),   # Failed
                (mock_logs[4], "report_4", True, {}),   # Failed
            ]

            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=mixed_results)
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Should complete without raising an exception
            await async_crashlogs_scan()

            # Verify error aggregation message was sent
            error_calls = [call for call in mock_msg_info.call_args_list
                          if "UNABLE TO PROPERLY SCAN" in str(call)]
            assert len(error_calls) == 1

            # Verify all failed logs are mentioned
            error_message = str(error_calls[0])
            assert "log_1.txt" in error_message
            assert "log_3.txt" in error_message
            assert "log_4.txt" in error_message
            # Successful logs should not be mentioned
            assert "log_0.txt" not in error_message
            assert "log_2.txt" not in error_message


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncIntegrationEdgeCasesUnit:
    """Unit tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_settings_handling(self):
        """Test handling of completely empty or None settings."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files", return_value=[]), \
             patch("ClassicLib.ScanLog.AsyncIntegration.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress_ctx, \
             patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.DB_PATHS", []):

            # Return all None values from settings
            mock_yaml_cache.batch_get_settings.return_value = [None, None, None, None]

            # Setup minimal mocks
            mock_progress = MagicMock()
            mock_progress.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.__exit__ = MagicMock()
            mock_progress.update = MagicMock()
            mock_progress_ctx.return_value = mock_progress

            mock_reformat.return_value = None
            mock_load.return_value = {}

            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=[])
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Should handle None values gracefully
            await async_crashlogs_scan()

            # Verify reformat was called with default empty tuple for None remove_list
            mock_reformat.assert_called_once_with([], ("",))

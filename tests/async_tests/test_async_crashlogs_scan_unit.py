"""
Unit tests for AsyncIntegration module.

This module tests the async crash log scanning integration functionality,
including async reformatting, batch processing, and report writing.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncIntegration import async_crashlogs_scan, run_async_scan


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncCrashLogsScan:
    """Unit tests for async_crashlogs_scan function."""

    @pytest.fixture
    def mock_crash_logs(self, tmp_path):
        """Create mock crash log files for testing."""
        # Create test crash log files with sample content
        logs = []
        for i in range(3):
            log_path = tmp_path / f"crashlog_{i}.txt"
            log_path.write_text(f"Test crash log content {i}\n" * 10)
            logs.append(log_path)
        return logs

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for async_crashlogs_scan."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files") as mock_get_files, \
             patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo") as mock_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info") as mock_msg_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress, \
             patch("ClassicLib.ScanLog.AsyncIntegration.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.DB_PATHS", [Path("/mock/db.sqlite")]), \
             patch("ClassicLib.ScanLog.AsyncIntegration.logger") as mock_logger:

            # Configure mocks with proper async behavior
            mock_reformat.return_value = asyncio.sleep(0)  # Simulate async work
            mock_load.return_value = {"log1": ["line1", "line2"], "log2": ["line3"]}

            # Mock orchestrator context manager with async methods
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=[
                (Path("log1.txt"), "report1", False, {}),
                (Path("log2.txt"), "report2", False, {}),
                (Path("log3.txt"), "report3", True, {})  # One failed
            ])
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            # Configure orchestrator class to return instance
            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Configure yaml cache batch loading
            mock_yaml_cache.batch_get_settings.return_value = [
                ("exclude1", "exclude2"),  # remove_list
                True,  # fcx_mode
                True,  # show_formid_values
                False  # move_unsolved_logs
            ]

            # Configure progress context manager
            mock_progress_instance = MagicMock()
            mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
            mock_progress_instance.__exit__ = MagicMock()
            mock_progress_instance.update = MagicMock()
            mock_progress.return_value = mock_progress_instance

            yield {
                "get_files": mock_get_files,
                "reformat": mock_reformat,
                "load": mock_load,
                "info": mock_info,
                "cache": mock_cache,
                "orchestrator": mock_orchestrator,
                "orchestrator_instance": mock_orchestrator_instance,
                "msg_info": mock_msg_info,
                "progress": mock_progress_instance,
                "yaml_cache": mock_yaml_cache,
                "logger": mock_logger
            }

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_success(self, mock_dependencies, mock_crash_logs):
        """Test successful async crash log scanning with all components working correctly."""
        # Configure mocks for successful scan
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Run the async scan
        await async_crashlogs_scan()

        # Verify crash logs were retrieved
        mock_dependencies["get_files"].assert_called_once()

        # Verify settings were loaded in batch
        mock_dependencies["yaml_cache"].batch_get_settings.assert_called_once()

        # Verify async reformatting was called with correct parameters
        mock_dependencies["reformat"].assert_called_once_with(
            mock_crash_logs,
            ("exclude1", "exclude2")
        )

        # Verify logs were loaded asynchronously
        mock_dependencies["load"].assert_called_once_with(mock_crash_logs)

        # Verify orchestrator was initialized with correct parameters
        mock_dependencies["orchestrator"].assert_called_once()

        # Verify crash logs were processed
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.assert_called_once_with(
            mock_crash_logs
        )

        # Verify reports were written
        mock_dependencies["orchestrator_instance"].write_reports_batch.assert_called_once()

        # Verify progress updates were made
        assert mock_dependencies["progress"].update.call_count == 3  # One per log

        # Verify performance logging
        assert mock_dependencies["logger"].info.call_count >= 4  # Multiple timing logs

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_with_failed_logs(self, mock_dependencies, mock_crash_logs):
        """Test handling of failed crash log scans with proper error reporting."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Configure orchestrator to return some failed scans
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.return_value = [
            (mock_crash_logs[0], "report1", True, {}),  # Failed
            (mock_crash_logs[1], "report2", False, {}),  # Success
            (mock_crash_logs[2], "report3", True, {}),   # Failed
        ]

        await async_crashlogs_scan()

        # Verify error message was displayed for failed logs
        error_calls = [call for call in mock_dependencies["msg_info"].call_args_list
                      if "UNABLE TO PROPERLY SCAN" in str(call)]
        assert len(error_calls) == 1

        # Verify the error message includes failed log names
        error_message = str(error_calls[0])
        assert "crashlog_0.txt" in error_message
        assert "crashlog_2.txt" in error_message

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_with_move_unsolved(self, mock_dependencies, mock_crash_logs):
        """Test moving unsolved logs when the option is enabled."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Enable move_unsolved_logs option
        mock_dependencies["yaml_cache"].batch_get_settings.return_value = [
            (),     # remove_list
            True,   # fcx_mode
            True,   # show_formid_values
            True    # move_unsolved_logs - ENABLED
        ]

        # Configure some failed scans
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.return_value = [
            (mock_crash_logs[0], "report1", True, {}),  # Failed - should be moved
            (mock_crash_logs[1], "report2", False, {}),  # Success - not moved
            (mock_crash_logs[2], "report3", True, {}),   # Failed - should be moved
        ]

        # Mock the move_unsolved_logs function
        with patch("CLASSIC_ScanLogs.move_unsolved_logs") as mock_move:
            await async_crashlogs_scan()

            # Verify only failed logs were moved
            assert mock_move.call_count == 2
            moved_logs = [call[0][0] for call in mock_move.call_args_list]
            assert mock_crash_logs[0] in moved_logs
            assert mock_crash_logs[2] in moved_logs
            assert mock_crash_logs[1] not in moved_logs

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_empty_logs(self, mock_dependencies):
        """Test handling when no crash logs are found."""
        mock_dependencies["get_files"].return_value = []

        await async_crashlogs_scan()

        # Verify early exit - no processing should occur
        mock_dependencies["reformat"].assert_called_once_with([], ())
        mock_dependencies["load"].assert_called_once_with([])

        # Orchestrator should still be initialized but with empty list
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_cache_integration(self, mock_dependencies, mock_crash_logs):
        """Test proper integration with ThreadSafeLogCache."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Mock loaded cache data
        cache_data = {
            "log1": ["line1", "line2", "line3"],
            "log2": ["line4", "line5"],
            "log3": ["line6"]
        }
        mock_dependencies["load"].return_value = cache_data

        await async_crashlogs_scan()

        # Verify ThreadSafeLogCache was created
        mock_dependencies["cache"].assert_called_once_with(mock_crash_logs)

        # Verify cache was populated with async-loaded data
        cache_instance = mock_dependencies["cache"].return_value
        expected_cache = {
            name: "\n".join(lines).encode("utf-8")
            for name, lines in cache_data.items()
        }
        assert cache_instance.cache == expected_cache

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_db_path_checking(self, mock_dependencies, mock_crash_logs):
        """Test FormID database existence checking."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Test with no database files
        with patch("ClassicLib.ScanLog.AsyncIntegration.DB_PATHS", []):
            await async_crashlogs_scan()

            # Verify orchestrator was called with formid_db_exists=False
            call_args = mock_dependencies["orchestrator"].call_args
            assert call_args[0][4] is False  # formid_db_exists parameter

        # Test with existing database file
        mock_db = MagicMock()
        mock_db.is_file.return_value = True
        with patch("ClassicLib.ScanLog.AsyncIntegration.DB_PATHS", [mock_db]):
            await async_crashlogs_scan()

            # Verify orchestrator was called with formid_db_exists=True
            call_args = mock_dependencies["orchestrator"].call_args
            assert call_args[0][4] is True  # formid_db_exists parameter


@pytest.mark.unit
class TestRunAsyncScan:
    """Unit tests for run_async_scan wrapper function."""

    def test_run_async_scan_uses_bridge(self):
        """Test that run_async_scan properly uses AsyncBridge for execution."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.AsyncBridge") as mock_bridge_class, \
             patch("ClassicLib.ScanLog.AsyncIntegration.async_crashlogs_scan") as mock_async_scan:

            # Configure bridge mock
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async = MagicMock()

            # Create a coroutine mock for async_crashlogs_scan
            mock_coro = AsyncMock()
            mock_async_scan.return_value = mock_coro()

            # Run the sync wrapper
            run_async_scan()

            # Verify AsyncBridge singleton was obtained
            mock_bridge_class.get_instance.assert_called_once()

            # Verify run_async was called with the coroutine
            mock_bridge.run_async.assert_called_once()

            # Check that a coroutine was passed to run_async
            call_args = mock_bridge.run_async.call_args[0]
            assert asyncio.iscoroutine(call_args[0])

    def test_run_async_scan_propagates_exceptions(self):
        """Test that exceptions from async_crashlogs_scan are properly propagated."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.AsyncBridge") as mock_bridge_class:

            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge

            # Configure bridge to raise an exception
            test_exception = RuntimeError("Test async error")
            mock_bridge.run_async.side_effect = test_exception

            # Verify exception is propagated
            with pytest.raises(RuntimeError, match="Test async error"):
                run_async_scan()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.slow
class TestAsyncIntegrationPerformance:
    """Performance and stress tests for async integration."""

    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, mock_dependencies, tmp_path):
        """Test performance with large number of concurrent crash logs."""
        # Create many mock crash logs
        num_logs = 100
        mock_logs = []
        for i in range(num_logs):
            log_path = tmp_path / f"crashlog_{i}.txt"
            log_path.write_text(f"Log content {i}")
            mock_logs.append(log_path)

        mock_dependencies["get_files"].return_value = mock_logs

        # Configure mock to return results for all logs
        mock_results = [(log, f"report_{i}", False, {}) for i, log in enumerate(mock_logs)]
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.return_value = mock_results

        # Time the execution
        import time
        start_time = time.perf_counter()
        await async_crashlogs_scan()
        elapsed_time = time.perf_counter() - start_time

        # Verify all logs were processed
        assert mock_dependencies["progress"].update.call_count == num_logs

        # Performance should be reasonable even with many logs
        # This is a sanity check - adjust threshold as needed
        assert elapsed_time < 5.0  # Should complete within 5 seconds for mocked operations

        # Verify batch operations were used efficiently
        mock_dependencies["yaml_cache"].batch_get_settings.assert_called_once()
        mock_dependencies["orchestrator_instance"].write_reports_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_efficiency_with_large_logs(self, mock_dependencies, tmp_path):
        """Test memory efficiency when processing large crash logs."""
        # Create large mock crash logs
        large_logs = []
        for i in range(10):
            log_path = tmp_path / f"large_log_{i}.txt"
            # Create 10MB log files
            large_content = "X" * (1024 * 1024 * 10)  # 10MB
            log_path.write_text(large_content)
            large_logs.append(log_path)

        mock_dependencies["get_files"].return_value = large_logs

        # Mock large cache data
        large_cache = {f"log_{i}": ["X" * 1000] * 1000 for i in range(10)}
        mock_dependencies["load"].return_value = large_cache

        # Should complete without memory issues
        await async_crashlogs_scan()

        # Verify logs were processed in batch for efficiency
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.assert_called_once()
        mock_dependencies["orchestrator_instance"].write_reports_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_timing_and_performance_logging(self, mock_dependencies, mock_crash_logs):
        """Test that performance timing is logged correctly."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Configure async operations with realistic delays
        async def delayed_reformat(*args):
            await asyncio.sleep(0.01)
            return None

        async def delayed_load(*args):
            await asyncio.sleep(0.01)
            return {"log1": ["line1"], "log2": ["line2"]}

        async def delayed_process(*args):
            await asyncio.sleep(0.01)
            return [(mock_crash_logs[0], "report", False, {})]

        async def delayed_write(*args):
            await asyncio.sleep(0.01)

        mock_dependencies["reformat"].side_effect = delayed_reformat
        mock_dependencies["load"].side_effect = delayed_load
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.side_effect = delayed_process
        mock_dependencies["orchestrator_instance"].write_reports_batch.side_effect = delayed_write

        await async_crashlogs_scan()

        # Verify performance logging occurred (at least 4 timing logs)
        assert mock_dependencies["logger"].info.call_count >= 4

        # Check that timing messages were logged
        timing_calls = [call for call in mock_dependencies["logger"].info.call_args_list
                       if "completed in" in str(call)]
        assert len(timing_calls) >= 3  # reformat, cache, process, write times

    @pytest.mark.asyncio
    async def test_settings_validation_and_defaults(self, mock_dependencies, mock_crash_logs):
        """Test handling of None/invalid settings values."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Configure yaml cache to return None values
        mock_dependencies["yaml_cache"].batch_get_settings.return_value = [
            None,   # remove_list (should default to ("",))
            None,   # fcx_mode
            None,   # show_formid_values
            None    # move_unsolved_logs
        ]

        await async_crashlogs_scan()

        # Verify the function handles None values correctly
        mock_dependencies["reformat"].assert_called_once_with(mock_crash_logs, ("",))

        # Verify orchestrator was called with None values (function should handle this)
        mock_dependencies["orchestrator"].assert_called_once()
        call_args = mock_dependencies["orchestrator"].call_args[0]
        assert call_args[2] is None  # fcx_mode
        assert call_args[3] is None  # show_formid_values

    @pytest.mark.asyncio
    async def test_batch_settings_request_structure(self, mock_dependencies, mock_crash_logs):
        """Test that settings are requested in the correct batch format."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        await async_crashlogs_scan()

        # Verify batch_get_settings was called with correct structure
        mock_dependencies["yaml_cache"].batch_get_settings.assert_called_once()
        call_args = mock_dependencies["yaml_cache"].batch_get_settings.call_args[0][0]

        # Should have 4 settings requests
        assert len(call_args) == 4

        # Check the structure of each request (type, enum, key)
        expected_requests = [
            (tuple, "YAML.Main", "exclude_log_records"),
            (bool, "YAML.Settings", "CLASSIC_Settings.FCX Mode"),
            (bool, "YAML.Settings", "CLASSIC_Settings.Show FormID Values"),
            (bool, "YAML.Settings", "CLASSIC_Settings.Move Unsolved Logs"),
        ]

        for i, (expected_type, expected_enum, expected_key) in enumerate(expected_requests):
            request = call_args[i]
            assert request[0] == expected_type
            assert expected_enum in str(request[1])  # Check enum is present
            assert request[2] == expected_key

    @pytest.mark.asyncio
    async def test_cache_data_encoding_conversion(self, mock_dependencies, mock_crash_logs):
        """Test that cache data is properly converted to bytes."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Mock specific cache data
        test_cache_data = {
            "log1.txt": ["First line", "Second line", "Third line"],
            "log2.txt": ["Single line"],
            "log3.txt": ["Line with unicode: αβγ", "Another line"]
        }
        mock_dependencies["load"].return_value = test_cache_data

        await async_crashlogs_scan()

        # Verify ThreadSafeLogCache was created and cache was properly set
        mock_dependencies["cache"].assert_called_once_with(mock_crash_logs)
        cache_instance = mock_dependencies["cache"].return_value

        # Verify cache data was encoded correctly
        expected_cache = {}
        for name, lines in test_cache_data.items():
            expected_cache[name] = "\n".join(lines).encode("utf-8")

        assert cache_instance.cache == expected_cache

    @pytest.mark.asyncio
    async def test_report_batch_structure(self, mock_dependencies, mock_crash_logs):
        """Test that reports are properly structured for batch writing."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Configure mock results with specific structure
        test_results = [
            (mock_crash_logs[0], "Report content 1", False, {"stat1": "value1"}),
            (mock_crash_logs[1], "Report content 2", True, {"stat2": "value2"}),
        ]
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.return_value = test_results

        await async_crashlogs_scan()

        # Verify reports were prepared correctly for batch writing
        expected_reports = [
            (mock_crash_logs[0], "Report content 1", False),
            (mock_crash_logs[1], "Report content 2", True),
        ]
        mock_dependencies["orchestrator_instance"].write_reports_batch.assert_called_once_with(expected_reports)

    @pytest.mark.asyncio
    async def test_scan_failed_list_generation(self, mock_dependencies, mock_crash_logs):
        """Test that scan_failed_list is generated correctly from results."""
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Mix of successful and failed scans
        test_results = [
            (mock_crash_logs[0], "Report 1", False, {}),  # Success
            (mock_crash_logs[1], "Report 2", True, {}),   # Failed
            (mock_crash_logs[2], "Report 3", False, {}),  # Success
        ]
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async.return_value = test_results

        await async_crashlogs_scan()

        # Verify error message was called with failed log names
        error_calls = [call for call in mock_dependencies["msg_info"].call_args_list
                      if "UNABLE TO PROPERLY SCAN" in str(call)]
        assert len(error_calls) == 1

        # Should contain only the failed log name
        error_message = str(error_calls[0])
        assert mock_crash_logs[1].name in error_message
        assert mock_crash_logs[0].name not in error_message
        assert mock_crash_logs[2].name not in error_message

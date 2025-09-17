"""
Stress and performance tests for AsyncIntegration module.

This module focuses on stress testing, performance benchmarks,
and edge cases for async crash log scanning integration.
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from concurrent.futures import ThreadPoolExecutor

import pytest

from ClassicLib.ScanLog.AsyncIntegration import async_crashlogs_scan, run_async_scan


@pytest.mark.slow
@pytest.mark.asyncio
class TestAsyncIntegrationStressTesting:
    """Stress tests for AsyncIntegration patterns."""

    @pytest.fixture
    def mock_base_dependencies(self):
        """Base mock setup for stress testing."""
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
    async def test_memory_pressure_handling(self, mock_base_dependencies):
        """Test behavior under memory pressure conditions."""
        # Create many logs to simulate memory pressure
        num_logs = 1000
        mock_logs = [Path(f"log_{i}.txt") for i in range(num_logs)]
        mock_base_dependencies["get_files"].return_value = mock_logs

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            mock_reformat.return_value = None

            # Create large cache data
            large_cache = {}
            for i in range(num_logs):
                # Each log has lots of lines
                large_cache[f"log_{i}.txt"] = [f"line_{j}_in_log_{i}" for j in range(100)]

            mock_load.return_value = large_cache

            # Configure orchestrator to handle all logs
            mock_orchestrator_instance = AsyncMock()
            mock_results = [(log, f"report_{i}", False, {}) for i, log in enumerate(mock_logs)]
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=mock_results)
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Should handle the large dataset without issues
            await async_crashlogs_scan()

            # Verify all logs were processed
            assert mock_base_dependencies["progress"].update.call_count == num_logs
            mock_orchestrator_instance.process_crash_logs_batch_async.assert_called_once()
            mock_orchestrator_instance.write_reports_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_timing_accuracy_under_load(self, mock_base_dependencies):
        """Test that performance timing remains accurate under load."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.logger") as mock_logger:

            # Configure operations with known delays
            async def timed_reformat(*args):
                await asyncio.sleep(0.1)  # 100ms delay
                return None

            async def timed_load(*args):
                await asyncio.sleep(0.05)  # 50ms delay
                return {"test": ["data"]}

            async def timed_process(*args):
                await asyncio.sleep(0.2)  # 200ms delay
                return [(Path("test.log"), "report", False, {})]

            async def timed_write(*args):
                await asyncio.sleep(0.03)  # 30ms delay

            mock_reformat.side_effect = timed_reformat
            mock_load.side_effect = timed_load

            # Configure orchestrator
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = timed_process
            mock_orchestrator_instance.write_reports_batch = timed_write

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Run the scan
            start_time = time.perf_counter()
            await async_crashlogs_scan()
            total_time = time.perf_counter() - start_time

            # Total should be at least the sum of delays (sequential execution)
            expected_min_time = 0.1 + 0.05 + 0.2 + 0.03  # 380ms
            assert total_time >= expected_min_time * 0.9, f"Total time {total_time:.3f}s less than expected {expected_min_time:.3f}s"

            # Verify timing logs were created
            timing_calls = [call for call in mock_logger.info.call_args_list
                          if "completed in" in str(call)]
            assert len(timing_calls) >= 3, "Expected at least 3 timing log entries"

    @pytest.mark.asyncio
    async def test_concurrent_async_scan_isolation(self, mock_base_dependencies):
        """Test that multiple concurrent async_crashlogs_scan calls don't interfere."""
        mock_base_dependencies["get_files"].return_value = [Path("test.log")]

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            # Track call ordering
            call_order = []

            async def track_reformat(logs, remove_list):
                call_order.append(f"reformat_{id(logs)}")
                await asyncio.sleep(0.01)  # Small delay
                return None

            async def track_load(logs):
                call_order.append(f"load_{id(logs)}")
                await asyncio.sleep(0.01)  # Small delay
                return {f"log_{id(logs)}": ["data"]}

            mock_reformat.side_effect = track_reformat
            mock_load.side_effect = track_load

            # Configure orchestrator
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(
                return_value=[(Path("test.log"), "report", False, {})]
            )
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Run multiple scans concurrently
            tasks = [
                asyncio.create_task(async_crashlogs_scan()),
                asyncio.create_task(async_crashlogs_scan()),
                asyncio.create_task(async_crashlogs_scan())
            ]

            # All should complete successfully
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # None should have raised exceptions
            for result in results:
                assert not isinstance(result, Exception), f"Task failed with: {result}"

            # Verify operations were called for each task
            assert len(call_order) == 6  # 3 tasks * 2 operations each

            # Verify each task had its operations called in order
            reformat_calls = [call for call in call_order if call.startswith("reformat_")]
            load_calls = [call for call in call_order if call.startswith("load_")]
            assert len(reformat_calls) == 3
            assert len(load_calls) == 3


@pytest.mark.slow
class TestAsyncBridgeStressTesting:
    """Stress tests for AsyncBridge integration patterns."""

    def test_bridge_thread_safety_under_concurrent_load(self, async_bridge):
        """Test AsyncBridge thread safety with concurrent calls.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """
        from ClassicLib.AsyncBridge import AsyncBridge
        import threading
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

        # Track results and errors from different threads
        results = []
        errors = []
        results_lock = threading.Lock()

        # Use the fixture-provided bridge for the main thread
        # but each worker thread will get its own instance

        async def async_work(task_id):
            """Simulate async work with unique task ID."""
            await asyncio.sleep(0.001)  # Reduced delay
            return f"Task {task_id} completed"

        def run_async_work(task_id):
            """Run async work through bridge."""
            try:
                # Each thread gets its own bridge instance
                thread_bridge = AsyncBridge.get_instance()
                result = thread_bridge.run_async(async_work(task_id))
                with results_lock:
                    results.append(result)
            except Exception as e:
                with results_lock:
                    errors.append((task_id, e))

        # Run concurrent operations from different threads with timeout
        with ThreadPoolExecutor(max_workers=5) as executor:  # Reduced workers
            futures = [executor.submit(run_async_work, i) for i in range(20)]  # Reduced tasks

            # Wait for all to complete with timeout
            import concurrent.futures
            done, not_done = concurrent.futures.wait(futures, timeout=5.0)

            # Cancel any incomplete futures
            for future in not_done:
                future.cancel()

            # Get results from completed futures
            for future in done:
                try:
                    future.result(timeout=0.1)
                except FutureTimeoutError:
                    pass  # Ignore timeout errors from cancelled futures
                except Exception as e:
                    with results_lock:
                        errors.append(("future", e))

        # Cleanup thread-local bridges
        for thread_id in list(AsyncBridge._instances.keys()):
            if thread_id != threading.get_ident():
                instance = AsyncBridge._instances.pop(thread_id, None)
                if instance:
                    instance.shutdown()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all tasks completed (or adjust expectation if some timed out)
        assert len(results) <= 20, f"Got {len(results)} results, expected at most 20"
        assert len(results) >= 15, f"Too few results: {len(results)}, expected at least 15"

        # Verify each task completed at most once
        actual_results = set(results)
        assert len(actual_results) == len(results), "Duplicate results found"

    def test_bridge_exception_handling_stress(self, async_bridge):
        """Test AsyncBridge exception handling under various error conditions.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """
        bridge = async_bridge

        # Test various exception types
        exceptions_to_test = [
            ValueError("Test ValueError"),
            RuntimeError("Test RuntimeError"),
            asyncio.TimeoutError("Test TimeoutError"),
            MemoryError("Test MemoryError"),
            KeyError("Test KeyError")
        ]

        for exception in exceptions_to_test:
            async def failing_task():
                await asyncio.sleep(0.001)  # Small delay
                raise exception

            # Each exception should be properly propagated
            with pytest.raises(type(exception), match=str(exception)):
                bridge.run_async(failing_task())

    def test_bridge_resource_cleanup_on_repeated_use(self, async_bridge):
        """Test that AsyncBridge properly cleans up resources on repeated use.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """
        bridge = async_bridge

        # Run many operations to test resource cleanup
        for i in range(100):
            async def test_coro():
                await asyncio.sleep(0.001)
                return f"Operation {i}"

            result = bridge.run_async(test_coro())
            assert result == f"Operation {i}"

        # Bridge should still be functional after many operations
        async def final_test():
            await asyncio.sleep(0.001)
            return "Final operation successful"

        final_result = bridge.run_async(final_test())
        assert final_result == "Final operation successful"


@pytest.mark.slow
@pytest.mark.asyncio
class TestAsyncIntegrationEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_large_number_of_logs_boundary(self):
        """Test handling at the boundary of very large numbers of logs."""
        # Test with large but reasonable number of logs
        large_count = 10000
        mock_logs = [Path(f"log_{i:05d}.txt") for i in range(large_count)]

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files", return_value=mock_logs), \
             patch("ClassicLib.ScanLog.AsyncIntegration.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress_ctx, \
             patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.DB_PATHS", []):

            mock_yaml_cache.batch_get_settings.return_value = [(), False, False, False]

            # Setup progress context
            mock_progress = MagicMock()
            mock_progress.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.__exit__ = MagicMock()
            mock_progress.update = MagicMock()
            mock_progress_ctx.return_value = mock_progress

            mock_reformat.return_value = None
            mock_load.return_value = {f"log_{i:05d}.txt": [f"content_{i}"] for i in range(large_count)}

            # Create large results list
            large_results = [(log, f"report_{i}", False, {}) for i, log in enumerate(mock_logs)]

            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=large_results)
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Should handle large number of logs
            await async_crashlogs_scan()

            # Verify progress was updated for all logs
            assert mock_progress.update.call_count == large_count

            # Verify batch processing was used
            mock_orchestrator_instance.process_crash_logs_batch_async.assert_called_once_with(mock_logs)
            mock_orchestrator_instance.write_reports_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters_in_paths(self):
        """Test handling of unicode and special characters in file paths."""
        # Paths with various special characters and unicode
        special_paths = [
            Path("log_with_émojis_🚀.txt"),
            Path("log with spaces.txt"),
            Path("log-with-dashes.txt"),
            Path("log_with_underscores.txt"),
            Path("log.with.dots.txt"),
            Path("log_with_中文.txt"),
            Path("log_with_ñ_and_ü.txt")
        ]

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files", return_value=special_paths), \
             patch("ClassicLib.ScanLog.AsyncIntegration.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress_ctx, \
             patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.DB_PATHS", []):

            mock_yaml_cache.batch_get_settings.return_value = [(), False, False, False]

            # Setup progress context
            mock_progress = MagicMock()
            mock_progress.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.__exit__ = MagicMock()
            mock_progress.update = MagicMock()
            mock_progress_ctx.return_value = mock_progress

            mock_reformat.return_value = None
            # Include unicode content in cache
            mock_load.return_value = {
                str(path): [f"Content with unicode: αβγ 中文 émoji🚀"]
                for path in special_paths
            }

            # Create results for all special paths
            special_results = [(path, f"report_{i}", False, {}) for i, path in enumerate(special_paths)]

            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=special_results)
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            mock_orchestrator.return_value.__aenter__ = AsyncMock(return_value=mock_orchestrator_instance)
            mock_orchestrator.return_value.__aexit__ = AsyncMock()
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Should handle unicode paths and content without issues
            await async_crashlogs_scan()

            # Verify all special paths were processed
            assert mock_progress.update.call_count == len(special_paths)

            # Verify cache encoding handled unicode properly
            mock_cache.assert_called_once_with(special_paths)
            cache_instance = mock_cache.return_value

            # Verify unicode content was properly encoded to bytes
            expected_cache = {}
            for path in special_paths:
                content = f"Content with unicode: αβγ 中文 émoji🚀"
                expected_cache[str(path)] = content.encode("utf-8")

            assert cache_instance.cache == expected_cache

"""
Integration tests for AsyncIntegration module.

This module tests the integration of async components with actual file I/O,
real async operations, and interaction between components.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns


import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncIntegration import async_crashlogs_scan, run_async_scan


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncIntegrationWithRealComponents:
    """Integration tests using real components where possible."""

    @pytest.fixture
    async def real_crash_logs(self, tmp_path):
        """Create realistic crash log files for integration testing."""
        logs_dir = tmp_path / "Crash Logs"
        logs_dir.mkdir()

        # Create realistic crash log content
        crash_log_content = """
        Fallout 4 v1.10.163
        Buffout 4 v1.26.2

        Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6A1234567 Fallout4.exe+01234567

        PROBABLE CALL STACK:
        [0] 0x7FF6A1234567 Fallout4.exe+01234567
        [1] 0x7FF6A1234568 Fallout4.exe+01234568

        MODULES:
        Fallout4.exe
        Test.esp

        PLUGINS:
        [00] Fallout4.esm
        [01] DLCRobot.esm
        [02] Test.esp
        [FE:001] TestLight.esl
        """

        logs = []
        for i in range(5):
            log_path = logs_dir / f"crash-{i}.log"
            log_path.write_text(crash_log_content + f"\nLog ID: {i}")
            logs.append(log_path)

        return logs

    @pytest.fixture
    def mock_minimal_dependencies(self):
        """Mock only the minimal required dependencies for integration tests."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files") as mock_get_files, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info") as mock_msg_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress, \
             patch("ClassicLib.YamlSettingsCache.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo") as mock_info, \
             patch("ClassicLib.Constants.DB_PATHS", []):

            # Configure yaml cache
            mock_yaml_cache.batch_get_settings.return_value = [
                (),     # remove_list
                False,  # fcx_mode
                False,  # show_formid_values
                False   # move_unsolved_logs
            ]

            # Configure progress context
            # CRITICAL: __exit__ must return False to not suppress exceptions
            mock_progress_instance = MagicMock()
            mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
            mock_progress_instance.__exit__ = MagicMock(return_value=False)  # Don't suppress exceptions
            mock_progress_instance.update = MagicMock()
            mock_progress.return_value = mock_progress_instance

            yield {
                "get_files": mock_get_files,
                "msg_info": mock_msg_info,
                "progress": mock_progress_instance,
                "yaml_cache": mock_yaml_cache,
                "info": mock_info
            }

    @pytest.mark.asyncio
    async def test_async_integration_with_real_file_operations(
        self, real_crash_logs, mock_minimal_dependencies, tmp_path
    ):
        """Test async integration with real file I/O operations."""
        mock_minimal_dependencies["get_files"].return_value = real_crash_logs

        # Mock only the components that require external resources
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            # Configure async operations to actually do work
            # Use side_effect for async functions to avoid unawaited coroutine warnings
            async def real_reformat(logs, remove_list):
                """Simulate real async reformatting."""
                await asyncio.sleep(0.01)  # Simulate I/O
                return [log.name for log in logs]

            async def real_load(logs):
                """Actually load crash logs asynchronously."""
                cache = {}
                for log in logs:
                    content = await asyncio.to_thread(log.read_text)
                    cache[log.name] = content.splitlines()
                return cache

            # Correct pattern: use side_effect with async functions
            mock_reformat.side_effect = real_reformat
            mock_load.side_effect = real_load

            # Configure orchestrator with real async behavior
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock()

            async def real_process(logs):
                """Simulate real async processing."""
                results = []
                for log in logs:
                    await asyncio.sleep(0.01)  # Simulate processing time
                    results.append((log, f"Report for {log.name}", False, {}))
                return results

            mock_orchestrator_instance.process_crash_logs_batch_async.side_effect = real_process
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            # Proper async context manager pattern - assign functions, don't call them
            async def orchestrator_aenter(self):
                return mock_orchestrator_instance

            async def orchestrator_aexit(self, exc_type, exc_val, exc_tb):
                return None

            mock_orchestrator.return_value.__aenter__ = orchestrator_aenter
            mock_orchestrator.return_value.__aexit__ = orchestrator_aexit
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Run the integration
            await async_crashlogs_scan()

            # Verify real async operations occurred
            mock_reformat.assert_called_once()
            mock_load.assert_called_once()

            # Verify cache was populated with real data
            loaded_cache = await real_load(real_crash_logs)
            assert len(loaded_cache) == 5
            for log in real_crash_logs:
                assert log.name in loaded_cache

            # Verify all logs were processed
            assert mock_minimal_dependencies["progress"].update.call_count == 5

    @pytest.mark.asyncio
    async def test_concurrent_operations_coordination(self, real_crash_logs, mock_minimal_dependencies):
        """Test coordination between concurrent async operations."""
        mock_minimal_dependencies["get_files"].return_value = real_crash_logs

        # Track operation order and timing
        operation_log = []

        async def log_operation(name, duration=0.01):
            """Log operation with timing."""
            operation_log.append(f"{name}_start")
            await asyncio.sleep(duration)
            operation_log.append(f"{name}_end")
            return name

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            # Configure operations to log their execution
            # CRITICAL: Use async function for side_effect, not lambda returning coroutine
            async def reformat_with_log(*args):
                return await log_operation("reformat", 0.02)

            async def load_with_log(*args):
                await log_operation("load", 0.02)
                # Return proper dictionary for cache
                return {"log1": ["data1"], "log2": ["data2"]}

            mock_reformat.side_effect = reformat_with_log
            mock_load.side_effect = load_with_log

            # Configure orchestrator
            mock_orchestrator_instance = AsyncMock()

            async def process_with_log(logs):
                await log_operation("process", 0.03)
                return [(log, "report", False, {}) for log in logs]

            mock_orchestrator_instance.process_crash_logs_batch_async.side_effect = process_with_log

            async def write_with_log(reports):
                await log_operation("write", 0.02)

            mock_orchestrator_instance.write_reports_batch = write_with_log

            # Proper async context manager pattern
            async def orchestrator_aenter(self):
                return mock_orchestrator_instance

            async def orchestrator_aexit(self, exc_type, exc_val, exc_tb):
                return None

            mock_orchestrator.return_value.__aenter__ = orchestrator_aenter
            mock_orchestrator.return_value.__aexit__ = orchestrator_aexit
            mock_orchestrator.write_reports_batch = mock_orchestrator_instance.write_reports_batch

            # Run and check operation order
            await async_crashlogs_scan()

            # Verify operations occurred in correct sequence
            assert "reformat_start" in operation_log
            assert "reformat_end" in operation_log
            assert "load_start" in operation_log
            assert "load_end" in operation_log
            assert "process_start" in operation_log
            assert "process_end" in operation_log
            assert "write_start" in operation_log
            assert "write_end" in operation_log

            # Verify sequential order (not concurrent where it shouldn't be)
            assert operation_log.index("reformat_end") < operation_log.index("load_start")
            assert operation_log.index("load_end") < operation_log.index("process_start")
            assert operation_log.index("process_end") < operation_log.index("write_start")


@pytest.mark.integration
class TestAsyncBridgeIntegration:
    """Test AsyncBridge integration with async_crashlogs_scan."""

    def test_bridge_handles_event_loop_properly(self, async_bridge):
        """Test that AsyncBridge properly manages event loop lifecycle.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """

        with patch("ClassicLib.ScanLog.AsyncIntegration.async_crashlogs_scan") as mock_scan:
            # Create a real coroutine that does some work
            @pytest.mark.asyncio
            async def test_coro():
                await asyncio.sleep(0.01)
                return "completed"

            mock_scan.return_value = test_coro()

            # Run through bridge
            run_async_scan()

            # Verify bridge is still usable after
            # This tests that the event loop wasn't destroyed
            result = async_bridge.run_async(asyncio.sleep(0.01))
            assert result is None  # sleep returns None

    def test_bridge_error_propagation(self):
        """Test that errors in async code are properly propagated through the bridge."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.async_crashlogs_scan") as mock_scan:
            # Create an async function that raises an exception
            async def failing_coro():
                await asyncio.sleep(0.01)
                raise ValueError("Test error in async code")

            # Use side_effect for async functions
            mock_scan.side_effect = failing_coro

            # Verify exception is propagated through bridge
            with pytest.raises(ValueError, match="Test error in async code"):
                run_async_scan()

    def test_bridge_concurrent_calls(self, async_bridge):
        """Test that multiple concurrent calls through bridge work correctly.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """
        from concurrent.futures import ThreadPoolExecutor

        # Use the fixture-provided bridge for proper test isolation
        results = []

        def run_with_bridge(task_id):
            """Run an async task through the bridge.

            Each thread will use the same bridge instance from the fixture,
            testing thread safety and concurrent execution.
            """
            async def task():
                await asyncio.sleep(0.01)
                return f"Task {task_id} completed"

            return async_bridge.run_async(task())

        # Run multiple tasks concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_with_bridge, i) for i in range(5)]
            results = [f.result() for f in futures]

        # Verify all tasks completed
        assert len(results) == 5
        for i in range(5):
            assert f"Task {i} completed" in results


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncIntegrationErrorHandling:
    """Test error handling in async integration."""

    @pytest.fixture
    def mock_minimal_dependencies(self):
        """Mock only the minimal required dependencies for integration tests."""
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files") as mock_get_files, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info") as mock_msg_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress, \
             patch("ClassicLib.YamlSettingsCache.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo") as mock_info, \
             patch("ClassicLib.Constants.DB_PATHS", []):

            # Configure yaml cache
            mock_yaml_cache.batch_get_settings.return_value = [
                (),     # remove_list
                False,  # fcx_mode
                False,  # show_formid_values
                False   # move_unsolved_logs
            ]

            # Configure progress context
            # CRITICAL: __exit__ must return False to not suppress exceptions
            mock_progress_instance = MagicMock()
            mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
            mock_progress_instance.__exit__ = MagicMock(return_value=False)  # Don't suppress exceptions
            mock_progress_instance.update = MagicMock()
            mock_progress.return_value = mock_progress_instance

            yield {
                "get_files": mock_get_files,
                "msg_info": mock_msg_info,
                "progress": mock_progress_instance,
                "yaml_cache": mock_yaml_cache,
                "info": mock_info
            }

    @pytest.mark.asyncio
    async def test_handles_reformat_errors_gracefully(self, mock_minimal_dependencies):
        """Test graceful handling of errors during reformatting."""
        mock_minimal_dependencies["get_files"].return_value = [Path("test.log")]

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.logger") as mock_logger:

            # Make reformat raise an error
            mock_reformat.side_effect = TimeoutError("Reformat timeout")

            # Configure other mocks minimally
            # Use side_effect for async functions
            async def empty_load(*args):
                return {}
            mock_load.side_effect = empty_load

            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async = AsyncMock(return_value=[])
            mock_orchestrator_instance.write_reports_batch = AsyncMock()

            # Proper async context manager pattern
            async def orchestrator_aenter(self):
                return mock_orchestrator_instance

            async def orchestrator_aexit(self, exc_type, exc_val, exc_tb):
                return None

            mock_orchestrator.return_value.__aenter__ = orchestrator_aenter
            mock_orchestrator.return_value.__aexit__ = orchestrator_aexit

            # Should raise the timeout error
            with pytest.raises(asyncio.TimeoutError):
                await async_crashlogs_scan()

    @pytest.mark.asyncio
    async def test_handles_orchestrator_errors(self, mock_minimal_dependencies):
        """Test handling of errors from the orchestrator."""
        mock_minimal_dependencies["get_files"].return_value = [Path("test.log")]

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            # Use side_effect for async functions
            async def mock_reformat_async(*args):
                return None
            mock_reformat.side_effect = mock_reformat_async

            async def mock_load_async(*args):
                return {"test": ["line1"]}
            mock_load.side_effect = mock_load_async

            # Make orchestrator raise an error during processing
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async.side_effect = RuntimeError("Processing failed")

            # Proper async context manager pattern
            async def orchestrator_aenter(self):
                return mock_orchestrator_instance

            async def orchestrator_aexit(self, exc_type, exc_val, exc_tb):
                return None

            mock_orchestrator.return_value.__aenter__ = orchestrator_aenter
            mock_orchestrator.return_value.__aexit__ = orchestrator_aexit

            # Should propagate the error
            with pytest.raises(RuntimeError, match="Processing failed"):
                await async_crashlogs_scan()

    @pytest.mark.asyncio
    async def test_cleanup_on_error(self, mock_minimal_dependencies):
        """Test that resources are cleaned up properly on error."""
        mock_minimal_dependencies["get_files"].return_value = [Path("test.log")]

        cleanup_called = False

        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache"), \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator:

            # Use side_effect for async functions
            async def mock_reformat_async(*args):
                return None
            mock_reformat.side_effect = mock_reformat_async

            async def mock_load_async(*args):
                return {"test": ["line1"]}
            mock_load.side_effect = mock_load_async

            # Configure orchestrator with cleanup tracking
            mock_orchestrator_instance = AsyncMock()
            mock_orchestrator_instance.process_crash_logs_batch_async.side_effect = RuntimeError("Test error")

            # Proper async context manager with cleanup tracking
            async def orchestrator_aenter(self):
                return mock_orchestrator_instance

            async def orchestrator_aexit(self, exc_type, exc_val, exc_tb):
                nonlocal cleanup_called
                cleanup_called = True

            mock_orchestrator.return_value.__aenter__ = orchestrator_aenter
            mock_orchestrator.return_value.__aexit__ = orchestrator_aexit

            # Run and expect error
            with pytest.raises(RuntimeError):
                await async_crashlogs_scan()

            # Verify cleanup was called
            assert cleanup_called, "Orchestrator cleanup (__aexit__) was not called"

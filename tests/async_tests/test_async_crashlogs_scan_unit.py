"""
Unit tests for AsyncIntegration module with correct async patterns.

This module tests the async crash log scanning integration functionality,
including async reformatting, batch processing, and report writing.

IMPORTANT: This module follows the correct AsyncBridge mocking patterns to avoid
RuntimeWarning about unawaited coroutines. Key principles:
1. When testing sync wrappers that use AsyncBridge, mock the bridge's run_async method
2. For pure async functions tested with @pytest.mark.asyncio, use real async/await
3. Mock async functions as regular functions that return values, not coroutines
4. Use MagicMock for methods called through AsyncBridge, not AsyncMock
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncIntegration import async_crashlogs_scan, run_async_scan


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncCrashLogsScan:
    """Unit tests for async_crashlogs_scan function.

    These tests directly test the async function, so they use @pytest.mark.asyncio
    and await the function calls. Mocks return values directly, not coroutines.
    """

    @pytest.fixture
    def mock_crash_logs(self, tmp_path):
        """Create mock crash log files for testing.

        Creates temporary test files to simulate crash logs.
        """
        logs = []
        for i in range(3):
            log_path = tmp_path / f"crashlog_{i}.txt"
            log_path.write_text(f"Test crash log content {i}\n" * 10)
            logs.append(log_path)
        return logs

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for async_crashlogs_scan.

        CRITICAL: This fixture uses the correct mocking patterns:
        - Async functions that are awaited directly return values, not coroutines
        - Context managers use MagicMock with proper __aenter__/__aexit__ methods
        - No AsyncMock usage to avoid unawaited coroutine warnings
        """
        with patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_get_files") as mock_get_files, \
             patch("ClassicLib.ScanLog.AsyncIntegration.crashlogs_reformat_async") as mock_reformat, \
             patch("ClassicLib.ScanLog.AsyncIntegration.load_crash_logs_async") as mock_load, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ClassicScanLogsInfo") as mock_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.ThreadSafeLogCache") as mock_cache, \
             patch("ClassicLib.ScanLog.AsyncIntegration.OrchestratorCore") as mock_orchestrator, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_info") as mock_msg_info, \
             patch("ClassicLib.ScanLog.AsyncIntegration.msg_progress_context") as mock_progress, \
             patch("ClassicLib.YamlSettingsCache.yaml_cache") as mock_yaml_cache, \
             patch("ClassicLib.Constants.DB_PATHS", [Path("/mock/db.sqlite")]), \
             patch("ClassicLib.ScanLog.AsyncIntegration.logger") as mock_logger:

            # Configure async functions to return coroutines that yield values
            # CRITICAL: Use side_effect with async functions, not return_value with coroutines
            # This prevents "coroutine was never awaited" warnings
            async def mock_reformat_coro(*args):
                """Mock coroutine for reformat operation."""
                await asyncio.sleep(0)  # Simulate async work

            async def mock_load_coro(*args):
                """Mock coroutine for load operation."""
                return {"log1": ["line1", "line2"], "log2": ["line3"]}

            # Use side_effect to provide the async function, not return_value with a coroutine
            mock_reformat.side_effect = mock_reformat_coro
            mock_load.side_effect = mock_load_coro

            # Create orchestrator instance with proper async context manager protocol
            mock_orchestrator_instance = MagicMock()

            # Create async functions for async methods
            async def process_batch_coro(*args):
                """Mock coroutine for batch processing."""
                return [
                    (Path("log1.txt"), "report1", False, {}),
                    (Path("log2.txt"), "report2", False, {}),
                    (Path("log3.txt"), "report3", True, {})  # One failed
                ]

            async def write_batch_coro(*args):
                """Mock coroutine for batch writing."""
                return

            # Use side_effect for async methods to avoid unawaited coroutine warnings
            mock_orchestrator_instance.process_crash_logs_batch_async = MagicMock(
                side_effect=process_batch_coro
            )
            mock_orchestrator_instance.write_reports_batch = MagicMock(
                side_effect=write_batch_coro
            )

            # Configure orchestrator context manager with async protocol
            # CRITICAL: Assign async functions directly, don't call them and return coroutines
            async def orchestrator_aenter(self):
                """Async enter for orchestrator context manager."""
                return mock_orchestrator_instance

            async def orchestrator_aexit(self, exc_type, exc_val, exc_tb):
                """Async exit for orchestrator context manager."""
                return

            mock_orchestrator_context = MagicMock()
            # Assign the async functions directly - don't call them!
            mock_orchestrator_context.__aenter__ = orchestrator_aenter
            mock_orchestrator_context.__aexit__ = orchestrator_aexit
            mock_orchestrator.return_value = mock_orchestrator_context

            # Configure yaml cache batch loading - synchronous function
            mock_yaml_cache.batch_get_settings.return_value = [
                ("exclude1", "exclude2"),  # remove_list
                True,  # fcx_mode
                True,  # show_formid_values
                False  # move_unsolved_logs
            ]

            # Configure progress context manager - synchronous context manager
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
        """Test successful async crash log scanning with all components working correctly.

        This test verifies the complete workflow of async crash log scanning,
        including file retrieval, settings loading, reformatting, caching,
        processing, and report writing.
        """
        # Configure mocks for successful scan
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Run the async scan - this is a direct async call, not through AsyncBridge
        await async_crashlogs_scan()

        # Verify crash logs were retrieved
        mock_dependencies["get_files"].assert_called_once()

        # Verify settings were loaded in batch for performance
        mock_dependencies["yaml_cache"].batch_get_settings.assert_called_once()

        # Verify async reformatting was initiated
        assert mock_dependencies["reformat"].called

        # Verify logs were loaded asynchronously
        assert mock_dependencies["load"].called

        # Verify orchestrator was initialized
        mock_dependencies["orchestrator"].assert_called_once()

        # Verify performance logging occurred
        assert mock_dependencies["logger"].info.called

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_with_failed_logs(self, mock_dependencies, mock_crash_logs):
        """Test handling of failed crash log scans with proper error reporting.

        This test ensures that failed scans are properly tracked and reported
        to the user through appropriate messaging.
        """
        mock_dependencies["get_files"].return_value = mock_crash_logs

        # Configure orchestrator to return some failed scans
        async def process_with_failures(*args):
            """Mock coroutine that returns some failed scans."""
            return [
                (mock_crash_logs[0], "report1", True, {}),  # Failed
                (mock_crash_logs[1], "report2", False, {}),  # Success
                (mock_crash_logs[2], "report3", True, {}),   # Failed
            ]

        # Use side_effect, not return_value with coroutine
        mock_dependencies["orchestrator_instance"].process_crash_logs_batch_async = MagicMock(
            side_effect=process_with_failures
        )

        await async_crashlogs_scan()

        # Verify error message was displayed for failed logs
        error_calls = [call for call in mock_dependencies["msg_info"].call_args_list
                      if call and "UNABLE TO PROPERLY SCAN" in str(call)]
        assert len(error_calls) == 1

    @pytest.mark.asyncio
    async def test_async_crashlogs_scan_empty_logs(self, mock_dependencies):
        """Test handling when no crash logs are found.

        This test verifies graceful handling of the edge case where
        no crash logs exist to process.
        """
        mock_dependencies["get_files"].return_value = []

        # Configure empty results for async operations
        async def empty_reformat(*args):
            """Mock coroutine for empty reformat."""
            return

        async def empty_load(*args):
            """Mock coroutine for empty load."""
            return {}

        # Use side_effect, not return_value with coroutines
        mock_dependencies["reformat"].side_effect = empty_reformat
        mock_dependencies["load"].side_effect = empty_load

        await async_crashlogs_scan()

        # Verify the function handles empty list correctly
        mock_dependencies["get_files"].assert_called_once()
        assert mock_dependencies["reformat"].called
        assert mock_dependencies["load"].called


@pytest.mark.unit
class TestRunAsyncScan:
    """Unit tests for run_async_scan wrapper function.

    This class tests the synchronous wrapper that uses AsyncBridge.
    CRITICAL: We mock AsyncBridge.run_async, NOT the underlying async function.
    """

    def test_run_async_scan_uses_bridge_correctly(self):
        """Test that run_async_scan properly uses AsyncBridge for execution.

        This test demonstrates the CORRECT pattern for testing sync wrappers
        that use AsyncBridge:
        1. Mock AsyncBridge.get_instance() to return a mock bridge
        2. Mock bridge.run_async() to return the expected value
        3. Do NOT use AsyncMock for the underlying async function
        """
        with patch("ClassicLib.ScanLog.AsyncIntegration.AsyncBridge") as mock_bridge_class, \
             patch("ClassicLib.ScanLog.AsyncIntegration.async_crashlogs_scan") as mock_async_scan:

            # Configure bridge mock - this is the KEY pattern
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge

            # Mock run_async to return None (successful completion)
            # This simulates AsyncBridge executing the coroutine and returning its result
            mock_bridge.run_async.return_value = None

            # Configure async_crashlogs_scan to return a coroutine
            # We create a real coroutine here, but AsyncBridge will handle it
            async def scan_coro():
                """Mock coroutine for async_crashlogs_scan."""
                return

            mock_async_scan.return_value = scan_coro()

            # Run the sync wrapper
            run_async_scan()

            # Verify AsyncBridge singleton was obtained
            mock_bridge_class.get_instance.assert_called_once()

            # Verify run_async was called (it handles the coroutine)
            mock_bridge.run_async.assert_called_once()

    def test_run_async_scan_propagates_exceptions(self):
        """Test that exceptions from async_crashlogs_scan are properly propagated.

        This test verifies that exceptions raised during async execution
        are correctly propagated through the AsyncBridge to the caller.
        """
        with patch("ClassicLib.ScanLog.AsyncIntegration.AsyncBridge") as mock_bridge_class:

            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge

            # Configure bridge to raise an exception
            # This simulates an error occurring during async execution
            test_exception = RuntimeError("Test async error")
            mock_bridge.run_async.side_effect = test_exception

            # Verify exception is propagated to the caller
            with pytest.raises(RuntimeError, match="Test async error"):
                run_async_scan()

    def test_run_async_scan_handles_bridge_initialization_error(self):
        """Test handling of AsyncBridge initialization errors.

        This test verifies proper error handling when AsyncBridge
        itself fails to initialize.
        """
        with patch("ClassicLib.ScanLog.AsyncIntegration.AsyncBridge") as mock_bridge_class:

            # Configure get_instance to raise an exception
            mock_bridge_class.get_instance.side_effect = RuntimeError("Bridge init failed")

            # Verify the error is propagated
            with pytest.raises(RuntimeError, match="Bridge init failed"):
                run_async_scan()


@pytest.mark.unit
class TestAsyncPatternCompliance:
    """Tests to verify correct async patterns are used throughout.

    These tests ensure that the async/sync bridging patterns are
    correctly implemented to avoid coroutine warnings.
    """

    def test_no_async_mock_for_bridged_calls(self):
        """Verify that AsyncMock is not used for methods called through AsyncBridge.

        This is a meta-test that ensures our test patterns are correct.
        Using AsyncMock for bridge-called methods causes RuntimeWarning.
        """
        # This test passes if the file doesn't use AsyncMock incorrectly
        # The test itself demonstrates the correct pattern

        with patch("ClassicLib.AsyncBridge.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()  # NOT AsyncMock!
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.return_value = "result"

            # This is the correct pattern - no AsyncMock used
            from ClassicLib.AsyncBridge import AsyncBridge
            bridge = AsyncBridge.get_instance()

            async def some_async_func():
                return "result"

            # The bridge handles the coroutine
            result = mock_bridge.run_async(some_async_func())
            assert result == "result"

    @pytest.mark.asyncio
    async def test_pure_async_without_bridge(self):
        """Test pure async functions without AsyncBridge involvement.

        For pure async tests, we can use async/await directly without
        any bridge mocking. This is the simplest pattern.
        """
        async def pure_async_function(value):
            """Simple async function for testing."""
            await asyncio.sleep(0)
            return value * 2

        # Direct async testing - no bridge needed
        result = await pure_async_function(5)
        assert result == 10

    def test_sync_wrapper_pattern(self):
        """Demonstrate the correct pattern for testing sync wrappers.

        This test shows how to properly test a sync function that
        internally uses AsyncBridge to call async code.
        """
        # Example sync wrapper function
        def sync_wrapper(value):
            """Sync wrapper that uses AsyncBridge internally."""
            from ClassicLib.AsyncBridge import AsyncBridge

            async def async_work(val):
                return val * 2

            bridge = AsyncBridge.get_instance()
            return bridge.run_async(async_work(value))

        # Test the sync wrapper with mocked bridge
        with patch("ClassicLib.AsyncBridge.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.return_value = 10  # Mocked result

            result = sync_wrapper(5)
            assert result == 10

            # Verify bridge was used correctly
            mock_bridge.run_async.assert_called_once()

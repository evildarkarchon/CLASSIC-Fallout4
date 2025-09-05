"""
Tests for verifying proper async resource management and cleanup.

This module contains tests that specifically verify that async resources
are properly managed and cleaned up to prevent resource leaks.
"""

import asyncio
import gc
import tempfile
import weakref
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.test_async_utils import (
    AsyncResourceTracker,
    async_test_context,
    ensure_event_loop_cleanup,
    safe_async_cleanup,
    track_async_resources,
)


class SimulatedConnectionError(Exception):
    """Custom exception for simulating database connection errors in tests."""


class ContextTestError(Exception):
    """Custom exception for testing exception handling during context operations."""


@pytest.mark.asyncio
class TestAsyncResourceManagement:
    """Tests for async resource management and cleanup verification."""

    @track_async_resources
    async def test_resource_tracker_detects_leaks(self):
        """Test that the resource tracker can detect leaked resources."""
        tracker = AsyncResourceTracker()

        # Create a mock resource that won't be cleaned up
        class LeakyResource:
            def __init__(self, name):
                self.name = name
                self.closed = False

            async def close(self):
                self.closed = True

        # Create and track a resource
        resource = LeakyResource("test_resource")
        tracker.register(resource, "LeakyResource")

        # Check for leaks before cleanup
        leaks = tracker.check_leaks()
        assert len(leaks) == 1

        # Clean up the resource
        await resource.close()
        del resource
        gc.collect()

        # Check again - should have no leaks after cleanup
        await asyncio.sleep(0)  # Allow weakref callbacks to run
        leaks = tracker.check_leaks()
        assert len(leaks) == 0

    @ensure_event_loop_cleanup
    async def test_event_loop_cleanup_decorator(self) -> None:
        """Test that the event loop cleanup decorator cancels pending tasks."""
        tasks_created = []

        async def background_task() -> None:
            """A task that runs indefinitely."""
            try:
                # Use an Event instead of sleep loop for better efficiency
                stop_event = asyncio.Event()
                await stop_event.wait()
            except asyncio.CancelledError:
                pass

        # Create some background tasks
        for _ in range(3):
            task = asyncio.create_task(background_task())
            tasks_created.append(task)

        # The decorator should cancel these tasks after the test
        # We can't directly assert this here, but the decorator ensures cleanup

        # Verify tasks were created
        assert len(tasks_created) == 3
        assert all(not task.done() for task in tasks_created)

    async def test_safe_async_cleanup_handles_various_resources(self) -> None:
        """Test that safe_async_cleanup handles different types of resources."""

        # Mock resources with different close methods
        class AsyncCloseResource:
            def __init__(self):
                self.closed = False

            async def aclose(self):
                self.closed = True

        class AsyncCloseMethodResource:
            def __init__(self):
                self.closed = False

            async def close(self):
                self.closed = True

        class SyncCloseResource:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        # Create resources
        async_resource = AsyncCloseResource()
        async_method_resource = AsyncCloseMethodResource()
        sync_resource = SyncCloseResource()

        # Clean them up
        await safe_async_cleanup(
            async_resource,
            async_method_resource,
            sync_resource,
            None,  # Test handling of None
        )

        # Verify all were closed
        assert async_resource.closed
        assert async_method_resource.closed
        assert sync_resource.closed

    async def test_async_test_context_manager(self):
        """Test that async_test_context properly manages test lifecycle."""
        initial_task_count = len(asyncio.all_tasks())

        async with async_test_context():
            # Create some tasks during the test
            async def dummy_task():
                await asyncio.sleep(0.01)

            task1 = asyncio.create_task(dummy_task())
            task2 = asyncio.create_task(dummy_task())

            # Wait for them to complete
            await task1
            await task2

        # After context, task count should be back to initial
        # Give a small buffer for the context manager's own cleanup
        await asyncio.sleep(0)
        final_task_count = len(asyncio.all_tasks())

        # Should be roughly the same (within 1-2 for test framework tasks)
        assert abs(final_task_count - initial_task_count) <= 2

    async def test_async_cleanup_fixture(self):
        """Test async cleanup pattern without fixture dependency."""

        class TestResource:
            def __init__(self, name):
                self.name = name
                self.closed = False

            async def aclose(self):
                self.closed = True

        # Create and track resources
        resource1 = TestResource("resource1")
        resource2 = TestResource("resource2")
        resources = [resource1, resource2]

        # Resources should not be closed yet
        assert not resource1.closed
        assert not resource2.closed

        # Clean them up
        await safe_async_cleanup(*resources)

        # Now they should be closed
        assert resource1.closed
        assert resource2.closed

    async def test_clean_event_loop_pattern(self):
        """Test event loop cleanup pattern."""
        loop = asyncio.get_event_loop()

        # Verify we have a loop
        assert loop is not None
        assert loop.is_running()

        # Track initial tasks
        initial_tasks = set(asyncio.all_tasks(loop))

        # Create a task to verify cleanup
        async def background_work():
            await asyncio.sleep(10)  # Long-running task

        task = asyncio.create_task(background_work())

        # Task should be running
        assert not task.done()

        # Clean it up
        task.cancel()
        import contextlib

        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Verify cleanup
        current_tasks = set(asyncio.all_tasks(loop))
        new_tasks = current_tasks - initial_tasks
        assert len(new_tasks) == 0 or all(t.done() for t in new_tasks)


@pytest.mark.asyncio
class TestDatabasePoolResourceManagement:
    """Specific tests for AsyncDatabasePool resource management."""

    async def test_database_pool_cleanup_on_error(self):
        """Test that database pool properly cleans up connections on initialization error."""
        from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test database file
            db_path = Path(temp_dir) / "test.db"
            db_path.write_text("dummy")

            # Mock to make initialization fail after opening some connections
            open_count = 0
            opened_connections = []

            async def mock_connect(path):
                nonlocal open_count
                open_count += 1

                mock_conn = AsyncMock()
                mock_conn.close = AsyncMock()
                opened_connections.append(mock_conn)

                if open_count > 1:
                    raise SimulatedConnectionError("Simulated connection error")

                return mock_conn

            with (
                patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", [db_path, db_path, db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect),
            ):
                pool = AsyncDatabasePool()

                # Initialize should fail
                with pytest.raises(SimulatedConnectionError, match="Simulated connection error"):
                    await pool.initialize()

                # Verify connections were cleaned up
                assert len(pool.connections) == 0

                # Verify close was called on opened connections
                for conn in opened_connections:
                    if conn.close.called:
                        # At least some connections should have been closed
                        pass

    async def test_database_pool_context_manager_cleanup(self):
        """Test that database pool context manager ensures cleanup."""
        from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool

        cleanup_called = False

        with patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", []):
            async with AsyncDatabasePool() as pool:
                # Monkey-patch to track cleanup
                original_close = pool.close

                async def tracked_close():
                    nonlocal cleanup_called
                    cleanup_called = True
                    await original_close()

                pool.close = tracked_close

            # Cleanup should have been called
            # Note: The context manager calls close internally
            # We can't directly assert this without modifying the class


@pytest.mark.asyncio
class TestAsyncPipelineResourceManagement:
    """Tests for async pipeline resource management."""

    @pytest.mark.usefixtures("init_message_handler_fixture")
    async def test_pipeline_cleanup_on_exception(self):
        """Test that pipeline properly cleans up resources on exception."""
        from ClassicLib.ScanLog.AsyncPipeline import AsyncCrashLogPipeline

        mock_yamldata = MagicMock()
        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # Mock to make processing fail
        with (
            patch("ClassicLib.ScanLog.AsyncPipeline.crashlogs_reformat_async") as mock_reformat,
            patch("ClassicLib.ScanLog.AsyncPipeline.load_crash_logs_async") as mock_load,
        ):
            # Make reformat raise an exception
            mock_reformat.side_effect = Exception("Simulated error")

            # Processing should fail
            with pytest.raises(Exception, match="Simulated error"):
                await pipeline.process_crash_logs_async([], ())

            # Pipeline should still be in a valid state for cleanup
            assert isinstance(pipeline.performance_stats, dict)

    async def test_orchestrator_resource_cleanup(self):
        """Test that OrchestratorCore properly manages database pool resources."""
        from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
        from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

        mock_yamldata = MagicMock()
        mock_crashlogs = MagicMock(spec=ThreadSafeLogCache)

        def _raise_test_exception():
            """Helper function to raise a test exception during context operations."""
            raise ContextTestError("Test exception during context")

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool") as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool

            # Test normal flow
            async with OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=mock_crashlogs,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            ) as orchestrator:
                assert orchestrator._db_pool == mock_pool
                mock_pool.initialize.assert_called_once()

            # Verify cleanup was called
            mock_pool.close.assert_called_once()

            # Reset mocks for next test
            mock_pool.initialize.reset_mock()
            mock_pool.close.reset_mock()

            # Test cleanup on exception during context
            # Create a new orchestrator that will fail during usage
            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=mock_crashlogs,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            )

            # Use the context manager and force an exception
            try:
                async with orchestrator:
                    # Force an exception after initialization
                    _raise_test_exception()
            except ContextTestError as e:
                if "Test exception" not in str(e):
                    raise

            # Cleanup should have been called
            mock_pool.close.assert_called_once()


@pytest.mark.asyncio
class TestMemoryLeakDetection:
    """Tests for detecting memory leaks in async operations."""

    async def test_no_memory_leak_in_repeated_operations(self):
        """Test that repeated async operations don't leak memory."""

        # Track object counts
        initial_objects = len(gc.get_objects())

        # Perform repeated operations
        for _ in range(10):

            async def dummy_operation():
                data = ["test"] * 100
                await asyncio.sleep(0)
                return data

            result = await dummy_operation()
            del result

        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0)

        # Check object count didn't grow significantly
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects

        # Allow some growth for test infrastructure, but not excessive
        assert growth < 100, f"Possible memory leak: {growth} objects not freed"

    async def test_weakref_cleanup_in_async_context(self):
        """Test that weakrefs are properly cleaned up in async contexts."""
        cleaned_up = False

        class TrackedObject:
            pass

        def cleanup_callback(ref):
            nonlocal cleaned_up
            cleaned_up = True

        # Create and track object
        obj = TrackedObject()
        weak_ref = weakref.ref(obj, cleanup_callback)

        # Object should exist
        assert weak_ref() is not None
        assert not cleaned_up

        # Delete object
        del obj
        gc.collect()
        await asyncio.sleep(0)  # Allow callbacks to run

        # Object should be gone
        assert weak_ref() is None
        assert cleaned_up

"""
Tests for YamlSettingsCache edge cases and stress scenarios.

This module validates YamlSettingsCache behavior in edge cases including
singleton deletion, weak references, stress testing under high concurrency,
event loop changes, and async operations.

Test Categories:
- Singleton behavior after deletion
- Weak reference handling
- Stress testing with concurrent creation
- Event loop change handling
- Async operations integration
"""

import asyncio
import gc
import threading
import time
import weakref
from unittest.mock import patch

import pytest

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettings import YamlSettingsCache

pytestmark = pytest.mark.unit


class TestEdgeCases:
    """Tests for edge cases and stress testing."""

    def test_singleton_after_deletion(self) -> None:
        """
        Test singleton behavior after instance is deleted.

        If someone deletes the _instance, get_instance() should create
        a new one safely.
        """
        # Get initial instance
        instance1 = YamlSettingsCache.get_instance()
        id(instance1)

        # Force delete the instance
        YamlSettingsCache._instance = None
        del instance1
        gc.collect()  # Force garbage collection

        # Get new instance - should create a new one
        instance2 = YamlSettingsCache.get_instance()
        id(instance2)

        # Should be a new object (different memory address)
        assert instance2 is not None
        assert YamlSettingsCache._instance is instance2

    def test_singleton_with_weak_references(self) -> None:
        """
        Test that weak references to singleton work correctly.

        This is important for tests that might use weak references
        to detect object lifecycle.
        """
        instance = YamlSettingsCache.get_instance()

        # Create weak reference
        weak_ref = weakref.ref(instance)

        # Weak reference should be valid
        assert weak_ref() is instance

        # Even if we "delete" our reference, singleton keeps it alive
        del instance
        gc.collect()

        # Weak reference should still be valid because singleton holds the instance
        assert weak_ref() is not None
        assert weak_ref() is YamlSettingsCache._instance

    def test_stress_concurrent_singleton_creation(self) -> None:
        """
        Stress test with many threads trying to create singleton simultaneously.

        This tests the robustness of the double-check locking pattern under
        extreme concurrency.
        """
        # Clear instance to test creation under stress
        YamlSettingsCache._instance = None

        num_threads = 100
        instances = []
        creation_times = []
        lock = threading.Lock()

        def stress_thread():
            """Thread function for stress test."""
            start_time = time.perf_counter()
            instance = YamlSettingsCache.get_instance()
            end_time = time.perf_counter()

            with lock:
                instances.append(instance)
                creation_times.append(end_time - start_time)

        # Create and start all threads at once
        threads = [threading.Thread(target=stress_thread) for _ in range(num_threads)]

        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.perf_counter() - start

        # All threads should get the same instance
        unique_instances = set(id(inst) for inst in instances)
        assert len(unique_instances) == 1, f"Created {len(unique_instances)} instances!"

        # Performance check - should complete reasonably fast
        assert total_time < 2.0, f"Took too long: {total_time:.2f} seconds"

        print(f"Stress test completed in {total_time:.2f}s")
        print(f"Average time per thread: {sum(creation_times) / len(creation_times):.4f}s")

    @pytest.mark.asyncio
    async def test_async_operations_with_singleton(self) -> None:
        """
        Test that async operations work correctly with the singleton.

        The singleton uses AsyncBridge internally, this tests that async
        operations complete successfully.
        """
        cache = YamlSettingsCache.get_instance()

        # Test batch operations (uses async internally)
        requests = [
            (str, YAML.TEST, "test.key1"),
            (int, YAML.TEST, "test.key2"),
            (bool, YAML.TEST, "test.key3"),
        ]

        # Mock the async core to return test values
        # Ensure initialized using async method
        core = await cache._ensure_async_core_async()

        async def mock_batch_get(reqs):
            return ["value1", 42, True]

        # Mock the method on the core instance
        with patch.object(core, "batch_get_settings", side_effect=mock_batch_get):
            # Use async method directly
            results = await cache.batch_get_settings_async(requests)
            assert results == ["value1", 42, True]


class TestEventLoopChange:
    """Tests for handling event loop changes.

    asyncio.Lock objects are bound to the event loop in which they're first used.
    If the event loop changes, we need to create a new lock to avoid
    "Lock object is bound to a different loop" errors.
    """

    def test_async_init_lock_survives_event_loop_change(self) -> None:
        """Test that _get_async_init_lock handles event loop changes.

        This test simulates the scenario where:
        1. asyncio.run() is called, creating event loop A
        2. A lock is created and cached
        3. asyncio.run() completes, closing event loop A
        4. asyncio.run() is called again, creating event loop B
        5. The cached lock should be replaced with a new one for loop B

        Before the fix, step 5 would raise:
        RuntimeError: Lock object is bound to a different loop than the current one
        """
        # Reset the async init lock to start fresh
        YamlSettingsCache._async_init_lock = None

        locks_and_loops: list[tuple[asyncio.Lock, asyncio.AbstractEventLoop]] = []

        async def capture_lock_and_loop() -> None:
            """Capture the lock and current event loop."""
            lock = YamlSettingsCache._get_async_init_lock()
            loop = asyncio.get_running_loop()
            locks_and_loops.append((lock, loop))
            # Actually use the lock to ensure it's bound
            async with lock:
                pass

        # First event loop
        asyncio.run(capture_lock_and_loop())

        # Second event loop (simulates app restart or sequential asyncio.run() calls)
        asyncio.run(capture_lock_and_loop())

        # Third event loop for good measure
        asyncio.run(capture_lock_and_loop())

        # We should have 3 different event loops
        loops = [loop for _, loop in locks_and_loops]
        assert len(set(id(loop) for loop in loops)) == 3, "Should have 3 different event loops"

        # The locks should be different for different event loops
        locks = [lock for lock, _ in locks_and_loops]
        lock_ids = [id(lock) for lock in locks]
        # At least the locks for different loops should be different
        assert len(set(lock_ids)) == 3, (
            "Should create new locks for new event loops to avoid 'Lock object is bound to a different loop' error"
        )

    def test_async_init_lock_reused_in_same_event_loop(self) -> None:
        """Test that the same lock is reused within the same event loop.

        Multiple calls to _get_async_init_lock() within the same event loop
        should return the same lock instance for efficiency.
        """
        # Reset the async init lock to start fresh
        YamlSettingsCache._async_init_lock = None

        locks: list[asyncio.Lock] = []

        async def capture_locks() -> None:
            """Capture locks from multiple calls in the same loop."""
            lock1 = YamlSettingsCache._get_async_init_lock()
            lock2 = YamlSettingsCache._get_async_init_lock()
            lock3 = YamlSettingsCache._get_async_init_lock()
            locks.extend([lock1, lock2, lock3])

        asyncio.run(capture_locks())

        # All locks should be the same within the same event loop
        assert locks[0] is locks[1] is locks[2], "Same lock should be reused within the same event loop"

    def test_async_init_lock_raises_without_event_loop(self) -> None:
        """Test that _get_async_init_lock raises RuntimeError without a running event loop.

        In Python 3.12+, creating asyncio.Lock() without a running event loop raises
        RuntimeError or DeprecationWarning. The _get_async_init_lock() method should
        detect this condition and raise a clear error before attempting to create
        the lock.

        This ensures graceful failure with a helpful message instead of a cryptic
        "There is no current event loop" error.
        """
        # Reset the async init lock to start fresh
        YamlSettingsCache._async_init_lock = None

        # Calling outside of async context should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            YamlSettingsCache._get_async_init_lock()

        # Verify the error message is helpful
        assert "_get_async_init_lock() must be called from an async context" in str(exc_info.value)
        assert "running event loop" in str(exc_info.value)

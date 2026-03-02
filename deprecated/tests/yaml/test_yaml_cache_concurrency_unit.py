"""
Consolidated tests for YamlSettingsCache concurrency and edge cases.

This module validates thread-safe behavior of YamlSettingsCache under concurrent
access, edge cases, and stress scenarios including:
- Parallel singleton access from multiple threads
- Concurrent read/write operations without corruption
- AsyncBridge interaction (thread-local vs singleton)
- Singleton deletion and recovery
- Weak reference handling
- Stress testing under high concurrency
- Event loop change handling

Test Categories:
- Thread safety in parallel test execution
- Edge cases and stress testing
- Event loop change handling
"""

import asyncio
import gc
import threading
import time
import weakref
from unittest.mock import patch

import pytest

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml import YamlSettingsCache

pytestmark = pytest.mark.unit


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafetyParallel:
    """Tests for thread safety in parallel test execution scenarios."""

    def test_parallel_singleton_access(self) -> None:
        """
        Test singleton behavior under parallel access from multiple threads.

        Simulates pytest-xdist parallel test execution where multiple worker
        processes might access the singleton simultaneously.
        """
        results = {}
        errors = []

        def worker_thread(worker_id: int) -> None:
            """Simulate a test worker accessing the singleton."""
            try:
                instance = YamlSettingsCache.get_instance()

                core = instance._get_async_core()

                cache_key = f"worker_{worker_id}_key"
                core.cache.settings_cache[cache_key] = f"value_{worker_id}"  # pyright: ignore[reportArgumentType]

                assert core.cache.settings_cache[cache_key] == f"value_{worker_id}"  # pyright: ignore[reportArgumentType]

                results[worker_id] = id(instance)
            except Exception as e:
                errors.append((worker_id, e))

        threads = []
        for i in range(20):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Errors in workers: {errors}"

        instance_ids = list(results.values())
        assert len(set(instance_ids)) == 1, "Multiple singleton instances created!"

    def test_concurrent_cache_operations(self) -> None:
        """
        Test that concurrent cache operations don't cause corruption.

        Multiple threads performing read/write operations on the cache
        should not cause data corruption or race conditions.
        """
        cache = YamlSettingsCache.get_instance()
        errors = []
        iterations = 100

        def read_write_thread(thread_id: int) -> None:
            """Perform concurrent read/write operations."""
            try:
                for i in range(iterations):
                    key = f"thread_{thread_id}_item_{i}"
                    value = f"value_{thread_id}_{i}"

                    core = cache._get_async_core()
                    core.cache.settings_cache[key] = value  # pyright: ignore[reportArgumentType]

                    read_value = core.cache.settings_cache.get(key)  # pyright: ignore[reportArgumentType]
                    assert read_value == value, f"Data corruption: expected {value}, got {read_value}"

                    other_key = f"thread_{(thread_id + 1) % 5}_item_{i}"
                    _ = core.cache.settings_cache.get(other_key)  # pyright: ignore[reportArgumentType]

            except Exception as e:
                errors.append((thread_id, e))

        threads = []
        for i in range(5):
            thread = threading.Thread(target=read_write_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Errors during concurrent operations: {errors}"

        core = cache._get_async_core()
        for thread_id in range(5):
            for i in range(iterations):
                key = f"thread_{thread_id}_item_{i}"
                expected_value = f"value_{thread_id}_{i}"
                actual_value = core.cache.settings_cache.get(key)  # pyright: ignore[reportArgumentType]
                assert actual_value == expected_value

    def test_async_bridge_interaction(self) -> None:
        """
        Test that YamlSettingsCache correctly interacts with AsyncBridge singleton.

        Both use singleton patterns and must not interfere with each other.
        Note: AsyncBridge is thread-local, so each thread gets its own instance.
        """
        yaml_cache_instance = YamlSettingsCache.get_instance()
        threading.get_ident()
        bridge_instance = AsyncBridge.get_instance()

        assert yaml_cache_instance is not None
        assert bridge_instance is not None

        assert yaml_cache_instance._get_bridge() is bridge_instance

        results = []

        def test_thread():
            """Thread testing both singletons."""
            cache = YamlSettingsCache.get_instance()
            bridge = AsyncBridge.get_instance()

            results.append({
                "thread_id": threading.get_ident(),
                "cache_id": id(cache),
                "bridge_id": id(bridge),
                "cache_bridge_id": id(cache._get_bridge()),
            })

        threads = [threading.Thread(target=test_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        cache_ids = set(r["cache_id"] for r in results)
        assert len(cache_ids) == 1, "YamlSettingsCache should be a true singleton"


# =============================================================================
# Edge Cases and Stress Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and stress testing."""

    def test_singleton_after_deletion(self) -> None:
        """
        Test singleton behavior after instance is deleted.

        If someone deletes the _instance, get_instance() should create
        a new one safely.
        """
        instance1 = YamlSettingsCache.get_instance()
        id(instance1)

        YamlSettingsCache._instance = None
        del instance1
        gc.collect()

        instance2 = YamlSettingsCache.get_instance()
        id(instance2)

        assert instance2 is not None
        assert YamlSettingsCache._instance is instance2

    def test_singleton_with_weak_references(self) -> None:
        """
        Test that weak references to singleton work correctly.

        This is important for tests that might use weak references
        to detect object lifecycle.
        """
        instance = YamlSettingsCache.get_instance()

        weak_ref = weakref.ref(instance)

        assert weak_ref() is instance

        del instance
        gc.collect()

        assert weak_ref() is not None
        assert weak_ref() is YamlSettingsCache._instance

    def test_stress_concurrent_singleton_creation(self) -> None:
        """
        Stress test with many threads trying to create singleton simultaneously.

        This tests the robustness of the double-check locking pattern under
        extreme concurrency.
        """
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

        threads = [threading.Thread(target=stress_thread) for _ in range(num_threads)]

        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.perf_counter() - start

        unique_instances = set(id(inst) for inst in instances)
        assert len(unique_instances) == 1, f"Created {len(unique_instances)} instances!"

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

        requests = [
            (str, YAML.TEST, "test.key1"),
            (int, YAML.TEST, "test.key2"),
            (bool, YAML.TEST, "test.key3"),
        ]

        core = await cache._ensure_async_core_async()

        async def mock_batch_get(reqs):
            return ["value1", 42, True]

        with patch.object(core, "batch_get_settings", side_effect=mock_batch_get):
            results = await cache.batch_get_settings_async(requests)
            assert results == ["value1", 42, True]


# =============================================================================
# Event Loop Change Handling Tests
# =============================================================================


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
        """
        YamlSettingsCache._async_init_lock = None

        locks_and_loops: list[tuple[asyncio.Lock, asyncio.AbstractEventLoop]] = []

        async def capture_lock_and_loop() -> None:
            """Capture the lock and current event loop."""
            lock = YamlSettingsCache._get_async_init_lock()
            loop = asyncio.get_running_loop()
            locks_and_loops.append((lock, loop))
            async with lock:
                pass

        asyncio.run(capture_lock_and_loop())
        asyncio.run(capture_lock_and_loop())
        asyncio.run(capture_lock_and_loop())

        loops = [loop for _, loop in locks_and_loops]
        assert len(set(id(loop) for loop in loops)) == 3, "Should have 3 different event loops"

        locks = [lock for lock, _ in locks_and_loops]
        lock_ids = [id(lock) for lock in locks]
        assert len(set(lock_ids)) == 3, (
            "Should create new locks for new event loops to avoid 'Lock object is bound to a different loop' error"
        )

    def test_async_init_lock_reused_in_same_event_loop(self) -> None:
        """Test that the same lock is reused within the same event loop.

        Multiple calls to _get_async_init_lock() within the same event loop
        should return the same lock instance for efficiency.
        """
        YamlSettingsCache._async_init_lock = None

        locks: list[asyncio.Lock] = []

        async def capture_locks() -> None:
            """Capture locks from multiple calls in the same loop."""
            lock1 = YamlSettingsCache._get_async_init_lock()
            lock2 = YamlSettingsCache._get_async_init_lock()
            lock3 = YamlSettingsCache._get_async_init_lock()
            locks.extend([lock1, lock2, lock3])

        asyncio.run(capture_locks())

        assert locks[0] is locks[1] is locks[2], "Same lock should be reused within the same event loop"

    def test_async_init_lock_raises_without_event_loop(self) -> None:
        """Test that _get_async_init_lock raises RuntimeError without a running event loop.

        In Python 3.12+, creating asyncio.Lock() without a running event loop raises
        RuntimeError or DeprecationWarning. The _get_async_init_lock() method should
        detect this condition and raise a clear error.
        """
        YamlSettingsCache._async_init_lock = None

        with pytest.raises(RuntimeError) as exc_info:
            YamlSettingsCache._get_async_init_lock()

        assert "_get_async_init_lock() must be called from an async context" in str(exc_info.value)
        assert "running event loop" in str(exc_info.value)

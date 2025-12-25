"""
Tests for YamlSettingsCache thread safety in parallel execution scenarios.

This module validates thread-safe behavior of YamlSettingsCache under concurrent
access, including parallel singleton access, concurrent cache operations, and
interaction with other singleton components like AsyncBridge.

Test Categories:
- Parallel singleton access from multiple threads
- Concurrent read/write operations without corruption
- AsyncBridge interaction (thread-local vs singleton)
"""

import threading

import pytest

from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.YamlSettings import YamlSettingsCache

pytestmark = pytest.mark.unit


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
                # Each worker gets the singleton
                instance = YamlSettingsCache.get_instance()

                # Perform some operations
                # Ensure initialized
                core = instance._get_async_core()

                # Simulate cache operations
                cache_key = f"worker_{worker_id}_key"
                core.cache.settings_cache[cache_key] = f"value_{worker_id}"  # pyright: ignore[reportArgumentType]

                # Verify write was successful
                assert core.cache.settings_cache[cache_key] == f"value_{worker_id}"  # pyright: ignore[reportArgumentType]

                results[worker_id] = id(instance)
            except Exception as e:
                errors.append((worker_id, e))

        # Create multiple worker threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors in workers: {errors}"

        # Verify all workers got the same singleton instance
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
                    # Write operation
                    key = f"thread_{thread_id}_item_{i}"
                    value = f"value_{thread_id}_{i}"

                    # Ensure initialized
                    # We access _get_async_core here which is thread-safe
                    core = cache._get_async_core()
                    core.cache.settings_cache[key] = value  # pyright: ignore[reportArgumentType]

                    # Read operation - verify our write
                    read_value = core.cache.settings_cache.get(key)  # pyright: ignore[reportArgumentType]
                    assert read_value == value, f"Data corruption: expected {value}, got {read_value}"

                    # Read other thread's data (if exists)
                    other_key = f"thread_{(thread_id + 1) % 5}_item_{i}"
                    _ = core.cache.settings_cache.get(other_key)  # pyright: ignore[reportArgumentType]

            except Exception as e:
                errors.append((thread_id, e))

        # Run multiple threads concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=read_write_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent operations: {errors}"

        # Verify all data was written correctly
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
        # Get both singletons in main thread
        yaml_cache_instance = YamlSettingsCache.get_instance()
        threading.get_ident()
        bridge_instance = AsyncBridge.get_instance()

        # Verify they're independent
        assert yaml_cache_instance is not None
        assert bridge_instance is not None

        # Verify YamlSettingsCache uses the bridge from the same thread
        assert yaml_cache_instance._get_bridge() is bridge_instance

        # Test that YamlCache is singleton but AsyncBridge is thread-local
        results = []

        def test_thread():
            """Thread testing both singletons."""
            cache = YamlSettingsCache.get_instance()
            bridge = AsyncBridge.get_instance()

            # Cache should be the same, bridge may be different (thread-local)
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

        # Verify all threads saw the same YamlCache instance
        cache_ids = set(r["cache_id"] for r in results)
        assert len(cache_ids) == 1, "YamlSettingsCache should be a true singleton"

        # AsyncBridge is thread-local, so different threads might have different instances
        # This is expected behavior for AsyncBridge

"""
Tests for YamlSettingsCache edge cases and stress scenarios.

This module validates YamlSettingsCache behavior in edge cases including
singleton deletion, weak references, stress testing under high concurrency,
and async operations.

Test Categories:
- Singleton behavior after deletion
- Weak reference handling
- Stress testing with concurrent creation
- Async operations integration
"""

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

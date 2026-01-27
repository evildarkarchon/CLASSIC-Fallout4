"""Tests for GlobalRegistry thread safety."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from ClassicLib.core.registry import GlobalRegistry

pytestmark = [pytest.mark.unit]


class TestThreadSafety:
    """Tests for GlobalRegistry thread safety."""

    def test_concurrent_access_basic(self) -> None:
        """Test concurrent access to the registry from multiple threads."""
        results = []
        errors = []

        def writer_thread(thread_id: int) -> None:
            """Write values to registry."""
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"value_{thread_id}_{i}"
                    GlobalRegistry.register(key, value)
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)

        def reader_thread(thread_id: int) -> None:
            """Read values from registry."""
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_key_{i}"
                    # Wait a bit for writer to potentially write
                    time.sleep(0.002)
                    value = GlobalRegistry.get(key)
                    if value is not None:
                        results.append((key, value))
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(5):
            writer = threading.Thread(target=writer_thread, args=(i,))
            reader = threading.Thread(target=reader_thread, args=(i,))
            threads.extend([writer, reader])

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify some values were successfully written and read
        assert len(results) > 0

    def test_concurrent_modification_same_key(self) -> None:
        """Test concurrent modification of the same key."""
        num_threads = 10
        iterations = 100
        key = "shared_counter"

        def increment_counter(thread_id: int) -> None:
            """Increment a shared counter."""
            for _ in range(iterations):
                # Read current value
                current = GlobalRegistry.get(key) or 0
                # Increment and write back
                GlobalRegistry.register(key, current + 1)
                time.sleep(0.0001)  # Small delay

        # Initialize counter
        GlobalRegistry.register(key, 0)

        # Run threads
        threads = [threading.Thread(target=increment_counter, args=(i,)) for i in range(num_threads)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # The final value might not be exactly num_threads * iterations
        # due to race conditions, but it should be a positive number
        final_value = GlobalRegistry.get(key)
        assert final_value > 0
        # Due to race conditions, we expect some lost updates
        assert final_value <= num_threads * iterations

    def test_concurrent_futures_pool(self) -> None:
        """Test registry access using ThreadPoolExecutor."""

        def register_and_get(key: str, value: str) -> tuple[str, bool]:
            """Register a value and verify it can be retrieved."""
            GlobalRegistry.register(key, value)
            retrieved = GlobalRegistry.get(key)
            return key, retrieved == value

        # Use ThreadPoolExecutor for concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(100):
                key = f"pool_key_{i}"
                value = f"pool_value_{i}"
                future = executor.submit(register_and_get, key, value)
                futures.append(future)

            # Collect results
            results = {}
            for future in as_completed(futures):
                key, success = future.result()
                results[key] = success

        # All operations should have succeeded
        assert all(results.values()), f"Some operations failed: {[k for k, v in results.items() if not v]}"
        assert len(results) == 100

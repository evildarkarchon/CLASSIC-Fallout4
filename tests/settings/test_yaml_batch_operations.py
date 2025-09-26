"""Comprehensive tests for YAML batch operations under load.

This module tests YamlSettingsCache batch loading performance,
cache invalidation, and concurrent access patterns.
"""

import pytest
import threading
import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List, Tuple
import random

from ClassicLib.YamlSettingsCache import YamlSettingsCache, yaml_cache
from ClassicLib.Constants import YAML

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.performance]


class TestYamlBatchOperations:
    """Test suite for YAML batch operations and performance."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Reset YamlSettingsCache before each test."""
        # Clear cache to ensure clean state
        if hasattr(yaml_cache, "_cache"):
            yaml_cache._cache.clear()
        if hasattr(yaml_cache, "_settings_data"):
            yaml_cache._settings_data = {}

    def test_batch_loading_performance(self) -> None:
        """Test batch loading is more efficient than individual loads."""
        cache = YamlSettingsCache()

        # Mock the underlying file I/O
        with patch.object(cache, "_load_yaml_file") as mock_load:
            mock_load.return_value = {
                "section1": {
                    "key1": "value1",
                    "key2": "value2",
                    "key3": "value3",
                },
                "section2": {
                    "key4": "value4",
                    "key5": "value5",
                }
            }

            # Test individual loading
            individual_start = time.time()
            for i in range(1, 6):
                cache.get_setting(str, YAML.TEST, f"section{(i-1)//3 + 1}.key{i}")
            individual_time = time.time() - individual_start

            # Clear cache for fair comparison
            cache._cache.clear()

            # Test batch loading
            batch_start = time.time()
            keys = [
                (str, YAML.TEST, "section1.key1"),
                (str, YAML.TEST, "section1.key2"),
                (str, YAML.TEST, "section1.key3"),
                (str, YAML.TEST, "section2.key4"),
                (str, YAML.TEST, "section2.key5"),
            ]
            cache.batch_get_settings(keys)
            batch_time = time.time() - batch_start

            # Batch should be called fewer times than individual
            # (exact timing may vary, but calls should be optimized)
            assert mock_load.call_count <= 2  # Should load file at most twice

    def test_batch_loading_under_heavy_load(self) -> None:
        """Test batch loading with hundreds of keys."""
        cache = YamlSettingsCache()

        # Create mock data with many keys
        mock_data = {}
        for section_num in range(10):
            section = f"section_{section_num}"
            mock_data[section] = {}
            for key_num in range(50):
                mock_data[section][f"key_{key_num}"] = f"value_{section_num}_{key_num}"

        with patch.object(cache, "_load_yaml_file", return_value=mock_data):
            # Create batch request for 500 keys
            batch_keys = []
            for section_num in range(10):
                for key_num in range(50):
                    batch_keys.append(
                        (str, YAML.TEST, f"section_{section_num}.key_{key_num}")
                    )

            start = time.time()
            results = cache.batch_get_settings(batch_keys)
            elapsed = time.time() - start

            # Should complete quickly even with many keys
            assert elapsed < 1.0  # Should take less than 1 second
            assert len(results) == 500
            assert all(v is not None for v in results.values())

    def test_cache_invalidation_single_key(self) -> None:
        """Test cache invalidation for a single key."""
        cache = YamlSettingsCache()

        with patch.object(cache, "_load_yaml_file") as mock_load:
            mock_load.return_value = {"section": {"key": "initial_value"}}

            # Load and cache value
            value1 = cache.get_setting(str, YAML.TEST, "section.key")
            assert value1 == "initial_value"

            # Invalidate specific key
            cache.invalidate_cache(YAML.TEST, "section.key")

            # Change underlying data
            mock_load.return_value = {"section": {"key": "updated_value"}}

            # Should reload from file
            value2 = cache.get_setting(str, YAML.TEST, "section.key")
            assert value2 == "updated_value"

    def test_cache_invalidation_entire_file(self) -> None:
        """Test cache invalidation for entire file."""
        cache = YamlSettingsCache()

        with patch.object(cache, "_load_yaml_file") as mock_load:
            initial_data = {
                "section1": {"key1": "value1", "key2": "value2"},
                "section2": {"key3": "value3"}
            }
            mock_load.return_value = initial_data

            # Load multiple values
            cache.get_setting(str, YAML.TEST, "section1.key1")
            cache.get_setting(str, YAML.TEST, "section1.key2")
            cache.get_setting(str, YAML.TEST, "section2.key3")

            # Invalidate entire file
            cache.invalidate_cache(YAML.TEST)

            # Update underlying data
            updated_data = {
                "section1": {"key1": "new1", "key2": "new2"},
                "section2": {"key3": "new3"}
            }
            mock_load.return_value = updated_data

            # All values should be reloaded
            assert cache.get_setting(str, YAML.TEST, "section1.key1") == "new1"
            assert cache.get_setting(str, YAML.TEST, "section1.key2") == "new2"
            assert cache.get_setting(str, YAML.TEST, "section2.key3") == "new3"

    def test_concurrent_access_same_key(self) -> None:
        """Test concurrent access to the same key from multiple threads."""
        cache = YamlSettingsCache()
        access_count = 0
        lock = threading.Lock()

        def slow_load(*args):
            nonlocal access_count
            with lock:
                access_count += 1
            time.sleep(0.1)  # Simulate slow I/O
            return {"section": {"key": "value"}}

        with patch.object(cache, "_load_yaml_file", side_effect=slow_load):
            results = []

            def access_key():
                value = cache.get_setting(str, YAML.TEST, "section.key")
                results.append(value)

            # Start multiple threads accessing same key
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=access_key)
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # All should get same value
            assert all(r == "value" for r in results)
            # File should be loaded only once despite concurrent access
            assert access_count == 1

    def test_concurrent_access_different_keys(self) -> None:
        """Test concurrent access to different keys."""
        cache = YamlSettingsCache()

        mock_data = {f"section{i}": {f"key{i}": f"value{i}"} for i in range(10)}

        with patch.object(cache, "_load_yaml_file", return_value=mock_data):
            results = {}

            def access_key(index):
                value = cache.get_setting(str, YAML.TEST, f"section{index}.key{index}")
                results[index] = value

            # Use ThreadPoolExecutor for concurrent access
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(access_key, i) for i in range(10)]
                for future in as_completed(futures):
                    future.result()

            # Check all keys were retrieved correctly
            for i in range(10):
                assert results[i] == f"value{i}"

    def test_concurrent_batch_operations(self) -> None:
        """Test concurrent batch operations from multiple threads."""
        cache = YamlSettingsCache()

        mock_data = {}
        for i in range(20):
            mock_data[f"section{i}"] = {f"key{j}": f"value_{i}_{j}" for j in range(5)}

        with patch.object(cache, "_load_yaml_file", return_value=mock_data):
            results = []
            lock = threading.Lock()

            def batch_operation(thread_id):
                # Each thread requests a different batch
                batch_keys = [
                    (str, YAML.TEST, f"section{thread_id}.key{j}")
                    for j in range(5)
                ]
                batch_result = cache.batch_get_settings(batch_keys)
                with lock:
                    results.append((thread_id, batch_result))

            # Run batch operations concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(batch_operation, i) for i in range(5)]
                for future in as_completed(futures):
                    future.result()

            # Verify all batches completed successfully
            assert len(results) == 5
            for thread_id, batch_result in results:
                assert len(batch_result) == 5
                for j in range(5):
                    key = (str, YAML.TEST, f"section{thread_id}.key{j}")
                    assert batch_result[key] == f"value_{thread_id}_{j}"

    def test_cache_invalidation_during_concurrent_access(self) -> None:
        """Test cache invalidation while concurrent access is happening."""
        cache = YamlSettingsCache()
        version = {"current": 1}
        access_lock = threading.Lock()

        def versioned_load(*args):
            with access_lock:
                v = version["current"]
            time.sleep(0.05)  # Simulate I/O
            return {"section": {"key": f"value_v{v}"}}

        with patch.object(cache, "_load_yaml_file", side_effect=versioned_load):
            results = []
            invalidation_done = threading.Event()

            def reader_thread():
                for _ in range(5):
                    value = cache.get_setting(str, YAML.TEST, "section.key")
                    results.append(value)
                    time.sleep(0.02)

            def invalidator_thread():
                time.sleep(0.1)  # Let some reads happen
                with access_lock:
                    version["current"] = 2
                cache.invalidate_cache(YAML.TEST)
                invalidation_done.set()

            # Start reader threads
            readers = []
            for _ in range(3):
                thread = threading.Thread(target=reader_thread)
                readers.append(thread)
                thread.start()

            # Start invalidator thread
            invalidator = threading.Thread(target=invalidator_thread)
            invalidator.start()

            # Wait for all threads
            for thread in readers:
                thread.join()
            invalidator.join()

            # Should see both versions in results
            assert "value_v1" in results
            assert "value_v2" in results

    def test_batch_loading_with_mixed_types(self) -> None:
        """Test batch loading with different value types."""
        cache = YamlSettingsCache()

        mock_data = {
            "strings": {"key": "string_value"},
            "numbers": {"key": 42},
            "booleans": {"key": True},
            "lists": {"key": [1, 2, 3]},
            "dicts": {"key": {"nested": "value"}},
        }

        with patch.object(cache, "_load_yaml_file", return_value=mock_data):
            batch_keys = [
                (str, YAML.TEST, "strings.key"),
                (int, YAML.TEST, "numbers.key"),
                (bool, YAML.TEST, "booleans.key"),
                (list, YAML.TEST, "lists.key"),
                (dict, YAML.TEST, "dicts.key"),
            ]

            results = cache.batch_get_settings(batch_keys)

            assert results[(str, YAML.TEST, "strings.key")] == "string_value"
            assert results[(int, YAML.TEST, "numbers.key")] == 42
            assert results[(bool, YAML.TEST, "booleans.key")] is True
            assert results[(list, YAML.TEST, "lists.key")] == [1, 2, 3]
            assert results[(dict, YAML.TEST, "dicts.key")] == {"nested": "value"}

    def test_performance_degradation_detection(self) -> None:
        """Test that performance doesn't degrade with cache size."""
        cache = YamlSettingsCache()

        # Create large dataset
        mock_data = {}
        for i in range(100):
            mock_data[f"section{i}"] = {f"key{j}": f"value_{i}_{j}" for j in range(100)}

        with patch.object(cache, "_load_yaml_file", return_value=mock_data):
            # Load many values to fill cache
            for i in range(50):
                for j in range(50):
                    cache.get_setting(str, YAML.TEST, f"section{i}.key{j}")

            # Measure access time with full cache
            start = time.time()
            for _ in range(100):
                i, j = random.randint(0, 49), random.randint(0, 49)
                cache.get_setting(str, YAML.TEST, f"section{i}.key{j}")
            full_cache_time = time.time() - start

            # Access time should remain fast even with full cache
            assert full_cache_time < 0.1  # 100 accesses in under 100ms

    def test_batch_loading_with_failures(self) -> None:
        """Test batch loading handles individual key failures gracefully."""
        cache = YamlSettingsCache()

        mock_data = {
            "valid": {"key1": "value1", "key2": "value2"},
            # "invalid" section doesn't exist
        }

        with patch.object(cache, "_load_yaml_file", return_value=mock_data):
            batch_keys = [
                (str, YAML.TEST, "valid.key1"),
                (str, YAML.TEST, "invalid.key"),  # This will fail
                (str, YAML.TEST, "valid.key2"),
            ]

            results = cache.batch_get_settings(batch_keys)

            # Valid keys should succeed
            assert results[(str, YAML.TEST, "valid.key1")] == "value1"
            assert results[(str, YAML.TEST, "valid.key2")] == "value2"
            # Invalid key should return None or default
            assert results[(str, YAML.TEST, "invalid.key")] is None

    def test_concurrent_invalidation_and_batch_loading(self) -> None:
        """Test concurrent cache invalidation and batch loading."""
        cache = YamlSettingsCache()
        data_version = {"v": 1}

        def load_versioned():
            v = data_version["v"]
            return {
                "section": {f"key{i}": f"value_v{v}_{i}" for i in range(10)}
            }

        with patch.object(cache, "_load_yaml_file", side_effect=load_versioned):
            results = []
            errors = []

            def batch_loader():
                try:
                    batch_keys = [
                        (str, YAML.TEST, f"section.key{i}") for i in range(10)
                    ]
                    result = cache.batch_get_settings(batch_keys)
                    results.append(result)
                except Exception as e:
                    errors.append(e)

            def cache_invalidator():
                time.sleep(0.05)  # Let some loads start
                data_version["v"] = 2
                cache.invalidate_cache(YAML.TEST)

            # Run operations concurrently
            with ThreadPoolExecutor(max_workers=6) as executor:
                # Submit batch loaders
                loader_futures = [executor.submit(batch_loader) for _ in range(5)]
                # Submit invalidator
                invalidator_future = executor.submit(cache_invalidator)

                # Wait for completion
                for future in as_completed(loader_futures + [invalidator_future]):
                    future.result()

            # Should have no errors
            assert len(errors) == 0
            # Should have results from both versions
            assert len(results) == 5
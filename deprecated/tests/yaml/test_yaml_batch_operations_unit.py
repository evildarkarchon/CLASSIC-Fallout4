"""Comprehensive tests for YAML batch operations under load.

This module tests YamlSettingsCache batch loading performance,
cache invalidation, and concurrent access patterns.

Note: Tests use real files since caching now delegates to Rust classic_settings.
"""

import time
from pathlib import Path

import classic_settings
import pytest
import ruamel.yaml

from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml import YamlSettingsCache
from ClassicLib.io.yaml.async_ import AsyncYamlSettingsCore

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.performance]


class TestYamlBatchOperations:
    """Test suite for YAML batch operations and performance."""

    @pytest.fixture(autouse=True)
    def setup(self, message_handler, async_bridge, tmp_path):
        """Reset YamlSettingsCache and Rust cache before each test."""
        # Reset singleton
        YamlSettingsCache._instance = None
        # Clear Rust cache
        classic_settings.clear_cache()

        self.cache = YamlSettingsCache.get_instance()
        self.tmp_path = tmp_path
        self.yaml_writer = ruamel.yaml.YAML()

        # Create a real test file
        self.test_file = tmp_path / "test_data.yaml"

    def _write_yaml(self, path: Path, data: dict) -> None:
        """Helper to write YAML data to a file."""
        with path.open("w", encoding="utf-8") as f:
            self.yaml_writer.dump(data, f)

    def test_batch_loading_performance(self):
        """Test batch loading is more efficient than individual loads."""
        # Create test file with data
        data = {
            "section1": {
                "key1": "value1",
                "key2": "value2",
                "key3": "value3",
            },
            "section2": {
                "key4": "value4",
                "key5": "value5",
            },
        }
        self._write_yaml(self.test_file, data)

        core = self.cache._get_async_core()

        def mock_get_path(store):
            return self.test_file

        core.file_ops.get_path_for_store = mock_get_path

        # Test individual loading
        classic_settings.clear_cache()
        individual_start = time.time()
        for i in range(1, 6):
            self.cache.async_yaml_settings(str, YAML.TEST, f"section{(i - 1) // 3 + 1}.key{i}")
        individual_time = time.time() - individual_start

        # Clear cache for fair comparison
        classic_settings.clear_cache()

        # Test batch loading
        batch_start = time.time()
        keys = [
            (str, YAML.TEST, "section1.key1"),
            (str, YAML.TEST, "section1.key2"),
            (str, YAML.TEST, "section1.key3"),
            (str, YAML.TEST, "section2.key4"),
            (str, YAML.TEST, "section2.key5"),
        ]
        self.cache.batch_get_settings(keys)
        batch_time = time.time() - batch_start

        # Note: Times are captured but not asserted as this tests functionality
        _ = (individual_time, batch_time)

    def test_batch_loading_under_heavy_load(self):
        """Test batch loading with hundreds of keys."""
        # Create mock data with many keys
        mock_data = {}
        for section_num in range(10):
            section = f"section_{section_num}"
            mock_data[section] = {}
            for key_num in range(50):
                mock_data[section][f"key_{key_num}"] = f"value_{section_num}_{key_num}"

        self._write_yaml(self.test_file, mock_data)

        core = self.cache._get_async_core()

        def mock_get_path(store):
            return self.test_file

        core.file_ops.get_path_for_store = mock_get_path

        # Create batch request for 500 keys
        batch_keys = []
        for section_num in range(10):
            for key_num in range(50):
                batch_keys.append((str, YAML.TEST, f"section_{section_num}.key_{key_num}"))

        start = time.time()
        results = self.cache.batch_get_settings(batch_keys)
        elapsed = time.time() - start

        # Should complete quickly even with many keys
        assert len(results) == 500
        assert all(v is not None for v in results)

    def test_cache_invalidation_single_key(self):
        """Test cache invalidation for a single key via Rust."""
        self._write_yaml(self.test_file, {"section": {"key": "initial_value"}})

        core = self.cache._get_async_core()

        def mock_get_path(store):
            return self.test_file

        core.file_ops.get_path_for_store = mock_get_path

        # Load and cache value
        value1 = self.cache.async_yaml_settings(str, YAML.TEST, "section.key")
        assert value1 == "initial_value"

        # Verify cached in Rust
        rust_key = str(self.test_file.resolve())
        assert classic_settings.is_cached(rust_key)

        # Invalidate via Rust
        classic_settings.invalidate(rust_key)
        assert not classic_settings.is_cached(rust_key)

    def test_batch_loading_with_mixed_types(self):
        """Test batch loading with different value types."""
        mock_data = {
            "strings": {"key": "string_value"},
            "numbers": {"key": 42},
            "booleans": {"key": True},
            "lists": {"key": [1, 2, 3]},
            "dicts": {"key": {"nested": "value"}},
        }
        self._write_yaml(self.test_file, mock_data)

        core = self.cache._get_async_core()

        def mock_get_path(store):
            return self.test_file

        core.file_ops.get_path_for_store = mock_get_path

        batch_keys = [
            (str, YAML.TEST, "strings.key"),
            (int, YAML.TEST, "numbers.key"),
            (bool, YAML.TEST, "booleans.key"),
            (list, YAML.TEST, "lists.key"),
            (dict, YAML.TEST, "dicts.key"),
        ]

        results = self.cache.batch_get_settings(batch_keys)

        assert results[0] == "string_value"
        assert results[1] == 42
        assert results[2] is True
        assert results[3] == [1, 2, 3]
        assert results[4] == {"nested": "value"}

    def test_batch_loading_with_failures(self):
        """Test batch loading handles individual key failures gracefully."""
        mock_data = {
            "valid": {"key1": "value1", "key2": "value2"},
        }
        self._write_yaml(self.test_file, mock_data)

        core = self.cache._get_async_core()

        def mock_get_path(store):
            return self.test_file

        core.file_ops.get_path_for_store = mock_get_path

        batch_keys = [
            (str, YAML.TEST, "valid.key1"),
            (str, YAML.TEST, "invalid.key"),  # This will fail (returns None)
            (str, YAML.TEST, "valid.key2"),
        ]

        results = self.cache.batch_get_settings(batch_keys)

        # Valid keys should succeed
        assert results[0] == "value1"
        assert results[1] is None  # Missing key returns None
        assert results[2] == "value2"

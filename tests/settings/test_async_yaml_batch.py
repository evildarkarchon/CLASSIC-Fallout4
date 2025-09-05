"""Tests for batch operations and concurrent access in AsyncYamlSettingsCore."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, F841

import asyncio
from pathlib import Path

import pytest
import ruamel.yaml

from ClassicLib.AsyncYamlSettingsCore import AsyncYamlSettingsCore
from ClassicLib.Constants import YAML


@pytest.fixture
async def async_yaml_core():
    """Create a fresh AsyncYamlSettingsCore instance for testing."""
    core = AsyncYamlSettingsCore()
    yield core
    # Cleanup if needed
    core.cache.clear()
    core.path_cache.clear()
    core.settings_cache.clear()


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "test.yaml"
    data = {"test_settings": {"string_value": "test", "bool_value": True, "int_value": 42, "nested": {"deep_value": "deep"}}}

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)

    return yaml_file


class TestAsyncYamlBatchOperations:
    """Test suite for batch and concurrent operations."""

    @pytest.mark.asyncio
    async def test_batch_get_settings(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test batch settings retrieval."""

        # Mock get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Prepare batch requests
        requests = [
            (str, YAML.TEST, "test_settings.string_value"),
            (bool, YAML.TEST, "test_settings.bool_value"),
            (int, YAML.TEST, "test_settings.int_value"),
        ]

        # Get all settings in batch
        results = await async_yaml_core.batch_get_settings(requests)

        assert results[0] == "test"
        assert results[1] is True
        assert results[2] == 42

    @pytest.mark.asyncio
    async def test_concurrent_loads(self, async_yaml_core, tmp_path):
        """Test concurrent YAML loading."""
        # Create multiple test files
        files = []
        for i in range(5):
            yaml_file = tmp_path / f"test_{i}.yaml"
            data = {"index": i, "value": f"test_{i}"}
            yaml = ruamel.yaml.YAML()
            # Use synchronous write for test setup - this is okay as it's test fixture setup
            with open(yaml_file, "w") as f:
                yaml.dump(data, f)
            files.append(yaml_file)

        # Load all files concurrently
        tasks = [async_yaml_core.load_yaml(f) for f in files]
        results = await asyncio.gather(*tasks)

        # Verify all loaded correctly
        for i, result in enumerate(results):
            assert result["index"] == i
            assert result["value"] == f"test_{i}"

    @pytest.mark.asyncio
    async def test_load_multiple_stores(self, async_yaml_core, tmp_path, monkeypatch):
        """Test loading multiple stores concurrently."""
        # Create test files for different stores
        files = {}
        for store in [YAML.Settings, YAML.Ignore]:
            yaml_file = tmp_path / f"{store.name}.yaml"
            data = {f"{store.name}_data": {"key": f"value_{store.name}"}}
            yaml = ruamel.yaml.YAML()
            # Use synchronous write for test setup - this is okay as it's test fixture setup
            with open(yaml_file, "w") as f:
                yaml.dump(data, f)
            files[store] = yaml_file

        # Mock get_path_for_store
        async def mock_get_path(store):
            return files.get(store, tmp_path / "nonexistent.yaml")

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Load multiple stores
        results = await async_yaml_core.load_multiple_stores([YAML.Settings, YAML.Ignore])

        assert YAML.Settings in results
        assert YAML.Ignore in results
        assert "Settings_data" in results[YAML.Settings]
        assert "Ignore_data" in results[YAML.Ignore]

    @pytest.mark.asyncio
    async def test_file_lock_concurrency(self, async_yaml_core, temp_yaml_file):
        """Test per-file locking for concurrent access."""
        # Track lock acquisitions
        lock_count = 0
        original_get_lock = async_yaml_core._get_file_lock

        async def mock_get_lock(path):
            nonlocal lock_count
            lock_count += 1
            return await original_get_lock(path)

        async_yaml_core._get_file_lock = mock_get_lock

        # Concurrent loads of same file
        tasks = [async_yaml_core.load_yaml(temp_yaml_file) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should get same result
        for result in results:
            assert result == results[0]

        # Lock should have been acquired multiple times
        assert lock_count == 10

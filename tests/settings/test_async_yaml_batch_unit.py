"""
Unit tests for async_yaml_batch - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import asyncio
from pathlib import Path

import pytest
import ruamel.yaml

from ClassicLib.Constants import YAML

pytestmark = pytest.mark.unit

class TestAsyncYamlBatchOperations:
    """Test suite for batch and concurrent operations."""

    @pytest.mark.asyncio
    async def test_batch_get_settings(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test batch settings retrieval."""

        def mock_get_path(store):
            return temp_yaml_file
        monkeypatch.setattr(async_yaml_core.file_ops, 'get_path_for_store', mock_get_path)
        requests = [(str, YAML.TEST, 'test_settings.string_value'), (bool, YAML.TEST, 'test_settings.bool_value'), (int, YAML.TEST, 'test_settings.int_value')]
        results = await async_yaml_core.batch_get_settings(requests)
        assert results[0] == 'test'
        assert results[1] is True
        assert results[2] == 42

    @pytest.mark.asyncio
    async def test_load_multiple_stores(self, async_yaml_core, tmp_path, monkeypatch):
        """Test loading multiple stores concurrently."""
        files = {}
        for store in [YAML.Settings, YAML.TEST]:
            yaml_file = tmp_path / f'{store.name}.yaml'
            data = {f'{store.name}_data': {'key': f'value_{store.name}'}}
            yaml = ruamel.yaml.YAML()
            with Path(yaml_file).open('w') as f:
                yaml.dump(data, f)
            files[store] = yaml_file

        def mock_get_path(store):
            return files.get(store, tmp_path / 'nonexistent.yaml')
        monkeypatch.setattr(async_yaml_core.file_ops, 'get_path_for_store', mock_get_path)
        requests = [(str, YAML.Settings, 'Settings_data.key'), (str, YAML.TEST, 'TEST_data.key')]
        results = await async_yaml_core.batch_get_settings(requests)
        assert results[0] == 'value_Settings'
        assert results[1] == 'value_TEST'

    @pytest.mark.asyncio
    async def test_file_lock_concurrency(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test per-file locking for concurrent access."""
        from ClassicLib.Constants import YAML

        def mock_get_path(store):
            return temp_yaml_file
        monkeypatch.setattr(async_yaml_core.file_ops, 'get_path_for_store', mock_get_path)
        lock_count = 0
        original_get_lock = async_yaml_core._get_file_lock

        def mock_get_lock(path):
            nonlocal lock_count
            lock_count += 1
            return original_get_lock(path)
        async_yaml_core._get_file_lock = mock_get_lock
        tasks = [async_yaml_core.async_yaml_settings(str, YAML.TEST, 'test_settings.string_value') for _ in range(10)]
        results = await asyncio.gather(*tasks)
        for result in results:
            assert result == results[0]
        assert lock_count >= 1

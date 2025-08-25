"""
Test suite for YamlSettingsCache sync wrapper.

Tests the synchronous wrapper functionality and integration with AsyncYamlSettingsCore.
"""

import time
from pathlib import Path
from unittest.mock import patch

import pytest
import ruamel.yaml

from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.YamlSettingsCache import (
    YamlSettingsCache,
    classic_settings,
    yaml_cache,
    yaml_settings,
)


@pytest.fixture
def init_message_handler_fixture():
    """Initialize message handler for tests."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    # Clean up
    import ClassicLib.MessageHandler
    ClassicLib.MessageHandler._message_handler = None


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "test.yaml"
    data = {
        "test_settings": {
            "string_value": "test",
            "bool_value": True,
            "int_value": 42,
            "nested": {
                "deep_value": "deep"
            }
        }
    }

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with open(yaml_file, 'w') as f:
        yaml.dump(data, f)

    return yaml_file


@pytest.fixture
def sync_yaml_cache():
    """Create a fresh YamlSettingsCache instance for testing."""
    # Create new instance bypassing singleton
    cache = object.__new__(YamlSettingsCache)
    cache.__init__()
    return cache


class TestYamlSettingsCacheSync:
    """Test suite for YamlSettingsCache sync wrapper."""

    def test_singleton_behavior(self):
        """Test that YamlSettingsCache maintains singleton pattern."""
        cache1 = YamlSettingsCache()
        cache2 = YamlSettingsCache()
        assert cache1 is cache2
        assert cache1 is yaml_cache

    def test_get_path_for_store(self, sync_yaml_cache):
        """Test path resolution through sync wrapper."""
        main_path = sync_yaml_cache.get_path_for_store(YAML.Main)
        assert main_path == Path("CLASSIC Data/databases/CLASSIC Main.yaml")

        settings_path = sync_yaml_cache.get_path_for_store(YAML.Settings)
        assert settings_path == Path("CLASSIC Settings.yaml")

    def test_load_yaml_sync(self, sync_yaml_cache, temp_yaml_file):
        """Test YAML loading through sync wrapper."""
        data = sync_yaml_cache.load_yaml(temp_yaml_file)
        assert data["test_settings"]["string_value"] == "test"
        assert data["test_settings"]["bool_value"] is True
        assert data["test_settings"]["int_value"] == 42

    def test_get_setting_sync(self, sync_yaml_cache, temp_yaml_file, monkeypatch):
        """Test get_setting through sync wrapper."""
        # Mock the async core's get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(sync_yaml_cache._async_core, "get_path_for_store", mock_get_path)

        # Test string value
        value = sync_yaml_cache.get_setting(str, YAML.TEST, "test_settings.string_value")
        assert value == "test"

        # Test nested value
        value = sync_yaml_cache.get_setting(str, YAML.TEST, "test_settings.nested.deep_value")
        assert value == "deep"

    def test_batch_operations_sync(self, sync_yaml_cache, temp_yaml_file, monkeypatch):
        """Test batch operations through sync wrapper."""
        # Mock the async core's get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(sync_yaml_cache._async_core, "get_path_for_store", mock_get_path)

        # Test batch_get_settings
        requests = [
            (str, YAML.TEST, "test_settings.string_value"),
            (bool, YAML.TEST, "test_settings.bool_value"),
            (int, YAML.TEST, "test_settings.int_value"),
        ]

        results = sync_yaml_cache.batch_get_settings(requests)
        assert results == ["test", True, 42]

    def test_load_multiple_stores_sync(self, sync_yaml_cache, tmp_path, monkeypatch):
        """Test loading multiple stores through sync wrapper."""
        # Create test files
        files = {}
        for store in [YAML.Settings, YAML.Ignore]:
            yaml_file = tmp_path / f"{store.name}.yaml"
            data = {f"{store.name}_data": {"key": f"value_{store.name}"}}
            yaml = ruamel.yaml.YAML()
            with open(yaml_file, 'w') as f:
                yaml.dump(data, f)
            files[store] = yaml_file

        # Mock get_path_for_store
        async def mock_get_path(store):
            return files.get(store, tmp_path / "nonexistent.yaml")

        monkeypatch.setattr(sync_yaml_cache._async_core, "get_path_for_store", mock_get_path)

        # Load multiple stores
        results = sync_yaml_cache.load_multiple_stores([YAML.Settings, YAML.Ignore])

        assert len(results) == 2
        assert "Settings_data" in results[YAML.Settings]
        assert "Ignore_data" in results[YAML.Ignore]

    def test_prefetch_sync(self, sync_yaml_cache, monkeypatch):
        """Test prefetch through sync wrapper."""
        prefetch_called = False

        async def mock_prefetch():
            nonlocal prefetch_called
            prefetch_called = True

        monkeypatch.setattr(sync_yaml_cache._async_core, "prefetch_all_settings", mock_prefetch)

        sync_yaml_cache.prefetch_all_settings()
        assert prefetch_called

    def test_metrics_sync(self, sync_yaml_cache):
        """Test metrics retrieval through sync wrapper."""
        metrics = sync_yaml_cache.get_metrics()
        assert isinstance(metrics, dict)
        assert 'cache_hits' in metrics
        assert 'cache_misses' in metrics
        assert 'file_reads' in metrics
        assert 'file_writes' in metrics

    def test_cache_property_access(self, sync_yaml_cache):
        """Test direct cache property access."""
        # Access cache properties
        assert isinstance(sync_yaml_cache.cache, dict)
        assert isinstance(sync_yaml_cache.path_cache, dict)
        assert isinstance(sync_yaml_cache.settings_cache, dict)

        # Verify they're from the async core
        assert sync_yaml_cache.cache is sync_yaml_cache._async_core.cache
        assert sync_yaml_cache.path_cache is sync_yaml_cache._async_core.path_cache
        assert sync_yaml_cache.settings_cache is sync_yaml_cache._async_core.settings_cache


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_yaml_settings_function(self, temp_yaml_file, monkeypatch):
        """Test yaml_settings module function."""
        # Mock the global cache's get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(yaml_cache._async_core, "get_path_for_store", mock_get_path)

        # Test basic retrieval
        value = yaml_settings(str, YAML.TEST, "test_settings.string_value")
        assert value == "test"

        # Test Path type conversion
        with patch.object(yaml_cache, 'get_setting', return_value="/some/path"):
            path_value = yaml_settings(Path, YAML.TEST, "some.path")
            assert isinstance(path_value, Path)
            # Path normalizes to OS-specific format
            assert path_value == Path("/some/path")

    def test_classic_settings_function(self, tmp_path, monkeypatch):
        """Test classic_settings module function."""
        # Create a mock settings file
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        data = {
            "CLASSIC_Settings": {
                "Test Setting": "test value",
                "Bool Setting": True
            }
        }
        yaml = ruamel.yaml.YAML()
        with open(settings_file, 'w') as f:
            yaml.dump(data, f)

        # Mock paths
        async def mock_get_path(store):
            if store == YAML.Settings:
                return settings_file
            return tmp_path / "nonexistent.yaml"

        monkeypatch.setattr(yaml_cache._async_core, "get_path_for_store", mock_get_path)

        # Test retrieval
        value = classic_settings(str, "Test Setting")
        assert value == "test value"

        bool_value = classic_settings(bool, "Bool Setting")
        assert bool_value is True

    def test_classic_settings_creates_file(self, tmp_path, monkeypatch):
        """Test that classic_settings creates settings file if missing."""
        # Mock paths
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        main_file = tmp_path / "CLASSIC Main.yaml"

        # Create Main.yaml with default settings
        main_data = {
            "CLASSIC_Info": {
                "default_settings": "CLASSIC_Settings:\n  Default: true\n"
            }
        }
        yaml = ruamel.yaml.YAML()
        with open(main_file, 'w') as f:
            yaml.dump(main_data, f)

        async def mock_get_path(store):
            if store == YAML.Settings:
                return settings_file
            if store == YAML.Main:
                return main_file
            return tmp_path / "nonexistent.yaml"

        monkeypatch.setattr(yaml_cache._async_core, "get_path_for_store", mock_get_path)
        monkeypatch.chdir(tmp_path)  # Change to temp dir

        # classic_settings should create the file
        value = classic_settings(bool, "Default")

        # File should now exist
        assert settings_file.exists()
        assert value is True


class TestSyncWrapperPerformance:
    """Performance tests for sync wrapper."""

    def test_sync_wrapper_overhead(self, sync_yaml_cache, temp_yaml_file):
        """Test that sync wrapper doesn't add significant overhead."""
        # Prime the cache
        sync_yaml_cache.load_yaml(temp_yaml_file)

        # Time 100 sync loads (from cache)
        start = time.time()
        for _ in range(100):
            sync_yaml_cache.load_yaml(temp_yaml_file)
        elapsed = time.time() - start

        # Should still be reasonably fast despite sync-to-async bridge
        assert elapsed < 1.0, f"100 sync loads took {elapsed:.2f}s, expected < 1.0s"

    def test_batch_vs_sequential_sync(self, sync_yaml_cache, temp_yaml_file, monkeypatch):
        """Test that batch operations are efficient in sync wrapper."""
        # Mock get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(sync_yaml_cache._async_core, "get_path_for_store", mock_get_path)

        # Prepare requests
        requests = [
            (str, YAML.TEST, "test_settings.string_value"),
            (bool, YAML.TEST, "test_settings.bool_value"),
            (int, YAML.TEST, "test_settings.int_value"),
        ] * 10  # 30 total requests

        # Time batch operation
        start = time.time()
        batch_results = sync_yaml_cache.batch_get_settings(requests)
        batch_time = time.time() - start

        # Time sequential operations
        start = time.time()
        sequential_results = []
        for req in requests:
            result = sync_yaml_cache.get_setting(*req)
            sequential_results.append(result)
        sequential_time = time.time() - start

        # Results should be identical
        assert batch_results == sequential_results

        # Batch shouldn't be too much slower (accounting for overhead)
        assert batch_time <= sequential_time * 3.0, \
            f"Batch took {batch_time:.3f}s vs sequential {sequential_time:.3f}s"

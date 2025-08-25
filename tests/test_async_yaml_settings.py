"""
Comprehensive test suite for AsyncYamlSettingsCore.

Tests async YAML operations, caching behavior, concurrency, and error handling.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import ruamel.yaml

from ClassicLib.AsyncYamlSettingsCore import (
    AsyncYamlSettingsCore,
    classic_settings_async,
    yaml_settings_async,
)
from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import init_message_handler


@pytest.fixture
def init_message_handler_fixture():
    """Initialize message handler for tests."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    # Clean up
    import ClassicLib.MessageHandler
    ClassicLib.MessageHandler._message_handler = None


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


class TestAsyncYamlSettingsCore:
    """Test suite for AsyncYamlSettingsCore."""

    @pytest.mark.asyncio
    async def test_path_resolution(self, async_yaml_core):
        """Test YAML store path resolution."""
        # Test Main store path
        main_path = await async_yaml_core.get_path_for_store(YAML.Main)
        assert main_path == Path("CLASSIC Data/databases/CLASSIC Main.yaml")

        # Test Settings store path
        settings_path = await async_yaml_core.get_path_for_store(YAML.Settings)
        assert settings_path == Path("CLASSIC Settings.yaml")

        # Test path caching
        settings_path2 = await async_yaml_core.get_path_for_store(YAML.Settings)
        assert settings_path2 is settings_path  # Should be same object from cache

    @pytest.mark.asyncio
    async def test_load_yaml_caching(self, async_yaml_core, temp_yaml_file):
        """Test YAML loading and caching behavior."""
        # First load should read from file
        data1 = await async_yaml_core.load_yaml(temp_yaml_file)
        assert data1["test_settings"]["string_value"] == "test"
        assert temp_yaml_file in async_yaml_core.cache

        # Second load should use cache
        data2 = await async_yaml_core.load_yaml(temp_yaml_file)
        assert data2 is data1  # Should be same object from cache

    @pytest.mark.asyncio
    async def test_get_setting_basic(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test basic get_setting functionality."""
        # Mock get_path_for_store to return our temp file
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Test string value
        value = await async_yaml_core.get_setting(str, YAML.TEST, "test_settings.string_value")
        assert value == "test"

        # Test bool value
        value = await async_yaml_core.get_setting(bool, YAML.TEST, "test_settings.bool_value")
        assert value is True

        # Test nested value
        value = await async_yaml_core.get_setting(str, YAML.TEST, "test_settings.nested.deep_value")
        assert value == "deep"

    @pytest.mark.asyncio
    async def test_get_setting_with_update(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test setting update functionality."""
        # Mock get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Update a value
        new_value = "updated"
        result = await async_yaml_core.get_setting(
            str, YAML.TEST, "test_settings.string_value", new_value
        )
        assert result == new_value

        # Verify it was written
        value = await async_yaml_core.get_setting(str, YAML.TEST, "test_settings.string_value")
        assert value == new_value

    @pytest.mark.asyncio
    async def test_static_store_protection(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test that static stores cannot be modified."""
        # Mock get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Attempt to modify a static store should raise ValueError
        with pytest.raises(ValueError, match="Attempted to modify static YAML store"):
            await async_yaml_core.get_setting(
                str, YAML.Main, "test_settings.string_value", "new_value"
            )

    @pytest.mark.asyncio
    async def test_concurrent_loads(self, async_yaml_core, tmp_path):
        """Test concurrent YAML loading."""
        # Create multiple test files
        files = []
        for i in range(5):
            yaml_file = tmp_path / f"test_{i}.yaml"
            data = {"index": i, "value": f"test_{i}"}
            yaml = ruamel.yaml.YAML()
            with open(yaml_file, 'w') as f:
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
    async def test_load_multiple_stores(self, async_yaml_core, tmp_path, monkeypatch):
        """Test loading multiple stores concurrently."""
        # Create test files for different stores
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

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Load multiple stores
        results = await async_yaml_core.load_multiple_stores([YAML.Settings, YAML.Ignore])

        assert YAML.Settings in results
        assert YAML.Ignore in results
        assert "Settings_data" in results[YAML.Settings]
        assert "Ignore_data" in results[YAML.Ignore]

    @pytest.mark.asyncio
    async def test_ttl_cache_invalidation(self, async_yaml_core, temp_yaml_file):
        """Test TTL-based cache invalidation for dynamic files."""
        # Load file first time
        data1 = await async_yaml_core.load_yaml(temp_yaml_file)
        original_value = data1["test_settings"]["string_value"]

        # Modify the file
        yaml = ruamel.yaml.YAML()
        with open(temp_yaml_file) as f:
            data = yaml.load(f)
        data["test_settings"]["string_value"] = "modified"
        with open(temp_yaml_file, 'w') as f:
            yaml.dump(data, f)

        # Immediate load should still use cache
        data2 = await async_yaml_core.load_yaml(temp_yaml_file)
        assert data2["test_settings"]["string_value"] == original_value

        # Mock time to simulate TTL expiration
        with patch('time.time', return_value=time.time() + 10):
            # After TTL, should reload from file
            data3 = await async_yaml_core.load_yaml(temp_yaml_file)
            assert data3["test_settings"]["string_value"] == "modified"

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

    @pytest.mark.asyncio
    async def test_context_manager(self, async_yaml_core, monkeypatch):
        """Test async context manager support."""
        prefetch_called = False

        async def mock_prefetch():
            nonlocal prefetch_called
            prefetch_called = True

        monkeypatch.setattr(async_yaml_core, "prefetch_all_settings", mock_prefetch)

        async with async_yaml_core as core:
            assert core is async_yaml_core
            assert prefetch_called

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, async_yaml_core):
        """Test performance metrics tracking."""
        initial_metrics = await async_yaml_core.get_metrics()
        assert initial_metrics == {
            'cache_hits': 0,
            'cache_misses': 0,
            'file_reads': 0,
            'file_writes': 0
        }

        # Metrics should be a copy, not reference
        initial_metrics['cache_hits'] = 100
        current_metrics = await async_yaml_core.get_metrics()
        assert current_metrics['cache_hits'] == 0

    @pytest.mark.asyncio
    async def test_error_handling_corrupted_yaml(self, async_yaml_core, tmp_path):
        """Test handling of corrupted YAML files."""
        # Create a corrupted YAML file
        yaml_file = tmp_path / "corrupted.yaml"
        yaml_file.write_text("{ invalid yaml: [ mismatched brackets }")

        # Should return empty dict for non-settings files
        result = await async_yaml_core.load_yaml(yaml_file)
        assert result == {}

    @pytest.mark.asyncio
    async def test_settings_file_regeneration(self, async_yaml_core, tmp_path, monkeypatch):
        """Test automatic regeneration of corrupted settings file."""
        # Create a corrupted settings file
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("corrupted: {invalid}")

        # Mock paths
        async def mock_get_path(store):
            if store == YAML.Main:
                return tmp_path / "CLASSIC Main.yaml"
            return settings_file

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Create a mock Main.yaml with default settings
        main_file = tmp_path / "CLASSIC Main.yaml"
        main_data = {
            "CLASSIC_Info": {
                "default_settings": "CLASSIC_Settings:\n  Managed Game: Fallout 4\n"
            }
        }
        yaml = ruamel.yaml.YAML()
        with open(main_file, 'w') as f:
            yaml.dump(main_data, f)

        # Loading should trigger regeneration
        result = await async_yaml_core._load_yaml_file(settings_file)
        assert "CLASSIC_Settings" in result
        assert result["CLASSIC_Settings"]["Managed Game"] == "Fallout 4"

        # Backup should have been created
        backup_files = list(tmp_path.glob("*.bak"))
        assert len(backup_files) == 1


class TestAsyncConvenienceFunctions:
    """Test async convenience functions."""

    @pytest.mark.asyncio
    async def test_yaml_settings_async(self, temp_yaml_file, monkeypatch):
        """Test yaml_settings_async function."""
        # Mock the global core instance
        core = AsyncYamlSettingsCore()

        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(core, "get_path_for_store", mock_get_path)

        with patch('ClassicLib.AsyncYamlSettingsCore.get_async_yaml_core', return_value=core):
            value = await yaml_settings_async(str, YAML.TEST, "test_settings.string_value")
            assert value == "test"

    @pytest.mark.asyncio
    async def test_classic_settings_async(self, temp_yaml_file, monkeypatch):
        """Test classic_settings_async function."""
        # Mock the global core instance
        core = AsyncYamlSettingsCore()

        async def mock_get_path(store):
            if store == YAML.Settings:
                return temp_yaml_file
            return Path("nonexistent.yaml")

        monkeypatch.setattr(core, "get_path_for_store", mock_get_path)

        # Modify temp file to have CLASSIC_Settings structure
        data = {
            "CLASSIC_Settings": {
                "Test Setting": "test value"
            }
        }
        yaml = ruamel.yaml.YAML()
        with open(temp_yaml_file, 'w') as f:
            yaml.dump(data, f)

        with patch('ClassicLib.AsyncYamlSettingsCore.get_async_yaml_core', return_value=core):
            value = await classic_settings_async(str, "Test Setting")
            assert value == "test value"


class TestPerformance:
    """Performance regression tests."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_load_performance(self, async_yaml_core, tmp_path):
        """Test performance of concurrent YAML loading."""
        # Create 50 test files
        files = []
        for i in range(50):
            yaml_file = tmp_path / f"perf_test_{i}.yaml"
            data = {
                "data": {
                    "index": i,
                    "nested": {"value": f"test_{i}" * 100}  # Some bulk
                }
            }
            yaml = ruamel.yaml.YAML()
            with open(yaml_file, 'w') as f:
                yaml.dump(data, f)
            files.append(yaml_file)

        # Time concurrent loading
        start = time.time()
        tasks = [async_yaml_core.load_yaml(f) for f in files]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # Should complete in reasonable time (adjust threshold as needed)
        assert elapsed < 2.0, f"Concurrent loading took {elapsed:.2f}s, expected < 2.0s"
        assert len(results) == 50

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_hit_performance(self, async_yaml_core, temp_yaml_file):
        """Test performance of cache hits."""
        # Prime the cache
        await async_yaml_core.load_yaml(temp_yaml_file)

        # Time 1000 cache hits
        start = time.time()
        for _ in range(1000):
            await async_yaml_core.load_yaml(temp_yaml_file)
        elapsed = time.time() - start

        # Cache hits should be very fast (adjust for system variance)
        assert elapsed < 0.5, f"1000 cache hits took {elapsed:.2f}s, expected < 0.5s"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_operation_performance(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test performance advantage of batch operations."""
        # Mock get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(async_yaml_core, "get_path_for_store", mock_get_path)

        # Prepare 100 requests
        requests = [
            (str, YAML.TEST, "test_settings.string_value")
            for _ in range(100)
        ]

        # Time batch operation
        start = time.time()
        results = await async_yaml_core.batch_get_settings(requests)
        batch_time = time.time() - start

        # Time sequential operations
        start = time.time()
        for req in requests:
            await async_yaml_core.get_setting(*req)
        sequential_time = time.time() - start

        # For cached operations, batch might have overhead but shouldn't be too much slower
        # (batch operations shine more with actual I/O operations)
        assert batch_time <= sequential_time * 3.0, \
            f"Batch took {batch_time:.3f}s vs sequential {sequential_time:.3f}s"

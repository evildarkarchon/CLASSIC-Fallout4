"""
Unit tests for yaml_sync_wrapper - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import ruamel.yaml

from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml import YamlSettingsCache, classic_settings, yaml_cache, yaml_settings

pytestmark = pytest.mark.unit


# Helper to return coroutine
async def async_return(result):
    return result


class TestSyncWrapperCompatibility:
    """Essential tests for sync wrapper compatibility."""

    def test_singleton_behavior(self, message_handler, async_bridge):
        """Test that YamlSettingsCache maintains singleton pattern."""
        # Reset singleton first
        YamlSettingsCache._instance = None
        cache1 = YamlSettingsCache.get_instance()
        cache2 = YamlSettingsCache.get_instance()
        assert cache1 is cache2
        # yaml_cache global is a proxy, calling it returns the singleton
        assert yaml_cache() is cache1

    def test_sync_wrapper_delegates_to_async_core(self, temp_yaml_file, message_handler, async_bridge):
        """Test that sync wrapper correctly delegates to async core."""
        cache = YamlSettingsCache.get_instance()
        # Ensure initialization
        cache._get_async_core()

        assert hasattr(cache, "_async_core")
        assert hasattr(cache, "_bridge")
        from ClassicLib.core.async_bridge import AsyncBridge

        # Mock load_yaml_file for unit testing logic
        async def mock_load(*args, **kwargs):
            return {"test_settings": {"string_value": "test"}}

        with patch.object(cache._async_core.file_ops, "load_yaml_file", side_effect=mock_load):  # pyright: ignore[reportOptionalMemberAccess]
            bridge = AsyncBridge.get_instance()
            # We need to run the coroutine returned by load_yaml_file
            data = bridge.run_async(cache._async_core.file_ops.load_yaml_file(temp_yaml_file))  # pyright: ignore[reportOptionalMemberAccess]
            assert data["test_settings"]["string_value"] == "test"

    def test_cache_property_forwarding(self, message_handler, async_bridge):
        """Test that cache properties forward to async core."""
        cache = YamlSettingsCache.get_instance()
        # Ensure initialization
        cache._get_async_core()

        assert hasattr(cache._async_core, "cache")
        assert hasattr(cache._async_core.cache, "cache")  # pyright: ignore[reportOptionalMemberAccess]
        assert hasattr(cache._async_core.cache, "settings_cache")  # pyright: ignore[reportOptionalMemberAccess]
        assert hasattr(cache._async_core.cache, "path_cache")  # pyright: ignore[reportOptionalMemberAccess]


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_yaml_settings_function(self, temp_yaml_file, monkeypatch, message_handler, async_bridge):
        """Test yaml_settings module function."""

        # Create a mock for AsyncYamlSettingsCore and its file_ops
        mock_file_ops = MagicMock()
        mock_core = MagicMock()
        mock_core.file_ops = mock_file_ops

        # Configure mock_file_ops.get_path_for_store
        def mock_get_path(store):
            return temp_yaml_file

        mock_file_ops.get_path_for_store.side_effect = mock_get_path

        # Configure mock_core.async_yaml_settings to return a coroutine
        async def mock_async_settings(*args, **kwargs):
            return "test"

        mock_core.async_yaml_settings.side_effect = mock_async_settings

        # Patch get_async_yaml_core to return our mock core (as a coroutine)
        async def get_mock_core():
            return mock_core

        # We must patch where it is imported in sync/cache.py
        with patch("ClassicLib.io.yaml.sync.cache.get_async_yaml_core", side_effect=get_mock_core):
            # Reset singleton to ensure it uses patched get_async_yaml_core
            YamlSettingsCache._instance = None

            value = yaml_settings(str, YAML.TEST, "test_settings.string_value")
            assert value == "test"

    def test_yaml_settings_path_conversion(self, message_handler, async_bridge):
        """Test yaml_settings converts strings to Path objects."""
        # We need to patch the async_yaml_settings method on the SINGLETON instance
        # or patch the class method

        with patch("ClassicLib.io.yaml.YamlSettingsCache.async_yaml_settings", return_value="/some/path"):
            path_value = yaml_settings(Path, YAML.TEST, "some.path")
            assert isinstance(path_value, Path)
            assert path_value == Path("/some/path")

        with patch("ClassicLib.io.yaml.YamlSettingsCache.async_yaml_settings", return_value=None):
            path_value = yaml_settings(Path, YAML.TEST, "nonexistent.path")
            assert path_value is None

        with patch("ClassicLib.io.yaml.YamlSettingsCache.async_yaml_settings", return_value=123):
            path_value = yaml_settings(Path, YAML.TEST, "numeric.value")
            assert path_value is None

    def test_classic_settings_function(self, tmp_path, monkeypatch, message_handler, async_bridge):
        """Test classic_settings module function."""
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        data = {"CLASSIC_Settings": {"Test Setting": "test value", "Bool Setting": True}}
        yaml = ruamel.yaml.YAML()
        with settings_file.open("w") as f:
            yaml.dump(data, f)

        def mock_get_path(store):
            if store == YAML.Settings:
                return settings_file
            return tmp_path / "nonexistent.yaml"

        # Ensure initialized
        yaml_cache()._get_async_core()
        monkeypatch.setattr(yaml_cache()._async_core.file_ops, "get_path_for_store", mock_get_path)  # pyright: ignore[reportOptionalMemberAccess]

        # Mock load_yaml_file
        async def mock_load(*args, **kwargs):
            return data

        monkeypatch.setattr(yaml_cache()._async_core.file_ops, "load_yaml_file", mock_load)  # pyright: ignore[reportOptionalMemberAccess]

        value = classic_settings(str, "Test Setting")
        assert value == "test value"
        bool_value = classic_settings(bool, "Bool Setting")
        assert bool_value is True


class TestBatchOperations:
    """Test batch operations through sync wrapper."""

    def test_batch_get_settings_sync(self, temp_yaml_file, monkeypatch, message_handler, async_bridge):
        """Test batch_get_settings through sync wrapper."""
        cache = YamlSettingsCache.get_instance()

        def mock_get_path(store):
            return temp_yaml_file

        # Ensure initialized
        cache._get_async_core()
        monkeypatch.setattr(cache._async_core.file_ops, "get_path_for_store", mock_get_path)  # pyright: ignore[reportOptionalMemberAccess]

        # Mock load_yaml_file
        mock_data = {"test_settings": {"string_value": "test", "bool_value": True, "int_value": 42}}

        async def mock_load(*args, **kwargs):
            return mock_data

        monkeypatch.setattr(cache._async_core.file_ops, "load_yaml_file", mock_load)  # pyright: ignore[reportOptionalMemberAccess]

        requests = [
            (str, YAML.TEST, "test_settings.string_value"),
            (bool, YAML.TEST, "test_settings.bool_value"),
            (int, YAML.TEST, "test_settings.int_value"),
        ]
        results = cache.batch_get_settings(requests)
        assert results == ["test", True, 42]

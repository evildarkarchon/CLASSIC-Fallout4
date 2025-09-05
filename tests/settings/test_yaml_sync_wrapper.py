"""
Test suite for YamlSettingsCache sync wrapper compatibility.

This module contains minimal tests to ensure the sync wrapper correctly
delegates to AsyncYamlSettingsCore. Most functionality is tested in the
async test suites.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
from pathlib import Path
from typing import cast
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
    data = {"test_settings": {"string_value": "test", "bool_value": True, "int_value": 42}}

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with yaml_file.open("w") as f:
        yaml.dump(data, f)

    return yaml_file


class TestSyncWrapperCompatibility:
    """Essential tests for sync wrapper compatibility."""

    def test_singleton_behavior(self):
        """Test that YamlSettingsCache maintains singleton pattern."""
        cache1 = YamlSettingsCache()
        cache2 = YamlSettingsCache()
        assert cache1 is cache2
        assert cache1 is yaml_cache

    def test_sync_wrapper_delegates_to_async_core(self, temp_yaml_file, init_message_handler_fixture):
        """Test that sync wrapper correctly delegates to async core."""
        cache = YamlSettingsCache()

        # Verify the async core exists
        assert hasattr(cache, "_async_core")
        assert hasattr(cache, "_bridge")

        # Test that load_yaml works through the bridge
        data = cast("dict[str, dict[str, str]]", cache.load_yaml(temp_yaml_file))
        assert data["test_settings"]["string_value"] == "test"

    def test_cache_property_forwarding(self):
        """Test that cache properties forward to async core."""
        cache = YamlSettingsCache()

        # Verify properties are forwarded
        assert cache.cache is cache._async_core.cache
        assert cache.path_cache is cache._async_core.path_cache
        assert cache.settings_cache is cache._async_core.settings_cache
        assert cache.file_mod_times is cache._async_core.file_mod_times


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

    def test_yaml_settings_path_conversion(self):
        """Test yaml_settings converts strings to Path objects."""
        with patch.object(yaml_cache, "get_setting", return_value="/some/path"):
            path_value = yaml_settings(Path, YAML.TEST, "some.path")
            assert isinstance(path_value, Path)
            assert path_value == Path("/some/path")

        # Test None handling
        with patch.object(yaml_cache, "get_setting", return_value=None):
            path_value = yaml_settings(Path, YAML.TEST, "nonexistent.path")
            assert path_value is None

        # Test non-string handling
        with patch.object(yaml_cache, "get_setting", return_value=123):
            path_value = yaml_settings(Path, YAML.TEST, "numeric.value")
            assert path_value is None

    def test_classic_settings_function(self, tmp_path, monkeypatch):
        """Test classic_settings module function."""
        # Create a mock settings file
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        data = {"CLASSIC_Settings": {"Test Setting": "test value", "Bool Setting": True}}
        yaml = ruamel.yaml.YAML()
        with settings_file.open("w") as f:
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

    def test_classic_settings_creates_file_if_missing(self, tmp_path, monkeypatch):
        """Test that classic_settings creates settings file if missing."""
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        main_file = tmp_path / "CLASSIC Main.yaml"

        # Create Main.yaml with default settings - using actual YAML formatting
        main_data = {"CLASSIC_Info": {"default_settings": "CLASSIC_Settings:\n  Default: true\n"}}
        yaml = ruamel.yaml.YAML()
        with main_file.open("w") as f:
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


class TestBatchOperations:
    """Test batch operations through sync wrapper."""

    def test_batch_get_settings_sync(self, temp_yaml_file, monkeypatch):
        """Test batch_get_settings through sync wrapper."""
        cache = YamlSettingsCache()

        # Mock get_path_for_store
        async def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(cache._async_core, "get_path_for_store", mock_get_path)

        # Test batch_get_settings
        requests = [
            (str, YAML.TEST, "test_settings.string_value"),
            (bool, YAML.TEST, "test_settings.bool_value"),
            (int, YAML.TEST, "test_settings.int_value"),
        ]

        results = cache.batch_get_settings(requests)
        assert results == ["test", True, 42]

    def test_load_multiple_stores_sync(self, tmp_path, monkeypatch):
        """Test load_multiple_stores through sync wrapper."""
        cache = YamlSettingsCache()

        # Create test files
        files = {}
        for store in [YAML.Settings, YAML.Ignore]:
            yaml_file = tmp_path / f"{store.name}.yaml"
            data = {f"{store.name}_data": {"key": f"value_{store.name}"}}
            yaml = ruamel.yaml.YAML()
            with yaml_file.open("w") as f:
                yaml.dump(data, f)
            files[store] = yaml_file

        # Mock get_path_for_store
        async def mock_get_path(store):
            return files.get(store, tmp_path / "nonexistent.yaml")

        monkeypatch.setattr(cache._async_core, "get_path_for_store", mock_get_path)

        # Load multiple stores
        results = cache.load_multiple_stores([YAML.Settings, YAML.Ignore])

        assert len(results) == 2
        assert "Settings_data" in results[YAML.Settings]
        assert "Ignore_data" in results[YAML.Ignore]

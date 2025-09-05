"""Tests for AsyncYamlSettingsCore basic functionality."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, F841

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
import ruamel.yaml

from ClassicLib.AsyncYamlSettingsCore import AsyncYamlSettingsCore
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
    data = {"test_settings": {"string_value": "test", "bool_value": True, "int_value": 42, "nested": {"deep_value": "deep"}}}

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)

    return yaml_file


class TestAsyncYamlSettingsCore:
    """Test suite for AsyncYamlSettingsCore basic functionality."""

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
        result = await async_yaml_core.get_setting(str, YAML.TEST, "test_settings.string_value", new_value)
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
            await async_yaml_core.get_setting(str, YAML.Main, "test_settings.string_value", "new_value")

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
        assert initial_metrics == {"cache_hits": 0, "cache_misses": 0, "file_reads": 0, "file_writes": 0}

        # Metrics should be a copy, not reference
        initial_metrics["cache_hits"] = 100
        current_metrics = await async_yaml_core.get_metrics()
        assert current_metrics["cache_hits"] == 0

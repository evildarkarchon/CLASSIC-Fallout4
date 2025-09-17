"""
Unit tests for yaml_sync_wrapper - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from typing import cast
from unittest.mock import patch
import pytest
import ruamel.yaml
from ClassicLib.Constants import YAML

from ClassicLib.YamlSettingsCache import YamlSettingsCache, classic_settings, yaml_cache, yaml_settings

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup

pytestmark = pytest.mark.unit

class TestSyncWrapperCompatibility:
    """Essential tests for sync wrapper compatibility."""

    def test_singleton_behavior(self, message_handler, async_bridge):
        """Test that YamlSettingsCache maintains singleton pattern."""
        cache1 = YamlSettingsCache()
        cache2 = YamlSettingsCache()
        assert cache1 is cache2
        assert cache1 is yaml_cache

    def test_sync_wrapper_delegates_to_async_core(self, temp_yaml_file, message_handler, async_bridge):
        """Test that sync wrapper correctly delegates to async core."""
        cache = YamlSettingsCache()
        assert hasattr(cache, '_async_core')
        assert hasattr(cache, '_bridge')
        from ClassicLib.AsyncBridge import AsyncBridge
        bridge = AsyncBridge.get_instance()
        data = bridge.run_async(cache._async_core.file_ops.load_yaml_file(temp_yaml_file))
        assert data['test_settings']['string_value'] == 'test'

    def test_cache_property_forwarding(self, message_handler, async_bridge):
        """Test that cache properties forward to async core."""
        cache = YamlSettingsCache()
        assert hasattr(cache._async_core, 'cache')
        assert hasattr(cache._async_core.cache, 'cache')
        assert hasattr(cache._async_core.cache, 'settings_cache')
        assert hasattr(cache._async_core.cache, 'path_cache')

class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_yaml_settings_function(self, temp_yaml_file, monkeypatch, message_handler, async_bridge):
        """Test yaml_settings module function."""

        def mock_get_path(store):
            return temp_yaml_file
        monkeypatch.setattr(yaml_cache._async_core.file_ops, 'get_path_for_store', mock_get_path)
        value = yaml_settings(str, YAML.TEST, 'test_settings.string_value')
        assert value == 'test'

    def test_yaml_settings_path_conversion(self, message_handler, async_bridge):
        """Test yaml_settings converts strings to Path objects."""
        with patch.object(yaml_cache, 'async_yaml_settings', return_value='/some/path'):
            path_value = yaml_settings(Path, YAML.TEST, 'some.path')
            assert isinstance(path_value, Path)
            assert path_value == Path('/some/path')
        with patch.object(yaml_cache, 'async_yaml_settings', return_value=None):
            path_value = yaml_settings(Path, YAML.TEST, 'nonexistent.path')
            assert path_value is None
        with patch.object(yaml_cache, 'async_yaml_settings', return_value=123):
            path_value = yaml_settings(Path, YAML.TEST, 'numeric.value')
            assert path_value is None

    def test_classic_settings_function(self, tmp_path, monkeypatch, message_handler, async_bridge):
        """Test classic_settings module function."""
        settings_file = tmp_path / 'CLASSIC Settings.yaml'
        data = {'CLASSIC_Settings': {'Test Setting': 'test value', 'Bool Setting': True}}
        yaml = ruamel.yaml.YAML()
        with settings_file.open('w') as f:
            yaml.dump(data, f)

        def mock_get_path(store):
            if store == YAML.Settings:
                return settings_file
            return tmp_path / 'nonexistent.yaml'
        monkeypatch.setattr(yaml_cache._async_core.file_ops, 'get_path_for_store', mock_get_path)
        value = classic_settings(str, 'Test Setting')
        assert value == 'test value'
        bool_value = classic_settings(bool, 'Bool Setting')
        assert bool_value is True

class TestBatchOperations:
    """Test batch operations through sync wrapper."""

    def test_batch_get_settings_sync(self, temp_yaml_file, monkeypatch, message_handler, async_bridge):
        """Test batch_get_settings through sync wrapper."""
        cache = YamlSettingsCache()

        def mock_get_path(store):
            return temp_yaml_file
        monkeypatch.setattr(cache._async_core.file_ops, 'get_path_for_store', mock_get_path)
        requests = [(str, YAML.TEST, 'test_settings.string_value'), (bool, YAML.TEST, 'test_settings.bool_value'), (int, YAML.TEST, 'test_settings.int_value')]
        results = cache.batch_get_settings(requests)
        assert results == ['test', True, 42]

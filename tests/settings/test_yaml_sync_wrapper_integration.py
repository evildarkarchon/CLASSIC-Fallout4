"""
Integration tests for yaml_sync_wrapper - integration logic testing.

This file contains integration tests that test interactions between components.
"""

import pytest
import ruamel.yaml

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import YamlSettingsCache, classic_settings, yaml_cache

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup

pytestmark = pytest.mark.integration


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_classic_settings_creates_file_if_missing(self, tmp_path, monkeypatch, message_handler, async_bridge):
        """Test that classic_settings creates settings file if missing."""
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        main_file = tmp_path / "CLASSIC Main.yaml"
        main_data = {"CLASSIC_Info": {"default_settings": "CLASSIC_Settings:\n  Default: true\n"}}
        yaml = ruamel.yaml.YAML()
        with main_file.open("w") as f:
            yaml.dump(main_data, f)

        def mock_get_path(store):
            if store == YAML.Settings:
                return settings_file
            if store == YAML.Main:
                return main_file
            return tmp_path / "nonexistent.yaml"

        monkeypatch.setattr(yaml_cache._async_core.file_ops, "get_path_for_store", mock_get_path)
        monkeypatch.chdir(tmp_path)
        value = classic_settings(bool, "Default")
        assert settings_file.exists()
        assert value is True


class TestBatchOperations:
    """Test batch operations through sync wrapper."""

    def test_batch_operations_multiple_stores(self, tmp_path, monkeypatch, message_handler, async_bridge):
        """Test batch operations with multiple stores through sync wrapper."""
        cache = YamlSettingsCache.get_instance()
        files = {}
        for store in [YAML.Settings, YAML.Ignore]:
            yaml_file = tmp_path / f"{store.name}.yaml"
            data = {f"{store.name}_data": {"key": f"value_{store.name}"}}
            yaml = ruamel.yaml.YAML()
            with yaml_file.open("w") as f:
                yaml.dump(data, f)
            files[store] = yaml_file

        def mock_get_path(store):
            return files.get(store, tmp_path / "nonexistent.yaml")

        monkeypatch.setattr(cache._async_core.file_ops, "get_path_for_store", mock_get_path)
        requests = [(dict, YAML.Settings, "Settings_data"), (dict, YAML.Ignore, "Ignore_data")]
        results = cache.batch_get_settings(requests)
        assert len(results) == 2
        assert results[0]["key"] == "value_Settings"
        assert results[1]["key"] == "value_Ignore"

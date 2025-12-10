"""
Integration tests for yaml_sync_wrapper - integration logic testing.

This file contains integration tests that test interactions between components.
"""

import pytest
import ruamel.yaml

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import YamlSettingsCache, classic_settings, yaml_cache

pytestmark = pytest.mark.integration


# Helper for async return values
async def async_return(result):
    return result


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

        # Ensure initialized
        core = yaml_cache._get_async_core()
        monkeypatch.setattr(core.file_ops, "get_path_for_store", mock_get_path)
        monkeypatch.chdir(tmp_path)

        # Mock load_yaml_file to avoid I/O issues in test environment
        async def mock_load(path, use_cache=True):
            if path == main_file:
                return main_data
            # For settings file, it might not exist yet or be created
            if path == settings_file:
                # If logic works, it writes the file then reads it.
                # But since we mock load, we must simulate the read after write.
                # However, classic_settings implementation:
                # 1. yaml_settings(Main) -> gets default
                # 2. write_file_sync(settings_path, default)
                # 3. yaml_settings(Settings) -> reads file

                # We can check if file exists on disk (real write)
                if settings_file.exists():
                    # Parse what was written or return expected
                    return {"CLASSIC_Settings": {"Default": True}}
                return {}
            return {}

        monkeypatch.setattr(core.file_ops, "load_yaml_file", mock_load)

        value = classic_settings(bool, "Default")
        assert settings_file.exists()
        assert value is True


class TestBatchOperations:
    """Test batch operations through sync wrapper."""

    def test_batch_operations_multiple_stores(self, tmp_path, monkeypatch, message_handler, async_bridge):
        """Test batch operations with multiple stores through sync wrapper."""
        cache = YamlSettingsCache.get_instance()
        files = {}
        data_map = {}

        for store in [YAML.Settings, YAML.Ignore]:
            yaml_file = tmp_path / f"{store.name}.yaml"
            data = {f"{store.name}_data": {"key": f"value_{store.name}"}}
            yaml = ruamel.yaml.YAML()
            with yaml_file.open("w") as f:
                yaml.dump(data, f)
            files[store] = yaml_file
            data_map[yaml_file] = data

        def mock_get_path(store):
            return files.get(store, tmp_path / "nonexistent.yaml")

        # Ensure initialized and capture the core reference
        core = cache._get_async_core()
        monkeypatch.setattr(core.file_ops, "get_path_for_store", mock_get_path)

        # Mock load_yaml_file
        async def mock_load(path, use_cache=True):
            return data_map.get(path, {})

        monkeypatch.setattr(core.file_ops, "load_yaml_file", mock_load)

        requests = [(dict, YAML.Settings, "Settings_data"), (dict, YAML.Ignore, "Ignore_data")]
        results = cache.batch_get_settings(requests)
        assert len(results) == 2
        assert results[0]["key"] == "value_Settings"
        assert results[1]["key"] == "value_Ignore"

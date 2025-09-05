"""Tests for error handling and recovery in AsyncYamlSettingsCore."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, F841

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


class TestAsyncYamlErrorHandling:
    """Test suite for error handling and recovery."""

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
        main_data = {"CLASSIC_Info": {"default_settings": "CLASSIC_Settings:\n  Managed Game: Fallout 4\n"}}
        yaml = ruamel.yaml.YAML()
        with open(main_file, "w") as f:
            yaml.dump(main_data, f)

        # Loading should trigger regeneration
        result = await async_yaml_core._load_yaml_file(settings_file)
        assert "CLASSIC_Settings" in result
        assert result["CLASSIC_Settings"]["Managed Game"] == "Fallout 4"

        # Backup should have been created
        backup_files = list(tmp_path.glob("*.bak"))
        assert len(backup_files) == 1

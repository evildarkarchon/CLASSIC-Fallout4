"""Tests for async convenience functions in AsyncYamlSettingsCore."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, F841

from pathlib import Path
from unittest.mock import patch

import pytest
import ruamel.yaml

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettings.async_ import (
    AsyncYamlSettingsCore,
    classic_settings_async,
    yaml_settings_async,
)


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "test.yaml"
    data = {"test_settings": {"string_value": "test", "bool_value": True, "int_value": 42, "nested": {"deep_value": "deep"}}}

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with Path(yaml_file).open("w") as f:
        yaml.dump(data, f)

    return yaml_file


class TestAsyncConvenienceFunctions:
    """Test async convenience functions."""

    @pytest.mark.asyncio
    async def test_yaml_settings_async(self, temp_yaml_file, monkeypatch):
        """Test yaml_settings_async function."""
        # Mock the global core instance
        core = AsyncYamlSettingsCore()

        def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(core.file_ops, "get_path_for_store", mock_get_path)

        with patch("ClassicLib.YamlSettings.async_.core.get_async_yaml_core", return_value=core):
            value = await yaml_settings_async(str, YAML.TEST, "test_settings.string_value")
            assert value == "test"

    @pytest.mark.asyncio
    async def test_classic_settings_async(self, temp_yaml_file, monkeypatch):
        """Test classic_settings_async function."""
        import aiofiles

        # Mock the global core instance
        core = AsyncYamlSettingsCore()

        def mock_get_path(store):
            if store == YAML.Settings:
                return temp_yaml_file
            return Path("nonexistent.yaml")

        monkeypatch.setattr(core.file_ops, "get_path_for_store", mock_get_path)

        # Modify temp file to have CLASSIC_Settings structure
        data = {"CLASSIC_Settings": {"Test Setting": "test value"}}
        yaml = ruamel.yaml.YAML()
        from io import StringIO

        stream = StringIO()
        yaml.dump(data, stream)
        async with aiofiles.open(temp_yaml_file, mode="w") as f:
            await f.write(stream.getvalue())

        with patch("ClassicLib.YamlSettings.async_.core.get_async_yaml_core", return_value=core):
            value = await classic_settings_async(str, "Test Setting")
            assert value == "test value"

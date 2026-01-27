"""
Test suite for AsyncYamlSettingsCore integration.

This module contains tests that focus on the integration of async YAML settings
with other components and advanced async scenarios.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
import asyncio
from pathlib import Path

import pytest

from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml.async_ import AsyncYamlSettingsCore

# Note: async_yaml_core and create_yaml_files fixtures are provided by
# tests/fixtures/yaml_fixtures.py via the root conftest.py


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncYamlIntegration:
    """Tests for AsyncYamlSettingsCore integration scenarios."""

    async def test_yaml_settings_loading(self, async_yaml_core, create_yaml_files: Path) -> None:
        """Test that YAML settings are correctly loaded asynchronously."""

        # Mock get_path_for_store to return our test file
        def mock_get_path(store):
            if store == YAML.TEST:
                return create_yaml_files / "CLASSIC Settings.yaml"
            return create_yaml_files / "nonexistent.yaml"

        async_yaml_core.file_ops.get_path_for_store = mock_get_path

        # Test loading settings
        result = await async_yaml_core.async_yaml_settings(str, YAML.TEST, "Game_Info.XSE_Acronym")
        assert result == "F4SE"

        mods = await async_yaml_core.async_yaml_settings(dict, YAML.TEST, "Mods_Alert_Single")
        assert "problematic_mod" in mods  # type: ignore
        assert mods["problematic_mod"] == "This mod causes crashes."  # type: ignore

    async def test_concurrent_yaml_operations(self, async_yaml_core, create_yaml_files: Path) -> None:
        """Test concurrent YAML operations with different stores."""

        # Mock get_path_for_store to return appropriate files
        def mock_get_path(store):
            if store == YAML.Settings:
                return create_yaml_files / "CLASSIC Settings.yaml"
            if store == YAML.Game_Local:
                return create_yaml_files / "CLASSIC Fallout4 Local.yaml"
            return create_yaml_files / "nonexistent.yaml"

        async_yaml_core.file_ops.get_path_for_store = mock_get_path

        # Concurrent operations on different stores
        tasks = [
            async_yaml_core.async_yaml_settings(str, YAML.Settings, "Game_Info.CRASHGEN_LogName"),
            async_yaml_core.async_yaml_settings(list, YAML.Game_Local, "catch_log_records"),
            async_yaml_core.async_yaml_settings(dict, YAML.Settings, "Mods_Alert_Single"),
        ]

        results = await asyncio.gather(*tasks)

        assert results[0] == "Buffout 4"
        assert "Record1" in results[1]
        assert "problematic_mod" in results[2]

    async def test_yaml_settings_with_local_override(self, async_yaml_core, create_yaml_files: Path) -> None:
        """Test that local YAML settings work correctly in async context."""

        # Setup mock to return different files based on the YAML enum
        def mock_get_path(yaml_store: YAML) -> Path:
            if yaml_store == YAML.TEST:
                return create_yaml_files / "CLASSIC Settings.yaml"
            if yaml_store == YAML.Game_Local:
                return create_yaml_files / "CLASSIC Fallout4 Local.yaml"
            # Handle static stores that the system checks for caching strategy
            if yaml_store == YAML.Main:
                return create_yaml_files / "nonexistent_main.yaml"
            if yaml_store == YAML.Game:
                return create_yaml_files / "nonexistent_game.yaml"
            raise FileNotFoundError(f"No YAML file found for {yaml_store}")

        async_yaml_core.file_ops.get_path_for_store = mock_get_path

        # Test that Game_Local settings can be accessed
        local_records = await async_yaml_core.async_yaml_settings(list, YAML.Game_Local, "catch_log_records")
        assert local_records is not None
        assert "Record1" in local_records
        assert "Record2" in local_records

    async def test_yaml_settings_update(self, async_yaml_core, create_yaml_files: Path) -> None:
        """Test that YAML settings can be updated asynchronously."""
        temp_file: Path = create_yaml_files / "temp_settings.yaml"
        temp_file.write_text("test_key: initial_value")

        def mock_get_path(yaml_store: YAML) -> Path:
            if yaml_store == YAML.TEST:
                return temp_file
            # Handle static stores that the system checks for caching strategy
            if yaml_store == YAML.Main:
                return create_yaml_files / "nonexistent_main.yaml"
            if yaml_store == YAML.Game:
                return create_yaml_files / "nonexistent_game.yaml"
            raise FileNotFoundError(f"No YAML file found for {yaml_store}")

        async_yaml_core.file_ops.get_path_for_store = mock_get_path

        # Test initial value
        initial_value = await async_yaml_core.async_yaml_settings(str, YAML.TEST, "test_key")
        assert initial_value == "initial_value"

        # Update value
        await async_yaml_core.async_yaml_settings(str, YAML.TEST, "test_key", "updated_value")

        # Check updated value
        updated_value = await async_yaml_core.async_yaml_settings(str, YAML.TEST, "test_key")
        assert updated_value == "updated_value"

    @pytest.mark.timing
    async def test_prefetch_all_settings(self, async_yaml_core, create_yaml_files: Path) -> None:
        """Test prefetching all settings for performance."""

        # Setup paths
        def mock_get_path(store):
            if store == YAML.Settings:
                return create_yaml_files / "CLASSIC Settings.yaml"
            if store == YAML.Game_Local:
                return create_yaml_files / "CLASSIC Fallout4 Local.yaml"
            return create_yaml_files / "nonexistent.yaml"

        async_yaml_core.file_ops.get_path_for_store = mock_get_path

        # Load multiple stores to populate cache
        stores_to_load = [(str, YAML.Settings, "Game_Info.CRASHGEN_LogName"), (list, YAML.Game_Local, "catch_log_records")]
        await async_yaml_core.batch_get_settings(stores_to_load)

        # Check that settings are cached
        assert len(async_yaml_core.cache.settings_cache) > 0

        # Accessing settings should now be from cache (fast)
        import time

        start = time.time()
        result = await async_yaml_core.async_yaml_settings(str, YAML.Settings, "Game_Info.CRASHGEN_LogName")
        elapsed = time.time() - start

        assert result == "Buffout 4"
        assert elapsed < 0.01  # Should be very fast from cache


@pytest.mark.asyncio
class TestAsyncYamlConvenienceFunctions:
    """Test async convenience functions."""

    async def test_yaml_settings_async_function(self, create_yaml_files: Path) -> None:
        """Test yaml_settings_async convenience function."""
        # Create a mock core
        core = AsyncYamlSettingsCore()

        def mock_get_path(store):
            if store == YAML.TEST:
                return create_yaml_files / "CLASSIC Settings.yaml"
            return create_yaml_files / "nonexistent.yaml"

        core.file_ops.get_path_for_store = mock_get_path  # pyright: ignore[reportAttributeAccessIssue]

        # Note: yaml_settings_async doesn't exist in the current API
        # We'll test the async_yaml_settings method directly
        result = await core.async_yaml_settings(str, YAML.TEST, "Game_Info.XSE_Acronym")
        assert result == "F4SE"


if __name__ == "__main__":
    pytest.main()

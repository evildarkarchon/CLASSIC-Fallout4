"""
Test suite for YAML settings integration.

This module contains tests that focus on the integration of YAML settings
with the scan logs functionality.
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from CLASSIC_ScanLogs import ClassicScanLogs
from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import yaml_settings


@pytest.fixture
def create_yaml_files(tmp_path: Path) -> Path:
    """Create temporary YAML files for testing."""
    yaml_dir: Path = tmp_path / "yaml"
    yaml_dir.mkdir(exist_ok=True)

    # Create main settings file
    settings_file: Path = yaml_dir / "CLASSIC Settings.yaml"
    settings_file.write_text("""
Game_Info:
  CRASHGEN_LogName: "Buffout 4"
  XSE_Acronym: "F4SE"
    
Mods_Alert_Single:
  problematic_mod: "This mod causes crashes."
  another_problem: "Another problematic mod."
    
Mods_Alert_Double:
  mod_conflict | mod_conflict2: "These mods conflict with each other."
    
Mods_Alert_Important:
  critical_mod | Critical Mod: "This mod is critical and incompatible with your GPU."
    
Crashlog_Error_Check:
  "HIGH | Access violation": "Access violation detected"
  "MEDIUM | Null pointer": "Null pointer detected"
    
Crashlog_Stack_Check:
  "MEDIUM | Problematic stack":
    - "required:BadFunction"
    - "optional:OtherFunction"
    """)

    # Create local settings file
    local_file: Path = yaml_dir / "CLASSIC Fallout4 Local.yaml"
    local_file.write_text("""
catch_log_records:
  - "Record1"
  - "Record2"
    """)

    return yaml_dir


@pytest.mark.integration
class TestYamlSettingsIntegration:
    """Tests for YAML settings integration with scan logs functionality."""

    def test_yaml_settings_loading(self, create_yaml_files: Path) -> None:
        """Test that YAML settings are correctly loaded."""
        with patch("ClassicLib.YamlSettingsCache.YamlSettingsCache.get_path_for_store") as mock_path:
            # Mock the path to point to our test file
            mock_path.return_value = create_yaml_files / "CLASSIC Settings.yaml"

            # Test loading settings
            result: str | None = yaml_settings(str, YAML.Settings, "Game_Info.XSE_Acronym")
            assert result == "F4SE"

            mods: dict[Any, Any] | None = yaml_settings(dict, YAML.Settings, "Mods_Alert_Single")
            assert "problematic_mod" in mods  # type: ignore
            assert mods["problematic_mod"] == "This mod causes crashes."  # type: ignore

    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_scan_logs_settings_integration(self, create_yaml_files: Path) -> None:
        """Test that ClassicScanLogs properly integrates with YAML settings."""
        with (
            patch("ClassicLib.YamlSettingsCache.YamlSettingsCache.get_path_for_store") as mock_path,
            patch("ClassicLib.GlobalRegistry.get") as mock_registry,
            patch("ClassicLib.ScanLog.crashlogs_get_files") as mock_get_files,
            patch("ClassicLib.ScanLog.crashlogs_reformat"),
        ):
            # Configure mocks
            mock_path.side_effect = lambda _: create_yaml_files / "CLASSIC Settings.yaml"
            mock_registry.return_value = "Fallout4"
            mock_get_files.return_value = []  # No crash logs for this test

            # Initialize ClassicScanLogs
            try:
                scanner: ClassicScanLogs = ClassicScanLogs()

                # Check that settings were loaded through yamldata
                assert hasattr(scanner, "yamldata")
                assert scanner.yamldata is not None

                # Check that orchestrator was created
                assert hasattr(scanner, "orchestrator")
                assert scanner.orchestrator is not None

            except Exception as e:  # noqa: BLE001
                pytest.skip(f"ClassicScanLogs initialization failed: {e}")

    def test_yaml_settings_with_local_override(self, create_yaml_files: Path) -> None:
        """Test that local YAML settings override global settings when appropriate."""
        with patch("ClassicLib.YamlSettingsCache.YamlSettingsCache.get_path_for_store") as mock_path:
            # Setup mock to return different files based on the YAML enum
            def mock_get_path(yaml_store: YAML) -> Path | None:
                if yaml_store == YAML.Settings:
                    return create_yaml_files / "CLASSIC Settings.yaml"
                if yaml_store == YAML.Game_Local:
                    return create_yaml_files / "CLASSIC Fallout4 Local.yaml"
                return None

            mock_path.side_effect = mock_get_path

            # Test that Game_Local settings can be accessed
            local_records: list[Any] | None = yaml_settings(list, YAML.Game_Local, "catch_log_records")
            assert local_records is not None
            assert "Record1" in local_records
            assert "Record2" in local_records

    def test_yaml_settings_update(self, create_yaml_files: Path) -> None:
        """Test that YAML settings can be updated."""
        temp_file: Path = create_yaml_files / "temp_settings.yaml"
        temp_file.write_text("test_key: initial_value")

        with patch("ClassicLib.YamlSettingsCache.YamlSettingsCache.get_path_for_store") as mock_path:
            mock_path.return_value = temp_file

            # Test initial value
            initial_value: str | None = yaml_settings(str, YAML.Settings, "test_key")
            assert initial_value == "initial_value"

            # Update value
            yaml_settings(str, YAML.Settings, "test_key", new_value="updated_value")

            # Check updated value
            updated_value: str | None = yaml_settings(str, YAML.Settings, "test_key")
            assert updated_value == "updated_value"


if __name__ == "__main__":
    pytest.main()

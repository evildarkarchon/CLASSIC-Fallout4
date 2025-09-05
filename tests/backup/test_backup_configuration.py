"""
Tests for backup configuration loading and validation.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.BackupManager import BackupManager
from ClassicLib.Constants import YAML


class TestBackupConfiguration:
    """Tests for backup configuration loading."""

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_success(self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager) -> None:
        """Test successful loading of backup configuration."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll", "*.exe", "*.ini"],  # backup_list
            "C:/Games/Fallout4",  # game_path
            "C:/Documents/F4SE/f4se.log",  # xse_log_file
            "0.6.23",  # xse_ver_latest
        ]

        # Load configuration
        manager.load_backup_configuration()

        # Verify configuration was loaded
        assert manager._backup_config["backup_list"] == ["*.dll", "*.exe", "*.ini"]
        assert manager._backup_config["game_path"] == "C:/Games/Fallout4"
        assert manager._backup_config["xse_log_file"] == "C:/Documents/F4SE/f4se.log"
        assert manager._backup_config["xse_ver_latest"] == "0.6.23"

        # Verify yaml_settings was called correctly
        assert mock_yaml_settings.call_count == 4

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_load_backup_configuration_vr_mode(self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager) -> None:
        """Test loading configuration in VR mode."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [["*.dll"], "C:/Games/Fallout4VR", "C:/Documents/F4SEVR/f4sevr.log", "0.1.2"]

        # Load configuration
        manager.load_backup_configuration()

        # Verify VR suffix was used in calls
        calls = mock_yaml_settings.call_args_list
        assert calls[1][0] == (str, YAML.Game_Local, "GameVR_Info.Root_Folder_Game")
        assert calls[2][0] == (str, YAML.Game_Local, "GameVR_Info.Docs_File_XSE")
        assert calls[3][0] == (str, YAML.Game, "GameVR_Info.XSE_Ver_Latest")

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_type_error_list(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when backup_list is not a list."""
        # Setup mock to return non-list for backup_list
        mock_yaml_settings.side_effect = [
            "not_a_list",  # Invalid type for backup_list
            "C:/Games/Fallout4",
            "C:/Documents/F4SE/f4se.log",
            "0.6.23",
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="Backup list must be a list of strings"):
            manager.load_backup_configuration()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_type_error_xse_log(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when xse_log_file is not a string."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll"],
            "C:/Games/Fallout4",
            123,  # Invalid type for xse_log_file
            "0.6.23",
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="XSE log file path must be a string"):
            manager.load_backup_configuration()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_type_error_xse_version(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when xse_ver_latest is not a string."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll"],
            "C:/Games/Fallout4",
            "C:/Documents/F4SE/f4se.log",
            None,  # Invalid type for xse_ver_latest
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="Latest XSE version must be a string"):
            manager.load_backup_configuration()

    @patch("ClassicLib.BackupManager.logger")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_with_logging(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, mock_logger: MagicMock, manager: BackupManager
    ) -> None:
        """Test that load_backup_configuration logs debug message."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [["*.dll"], "C:/Games", "C:/xse.log", "0.6.23"]

        # Load configuration
        manager.load_backup_configuration()

        # Verify debug logging
        mock_logger.debug.assert_called_with("Loaded backup configuration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

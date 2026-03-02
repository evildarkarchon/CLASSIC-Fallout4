"""Tests for backup configuration loading and validation."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.backup import BackupManager

pytestmark = [pytest.mark.unit]


class TestBackupConfiguration:
    """Tests for backup configuration loading."""

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch.object(GlobalRegistry, "is_vr_version", return_value=False)
    def test_load_backup_configuration_success(
        self, mock_is_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test successful loading of backup configuration."""
        mock_version_info = MagicMock()
        mock_version_info.xse.compatible_version = "0.6.23"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll", "*.exe", "*.ini"],  # backup_list
            "C:/Games/Fallout4",  # game_path
            "C:/Documents/F4SE/f4se.log",  # xse_log_file
        ]

        # Load configuration
        manager.load_backup_configuration()

        # Verify configuration was loaded
        assert manager._backup_config["backup_list"] == ["*.dll", "*.exe", "*.ini"]
        assert manager._backup_config["game_path"] == "C:/Games/Fallout4"
        assert manager._backup_config["xse_log_file"] == "C:/Documents/F4SE/f4se.log"
        assert manager._backup_config["xse_ver_latest"] == "0.6.23"

        # Verify xse version came from Version Registry, not YAML key
        mock_registry.get_by_id.assert_called_once_with("FO4_OG")
        assert mock_yaml_settings.call_count == 3

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch.object(GlobalRegistry, "is_vr_version", return_value=True)
    def test_load_backup_configuration_vr_mode(
        self, mock_is_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test loading configuration in VR mode uses VR entry from Version Registry."""
        mock_version_info = MagicMock()
        mock_version_info.xse.compatible_version = "0.1.2"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Setup mock returns
        mock_yaml_settings.side_effect = [["*.dll"], "C:/Games/Fallout4VR", "C:/Documents/F4SEVR/f4sevr.log"]

        # Load configuration
        manager.load_backup_configuration()

        # Verify Game_Info prefix is always used (GameVR_Info was removed)
        calls = mock_yaml_settings.call_args_list
        assert calls[1][0] == (str, YAML.Game_Local, "Game_Info.Root_Folder_Game")
        assert calls[2][0] == (str, YAML.Game_Local, "Game_Info.Docs_File_XSE")
        mock_registry.get_by_id.assert_called_once_with("FO4_VR")

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch.object(GlobalRegistry, "is_vr_version", return_value=False)
    def test_load_backup_configuration_type_error_list(
        self, mock_is_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when backup_list is not a list."""
        mock_version_info = MagicMock()
        mock_version_info.xse.compatible_version = "0.6.23"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Setup mock to return non-list for backup_list
        mock_yaml_settings.side_effect = [
            "not_a_list",  # Invalid type for backup_list
            "C:/Games/Fallout4",
            "C:/Documents/F4SE/f4se.log",
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="Backup list must be a list of strings"):
            manager.load_backup_configuration()

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch.object(GlobalRegistry, "is_vr_version", return_value=False)
    def test_load_backup_configuration_type_error_xse_log(
        self, mock_is_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when xse_log_file is not a string."""
        mock_version_info = MagicMock()
        mock_version_info.xse.compatible_version = "0.6.23"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll"],
            "C:/Games/Fallout4",
            123,  # Invalid type for xse_log_file
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="XSE log file path must be a string"):
            manager.load_backup_configuration()

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch.object(GlobalRegistry, "is_vr_version", return_value=False)
    def test_load_backup_configuration_type_error_xse_version(
        self, mock_is_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when xse_ver_latest is not a string."""
        mock_yaml_settings.side_effect = [
            ["*.dll"],
            "C:/Games/Fallout4",
            "C:/Documents/F4SE/f4se.log",
        ]

        mock_version_info = MagicMock()
        mock_version_info.xse = None
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Should raise TypeError
        with pytest.raises(TypeError, match="Latest XSE version must be a string"):
            manager.load_backup_configuration()

    @patch("ClassicLib.support.backup.logger")
    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch.object(GlobalRegistry, "is_vr_version", return_value=False)
    def test_load_backup_configuration_with_logging(
        self,
        mock_is_vr: MagicMock,
        mock_get_registry: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_logger: MagicMock,
        manager: BackupManager,
    ) -> None:
        """Test that load_backup_configuration logs debug message."""
        mock_version_info = MagicMock()
        mock_version_info.xse.compatible_version = "0.6.23"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Setup mock returns
        mock_yaml_settings.side_effect = [["*.dll"], "C:/Games", "C:/xse.log"]

        # Load configuration
        manager.load_backup_configuration()

        # Verify debug logging
        mock_logger.debug.assert_called_with("Loaded backup configuration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

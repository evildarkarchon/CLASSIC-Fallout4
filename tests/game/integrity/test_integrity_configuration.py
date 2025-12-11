"""Tests for game integrity configuration loading."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.GameIntegrity import GameIntegrityChecker


class TestConfigurationLoading:
    """Tests for configuration loading and validation."""

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_configuration_success(self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, checker: GameIntegrityChecker) -> None:
        """Test successful loading of configuration."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            "C:/Games/Fallout4/steam_api.ini",  # steam_ini_path
            "hash_old",  # exe_hash_old
            "hash_new",  # exe_hash_new
            "C:/Games/Fallout4/Fallout4.exe",  # game_exe_path
            "Fallout4",  # root_name
            "Warning message",  # root_warn
        ]

        # Load configuration
        checker.load_configuration()

        # Verify configuration was loaded
        assert checker._config["steam_ini_path"] == "C:/Games/Fallout4/steam_api.ini"
        assert checker._config["exe_hash_old"] == "hash_old"
        assert checker._config["exe_hash_new"] == "hash_new"
        assert checker._config["game_exe_path"] == "C:/Games/Fallout4/Fallout4.exe"
        assert checker._config["root_name"] == "Fallout4"
        assert checker._config["root_warn"] == "Warning message"

        # Verify yaml_settings was called correctly
        assert mock_yaml_settings.call_count == 6

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_load_configuration_vr_mode(self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, checker: GameIntegrityChecker) -> None:
        """Test loading configuration in VR mode."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            "C:/Games/Fallout4VR/steam_api.ini",
            "hash_old_vr",
            "hash_new_vr",
            "C:/Games/Fallout4VR/Fallout4VR.exe",
            "Fallout4VR",
            "VR Warning",
        ]

        # Load configuration
        checker.load_configuration()

        # Verify VR suffix was used in calls
        calls = mock_yaml_settings.call_args_list
        assert calls[0][0] == (str, YAML.Game_Local, "GameVR_Info.Game_File_SteamINI")
        assert calls[3][0] == (str, YAML.Game_Local, "GameVR_Info.Game_File_EXE")
        assert calls[4][0] == (str, YAML.Game, "GameVR_Info.Main_Root_Name")

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_configuration_type_error(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, checker: GameIntegrityChecker
    ) -> None:
        """Test TypeError when configuration value is not a string."""
        # Setup mock to return non-string value
        mock_yaml_settings.side_effect = [
            "C:/Games/Fallout4/steam_api.ini",
            123,  # Invalid type for exe_hash_old
            "hash_new",
            "C:/Games/Fallout4/Fallout4.exe",
            "Fallout4",
            "Warning",
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="Expected string for exe_hash_old"):
            checker.load_configuration()

    @patch("ClassicLib.GameIntegrity.logger")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_configuration_with_logging(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, mock_logger: MagicMock, checker: GameIntegrityChecker
    ) -> None:
        """Test that load_configuration logs debug message."""
        # Setup mock returns
        mock_yaml_settings.side_effect = ["path1", "hash1", "hash2", "exe", "name", "warn"]

        # Load configuration
        checker.load_configuration()

        # Verify debug logging
        mock_logger.debug.assert_called_with("Loaded game integrity configuration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test suite for ClassicLib/GameIntegrity.py game integrity checking functionality.

This module contains tests for the GameIntegrityChecker class which validates
game installation and file integrity.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.GameIntegrity import GameIntegrityChecker


class TestGameIntegrityChecker:
    """Tests for the GameIntegrityChecker class."""

    @pytest.fixture
    def checker(self) -> GameIntegrityChecker:
        """Create a GameIntegrityChecker instance for testing."""
        return GameIntegrityChecker()

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Create mock configuration for testing."""
        return {
            "steam_ini_path": "C:/Games/Fallout4/steam_api.ini",
            "exe_hash_old": "hash_old_version",
            "exe_hash_new": "hash_new_version",
            "game_exe_path": "C:/Games/Fallout4/Fallout4.exe",
            "root_name": "Fallout4",
            "root_warn": "WARNING: Game installed in Program Files!",
        }

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
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

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
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

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
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

    @patch("ClassicLib.GameIntegrity.calculate_file_hash")
    def test_check_executable_version_latest(
        self, mock_hash: MagicMock, checker: GameIntegrityChecker, mock_config: dict[str, str], tmp_path: Path
    ) -> None:
        """Test checking executable when it's the latest version."""
        # Create fake exe file
        exe_path = tmp_path / "Fallout4.exe"
        exe_path.write_text("fake exe content")

        # Update config with test path
        mock_config["game_exe_path"] = str(exe_path)
        mock_config["steam_ini_path"] = str(tmp_path / "steam_api.ini")
        checker._config = mock_config

        # Mock hash calculation to return new version hash
        mock_hash.return_value = "hash_new_version"

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be valid and have success message
        assert is_valid is True
        assert "✔️ You have the latest version" in message
        assert "Fallout4" in message

    @patch("ClassicLib.GameIntegrity.calculate_file_hash")
    def test_check_executable_version_outdated_with_steam_ini(
        self, mock_hash: MagicMock, checker: GameIntegrityChecker, mock_config: dict[str, str], tmp_path: Path
    ) -> None:
        """Test checking executable when outdated with Steam INI present."""
        # Create fake exe and steam ini files
        exe_path = tmp_path / "Fallout4.exe"
        exe_path.write_text("fake exe content")
        steam_ini = tmp_path / "steam_api.ini"
        steam_ini.write_text("steam config")

        # Update config with test paths
        mock_config["game_exe_path"] = str(exe_path)
        mock_config["steam_ini_path"] = str(steam_ini)
        checker._config = mock_config

        # Mock hash calculation to return outdated hash
        mock_hash.return_value = "hash_outdated"

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid with skull emoji
        assert is_valid is False
        assert "💀 CAUTION" in message
        assert "OUT OF DATE" in message

    @patch("ClassicLib.GameIntegrity.calculate_file_hash")
    def test_check_executable_version_outdated_no_steam_ini(
        self, mock_hash: MagicMock, checker: GameIntegrityChecker, mock_config: dict[str, str], tmp_path: Path
    ) -> None:
        """Test checking executable when outdated without Steam INI."""
        # Create fake exe file (no steam ini)
        exe_path = tmp_path / "Fallout4.exe"
        exe_path.write_text("fake exe content")

        # Update config with test path
        mock_config["game_exe_path"] = str(exe_path)
        mock_config["steam_ini_path"] = str(tmp_path / "steam_api.ini")  # Doesn't exist
        checker._config = mock_config

        # Mock hash calculation to return outdated hash
        mock_hash.return_value = "hash_outdated"

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid with X emoji
        assert is_valid is False
        assert "❌ CAUTION" in message
        assert "OUT OF DATE" in message

    def test_check_executable_version_no_exe(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking executable when exe file doesn't exist."""
        # Set non-existent exe path
        mock_config["game_exe_path"] = "/nonexistent/Fallout4.exe"
        checker._config = mock_config

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid
        assert is_valid is False
        assert message == "Game executable not found"

    def test_check_executable_version_no_path_configured(self, checker: GameIntegrityChecker) -> None:
        """Test checking executable when no path is configured."""
        checker._config = {"game_exe_path": None}

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid
        assert is_valid is False
        assert message == "Game executable not found"

    def test_check_installation_location_good(self, checker: GameIntegrityChecker, mock_config: dict[str, str], tmp_path: Path) -> None:
        """Test checking installation when NOT in Program Files."""
        # Create fake exe in good location
        exe_path = tmp_path / "Games" / "Fallout4" / "Fallout4.exe"
        exe_path.parent.mkdir(parents=True, exist_ok=True)
        exe_path.write_text("fake exe")

        mock_config["game_exe_path"] = str(exe_path)
        checker._config = mock_config

        # Check location
        is_valid, message = checker.check_installation_location()

        # Should be valid
        assert is_valid is True
        assert "✔️" in message
        assert "outside of the Program Files folder" in message

    def test_check_installation_location_bad(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking installation when IN Program Files."""
        # Set exe path in Program Files
        mock_config["game_exe_path"] = "C:/Program Files/Steam/Fallout4/Fallout4.exe"
        checker._config = mock_config

        # Mock file existence check
        with patch("pathlib.Path.is_file", return_value=True):
            # Check location
            is_valid, message = checker.check_installation_location()

        # Should be invalid with warning
        assert is_valid is False
        assert message == "WARNING: Game installed in Program Files!"

    def test_check_installation_location_no_exe(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking installation when exe doesn't exist."""
        mock_config["game_exe_path"] = "/nonexistent/Fallout4.exe"
        checker._config = mock_config

        # Check location
        is_valid, message = checker.check_installation_location()

        # Should return invalid with empty message
        assert is_valid is False
        assert message == ""

    def test_check_installation_location_no_warning_configured(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking installation with no warning message configured."""
        mock_config["game_exe_path"] = "C:/Program Files/Fallout4/Fallout4.exe"
        mock_config["root_warn"] = None
        checker._config = mock_config

        with patch("pathlib.Path.is_file", return_value=True):
            is_valid, message = checker.check_installation_location()

        assert is_valid is False
        assert message == ""

    @patch.object(GameIntegrityChecker, "check_installation_location")
    @patch.object(GameIntegrityChecker, "check_executable_version")
    @patch.object(GameIntegrityChecker, "load_configuration")
    @patch("ClassicLib.GameIntegrity.logger")
    def test_run_full_check_all_messages(
        self,
        mock_logger: MagicMock,
        mock_load: MagicMock,
        mock_check_version: MagicMock,
        mock_check_location: MagicMock,
        checker: GameIntegrityChecker,
    ) -> None:
        """Test running full integrity check with all checks returning messages."""
        # Setup mocks
        mock_check_version.return_value = (True, "Version OK\n")
        mock_check_location.return_value = (True, "Location OK\n")

        # Run full check
        result = checker.run_full_check()

        # Verify all checks were called
        mock_load.assert_called_once()
        mock_check_version.assert_called_once()
        mock_check_location.assert_called_once()

        # Verify result contains both messages
        assert result == "Version OK\nLocation OK\n"

        # Verify logging
        mock_logger.debug.assert_called_with("- - - INITIATED GAME INTEGRITY CHECK")

    @patch.object(GameIntegrityChecker, "check_installation_location")
    @patch.object(GameIntegrityChecker, "check_executable_version")
    def test_run_full_check_no_config(
        self, mock_check_version: MagicMock, mock_check_location: MagicMock, checker: GameIntegrityChecker
    ) -> None:
        """Test running full check loads configuration if not present."""
        # Setup mocks
        mock_check_version.return_value = (False, "Version Bad")
        mock_check_location.return_value = (False, "")

        # Ensure no config is loaded
        assert not checker._config

        with patch.object(checker, "load_configuration") as mock_load:
            # Run full check
            result = checker.run_full_check()

            # Verify configuration was loaded
            mock_load.assert_called_once()

    @patch.object(GameIntegrityChecker, "check_installation_location")
    @patch.object(GameIntegrityChecker, "check_executable_version")
    def test_run_full_check_empty_messages(
        self, mock_check_version: MagicMock, mock_check_location: MagicMock, checker: GameIntegrityChecker
    ) -> None:
        """Test running full check with empty messages."""
        # Setup mocks to return empty messages
        mock_check_version.return_value = (True, "")
        mock_check_location.return_value = (True, "")

        # Set dummy config so load_configuration isn't called
        checker._config = {"dummy": "config"}

        # Run full check
        result = checker.run_full_check()

        # Should return empty string
        assert result == ""

    @patch("ClassicLib.GameIntegrity.logger")
    def test_run_full_check_logging(self, mock_logger: MagicMock, checker: GameIntegrityChecker) -> None:
        """Test that run_full_check logs debug message."""
        # Set dummy config
        checker._config = {"dummy": "config"}

        with patch.object(checker, "check_executable_version", return_value=(True, "")):
            with patch.object(checker, "check_installation_location", return_value=(True, "")):
                checker.run_full_check()

        # Verify debug logging
        mock_logger.debug.assert_called_with("- - - INITIATED GAME INTEGRITY CHECK")

    @patch("ClassicLib.GameIntegrity.logger")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
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

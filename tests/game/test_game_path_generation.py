"""
Test suite for game path generation functionality.

This module contains tests for generating game folder and file paths
based on different game versions (OG, NG, VR).
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib import Constants, GlobalRegistry
from ClassicLib.GamePath import game_generate_paths


class TestGamePathGeneration:
    """Tests for game path generation functionality."""

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_fallout4_og_version(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths for Fallout 4 OG version."""
        game_path = str(tmp_path / "Fallout4")
        # Provide enough values for all yaml_settings calls (read and write operations)
        mock_yaml.side_effect = [
            game_path,  # Root_Folder_Game (read)
            "F4SE",  # XSE_Acronym VR (read)
            "F4SE",  # XSE_Acronym base (read)
            None,  # Game_Folder_Data (write)
            None,  # Game_Folder_Scripts (write)
            None,  # Game_Folder_Plugins (write)
            None,  # Game_File_SteamINI (write)
            None,  # Game_File_EXE (write)
            f"{game_path}\\Fallout4.exe",  # Game_File_EXE (read for version)
            None,  # Game_File_AddressLib (write)
        ]

        mock_get_version.return_value = Constants.OG_VERSION

        game_generate_paths()

        # Should have called yaml_settings multiple times to set various paths
        assert mock_yaml.call_count >= 6  # At least 6 calls for path settings
        mock_get_version.assert_called_once()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_fallout4_ng_version(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths for Fallout 4 NG version."""
        game_path = str(tmp_path / "Fallout4")
        # Provide enough values for all yaml_settings calls
        mock_yaml.side_effect = [
            game_path,  # Root_Folder_Game (read)
            "F4SE",  # XSE_Acronym VR (read)
            "F4SE",  # XSE_Acronym base (read)
            None,  # Game_Folder_Data (write)
            None,  # Game_Folder_Scripts (write)
            None,  # Game_Folder_Plugins (write)
            None,  # Game_File_SteamINI (write)
            None,  # Game_File_EXE (write)
            f"{game_path}\\Fallout4.exe",  # Game_File_EXE (read for version)
            None,  # Game_File_AddressLib (write)
        ]

        mock_get_version.return_value = Constants.NG_VERSION

        game_generate_paths()

        # Should have called yaml_settings multiple times
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_generate_paths_fallout4_vr(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths for Fallout 4 VR."""
        game_path = str(tmp_path / "Fallout4VR")
        # Provide enough values for all yaml_settings calls
        mock_yaml.side_effect = [
            game_path,  # Root_Folder_Game (read)
            "F4SEVR",  # XSE_Acronym VR (read)
            "F4SE",  # XSE_Acronym base (read)
            None,  # Game_Folder_Data (write)
            None,  # Game_Folder_Scripts (write)
            None,  # Game_Folder_Plugins (write)
            None,  # Game_File_SteamINI (write)
            None,  # Game_File_EXE (write)
            f"{game_path}\\Fallout4VR.exe",  # Game_File_EXE (read for version)
            None,  # Game_File_AddressLib (write)
        ]

        mock_get_version.return_value = Version("1.2.72.0")

        game_generate_paths()

        # Should have called yaml_settings for VR-specific AddressLib path
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_unsupported_version(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths with unsupported game version."""
        game_path = str(tmp_path / "Fallout4")
        # Provide enough values for all yaml_settings calls before exception
        mock_yaml.side_effect = [
            game_path,  # Root_Folder_Game (read)
            "F4SE",  # XSE_Acronym VR (read)
            "F4SE",  # XSE_Acronym base (read)
            None,  # Game_Folder_Data (write)
            None,  # Game_Folder_Scripts (write)
            None,  # Game_Folder_Plugins (write)
            None,  # Game_File_SteamINI (write)
            None,  # Game_File_EXE (write)
            f"{game_path}\\Fallout4.exe",  # Game_File_EXE (read for version)
        ]

        # Use an unsupported version
        mock_get_version.return_value = Version("999.999.999.999")

        with pytest.raises(ValueError, match="Unsupported or invalid game version"):
            game_generate_paths()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_missing_game_path(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_yaml: MagicMock
    ) -> None:
        """Test game_generate_paths with missing game path."""
        mock_yaml.return_value = None  # Simulate missing game path

        with pytest.raises(TypeError):
            game_generate_paths()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_missing_xse_acronym(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_yaml: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths with missing XSE acronym."""
        game_path = str(tmp_path / "Fallout4")
        mock_yaml.side_effect = [
            game_path,  # Root_Folder_Game
            "F4SE",  # XSE_Acronym VR
            None,  # XSE_Acronym base - missing
        ]

        with pytest.raises(TypeError):
            game_generate_paths()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

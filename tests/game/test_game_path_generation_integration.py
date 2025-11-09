"""
Integration tests for game_path_generation - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import game_generate_paths

pytestmark = pytest.mark.integration


class TestGamePathGeneration:
    """Tests for game path generation functionality."""

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_generate_paths_fallout4_vr(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths for Fallout 4 VR."""
        game_path = str(tmp_path / "Fallout4VR")
        mock_yaml.side_effect = [game_path, "F4SEVR", "F4SE", None, None, None, None, None, f"{game_path}\\Fallout4VR.exe", None]
        mock_get_version.return_value = Version("1.2.72.0")
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_unsupported_version(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths with unsupported game version."""
        game_path = str(tmp_path / "Fallout4")
        mock_yaml.side_effect = [game_path, "F4SE", "F4SE", None, None, None, None, None, f"{game_path}\\Fallout4.exe"]
        mock_get_version.return_value = Version("999.999.999.999")
        with pytest.raises(ValueError, match="Unsupported or invalid game version"):
            game_generate_paths()

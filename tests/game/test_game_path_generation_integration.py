"""
Integration tests for game_path_generation - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import game_generate_paths

pytestmark = pytest.mark.integration


class TestGamePathGeneration:
    """Tests for game path generation functionality."""

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_generate_paths_fallout4_vr(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        mock_get_registry: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths for Fallout 4 VR."""
        # Mock version registry
        mock_version_info = MagicMock()
        mock_version_info.xse.acronym = "F4SE"
        mock_version_info.address_library.filename = "version-1-2-72-0.csv"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_match_result = MagicMock()
        mock_match_result.should_warn = False
        mock_match_result.version_info = mock_version_info
        mock_registry.match_version.return_value = mock_match_result
        mock_get_registry.return_value = mock_registry

        game_path = str(tmp_path / "Fallout4VR")

        def yaml_side_effect(_type, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if "Game_File_EXE" in key_path:
                if args:
                    return args[0]
                return f"{game_path}\\Fallout4VR.exe"
            return args[0] if args else None

        mock_yaml.side_effect = yaml_side_effect
        mock_get_version.return_value = Version("1.2.72.0")
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

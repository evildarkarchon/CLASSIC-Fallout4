"""
Unit tests for game_path_registry - unit logic testing.

This file contains unit tests for Rust-based game path detection
via the GamePathFinder class.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestGamePathFindWithRustFinder:
    """Tests for game_path_find() with Rust finder."""

    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    def test_game_path_find_uses_rust_finder(self, mock_rust_finder_cls: MagicMock, mock_msg_info: MagicMock, message_handler) -> None:
        """Test that game_path_find uses Rust finder for path detection."""
        # Mock Rust finder to return a valid path
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = "C:/Program Files/Fallout4"
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        with patch("ClassicLib.support.game_path.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.XSE_Acronym": "F4SE",
                "Game_VR_Info.XSE_Acronym": "F4SEVR",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": None,
                "Game_VR_Info.Docs_File_XSE": None,
            }.get(key)
            with patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                    from ClassicLib.support.game_path import game_path_find

                    game_path_find()
                    mock_rust_finder.find_game_path.assert_called_once()

"""
Unit tests for game_path_registry - unit logic testing.

This file contains unit tests for registry-based game path detection.
The implementation uses RustGamePathFinder exclusively.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import _game_path_find_registry

pytestmark = pytest.mark.unit


class TestRegistryDetection:
    """Tests for Rust-based registry game path detection."""

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_not_found(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_rust_finder_cls: MagicMock,
        message_handler,
    ) -> None:
        """Test registry detection when game is not found."""
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = FileNotFoundError("Game not found")
        mock_rust_finder_cls.return_value = mock_rust_finder

        result = _game_path_find_registry("Fallout4.exe")

        assert result is None
        mock_rust_finder_cls.assert_called_once()

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_value_error(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_rust_finder_cls: MagicMock,
        message_handler,
    ) -> None:
        """Test registry detection when path validation fails."""
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = ValueError("Invalid path")
        mock_rust_finder_cls.return_value = mock_rust_finder

        result = _game_path_find_registry("Fallout4.exe")

        assert result is None

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_os_error(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_rust_finder_cls: MagicMock,
        message_handler,
    ) -> None:
        """Test registry detection when OS error occurs."""
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = OSError("Registry access denied")
        mock_rust_finder_cls.return_value = mock_rust_finder

        result = _game_path_find_registry("Fallout4.exe")

        assert result is None


class TestGamePathFindWithRustFinder:
    """Tests for game_path_find() with Rust finder."""

    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    def test_game_path_find_uses_rust_finder(
        self, mock_rust_finder_cls: MagicMock, mock_msg_info: MagicMock, message_handler
    ) -> None:
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

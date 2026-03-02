"""
Unit tests for game_path_validation - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
The implementation uses RustGamePathFinder exclusively.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import game_path_find

pytestmark = pytest.mark.unit


class TestXSELogParsing:
    """Tests for XSE log file parsing to find game path via Rust finder."""

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    def test_game_path_find_missing_xse_file(
        self,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test game path detection when XSE file is missing - prompts for user input."""
        game_path = Path("C:/Games/Fallout4")

        # Rust finder fails to find path via XSE log (forces user input)
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = FileNotFoundError("XSE file not found")
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        mock_path_validator.is_valid_path.return_value = True

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
                with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                    with patch("builtins.input", return_value="C:/Games/Fallout4"):
                        with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                            game_path_find()
                            # Should have used Rust finder
                            mock_rust_finder_cls.assert_called_once()

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    def test_game_path_find_missing_xse_path_config(
        self,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        message_handler,
    ) -> None:
        """Test game path detection when XSE path config is missing."""
        # Rust finder fails (no XSE log configured)
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = FileNotFoundError("No XSE log")
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        mock_path_validator.is_valid_path.return_value = True

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
                with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                    with patch("builtins.input", return_value="C:/Games/Fallout4"):
                        with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                            game_path_find()
                            # Should have used Rust finder
                            mock_rust_finder_cls.assert_called_once()


class TestYAMLValidation:
    """Tests for YAML settings validation and error handling."""

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    def test_game_path_find_invalid_yaml_types(
        self,
        mock_rust_finder_cls: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        message_handler,
    ) -> None:
        """Test game path detection with invalid YAML types raises TypeError."""
        with patch("ClassicLib.support.game_path.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.XSE_Acronym": 123,  # Invalid type - should be string
                "Game_VR_Info.XSE_Acronym": "F4SEVR",
                "Game_Info.Main_Root_Name": None,  # Invalid - should be string
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
            }.get(key)
            with pytest.raises(TypeError):
                game_path_find()

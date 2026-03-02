"""
Integration tests for game_path_validation - integration logic testing.

This file contains integration tests for game path validation and user input.
The implementation uses RustGamePathFinder exclusively.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import game_path_find

pytestmark = pytest.mark.integration


class TestXSELogParsing:
    """Tests for XSE log file parsing to find game path via Rust finder."""

    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path", return_value=None)
    @patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    def test_game_path_find_xse_log_parsing(
        self,
        mock_rust_finder_cls: MagicMock,
        mock_save_cache: MagicMock,
        mock_cached_path: MagicMock,
        mock_msg_info: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game path detection from XSE log file via Rust finder."""
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        (game_dir / "Fallout4.exe").write_text("fake exe")

        xse_log = tmp_path / "f4se.log"
        xse_log.write_text(
            "F4SE runtime: initialize (version = 0.6.21)\nplugin directory = C:/Games/Fallout4/Data/F4SE/Plugins\nLaunching game executable..."
        )

        # Mock Rust finder to return the game path
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = str(game_dir)
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        with patch("ClassicLib.support.game_path.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.XSE_Acronym": "F4SE",
                "Game_VR_Info.XSE_Acronym": "F4SEVR",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": str(xse_log),
                "Game_VR_Info.Docs_File_XSE": str(xse_log),
            }.get(key)

            game_path_find()

            # Verify Rust finder was used
            mock_rust_finder_cls.assert_called_once()


class TestManualPathInput:
    """Tests for manual game path input and validation via Rust finder."""

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("builtins.input", return_value="C:/Games/Fallout4")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    def test_game_path_find_manual_input_success(
        self,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_input: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test manual game path input success when Rust finder fails to find path."""
        game_path = Path("C:/Games/Fallout4")

        # Mock Rust finder to fail initially (forcing user input)
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = FileNotFoundError("Game not found")
        mock_rust_finder.validate_game_path.return_value = None  # Valid path
        mock_rust_finder_cls.return_value = mock_rust_finder

        # Mock PathValidator to accept the path
        mock_path_validator.is_valid_path.return_value = True

        with patch("ClassicLib.support.game_path.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.Docs_File_XSE": None,
                "Game_VR_Info.Docs_File_XSE": None,
                "Game_Info.XSE_Acronym": "F4SE",
                "Game_VR_Info.XSE_Acronym": "F4SEVR",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
            }.get(key)
            with patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                    with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                        game_path_find()
                        mock_input.assert_called()

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("builtins.input", side_effect=["invalid_path", "C:/Games/Fallout4"])
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    def test_game_path_find_manual_input_invalid_path(
        self,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_input: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test manual game path input with invalid path first."""
        # Mock Rust finder to fail initially (forcing user input)
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = FileNotFoundError("Game not found")
        mock_rust_finder.validate_game_path.return_value = None  # Valid on second try
        mock_rust_finder_cls.return_value = mock_rust_finder

        # PathValidator: first call invalid, second call valid
        mock_path_validator.is_valid_path.side_effect = [False, True]

        with patch("ClassicLib.support.game_path.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.Docs_File_XSE": None,
                "Game_VR_Info.Docs_File_XSE": None,
                "Game_Info.XSE_Acronym": "F4SE",
                "Game_VR_Info.XSE_Acronym": "F4SEVR",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
            }.get(key)
            with patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                    with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                        game_path_find()
                        # Should call input twice: first invalid, second valid
                        assert mock_input.call_count == 2
                        # Should have error for invalid path
                        assert mock_msg_error.call_count >= 1

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("builtins.input", side_effect=["C:/Games/NoExe", "C:/Games/Fallout4"])
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    def test_game_path_find_manual_input_no_executable(
        self,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_input: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test manual game path input when executable is missing in first attempt."""
        # Mock Rust finder to fail initially (forcing user input)
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = FileNotFoundError("Game not found")
        # First validate_game_path fails (no exe), second succeeds
        mock_rust_finder.validate_game_path.side_effect = [
            ValueError("Executable not found"),
            None,  # Success
        ]
        mock_rust_finder_cls.return_value = mock_rust_finder

        # PathValidator: both paths exist
        mock_path_validator.is_valid_path.return_value = True

        with patch("ClassicLib.support.game_path.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.Docs_File_XSE": None,
                "Game_VR_Info.Docs_File_XSE": None,
                "Game_Info.XSE_Acronym": "F4SE",
                "Game_VR_Info.XSE_Acronym": "F4SEVR",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
            }.get(key)
            with patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                    with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                        game_path_find()
                        # Should call input twice: first missing exe, second has exe
                        assert mock_input.call_count == 2
                        # Should have error for missing executable
                        assert mock_msg_error.call_count >= 1

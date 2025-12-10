"""
Integration tests for game_path_validation - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import game_path_find

pytestmark = pytest.mark.integration


class TestXSELogParsing:
    """Tests for XSE log file parsing to find game path."""

    @patch("ClassicLib.GamePath.msg_info")
    def test_game_path_find_xse_log_parsing(self, mock_msg_info: MagicMock, tmp_path: Path) -> None:
        """Test game path detection from XSE log file."""
        xse_log = tmp_path / "f4se.log"
        xse_log.write_text(
            "F4SE runtime: initialize (version = 0.6.21)\nplugin directory = C:/Games/Fallout4/Data/F4SE/Plugins\nLaunching game executable..."
        )
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.XSE_Acronym": "f4se",
                "Game_VR_Info.XSE_Acronym": "f4sevr",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": str(xse_log),
                "Game_VR_Info.Docs_File_XSE": str(xse_log),
            }.get(key)
            with patch("ClassicLib.Util.validate_path", return_value=(True, "")):
                with patch("pathlib.Path.is_dir", return_value=True):
                    with patch("pathlib.Path.is_file", return_value=True):
                        game_path_find()


class TestManualPathInput:
    """Tests for manual game path input and validation."""

    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    @patch("builtins.input", return_value="C:/Games/Fallout4")
    def test_game_path_find_manual_input_success(
        self, mock_input: MagicMock, mock_msg_info: MagicMock, mock_msg_error: MagicMock, tmp_path: Path, message_handler
    ) -> None:
        """Test manual game path input success - when XSE log parsing fails to find path."""
        fake_xse_log = tmp_path / "f4se.log"
        # Write XSE log without plugin directory line (so path extraction fails)
        fake_xse_log.write_text("F4SE runtime: initialize (version = 0.6.21)\nNo plugin directory info here\n")
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            yaml_call_count = 0

            def yaml_side_effect(type_hint, store, key, *args):
                nonlocal yaml_call_count
                yaml_call_count += 1
                read_values = {
                    "Game_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_VR_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_Info.XSE_Acronym": "f4se",
                    "Game_VR_Info.XSE_Acronym": "f4sevr",
                    "Game_Info.Main_Root_Name": "Fallout 4",
                    "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                }
                if len(args) > 0:
                    return None
                return read_values.get(key)

            mock_yaml.side_effect = yaml_side_effect
            with patch("ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.ResourceLoader.ResourceLoader.save_path_to_cache"):
                    with patch("ClassicLib.GamePath._game_path_find_registry", return_value=None):
                        with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                            with patch("ClassicLib.Util.validate_path", side_effect=[(True, ""), (True, "")]):
                                with patch("pathlib.Path.is_dir", return_value=True):
                                    with patch("pathlib.Path.is_file", side_effect=[True, False, True]):
                                        with patch("ClassicLib.GamePath.open_file_with_encoding") as mock_open:
                                            # Return log lines without plugin directory info
                                            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                                                "F4SE runtime: initialize (version = 0.6.21)\n",
                                                "No plugin directory info here\n",
                                            ]
                                            game_path_find()
                                            mock_input.assert_called()

    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    @patch("builtins.input", side_effect=["invalid_path", "C:/Games/Fallout4"])
    def test_game_path_find_manual_input_invalid_path(
        self, mock_input: MagicMock, mock_msg_info: MagicMock, mock_msg_error: MagicMock, tmp_path: Path, message_handler
    ) -> None:
        """Test manual game path input with invalid path first."""
        fake_xse_log = tmp_path / "f4se.log"
        # Write XSE log without plugin directory info
        fake_xse_log.write_text("F4SE runtime: initialize (version = 0.6.21)\nNo plugin directory info here\n")
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            yaml_call_count = 0

            def yaml_side_effect(type_hint, store, key, *args) -> str | None:
                nonlocal yaml_call_count
                yaml_call_count += 1
                read_values = {
                    "Game_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_VR_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_Info.XSE_Acronym": "f4se",
                    "Game_VR_Info.XSE_Acronym": "f4sevr",
                    "Game_Info.Main_Root_Name": "Fallout 4",
                    "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                }
                if len(args) > 0:
                    return None
                return read_values.get(key)

            mock_yaml.side_effect = yaml_side_effect
            with patch("ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.ResourceLoader.ResourceLoader.save_path_to_cache"):
                    with patch("ClassicLib.GamePath._game_path_find_registry", return_value=None):
                        with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                            with patch(
                                "ClassicLib.Util.validate_path", side_effect=[(True, ""), (False, "Path does not exist"), (True, "")]
                            ):
                                with patch("pathlib.Path.is_dir", side_effect=[True, False, True]):
                                    with patch("pathlib.Path.is_file", side_effect=[True, False, True]):
                                        with patch("ClassicLib.GamePath.open_file_with_encoding") as mock_open:
                                            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                                                "F4SE runtime: initialize (version = 0.6.21)\n",
                                                "No plugin directory info here\n",
                                            ]
                                            game_path_find()
                                            # Should call input twice: first invalid, second valid
                                            assert mock_input.call_count == 2
                                            # Should have error for invalid path
                                            assert mock_msg_error.call_count >= 1

    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    @patch("builtins.input", side_effect=["C:/Games/Fallout4", "C:/Games/Fallout4WithExe"])
    def test_game_path_find_manual_input_no_executable(
        self, mock_input: MagicMock, mock_msg_info: MagicMock, mock_msg_error: MagicMock, tmp_path: Path, message_handler
    ) -> None:
        """Test manual game path input when executable is missing in first attempt."""
        fake_xse_log = tmp_path / "f4se.log"
        # Write XSE log without plugin directory info
        fake_xse_log.write_text("F4SE runtime: initialize (version = 0.6.21)\nNo plugin directory info here\n")
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            yaml_call_count = 0

            def yaml_side_effect(type_hint, store, key, *args) -> str | None:
                nonlocal yaml_call_count
                yaml_call_count += 1
                read_values = {
                    "Game_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_VR_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_Info.XSE_Acronym": "f4se",
                    "Game_VR_Info.XSE_Acronym": "f4sevr",
                    "Game_Info.Main_Root_Name": "Fallout 4",
                    "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                }
                if len(args) > 0:
                    return None
                return read_values.get(key)

            mock_yaml.side_effect = yaml_side_effect
            with patch("ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.ResourceLoader.ResourceLoader.save_path_to_cache"):
                    with patch("ClassicLib.GamePath._game_path_find_registry", return_value=None):
                        with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):
                            with patch("ClassicLib.Util.validate_path", side_effect=[(True, ""), (True, ""), (True, "")]):
                                with patch("pathlib.Path.is_dir", return_value=True):
                                    # First: XSE file exists, then check exe (doesn't exist), then check exe again (exists)
                                    with patch("pathlib.Path.is_file", side_effect=[True, False, True]):
                                        with patch("pathlib.Path.joinpath") as mock_join:
                                            # Create mock Path objects for the exe checks
                                            exe_path_mock1 = MagicMock()
                                            exe_path_mock1.is_file.return_value = False  # First path doesn't have exe
                                            exe_path_mock2 = MagicMock()
                                            exe_path_mock2.is_file.return_value = True  # Second path has exe

                                            joinpath_call_count = 0

                                            def joinpath_side_effect(filename):
                                                nonlocal joinpath_call_count
                                                if filename == "Fallout4.exe":
                                                    # Return different mock for each call
                                                    joinpath_call_count += 1
                                                    if joinpath_call_count == 1:
                                                        return exe_path_mock1
                                                    return exe_path_mock2
                                                return MagicMock()

                                            mock_join.side_effect = joinpath_side_effect

                                            with patch("ClassicLib.GamePath.open_file_with_encoding") as mock_open:
                                                mock_open.return_value.__enter__.return_value.readlines.return_value = [
                                                    "F4SE runtime: initialize (version = 0.6.21)\n",
                                                    "No plugin directory info here\n",
                                                ]
                                                game_path_find()
                                                # Should call input twice: first missing exe, second has exe
                                                assert mock_input.call_count == 2
                                                # Should have error for missing executable
                                                assert mock_msg_error.call_count >= 1

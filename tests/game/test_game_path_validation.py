"""
Test suite for game path validation and user input functionality.

This module contains tests for XSE log parsing, manual path input,
path validation, and error handling.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import game_path_find


class TestXSELogParsing:
    """Tests for XSE log file parsing to find game path."""

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_info")
    def test_game_path_find_xse_log_parsing(
        self,
        mock_msg_info: MagicMock,  # noqa: ARG002
        tmp_path: Path
    ) -> None:
        """Test game path detection from XSE log file."""
        # Create a mock XSE log file
        xse_log = tmp_path / "f4se.log"
        xse_log.write_text(
            "F4SE runtime: initialize (version = 0.6.21)\n"
            "plugin directory = C:/Games/Fallout4/Data/F4SE/Plugins\n"
            "Launching game executable..."
        )

        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {  # noqa: ARG005
                "Game_Info.XSE_Acronym": "f4se",
                "Game_VR_Info.XSE_Acronym": "f4sevr",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": str(xse_log),
                "Game_VR_Info.Docs_File_XSE": str(xse_log),
            }.get(key)

            with patch("ClassicLib.Util.validate_path", return_value=(True, "")):  # noqa: SIM117
                with patch("pathlib.Path.is_dir", return_value=True):
                    with patch("pathlib.Path.is_file", return_value=True):
                        game_path_find()

                        # Should parse the log file for plugin directory

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    def test_game_path_find_missing_xse_file(
        self,
        mock_msg_info: MagicMock,  # noqa: ARG002
        mock_msg_error: MagicMock,
        tmp_path: Path  # noqa: ARG002
    ) -> None:
        """Test game path detection when XSE file is missing."""
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {  # noqa: ARG005
                "Game_Info.XSE_Acronym": "f4se",
                "Game_VR_Info.XSE_Acronym": "f4sevr",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": None,  # Missing XSE file path
                "Game_VR_Info.Docs_File_XSE": None,
            }.get(key)

            game_path_find()

            # Should show error message for missing XSE file
            mock_msg_error.assert_called()

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    def test_game_path_find_missing_xse_path_config(
        self,
        mock_msg_info: MagicMock,  # noqa: ARG002
        mock_msg_error: MagicMock
    ) -> None:
        """Test game path detection when XSE path config is missing."""
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            # Mock missing XSE path configuration but provide required string values
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {  # noqa: ARG005
                "Game_Info.XSE_Acronym": "f4se",
                "Game_VR_Info.XSE_Acronym": "f4sevr",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": None,  # Missing XSE file path
                "Game_VR_Info.Docs_File_XSE": None,
            }.get(key)

            game_path_find()

            # Should show error message for missing XSE file config
            mock_msg_error.assert_called()


class TestManualPathInput:
    """Tests for manual game path input and validation."""

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    @patch("builtins.input", return_value="C:/Games/Fallout4")
    def test_game_path_find_manual_input_success(
        self,
        mock_input: MagicMock,
        mock_msg_info: MagicMock,  # noqa: ARG002
        mock_msg_error: MagicMock,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        """Test manual game path input success."""
        # Create a fake XSE log file that will be parsed but won't have plugin directory
        fake_xse_log = tmp_path / "f4se.log"
        fake_xse_log.write_text("F4SE runtime: initialize (version = 0.6.21)\nSome other log content\n")

        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            # Mock YAML calls to handle both read and write operations
            yaml_call_count = 0

            def yaml_side_effect(type_hint, store, key, *args):  # noqa: ANN001, ANN002, ANN202, ARG001
                nonlocal yaml_call_count
                yaml_call_count += 1

                # Handle read operations
                read_values = {
                    "Game_Info.Docs_File_XSE": str(fake_xse_log),  # Valid XSE file path
                    "Game_VR_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_Info.XSE_Acronym": "f4se",
                    "Game_VR_Info.XSE_Acronym": "f4sevr",
                    "Game_Info.Main_Root_Name": "Fallout 4",
                    "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                }

                # If it's a write operation (has 4th argument), return None
                if len(args) > 0:
                    return None

                # Otherwise it's a read operation
                return read_values.get(key)

            mock_yaml.side_effect = yaml_side_effect

            with patch("ClassicLib.GamePath._game_path_find_registry", return_value=None):  # Registry fails  # noqa: SIM117
                with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):  # Force CLI mode
                    with patch("ClassicLib.Util.validate_path", side_effect=[(True, ""), (True, "")]):  # XSE file valid, input path valid
                        with patch("pathlib.Path.is_dir", return_value=True):
                            with patch("pathlib.Path.is_file", return_value=True):
                                with patch("ClassicLib.GamePath.open_file_with_encoding") as mock_open:
                                    # Mock XSE log content without plugin directory line
                                    mock_open.return_value.__enter__.return_value.readlines.return_value = [
                                        "F4SE runtime: initialize (version = 0.6.21)\n",
                                        "Some other log content\n",
                                    ]

                                    game_path_find()

                                    # Should call input and accept valid path
                                    mock_input.assert_called()

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    @patch("builtins.input", side_effect=["invalid_path", "C:/Games/Fallout4"])
    def test_game_path_find_manual_input_invalid_path(
        self,
        mock_input: MagicMock,
        mock_msg_info: MagicMock,  # noqa: ARG002
        mock_msg_error: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test manual game path input with invalid path first."""
        # Create a fake XSE log file that will be parsed but won't have plugin directory
        fake_xse_log = tmp_path / "f4se.log"
        fake_xse_log.write_text("F4SE runtime: initialize (version = 0.6.21)\nSome other log content\n")

        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            # Mock YAML calls to handle both read and write operations
            yaml_call_count = 0

            def yaml_side_effect(type_hint, store, key, *args) -> str | None:  # noqa: ANN001, ANN002, ARG001
                nonlocal yaml_call_count
                yaml_call_count += 1

                # Handle read operations
                read_values = {
                    "Game_Info.Docs_File_XSE": str(fake_xse_log),  # Valid XSE file path
                    "Game_VR_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_Info.XSE_Acronym": "f4se",
                    "Game_VR_Info.XSE_Acronym": "f4sevr",
                    "Game_Info.Main_Root_Name": "Fallout 4",
                    "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                }

                # If it's a write operation (has 4th argument), return None
                if len(args) > 0:
                    return None

                # Otherwise it's a read operation
                return read_values.get(key)

            mock_yaml.side_effect = yaml_side_effect

            with patch("ClassicLib.GamePath._game_path_find_registry", return_value=None):  # Registry fails  # noqa: SIM117
                with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):  # Force CLI mode
                    with patch("ClassicLib.Util.validate_path", side_effect=[(True, ""), (False, "Path does not exist"), (True, "")]):
                        with patch("pathlib.Path.is_dir", side_effect=[False, True]):  # First invalid, then valid
                            with patch("pathlib.Path.is_file", return_value=True):
                                with patch("ClassicLib.GamePath.open_file_with_encoding") as mock_open:
                                    # Mock XSE log content without plugin directory line
                                    mock_open.return_value.__enter__.return_value.readlines.return_value = [
                                        "F4SE runtime: initialize (version = 0.6.21)\n",
                                        "Some other log content\n",
                                    ]

                                    game_path_find()

                                    # Should call input twice and show error
                                    assert mock_input.call_count == 2
                                    assert mock_msg_error.call_count >= 1

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    @patch("builtins.input", side_effect=["C:/Games/Fallout4", "C:/Games/Fallout4"])
    def test_game_path_find_manual_input_no_executable(
        self,
        mock_input: MagicMock,
        mock_msg_info: MagicMock,  # noqa: ARG002
        mock_msg_error: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test manual game path input when executable is missing."""
        # Create a fake XSE log file that will be parsed but won't have plugin directory
        fake_xse_log = tmp_path / "f4se.log"
        fake_xse_log.write_text("F4SE runtime: initialize (version = 0.6.21)\nSome other log content\n")

        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            # Mock YAML calls to handle both read and write operations
            yaml_call_count = 0

            def yaml_side_effect(type_hint, store, key, *args) -> str | None:  # noqa: ANN001, ANN002, ARG001
                nonlocal yaml_call_count
                yaml_call_count += 1

                # Handle read operations
                read_values = {
                    "Game_Info.Docs_File_XSE": str(fake_xse_log),  # Valid XSE file path
                    "Game_VR_Info.Docs_File_XSE": str(fake_xse_log),
                    "Game_Info.XSE_Acronym": "f4se",
                    "Game_VR_Info.XSE_Acronym": "f4sevr",
                    "Game_Info.Main_Root_Name": "Fallout 4",
                    "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                }

                # If it's a write operation (has 4th argument), return None
                if len(args) > 0:
                    return None

                # Otherwise it's a read operation
                return read_values.get(key)

            mock_yaml.side_effect = yaml_side_effect

            with patch("ClassicLib.GamePath._game_path_find_registry", return_value=None):  # Registry fails  # noqa: SIM117
                with patch.object(GlobalRegistry, "is_gui_mode", return_value=False):  # Force CLI mode
                    with patch("ClassicLib.Util.validate_path", side_effect=[(True, ""), (True, ""), (True, "")]):
                        with patch("pathlib.Path.is_dir", return_value=True):
                            with patch("pathlib.Path.is_file", side_effect=[False, True]):  # First no exe, then valid
                                with patch("ClassicLib.GamePath.open_file_with_encoding") as mock_open:
                                    # Mock XSE log content without plugin directory line
                                    mock_open.return_value.__enter__.return_value.readlines.return_value = [
                                        "F4SE runtime: initialize (version = 0.6.21)\n",
                                        "Some other log content\n",
                                    ]

                                    game_path_find()

                                    # Should call input twice and show error
                                    assert mock_input.call_count == 2
                                    assert mock_msg_error.call_count >= 1


class TestYAMLValidation:
    """Tests for YAML settings validation and error handling."""

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    def test_game_path_find_invalid_yaml_types(
        self,
        mock_msg_info: MagicMock,  # noqa: ARG002
        mock_msg_error: MagicMock  # noqa: ARG002
    ) -> None:
        """Test game path detection with invalid YAML types."""
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            # Mock invalid YAML types - this should trigger TypeError
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {  # noqa: ARG005
                "Game_Info.XSE_Acronym": 123,  # Invalid type (should be string)
                "Game_VR_Info.XSE_Acronym": "f4sevr",
                "Game_Info.Main_Root_Name": None,  # Invalid type (should be string)
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
            }.get(key)

            # Should raise TypeError due to invalid types
            with pytest.raises(TypeError):
                game_path_find()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

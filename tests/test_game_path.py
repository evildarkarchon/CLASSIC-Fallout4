"""
Test suite for ClassicLib/GamePath.py game path detection.

This module contains tests for game path detection functionality,
including registry-based detection, Steam library scanning, and path validation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib import Constants, GlobalRegistry
from ClassicLib.GamePath import (
    _game_path_find_registry,
    game_generate_paths,
    game_path_find,
)


class TestGamePathDetection:
    """Tests for game path detection functionality."""

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    @patch("winreg.CloseKey")
    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "register")
    def test_registry_detection_bethesda_success(  # noqa: PLR0913
        self,
        mock_register: MagicMock,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_yaml: MagicMock,
        mock_close: MagicMock,
        mock_query: MagicMock,
        mock_open: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful registry detection via Bethesda key."""
        # Create a fake game directory with executable
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        (game_dir / "Fallout4.exe").write_text("fake exe")

        # Mock registry calls
        mock_query.return_value = (str(game_dir), None)

        result = _game_path_find_registry("Fallout4.exe")

        assert result == game_dir
        mock_open.assert_called_once()
        mock_query.assert_called_once_with(mock_open.return_value, "installed path")
        mock_close.assert_called_once()
        mock_yaml.assert_called_once()
        mock_register.assert_called_once_with(GlobalRegistry.Keys.GAME_PATH, game_dir)

    @patch("winreg.OpenKey", side_effect=[FileNotFoundError, MagicMock()])
    @patch("winreg.QueryValueEx")
    @patch("winreg.CloseKey")
    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "register")
    def test_registry_detection_gog_fallback_success(  # noqa: PLR0913
        self,
        mock_register: MagicMock,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_yaml: MagicMock,
        mock_close: MagicMock,  # noqa: ARG002
        mock_query: MagicMock,
        mock_open: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful registry detection via GOG key fallback."""
        # Create a fake game directory with executable
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        (game_dir / "Fallout4.exe").write_text("fake exe")

        # Mock registry calls - Bethesda fails, GOG succeeds
        mock_query.return_value = (str(game_dir), None)

        result = _game_path_find_registry("Fallout4.exe")

        assert result == game_dir
        # Should have called OpenKey twice - first Bethesda (fails), then GOG (succeeds)
        assert mock_open.call_count == 2
        mock_yaml.assert_called_once()
        mock_register.assert_called_once_with(GlobalRegistry.Keys.GAME_PATH, game_dir)

    @patch("winreg.OpenKey", side_effect=FileNotFoundError)
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_both_keys_fail(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_open: MagicMock) -> None:  # noqa: ARG002
        """Test registry detection when both Bethesda and GOG keys fail."""
        result = _game_path_find_registry("Fallout4.exe")

        assert result is None
        # Should have tried both registry keys
        assert mock_open.call_count == 2

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    @patch("winreg.CloseKey")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_invalid_path(  # noqa: PLR0913
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_close: MagicMock,
        mock_query: MagicMock,
        mock_open: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test registry detection with path that doesn't contain game executable."""
        # Create directory without the executable
        game_dir = tmp_path / "InvalidGame"
        game_dir.mkdir()

        mock_query.return_value = (str(game_dir), None)

        result = _game_path_find_registry("Fallout4.exe")

        assert result is None
        mock_open.assert_called_once()
        mock_query.assert_called_once()
        mock_close.assert_called_once()

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx", return_value=(None, None))
    @patch("winreg.CloseKey")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_null_path(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_close: MagicMock,  # noqa: ARG002
        mock_query: MagicMock,  # noqa: ARG002
        mock_open: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test registry detection with null path value."""
        result = _game_path_find_registry("Fallout4.exe")

        assert result is None

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_info")
    @patch("platform.system", return_value="Windows")
    def test_game_path_find_windows_registry_success(self, mock_platform: MagicMock, mock_msg_info: MagicMock) -> None:  # noqa: ARG002
        """Test successful Windows registry-based game path detection."""
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            # Mock YAML settings to return required string values to avoid TypeError
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {  # noqa: ARG005
                "Game_Info.XSE_Acronym": "f4se",
                "Game_VR_Info.XSE_Acronym": "f4sevr",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": None,  # Set to None to skip XSE file reading and use registry
                "Game_VR_Info.Docs_File_XSE": None,
            }.get(key)

            with patch("ClassicLib.GamePath._game_path_find_registry") as mock_registry:
                # Mock registry function to return a valid path (simulates successful registry detection)
                mock_registry.return_value = Path("C:/Program Files/Fallout4")

                game_path_find()

                # Verify registry detection was called
                mock_registry.assert_called_once_with("Fallout4.exe")

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_info")
    def test_game_path_find_xse_log_parsing(self, mock_msg_info: MagicMock, tmp_path: Path) -> None:  # noqa: ARG002
        """Test game path detection from XSE log file."""
        # Create a mock XSE log file
        xse_log = tmp_path / "f4se.log"
        xse_log.write_text(
            "F4SE runtime: initialize (version = 0.6.21)\nplugin directory = C:/Games/Fallout4/Data/F4SE/Plugins\nLaunching game executable..."
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
    def test_game_path_find_missing_xse_file(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock, tmp_path: Path) -> None:  # noqa: ARG002
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
    def test_game_path_find_missing_xse_path_config(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock) -> None:  # noqa: ARG002
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

    @pytest.mark.usefixtures("init_message_handler_fixture")
    @patch("ClassicLib.GamePath.msg_error")
    @patch("ClassicLib.GamePath.msg_info")
    def test_game_path_find_invalid_yaml_types(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock) -> None:  # noqa: ARG002
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
    def test_generate_paths_missing_game_path(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock) -> None:  # noqa: ARG002
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


class TestMultiPlatformSupport:
    """Tests for cross-platform compatibility."""

    @patch("platform.system", return_value="Linux")
    @patch("ClassicLib.GamePath._game_path_find_registry")
    def test_linux_skips_registry(self, mock_registry: MagicMock, mock_platform: MagicMock) -> None:  # noqa: ARG002
        """Test that Linux systems skip Windows registry detection."""
        # Mock other dependencies to focus on the platform check
        with patch("ClassicLib.GamePath.yaml_settings", side_effect=[None, "F4SE", "F4SE", "Fallout 4"]):  # noqa: SIM117
            with patch("ClassicLib.Util.validate_path", return_value=(False, "Missing file")):
                with patch.object(GlobalRegistry, "is_gui_mode", return_value=True):
                    with patch("CLASSIC_Interface.show_game_path_dialog_static", return_value=Path("/fake/path")):
                        game_path_find()

        # Registry function should not be called on Linux
        mock_registry.assert_not_called()

    @patch("platform.system", return_value="Windows")
    @patch("ClassicLib.GamePath._game_path_find_registry", return_value=None)
    def test_windows_uses_registry(self, mock_registry: MagicMock, mock_platform: MagicMock) -> None:  # noqa: ARG002
        """Test that Windows systems use registry detection."""
        # Mock other dependencies to focus on the platform check
        with patch("ClassicLib.GamePath.yaml_settings", side_effect=[None, "F4SE", "F4SE", "Fallout 4"]):  # noqa: SIM117
            with patch("ClassicLib.Util.validate_path", return_value=(False, "Missing file")):
                with patch.object(GlobalRegistry, "is_gui_mode", return_value=True):
                    with patch("CLASSIC_Interface.show_game_path_dialog_static", return_value=Path("/fake/path")):
                        game_path_find()

        # Registry function should be called on Windows
        mock_registry.assert_called_once_with("Fallout4.exe")


if __name__ == "__main__":
    pytest.main()

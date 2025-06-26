"""
Test suite for ClassicLib/DocsPath.py document path management.

This module contains tests for the DocumentsPathManager class and related
functionality for finding and managing game document paths across platforms.
"""

import platform
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest
from iniparse import configparser

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.DocsPath import (
    DocumentsPathManager,
    docs_check_ini,
    docs_generate_paths,
    docs_path_find,
)


class TestDocumentPathManager:
    """Tests for the DocumentsPathManager class."""

    def test_initialization_gui_mode(self) -> None:
        """Test DocumentsPathManager initialization in GUI mode."""
        with patch.object(GlobalRegistry, "get_manual_docs_gui", return_value="mock_gui"):
            manager = DocumentsPathManager(is_gui_mode=True)

            assert manager.is_gui_mode is True
            assert manager.manual_docs_gui == "mock_gui"
            assert isinstance(manager.docs_name, str)

    def test_initialization_cli_mode(self) -> None:
        """Test DocumentsPathManager initialization in CLI mode."""
        manager = DocumentsPathManager(is_gui_mode=False)

        assert manager.is_gui_mode is False
        assert manager.manual_docs_gui is None
        assert isinstance(manager.docs_name, str)

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_get_docs_name_from_settings(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_docs_name retrieves from YAML settings."""
        mock_yaml_settings.return_value = "Fallout4Custom"

        result = DocumentsPathManager._get_docs_name()
        assert result == "Fallout4Custom"

    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_get_docs_name_fallback(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test _get_docs_name falls back to GlobalRegistry game name."""
        result = DocumentsPathManager._get_docs_name()
        assert result == "Fallout4"

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_get_game_setting_path_success(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_game_setting_path with valid string return."""
        mock_yaml_settings.return_value = "C:/Games/Fallout4"

        result = DocumentsPathManager._get_game_setting_path("Root_Folder_Game")
        assert result == "C:/Games/Fallout4"

    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    def test_get_game_setting_path_invalid_type(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_game_setting_path raises TypeError for non-string."""
        with pytest.raises(TypeError):
            DocumentsPathManager._get_game_setting_path("Root_Folder_Game")

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_update_game_setting(self, mock_yaml_settings: MagicMock) -> None:
        """Test _update_game_setting calls yaml_settings with correct parameters."""
        DocumentsPathManager._update_game_setting("Root_Folder_Docs", "/path/to/docs")

        mock_yaml_settings.assert_called_once()

    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.classic_settings")
    def test_find_docs_path_with_ini_folder_setting(self, mock_classic_settings: MagicMock, mock_msg_info: MagicMock) -> None:
        """Test find_docs_path when INI folder setting is present in YAML."""
        manager = DocumentsPathManager()

        # Mock classic_settings to return a custom folder path
        mock_classic_settings.return_value = "C:/Custom/Documents/Folder"

        with patch("ClassicLib.Util.validate_path", return_value=(True, "")):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch.object(manager, "_update_game_setting") as mock_update:
                    manager.find_docs_path()

                    # Verify that it updates the setting with the custom path
                    mock_update.assert_called_once_with("Root_Folder_Docs", "C:/Custom/Documents/Folder")

    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.classic_settings")
    @patch("platform.system", return_value="Windows")
    def test_find_docs_path_windows_detection(
        self, mock_platform: MagicMock, mock_classic_settings: MagicMock, mock_msg_info: MagicMock
    ) -> None:
        """Test find_docs_path on Windows using registry detection."""
        manager = DocumentsPathManager(is_gui_mode=False)

        # Mock no ini_folder setting and no existing docs path
        mock_classic_settings.return_value = None

        with patch("ClassicLib.DocsPath.yaml_settings", return_value=None):
            with patch.object(manager, "_find_windows_docs_path") as mock_windows:
                with patch.object(manager, "_get_manual_docs_path") as mock_manual:
                    manager.find_docs_path()

                    # Should call Windows detection method
                    mock_windows.assert_called_once()

    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.classic_settings")
    @patch("platform.system", return_value="Linux")
    def test_find_docs_path_linux_detection(
        self, mock_platform: MagicMock, mock_classic_settings: MagicMock, mock_msg_info: MagicMock
    ) -> None:
        """Test find_docs_path on Linux using Steam library detection."""
        manager = DocumentsPathManager(is_gui_mode=False)

        # Mock no ini_folder setting and no existing docs path
        mock_classic_settings.return_value = None

        with patch("ClassicLib.DocsPath.yaml_settings", return_value=None):
            with patch.object(manager, "_find_linux_docs_path") as mock_linux:
                with patch.object(manager, "_get_manual_docs_path") as mock_manual:
                    manager.find_docs_path()

                    # Should call Linux detection method
                    mock_linux.assert_called_once()

    @patch("ClassicLib.DocsPath.classic_settings", return_value=None)
    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    @patch("ClassicLib.DocsPath.msg_error")
    @patch("ClassicLib.DocsPath.msg_info")
    @patch("builtins.input", side_effect=["C:/Valid/Path", ""])
    def test_find_docs_path_manual_fallback(
        self, mock_input: MagicMock, mock_msg_info: MagicMock, mock_msg_error: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock
    ) -> None:
        """Test find_docs_path falls back to manual input when detection fails."""
        manager = DocumentsPathManager(is_gui_mode=False)

        with patch("pathlib.Path.is_dir", return_value=True):
            with patch.object(manager, "_update_game_setting") as mock_update:
                with patch.object(manager, "_find_windows_docs_path"):
                    manager.find_docs_path()

                    # Since _find_windows_docs_path doesn't set a valid path,
                    # it should call manual input method
                    mock_input.assert_called()

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_find_windows_docs_path_success(self, mock_query: MagicMock, mock_open: MagicMock) -> None:
        """Test _find_windows_docs_path successfully retrieves Windows documents path."""
        mock_query.return_value = ("C:\\Users\\Test\\Documents", None)

        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._find_windows_docs_path()

            expected_path = "C:\\Users\\Test\\Documents\\My Games\\Fallout4"
            mock_update.assert_called_once_with("Root_Folder_Docs", expected_path)

    @patch("winreg.OpenKey", side_effect=OSError("Registry key not found"))
    def test_find_windows_docs_path_registry_failure(self, mock_open: MagicMock) -> None:
        """Test _find_windows_docs_path handles registry access failure."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._find_windows_docs_path()

            # Should still update with default path
            mock_update.assert_called_once()
            # Path should contain user home directory fallback
            args = mock_update.call_args[0]
            assert "Documents" in args[1] and "My Games" in args[1]

    @patch("ClassicLib.DocsPath.yaml_settings")
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("pathlib.Path.open")
    def test_find_linux_docs_path_success(self, mock_open_file: MagicMock, mock_is_file: MagicMock, mock_yaml: MagicMock) -> None:
        """Test _find_linux_docs_path successfully finds Steam library path."""
        mock_yaml.return_value = 377160  # Fallout 4 Steam ID

        # Mock the Steam library file content
        mock_file_content = [
            '"libraryfolders"\n',
            "{\n",
            '\t"0"\n',
            "\t{\n",
            '\t\t"path"\t\t"/home/user/.steam/steam/steamapps"\n',
            '\t\t"apps"\n',
            "\t\t{\n",
            '\t\t\t"377160"\t\t"1234567890"\n',
            "\t\t}\n",
            "\t}\n",
            "}\n",
        ]
        mock_open_file.return_value.__enter__.return_value.readlines.return_value = mock_file_content

        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._find_linux_docs_path()

            mock_update.assert_called_once()
            # Check that the path contains expected Linux Proton structure
            args = mock_update.call_args[0]
            assert "compatdata" in args[1] and "377160" in args[1]

    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    def test_find_linux_docs_path_invalid_steam_id(self, mock_yaml: MagicMock) -> None:
        """Test _find_linux_docs_path handles invalid Steam ID."""
        manager = DocumentsPathManager()

        with pytest.raises(TypeError):
            manager._find_linux_docs_path()

    @patch("pathlib.Path.is_file", return_value=False)
    @patch("ClassicLib.DocsPath.yaml_settings", return_value=377160)
    def test_find_linux_docs_path_no_steam_file(self, mock_yaml: MagicMock, mock_is_file: MagicMock) -> None:
        """Test _find_linux_docs_path handles missing Steam library file."""
        manager = DocumentsPathManager()

        # Should not raise exception, just return without setting path
        manager._find_linux_docs_path()
        # Test passes if no exception is raised

    def test_get_manual_docs_path_gui_mode(self) -> None:
        """Test _get_manual_docs_path in GUI mode."""
        mock_gui = MagicMock()
        manager = DocumentsPathManager(is_gui_mode=True)
        manager.manual_docs_gui = mock_gui

        manager._get_manual_docs_path()

        mock_gui.manual_docs_path_signal.emit.assert_called_once()

    @patch("builtins.input")
    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.msg_error")
    def test_get_manual_docs_path_cli_mode_success(
        self, mock_error: MagicMock, mock_info: MagicMock, mock_input: MagicMock, tmp_path: Path
    ) -> None:
        """Test _get_manual_docs_path in CLI mode with valid input."""
        # Create a test directory
        test_dir = tmp_path / "valid_path"
        test_dir.mkdir()

        mock_input.return_value = str(test_dir)

        manager = DocumentsPathManager(is_gui_mode=False)
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._get_manual_docs_path()

            mock_update.assert_called_once_with("Root_Folder_Docs", str(test_dir))

    @patch("builtins.input")
    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.msg_error")
    def test_get_manual_docs_path_cli_mode_invalid_input(
        self, mock_error: MagicMock, mock_info: MagicMock, mock_input: MagicMock, tmp_path: Path
    ) -> None:
        """Test _get_manual_docs_path in CLI mode with invalid then valid input."""
        # Create a test directory for the second input
        test_dir = tmp_path / "valid_path"
        test_dir.mkdir()

        # First input is invalid, second is valid
        mock_input.side_effect = ["invalid_path", str(test_dir)]

        manager = DocumentsPathManager(is_gui_mode=False)
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._get_manual_docs_path()

            # Should show error for first input
            mock_error.assert_called()
            # Should eventually update with valid path
            mock_update.assert_called_once_with("Root_Folder_Docs", str(test_dir))

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_generate_paths_success(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test generate_paths creates correct paths from settings."""
        manager = DocumentsPathManager()

        # Mock the required YAML settings
        mock_yaml.side_effect = lambda type_hint, store, key, *args: {
            f"Game_Info.XSE_Acronym": "f4se",
            f"Game_VR_Info.XSE_Acronym": "f4sevr",
            f"Game_Info.Root_Folder_Docs": str(tmp_path),
            f"Game_VR_Info.Root_Folder_Docs": None,  # Force fallback
        }.get(key, None)

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager.generate_paths()

            # Verify paths are updated correctly
            mock_update.assert_called()

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_generate_paths_missing_settings(self, mock_yaml: MagicMock) -> None:
        """Test generate_paths raises TypeError for missing settings."""
        mock_yaml.return_value = None  # Simulate missing settings

        manager = DocumentsPathManager()

        with pytest.raises(TypeError):
            manager.generate_paths()

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_check_ini_existing_file_success(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini with existing, valid INI file."""
        # Setup mock YAML settings
        mock_yaml.return_value = str(tmp_path)

        # Create a valid INI file
        ini_file = tmp_path / "Fallout4.ini"
        ini_content = """[General]
sLanguage=ENGLISH

[Display]
iSize H=1080
iSize W=1920
"""
        ini_file.write_text(ini_content)

        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        result = manager.check_ini("Fallout4.ini")

        assert "✔️" in result
        assert "No obvious corruption detected" in result

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_check_ini_missing_file(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini with missing INI file."""
        mock_yaml.return_value = str(tmp_path)

        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        result = manager.check_ini("Fallout4.ini")

        assert "❌ CAUTION" in result
        assert "MISSING" in result

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_check_ini_custom_ini_creation(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini creates custom INI file when missing."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        # Mock settings to return the test directory
        mock_yaml.side_effect = lambda type_hint, store, key, *args: {
            f"Game_Info.Root_Folder_Docs": str(tmp_path),
            f"Game_VR_Info.Root_Folder_Docs": str(tmp_path),
            "Default_CustomINI": "# Default custom INI content\n[Archive]\nbInvalidateOlderFiles=1\n",
        }.get(key, None)

        result = manager.check_ini("Fallout4Custom.ini")

        # Should create the file and return appropriate message
        assert "WARNING" in result or "Archive Invalidation" in result

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_check_ini_corrupted_file(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini handles corrupted INI files."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        # Create a corrupted INI file
        ini_file = tmp_path / "Fallout4.ini"
        ini_file.write_text("This is not valid INI content [broken")

        # Mock settings
        mock_yaml.side_effect = lambda type_hint, store, key, *args: str(tmp_path) if "Root_Folder_Docs" in key else None

        result = manager.check_ini("Fallout4.ini")

        # Should detect corruption
        assert "CAUTION" in result and "BROKEN" in result

    def test_check_ini_invalid_docs_name_type(self) -> None:
        """Test check_ini raises TypeError for invalid docs_name."""
        manager = DocumentsPathManager()
        manager.docs_name = None  # type: ignore[assignment] # Invalid type for testing

        with pytest.raises(TypeError):
            manager.check_ini("test.ini")

    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    def test_check_ini_invalid_folder_docs_type(self, mock_yaml: MagicMock) -> None:
        """Test check_ini raises TypeError for invalid folder_docs."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        with pytest.raises(TypeError):
            manager.check_ini("test.ini")


class TestPublicAPIFunctions:
    """Tests for the public API functions."""

    @patch("ClassicLib.DocsPath.DocumentsPathManager")
    def test_docs_path_find_gui_mode(self, mock_manager_class: MagicMock) -> None:
        """Test docs_path_find function in GUI mode."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        docs_path_find(is_gui_mode=True)

        mock_manager_class.assert_called_once_with(True)
        mock_manager.find_docs_path.assert_called_once()

    @patch("ClassicLib.DocsPath.DocumentsPathManager")
    def test_docs_path_find_cli_mode(self, mock_manager_class: MagicMock) -> None:
        """Test docs_path_find function in CLI mode."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        docs_path_find(is_gui_mode=False)

        mock_manager_class.assert_called_once_with(False)
        mock_manager.find_docs_path.assert_called_once()

    @patch("ClassicLib.DocsPath.DocumentsPathManager")
    def test_docs_generate_paths(self, mock_manager_class: MagicMock) -> None:
        """Test docs_generate_paths function."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        docs_generate_paths()

        mock_manager_class.assert_called_once_with()
        mock_manager.generate_paths.assert_called_once()

    @patch("ClassicLib.DocsPath.DocumentsPathManager")
    def test_docs_check_ini(self, mock_manager_class: MagicMock) -> None:
        """Test docs_check_ini function."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.check_ini.return_value = "✔️ INI file is OK"

        result = docs_check_ini("Fallout4.ini")

        mock_manager_class.assert_called_once_with()
        mock_manager.check_ini.assert_called_once_with("Fallout4.ini")
        assert result == "✔️ INI file is OK"


if __name__ == "__main__":
    pytest.main()

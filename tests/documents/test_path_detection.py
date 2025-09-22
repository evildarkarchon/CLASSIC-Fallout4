"""Tests for document path detection and platform-specific path finding."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import init_message_handler
from ClassicLib.DocsPath import DocumentsPathManager


@pytest.fixture(autouse=True)
def init_message_handler_fixture():
    """Initialize MessageHandler for all tests in this module."""
    # Initialize the MessageHandler to prevent RuntimeError
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    # Clean up the global message handler after tests
    import ClassicLib.MessageHandler
    ClassicLib.MessageHandler._message_handler = None


class TestPathDetection:
    """Tests for document path detection functionality."""

    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.classic_settings")
    def test_find_docs_path_with_ini_folder_setting(self, mock_classic_settings: MagicMock, mock_msg_info: MagicMock) -> None:  # noqa: ARG002
        """Test find_docs_path when INI folder setting is present in YAML."""
        manager = DocumentsPathManager()

        # Mock classic_settings to return a custom folder path
        mock_classic_settings.return_value = "C:/Custom/Documents/Folder"

        # Patch ResourceLoader at source since DocsPath imports it locally
        with patch("ClassicLib.ResourceLoader.ResourceLoader") as mock_resource_loader:
            mock_resource_loader.get_cached_docs_path.return_value = None  # No cached path
            mock_resource_loader.save_path_to_cache.return_value = None

            with patch("ClassicLib.Util.validate_path", return_value=(True, "")):  # noqa: SIM117
                with patch("pathlib.Path.is_dir", return_value=True):
                    with patch.object(manager, "_update_game_setting") as mock_update:
                        manager.find_docs_path()

                        # Verify that it updates the setting with the custom path
                        mock_update.assert_called_once_with("Root_Folder_Docs", "C:/Custom/Documents/Folder")

    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.classic_settings")
    @patch("platform.system", return_value="Windows")
    def test_find_docs_path_windows_detection(
        self,
        mock_platform: MagicMock,  # noqa: ARG002
        mock_classic_settings: MagicMock,
        mock_msg_info: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test find_docs_path on Windows using registry detection."""
        manager = DocumentsPathManager(is_gui_mode=False)

        # Mock no ini_folder setting and no existing docs path
        mock_classic_settings.return_value = None

        # Patch ResourceLoader at source since DocsPath imports it locally
        with patch("ClassicLib.ResourceLoader.ResourceLoader") as mock_resource_loader:
            mock_resource_loader.get_cached_docs_path.return_value = None
            mock_resource_loader.save_path_to_cache.return_value = None

            with patch("ClassicLib.DocsPath.yaml_settings", return_value=None):  # noqa: SIM117
                with patch.object(manager, "_find_windows_docs_path") as mock_windows:
                    with patch.object(manager, "_get_manual_docs_path") as mock_manual:  # noqa: F841
                        manager.find_docs_path()

                        # Should call Windows detection method
                        mock_windows.assert_called_once()

    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.classic_settings")
    @patch("platform.system", return_value="Linux")
    def test_find_docs_path_linux_detection(
        self,
        mock_platform: MagicMock,  # noqa: ARG002
        mock_classic_settings: MagicMock,
        mock_msg_info: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test find_docs_path on Linux using Steam library detection."""
        manager = DocumentsPathManager(is_gui_mode=False)

        # Mock no ini_folder setting and no existing docs path
        mock_classic_settings.return_value = None

        # Patch ResourceLoader at source since DocsPath imports it locally
        with patch("ClassicLib.ResourceLoader.ResourceLoader") as mock_resource_loader:
            mock_resource_loader.get_cached_docs_path.return_value = None
            mock_resource_loader.save_path_to_cache.return_value = None

            with patch("ClassicLib.DocsPath.yaml_settings", return_value=None):  # noqa: SIM117
                with patch.object(manager, "_find_linux_docs_path") as mock_linux:
                    with patch.object(manager, "_get_manual_docs_path") as mock_manual:  # noqa: F841
                        manager.find_docs_path()

                        # Should call Linux detection method
                        mock_linux.assert_called_once()

    @patch("ClassicLib.DocsPath.classic_settings", return_value=None)
    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    @patch("ClassicLib.DocsPath.msg_error")
    @patch("ClassicLib.DocsPath.msg_info")
    @patch("builtins.input", side_effect=["C:/Valid/Path", ""])
    def test_find_docs_path_manual_fallback(
        self,
        mock_input: MagicMock,
        mock_msg_info: MagicMock,  # noqa: ARG002
        mock_msg_error: MagicMock,  # noqa: ARG002
        mock_yaml: MagicMock,  # noqa: ARG002
        mock_classic: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test find_docs_path falls back to manual input when detection fails."""
        manager = DocumentsPathManager(is_gui_mode=False)

        # Patch ResourceLoader at source since DocsPath imports it locally
        with patch("ClassicLib.ResourceLoader.ResourceLoader") as mock_resource_loader:
            mock_resource_loader.get_cached_docs_path.return_value = None
            mock_resource_loader.save_path_to_cache.return_value = None

            with patch("pathlib.Path.is_dir", return_value=True):  # noqa: SIM117
                with patch.object(manager, "_update_game_setting") as mock_update:  # noqa: F841
                    with patch.object(manager, "_find_windows_docs_path"):
                        manager.find_docs_path()

                        # Since _find_windows_docs_path doesn't set a valid path,
                        # it should call manual input method
                        assert mock_input.called

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_find_windows_docs_path_success(self, mock_query: MagicMock, mock_open: MagicMock) -> None:  # noqa: ARG002
        """Test _find_windows_docs_path successfully retrieves Windows documents path."""
        mock_query.return_value = ("C:\\Users\\Test\\Documents", None)

        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._find_windows_docs_path()

            expected_path = "C:\\Users\\Test\\Documents\\My Games\\Fallout4"
            mock_update.assert_called_once_with("Root_Folder_Docs", expected_path)

    @patch("winreg.OpenKey", side_effect=OSError("Registry key not found"))
    def test_find_windows_docs_path_registry_failure(self, mock_open: MagicMock) -> None:  # noqa: ARG002
        """Test _find_windows_docs_path handles registry access failure."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._find_windows_docs_path()

            # Should still update with default path
            mock_update.assert_called_once()
            # Path should contain user home directory fallback
            args = mock_update.call_args[0]
            assert "Documents" in args[1]
            assert "My Games" in args[1]

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux-specific test")
    @patch("ClassicLib.DocsPath.yaml_settings")
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("pathlib.Path.open")
    def test_find_linux_docs_path_success(self, mock_open_file: MagicMock, mock_is_file: MagicMock, mock_yaml: MagicMock) -> None:  # noqa: ARG002
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
            assert "compatdata" in args[1]
            assert "377160" in args[1]

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux-specific test")
    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    def test_find_linux_docs_path_invalid_steam_id(self, mock_yaml: MagicMock) -> None:  # noqa: ARG002
        """Test _find_linux_docs_path handles invalid Steam ID."""
        manager = DocumentsPathManager()

        with pytest.raises(TypeError):
            manager._find_linux_docs_path()

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux-specific test")
    @patch("pathlib.Path.is_file", return_value=False)
    @patch("ClassicLib.DocsPath.yaml_settings", return_value=377160)
    def test_find_linux_docs_path_no_steam_file(self, mock_yaml: MagicMock, mock_is_file: MagicMock) -> None:  # noqa: ARG002
        """Test _find_linux_docs_path handles missing Steam library file."""
        manager = DocumentsPathManager()

        # Should not raise exception, just return without setting path
        manager._find_linux_docs_path()
        # Test passes if no exception is raised

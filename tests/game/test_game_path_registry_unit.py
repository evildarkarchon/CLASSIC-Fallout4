"""
Unit tests for game_path_registry - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import _game_path_find_registry

pytestmark = pytest.mark.unit


class TestRegistryDetection:
    """Tests for Windows registry-based game path detection."""

    @patch("winreg.OpenKey", side_effect=FileNotFoundError)
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_both_keys_fail(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_open: MagicMock, message_handler
    ) -> None:
        """Test registry detection when both Bethesda and GOG keys fail."""
        result = _game_path_find_registry("Fallout4.exe")
        assert result is None
        assert mock_open.call_count == 2

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx", return_value=(None, None))
    @patch("winreg.CloseKey")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_null_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_close: MagicMock,
        mock_query: MagicMock,
        mock_open: MagicMock,
        message_handler,
    ) -> None:
        """Test registry detection with null path value."""
        result = _game_path_find_registry("Fallout4.exe")
        assert result is None

    @patch("ClassicLib.GamePath.msg_info")
    @patch("platform.system", return_value="Windows")
    def test_game_path_find_windows_registry_success(self, mock_platform: MagicMock, mock_msg_info: MagicMock, message_handler) -> None:
        """Test successful Windows registry-based game path detection."""
        with patch("ClassicLib.GamePath.yaml_settings") as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {
                "Game_Info.XSE_Acronym": "f4se",
                "Game_VR_Info.XSE_Acronym": "f4sevr",
                "Game_Info.Main_Root_Name": "Fallout 4",
                "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
                "Game_Info.Docs_File_XSE": None,
                "Game_VR_Info.Docs_File_XSE": None,
            }.get(key)
            with patch("ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path", return_value=None):
                with patch("ClassicLib.GamePath._game_path_find_registry") as mock_registry:
                    mock_registry.return_value = Path("C:/Program Files/Fallout4")
                    from ClassicLib.GamePath import game_path_find

                    game_path_find()
                    mock_registry.assert_called_once_with("Fallout4.exe")

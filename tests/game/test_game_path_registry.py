"""
Test suite for game path Windows registry detection functionality.

This module contains tests for Windows registry-based game path detection,
including Bethesda and GOG registry key lookups.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import _game_path_find_registry


class TestRegistryDetection:
    """Tests for Windows registry-based game path detection."""

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
    def test_registry_detection_both_keys_fail(
        self,
        mock_get_vr: MagicMock,  # noqa: ARG002
        mock_get_game: MagicMock,  # noqa: ARG002
        mock_open: MagicMock
    ) -> None:
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
    def test_game_path_find_windows_registry_success(
        self,
        mock_platform: MagicMock,  # noqa: ARG002
        mock_msg_info: MagicMock  # noqa: ARG002
    ) -> None:
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

                from ClassicLib.GamePath import game_path_find
                game_path_find()

                # Verify registry detection was called
                mock_registry.assert_called_once_with("Fallout4.exe")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

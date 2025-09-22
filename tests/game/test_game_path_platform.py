"""
Test suite for cross-platform game path detection functionality.

This module contains tests for platform-specific behavior,
ensuring proper operation on Windows and Linux systems.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import game_path_find


class TestMultiPlatformSupport:
    """Tests for cross-platform compatibility."""

    @patch("platform.system", return_value="Linux")
    @patch("ClassicLib.GamePath._game_path_find_registry")
    def test_linux_skips_registry(
        self,
        mock_registry: MagicMock,
        mock_platform: MagicMock,  # noqa: ARG002
        message_handler
    ) -> None:
        """Test that Linux systems skip Windows registry detection."""
        # Mock other dependencies to focus on the platform check
        # Provide more values to avoid StopIteration
        yaml_values = {
            'Game_Info.Docs_File_XSE': None,
            'Game_VR_Info.Docs_File_XSE': None,
            'Game_Info.XSE_Acronym': 'F4SE',
            'Game_VR_Info.XSE_Acronym': 'F4SEVR',
            'Game_Info.Main_Root_Name': 'Fallout 4',
            'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR'
        }
        with patch("ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path", return_value=None):
            with patch("ClassicLib.GamePath.yaml_settings", side_effect=lambda t, s, k, *args: yaml_values.get(k)):  # noqa: SIM117
                with patch("ClassicLib.Util.validate_path", return_value=(False, "Missing file")):
                    with patch.object(GlobalRegistry, "is_gui_mode", return_value=True):
                        with patch("ClassicLib.Interface.PathDialogMixin.show_game_path_dialog_static", return_value=Path("/fake/path")):
                            game_path_find()

        # Registry function should not be called on Linux
        mock_registry.assert_not_called()

    @patch("platform.system", return_value="Windows")
    @patch("ClassicLib.GamePath._game_path_find_registry", return_value=None)
    def test_windows_uses_registry(
        self,
        mock_registry: MagicMock,
        mock_platform: MagicMock,  # noqa: ARG002
        message_handler
    ) -> None:
        """Test that Windows systems use registry detection."""
        # Mock other dependencies to focus on the platform check
        # Provide more values to avoid StopIteration
        yaml_values = {
            'Game_Info.Docs_File_XSE': None,
            'Game_VR_Info.Docs_File_XSE': None,
            'Game_Info.XSE_Acronym': 'F4SE',
            'Game_VR_Info.XSE_Acronym': 'F4SEVR',
            'Game_Info.Main_Root_Name': 'Fallout 4',
            'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR'
        }
        with patch("ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path", return_value=None):
            with patch("ClassicLib.GamePath.yaml_settings", side_effect=lambda t, s, k, *args: yaml_values.get(k)):  # noqa: SIM117
                with patch("ClassicLib.Util.validate_path", return_value=(False, "Missing file")):
                    with patch.object(GlobalRegistry, "is_gui_mode", return_value=True):
                        with patch("ClassicLib.Interface.PathDialogMixin.show_game_path_dialog_static", return_value=Path("/fake/path")):
                            game_path_find()

        # Registry function should be called on Windows
        mock_registry.assert_called_once_with("Fallout4.exe")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

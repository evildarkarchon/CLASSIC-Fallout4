"""
Test suite for cross-platform game path detection functionality.

This module contains tests for platform-specific behavior,
ensuring proper operation on Windows and Linux systems.
The implementation uses RustGamePathFinder exclusively.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import game_path_find

pytestmark = pytest.mark.unit


class TestMultiPlatformSupport:
    """Tests for cross-platform compatibility."""

    @patch("platform.system", return_value="Linux")
    @patch("ClassicLib.support.game_path._game_path_find_registry")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    def test_linux_skips_registry(
        self,
        mock_rust_finder_cls: MagicMock,
        mock_registry: MagicMock,
        mock_platform: MagicMock,
        message_handler,
    ) -> None:
        """Test that Linux systems skip Windows registry detection."""
        # Mock Rust finder to succeed via find_game_path
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = "/fake/path"
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        yaml_values = {
            "Game_Info.Docs_File_XSE": None,
            "Game_VR_Info.Docs_File_XSE": None,
            "Game_Info.XSE_Acronym": "F4SE",
            "Game_VR_Info.XSE_Acronym": "F4SEVR",
            "Game_Info.Main_Root_Name": "Fallout 4",
            "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
        }
        with patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path", return_value=None):
            with patch("ClassicLib.support.game_path.yaml_settings", side_effect=lambda t, s, k, *args: yaml_values.get(k)):
                with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                    game_path_find()

        # Registry function should not be called on Linux
        mock_registry.assert_not_called()

    @patch("platform.system", return_value="Windows")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    def test_windows_uses_rust_finder(
        self,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_platform: MagicMock,
        message_handler,
    ) -> None:
        """Test that Windows systems use Rust finder for path detection."""
        # Mock Rust finder to succeed via find_game_path
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = "C:/Games/Fallout4"
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        mock_path_validator.is_valid_path.return_value = True

        yaml_values = {
            "Game_Info.Docs_File_XSE": None,
            "Game_VR_Info.Docs_File_XSE": None,
            "Game_Info.XSE_Acronym": "F4SE",
            "Game_VR_Info.XSE_Acronym": "F4SEVR",
            "Game_Info.Main_Root_Name": "Fallout 4",
            "Game_VR_Info.Main_Root_Name": "Fallout 4 VR",
        }
        with patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path", return_value=None):
            with patch("ClassicLib.support.game_path.yaml_settings", side_effect=lambda t, s, k, *args: yaml_values.get(k)):
                with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
                    game_path_find()

        # Rust finder should be called (handles registry internally)
        mock_rust_finder.find_game_path.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

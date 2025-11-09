"""
Integration tests for game_path_registry - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import _game_path_find_registry

pytestmark = pytest.mark.integration


class TestRegistryDetection:
    """Tests for Windows registry-based game path detection."""

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    @patch("winreg.CloseKey")
    @patch("ClassicLib.ResourceLoader.ResourceLoader.save_path_to_cache")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "register")
    def test_registry_detection_bethesda_success(
        self,
        mock_register: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_save_cache: MagicMock,
        mock_close: MagicMock,
        mock_query: MagicMock,
        mock_open: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test successful registry detection via Bethesda key."""
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        (game_dir / "Fallout4.exe").write_text("fake exe")
        mock_query.return_value = (str(game_dir), None)
        result = _game_path_find_registry("Fallout4.exe")
        assert result == game_dir
        mock_open.assert_called_once()
        mock_query.assert_called_once_with(mock_open.return_value, "installed path")
        mock_close.assert_called_once()
        mock_save_cache.assert_called_once_with(game_dir, "GamePath")
        mock_register.assert_called_once_with(GlobalRegistry.Keys.GAME_PATH, game_dir)

    @patch("winreg.OpenKey", side_effect=[FileNotFoundError, MagicMock()])
    @patch("winreg.QueryValueEx")
    @patch("winreg.CloseKey")
    @patch("ClassicLib.ResourceLoader.ResourceLoader.save_path_to_cache")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "register")
    def test_registry_detection_gog_fallback_success(
        self,
        mock_register: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_save_cache: MagicMock,
        mock_close: MagicMock,
        mock_query: MagicMock,
        mock_open: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test successful registry detection via GOG key fallback."""
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        (game_dir / "Fallout4.exe").write_text("fake exe")
        mock_query.return_value = (str(game_dir), None)
        result = _game_path_find_registry("Fallout4.exe")
        assert result == game_dir
        assert mock_open.call_count == 2
        mock_save_cache.assert_called_once_with(game_dir, "GamePath")
        mock_register.assert_called_once_with(GlobalRegistry.Keys.GAME_PATH, game_dir)

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    @patch("winreg.CloseKey")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_invalid_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_close: MagicMock,
        mock_query: MagicMock,
        mock_open: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test registry detection with path that doesn't contain game executable."""
        game_dir = tmp_path / "InvalidGame"
        game_dir.mkdir()
        mock_query.return_value = (str(game_dir), None)
        result = _game_path_find_registry("Fallout4.exe")
        assert result is None
        mock_open.assert_called_once()
        mock_query.assert_called_once()
        mock_close.assert_called_once()

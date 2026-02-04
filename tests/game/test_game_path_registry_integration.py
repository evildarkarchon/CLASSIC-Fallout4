"""
Integration tests for game_path_registry - integration logic testing.

This file contains integration tests for registry-based game path detection.
The implementation uses RustGamePathFinder exclusively.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import _game_path_find_registry

pytestmark = pytest.mark.integration


class TestRegistryDetection:
    """Integration tests for Rust-based registry game path detection."""

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_success(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_save_cache: MagicMock,
        mock_rust_finder_cls: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test successful registry detection via Rust finder."""
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        (game_dir / "Fallout4.exe").write_text("fake exe")

        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = str(game_dir)
        mock_rust_finder_cls.return_value = mock_rust_finder

        result = _game_path_find_registry("Fallout4.exe")

        assert result == game_dir
        mock_rust_finder_cls.assert_called_once()
        mock_save_cache.assert_called_once_with(game_dir, "GamePath")

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_registry_detection_returns_path_object(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_rust_finder_cls: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test registry detection returns Path object from string."""
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()

        mock_rust_finder = MagicMock()
        # Rust returns a string, function should convert to Path
        mock_rust_finder.find_game_path.return_value = str(game_dir)
        mock_rust_finder_cls.return_value = mock_rust_finder

        with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
            result = _game_path_find_registry("Fallout4.exe")

        assert isinstance(result, Path)
        assert result == game_dir

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "register")
    def test_registry_detection_registers_path(
        self,
        mock_register: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_rust_finder_cls: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test successful registry detection registers path globally."""
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()

        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = str(game_dir)
        mock_rust_finder_cls.return_value = mock_rust_finder

        with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
            result = _game_path_find_registry("Fallout4.exe")

        assert result == game_dir
        mock_register.assert_called_once_with(GlobalRegistry.Keys.GAME_PATH, game_dir)

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_registry_detection_vr_mode(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_rust_finder_cls: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test registry detection in VR mode passes correct parameters."""
        game_dir = tmp_path / "Fallout4VR"
        game_dir.mkdir()

        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = str(game_dir)
        mock_rust_finder_cls.return_value = mock_rust_finder

        with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache"):
            result = _game_path_find_registry("Fallout4VR.exe")

        assert result == game_dir
        # Verify VR mode was passed to Rust finder
        call_args = mock_rust_finder_cls.call_args
        assert call_args[0][3] is True  # is_vr parameter

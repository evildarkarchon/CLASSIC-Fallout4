"""Unit tests for game_path_generation - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib import Constants, GlobalRegistry
from ClassicLib.Constants import NULL_VERSION
from ClassicLib.GamePath import game_generate_paths, game_path_find

pytestmark = pytest.mark.unit


class TestGamePathGeneration:
    """Tests for game path generation functionality."""

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_fallout4_og_version(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths for Fallout 4 OG version."""
        game_path = str(tmp_path / "Fallout4")
        mock_yaml.side_effect = [game_path, "F4SE", "F4SE", None, None, None, None, None, f"{game_path}\\Fallout4.exe", None]
        mock_get_version.return_value = Constants.OG_VERSION
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_fallout4_ng_version(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths for Fallout 4 NG version."""
        game_path = str(tmp_path / "Fallout4")
        mock_yaml.side_effect = [game_path, "F4SE", "F4SE", None, None, None, None, None, f"{game_path}\\Fallout4.exe", None]
        mock_get_version.return_value = Constants.NG_VERSION
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_missing_game_path(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock) -> None:
        """Test game_generate_paths with missing game path."""
        mock_yaml.return_value = None
        with pytest.raises(TypeError):
            game_generate_paths()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_missing_xse_acronym(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths with missing XSE acronym."""
        game_path = str(tmp_path / "Fallout4")
        mock_yaml.side_effect = [game_path, "F4SE", None]
        with pytest.raises(TypeError):
            game_generate_paths()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_null_version_uses_default(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths uses default when version detection fails."""
        game_path = str(tmp_path / "Fallout4")
        mock_yaml.side_effect = [game_path, "F4SE", "F4SE", None, None, None, None, None, f"{game_path}\\Fallout4.exe", None]
        mock_get_version.return_value = NULL_VERSION

        game_generate_paths()

        assert mock_yaml.call_count >= 6

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch("ClassicLib.GamePath.get_game_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Starfield")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_unsupported_game_raises_error(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths raises ValueError for unsupported games."""
        game_path = str(tmp_path / "Starfield")
        mock_yaml.side_effect = [game_path, "SFSE", "SFSE", None, None, None, None, None, f"{game_path}\\Starfield.exe"]
        mock_get_version.return_value = Version("1.0.0")

        with pytest.raises(ValueError, match="Unsupported game"):
            game_generate_paths()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_empty_game_path_raises_error(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock
    ) -> None:
        """Test game_generate_paths raises TypeError with empty string path."""
        mock_yaml.side_effect = ["", "F4SE", "F4SE"]  # Empty string path

        with pytest.raises(TypeError):
            game_generate_paths()

    @patch("ClassicLib.GamePath.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_whitespace_game_path_raises_error(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock
    ) -> None:
        """Test game_generate_paths raises TypeError with whitespace-only path."""
        mock_yaml.side_effect = ["   ", "F4SE", "F4SE"]  # Whitespace-only path

        with pytest.raises(TypeError):
            game_generate_paths()


class TestGamePathFind:
    """Tests for game_path_find() top-level function."""

    @patch("ClassicLib.GamePath.GamePathFinder")
    def test_game_path_find_creates_finder_and_calls_find(self, mock_finder_class: MagicMock, message_handler) -> None:
        """Test game_path_find creates finder and calls find_game_path."""
        mock_finder = MagicMock()
        mock_finder_class.return_value = mock_finder

        game_path_find()

        mock_finder_class.assert_called_once()
        mock_finder.find_game_path.assert_called_once()


class TestVersionWarningLogging:
    """Tests for _log_version_warning helper function."""

    @patch("ClassicLib.GamePath.get_version_registry")
    def test_log_version_warning_logs_only_once(self, mock_registry: MagicMock, message_handler) -> None:
        """Test _log_version_warning only logs once per session."""
        import ClassicLib.GamePath as gp

        # Reset the flag
        gp._VERSION_WARNING_LOGGED = False

        mock_version_registry = MagicMock()
        mock_version_registry.get_all_for_game.return_value = [
            MagicMock(version=Version("1.10.163.0")),
            MagicMock(version=Version("1.10.980.0")),
        ]
        mock_registry.return_value = mock_version_registry

        # First call should log
        gp._log_version_warning(Version("9.9.9.9"))
        assert gp._VERSION_WARNING_LOGGED is True

        # Second call should not log again (flag is already True)
        gp._log_version_warning(Version("8.8.8.8"))
        # Registry should only be called once
        assert mock_registry.call_count == 1

        # Reset for other tests
        gp._VERSION_WARNING_LOGGED = False

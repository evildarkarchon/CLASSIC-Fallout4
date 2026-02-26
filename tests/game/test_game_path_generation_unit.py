"""Unit tests for game_path_generation - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.core.constants import NULL_VERSION
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import game_generate_paths, game_path_find

pytestmark = pytest.mark.unit


def _make_version_registry_mock(xse_acronym: str = "F4SE") -> MagicMock:
    """Create a mock version registry with standard configuration."""
    mock_version_info = MagicMock()
    mock_version_info.xse.acronym = xse_acronym
    mock_version_info.address_library.filename = "version-1-10-163-0.bin"
    mock_registry = MagicMock()
    mock_registry.get_by_id.return_value = mock_version_info
    mock_match_result = MagicMock()
    mock_match_result.should_warn = False
    mock_match_result.version_info = mock_version_info
    mock_registry.match_version.return_value = mock_match_result
    return mock_registry


class TestGamePathGeneration:
    """Tests for game path generation functionality."""

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_fallout4_og_version(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        mock_get_registry: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths for Fallout 4 OG version."""
        mock_get_registry.return_value = _make_version_registry_mock()
        game_path = str(tmp_path / "Fallout4")

        def yaml_side_effect(_type, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if "Game_File_EXE" in key_path:
                if args:
                    return args[0]  # Return the value being set
                return f"{game_path}\\Fallout4.exe"
            return args[0] if args else None

        mock_yaml.side_effect = yaml_side_effect
        mock_get_version.return_value = Version("1.10.163.0")
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_fallout4_ng_version(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        mock_get_registry: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths for Fallout 4 NG version."""
        mock_get_registry.return_value = _make_version_registry_mock()
        game_path = str(tmp_path / "Fallout4")

        def yaml_side_effect(_type, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if "Game_File_EXE" in key_path:
                if args:
                    return args[0]
                return f"{game_path}\\Fallout4.exe"
            return args[0] if args else None

        mock_yaml.side_effect = yaml_side_effect
        mock_get_version.return_value = Version("1.10.984.0")
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_missing_game_path(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, mock_get_registry: MagicMock
    ) -> None:
        """Test game_generate_paths with missing game path."""
        mock_get_registry.return_value = _make_version_registry_mock()
        mock_yaml.return_value = None
        with pytest.raises(TypeError):
            game_generate_paths()

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_missing_xse_acronym(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, mock_get_registry: MagicMock, tmp_path: Path
    ) -> None:
        """Test game_generate_paths with missing XSE acronym."""
        # Return a registry with None xse
        mock_version_info = MagicMock()
        mock_version_info.xse = None
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        game_path = str(tmp_path / "Fallout4")
        mock_yaml.return_value = game_path

        with pytest.raises(TypeError):
            game_generate_paths()

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_null_version_uses_default(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        mock_get_registry: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths uses default when version detection fails."""
        mock_get_registry.return_value = _make_version_registry_mock()
        game_path = str(tmp_path / "Fallout4")

        def yaml_side_effect(_type, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if "Game_File_EXE" in key_path:
                if args:
                    return args[0]
                return f"{game_path}\\Fallout4.exe"
            return args[0] if args else None

        mock_yaml.side_effect = yaml_side_effect
        mock_get_version.return_value = NULL_VERSION

        game_generate_paths()

        assert mock_yaml.call_count >= 6

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Starfield")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_unsupported_game_raises_error(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml: MagicMock,
        mock_get_registry: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test game_generate_paths raises ValueError for unsupported games."""
        mock_get_registry.return_value = _make_version_registry_mock("SFSE")
        game_path = str(tmp_path / "Starfield")

        def yaml_side_effect(_type, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if "Game_File_EXE" in key_path:
                if args:
                    return args[0]
                return f"{game_path}\\Starfield.exe"
            return args[0] if args else None

        mock_yaml.side_effect = yaml_side_effect
        mock_get_version.return_value = Version("1.0.0")

        with pytest.raises(ValueError, match="Unsupported game"):
            game_generate_paths()

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_empty_game_path_raises_error(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, mock_get_registry: MagicMock
    ) -> None:
        """Test game_generate_paths raises TypeError with empty string path."""
        mock_get_registry.return_value = _make_version_registry_mock()
        mock_yaml.return_value = ""

        with pytest.raises(TypeError):
            game_generate_paths()

    @patch("ClassicLib.support.game_path.get_version_registry")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_generate_paths_whitespace_game_path_raises_error(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, mock_get_registry: MagicMock
    ) -> None:
        """Test game_generate_paths raises TypeError with whitespace-only path."""
        mock_get_registry.return_value = _make_version_registry_mock()
        mock_yaml.return_value = "   "

        with pytest.raises(TypeError):
            game_generate_paths()


class TestGamePathFind:
    """Tests for game_path_find() top-level function."""

    @patch("ClassicLib.support.game_path.GamePathFinder")
    def test_game_path_find_creates_finder_and_calls_find(self, mock_finder_class: MagicMock, message_handler) -> None:
        """Test game_path_find creates finder and calls find_game_path."""
        mock_finder = MagicMock()
        mock_finder_class.return_value = mock_finder

        game_path_find()

        mock_finder_class.assert_called_once()
        mock_finder.find_game_path.assert_called_once()


class TestVersionWarningLogging:
    """Tests for _log_version_warning helper function."""

    @patch("ClassicLib.support.game_path.get_version_registry")
    def test_log_version_warning_logs_only_once(self, mock_registry: MagicMock, message_handler) -> None:
        """Test _log_version_warning only logs once per unique arguments (lru_cache)."""
        import ClassicLib.support.game_path as gp

        # Clear the lru_cache before testing
        gp._log_version_warning.cache_clear()

        mock_version_registry = MagicMock()
        mock_version_registry.get_all_for_game.return_value = [
            MagicMock(version=Version("1.10.163.0")),
            MagicMock(version=Version("1.10.980.0")),
        ]
        mock_registry.return_value = mock_version_registry

        # First call should log
        result = gp._log_version_warning(Version("9.9.9.9"))
        assert result is True

        # Second call with same args should be cached (not call registry again)
        gp._log_version_warning(Version("9.9.9.9"))
        # Registry should only be called once for same args
        assert mock_registry.call_count == 1

        # Clear cache for other tests
        gp._log_version_warning.cache_clear()

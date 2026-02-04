"""Unit tests for GamePathFinder class methods.

This file contains unit tests for GamePathFinder methods that still exist:
- _save_game_path()
- _get_path_from_user_gui()
- _get_path_from_user_console()
- __init__()

Note: The following private methods were removed during Rust migration:
- _validate_xse_file() -> Now handled by RustGamePathFinder
- _parse_xse_log_for_path() -> Now handled by RustGamePathFinder
- _validate_game_path() -> Now handled by RustGamePathFinder.validate_game_path()
- _report_xse_error() -> Replaced by Rust error handling
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import GamePathFinder

pytestmark = pytest.mark.unit


class TestSaveGamePath:
    """Tests for GamePathFinder._save_game_path() method."""

    @patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_save_game_path_saves_and_registers(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_save_cache: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _save_game_path saves to cache and registers in GlobalRegistry."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        game_path = tmp_path / "Fallout4"
        game_path.mkdir()

        finder = GamePathFinder()
        finder._save_game_path(game_path)

        mock_save_cache.assert_called_once_with(game_path, "GamePath")
        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH) == game_path


class TestGetPathFromUserGui:
    """Tests for GamePathFinder._get_path_from_user_gui() method."""

    @patch("ClassicLib.support.game_path.show_game_path_dialog_static")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_get_path_from_user_gui_returns_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_dialog: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _get_path_from_user_gui returns path from dialog."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        expected_path = tmp_path / "Fallout4"
        mock_dialog.return_value = expected_path

        finder = GamePathFinder()
        result = finder._get_path_from_user_gui()

        assert result == expected_path
        mock_dialog.assert_called_once()

    @patch("ClassicLib.support.game_path.show_game_path_dialog_static")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_get_path_from_user_gui_cancelled_raises_error(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_dialog: MagicMock,
        message_handler,
    ) -> None:
        """Test _get_path_from_user_gui raises RuntimeError when cancelled."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        mock_dialog.return_value = None

        finder = GamePathFinder()

        with pytest.raises(RuntimeError, match="cancelled"):
            finder._get_path_from_user_gui()


class TestGetPathFromUserConsole:
    """Tests for GamePathFinder._get_path_from_user_console() method."""

    @patch("builtins.input")
    @patch("ClassicLib.support.game_path.PathValidator")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_get_path_from_user_console_valid_input(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_msg_info: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_path_validator: MagicMock,
        mock_input: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _get_path_from_user_console returns valid path from input."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        game_path = tmp_path / "Fallout4"
        game_path.mkdir()
        exe_path = game_path / "Fallout4.exe"
        exe_path.write_text("# Fake exe")

        mock_input.return_value = str(game_path)
        # Mock Rust PathValidator to return True for valid path check
        mock_path_validator.is_valid_path.return_value = True
        # Mock RustGamePathFinder.validate_game_path to succeed (no exception)
        mock_rust_finder = MagicMock()
        mock_rust_finder_cls.return_value = mock_rust_finder

        finder = GamePathFinder()
        result = finder._get_path_from_user_console()

        assert result == game_path

    @patch("builtins.input")
    @patch("ClassicLib.support.game_path.PathValidator")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_get_path_from_user_console_retry_on_invalid(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_path_validator: MagicMock,
        mock_input: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _get_path_from_user_console retries on invalid input."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        game_path = tmp_path / "Fallout4"
        game_path.mkdir()
        exe_path = game_path / "Fallout4.exe"
        exe_path.write_text("# Fake exe")

        # First call invalid (PathValidator returns False), second call valid
        mock_input.side_effect = [
            "C:/Invalid/Path",
            str(game_path),
        ]
        # PathValidator.is_valid_path: False on first call, True on second
        mock_path_validator.is_valid_path.side_effect = [False, True]
        # Mock RustGamePathFinder to succeed on validation
        mock_rust_finder = MagicMock()
        mock_rust_finder_cls.return_value = mock_rust_finder

        finder = GamePathFinder()
        result = finder._get_path_from_user_console()

        assert result == game_path
        assert mock_input.call_count == 2
        mock_msg_error.assert_called_once()

    @patch("builtins.input")
    @patch("ClassicLib.support.game_path.PathValidator")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.msg_info")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_get_path_from_user_console_retry_on_missing_exe(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_msg_info: MagicMock,
        mock_msg_error: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_path_validator: MagicMock,
        mock_input: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _get_path_from_user_console retries when exe is missing."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        # First path without exe, second with exe
        invalid_path = tmp_path / "NoExe"
        invalid_path.mkdir()

        valid_path = tmp_path / "Fallout4"
        valid_path.mkdir()
        (valid_path / "Fallout4.exe").write_text("# Fake exe")

        mock_input.side_effect = [
            str(invalid_path),
            str(valid_path),
        ]
        # PathValidator returns True for both paths (they exist)
        mock_path_validator.is_valid_path.return_value = True
        # Mock RustGamePathFinder: first call raises ValueError (missing exe), second succeeds
        mock_rust_finder = MagicMock()
        mock_rust_finder.validate_game_path.side_effect = [
            ValueError("Executable not found"),
            None,  # Success on second call
        ]
        mock_rust_finder_cls.return_value = mock_rust_finder

        finder = GamePathFinder()
        result = finder._get_path_from_user_console()

        assert result == valid_path
        assert mock_input.call_count == 2


class TestGamePathFinderInit:
    """Tests for GamePathFinder.__init__() constructor."""

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_init_sets_all_attributes(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_rust_finder_cls: MagicMock,
        message_handler,
    ) -> None:
        """Test __init__ properly initializes all attributes."""
        mock_yaml.side_effect = [
            "C:/Docs/Fallout4/F4SE/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        finder = GamePathFinder()

        assert finder.exe_name == "Fallout4.exe"
        assert finder.xse_file == "C:/Docs/Fallout4/F4SE/f4se.log"
        assert finder.xse_acronym == "F4SE"
        assert finder.xse_acronym_base == "F4SE"
        assert finder.game_name == "Fallout 4"

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_init_vr_mode(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_rust_finder_cls: MagicMock,
        message_handler,
    ) -> None:
        """Test __init__ handles VR mode correctly."""
        mock_yaml.side_effect = [
            "C:/Docs/Fallout4VR/F4SEVR/f4sevr.log",
            "F4SEVR",
            "F4SE",
            "Fallout 4 VR",
        ]

        finder = GamePathFinder()

        assert finder.exe_name == "Fallout4VR.exe"
        assert finder.xse_acronym == "F4SEVR"

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_init_invalid_types_raises_error(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_rust_finder_cls: MagicMock,
        message_handler,
    ) -> None:
        """Test __init__ raises TypeError for invalid YAML types."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            123,  # Invalid type
            "F4SE",
            "Fallout 4",
        ]

        with pytest.raises(TypeError):
            GamePathFinder()

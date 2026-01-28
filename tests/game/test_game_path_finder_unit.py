"""Unit tests for GamePathFinder class methods.

This file contains unit tests for GamePathFinder internal methods:
- _validate_xse_file()
- _parse_xse_log_for_path()
- _validate_game_path()
- _save_game_path()
- _get_path_from_user_gui()
- _get_path_from_user_console()
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.game_path import GamePathFinder

pytestmark = pytest.mark.unit


class TestValidateXseFile:
    """Tests for GamePathFinder._validate_xse_file() method."""

    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_validate_xse_file_missing_path(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, message_handler
    ) -> None:
        """Test _validate_xse_file returns False when xse_file is empty."""
        mock_yaml.side_effect = [
            None,  # xse_file is None
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        with patch("ClassicLib.support.game_path.msg_error"):
            finder = GamePathFinder()
            result = finder._validate_xse_file()

        assert result is False

    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_validate_xse_file_path_not_found(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_validate: MagicMock,
        mock_yaml: MagicMock,
        message_handler,
    ) -> None:
        """Test _validate_xse_file returns False when file doesn't exist."""
        mock_yaml.side_effect = [
            "C:/path/to/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]
        mock_validate.return_value = (False, "Path does not exist")

        with patch("ClassicLib.support.game_path.msg_error"):
            finder = GamePathFinder()
            result = finder._validate_xse_file()

        assert result is False

    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_validate_xse_file_valid(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_validate: MagicMock,
        mock_yaml: MagicMock,
        message_handler,
    ) -> None:
        """Test _validate_xse_file returns True when file is valid."""
        mock_yaml.side_effect = [
            "C:/path/to/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]
        mock_validate.return_value = (True, "")

        finder = GamePathFinder()
        result = finder._validate_xse_file()

        assert result is True


class TestReportXseError:
    """Tests for GamePathFinder._report_xse_error() method."""

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_report_xse_error_file_not_exist(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_msg_error: MagicMock,
        message_handler,
    ) -> None:
        """Test _report_xse_error handles missing file error."""
        mock_yaml.side_effect = [
            "C:/path/to/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        finder = GamePathFinder()
        finder._report_xse_error("Path does not exist")

        mock_msg_error.assert_called_once()
        call_args = mock_msg_error.call_args[0][0]
        assert "MISSING" in call_args

    @patch("ClassicLib.support.game_path.msg_error")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_report_xse_error_access_denied(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_msg_error: MagicMock,
        message_handler,
    ) -> None:
        """Test _report_xse_error handles access denied error."""
        mock_yaml.side_effect = [
            "C:/path/to/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        finder = GamePathFinder()
        finder._report_xse_error("Permission denied")

        mock_msg_error.assert_called_once()
        call_args = mock_msg_error.call_args[0][0]
        assert "CANNOT ACCESS" in call_args


class TestParseXseLogForPath:
    """Tests for GamePathFinder._parse_xse_log_for_path() method."""

    @patch("ClassicLib.support.game_path._HAS_RUST_PATH", False)
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.support.game_path.open_file_with_encoding")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_parse_xse_log_extracts_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_open: MagicMock,
        mock_yaml: MagicMock,
        message_handler,
    ) -> None:
        """Test _parse_xse_log_for_path extracts game path from log."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        # Mock file content with plugin directory line
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(
            return_value=iter([
                "f4se loader log\n",
                "version = 0.6.21\n",
                "plugin directory = C:\\Games\\Fallout4\\Data\\F4SE\\Plugins\n",
                "checking plugin C:\\Games\\Fallout4\\Data\\F4SE\\Plugins\\test.dll\n",
            ])
        )
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_file

        finder = GamePathFinder()
        result = finder._parse_xse_log_for_path()

        assert result is not None
        assert "Fallout4" in str(result)

    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch("ClassicLib.support.game_path.open_file_with_encoding")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_parse_xse_log_no_plugin_directory(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_open: MagicMock,
        mock_yaml: MagicMock,
        message_handler,
    ) -> None:
        """Test _parse_xse_log_for_path returns None when no plugin directory found."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]

        # Mock file content without plugin directory line
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(
            return_value=iter([
                "f4se loader log\n",
                "version = 0.6.21\n",
                "some other content\n",
            ])
        )
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_file

        finder = GamePathFinder()
        result = finder._parse_xse_log_for_path()

        assert result is None


class TestValidateGamePath:
    """Tests for GamePathFinder._validate_game_path() method."""

    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_validate_game_path_invalid_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_validate: MagicMock,
        message_handler,
    ) -> None:
        """Test _validate_game_path returns False for invalid paths."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]
        mock_validate.return_value = (False, "Path not accessible")

        finder = GamePathFinder()
        result = finder._validate_game_path(Path("C:/Invalid/Path"))

        assert result is False

    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_validate_game_path_not_directory(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_validate: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _validate_game_path returns False when path is not a directory."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]
        mock_validate.return_value = (True, "")

        # Create a file, not a directory
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("test")

        finder = GamePathFinder()
        result = finder._validate_game_path(file_path)

        assert result is False

    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_validate_game_path_missing_exe(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_validate: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _validate_game_path returns False when exe is missing."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]
        mock_validate.return_value = (True, "")

        # Create directory without exe
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()

        finder = GamePathFinder()
        result = finder._validate_game_path(game_dir)

        assert result is False

    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_validate_game_path_valid(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_validate: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _validate_game_path returns True for valid paths."""
        mock_yaml.side_effect = [
            "C:/Docs/f4se.log",
            "F4SE",
            "F4SE",
            "Fallout 4",
        ]
        mock_validate.return_value = (True, "")

        # Create directory with exe
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        exe_path = game_dir / "Fallout4.exe"
        exe_path.write_text("# Fake exe")

        finder = GamePathFinder()
        result = finder._validate_game_path(game_dir)

        assert result is True


class TestSaveGamePath:
    """Tests for GamePathFinder._save_game_path() method."""

    @patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache")
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_save_game_path_saves_and_registers(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
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
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_get_path_from_user_gui_returns_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
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
    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_get_path_from_user_gui_cancelled_raises_error(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
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
    @patch("ClassicLib.Utils.path_utils.validate_path")
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
        mock_validate: MagicMock,
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
        mock_validate.return_value = (True, "")

        finder = GamePathFinder()
        result = finder._get_path_from_user_console()

        assert result == game_path

    @patch("builtins.input")
    @patch("ClassicLib.Utils.path_utils.validate_path")
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
        mock_validate: MagicMock,
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

        # First call invalid, second call valid
        mock_input.side_effect = [
            "C:/Invalid/Path",
            str(game_path),
        ]
        mock_validate.side_effect = [
            (False, "Path not found"),
            (True, ""),
        ]

        finder = GamePathFinder()
        result = finder._get_path_from_user_console()

        assert result == game_path
        assert mock_input.call_count == 2
        mock_msg_error.assert_called_once()

    @patch("builtins.input")
    @patch("ClassicLib.Utils.path_utils.validate_path")
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
        mock_validate: MagicMock,
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
        mock_validate.return_value = (True, "")

        finder = GamePathFinder()
        result = finder._get_path_from_user_console()

        assert result == valid_path
        assert mock_input.call_count == 2


class TestGamePathFinderInit:
    """Tests for GamePathFinder.__init__() constructor."""

    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_init_sets_all_attributes(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, message_handler
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

    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_init_vr_mode(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, message_handler) -> None:
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

    @patch("ClassicLib.support.game_path.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_init_invalid_types_raises_error(
        self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, message_handler
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

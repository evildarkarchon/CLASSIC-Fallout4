"""Tests for DocumentsPathManager class core functionality."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.DocsPath import DocumentsPathManager


class TestDocumentPathManager:
    """Tests for the DocumentsPathManager class."""

    def test_initialization_gui_mode(self) -> None:
        """Test DocumentsPathManager initialization in GUI mode."""
        with patch.object(GlobalRegistry, "get_manual_docs_gui", return_value="mock_gui"):
            manager = DocumentsPathManager(is_gui_mode=True)

            assert manager.is_gui_mode is True
            assert manager.manual_docs_gui == "mock_gui"
            assert isinstance(manager.docs_name, str)

    def test_initialization_cli_mode(self) -> None:
        """Test DocumentsPathManager initialization in CLI mode."""
        manager = DocumentsPathManager(is_gui_mode=False)

        assert manager.is_gui_mode is False
        assert manager.manual_docs_gui is None
        assert isinstance(manager.docs_name, str)

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_get_docs_name_from_settings(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_docs_name retrieves from YAML settings."""
        mock_yaml_settings.return_value = "Fallout4Custom"

        result = DocumentsPathManager._get_docs_name()
        assert result == "Fallout4Custom"

    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_get_docs_name_fallback(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:  # noqa: ARG002
        """Test _get_docs_name falls back to GlobalRegistry game name."""
        result = DocumentsPathManager._get_docs_name()
        assert result == "Fallout4"

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_get_game_setting_path_success(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_game_setting_path with valid string return."""
        mock_yaml_settings.return_value = "C:/Games/Fallout4"

        result = DocumentsPathManager._get_game_setting_path("Root_Folder_Game")
        assert result == "C:/Games/Fallout4"

    @patch("ClassicLib.DocsPath.yaml_settings", return_value=None)
    def test_get_game_setting_path_invalid_type(self, mock_yaml_settings: MagicMock) -> None:  # noqa: ARG002
        """Test _get_game_setting_path raises TypeError for non-string."""
        with pytest.raises(TypeError):
            DocumentsPathManager._get_game_setting_path("Root_Folder_Game")

    @patch("ClassicLib.DocsPath.yaml_settings")
    def test_update_game_setting(self, mock_yaml_settings: MagicMock) -> None:
        """Test _update_game_setting calls yaml_settings with correct parameters."""
        DocumentsPathManager._update_game_setting("Root_Folder_Docs", "/path/to/docs")

        mock_yaml_settings.assert_called_once()

    def test_get_manual_docs_path_gui_mode(self) -> None:
        """Test _get_manual_docs_path in GUI mode."""
        mock_gui = MagicMock()
        manager = DocumentsPathManager(is_gui_mode=True)
        manager.manual_docs_gui = mock_gui

        manager._get_manual_docs_path()

        mock_gui.manual_docs_path_signal.emit.assert_called_once()

    @patch("builtins.input")
    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.msg_error")
    def test_get_manual_docs_path_cli_mode_success(
        self,
        mock_error: MagicMock,  # noqa: ARG002
        mock_info: MagicMock,  # noqa: ARG002
        mock_input: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test _get_manual_docs_path in CLI mode with valid input."""
        # Create a test directory
        test_dir = tmp_path / "valid_path"
        test_dir.mkdir()

        mock_input.return_value = str(test_dir)

        manager = DocumentsPathManager(is_gui_mode=False)
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._get_manual_docs_path()

            mock_update.assert_called_once_with("Root_Folder_Docs", str(test_dir))

    @patch("builtins.input")
    @patch("ClassicLib.DocsPath.msg_info")
    @patch("ClassicLib.DocsPath.msg_error")
    def test_get_manual_docs_path_cli_mode_invalid_input(
        self,
        mock_error: MagicMock,
        mock_info: MagicMock,  # noqa: ARG002
        mock_input: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test _get_manual_docs_path in CLI mode with invalid then valid input."""
        # Create a test directory for the second input
        test_dir = tmp_path / "valid_path"
        test_dir.mkdir()

        # First input is invalid, second is valid
        mock_input.side_effect = ["invalid_path", str(test_dir)]

        manager = DocumentsPathManager(is_gui_mode=False)
        manager.docs_name = "Fallout4"

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._get_manual_docs_path()

            # Should show error for first input
            mock_error.assert_called()
            # Should eventually update with valid path
            mock_update.assert_called_once_with("Root_Folder_Docs", str(test_dir))

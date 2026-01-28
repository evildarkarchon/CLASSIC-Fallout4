"""
Unit tests for document_manager - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.docs_path import DocumentsPathManager

pytestmark = pytest.mark.unit


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

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_get_docs_name_from_settings(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_docs_name retrieves from YAML settings."""
        mock_yaml_settings.return_value = "Fallout4Custom"
        result = DocumentsPathManager._get_docs_name()
        assert result == "Fallout4Custom"

    @patch("ClassicLib.io.yaml.yaml_settings", return_value=None)
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_get_docs_name_fallback(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test _get_docs_name falls back to GlobalRegistry game name."""
        result = DocumentsPathManager._get_docs_name()
        assert result == "Fallout4"

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_get_game_setting_path_success(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_game_setting_path with valid string return."""
        mock_yaml_settings.return_value = "C:/Games/Fallout4"
        result = DocumentsPathManager._get_game_setting_path("Root_Folder_Game")
        assert result == "C:/Games/Fallout4"

    @patch("ClassicLib.io.yaml.yaml_settings", return_value=None)
    def test_get_game_setting_path_invalid_type(self, mock_yaml_settings: MagicMock) -> None:
        """Test _get_game_setting_path raises TypeError for non-string."""
        with pytest.raises(TypeError):
            DocumentsPathManager._get_game_setting_path("Root_Folder_Game")

    @patch("ClassicLib.io.yaml.yaml_settings")
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

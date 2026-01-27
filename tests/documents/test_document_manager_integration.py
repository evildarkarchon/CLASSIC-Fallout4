"""
Integration tests for document_manager - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.support.docs_path import DocumentsPathManager

pytestmark = pytest.mark.integration


class TestDocumentPathManager:
    """Tests for the DocumentsPathManager class."""

    @patch("builtins.input")
    @patch("ClassicLib.support.docs_path.msg_info")
    @patch("ClassicLib.support.docs_path.msg_error")
    def test_get_manual_docs_path_cli_mode_success(
        self, mock_error: MagicMock, mock_info: MagicMock, mock_input: MagicMock, tmp_path: Path
    ) -> None:
        """Test _get_manual_docs_path in CLI mode with valid input."""
        test_dir = tmp_path / "valid_path"
        test_dir.mkdir()
        mock_input.return_value = str(test_dir)
        manager = DocumentsPathManager(is_gui_mode=False)
        manager.docs_name = "Fallout4"
        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._get_manual_docs_path()
            mock_update.assert_called_once_with("Root_Folder_Docs", str(test_dir))

    @patch("builtins.input")
    @patch("ClassicLib.support.docs_path.msg_info")
    @patch("ClassicLib.support.docs_path.msg_error")
    def test_get_manual_docs_path_cli_mode_invalid_input(
        self, mock_error: MagicMock, mock_info: MagicMock, mock_input: MagicMock, tmp_path: Path
    ) -> None:
        """Test _get_manual_docs_path in CLI mode with invalid then valid input."""
        test_dir = tmp_path / "valid_path"
        test_dir.mkdir()
        mock_input.side_effect = ["invalid_path", str(test_dir)]
        manager = DocumentsPathManager(is_gui_mode=False)
        manager.docs_name = "Fallout4"
        with patch.object(manager, "_update_game_setting") as mock_update:
            manager._get_manual_docs_path()
            mock_error.assert_called()
            mock_update.assert_called_once_with("Root_Folder_Docs", str(test_dir))

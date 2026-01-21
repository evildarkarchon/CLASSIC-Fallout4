"""Unit tests for PathDialogController.

This module tests the PathDialogController class that handles path selection
dialogs for game installation and documentation directories.

All tests in this module require Qt and cannot run in parallel workers.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


class TestPathDialogController:
    """Tests for PathDialogController class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.signal_hub = MagicMock()
        return context

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test PathDialogController can be created with proper initialization."""
        from ClassicLib.Interface.controllers.path_dialog import PathDialogController

        controller = PathDialogController(mock_context)

        assert controller is not None
        assert controller._ctx is mock_context

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_show_manual_docs_path_dialog(self, mock_dialog_class, mock_registry, mock_context):
        """Test show_manual_docs_path_dialog opens dialog and saves path."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import PathDialogController

        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog.get_path.return_value = "/path/to/docs"
        mock_dialog_class.return_value = mock_dialog
        mock_registry.get_game.return_value = "Fallout4"

        controller = PathDialogController(mock_context)
        controller.show_manual_docs_path_dialog()

        mock_dialog_class.assert_called_once()
        mock_dialog.exec.assert_called_once()
        mock_registry.register.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_show_manual_docs_path_dialog_cancelled(self, mock_dialog_class, mock_registry, mock_context):
        """Test show_manual_docs_path_dialog handles cancellation."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import PathDialogController

        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_class.return_value = mock_dialog
        mock_registry.get_game.return_value = "Fallout4"

        controller = PathDialogController(mock_context)
        controller.show_manual_docs_path_dialog()

        mock_registry.register.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_show_game_path_dialog(self, mock_dialog_class, mock_registry, mock_context):
        """Test show_game_path_dialog opens dialog and saves path."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import PathDialogController

        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog.get_path.return_value = "/path/to/game"
        mock_dialog_class.return_value = mock_dialog
        mock_registry.get_game.return_value = "Fallout4"

        controller = PathDialogController(mock_context)
        controller.show_game_path_dialog()

        mock_dialog_class.assert_called_once()
        mock_dialog.exec.assert_called_once()
        mock_registry.register.assert_called_once_with(mock_registry.Keys.GAME_PATH, "/path/to/game")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_show_game_path_dialog_cancelled(self, mock_dialog_class, mock_registry, mock_context):
        """Test show_game_path_dialog handles cancellation."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import PathDialogController

        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_class.return_value = mock_dialog
        mock_registry.get_game.return_value = "Fallout4"

        controller = PathDialogController(mock_context)
        controller.show_game_path_dialog()

        mock_registry.register.assert_not_called()


class TestShowGamePathDialogStatic:
    """Tests for show_game_path_dialog_static function."""

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_returns_valid_path(self, mock_dialog_class, mock_registry):
        """Test show_game_path_dialog_static returns valid game path."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import show_game_path_dialog_static

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create game executable
            game_exe = Path(tmpdir) / "Fallout4.exe"
            game_exe.write_text("fake exe")

            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_path.return_value = tmpdir
            mock_dialog_class.return_value = mock_dialog
            mock_registry.get_game.return_value = "Fallout4"
            mock_registry.get_vr.return_value = ""

            result = show_game_path_dialog_static()

            assert result == Path(tmpdir)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.msg_info")
    @patch("ClassicLib.Interface.controllers.path_dialog.QMessageBox")
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_shows_error_for_invalid_path(self, mock_dialog_class, mock_registry, mock_msgbox, mock_msg_info):
        """Test show_game_path_dialog_static shows error for invalid path."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import show_game_path_dialog_static

        with tempfile.TemporaryDirectory() as tmpdir:
            # No game executable, then user cancels and exits
            mock_dialog = MagicMock()
            # First: accept invalid path, then reject and exit
            mock_dialog.exec.side_effect = [
                QDialog.DialogCode.Accepted,
                QDialog.DialogCode.Rejected,
            ]
            mock_dialog.get_path.return_value = tmpdir
            mock_dialog_class.return_value = mock_dialog
            mock_registry.get_game.return_value = "Fallout4"
            mock_registry.get_vr.return_value = ""
            mock_msgbox.StandardButton.Yes = 1
            mock_msgbox.StandardButton.No = 0
            mock_msgbox.question.return_value = 1  # Yes, exit

            with pytest.raises(SystemExit):
                show_game_path_dialog_static()

            # Verify error was shown
            mock_msgbox.critical.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.QMessageBox")
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_loops_on_cancel_then_no(self, mock_dialog_class, mock_registry, mock_msgbox):
        """Test show_game_path_dialog_static loops when user clicks No on exit."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import show_game_path_dialog_static

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create game executable
            game_exe = Path(tmpdir) / "Fallout4.exe"
            game_exe.write_text("fake exe")

            mock_dialog = MagicMock()
            # First cancel (user clicks No to not exit), then accept valid path
            mock_dialog.exec.side_effect = [
                QDialog.DialogCode.Rejected,
                QDialog.DialogCode.Accepted,
            ]
            mock_dialog.get_path.return_value = tmpdir
            mock_dialog_class.return_value = mock_dialog
            mock_registry.get_game.return_value = "Fallout4"
            mock_registry.get_vr.return_value = ""
            mock_msgbox.StandardButton.Yes = 1
            mock_msgbox.StandardButton.No = 0
            mock_msgbox.question.return_value = 0  # No, don't exit

            result = show_game_path_dialog_static()

            assert result == Path(tmpdir)
            mock_msgbox.question.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.path_dialog.GlobalRegistry")
    @patch("ClassicLib.Interface.controllers.path_dialog.ManualPathDialog")
    def test_vr_suffix_in_exe_name(self, mock_dialog_class, mock_registry):
        """Test show_game_path_dialog_static includes VR suffix in exe name."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.path_dialog import show_game_path_dialog_static

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create VR game executable
            game_exe = Path(tmpdir) / "Fallout4VR.exe"
            game_exe.write_text("fake vr exe")

            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_path.return_value = tmpdir
            mock_dialog_class.return_value = mock_dialog
            mock_registry.get_game.return_value = "Fallout4"
            mock_registry.get_vr.return_value = "VR"

            result = show_game_path_dialog_static()

            assert result == Path(tmpdir)

"""
Unit tests for FolderManagement mixin.

This module tests the folder selection, validation, and path management
functionality with properly mocked Qt dialogs and file operations.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import ANY, Mock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QFileDialog, QLineEdit, QMessageBox

from ClassicLib.Interface.shared.FolderManagement import FolderManagementMixin


@pytest.mark.unit
@pytest.mark.gui
class TestFolderManagementMixin:
    """Unit tests for FolderManagementMixin class."""

    @pytest.fixture(autouse=True)
    def init_message_handler(self):
        """Initialize MessageHandler for tests that use msg_error."""
        from ClassicLib.messaging import handler as handler_module
        from ClassicLib.messaging import init_message_handler

        # Initialize message handler for non-GUI mode
        init_message_handler(parent=None, is_gui_mode=False)
        yield
        # Clean up the handler after test by resetting the module-level global
        handler_module._message_handler = None

    @pytest.fixture
    def mock_widget(self, qt_application):
        """Create a mock widget with FolderManagementMixin."""
        from PySide6.QtWidgets import QWidget

        # Create a test class that includes the mixin and inherits from QWidget
        class TestWidget(QWidget, FolderManagementMixin):
            def __init__(self):
                super().__init__()
                self.scan_folder_edit = QLineEdit()
                self.mods_folder_edit = QLineEdit()

        return TestWidget()

    @pytest.fixture
    def mock_widget_no_edits(self, qt_application):
        """Create a mock widget without edit fields."""
        from PySide6.QtWidgets import QWidget

        class TestWidget(QWidget, FolderManagementMixin):
            def __init__(self):
                super().__init__()
                self.scan_folder_edit = None
                self.mods_folder_edit = None

        return TestWidget()

    def test_select_folder_scan_valid_path(self, mock_widget, monkeypatch):
        """Test selecting a valid scan folder path."""
        test_path = "/valid/scan/path"

        # Mock dialog to return a valid path
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: test_path)

        # Mock validation function
        with (
            patch("ClassicLib.scanning.logs.util_legacy.is_valid_custom_scan_path", return_value=True),
            patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings,
        ):
            mock_widget.select_folder_scan()

            # Verify the path was set in the edit field
            assert mock_widget.scan_folder_edit.text() == test_path

            # Verify settings were saved
            mock_yaml_settings.assert_called_once()
            call_args = mock_yaml_settings.call_args
            assert call_args[0][2] == "CLASSIC_Settings.SCAN Custom Path"
            assert call_args[0][3] == test_path

    def test_select_folder_scan_invalid_path(self, mock_widget, monkeypatch):
        """Test selecting an invalid scan folder path shows warning."""
        invalid_path = "/Crash Logs/subfolder"
        valid_path = "/valid/path"

        # Mock dialog to return invalid path first, then valid path
        paths = [invalid_path, valid_path]
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: paths.pop(0) if paths else "")

        # Mock validation - invalid first, then valid
        validations = [False, True]

        def mock_validation(path):
            if path:
                return validations.pop(0)
            return False

        # Mock warning dialog
        mock_warning = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "warning", mock_warning)

        with (
            patch("ClassicLib.scanning.logs.util_legacy.is_valid_custom_scan_path", side_effect=mock_validation),
            patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings,
        ):
            mock_widget.select_folder_scan()

            # Verify warning was shown for invalid path
            mock_warning.assert_called_once()
            warning_args = mock_warning.call_args[0]
            assert "Invalid Custom Scan Path" in warning_args[1]
            assert "Crash Logs" in warning_args[2]

            # Verify valid path was eventually set
            assert mock_widget.scan_folder_edit.text() == valid_path
            mock_yaml_settings.assert_called_with(str, ANY, "CLASSIC_Settings.SCAN Custom Path", valid_path)

    def test_select_folder_scan_cancelled(self, mock_widget, monkeypatch):
        """Test cancelling folder selection dialog."""
        # Mock dialog to return empty string (cancelled)
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: "")

        with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings:
            mock_widget.select_folder_scan()

            # Verify nothing was changed
            assert mock_widget.scan_folder_edit.text() == ""
            mock_yaml_settings.assert_not_called()

    def test_validate_scan_folder_text_valid(self, mock_widget, monkeypatch):
        """Test validating manually entered valid scan folder text."""
        test_path = "/valid/existing/path"
        mock_widget.scan_folder_edit.setText(test_path)

        # Mock the helper functions directly to avoid Path mocking complexity
        with (
            patch("ClassicLib.Interface.shared.FolderManagement._is_valid_directory", return_value=True),
            patch("ClassicLib.Interface.shared.FolderManagement._normalize_path", return_value=Path(test_path)),
            patch("ClassicLib.scanning.logs.util_legacy.is_valid_custom_scan_path", return_value=True),
            patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings,
        ):
            mock_widget.validate_scan_folder_text()

            # Verify settings were saved with normalized path
            mock_yaml_settings.assert_called_once()
            call_args = mock_yaml_settings.call_args[0]
            assert call_args[2] == "CLASSIC_Settings.SCAN Custom Path"
            # Verify saved path matches test path (normalize path separators for comparison)
            saved_path = str(call_args[3]).replace("\\", "/")
            assert test_path in saved_path

    def test_validate_scan_folder_text_empty(self, mock_widget):
        """Test validating empty scan folder text clears the setting."""
        mock_widget.scan_folder_edit.setText("")

        with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings:
            mock_widget.validate_scan_folder_text()

            # Verify setting was cleared with space
            mock_yaml_settings.assert_called_once_with(str, ANY, "CLASSIC_Settings.SCAN Custom Path", " ")

    def test_validate_scan_folder_text_nonexistent(self, mock_widget, monkeypatch):
        """Test validating non-existent path shows warning and clears field."""
        nonexistent_path = "/nonexistent/path"
        mock_widget.scan_folder_edit.setText(nonexistent_path)

        mock_warning = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "warning", mock_warning)

        # Mock helper function to return False (path doesn't exist)
        with (
            patch("ClassicLib.Interface.shared.FolderManagement._is_valid_directory", return_value=False),
            patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings,
        ):
            mock_widget.validate_scan_folder_text()

            # Verify warning was shown
            mock_warning.assert_called_once()
            warning_args = mock_warning.call_args[0]
            assert "Invalid Path" in warning_args[1]
            assert "does not exist" in warning_args[2]

            # Verify field was cleared
            assert mock_widget.scan_folder_edit.text() == ""

            # Verify setting was cleared
            mock_yaml_settings.assert_called_with(str, ANY, "CLASSIC_Settings.SCAN Custom Path", "")

    def test_validate_scan_folder_text_restricted(self, mock_widget, monkeypatch):
        """Test validating restricted path shows warning and clears field."""
        restricted_path = "/Crash Logs"
        mock_widget.scan_folder_edit.setText(restricted_path)

        mock_warning = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "warning", mock_warning)

        # Mock the helper functions directly - path exists but is restricted
        with (
            patch("ClassicLib.Interface.shared.FolderManagement._is_valid_directory", return_value=True),
            patch("ClassicLib.scanning.logs.util_legacy.is_valid_custom_scan_path", return_value=False),
            patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings,
        ):
            mock_widget.validate_scan_folder_text()

            # Verify warning about restricted path
            mock_warning.assert_called_once()
            warning_args = mock_warning.call_args[0]
            assert "Invalid Custom Scan Path" in warning_args[1]
            assert "Crash Logs" in warning_args[2]

            # Verify field and setting were cleared
            assert mock_widget.scan_folder_edit.text() == ""
            mock_yaml_settings.assert_called_with(str, ANY, "CLASSIC_Settings.SCAN Custom Path", "")

    def test_validate_scan_folder_text_no_edit(self, mock_widget_no_edits):
        """Test validate_scan_folder_text when edit field is None."""
        # Should return early without error
        mock_widget_no_edits.validate_scan_folder_text()
        # No assertion needed - just verify no exception

    def test_select_folder_mods(self, mock_widget, monkeypatch):
        """Test selecting mods folder."""
        test_path = "/mods/folder"

        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: test_path)

        with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings:
            mock_widget.select_folder_mods()

            # Verify path was set
            assert mock_widget.mods_folder_edit.text() == test_path

            # Verify settings were saved
            mock_yaml_settings.assert_called_once_with(str, ANY, "CLASSIC_Settings.MODS Folder Path", test_path)

    def test_select_folder_mods_cancelled(self, mock_widget, monkeypatch):
        """Test cancelling mods folder selection."""
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: "")

        with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings:
            mock_widget.select_folder_mods()

            # Verify nothing changed
            assert mock_widget.mods_folder_edit.text() == ""
            mock_yaml_settings.assert_not_called()

    def test_initialize_folder_paths(self, mock_widget):
        """Test initializing folder paths from settings."""
        scan_path = "/saved/scan/path"
        mods_path = "/saved/mods/path"

        with patch("ClassicLib.io.yaml.classic_settings") as mock_settings:
            # Configure return values for different calls
            mock_settings.side_effect = [scan_path, mods_path]

            mock_widget.initialize_folder_paths()

            # Verify paths were set in edit fields
            assert mock_widget.scan_folder_edit.text() == scan_path
            assert mock_widget.mods_folder_edit.text() == mods_path

            # Verify settings were retrieved
            assert mock_settings.call_count == 2
            calls = mock_settings.call_args_list
            assert calls[0][0] == (str, "SCAN Custom Path")
            assert calls[1][0] == (str, "MODS Folder Path")

    def test_initialize_folder_paths_no_saved(self, mock_widget):
        """Test initializing when no saved paths exist."""
        with patch("ClassicLib.io.yaml.classic_settings", return_value=None):
            mock_widget.initialize_folder_paths()

            # Edit fields should remain empty
            assert mock_widget.scan_folder_edit.text() == ""
            assert mock_widget.mods_folder_edit.text() == ""

    def test_initialize_folder_paths_no_edits(self, mock_widget_no_edits):
        """Test initializing paths when edit fields are None."""
        with patch("ClassicLib.io.yaml.classic_settings", return_value="/some/path"):
            # Should not raise exception
            mock_widget_no_edits.initialize_folder_paths()

    def test_select_folder_ini(self, mock_widget, monkeypatch):
        """Test selecting INI folder path."""
        test_path = "/ini/folder"

        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: test_path)

        mock_info = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "information", mock_info)

        with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_settings:
            mock_widget.select_folder_ini()

            # Verify settings were saved
            mock_yaml_settings.assert_called_once_with(str, ANY, "CLASSIC_Settings.INI Folder Path", test_path)

            # Verify confirmation dialog
            mock_info.assert_called_once()
            info_args = mock_info.call_args[0]
            assert "New INI Path Set" in info_args[1]
            assert test_path in info_args[2]

    def test_open_settings_file_exists(self, mock_widget, tmp_path):
        """Test opening settings file when it exists."""
        settings_dir = tmp_path / "CLASSIC Data"
        settings_dir.mkdir()
        settings_file = settings_dir / "CLASSIC Settings.yaml"
        settings_file.write_text("test settings")

        with (
            patch("ClassicLib.Interface.shared.FolderManagement.get_local_dir", return_value=settings_dir),
            patch.object(mock_widget, "_open_file_with_notepadpp") as mock_open,
        ):
            mock_widget.open_settings()

            # Verify file was opened
            mock_open.assert_called_once_with(settings_file)

    def test_open_settings_file_missing(self, mock_widget, tmp_path, monkeypatch):
        """Test opening settings when file is missing shows error."""
        settings_dir = tmp_path / "CLASSIC Data"
        settings_dir.mkdir()

        mock_critical = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "critical", mock_critical)

        with patch("ClassicLib.Interface.shared.FolderManagement.get_local_dir", return_value=settings_dir):
            mock_widget.open_settings()

            # Verify error dialog was shown
            mock_critical.assert_called_once()
            error_args = mock_critical.call_args[0]
            assert "Settings File Missing" in error_args[1]
            assert "restart the application" in error_args[2]

    def test_open_backup_folder_exists(self, mock_widget, tmp_path, monkeypatch):
        """Test opening backup folder when it exists."""
        backup_dir = tmp_path / "CLASSIC Backup"
        backup_dir.mkdir()

        mock_open_url = Mock()
        monkeypatch.setattr("ClassicLib.Interface.shared.FolderManagement.QDesktopServices.openUrl", mock_open_url)

        with patch("ClassicLib.Interface.shared.FolderManagement.get_local_dir", return_value=tmp_path):
            mock_widget.open_backup_folder()

            # Verify folder was opened
            mock_open_url.assert_called_once()
            url = mock_open_url.call_args[0][0]
            assert isinstance(url, QUrl)
            # Convert paths to use consistent separators for comparison
            url_path = url.toLocalFile().replace("/", "\\")
            expected_path = str(backup_dir).replace("/", "\\")
            assert expected_path in url_path

    def test_open_backup_folder_not_exists(self, mock_widget, tmp_path):
        """Test opening backup folder when it doesn't exist shows error."""
        with (
            patch("ClassicLib.Interface.shared.FolderManagement.get_local_dir", return_value=tmp_path),
            patch("ClassicLib.Interface.shared.FolderManagement.msg_error") as mock_error,
        ):
            mock_widget.open_backup_folder()

            # Verify error message
            mock_error.assert_called_once_with("Backup folder has not been created yet.")

    def test_open_crash_logs_folder_exists(self, mock_widget, tmp_path, monkeypatch):
        """Test opening crash logs folder when it exists."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        mock_open_url = Mock()
        monkeypatch.setattr("ClassicLib.Interface.shared.FolderManagement.QDesktopServices.openUrl", mock_open_url)

        with patch("ClassicLib.Interface.shared.FolderManagement.get_local_dir", return_value=tmp_path):
            mock_widget.open_crash_logs_folder()

            # Verify folder was opened
            mock_open_url.assert_called_once()

    def test_open_crash_logs_folder_creates_if_missing(self, mock_widget, tmp_path, monkeypatch):
        """Test that crash logs folder is created if it doesn't exist."""
        mock_open_url = Mock()
        monkeypatch.setattr("ClassicLib.Interface.shared.FolderManagement.QDesktopServices.openUrl", mock_open_url)

        with patch("ClassicLib.Interface.shared.FolderManagement.get_local_dir", return_value=tmp_path):
            mock_widget.open_crash_logs_folder()

            # Verify folder was created
            crash_logs_dir = tmp_path / "Crash Logs"
            assert crash_logs_dir.exists()
            assert crash_logs_dir.is_dir()

            # Verify it was opened
            mock_open_url.assert_called_once()

    @pytest.mark.skipif(os.environ.get("CI") is not None, reason="Notepad++ not available in CI environment")
    def test_open_file_with_notepadpp_exists(self, tmp_path, monkeypatch):
        """Test opening file with Notepad++ when it exists."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Mock Notepad++ existence
        mock_notepadpp = Mock(spec=Path)
        mock_notepadpp.exists.return_value = True

        mock_popen = Mock()
        monkeypatch.setattr(subprocess, "Popen", mock_popen)

        with patch("pathlib.Path") as mock_path_class:
            # Configure Path constructor behavior
            def path_side_effect(path_str):
                if "Notepad++" in str(path_str):
                    return mock_notepadpp
                return Path(path_str)

            mock_path_class.side_effect = path_side_effect

            FolderManagementMixin._open_file_with_notepadpp(test_file)

            # Verify Notepad++ was launched
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert "notepad++.exe" in call_args[0]
            assert str(test_file) in call_args

    def test_open_file_with_notepadpp_fallback(self, tmp_path, monkeypatch):
        """Test fallback to system default when Notepad++ doesn't exist."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Mock QDesktopServices.openUrl to prevent actual file opening
        mock_open_url = Mock()
        monkeypatch.setattr("ClassicLib.Interface.shared.FolderManagement.QDesktopServices.openUrl", mock_open_url)

        # Mock Path.exists for the notepad++ check
        original_exists = Path.exists

        def mock_exists(self):
            if "Notepad++" in str(self):
                return False  # Notepad++ doesn't exist
            return original_exists(self)

        with patch.object(Path, "exists", mock_exists):
            FolderManagementMixin._open_file_with_notepadpp(test_file)

            # Verify system default was used (QDesktopServices.openUrl was called)
            mock_open_url.assert_called_once()
            # Check the URL contains the test file path
            call_args = mock_open_url.call_args[0][0]
            assert isinstance(call_args, QUrl)
            # The URL was created so we can verify it was called

    def test_open_file_notepadpp_error_fallback(self, tmp_path, monkeypatch):
        """Test fallback when Notepad++ launch fails."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Mock Notepad++ exists but launch fails
        mock_notepadpp = Mock(spec=Path)
        mock_notepadpp.exists.return_value = True

        mock_popen = Mock(side_effect=OSError("Launch failed"))
        monkeypatch.setattr(subprocess, "Popen", mock_popen)

        mock_open_url = Mock()
        monkeypatch.setattr("ClassicLib.Interface.shared.FolderManagement.QDesktopServices.openUrl", mock_open_url)

        with patch("pathlib.Path") as mock_path_class:

            def path_side_effect(path_str):
                if "Notepad++" in str(path_str):
                    return mock_notepadpp
                return Path(path_str)

            mock_path_class.side_effect = path_side_effect

            FolderManagementMixin._open_file_with_notepadpp(test_file)

            # Verify fallback was used after error
            mock_open_url.assert_called_once()

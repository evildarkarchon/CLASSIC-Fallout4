"""Unit tests for ResultsViewerMixin UI operations.

Tests the UI interactions, context menus, and user operations
in isolation with mocked Qt components.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import pytest
from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from ClassicLib import MessageHandler
from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin
from tests.fixtures.registry_fixtures import init_message_handler_fixture  # noqa: F401


@pytest.fixture
def mock_qt_components():
    """Mock Qt components for testing."""
    with patch("ClassicLib.Interface.ResultsViewerMixin.QFileSystemWatcher") as mock_watcher, \
         patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer:

        # Setup watcher mock
        watcher_instance = MagicMock(spec=QFileSystemWatcher)
        watcher_instance.directories.return_value = []
        mock_watcher.return_value = watcher_instance

        # Setup timer mock
        timer_instance = MagicMock(spec=QTimer)
        mock_timer.return_value = timer_instance

        yield {
            "watcher": watcher_instance,
            "timer": timer_instance,
            "watcher_class": mock_watcher,
            "timer_class": mock_timer
        }


@pytest.fixture
def viewer_mixin(mock_qt_components, init_message_handler_fixture):
    """Create a ResultsViewerMixin instance with mocked dependencies."""

    class TestViewer(ResultsViewerMixin):
        """Test class that includes the mixin."""

        def __init__(self):
            # Mock required attributes
            self.results_tab = MagicMock(spec=QWidget)
            self.results_list = MagicMock()
            # Mock count() to return an integer, not a MagicMock
            self.results_list.count.return_value = 0
            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()

            # Initialize signals with emit method
            self.report_loaded = MagicMock(spec=Signal)
            self.report_loaded.emit = MagicMock()
            self.reports_refreshed = MagicMock(spec=Signal)
            self.reports_refreshed.emit = MagicMock()

    viewer = TestViewer()
    viewer.file_watcher = mock_qt_components["watcher"]
    viewer.refresh_timer = mock_qt_components["timer"]
    viewer.current_report_path = None

    return viewer


@pytest.mark.unit
@pytest.mark.gui
class TestReportSelection:
    """Tests for report selection handling."""

    def test_on_report_selected_with_valid_item(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should load report when valid item selected."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_path.write_text("Test content")

        mock_item = MagicMock()
        viewer_mixin.results_list.selectedItems.return_value = [mock_item]
        viewer_mixin.results_list.get_report_path.return_value = report_path

        with patch.object(viewer_mixin, "load_report") as mock_load:
            viewer_mixin._on_report_selected()

            mock_load.assert_called_once_with(report_path)

    def test_on_report_selected_no_items(self, viewer_mixin, gui_message_handler):
        """Should do nothing when no items selected."""
        viewer_mixin.results_list.selectedItems.return_value = []

        with patch.object(viewer_mixin, "load_report") as mock_load:
            viewer_mixin._on_report_selected()

            mock_load.assert_not_called()

    def test_on_report_selected_null_path(self, viewer_mixin, gui_message_handler):
        """Should not load when get_report_path returns None."""
        mock_item = MagicMock()
        viewer_mixin.results_list.selectedItems.return_value = [mock_item]
        viewer_mixin.results_list.get_report_path.return_value = None

        with patch.object(viewer_mixin, "load_report") as mock_load:
            viewer_mixin._on_report_selected()

            mock_load.assert_not_called()


@pytest.mark.unit
@pytest.mark.gui
class TestReportDeletion:
    """Tests for report deletion operations."""

    def test_delete_selected_report_with_confirmation(self, viewer_mixin, gui_message_handler):
        """Should delete report after user confirmation."""
        # Create mock path objects
        mock_report_path = MagicMock(spec=Path)
        mock_report_path.name = "test-AUTOSCAN.md"
        mock_report_path.exists.return_value = True

        # Create mock crash log path that doesn't exist
        mock_crash_log_path = MagicMock(spec=Path)
        mock_crash_log_path.exists.return_value = False
        mock_report_path.with_suffix.return_value = mock_crash_log_path

        # Setup mocks
        viewer_mixin.results_list.selectedItems.return_value = [MagicMock()]
        viewer_mixin.results_list.get_report_path.return_value = mock_report_path
        viewer_mixin.current_report_path = mock_report_path

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMessageBox") as mock_msgbox, \
             patch("ClassicLib.Interface.ResultsViewerMixin.msg_info") as mock_info, \
             patch.object(viewer_mixin, "refresh_reports_list") as mock_refresh:

            # Set up StandardButton enum on the mock
            mock_msgbox.StandardButton = QMessageBox.StandardButton
            mock_msgbox.question.return_value = QMessageBox.StandardButton.Yes

            viewer_mixin._delete_selected_report()

            # Verify unlink called on path
            mock_report_path.unlink.assert_called_once()

            # Verify UI updated
            viewer_mixin.markdown_viewer.clear.assert_called()
            viewer_mixin.metadata_widget.clear.assert_called()
            assert viewer_mixin.current_report_path is None
            mock_refresh.assert_called_once()
            mock_info.assert_called_once()

    def test_delete_selected_report_cancelled(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should not delete if user cancels."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_path.write_text("Report")

        viewer_mixin.results_list.selectedItems.return_value = [MagicMock()]
        viewer_mixin.results_list.get_report_path.return_value = report_path

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMessageBox") as mock_msgbox:
            mock_msgbox.StandardButton = QMessageBox.StandardButton
            mock_msgbox.question.return_value = QMessageBox.StandardButton.No

            viewer_mixin._delete_selected_report()

            # File should still exist
            assert report_path.exists()

    def test_delete_no_selection(self, viewer_mixin, gui_message_handler):
        """Should show warning when no report selected."""
        viewer_mixin.results_list.selectedItems.return_value = []

        with patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning:
            viewer_mixin._delete_selected_report()

            mock_warning.assert_called_once_with("No report selected")


@pytest.mark.unit
@pytest.mark.gui
class TestReportOperations:
    """Tests for report operations like copy and open folder."""

    def test_copy_report_to_clipboard(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should copy report content to clipboard."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_content = "Report content"
        report_path.write_text(report_content)

        viewer_mixin.current_report_path = report_path

        with patch("PySide6.QtWidgets.QApplication") as mock_app, \
             patch("ClassicLib.Interface.ResultsViewerMixin.msg_info") as mock_info:

            mock_clipboard = MagicMock()
            mock_app.clipboard.return_value = mock_clipboard

            viewer_mixin._copy_report()

            mock_clipboard.setText.assert_called_with(report_content)
            mock_info.assert_called_once()

    def test_copy_report_no_report_loaded(self, viewer_mixin, gui_message_handler):
        """Should show warning when no report is loaded."""
        viewer_mixin.current_report_path = None

        with patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning:
            viewer_mixin._copy_report()

            mock_warning.assert_called_once_with("No report loaded")

    def test_copy_report_handles_read_error(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should handle errors when reading report for clipboard."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        viewer_mixin.current_report_path = report_path

        with patch.object(Path, "read_text", side_effect=IOError("Read error")), \
             patch("ClassicLib.Interface.ResultsViewerMixin.msg_error") as mock_error:

            viewer_mixin._copy_report()

            mock_error.assert_called_once()

    def test_open_reports_folder(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should open reports folder in file explorer."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        with patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry, \
             patch("PySide6.QtGui.QDesktopServices") as mock_desktop:

            mock_registry.get_local_dir.return_value = str(tmp_path)

            viewer_mixin._open_reports_folder()

            mock_desktop.openUrl.assert_called_once()

    def test_open_reports_folder_no_local_dir(self, viewer_mixin, gui_message_handler):
        """Should show warning when local directory not configured."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry, \
             patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning:

            mock_registry.get_local_dir.return_value = None

            viewer_mixin._open_reports_folder()

            mock_warning.assert_called_once_with("Local directory not configured")

    def test_open_reports_folder_not_exists(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should show warning when Crash Logs folder doesn't exist."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry, \
             patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning:

            mock_registry.get_local_dir.return_value = str(tmp_path)
            # Crash Logs directory not created

            viewer_mixin._open_reports_folder()

            mock_warning.assert_called_once_with("Crash Logs folder does not exist")


@pytest.mark.unit
@pytest.mark.gui
class TestContextMenu:
    """Tests for context menu functionality."""

    def test_show_context_menu_with_item(self, viewer_mixin, gui_message_handler):
        """Should show context menu with all actions when item selected."""
        mock_item = MagicMock()
        mock_position = MagicMock()

        viewer_mixin.results_list.itemAt.return_value = mock_item

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMenu") as mock_menu_class, \
             patch("ClassicLib.Interface.ResultsViewerMixin.QAction") as mock_action_class:

            mock_menu = MagicMock()
            mock_menu_class.return_value = mock_menu

            viewer_mixin._show_context_menu(mock_position)

            # Verify menu created
            mock_menu_class.assert_called_once_with(viewer_mixin.results_list)

            # Verify actions added (3 actions + 2 separators)
            assert mock_menu.addAction.call_count == 3
            assert mock_menu.addSeparator.call_count == 2

            # Verify menu shown
            mock_menu.exec.assert_called_once()

    def test_show_context_menu_no_item(self, viewer_mixin, gui_message_handler):
        """Should not show menu when no item at position."""
        viewer_mixin.results_list.itemAt.return_value = None

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMenu") as mock_menu_class:
            viewer_mixin._show_context_menu(MagicMock())

            # Menu should not be created
            mock_menu_class.assert_not_called()


@pytest.mark.unit
@pytest.mark.gui
class TestAutoRefresh:
    """Tests for auto-refresh functionality."""

    def test_setup_auto_refresh_enabled(self, viewer_mixin, gui_message_handler):
        """Should enable auto-refresh when configured."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:
            mock_settings.side_effect = [True, 5000]  # Enabled, 5 second interval

            viewer_mixin._setup_auto_refresh()

            viewer_mixin.refresh_timer.start.assert_called_with(5000)

    def test_setup_auto_refresh_disabled(self, viewer_mixin, gui_message_handler):
        """Should not start timer when auto-refresh is disabled."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:
            mock_settings.return_value = False

            viewer_mixin._setup_auto_refresh()

            viewer_mixin.refresh_timer.start.assert_not_called()

    def test_setup_auto_refresh_with_default_interval(self, viewer_mixin, gui_message_handler):
        """Should use default interval when not configured."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:
            # First call returns True (enabled), second uses default
            mock_settings.side_effect = [True, 5000]

            viewer_mixin._setup_auto_refresh()

            viewer_mixin.refresh_timer.start.assert_called_with(5000)

    def test_directory_changed_triggers_debounced_refresh(self, viewer_mixin, gui_message_handler):
        """Should debounce rapid directory changes."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer:
            viewer_mixin._on_directory_changed("/some/path")

            # Should schedule debounced refresh
            mock_timer.singleShot.assert_called_with(500, viewer_mixin._debounced_refresh)

            # Second call should not schedule another
            viewer_mixin._on_directory_changed("/some/path")
            assert mock_timer.singleShot.call_count == 1

    def test_debounced_refresh_clears_pending_flag(self, viewer_mixin, gui_message_handler):
        """Should clear pending flag after refresh."""
        viewer_mixin._refresh_pending = True

        with patch.object(viewer_mixin, "refresh_reports_list") as mock_refresh:
            viewer_mixin._debounced_refresh()

            assert viewer_mixin._refresh_pending is False
            mock_refresh.assert_called_once()

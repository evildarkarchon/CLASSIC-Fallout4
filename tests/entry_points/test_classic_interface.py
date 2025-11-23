"""Tests for CLASSIC_Interface.py GUI entry point.

This module tests the GUI application initialization, window setup,
and component integration for the main CLASSIC interface.
"""

# ruff: noqa: PLR6301, ARG002

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mark all tests in this module as GUI tests
pytestmark = [pytest.mark.gui, pytest.mark.unit]


class TestClassicInterface:
    """Test suite for CLASSIC_Interface.py GUI entry point."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up test environment."""
        # Clear any existing QApplication instances
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            app.quit()

    @patch("CLASSIC_Interface.SetupCoordinator")
    @patch("CLASSIC_Interface.QApplication")
    def test_main_entry_point_initialization(self, mock_qapp: Mock, mock_setup_coordinator: Mock) -> None:
        """Test that the main entry point initializes correctly."""
        # Arrange
        mock_app_instance = MagicMock()
        mock_qapp.return_value = mock_app_instance
        mock_qapp.instance.return_value = None  # No existing app
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance

        # Act
        with patch("CLASSIC_Interface.MainWindow") as mock_window_class, patch.object(sys, "exit") as mock_exit:
            mock_window = MagicMock()
            mock_window_class.return_value = mock_window
            mock_app_instance.exec.return_value = 0

            # Simulate running main function
            with patch.object(sys, "argv", ["test"]):
                import CLASSIC_Interface

                CLASSIC_Interface.main()

        # Assert
        mock_setup_coordinator.assert_called_once()
        mock_coordinator_instance.initialize_application.assert_called_once_with(is_gui=True)
        mock_window_class.assert_called_once()
        mock_window.show.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("CLASSIC_Interface.GlobalRegistry")
    @patch("CLASSIC_Interface.init_message_handler")
    @patch("CLASSIC_Interface.yaml_settings")
    @patch("CLASSIC_Interface.classic_settings")
    def test_main_window_initialization(
        self, mock_classic_settings: Mock, mock_yaml_settings: Mock, mock_init_msg_handler: Mock, mock_global_registry: Mock
    ) -> None:
        """Test MainWindow initialization and component setup."""
        from PySide6.QtWidgets import QApplication

        from CLASSIC_Interface import MainWindow

        # Arrange
        _ = QApplication.instance() or QApplication([])
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = False  # Disable update check
        mock_global_registry.get_local_dir.return_value = Path()

        # Act
        with (
            patch.object(MainWindow, "setup_main_tab"),
            patch.object(MainWindow, "setup_backups_tab"),
            patch.object(MainWindow, "setup_articles_tab"),
            patch.object(MainWindow, "setup_results_tab"),
            patch.object(MainWindow, "setup_window_geometry"),
            patch.object(MainWindow, "initialize_folder_paths"),
        ):
            window = MainWindow()

        # Assert
        assert window.windowTitle() == "Crash Log Auto Scanner & Setup Integrity Checker | 1.0.0"
        assert window.tab_widget is not None
        assert window.tab_widget.count() == 4
        assert window.tab_widget.tabText(0) == "MAIN OPTIONS"
        assert window.tab_widget.tabText(1) == "FILE BACKUP"
        assert window.tab_widget.tabText(2) == "ARTICLES"
        assert window.tab_widget.tabText(3) == "RESULTS"
        mock_init_msg_handler.assert_called_once_with(parent=window, is_gui_mode=True)

    def test_main_window_mixins_inheritance(self) -> None:
        """Test that MainWindow properly inherits from all required mixins."""
        from CLASSIC_Interface import MainWindow
        from ClassicLib.Interface.BackupOperations import BackupOperationsMixin
        from ClassicLib.Interface.FolderManagementMixin import FolderManagementMixin
        from ClassicLib.Interface.HelpAndAboutMixin import HelpAndAboutMixin
        from ClassicLib.Interface.PapyrusManager import PapyrusManagerMixin
        from ClassicLib.Interface.PastebinMixin import PastebinMixin
        from ClassicLib.Interface.PathDialogMixin import PathDialogMixin
        from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin
        from ClassicLib.Interface.ScanOperations import ScanOperationsMixin
        from ClassicLib.Interface.TabSetupMixin import TabSetupMixin
        from ClassicLib.Interface.UpdateManager import UpdateManagerMixin
        from ClassicLib.Interface.WindowGeometryMixin import WindowGeometryMixin

        # Assert all mixins are properly inherited
        assert issubclass(MainWindow, ScanOperationsMixin)
        assert issubclass(MainWindow, UpdateManagerMixin)
        assert issubclass(MainWindow, FolderManagementMixin)
        assert issubclass(MainWindow, BackupOperationsMixin)
        assert issubclass(MainWindow, PapyrusManagerMixin)
        assert issubclass(MainWindow, PastebinMixin)
        assert issubclass(MainWindow, PathDialogMixin)
        assert issubclass(MainWindow, TabSetupMixin)
        assert issubclass(MainWindow, ResultsViewerMixin)
        assert issubclass(MainWindow, HelpAndAboutMixin)
        assert issubclass(MainWindow, WindowGeometryMixin)

    @patch("CLASSIC_Interface.classic_settings")
    @patch("CLASSIC_Interface.yaml_settings")
    @patch("CLASSIC_Interface.GlobalRegistry")
    def test_main_window_update_check_timer(
        self, mock_global_registry: Mock, mock_yaml_settings: Mock, mock_classic_settings: Mock
    ) -> None:
        """Test update check timer initialization."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        from CLASSIC_Interface import MainWindow

        # Arrange
        _ = QApplication.instance() or QApplication([])
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = True  # Enable update check
        mock_global_registry.get_local_dir.return_value = Path()

        # Act
        with (
            patch.object(MainWindow, "setup_main_tab"),
            patch.object(MainWindow, "setup_backups_tab"),
            patch.object(MainWindow, "setup_articles_tab"),
            patch.object(MainWindow, "setup_results_tab"),
            patch.object(MainWindow, "setup_window_geometry"),
            patch.object(MainWindow, "initialize_folder_paths"),
            patch.object(QTimer, "singleShot") as mock_timer,
        ):
            window = MainWindow()

        # Assert
        assert hasattr(window, "update_check_timer")
        assert window.update_check_timer is not None
        assert not window.is_update_check_running
        mock_timer.assert_called_once_with(0, window.update_popup)

    @patch("CLASSIC_Interface.logger")
    @patch("CLASSIC_Interface.classic_settings")
    @patch("CLASSIC_Interface.yaml_settings")
    @patch("CLASSIC_Interface.GlobalRegistry")
    def test_main_window_close_event(
        self, mock_global_registry: Mock, mock_yaml_settings: Mock, mock_classic_settings: Mock, mock_logger: Mock
    ) -> None:
        """Test proper cleanup during window close."""
        from PySide6.QtWidgets import QApplication

        from CLASSIC_Interface import MainWindow

        # Arrange
        _ = QApplication.instance() or QApplication([])
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = False
        with (
            patch.object(MainWindow, "setup_main_tab"),
            patch.object(MainWindow, "setup_backups_tab"),
            patch.object(MainWindow, "setup_articles_tab"),
            patch.object(MainWindow, "setup_results_tab"),
            patch.object(MainWindow, "setup_window_geometry"),
            patch.object(MainWindow, "initialize_folder_paths"),
        ):
            window = MainWindow()

        # Setup mock event
        mock_event = MagicMock()
        window.papyrus_monitor_worker = MagicMock()

        # Act
        with (
            patch.object(window, "save_current_tab_geometry") as mock_save,
            patch.object(window, "stop_papyrus_monitoring") as mock_stop_papyrus,
            patch.object(window.thread_manager, "stop_all_threads") as mock_stop_threads,
        ):
            window.closeEvent(mock_event)

        # Assert
        mock_logger.info.assert_any_call("Application closing - cleaning up resources...")
        mock_save.assert_called_once()
        mock_stop_papyrus.assert_called_once()
        mock_stop_threads.assert_called_once_with(wait_ms=3000)
        mock_event.accept.assert_called_once()
        mock_logger.info.assert_any_call("Resource cleanup completed")

    def test_open_url_static_method(self) -> None:
        """Test the open_url static method."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QApplication

        from CLASSIC_Interface import MainWindow

        # Arrange
        _ = QApplication.instance() or QApplication([])
        test_url = "https://example.com"

        # Act
        with patch.object(QDesktopServices, "openUrl") as mock_open:
            MainWindow.open_url(test_url)

        # Assert
        mock_open.assert_called_once()
        call_args = mock_open.call_args[0][0]
        assert isinstance(call_args, QUrl)
        assert call_args.toString() == test_url

    @patch("CLASSIC_Interface.SetupCoordinator")
    @patch("CLASSIC_Interface.QApplication")
    def test_keyboard_interrupt_handling(self, mock_qapp: Mock, mock_setup_coordinator: Mock) -> None:
        """Test proper handling of keyboard interrupt."""
        # Arrange
        mock_app_instance = MagicMock()
        mock_qapp.return_value = mock_app_instance
        mock_app_instance.exec.side_effect = KeyboardInterrupt()

        # Act & Assert
        with patch("CLASSIC_Interface.MainWindow"), patch.object(sys, "exit"), patch.object(sys, "argv", ["test"]):
            import CLASSIC_Interface

            CLASSIC_Interface.main()

        # Should exit with code 1 on KeyboardInterrupt
        mock_app_instance.exit.assert_called_once_with(1)

    @patch("CLASSIC_Interface.msg_error")
    @patch("CLASSIC_Interface.QMessageBox")
    @patch("CLASSIC_Interface.SetupCoordinator")
    @patch("CLASSIC_Interface.QApplication")
    def test_unhandled_exception_handling(
        self, mock_qapp: Mock, mock_setup_coordinator: Mock, mock_msgbox: Mock, mock_msg_error: Mock
    ) -> None:
        """Test proper handling of unhandled exceptions during startup."""
        # Arrange
        mock_app_instance = MagicMock()
        mock_qapp.return_value = mock_app_instance
        mock_qapp.instance.return_value = mock_app_instance
        test_exception = Exception("Test startup error")

        # Act
        with (
            patch("CLASSIC_Interface.MainWindow", side_effect=test_exception),
            patch.object(sys, "argv", ["test"]),
            patch.object(sys, "exit") as mock_exit,
        ):
            import CLASSIC_Interface

            CLASSIC_Interface.main()

        # Assert
        mock_msg_error.assert_called_once()
        assert "Unhandled exception during application startup" in str(mock_msg_error.call_args)
        mock_msgbox.critical.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch("CLASSIC_Interface.GlobalRegistry")
    @patch("CLASSIC_Interface.classic_settings")
    @patch("CLASSIC_Interface.yaml_settings")
    def test_thread_manager_initialization(self, mock_yaml_settings: Mock, mock_classic_settings: Mock, mock_global_registry: Mock) -> None:
        """Test that thread manager is properly initialized."""
        from PySide6.QtWidgets import QApplication

        from CLASSIC_Interface import MainWindow

        # Arrange
        _ = QApplication.instance() or QApplication([])
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = False
        mock_global_registry.get_local_dir.return_value = Path()

        # Act
        with (
            patch.object(MainWindow, "setup_main_tab"),
            patch.object(MainWindow, "setup_backups_tab"),
            patch.object(MainWindow, "setup_articles_tab"),
            patch.object(MainWindow, "setup_results_tab"),
            patch.object(MainWindow, "setup_window_geometry"),
            patch.object(MainWindow, "initialize_folder_paths"),
        ):
            window = MainWindow()

        # Assert
        assert hasattr(window, "thread_manager")
        assert window.thread_manager is not None
        assert hasattr(window, "audio_player")
        assert window.audio_player is not None
        assert hasattr(window, "_scan_mutex")
        assert window._scan_mutex is not None
        assert hasattr(window, "_running_scans")
        assert isinstance(window._running_scans, set)

"""Tests for CLASSIC_Interface.py GUI entry point.

This module tests the GUI application initialization, window setup,
and component integration for the main CLASSIC interface.
"""

# ruff: noqa: PLR6301, ARG002

import os
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mark all tests in this module as GUI tests
pytestmark = [pytest.mark.gui, pytest.mark.unit]


@pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests unstable in xdist workers on Windows")
class TestClassicInterface:
    """Test suite for CLASSIC_Interface.py GUI entry point."""

    @pytest.fixture(autouse=True)
    def setup(self, qt_application) -> Generator[None, None, None]:
        """Set up test environment.

        Args:
            qt_application: Session-scoped QApplication from qt_fixtures.py.
                Using this fixture ensures proper Qt lifecycle management and
                AsyncBridge cleanup between tests.
        """
        from ClassicLib.MessageHandler.handler import _message_handler_lock

        # Shutdown any existing AsyncBridge instances BEFORE patching.
        # This is critical because patching the class doesn't stop already-running
        # background threads, which can cause access violations on Windows.
        try:
            if "ClassicLib.AsyncBridge" in sys.modules:
                from ClassicLib.AsyncBridge import AsyncBridge

                # Shutdown all existing instances
                if hasattr(AsyncBridge, "_instances") and AsyncBridge._instances:
                    for instance in list(AsyncBridge._instances.values()):
                        try:
                            instance.shutdown()
                        except Exception:
                            pass  # Ignore shutdown errors
                    with AsyncBridge._lock:
                        AsyncBridge._instances.clear()
        except Exception:
            pass  # Ignore if AsyncBridge not available

        # Patch AsyncBridge to prevent new background threads from starting
        patcher = patch("ClassicLib.AsyncBridge.AsyncBridge")
        patcher.start()

        # Reset MessageHandler singleton to prevent dangling parent references
        from ClassicLib.MessageHandler import handler as msg_handler_module

        with _message_handler_lock:
            msg_handler_module._message_handler = None

        yield

        # Cleanup after test
        with _message_handler_lock:
            msg_handler_module._message_handler = None

        patcher.stop()

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

    @patch("CLASSIC_Interface.QTimer")
    @patch("CLASSIC_Interface.GlobalRegistry")
    @patch("CLASSIC_Interface.init_message_handler")
    @patch("CLASSIC_Interface.yaml_settings")
    @patch("CLASSIC_Interface.classic_settings")
    @patch("CLASSIC_Interface.get_thread_manager")
    def test_main_window_initialization(
        self,
        mock_get_thread_manager: Mock,
        mock_classic_settings: Mock,
        mock_yaml_settings: Mock,
        mock_init_msg_handler: Mock,
        mock_global_registry: Mock,
        mock_qtimer: Mock,
    ) -> None:
        """Test MainWindow initialization and component setup."""
        from CLASSIC_Interface import MainWindow

        # Arrange - QApplication is managed by qt_application fixture via setup
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = False  # Disable update check
        mock_global_registry.get_local_dir.return_value = Path()
        mock_get_thread_manager.return_value = MagicMock()
        # Mock QTimer to prevent access violations on Windows offscreen platform
        mock_timer_instance = MagicMock()
        mock_qtimer.return_value = mock_timer_instance

        # Act - patch UISetupController to avoid complex UI initialization
        with patch("CLASSIC_Interface.UISetupController") as mock_ui_setup:
            mock_ui_setup_instance = MagicMock()
            mock_ui_setup.return_value = mock_ui_setup_instance
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

    def test_main_window_composition_architecture(self) -> None:
        """Test that MainWindow uses composition-based controller architecture."""
        from CLASSIC_Interface import MainWindow
        from ClassicLib.Interface.controllers.backup_manager import BackupManager
        from ClassicLib.Interface.controllers.folder_manager import FolderManager
        from ClassicLib.Interface.controllers.help_about import HelpAboutController
        from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager
        from ClassicLib.Interface.controllers.pastebin_controller import PastebinController
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController
        from ClassicLib.Interface.controllers.scan_controller import ScanController
        from ClassicLib.Interface.controllers.ui_setup import UISetupController
        from ClassicLib.Interface.controllers.update_manager import UpdateManager
        from ClassicLib.Interface.controllers.window_geometry import WindowGeometryManager

        # MainWindow should NOT inherit from mixins (composition architecture)
        assert not any(
            "Mixin" in base.__name__ for base in MainWindow.__mro__ if hasattr(base, "__name__")
        ), "MainWindow should not inherit from mixin classes"

        # MainWindow should use QMainWindow as base
        from PySide6.QtWidgets import QMainWindow
        assert issubclass(MainWindow, QMainWindow), "MainWindow should inherit from QMainWindow"

        # Verify controller class imports work (architecture is in place)
        assert ScanController is not None
        assert UpdateManager is not None
        assert FolderManager is not None
        assert BackupManager is not None
        assert PapyrusManager is not None
        assert PastebinController is not None
        assert ResultsViewerController is not None
        assert HelpAboutController is not None
        assert WindowGeometryManager is not None
        assert UISetupController is not None

    @patch("CLASSIC_Interface.QTimer")
    @patch("CLASSIC_Interface.classic_settings")
    @patch("CLASSIC_Interface.yaml_settings")
    @patch("CLASSIC_Interface.GlobalRegistry")
    @patch("CLASSIC_Interface.get_thread_manager")
    def test_main_window_update_check_timer(
        self,
        mock_get_thread_manager: Mock,
        mock_global_registry: Mock,
        mock_yaml_settings: Mock,
        mock_classic_settings: Mock,
        mock_qtimer: Mock,
    ) -> None:
        """Test update check timer initialization."""
        from CLASSIC_Interface import MainWindow

        # Arrange - QApplication is managed by qt_application fixture via setup
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = True  # Enable update check
        mock_global_registry.get_local_dir.return_value = Path()
        mock_get_thread_manager.return_value = MagicMock()
        # Mock QTimer to prevent access violations on Windows offscreen platform
        mock_timer_instance = MagicMock()
        mock_qtimer.return_value = mock_timer_instance

        # Act - patch UISetupController to avoid complex UI initialization
        with patch("CLASSIC_Interface.UISetupController") as mock_ui_setup:
            mock_ui_setup_instance = MagicMock()
            mock_ui_setup.return_value = mock_ui_setup_instance
            window = MainWindow()

        # Assert - update check should be triggered via singleShot
        # In the new architecture, update check is handled by UpdateManager controller
        assert hasattr(window, "update_manager")
        mock_qtimer.singleShot.assert_called_once()

    @patch("CLASSIC_Interface.QTimer")
    @patch("CLASSIC_Interface.logger")
    @patch("CLASSIC_Interface.classic_settings")
    @patch("CLASSIC_Interface.yaml_settings")
    @patch("CLASSIC_Interface.GlobalRegistry")
    @patch("CLASSIC_Interface.get_thread_manager")
    def test_main_window_close_event(
        self,
        mock_get_thread_manager: Mock,
        mock_global_registry: Mock,
        mock_yaml_settings: Mock,
        mock_classic_settings: Mock,
        mock_logger: Mock,
        mock_qtimer: Mock,
    ) -> None:
        """Test proper cleanup during window close."""
        from CLASSIC_Interface import MainWindow

        # Arrange - QApplication is managed by qt_application fixture via setup
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = False
        mock_global_registry.get_local_dir.return_value = Path()
        mock_thread_manager = MagicMock()
        mock_get_thread_manager.return_value = mock_thread_manager
        # Mock QTimer to prevent access violations on Windows offscreen platform
        mock_timer_instance = MagicMock()
        mock_qtimer.return_value = mock_timer_instance

        # Create window with mocked UISetupController
        with patch("CLASSIC_Interface.UISetupController") as mock_ui_setup:
            mock_ui_setup_instance = MagicMock()
            mock_ui_setup.return_value = mock_ui_setup_instance
            window = MainWindow()

        # Setup mock event
        mock_event = MagicMock()

        # Act
        with (
            patch.object(window.window_geometry, "save_current_tab_geometry") as mock_save,
            patch.object(window.papyrus_manager, "is_monitoring", return_value=True),
            patch.object(window.papyrus_manager, "stop_monitoring") as mock_stop_papyrus,
            patch.object(window.thread_manager, "stop_all_threads") as mock_stop_threads,
            patch.object(window.update_manager, "stop_timer") as mock_stop_timer,
        ):
            window.closeEvent(mock_event)

        # Assert
        mock_logger.info.assert_any_call("Application closing - cleaning up resources...")
        mock_save.assert_called_once()
        mock_stop_papyrus.assert_called_once()
        mock_stop_threads.assert_called_once_with(wait_ms=3000)
        mock_stop_timer.assert_called_once()
        mock_event.accept.assert_called_once()
        mock_logger.info.assert_any_call("Resource cleanup completed")

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

    @patch("CLASSIC_Interface.QTimer")
    @patch("CLASSIC_Interface.GlobalRegistry")
    @patch("CLASSIC_Interface.classic_settings")
    @patch("CLASSIC_Interface.yaml_settings")
    @patch("CLASSIC_Interface.get_thread_manager")
    def test_controller_initialization(
        self,
        mock_get_thread_manager: Mock,
        mock_yaml_settings: Mock,
        mock_classic_settings: Mock,
        mock_global_registry: Mock,
        mock_qtimer: Mock,
    ) -> None:
        """Test that all controllers are properly initialized."""
        from CLASSIC_Interface import MainWindow

        # Arrange - QApplication is managed by qt_application fixture via setup
        mock_yaml_settings.return_value = "1.0.0"
        mock_classic_settings.return_value = False
        mock_global_registry.get_local_dir.return_value = Path()
        mock_thread_manager = MagicMock()
        mock_get_thread_manager.return_value = mock_thread_manager
        # Mock QTimer to prevent access violations on Windows offscreen platform
        mock_timer_instance = MagicMock()
        mock_qtimer.return_value = mock_timer_instance

        # Act - patch UISetupController to avoid complex UI initialization
        with patch("CLASSIC_Interface.UISetupController") as mock_ui_setup:
            mock_ui_setup_instance = MagicMock()
            mock_ui_setup.return_value = mock_ui_setup_instance
            window = MainWindow()

        # Assert - all controllers should be created
        assert hasattr(window, "scan_controller")
        assert hasattr(window, "update_manager")
        assert hasattr(window, "papyrus_manager")
        assert hasattr(window, "pastebin_controller")
        assert hasattr(window, "results_viewer")
        assert hasattr(window, "backup_manager")
        assert hasattr(window, "folder_manager")
        assert hasattr(window, "help_about")
        assert hasattr(window, "window_geometry")
        assert hasattr(window, "ui_setup")

        # Assert - context and signal_hub should be created
        assert hasattr(window, "context")
        assert hasattr(window, "signal_hub")
        assert hasattr(window, "thread_manager")
        assert window.thread_manager is mock_thread_manager
        mock_get_thread_manager.assert_called_once()

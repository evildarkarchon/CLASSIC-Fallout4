"""Tests for CLASSIC_TUI.py Terminal User Interface entry point.

This module tests the TUI application initialization, setup coordination,
and proper component configuration for the terminal interface.

NOTE: All tests mock the CLASSICTuiApp.run() method to prevent the interactive
interface from blocking test execution.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call
from typing import Any

# Mark all tests in this module
pytestmark = [pytest.mark.unit]


class TestClassicTUI:
    """Test suite for CLASSIC_TUI.py TUI entry point."""

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_main_function_initialization(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that the main() function initializes correctly."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance

        # Act
        from CLASSIC_TUI import main
        main()

        # Assert
        mock_setup_coordinator.assert_called_once()
        mock_coordinator_instance.initialize_application.assert_called_once_with(is_gui=False)
        mock_tui_app.assert_called_once()
        mock_app_instance.run.assert_called_once()

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_main_entry_point_execution(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that __main__ block executes correctly."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance

        # Act
        with patch("CLASSIC_TUI.__name__", "__main__"):
            import importlib
            import CLASSIC_TUI
            importlib.reload(CLASSIC_TUI)

        # Assert
        mock_setup_coordinator.assert_called_once()
        mock_coordinator_instance.initialize_application.assert_called_once_with(is_gui=False)
        mock_tui_app.assert_called_once()
        mock_app_instance.run.assert_called_once()

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_setup_coordinator_is_gui_false(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that SetupCoordinator is initialized with is_gui=False for TUI."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance

        # Act
        from CLASSIC_TUI import main
        main()

        # Assert - Specifically verify is_gui=False
        call_args = mock_coordinator_instance.initialize_application.call_args
        assert call_args[1]["is_gui"] is False

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_tui_app_run_called(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that CLASSICTuiApp.run() is called after initialization."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance

        # Track call order
        call_order = []
        mock_coordinator_instance.initialize_application.side_effect = lambda *args, **kwargs: call_order.append("setup")
        mock_app_instance.run.side_effect = lambda: call_order.append("run")

        # Act
        from CLASSIC_TUI import main
        main()

        # Assert - Verify order: setup first, then run
        assert call_order == ["setup", "run"]

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_exception_propagation_from_setup(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that exceptions from SetupCoordinator are properly propagated."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        test_exception = Exception("Setup failed")
        mock_coordinator_instance.initialize_application.side_effect = test_exception

        # Act & Assert
        from CLASSIC_TUI import main
        with pytest.raises(Exception) as exc_info:
            main()

        assert str(exc_info.value) == "Setup failed"
        # TUI app should not be created if setup fails
        mock_tui_app.assert_not_called()

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_exception_propagation_from_app_run(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that exceptions from CLASSICTuiApp.run() are properly propagated."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance
        test_exception = Exception("TUI run failed")
        mock_app_instance.run.side_effect = test_exception

        # Act & Assert
        from CLASSIC_TUI import main
        with pytest.raises(Exception) as exc_info:
            main()

        assert str(exc_info.value) == "TUI run failed"
        # Setup should complete before the exception
        mock_coordinator_instance.initialize_application.assert_called_once_with(is_gui=False)

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_sys_path_modification(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that sys.path is modified to include parent directory."""
        # The module modifies sys.path at import time
        import CLASSIC_TUI

        # Get the expected parent path
        tui_file_path = Path(CLASSIC_TUI.__file__)
        expected_parent = str(tui_file_path.parent)

        # Assert that the parent directory is in sys.path
        assert expected_parent in sys.path or any(
            Path(p).resolve() == Path(expected_parent).resolve()
            for p in sys.path
        )

    def test_module_imports(self) -> None:
        """Test that required modules can be imported."""
        # This tests that the imports at the top of CLASSIC_TUI work
        try:
            from ClassicLib.SetupCoordinator import SetupCoordinator
            from ClassicLib.TUI.app import CLASSICTuiApp
        except ImportError as e:
            pytest.fail(f"Failed to import required modules: {e}")

        # Verify the imported classes exist
        assert SetupCoordinator is not None
        assert CLASSICTuiApp is not None

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_keyboard_interrupt_handling(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test proper handling of keyboard interrupt during TUI execution."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance
        mock_app_instance.run.side_effect = KeyboardInterrupt()

        # Act
        from CLASSIC_TUI import main
        with pytest.raises(KeyboardInterrupt):
            main()

        # Assert - Setup should complete before interrupt
        mock_coordinator_instance.initialize_application.assert_called_once()

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_multiple_main_calls(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that main() can be called multiple times (for testing purposes)."""
        # Arrange
        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance

        # Act
        from CLASSIC_TUI import main
        main()
        main()
        main()

        # Assert - Each call should create new instances
        assert mock_setup_coordinator.call_count == 3
        assert mock_tui_app.call_count == 3
        assert mock_coordinator_instance.initialize_application.call_count == 3
        assert mock_app_instance.run.call_count == 3

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_setup_coordinator_singleton_behavior(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that SetupCoordinator is created fresh for each main() call."""
        # Arrange
        coordinator_instances = []

        def create_coordinator():
            instance = MagicMock()
            coordinator_instances.append(instance)
            return instance

        mock_setup_coordinator.side_effect = create_coordinator
        mock_tui_app.return_value = MagicMock()

        # Act
        from CLASSIC_TUI import main
        main()
        main()

        # Assert - Different coordinator instances
        assert len(coordinator_instances) == 2
        assert coordinator_instances[0] is not coordinator_instances[1]

    @patch("CLASSIC_TUI.CLASSICTuiApp")
    @patch("CLASSIC_TUI.SetupCoordinator")
    def test_tui_app_creation_timing(
        self,
        mock_setup_coordinator: Mock,
        mock_tui_app: Mock
    ) -> None:
        """Test that CLASSICTuiApp is created after SetupCoordinator initialization."""
        # Arrange
        creation_order = []

        mock_coordinator_instance = MagicMock()
        mock_setup_coordinator.return_value = mock_coordinator_instance
        mock_setup_coordinator.side_effect = lambda: creation_order.append("coordinator") or mock_coordinator_instance

        mock_app_instance = MagicMock()
        mock_tui_app.return_value = mock_app_instance
        mock_tui_app.side_effect = lambda: creation_order.append("app") or mock_app_instance

        mock_coordinator_instance.initialize_application.side_effect = lambda *args, **kwargs: creation_order.append("init")

        # Act
        from CLASSIC_TUI import main
        main()

        # Assert - Correct order
        assert creation_order == ["coordinator", "init", "app"]
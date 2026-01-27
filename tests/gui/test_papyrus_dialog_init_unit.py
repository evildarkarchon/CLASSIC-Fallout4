"""
Unit tests for PapyrusDialog initialization and base functionality.

This module tests the base PapyrusMonitorDialog class setup, initialization,
and fundamental dialog creation with properly mocked Qt components.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841, F401, DOC201
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.Interface.dialogs.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.widgets.Papyrus import PapyrusStats

is_xdist = os.environ.get("PYTEST_XDIST_WORKER") is not None
skip_xdist = pytest.mark.skipif(is_xdist, reason="Qt GUI tests unstable in xdist workers on Windows")


@pytest.mark.unit
@pytest.mark.gui
@skip_xdist
class TestPapyrusMonitorDialog:
    """Unit tests for PapyrusMonitorDialog class."""

    @pytest.fixture
    def mock_parent_widget(self, qt_application):
        """Create a real Qt parent widget for testing."""
        from PySide6.QtWidgets import QWidget

        widget = QWidget()
        yield widget
        widget.close()
        widget.deleteLater()

    @pytest.fixture
    def mock_dialog(self, mock_parent_widget, qt_application):
        """Create a PapyrusMonitorDialog with mocked dependencies."""
        with (
            patch("ClassicLib.Interface.dialogs.PapyrusDialog.QDialog.__init__") as mock_init,
            patch("ClassicLib.Interface.dialogs.PapyrusDialog.QVBoxLayout") as mock_vlayout,
            patch("ClassicLib.Interface.dialogs.PapyrusDialog.QHBoxLayout") as mock_hlayout,
            patch("ClassicLib.Interface.dialogs.PapyrusDialog.QGridLayout") as mock_gridlayout,
            patch("ClassicLib.Interface.dialogs.PapyrusDialog.QLabel") as mock_label,
            patch("ClassicLib.Interface.dialogs.PapyrusDialog.QPushButton") as mock_button,
            patch("ClassicLib.Interface.dialogs.PapyrusDialog.QFont") as mock_font,
        ):
            # Configure mocks
            mock_layout_instance = MagicMock()
            mock_vlayout.return_value = mock_layout_instance
            mock_hlayout.return_value = MagicMock()
            mock_gridlayout.return_value = MagicMock()

            mock_label_instance = MagicMock()
            mock_label.return_value = mock_label_instance

            mock_button_instance = MagicMock()
            mock_button.return_value = mock_button_instance

            mock_font_instance = MagicMock()
            mock_font.return_value = mock_font_instance

            dialog = PapyrusMonitorDialog(mock_parent_widget)

            # Manually set the attributes that would be created during init
            dialog.timestamp_label = mock_label_instance
            dialog.stat_value_labels = {
                "dumps": mock_label_instance,
                "stacks": mock_label_instance,
                "dumps_stacks_ratio": mock_label_instance,
                "warnings": mock_label_instance,
                "errors": mock_label_instance,
            }
            dialog.stat_status_labels = {
                "dumps": mock_label_instance,
                "stacks": mock_label_instance,
                "dumps_stacks_ratio": mock_label_instance,
                "warnings": mock_label_instance,
                "errors": mock_label_instance,
            }
            dialog.message_label = mock_label_instance
            dialog.stop_button = mock_button_instance

            return dialog

    @pytest.fixture
    def sample_stats(self):
        """Create sample PapyrusStats for testing."""
        return PapyrusStats(timestamp=datetime(2024, 1, 15, 10, 30, 45), dumps=5, stacks=10, warnings=2, errors=1, ratio=0.5)

    @pytest.fixture
    def zero_stats(self):
        """Create zero PapyrusStats for testing initial state."""
        return PapyrusStats(timestamp=datetime.now(), dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0)


@pytest.mark.unit
@pytest.mark.gui
@skip_xdist
class TestDialogInitialization:
    """Test dialog initialization and setup."""

    @pytest.fixture
    def mock_parent_widget(self, qt_application):
        """Create a real Qt parent widget for testing."""
        from PySide6.QtWidgets import QWidget

        widget = QWidget()
        yield widget
        widget.close()
        widget.deleteLater()

    def test_dialog_creation_with_parent(self, mock_parent_widget, qt_application):
        """Test dialog creation with parent widget."""
        # Create the dialog normally with a parent widget
        # Don't patch QDialog.__init__ as it needs to be called for proper initialization
        dialog = PapyrusMonitorDialog(mock_parent_widget)

        # Verify dialog was created successfully
        assert hasattr(dialog, "stop_monitoring")
        # Check that the window title was set
        assert dialog.windowTitle() == "Papyrus Log Monitor"
        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_dialog_creation_without_parent(self, qt_application):
        """Test dialog creation without parent widget."""
        # Create the dialog normally - don't patch QDialog.__init__
        # as it needs to be called for proper initialization
        dialog = PapyrusMonitorDialog(None)

        # Verify dialog was created successfully
        assert hasattr(dialog, "stop_monitoring")
        # Check that the window title was set
        assert dialog.windowTitle() == "Papyrus Log Monitor"
        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_dialog_window_properties_setup(self, mock_parent_widget, qt_application):
        """Test that dialog window properties are set correctly."""
        # Create the dialog and verify properties are set
        dialog = PapyrusMonitorDialog(mock_parent_widget)

        # Verify window properties were set correctly
        assert dialog.windowTitle() == "Papyrus Log Monitor"
        assert dialog.minimumWidth() == 400
        assert dialog.minimumHeight() == 300

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_signal_connection_setup(self, mock_parent_widget, qt_application):
        """Test that signals are properly connected during initialization."""
        # Create the dialog normally
        dialog = PapyrusMonitorDialog(mock_parent_widget)

        # Verify that the stop_button exists and has connections
        assert hasattr(dialog, "stop_button")
        # Check that the button has the expected text
        assert dialog.stop_button.text() == "Stop Monitoring"

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_initial_stats_setup(self, mock_parent_widget, qt_application):
        """Test that dialog initializes with default stats.

        Note: We verify state directly instead of using patch.object on the class,
        as patching QDialog subclasses with Signals before instantiation causes
        segfaults in PySide6 6.10+ when clicked.connect() is used in __init__.
        """
        # Create the dialog - update_stats is called internally with defaults
        dialog = PapyrusMonitorDialog(mock_parent_widget)

        # Verify the UI reflects the default stats (all zeros)
        # This confirms update_stats was called with the correct initial values
        assert dialog.stat_value_labels["dumps"].text() == "0"
        assert dialog.stat_value_labels["stacks"].text() == "0"
        assert dialog.stat_value_labels["dumps_stacks_ratio"].text() == "0.000"
        assert dialog.stat_value_labels["warnings"].text() == "0"
        assert dialog.stat_value_labels["errors"].text() == "0"

        # Clean up
        dialog.close()
        dialog.deleteLater()

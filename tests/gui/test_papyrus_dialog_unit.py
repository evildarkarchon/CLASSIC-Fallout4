"""
Unit tests for PapyrusDialog module.

This module tests the PapyrusMonitorDialog functionality with fully mocked Qt
components, including UI updates, statistics handling, and dialog operations.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from unittest.mock import create_autospec

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ClassicLib.Interface.Papyrus import PapyrusStats
from ClassicLib.Interface.PapyrusDialog import PapyrusMonitorDialog


@pytest.mark.unit
@pytest.mark.gui
class TestPapyrusMonitorDialog:
    """Unit tests for PapyrusMonitorDialog class."""

    @pytest.fixture
    def dialog(self, qt_application):
        """Create a PapyrusMonitorDialog instance for testing."""
        return PapyrusMonitorDialog()

    @pytest.fixture
    def mock_stats(self):
        """Create mock PapyrusStats for testing."""
        return PapyrusStats(
            timestamp=datetime(2024, 1, 15, 14, 30, 45),
            dumps=10,
            stacks=20,
            warnings=2,
            errors=1,
            ratio=0.5
        )

    def test_dialog_initialization(self, dialog):
        """Test proper initialization of the dialog."""
        # Verify dialog properties
        assert dialog.windowTitle() == "Papyrus Log Monitor"
        assert dialog.minimumWidth() == 400
        assert dialog.minimumHeight() == 300
        assert dialog.windowFlags() & Qt.WindowType.Dialog

        # Verify stop_monitoring signal exists
        assert hasattr(dialog, 'stop_monitoring')
        assert dialog.stop_monitoring is not None

    def test_dialog_layout_structure(self, dialog):
        """Test that the dialog has proper layout structure."""
        # Verify main layout is VBoxLayout
        main_layout = dialog.layout()
        assert isinstance(main_layout, QVBoxLayout)

        # Verify essential components exist
        assert hasattr(dialog, 'timestamp_label')
        assert isinstance(dialog.timestamp_label, QLabel)

        assert hasattr(dialog, 'stat_value_labels')
        assert isinstance(dialog.stat_value_labels, dict)

        assert hasattr(dialog, 'stat_status_labels')
        assert isinstance(dialog.stat_status_labels, dict)

        assert hasattr(dialog, 'message_label')
        assert isinstance(dialog.message_label, QLabel)

        assert hasattr(dialog, 'stop_button')
        assert isinstance(dialog.stop_button, QPushButton)

    def test_stat_labels_initialization(self, dialog):
        """Test that statistics labels are properly initialized."""
        # Verify expected stat label keys exist
        expected_keys = ["dumps", "stacks", "dumps_stacks_ratio", "warnings", "errors"]

        for key in expected_keys:
            assert key in dialog.stat_value_labels
            assert isinstance(dialog.stat_value_labels[key], QLabel)

            assert key in dialog.stat_status_labels
            assert isinstance(dialog.stat_status_labels[key], QLabel)

        # Verify initial values are set to "0" or default
        for key in expected_keys:
            value_label = dialog.stat_value_labels[key]
            if key == "dumps_stacks_ratio":
                assert "0.000" in value_label.text()
            else:
                assert value_label.text() == "0"

    def test_stop_button_connection(self, dialog):
        """Test that stop button is properly connected."""
        # Stop button should exist and have text
        assert dialog.stop_button.text() == "Stop Monitoring"

        # Test button click connection
        with patch.object(dialog, 'on_stop_clicked') as mock_stop:
            dialog.stop_button.click()
            mock_stop.assert_called_once()

    def test_update_stats_basic(self, dialog, mock_stats):
        """Test basic statistics update functionality."""
        dialog.update_stats(mock_stats)

        # Verify timestamp update
        expected_time = "14:30:45"
        assert expected_time in dialog.timestamp_label.text()

        # Verify stat values are updated
        assert dialog.stat_value_labels["dumps"].text() == "10"
        assert dialog.stat_value_labels["stacks"].text() == "20"
        assert dialog.stat_value_labels["dumps_stacks_ratio"].text() == "0.500"
        assert dialog.stat_value_labels["warnings"].text() == "2"
        assert dialog.stat_value_labels["errors"].text() == "1"

    def test_update_stats_calls_helper_methods(self, dialog, mock_stats):
        """Test that update_stats calls appropriate helper methods."""
        with patch.object(dialog, '_update_status_indicators') as mock_status, \
             patch.object(dialog, '_update_message') as mock_message:

            dialog.update_stats(mock_stats)

            mock_status.assert_called_once_with(mock_stats)
            mock_message.assert_called_once_with(mock_stats)

    def test_update_status_indicators_ratio_high(self, dialog):
        """Test status indicators with high ratio (> 0.8)."""
        high_ratio_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=90, stacks=100, warnings=0, errors=0, ratio=0.9
        )

        dialog._update_status_indicators(high_ratio_stats)

        # High ratio should show red X
        ratio_label = dialog.stat_status_labels["dumps_stacks_ratio"]
        assert ratio_label.text() == "❌"
        assert "red" in ratio_label.styleSheet()

    def test_update_status_indicators_ratio_medium(self, dialog):
        """Test status indicators with medium ratio (0.5 < ratio <= 0.8)."""
        medium_ratio_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=60, stacks=100, warnings=0, errors=0, ratio=0.6
        )

        dialog._update_status_indicators(medium_ratio_stats)

        # Medium ratio should show warning
        ratio_label = dialog.stat_status_labels["dumps_stacks_ratio"]
        assert ratio_label.text() == "⚠️"
        assert "orange" in ratio_label.styleSheet()

    def test_update_status_indicators_ratio_low(self, dialog):
        """Test status indicators with low ratio (<= 0.5)."""
        low_ratio_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=30, stacks=100, warnings=0, errors=0, ratio=0.3
        )

        dialog._update_status_indicators(low_ratio_stats)

        # Low ratio should show green checkmark
        ratio_label = dialog.stat_status_labels["dumps_stacks_ratio"]
        assert ratio_label.text() == "✓"
        assert "green" in ratio_label.styleSheet()

    def test_update_status_indicators_warnings_present(self, dialog):
        """Test status indicators when warnings are present."""
        warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=10, stacks=20, warnings=5, errors=0, ratio=0.5
        )

        dialog._update_status_indicators(warning_stats)

        # Warnings present should show warning icon
        warning_label = dialog.stat_status_labels["warnings"]
        assert warning_label.text() == "⚠️"
        assert "orange" in warning_label.styleSheet()

    def test_update_status_indicators_no_warnings(self, dialog):
        """Test status indicators when no warnings are present."""
        no_warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=10, stacks=20, warnings=0, errors=0, ratio=0.5
        )

        dialog._update_status_indicators(no_warning_stats)

        # No warnings should show green checkmark
        warning_label = dialog.stat_status_labels["warnings"]
        assert warning_label.text() == "✓"
        assert "green" in warning_label.styleSheet()

    def test_update_status_indicators_errors_present(self, dialog):
        """Test status indicators when errors are present."""
        error_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=10, stacks=20, warnings=0, errors=3, ratio=0.5
        )

        dialog._update_status_indicators(error_stats)

        # Errors present should show red X
        error_label = dialog.stat_status_labels["errors"]
        assert error_label.text() == "❌"
        assert "red" in error_label.styleSheet()

    def test_update_status_indicators_no_errors(self, dialog):
        """Test status indicators when no errors are present."""
        no_error_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=10, stacks=20, warnings=0, errors=0, ratio=0.5
        )

        dialog._update_status_indicators(no_error_stats)

        # No errors should show green checkmark
        error_label = dialog.stat_status_labels["errors"]
        assert error_label.text() == "✓"
        assert "green" in error_label.styleSheet()

    def test_update_message_errors_priority(self, dialog):
        """Test message update when errors are present (highest priority)."""
        error_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=10, stacks=20, warnings=5, errors=2, ratio=0.9
        )

        dialog._update_message(error_stats)

        # Errors should take priority over warnings and high ratio
        assert "2 errors detected" in dialog.message_label.text()
        assert "red" in dialog.message_label.styleSheet()
        assert "bold" in dialog.message_label.styleSheet()

    def test_update_message_warnings_priority(self, dialog):
        """Test message update when warnings are present (no errors)."""
        warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=10, stacks=20, warnings=3, errors=0, ratio=0.9
        )

        dialog._update_message(warning_stats)

        # Warnings should take priority over high ratio when no errors
        assert "3 warnings detected" in dialog.message_label.text()
        assert "orange" in dialog.message_label.styleSheet()
        assert "bold" in dialog.message_label.styleSheet()

    def test_update_message_high_ratio_warning(self, dialog):
        """Test message update for high ratio warning (no errors/warnings)."""
        high_ratio_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=90, stacks=100, warnings=0, errors=0, ratio=0.9
        )

        dialog._update_message(high_ratio_stats)

        # High ratio should show warning when no errors/warnings
        assert "High dumps-to-stacks ratio detected" in dialog.message_label.text()
        assert "red" in dialog.message_label.styleSheet()
        assert "bold" in dialog.message_label.styleSheet()

    def test_update_message_medium_ratio_caution(self, dialog):
        """Test message update for medium ratio caution."""
        medium_ratio_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=60, stacks=100, warnings=0, errors=0, ratio=0.6
        )

        dialog._update_message(medium_ratio_stats)

        # Medium ratio should show caution message
        assert "Elevated dumps-to-stacks ratio" in dialog.message_label.text()
        assert "orange" in dialog.message_label.styleSheet()

    def test_update_message_normal_status(self, dialog):
        """Test message update for normal status."""
        normal_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=30, stacks=100, warnings=0, errors=0, ratio=0.3
        )

        dialog._update_message(normal_stats)

        # Normal status should show positive message
        assert "appears normal" in dialog.message_label.text()
        assert "green" in dialog.message_label.styleSheet()

    def test_on_stop_clicked(self, dialog):
        """Test on_stop_clicked method behavior."""
        with patch.object(dialog, 'accept') as mock_accept:
            # Mock the signal emit
            dialog.stop_monitoring = Mock()

            dialog.on_stop_clicked()

            # Should emit stop signal and close dialog
            dialog.stop_monitoring.emit.assert_called_once()
            mock_accept.assert_called_once()

    def test_handle_error(self, dialog):
        """Test error handling method."""
        error_message = "Test error occurred"

        dialog.handle_error(error_message)

        # Verify error message is displayed correctly
        assert f"Error: {error_message}" in dialog.message_label.text()
        assert "red" in dialog.message_label.styleSheet()
        assert "bold" in dialog.message_label.styleSheet()

    def test_close_event(self, dialog):
        """Test close event handling."""
        # Create a mock close event
        mock_event = Mock(spec=QCloseEvent)
        dialog.stop_monitoring = Mock()

        dialog.closeEvent(mock_event)

        # Should emit stop signal and accept the event
        dialog.stop_monitoring.emit.assert_called_once()
        mock_event.accept.assert_called_once()

    def test_initial_stats_are_set(self, dialog):
        """Test that initial stats are properly set during initialization."""
        # The dialog should initialize with default stats
        # Check that labels have been initialized
        assert dialog.timestamp_label.text()  # Should have some timestamp text

        # Initial stat values should be 0
        assert dialog.stat_value_labels["dumps"].text() == "0"
        assert dialog.stat_value_labels["stacks"].text() == "0"
        assert dialog.stat_value_labels["warnings"].text() == "0"
        assert dialog.stat_value_labels["errors"].text() == "0"
        assert "0.000" in dialog.stat_value_labels["dumps_stacks_ratio"].text()

    def test_font_configuration(self, dialog):
        """Test that fonts are configured correctly."""
        # Find the title label (should be the first QLabel added to main layout)
        main_layout = dialog.layout()

        # Look for title label in the layout
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QLabel) and "Papyrus Log Monitoring" in widget.text():
                    # Verify font properties
                    font = widget.font()
                    assert font.bold()
                    assert font.pointSize() == 14
                    break
        else:
            pytest.fail("Title label not found")

    def test_label_alignments(self, dialog):
        """Test that labels have proper alignments."""
        # Timestamp label should be center-aligned
        assert dialog.timestamp_label.alignment() & Qt.AlignmentFlag.AlignCenter

        # Message label should be center-aligned and word-wrapped
        assert dialog.message_label.alignment() & Qt.AlignmentFlag.AlignCenter
        assert dialog.message_label.wordWrap()

        # Value labels should be center-aligned
        for value_label in dialog.stat_value_labels.values():
            assert value_label.alignment() & Qt.AlignmentFlag.AlignCenter

        # Status labels should be center-aligned
        for status_label in dialog.stat_status_labels.values():
            assert status_label.alignment() & Qt.AlignmentFlag.AlignCenter

    def test_comprehensive_stats_update_workflow(self, dialog):
        """Test complete statistics update workflow."""
        # Create stats with various conditions
        complex_stats = PapyrusStats(
            timestamp=datetime(2024, 3, 15, 16, 45, 30),
            dumps=75,
            stacks=100,
            warnings=3,
            errors=1,
            ratio=0.75
        )

        dialog.update_stats(complex_stats)

        # Verify all components are updated
        assert "16:45:30" in dialog.timestamp_label.text()
        assert dialog.stat_value_labels["dumps"].text() == "75"
        assert dialog.stat_value_labels["stacks"].text() == "100"
        assert dialog.stat_value_labels["dumps_stacks_ratio"].text() == "0.750"
        assert dialog.stat_value_labels["warnings"].text() == "3"
        assert dialog.stat_value_labels["errors"].text() == "1"

        # With errors present, error message should be displayed
        assert "1 errors detected" in dialog.message_label.text()
        assert "red" in dialog.message_label.styleSheet()

        # Status indicators should reflect the stats
        assert dialog.stat_status_labels["errors"].text() == "❌"
        assert dialog.stat_status_labels["warnings"].text() == "⚠️"
        # Ratio 0.75 is medium (0.5 < 0.75 <= 0.8)
        assert dialog.stat_status_labels["dumps_stacks_ratio"].text() == "⚠️"

    def test_edge_case_zero_stats(self, dialog):
        """Test handling of all-zero statistics."""
        zero_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0
        )

        dialog.update_stats(zero_stats)

        # All values should be zero
        assert dialog.stat_value_labels["dumps"].text() == "0"
        assert dialog.stat_value_labels["stacks"].text() == "0"
        assert dialog.stat_value_labels["warnings"].text() == "0"
        assert dialog.stat_value_labels["errors"].text() == "0"
        assert "0.000" in dialog.stat_value_labels["dumps_stacks_ratio"].text()

        # All status indicators should be green
        assert dialog.stat_status_labels["dumps_stacks_ratio"].text() == "✓"
        assert dialog.stat_status_labels["warnings"].text() == "✓"
        assert dialog.stat_status_labels["errors"].text() == "✓"

        # Message should indicate normal status
        assert "appears normal" in dialog.message_label.text()

    def test_signal_emission_on_destruction(self, qt_application):
        """Test that signals are properly handled during dialog destruction."""
        dialog = PapyrusMonitorDialog()

        # Mock the signal to track emissions
        signal_emitted = False
        def signal_handler():
            nonlocal signal_emitted
            signal_emitted = True

        dialog.stop_monitoring.connect(signal_handler)

        # Close the dialog
        dialog.close()

        # Signal should have been emitted
        assert signal_emitted

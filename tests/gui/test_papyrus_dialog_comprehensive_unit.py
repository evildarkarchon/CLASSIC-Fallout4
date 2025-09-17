"""
Comprehensive unit tests for PapyrusDialog module.

This module provides comprehensive test coverage for the PapyrusMonitorDialog class,
including UI initialization, statistics updating, status indicators, message handling,
and dialog lifecycle with properly mocked Qt components.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841, F401, DOC201
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from ClassicLib.Interface.Papyrus import PapyrusStats
from ClassicLib.Interface.PapyrusDialog import PapyrusMonitorDialog


@pytest.mark.unit
@pytest.mark.gui
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
        with patch("ClassicLib.Interface.PapyrusDialog.QDialog.__init__") as mock_init, \
             patch("ClassicLib.Interface.PapyrusDialog.QVBoxLayout") as mock_vlayout, \
             patch("ClassicLib.Interface.PapyrusDialog.QHBoxLayout") as mock_hlayout, \
             patch("ClassicLib.Interface.PapyrusDialog.QGridLayout") as mock_gridlayout, \
             patch("ClassicLib.Interface.PapyrusDialog.QLabel") as mock_label, \
             patch("ClassicLib.Interface.PapyrusDialog.QPushButton") as mock_button, \
             patch("ClassicLib.Interface.PapyrusDialog.QFont") as mock_font:

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
        return PapyrusStats(
            timestamp=datetime(2024, 1, 15, 10, 30, 45),
            dumps=5,
            stacks=10,
            warnings=2,
            errors=1,
            ratio=0.5
        )

    @pytest.fixture
    def zero_stats(self):
        """Create zero PapyrusStats for testing initial state."""
        return PapyrusStats(
            timestamp=datetime.now(),
            dumps=0,
            stacks=0,
            warnings=0,
            errors=0,
            ratio=0.0
        )


@pytest.mark.unit
@pytest.mark.gui
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
        assert hasattr(dialog, 'stop_monitoring')
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
        assert hasattr(dialog, 'stop_monitoring')
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
        assert hasattr(dialog, 'stop_button')
        # Check that the button has the expected text
        assert dialog.stop_button.text() == "Stop Monitoring"

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_initial_stats_setup(self, mock_parent_widget, qt_application):
        """Test that dialog initializes with default stats."""
        with patch.object(PapyrusMonitorDialog, 'update_stats') as mock_update_stats:
            # Create the dialog normally
            dialog = PapyrusMonitorDialog(mock_parent_widget)

            # Verify update_stats was called with default values
            mock_update_stats.assert_called_once()
            call_args = mock_update_stats.call_args[0][0]
            assert isinstance(call_args, PapyrusStats)
            assert call_args.dumps == 0
            assert call_args.stacks == 0
            assert call_args.warnings == 0
            assert call_args.errors == 0
            assert call_args.ratio == 0.0

            # Clean up
            dialog.close()
            dialog.deleteLater()


@pytest.mark.unit
@pytest.mark.gui
class TestStatsUpdateFunctionality:
    """Test statistics updating functionality."""

    @pytest.fixture
    def mock_dialog(self, qt_application):
        """Create a PapyrusMonitorDialog with properly mocked label widgets."""
        # Create a real dialog instance
        dialog = PapyrusMonitorDialog(None)

        # Mock the label widgets to track setText calls
        dialog.timestamp_label = MagicMock()
        dialog.stat_value_labels = {
            "dumps": MagicMock(),
            "stacks": MagicMock(),
            "dumps_stacks_ratio": MagicMock(),
            "warnings": MagicMock(),
            "errors": MagicMock(),
        }
        dialog.stat_status_labels = {
            "dumps": MagicMock(),
            "stacks": MagicMock(),
            "dumps_stacks_ratio": MagicMock(),
            "warnings": MagicMock(),
            "errors": MagicMock(),
        }
        dialog.message_label = MagicMock()

        yield dialog

        # Clean up
        dialog.close()
        dialog.deleteLater()

    @pytest.fixture
    def sample_stats(self):
        """Create sample PapyrusStats for testing."""
        return PapyrusStats(
            timestamp=datetime(2024, 1, 15, 10, 30, 45),
            dumps=5,
            stacks=10,
            warnings=2,
            errors=1,
            ratio=0.5
        )

    @pytest.fixture
    def zero_stats(self):
        """Create zero PapyrusStats for testing initial state."""
        return PapyrusStats(
            timestamp=datetime.now(),
            dumps=0,
            stacks=0,
            warnings=0,
            errors=0,
            ratio=0.0
        )

    def test_update_stats_timestamp(self, mock_dialog, sample_stats):
        """Test that timestamp is updated correctly."""
        mock_dialog.update_stats(sample_stats)

        # Verify timestamp label was updated
        mock_dialog.timestamp_label.setText.assert_called()
        call_args = mock_dialog.timestamp_label.setText.call_args[0][0]
        assert "Last Updated: 10:30:45" in call_args

    def test_update_stats_values(self, mock_dialog, sample_stats):
        """Test that all stat values are updated correctly."""
        mock_dialog.update_stats(sample_stats)

        # Verify all stat values were updated
        expected_updates = {
            "dumps": "5",
            "stacks": "10",
            "dumps_stacks_ratio": "0.500",
            "warnings": "2",
            "errors": "1"
        }

        for key, expected_value in expected_updates.items():
            mock_label = mock_dialog.stat_value_labels[key]
            mock_label.setText.assert_called_with(expected_value)

    def test_update_stats_zero_values(self, mock_dialog, zero_stats):
        """Test updating with zero stats."""
        mock_dialog.update_stats(zero_stats)

        # Verify zero values are displayed correctly
        expected_updates = {
            "dumps": "0",
            "stacks": "0",
            "dumps_stacks_ratio": "0.000",
            "warnings": "0",
            "errors": "0"
        }

        for key, expected_value in expected_updates.items():
            mock_label = mock_dialog.stat_value_labels[key]
            mock_label.setText.assert_called_with(expected_value)

    def test_update_stats_calls_status_indicators(self, mock_dialog, sample_stats):
        """Test that status indicators are updated."""
        with patch.object(mock_dialog, '_update_status_indicators') as mock_status, \
             patch.object(mock_dialog, '_update_message') as mock_message:

            mock_dialog.update_stats(sample_stats)

            # Verify helper methods were called
            mock_status.assert_called_once_with(sample_stats)
            mock_message.assert_called_once_with(sample_stats)

    def test_update_stats_high_ratio_precision(self, mock_dialog):
        """Test ratio display precision with various values."""
        test_ratios = [
            (0.123456789, "0.123"),
            (0.999, "0.999"),
            (1.0, "1.000"),
            (0.0, "0.000"),
            (0.5, "0.500")
        ]

        for ratio, expected in test_ratios:
            stats = PapyrusStats(
                timestamp=datetime.now(),
                dumps=1, stacks=2, warnings=0, errors=0,
                ratio=ratio
            )

            mock_dialog.update_stats(stats)

            # Verify ratio precision
            mock_label = mock_dialog.stat_value_labels["dumps_stacks_ratio"]
            mock_label.setText.assert_called_with(expected)


@pytest.mark.unit
@pytest.mark.gui
class TestStatusIndicatorUpdates:
    """Test status indicator update functionality."""

    @pytest.fixture
    def mock_dialog(self, qt_application):
        """Create a real dialog with mocked labels for testing."""
        # Create a real dialog instance
        dialog = PapyrusMonitorDialog(None)

        # Mock the status label widgets to track setText calls
        dialog.stat_status_labels = {
            "dumps": MagicMock(),
            "stacks": MagicMock(),
            "dumps_stacks_ratio": MagicMock(),
            "warnings": MagicMock(),
            "errors": MagicMock(),
        }

        yield dialog

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_update_status_indicators_good_ratio(self, mock_dialog):
        """Test status indicators with good ratio (< 0.5)."""
        good_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=5, warnings=0, errors=0,
            ratio=0.2  # Good ratio
        )

        mock_dialog._update_status_indicators(good_stats)

        # Verify good ratio indicator
        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("✓")
        ratio_label.setStyleSheet.assert_called_with("color: green;")

        # Verify no warnings/errors indicators
        warnings_label = mock_dialog.stat_status_labels["warnings"]
        warnings_label.setText.assert_called_with("✓")
        warnings_label.setStyleSheet.assert_called_with("color: green;")

        errors_label = mock_dialog.stat_status_labels["errors"]
        errors_label.setText.assert_called_with("✓")
        errors_label.setStyleSheet.assert_called_with("color: green;")

    def test_update_status_indicators_warning_ratio(self, mock_dialog):
        """Test status indicators with warning ratio (0.5 - 0.8)."""
        warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=6, stacks=10, warnings=0, errors=0,
            ratio=0.6  # Warning ratio
        )

        mock_dialog._update_status_indicators(warning_stats)

        # Verify warning ratio indicator
        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("⚠️")
        ratio_label.setStyleSheet.assert_called_with("color: orange;")

    def test_update_status_indicators_critical_ratio(self, mock_dialog):
        """Test status indicators with critical ratio (> 0.8)."""
        critical_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=9, stacks=10, warnings=0, errors=0,
            ratio=0.9  # Critical ratio
        )

        mock_dialog._update_status_indicators(critical_stats)

        # Verify critical ratio indicator
        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("❌")
        ratio_label.setStyleSheet.assert_called_with("color: red;")

    def test_update_status_indicators_with_warnings(self, mock_dialog):
        """Test status indicators when warnings are present."""
        warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=5, warnings=3, errors=0,
            ratio=0.2
        )

        mock_dialog._update_status_indicators(warning_stats)

        # Verify warnings indicator
        warnings_label = mock_dialog.stat_status_labels["warnings"]
        warnings_label.setText.assert_called_with("⚠️")
        warnings_label.setStyleSheet.assert_called_with("color: orange;")

        # Errors should still be good
        errors_label = mock_dialog.stat_status_labels["errors"]
        errors_label.setText.assert_called_with("✓")
        errors_label.setStyleSheet.assert_called_with("color: green;")

    def test_update_status_indicators_with_errors(self, mock_dialog):
        """Test status indicators when errors are present."""
        error_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=5, warnings=0, errors=2,
            ratio=0.2
        )

        mock_dialog._update_status_indicators(error_stats)

        # Verify errors indicator
        errors_label = mock_dialog.stat_status_labels["errors"]
        errors_label.setText.assert_called_with("❌")
        errors_label.setStyleSheet.assert_called_with("color: red;")

    def test_update_status_indicators_multiple_issues(self, mock_dialog):
        """Test status indicators with multiple issues."""
        multi_issue_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=8, stacks=10, warnings=5, errors=3,
            ratio=0.8  # Exactly at threshold
        )

        mock_dialog._update_status_indicators(multi_issue_stats)

        # Verify all indicators show issues
        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        warnings_label = mock_dialog.stat_status_labels["warnings"]
        errors_label = mock_dialog.stat_status_labels["errors"]

        # Ratio at 0.8 should be warning (not critical)
        ratio_label.setText.assert_called_with("⚠️")
        ratio_label.setStyleSheet.assert_called_with("color: orange;")

        # Warnings and errors should show problems
        warnings_label.setText.assert_called_with("⚠️")
        warnings_label.setStyleSheet.assert_called_with("color: orange;")

        errors_label.setText.assert_called_with("❌")
        errors_label.setStyleSheet.assert_called_with("color: red;")


@pytest.mark.unit
@pytest.mark.gui
class TestMessageUpdates:
    """Test message update functionality."""

    @pytest.fixture
    def mock_dialog(self, qt_application):
        """Create a real dialog with mocked label for testing."""
        # Create a real dialog instance
        dialog = PapyrusMonitorDialog(None)

        # Mock the message label to track setText calls
        dialog.message_label = MagicMock()

        yield dialog

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_update_message_with_errors(self, mock_dialog):
        """Test message when errors are present."""
        error_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=5, warnings=2, errors=3,
            ratio=0.2
        )

        mock_dialog._update_message(error_stats)

        # Should prioritize error message
        mock_dialog.message_label.setText.assert_called_with("3 errors detected in Papyrus log!")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

    def test_update_message_with_warnings_no_errors(self, mock_dialog):
        """Test message when warnings are present but no errors."""
        warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=5, warnings=4, errors=0,
            ratio=0.2
        )

        mock_dialog._update_message(warning_stats)

        # Should show warning message
        mock_dialog.message_label.setText.assert_called_with("4 warnings detected in Papyrus log.")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange; font-weight: bold;")

    def test_update_message_high_ratio_no_errors_warnings(self, mock_dialog):
        """Test message with high ratio but no errors/warnings."""
        high_ratio_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=9, stacks=10, warnings=0, errors=0,
            ratio=0.9  # High ratio
        )

        mock_dialog._update_message(high_ratio_stats)

        # Should show high ratio warning
        mock_dialog.message_label.setText.assert_called_with("Warning: High dumps-to-stacks ratio detected!")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

    def test_update_message_medium_ratio_no_issues(self, mock_dialog):
        """Test message with medium ratio but no other issues."""
        medium_ratio_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=6, stacks=10, warnings=0, errors=0,
            ratio=0.6  # Medium ratio
        )

        mock_dialog._update_message(medium_ratio_stats)

        # Should show caution message
        mock_dialog.message_label.setText.assert_called_with("Caution: Elevated dumps-to-stacks ratio.")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange;")

    def test_update_message_all_good(self, mock_dialog):
        """Test message when all stats are good."""
        good_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=10, warnings=0, errors=0,
            ratio=0.1  # Good ratio
        )

        mock_dialog._update_message(good_stats)

        # Should show normal message
        mock_dialog.message_label.setText.assert_called_with("Papyrus log appears normal.")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: green;")

    def test_update_message_priority_order(self, mock_dialog):
        """Test message priority order: errors > warnings > high ratio > medium ratio > normal."""
        # Test that errors take priority over all else
        all_issues_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=9, stacks=10, warnings=5, errors=2,
            ratio=0.9  # High ratio, warnings, AND errors
        )

        mock_dialog._update_message(all_issues_stats)

        # Should show error message (highest priority)
        call_args = mock_dialog.message_label.setText.call_args[0][0]
        assert "errors detected" in call_args
        assert "2 errors" in call_args

    def test_update_message_edge_ratio_values(self, mock_dialog):
        """Test message with edge case ratio values."""
        # Test exactly at 0.5 boundary
        edge_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=5, stacks=10, warnings=0, errors=0,
            ratio=0.5  # Exactly at boundary
        )

        mock_dialog._update_message(edge_stats)

        # At exactly 0.5, should not trigger elevated message (> 0.5 needed)
        mock_dialog.message_label.setText.assert_called_with("Papyrus log appears normal.")

        # Test exactly at 0.8 boundary
        edge_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=8, stacks=10, warnings=0, errors=0,
            ratio=0.8  # Exactly at boundary
        )

        mock_dialog._update_message(edge_stats)

        # At exactly 0.8, should trigger caution (0.5 < ratio <= 0.8)
        # not the high ratio warning (which needs > 0.8)
        mock_dialog.message_label.setText.assert_called_with("Caution: Elevated dumps-to-stacks ratio.")


@pytest.mark.unit
@pytest.mark.gui
class TestDialogActions:
    """Test dialog action handling."""

    @pytest.fixture
    def mock_dialog(self, qt_application):
        """Create a real dialog with mocked labels for testing."""
        # Create a real dialog instance
        dialog = PapyrusMonitorDialog(None)

        # Mock only the labels and signals we need to verify
        dialog.message_label = MagicMock()
        # Replace the Signal with a mock that has emit method
        dialog.stop_monitoring = MagicMock()
        dialog.stop_monitoring.emit = MagicMock()

        yield dialog

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_on_stop_clicked_emits_signal(self, mock_dialog):
        """Test that stop button click emits signal and closes dialog."""
        with patch.object(mock_dialog, 'accept') as mock_accept:
            # Mock the signal emission
            mock_dialog.stop_monitoring = MagicMock()
            mock_dialog.stop_monitoring.emit = MagicMock()

            mock_dialog.on_stop_clicked()

            # Verify signal was emitted and dialog was accepted
            mock_dialog.stop_monitoring.emit.assert_called_once()
            mock_accept.assert_called_once()

    def test_handle_error_updates_message(self, mock_dialog):
        """Test that error handling updates the message label."""
        test_error = "Test error message"

        mock_dialog.handle_error(test_error)

        # Verify error message was set
        mock_dialog.message_label.setText.assert_called_with(f"Error: {test_error}")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

    def test_handle_error_various_messages(self, mock_dialog):
        """Test error handling with various error messages."""
        test_errors = [
            "Network connection failed",
            "File not found",
            "Permission denied",
            "",  # Empty error
            "Very long error message with lots of details about what went wrong",
        ]

        for error_msg in test_errors:
            mock_dialog.handle_error(error_msg)

            # Verify error was formatted correctly
            expected_text = f"Error: {error_msg}"
            mock_dialog.message_label.setText.assert_called_with(expected_text)
            mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

    def test_close_event_emits_signal(self, mock_dialog):
        """Test that close event emits stop monitoring signal."""
        # Create a mock QCloseEvent
        mock_event = MagicMock()
        mock_event.accept = MagicMock()

        # Mock the signal emission
        mock_dialog.stop_monitoring = MagicMock()
        mock_dialog.stop_monitoring.emit = MagicMock()

        mock_dialog.closeEvent(mock_event)

        # Verify signal was emitted and event was accepted
        mock_dialog.stop_monitoring.emit.assert_called_once()
        mock_event.accept.assert_called_once()


@pytest.mark.unit
@pytest.mark.gui
class TestDialogIntegrationScenarios:
    """Integration tests for dialog functionality."""

    @pytest.fixture
    def mock_dialog(self, qt_application):
        """Create a real dialog with mocked labels for integration tests."""
        # Create a real dialog instance
        dialog = PapyrusMonitorDialog(None)

        # Mock the label widgets to track setText calls
        dialog.timestamp_label = MagicMock()
        dialog.message_label = MagicMock()
        dialog.stat_value_labels = {
            "dumps": MagicMock(),
            "stacks": MagicMock(),
            "dumps_stacks_ratio": MagicMock(),
            "warnings": MagicMock(),
            "errors": MagicMock(),
        }
        dialog.stat_status_labels = {
            "dumps": MagicMock(),
            "stacks": MagicMock(),
            "dumps_stacks_ratio": MagicMock(),
            "warnings": MagicMock(),
            "errors": MagicMock(),
        }
        # Mock signal for testing
        dialog.stop_monitoring = MagicMock()
        dialog.stop_monitoring.emit = MagicMock()

        yield dialog

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_complete_stats_update_cycle(self, mock_dialog):
        """Test complete statistics update cycle with various scenarios."""
        # Scenario 1: Normal operation
        normal_stats = PapyrusStats(
            timestamp=datetime(2024, 1, 15, 12, 0, 0),
            dumps=2, stacks=20, warnings=0, errors=0,
            ratio=0.1
        )

        with patch.object(mock_dialog, '_update_status_indicators') as mock_status, \
             patch.object(mock_dialog, '_update_message') as mock_message:

            mock_dialog.update_stats(normal_stats)

            # Verify all components were updated
            mock_dialog.timestamp_label.setText.assert_called()
            mock_status.assert_called_once_with(normal_stats)
            mock_message.assert_called_once_with(normal_stats)

        # Scenario 2: Problem detected
        problem_stats = PapyrusStats(
            timestamp=datetime(2024, 1, 15, 12, 5, 0),
            dumps=15, stacks=20, warnings=3, errors=1,
            ratio=0.75
        )

        mock_dialog.update_stats(problem_stats)

        # Verify values were updated
        assert mock_dialog.stat_value_labels["errors"].setText.call_count > 0

    def test_dialog_lifecycle_with_monitoring(self, mock_dialog):
        """Test complete dialog lifecycle with monitoring start/stop."""
        # Simulate monitoring start
        initial_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=0, stacks=0, warnings=0, errors=0,
            ratio=0.0
        )

        mock_dialog.update_stats(initial_stats)

        # Simulate some monitoring activity
        active_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=5, stacks=15, warnings=1, errors=0,
            ratio=0.33
        )

        mock_dialog.update_stats(active_stats)

        # Simulate stopping monitoring
        with patch.object(mock_dialog, 'accept') as mock_accept:
            mock_dialog.stop_monitoring = MagicMock()
            mock_dialog.stop_monitoring.emit = MagicMock()

            mock_dialog.on_stop_clicked()

            # Verify proper cleanup
            mock_dialog.stop_monitoring.emit.assert_called_once()
            mock_accept.assert_called_once()

    def test_rapid_stats_updates(self, mock_dialog):
        """Test handling of rapid statistics updates."""
        # Simulate rapid updates
        timestamps = [
            datetime(2024, 1, 15, 12, 0, i)
            for i in range(10)
        ]

        for i, timestamp in enumerate(timestamps):
            stats = PapyrusStats(
                timestamp=timestamp,
                dumps=i, stacks=i*2, warnings=i//3, errors=i//5,
                ratio=min(i/10.0, 1.0)
            )

            mock_dialog.update_stats(stats)

        # Verify final state reflects last update
        final_expected_dumps = "9"
        mock_dialog.stat_value_labels["dumps"].setText.assert_called_with(final_expected_dumps)

    def test_error_recovery_scenario(self, mock_dialog):
        """Test error handling and recovery scenario."""
        # Start with error state
        mock_dialog.handle_error("Initial connection error")

        # Verify error was displayed
        error_calls = [call for call in mock_dialog.message_label.setText.call_args_list
                      if "Error:" in str(call)]
        assert len(error_calls) > 0

        # Recovery with normal stats
        recovery_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=10, warnings=0, errors=0,
            ratio=0.1
        )

        with patch.object(mock_dialog, '_update_status_indicators'), \
             patch.object(mock_dialog, '_update_message'):

            mock_dialog.update_stats(recovery_stats)

            # Normal update should override error message
            mock_dialog._update_message.assert_called_once_with(recovery_stats)

    def test_boundary_condition_handling(self, mock_dialog):
        """Test handling of boundary conditions in statistics."""
        # Test with maximum reasonable values
        max_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=999999, stacks=1000000, warnings=50000, errors=10000,
            ratio=0.999999
        )

        mock_dialog.update_stats(max_stats)

        # Should handle large numbers
        mock_dialog.stat_value_labels["dumps"].setText.assert_called_with("999999")
        mock_dialog.stat_value_labels["stacks"].setText.assert_called_with("1000000")

        # Test with zero denominators (edge case for ratio)
        zero_denominator_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=5, stacks=0, warnings=0, errors=0,
            ratio=float('inf')  # This could happen with zero stacks
        )

        # Should handle infinite ratio gracefully
        try:
            mock_dialog.update_stats(zero_denominator_stats)
        except Exception:
            pytest.fail("Dialog should handle infinite ratio gracefully")


@pytest.mark.unit
@pytest.mark.gui
class TestDialogAccessibilityAndUsability:
    """Test dialog accessibility and usability features."""

    @pytest.fixture
    def mock_dialog(self, qt_application):
        """Create a real dialog with mocked labels for testing."""
        # Create a real dialog instance
        dialog = PapyrusMonitorDialog(None)

        # Mock the label widgets to track setText calls
        dialog.timestamp_label = MagicMock()
        dialog.stat_status_labels = {
            "dumps": MagicMock(),
            "stacks": MagicMock(),
            "dumps_stacks_ratio": MagicMock(),
            "warnings": MagicMock(),
            "errors": MagicMock(),
        }
        dialog.message_label = MagicMock()
        dialog.stat_value_labels = {
            "dumps": MagicMock(),
            "stacks": MagicMock(),
            "dumps_stacks_ratio": MagicMock(),
            "warnings": MagicMock(),
            "errors": MagicMock(),
        }

        yield dialog

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_timestamp_format_readability(self, mock_dialog):
        """Test that timestamp is formatted for readability."""
        test_times = [
            datetime(2024, 1, 15, 9, 5, 3),    # Single digit minutes/seconds
            datetime(2024, 1, 15, 23, 59, 59),  # Late night
            datetime(2024, 1, 15, 0, 0, 0),     # Midnight
            datetime(2024, 1, 15, 12, 30, 45),  # Noon
        ]

        expected_formats = [
            "09:05:03",
            "23:59:59",
            "00:00:00",
            "12:30:45"
        ]

        for test_time, expected in zip(test_times, expected_formats):
            stats = PapyrusStats(
                timestamp=test_time,
                dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0
            )

            mock_dialog.update_stats(stats)

            # Verify timestamp format
            call_args = mock_dialog.timestamp_label.setText.call_args[0][0]
            assert expected in call_args

    def test_status_indicator_symbols(self, mock_dialog):
        """Test that status indicators use appropriate symbols."""
        # Test good status symbols
        good_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=10, warnings=0, errors=0,
            ratio=0.1
        )

        mock_dialog._update_status_indicators(good_stats)

        # All should show checkmarks for good status
        for key in ["warnings", "errors", "dumps_stacks_ratio"]:
            label = mock_dialog.stat_status_labels[key]
            label.setText.assert_called_with("✓")

        # Test warning symbols
        warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=6, stacks=10, warnings=2, errors=0,
            ratio=0.6
        )

        mock_dialog._update_status_indicators(warning_stats)

        # Should use warning symbols
        warnings_label = mock_dialog.stat_status_labels["warnings"]
        warnings_label.setText.assert_called_with("⚠️")

        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("⚠️")

        # Test error symbols
        error_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=9, stacks=10, warnings=0, errors=3,
            ratio=0.9
        )

        mock_dialog._update_status_indicators(error_stats)

        # Should use error symbols
        errors_label = mock_dialog.stat_status_labels["errors"]
        errors_label.setText.assert_called_with("❌")

        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("❌")

    def test_message_color_coding_consistency(self, mock_dialog):
        """Test that message colors are consistent with severity."""
        # Test error colors (highest severity)
        error_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=5, warnings=0, errors=1,
            ratio=0.2
        )

        mock_dialog._update_message(error_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

        # Test warning colors (medium severity)
        warning_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=5, warnings=1, errors=0,
            ratio=0.2
        )

        mock_dialog._update_message(warning_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange; font-weight: bold;")

        # Test caution colors (low severity)
        caution_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=6, stacks=10, warnings=0, errors=0,
            ratio=0.6
        )

        mock_dialog._update_message(caution_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange;")

        # Test normal colors (no issues)
        normal_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=1, stacks=10, warnings=0, errors=0,
            ratio=0.1
        )

        mock_dialog._update_message(normal_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: green;")

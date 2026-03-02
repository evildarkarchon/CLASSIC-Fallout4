from datetime import timezone

"""
Unit tests for PapyrusDialog action handling and integration scenarios.

This module tests dialog action handling (stop button, error handling, close events)
and integration scenarios for the PapyrusMonitorDialog class with properly mocked Qt components.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841, F401, DOC201
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.Interface.dialogs.papyrus_dialog import PapyrusMonitorDialog
from ClassicLib.Interface.widgets.papyrus import PapyrusStats

is_xdist = os.environ.get("PYTEST_XDIST_WORKER") is not None
skip_xdist = pytest.mark.skipif(is_xdist, reason="Qt GUI tests unstable in xdist workers on Windows")


@pytest.mark.unit
@pytest.mark.gui
@skip_xdist
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
        with patch.object(mock_dialog, "accept") as mock_accept:
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
@skip_xdist
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
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc), dumps=2, stacks=20, warnings=0, errors=0, ratio=0.1
        )

        with (
            patch.object(mock_dialog, "_update_status_indicators") as mock_status,
            patch.object(mock_dialog, "_update_message") as mock_message,
        ):
            mock_dialog.update_stats(normal_stats)

            # Verify all components were updated
            mock_dialog.timestamp_label.setText.assert_called()
            mock_status.assert_called_once_with(normal_stats)
            mock_message.assert_called_once_with(normal_stats)

        # Scenario 2: Problem detected
        problem_stats = PapyrusStats(
            timestamp=datetime(2024, 1, 15, 12, 5, 0, tzinfo=timezone.utc), dumps=15, stacks=20, warnings=3, errors=1, ratio=0.75
        )

        mock_dialog.update_stats(problem_stats)

        # Verify values were updated
        assert mock_dialog.stat_value_labels["errors"].setText.call_count > 0

    def test_dialog_lifecycle_with_monitoring(self, mock_dialog):
        """Test complete dialog lifecycle with monitoring start/stop."""
        # Simulate monitoring start
        initial_stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0)

        mock_dialog.update_stats(initial_stats)

        # Simulate some monitoring activity
        active_stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=5, stacks=15, warnings=1, errors=0, ratio=0.33)

        mock_dialog.update_stats(active_stats)

        # Simulate stopping monitoring
        with patch.object(mock_dialog, "accept") as mock_accept:
            mock_dialog.stop_monitoring = MagicMock()
            mock_dialog.stop_monitoring.emit = MagicMock()

            mock_dialog.on_stop_clicked()

            # Verify proper cleanup
            mock_dialog.stop_monitoring.emit.assert_called_once()
            mock_accept.assert_called_once()

    def test_rapid_stats_updates(self, mock_dialog):
        """Test handling of rapid statistics updates."""
        # Simulate rapid updates
        timestamps = [datetime(2024, 1, 15, 12, 0, i, tzinfo=timezone.utc) for i in range(10)]

        for i, timestamp in enumerate(timestamps):
            stats = PapyrusStats(timestamp=timestamp, dumps=i, stacks=i * 2, warnings=i // 3, errors=i // 5, ratio=min(i / 10.0, 1.0))

            mock_dialog.update_stats(stats)

        # Verify final state reflects last update
        final_expected_dumps = "9"
        mock_dialog.stat_value_labels["dumps"].setText.assert_called_with(final_expected_dumps)

    def test_error_recovery_scenario(self, mock_dialog):
        """Test error handling and recovery scenario."""
        # Start with error state
        mock_dialog.handle_error("Initial connection error")

        # Verify error was displayed
        error_calls = [call for call in mock_dialog.message_label.setText.call_args_list if "Error:" in str(call)]
        assert len(error_calls) > 0

        # Recovery with normal stats
        recovery_stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=1, stacks=10, warnings=0, errors=0, ratio=0.1)

        with patch.object(mock_dialog, "_update_status_indicators"), patch.object(mock_dialog, "_update_message"):
            mock_dialog.update_stats(recovery_stats)

            # Normal update should override error message
            mock_dialog._update_message.assert_called_once_with(recovery_stats)

    def test_boundary_condition_handling(self, mock_dialog):
        """Test handling of boundary conditions in statistics."""
        # Test with maximum reasonable values
        max_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc), dumps=999999, stacks=1000000, warnings=50000, errors=10000, ratio=0.999999
        )

        mock_dialog.update_stats(max_stats)

        # Should handle large numbers
        mock_dialog.stat_value_labels["dumps"].setText.assert_called_with("999999")
        mock_dialog.stat_value_labels["stacks"].setText.assert_called_with("1000000")

        # Test with zero denominators (edge case for ratio)
        zero_denominator_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=5,
            stacks=0,
            warnings=0,
            errors=0,
            ratio=float("inf"),  # This could happen with zero stacks
        )

        # Should handle infinite ratio gracefully
        try:
            mock_dialog.update_stats(zero_denominator_stats)
        except Exception:
            pytest.fail("Dialog should handle infinite ratio gracefully")

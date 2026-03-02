from datetime import timezone

"""
Unit tests for PapyrusDialog update functionality.

This module tests statistics updates, status indicator updates, and message
updates for the PapyrusMonitorDialog class with properly mocked Qt components.
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
            timestamp=datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc), dumps=5, stacks=10, warnings=2, errors=1, ratio=0.5
        )

    @pytest.fixture
    def zero_stats(self):
        """Create zero PapyrusStats for testing initial state."""
        return PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0)

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
        expected_updates = {"dumps": "5", "stacks": "10", "dumps_stacks_ratio": "0.500", "warnings": "2", "errors": "1"}

        for key, expected_value in expected_updates.items():
            mock_label = mock_dialog.stat_value_labels[key]
            mock_label.setText.assert_called_with(expected_value)

    def test_update_stats_zero_values(self, mock_dialog, zero_stats):
        """Test updating with zero stats."""
        mock_dialog.update_stats(zero_stats)

        # Verify zero values are displayed correctly
        expected_updates = {"dumps": "0", "stacks": "0", "dumps_stacks_ratio": "0.000", "warnings": "0", "errors": "0"}

        for key, expected_value in expected_updates.items():
            mock_label = mock_dialog.stat_value_labels[key]
            mock_label.setText.assert_called_with(expected_value)

    def test_update_stats_calls_status_indicators(self, mock_dialog, sample_stats):
        """Test that status indicators are updated."""
        with (
            patch.object(mock_dialog, "_update_status_indicators") as mock_status,
            patch.object(mock_dialog, "_update_message") as mock_message,
        ):
            mock_dialog.update_stats(sample_stats)

            # Verify helper methods were called
            mock_status.assert_called_once_with(sample_stats)
            mock_message.assert_called_once_with(sample_stats)

    def test_update_stats_high_ratio_precision(self, mock_dialog):
        """Test ratio display precision with various values."""
        test_ratios = [(0.123456789, "0.123"), (0.999, "0.999"), (1.0, "1.000"), (0.0, "0.000"), (0.5, "0.500")]

        for ratio, expected in test_ratios:
            stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=1, stacks=2, warnings=0, errors=0, ratio=ratio)

            mock_dialog.update_stats(stats)

            # Verify ratio precision
            mock_label = mock_dialog.stat_value_labels["dumps_stacks_ratio"]
            mock_label.setText.assert_called_with(expected)


@pytest.mark.unit
@pytest.mark.gui
@skip_xdist
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
            timestamp=datetime.now(timezone.utc),
            dumps=1,
            stacks=5,
            warnings=0,
            errors=0,
            ratio=0.2,  # Good ratio
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
            timestamp=datetime.now(timezone.utc),
            dumps=6,
            stacks=10,
            warnings=0,
            errors=0,
            ratio=0.6,  # Warning ratio
        )

        mock_dialog._update_status_indicators(warning_stats)

        # Verify warning ratio indicator
        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("⚠️")
        ratio_label.setStyleSheet.assert_called_with("color: orange;")

    def test_update_status_indicators_critical_ratio(self, mock_dialog):
        """Test status indicators with critical ratio (> 0.8)."""
        critical_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=9,
            stacks=10,
            warnings=0,
            errors=0,
            ratio=0.9,  # Critical ratio
        )

        mock_dialog._update_status_indicators(critical_stats)

        # Verify critical ratio indicator
        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("❌")
        ratio_label.setStyleSheet.assert_called_with("color: red;")

    def test_update_status_indicators_with_warnings(self, mock_dialog):
        """Test status indicators when warnings are present."""
        warning_stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=1, stacks=5, warnings=3, errors=0, ratio=0.2)

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
        error_stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=1, stacks=5, warnings=0, errors=2, ratio=0.2)

        mock_dialog._update_status_indicators(error_stats)

        # Verify errors indicator
        errors_label = mock_dialog.stat_status_labels["errors"]
        errors_label.setText.assert_called_with("❌")
        errors_label.setStyleSheet.assert_called_with("color: red;")

    def test_update_status_indicators_multiple_issues(self, mock_dialog):
        """Test status indicators with multiple issues."""
        multi_issue_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=8,
            stacks=10,
            warnings=5,
            errors=3,
            ratio=0.8,  # Exactly at threshold
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
@skip_xdist
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
        error_stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=1, stacks=5, warnings=2, errors=3, ratio=0.2)

        mock_dialog._update_message(error_stats)

        # Should prioritize error message
        mock_dialog.message_label.setText.assert_called_with("3 errors detected in Papyrus log!")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

    def test_update_message_with_warnings_no_errors(self, mock_dialog):
        """Test message when warnings are present but no errors."""
        warning_stats = PapyrusStats(timestamp=datetime.now(timezone.utc), dumps=1, stacks=5, warnings=4, errors=0, ratio=0.2)

        mock_dialog._update_message(warning_stats)

        # Should show warning message
        mock_dialog.message_label.setText.assert_called_with("4 warnings detected in Papyrus log.")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange; font-weight: bold;")

    def test_update_message_high_ratio_no_errors_warnings(self, mock_dialog):
        """Test message with high ratio but no errors/warnings."""
        high_ratio_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=9,
            stacks=10,
            warnings=0,
            errors=0,
            ratio=0.9,  # High ratio
        )

        mock_dialog._update_message(high_ratio_stats)

        # Should show high ratio warning
        mock_dialog.message_label.setText.assert_called_with("Warning: High dumps-to-stacks ratio detected!")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

    def test_update_message_medium_ratio_no_issues(self, mock_dialog):
        """Test message with medium ratio but no other issues."""
        medium_ratio_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=6,
            stacks=10,
            warnings=0,
            errors=0,
            ratio=0.6,  # Medium ratio
        )

        mock_dialog._update_message(medium_ratio_stats)

        # Should show caution message
        mock_dialog.message_label.setText.assert_called_with("Caution: Elevated dumps-to-stacks ratio.")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange;")

    def test_update_message_all_good(self, mock_dialog):
        """Test message when all stats are good."""
        good_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=1,
            stacks=10,
            warnings=0,
            errors=0,
            ratio=0.1,  # Good ratio
        )

        mock_dialog._update_message(good_stats)

        # Should show normal message
        mock_dialog.message_label.setText.assert_called_with("Papyrus log appears normal.")
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: green;")

    def test_update_message_priority_order(self, mock_dialog):
        """Test message priority order: errors > warnings > high ratio > medium ratio > normal."""
        # Test that errors take priority over all else
        all_issues_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=9,
            stacks=10,
            warnings=5,
            errors=2,
            ratio=0.9,  # High ratio, warnings, AND errors
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
            timestamp=datetime.now(timezone.utc),
            dumps=5,
            stacks=10,
            warnings=0,
            errors=0,
            ratio=0.5,  # Exactly at boundary
        )

        mock_dialog._update_message(edge_stats)

        # At exactly 0.5, should not trigger elevated message (> 0.5 needed)
        mock_dialog.message_label.setText.assert_called_with("Papyrus log appears normal.")

        # Test exactly at 0.8 boundary
        edge_stats = PapyrusStats(
            timestamp=datetime.now(timezone.utc),
            dumps=8,
            stacks=10,
            warnings=0,
            errors=0,
            ratio=0.8,  # Exactly at boundary
        )

        mock_dialog._update_message(edge_stats)

        # At exactly 0.8, should trigger caution (0.5 < ratio <= 0.8)
        # not the high ratio warning (which needs > 0.8)
        mock_dialog.message_label.setText.assert_called_with("Caution: Elevated dumps-to-stacks ratio.")

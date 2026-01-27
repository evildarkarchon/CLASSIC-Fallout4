"""
Unit tests for PapyrusDialog UI, accessibility, and layout.

This module tests accessibility features, usability, layout, and formatting
for the PapyrusMonitorDialog class with properly mocked Qt components.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841, F401, DOC201
import os
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from ClassicLib.Interface.dialogs.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.widgets.Papyrus import PapyrusStats

is_xdist = os.environ.get("PYTEST_XDIST_WORKER") is not None
skip_xdist = pytest.mark.skipif(is_xdist, reason="Qt GUI tests unstable in xdist workers on Windows")


@pytest.mark.unit
@pytest.mark.gui
@skip_xdist
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
            datetime(2024, 1, 15, 9, 5, 3),  # Single digit minutes/seconds
            datetime(2024, 1, 15, 23, 59, 59),  # Late night
            datetime(2024, 1, 15, 0, 0, 0),  # Midnight
            datetime(2024, 1, 15, 12, 30, 45),  # Noon
        ]

        expected_formats = ["09:05:03", "23:59:59", "00:00:00", "12:30:45"]

        for test_time, expected in zip(test_times, expected_formats, strict=False):
            stats = PapyrusStats(timestamp=test_time, dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0)

            mock_dialog.update_stats(stats)

            # Verify timestamp format
            call_args = mock_dialog.timestamp_label.setText.call_args[0][0]
            assert expected in call_args

    def test_status_indicator_symbols(self, mock_dialog):
        """Test that status indicators use appropriate symbols."""
        # Test good status symbols
        good_stats = PapyrusStats(timestamp=datetime.now(), dumps=1, stacks=10, warnings=0, errors=0, ratio=0.1)

        mock_dialog._update_status_indicators(good_stats)

        # All should show checkmarks for good status
        for key in ["warnings", "errors", "dumps_stacks_ratio"]:
            label = mock_dialog.stat_status_labels[key]
            label.setText.assert_called_with("✓")

        # Test warning symbols
        warning_stats = PapyrusStats(timestamp=datetime.now(), dumps=6, stacks=10, warnings=2, errors=0, ratio=0.6)

        mock_dialog._update_status_indicators(warning_stats)

        # Should use warning symbols
        warnings_label = mock_dialog.stat_status_labels["warnings"]
        warnings_label.setText.assert_called_with("⚠️")

        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("⚠️")

        # Test error symbols
        error_stats = PapyrusStats(timestamp=datetime.now(), dumps=9, stacks=10, warnings=0, errors=3, ratio=0.9)

        mock_dialog._update_status_indicators(error_stats)

        # Should use error symbols
        errors_label = mock_dialog.stat_status_labels["errors"]
        errors_label.setText.assert_called_with("❌")

        ratio_label = mock_dialog.stat_status_labels["dumps_stacks_ratio"]
        ratio_label.setText.assert_called_with("❌")

    def test_message_color_coding_consistency(self, mock_dialog):
        """Test that message colors are consistent with severity."""
        # Test error colors (highest severity)
        error_stats = PapyrusStats(timestamp=datetime.now(), dumps=1, stacks=5, warnings=0, errors=1, ratio=0.2)

        mock_dialog._update_message(error_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: red; font-weight: bold;")

        # Test warning colors (medium severity)
        warning_stats = PapyrusStats(timestamp=datetime.now(), dumps=1, stacks=5, warnings=1, errors=0, ratio=0.2)

        mock_dialog._update_message(warning_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange; font-weight: bold;")

        # Test caution colors (low severity)
        caution_stats = PapyrusStats(timestamp=datetime.now(), dumps=6, stacks=10, warnings=0, errors=0, ratio=0.6)

        mock_dialog._update_message(caution_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: orange;")

        # Test normal colors (no issues)
        normal_stats = PapyrusStats(timestamp=datetime.now(), dumps=1, stacks=10, warnings=0, errors=0, ratio=0.1)

        mock_dialog._update_message(normal_stats)
        mock_dialog.message_label.setStyleSheet.assert_called_with("color: green;")


@pytest.mark.unit
@pytest.mark.gui
@skip_xdist
class TestDialogLayoutAndFormatting:
    """Test dialog layout, formatting, and visual properties."""

    @pytest.fixture
    def dialog(self, qt_application):
        """Create a real PapyrusMonitorDialog for layout testing."""
        from PySide6.QtWidgets import QLabel

        dialog = PapyrusMonitorDialog(None)
        yield dialog
        dialog.close()
        dialog.deleteLater()

    def test_font_configuration(self, dialog):
        """Test that fonts are configured correctly."""
        from PySide6.QtWidgets import QLabel, QVBoxLayout

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
                    return
        pytest.fail("Title label not found")

    def test_label_alignments(self, dialog):
        """Test that labels have proper alignments."""
        from PySide6.QtCore import Qt

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

    def test_signal_emission_on_destruction(self, qt_application):
        """Test that signals are properly handled during dialog destruction."""
        dialog = PapyrusMonitorDialog(None)

        # Track signal emissions
        signal_emitted = False

        def signal_handler():
            nonlocal signal_emitted
            signal_emitted = True

        dialog.stop_monitoring.connect(signal_handler)

        # Close the dialog
        dialog.close()

        # Signal should have been emitted
        assert signal_emitted

        # Cleanup
        dialog.deleteLater()

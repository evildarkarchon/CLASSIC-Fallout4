"""
Report metadata widget for displaying scan report statistics.

This module provides a widget for showing metadata and statistics about
CLASSIC scan reports including date, size, and issue counts.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)

if TYPE_CHECKING:
    from pathlib import Path

# Pre-compiled regex patterns for performance optimization
# noinspection RegExpRedundantEscape
_ERROR_PATTERN = re.compile(r"\[!?\s*ERROR\s*\]([^\n]*)", re.IGNORECASE)
# noinspection RegExpRedundantEscape
_WARNING_PATTERN = re.compile(r"\[!?\s*WARNING\s*\]([^\n]*)", re.IGNORECASE)
_ISSUE_LIST_PATTERN = re.compile(r"^[-*]\s+.+", re.MULTILINE)


class ReportMetadataWidget(QGroupBox):
    """
    Widget for displaying report metadata and statistics.

    Shows information about the scan report including date, size, and issue counts.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the metadata widget."""
        super().__init__("Report Information", parent)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setSpacing(15)

        # Create labels for metadata
        self.date_label = QLabel("Date: N/A")
        self.size_label = QLabel("Size: N/A")
        self.issues_label = QLabel("Issues: N/A")

        # Add labels to layout
        layout.addWidget(self.date_label)
        layout.addWidget(self.issues_label)
        layout.addWidget(self.size_label)
        layout.addStretch()

        # Style the widget
        self._apply_styling()

        # Set maximum height to keep it compact
        self.setMaximumHeight(60)

    def _apply_styling(self) -> None:
        """Apply custom styling to the widget."""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                font-weight: normal;
            }
        """)

    def update_metadata(self, report_path: Path, content: str) -> None:
        """
        Update the displayed metadata from a report.

        Args:
            report_path: Path to the report file.
            content: The report content.
        """
        # Update date from file modification time
        stat = report_path.stat()
        mod_time = QDateTime.fromSecsSinceEpoch(int(stat.st_mtime))
        self.date_label.setText(f"Date: {mod_time.toString('yyyy-MM-dd hh:mm:ss')}")

        # Update size
        size_kb = stat.st_size / 1024
        self.size_label.setText(f"Size: {size_kb:.1f} KB")

        # Count issues
        issues = self._count_issues(content)
        self.issues_label.setText(f"Issues: {issues}")

    # noinspection RegExpRedundantEscape
    @staticmethod
    def _count_issues(content: str) -> str:
        """
        Count the number of issues in the report.

        Args:
            content: The report content.

        Returns:
            Issue count string.
        """
        # Count various issue indicators using pre-compiled patterns
        errors = len(_ERROR_PATTERN.findall(content))
        warnings = len(_WARNING_PATTERN.findall(content))

        # Look for issue lists
        issues = len(_ISSUE_LIST_PATTERN.findall(content))

        if errors > 0:
            return f"{errors} errors, {warnings} warnings"
        if warnings > 0:
            return f"{warnings} warnings"
        if issues > 0:
            return f"{issues} items"
        return "None found"

    def clear(self) -> None:
        """Clear all metadata displays."""
        self.date_label.setText("Date: N/A")
        self.size_label.setText("Size: N/A")
        self.issues_label.setText("Issues: N/A")

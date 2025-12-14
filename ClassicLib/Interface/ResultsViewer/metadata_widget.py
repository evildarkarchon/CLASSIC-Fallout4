"""Widget for displaying report metadata.

This module provides the ReportMetadataWidget which displays information
such as modification date, file size, and issue counts for scan reports.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QWidget


class ReportMetadataWidget(QGroupBox):
    """Widget for displaying report metadata.

    This widget provides a user interface to display metadata such as the last
    modification date, size of the report file, and the count of issues found
    within a report. It is compact and styled to blend seamlessly within a
    larger application interface.

    Attributes:
        date_label (QLabel): Label to display the report's last modified date.
        size_label (QLabel): Label to display the size of the report file.
        issues_label (QLabel): Label for displaying the issue count within the
            report.

    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create a widget displaying metadata about a report including date, size, and issues.

        The widget organizes the metadata within a horizontal layout and provides styling to
        keep the widget visually cohesive and compact. The metadata labels are dynamically
        created with default placeholder values.
        """
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
        """Apply specific styling to the graphical components using Qt's stylesheet syntax.

        This method configures the appearance of QGroupBox and QLabel elements by setting
        properties such as font weight, borders, margin, and padding. The styling is
        applied through Qt's setStyleSheet function utilizing cascading style sheets (CSS).
        """
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
        """Update metadata display such as date, file size, and issue count for a given report.

        This method extracts metadata from the given report file, including its modification
        time and size in kilobytes, and updates corresponding display labels. It also analyzes
        the content of the report to calculate and display the number of issues found.

        Args:
            report_path (Path): Path to the report file for which metadata needs to be updated.
            content (str): The content of the report, used to calculate the issue count.

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
        """Count various issue indicators in a given content.

        This method examines the input string to identify and count specific issue
        indicators such as errors, warnings, and general issue items. It makes use
        of regular expressions to detect problem patterns and produces a summary
        string detailing the findings.

        Args:
            content (str): The input text content to evaluate for issues.

        Returns:
            str: A summary string indicating the number of errors, warnings, or issue items
            found in the content, or "None found" if no issues are detected.

        """
        # Count various issue indicators
        errors = len(re.findall(r"\[!?\s*ERROR\s*\]", content, re.IGNORECASE))
        warnings = len(re.findall(r"\[!?\s*WARNING\s*\]", content, re.IGNORECASE))

        # Look for issue lists
        issues = len(re.findall(r"^[-*]\s+.+", content, re.MULTILINE))

        if errors > 0:
            return f"{errors} errors, {warnings} warnings"
        if warnings > 0:
            return f"{warnings} warnings"
        if issues > 0:
            return f"{issues} items"
        return "None found"

    def clear(self) -> None:
        """Clear the content of the labels displaying date, size, and issues.

        This method resets the text content of `date_label`, `size_label`, and
        `issues_label` to indicate that the values are not available.
        """
        self.date_label.setText("Date: N/A")
        self.size_label.setText("Size: N/A")
        self.issues_label.setText("Issues: N/A")


__all__ = ["ReportMetadataWidget"]

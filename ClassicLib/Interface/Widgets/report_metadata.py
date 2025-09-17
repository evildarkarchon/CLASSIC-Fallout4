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
    A widget for displaying report metadata like date, size, and issues.

    This class provides a compact user interface component for showing metadata
    about a report. The metadata includes the report's last modification date,
    size in kilobytes, and count of issues (errors, warnings, etc.). The widget
    can be updated dynamically with a report file's path and content.

    Attributes:
        date_label (QLabel): Label for displaying the report modification date.
        size_label (QLabel): Label for displaying the report size in KB.
        issues_label (QLabel): Label for displaying the count of issues in the
            report.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initializes a QWidget-based component that displays report metadata including
        date, size, and the number of issues. This compact widget is styled and designed
        to fit efficiently within layouts.

        Args:
            parent (QWidget | None): The parent widget for this component. Defaults to None.
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
        """
        Applies a predefined stylesheet to the current widget to modify its visual
        appearance.

        The method is responsible for setting a specific style for QGroupBox and QLabel
        in the widget hierarchy. This includes setting font properties, borders, and
        margins. The styling is applied consistently to ensure a unified visual design.
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
        """
        Updates the metadata display labels with file information such as modification date,
        file size, and the number of issues present in the content.

        Args:
            report_path (Path): The file path of the report used to retrieve metadata.
            content (str): The textual content of the report required for counting issues.
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
        Counts various issue indicators within the provided content using
        pre-compiled patterns.

        This method analyzes a string input and identifies occurrences
        of errors, warnings, or issue lists based on specific patterns.
        It then summarizes the results in a formatted string.

        Args:
            content: A string to analyze for errors, warnings, and issue lists.

        Returns:
            A string summarizing the count of errors, warnings, or items
            found. If none are found, it returns "None found".
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
        """
        Clears the values displayed on the labels for date, size, and issues, setting
        them to default "N/A" values.

        This method is used to reset the state of the labels to indicate that no
        specific information is available.
        """
        self.date_label.setText("Date: N/A")
        self.size_label.setText("Size: N/A")
        self.issues_label.setText("Issues: N/A")

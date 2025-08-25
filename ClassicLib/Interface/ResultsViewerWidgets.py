"""
Custom widgets for the results viewer interface.

This module provides specialized widgets for displaying and interacting with
CLASSIC scan reports, including a report list, markdown viewer, and metadata display.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QWidget,
)

from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from pathlib import Path

# Pre-compiled regex patterns for performance optimization
# noinspection RegExpRedundantEscape
_FOUND_SECTION_PATTERN = re.compile(r"(\[!\]\s*FOUND\s*:\s*\[[^\]]+\][^\n]*)\n((?:[ \t]+[^\n]+\n)+?)(?=\n|\Z)")
# noinspection RegExpRedundantEscape
_ERROR_PATTERN = re.compile(r"\[!?\s*ERROR\s*\]([^\n]*)", re.IGNORECASE)
# noinspection RegExpRedundantEscape
_WARNING_PATTERN = re.compile(r"\[!?\s*WARNING\s*\]([^\n]*)", re.IGNORECASE)
# noinspection RegExpRedundantEscape
_SOLVED_PATTERN = re.compile(r"\[!?\s*SOLVED\s*\]([^\n]*)", re.IGNORECASE)
_ISSUE_LIST_PATTERN = re.compile(r"^[-*]\s+.+", re.MULTILINE)


class ReportListWidget(QListWidget):
    """
    Custom list widget for displaying scan reports with enhanced features.

    Provides sorting, filtering, and custom item display with report metadata.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the report list widget."""
        super().__init__(parent)

        # Storage for report paths (using item id as key)
        self._report_paths: dict[int, Path] = {}

        # Setup widget properties
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)  # We'll handle sorting manually
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # Create search filter
        self._setup_search_filter()

        # Style configuration
        self._setup_styling()

    def _setup_search_filter(self) -> None:
        """Setup the search filter functionality."""
        # Create search box (will be added to layout by parent)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search reports...")
        self.search_box.textChanged.connect(self._filter_reports)
        self.search_box.setClearButtonEnabled(True)

    def _setup_styling(self) -> None:
        """Configure the widget styling."""
        # Set font for better readability
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

        # Set minimum size
        self.setMinimumWidth(250)

    def populate_reports(self, reports: list[Path]) -> None:
        """
        Populate the list with report files.

        Args:
            reports: List of Path objects pointing to report files.
        """
        # Clear existing items
        self.clear()
        self._report_paths.clear()

        for report_path in reports:
            # Create list item
            item = self._create_report_item(report_path)

            # Add to list
            self.addItem(item)

        # Select first item if available
        if self.count() > 0:
            self.setCurrentRow(0)

    def _create_report_item(self, report_path: Path) -> QListWidgetItem:
        """
        Create a list item for a report file.

        Args:
            report_path: Path to the report file.

        Returns:
            Configured QListWidgetItem.
        """
        # Extract information from filename
        filename = report_path.stem  # Remove -AUTOSCAN suffix

        # Parse timestamp from filename if possible
        timestamp_str = self._extract_timestamp(filename)

        # Determine report status
        status = self._determine_report_status(report_path)
        display_text = f"{timestamp_str}\n{report_path.name}" if timestamp_str else report_path.name

        item = QListWidgetItem(display_text)

        # Set tooltip with full path
        item.setToolTip(str(report_path))

        # Apply status-based styling
        self._apply_status_styling(item, status)

        # Store metadata
        item.setData(
            Qt.ItemDataRole.UserRole,
            {"path": report_path, "status": status, "timestamp": timestamp_str, "size": report_path.stat().st_size},
        )

        return item

    @staticmethod
    def _extract_timestamp(filename: str) -> str | None:
        """
        Extract timestamp from crash log filename.

        Args:
            filename: The filename to parse.

        Returns:
            Formatted timestamp string or None.
        """
        # Pattern for crash log timestamps: crash-YYYY-MM-DD-HHMMSS
        pattern = r"crash-(\d{4})-(\d{2})-(\d{2})-(\d{6})"
        match = re.match(pattern, filename)

        if match:
            year, month, day, time = match.groups()
            hour = time[:2]
            minute = time[2:4]
            second = time[4:6]

            try:
                dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        # Fallback to file modification time
        return None

    @staticmethod
    def _determine_report_status(report_path: Path) -> str:
        """
        Determine the status of a report by examining its content.

        Args:
            report_path: Path to the report file.

        Returns:
            Status string: "solved", "unsolved", "incomplete", or "unknown".
        """
        try:
            content = report_path.read_text(encoding="utf-8", errors="ignore")

            # Check for status indicators in content
            if "INCOMPLETE" in content.upper():
                return "incomplete"
            if "UNSOLVED" in content.upper() or "could not be determined" in content.lower():
                return "unsolved"
            if "SOLVED" in content.upper() or "RECOMMENDATIONS" in content:
                return "solved"
            return "unknown"

        except Exception as e:
            logger.debug(f"Could not determine status for {report_path.name}: {e}")
            return "unknown"

    @staticmethod
    def _apply_status_styling(item: QListWidgetItem, status: str) -> None:
        """
        Apply visual styling based on report status.

        Args:
            item: The list widget item to style.
            status: The report status.
        """
        if status == "solved":
            # Green tint for solved
            item.setBackground(QBrush(QColor(200, 255, 200, 30)))
            item.setForeground(QBrush(QColor(0, 128, 0)))
        elif status == "unsolved":
            # Red tint for unsolved
            item.setBackground(QBrush(QColor(255, 200, 200, 30)))
            item.setForeground(QBrush(QColor(128, 0, 0)))
        elif status == "incomplete":
            # Yellow tint for incomplete
            item.setBackground(QBrush(QColor(255, 255, 200, 30)))
            item.setForeground(QBrush(QColor(128, 128, 0)))
        else:
            # Default styling
            pass

    def _filter_reports(self, text: str) -> None:
        """
        Filter displayed reports based on search text.

        Args:
            text: The search text to filter by.
        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                # Check if search text is in item text or tooltip
                matches = text.lower() in item.text().lower() or text.lower() in item.toolTip().lower()
                item.setHidden(not matches)

    @staticmethod
    def get_report_path(item: QListWidgetItem) -> Path | None:
        """
        Get the report path for a list item.

        Args:
            item: The list widget item.

        Returns:
            Path to the report file or None.
        """
        # Get the metadata stored in UserRole
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and isinstance(data, dict):
            return data.get("path")
        return None

    def get_search_widget(self) -> QWidget:
        """
        Get a widget containing the search functionality.

        Returns:
            Widget with search box.
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 5)

        search_label = QLabel("Filter:")
        layout.addWidget(search_label)
        layout.addWidget(self.search_box)

        return widget


class MarkdownViewer(QTextBrowser):
    """
    Enhanced text browser for displaying markdown-formatted reports.

    Provides markdown rendering, zoom controls, and custom styling.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the markdown viewer."""
        super().__init__(parent)

        # Configure viewer properties
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)

        # Setup markdown support
        self.setAcceptRichText(True)

        # Initialize zoom level
        self._zoom_level = 100

        # Apply custom styling
        self._apply_styling()

    def _apply_styling(self) -> None:
        """Apply custom CSS styling for markdown content."""
        # Base stylesheet for markdown rendering
        style = """
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #e0e0e0;
            background-color: #2b2b2b;
            padding: 10px;
        }
        h1 {
            color: #4CAF50;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 5px;
            margin-top: 20px;
        }
        h2 {
            color: #81C784;
            border-bottom: 1px solid #81C784;
            padding-bottom: 3px;
            margin-top: 15px;
        }
        h3 {
            color: #A5D6A7;
            margin-top: 10px;
        }
        code {
            background-color: #1e1e1e;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Courier New', monospace;
            color: #ce9178;
        }
        pre {
            background-color: #1e1e1e;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        blockquote {
            border-left: 4px solid #4CAF50;
            padding-left: 10px;
            color: #b0b0b0;
            font-style: italic;
        }
        ul, ol {
            padding-left: 20px;
        }
        li {
            margin: 5px 0;
        }
        a {
            color: #64B5F6;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        }
        th, td {
            border: 1px solid #555;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #3a3a3a;
            color: #4CAF50;
        }
        tr:nth-child(even) {
            background-color: #2a2a2a;
        }
        .error {
            color: #f44336;
            font-weight: bold;
        }
        .warning {
            color: #ff9800;
            font-weight: bold;
        }
        .success {
            color: #4CAF50;
            font-weight: bold;
        }
        .info {
            color: #2196F3;
        }
        """

        self.document().setDefaultStyleSheet(style)

    def setMarkdown(self, markdown: str) -> None:
        """
        Set markdown content with enhanced processing.

        Args:
            markdown: The markdown text to display.
        """
        # Process markdown for better display
        processed = self._process_markdown(markdown)

        # Use Qt's built-in markdown support
        super().setMarkdown(processed)

        # Scroll to top
        self.moveCursor(QTextCursor.MoveOperation.Start)

    @staticmethod
    def _process_markdown(markdown: str) -> str:
        """
        Process markdown for enhanced display.

        Args:
            markdown: Raw markdown text.

        Returns:
            Processed markdown text.
        """
        # For better line break preservation, wrap content sections in code blocks
        # This ensures QTextBrowser preserves formatting
        processed = markdown

        # Find [!] FOUND sections and wrap multiline content in code blocks
        def wrap_multiline_content(match):  # noqa: ANN001, ANN202
            header = match.group(1)
            content = match.group(2).rstrip()  # Remove trailing whitespace/newlines
            # Wrap the content in a code b
            return f"{header}\n```\n{content}\n```\n"

        # Use pre-compiled regex patterns for performance
        processed = _FOUND_SECTION_PATTERN.sub(wrap_multiline_content, processed)
        processed = _ERROR_PATTERN.sub(r'<span class="error">[ERROR]\1</span>', processed)
        processed = _WARNING_PATTERN.sub(r'<span class="warning">[WARNING]\1</span>', processed)
        processed = _SOLVED_PATTERN.sub(r'<span class="success">[SOLVED]\1</span>', processed)

        return processed  # noqa: RET504

    def zoom_in(self) -> None:
        """Increase zoom level by 10%."""
        self._zoom_level = min(200, self._zoom_level + 10)
        self._apply_zoom()

    def zoom_out(self) -> None:
        """Decrease zoom level by 10%."""
        self._zoom_level = max(50, self._zoom_level - 10)
        self._apply_zoom()

    def reset_zoom(self) -> None:
        """Reset zoom to 100%."""
        self._zoom_level = 100
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        """Apply the current zoom level."""
        # Apply zoom by scaling the font size
        font = self.font()
        base_size = 14  # Base font size from CSS
        new_size = int(base_size * (self._zoom_level / 100.0))
        font.setPointSize(max(8, new_size))  # Minimum size of 8pt
        self.setFont(font)

    def get_zoom_level(self) -> int:
        """Get the current zoom level as a percentage."""
        return self._zoom_level


class ReportMetadataWidget(QGroupBox):
    """
    Widget for displaying report metadata and statistics.

    Shows information about the scan report including date, status, and statistics.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the metadata widget."""
        super().__init__("Report Information", parent)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setSpacing(15)

        # Create labels for metadata
        self.date_label = QLabel("Date: N/A")
        self.status_label = QLabel("Status: N/A")
        self.size_label = QLabel("Size: N/A")
        self.issues_label = QLabel("Issues: N/A")

        # Add labels to layout
        layout.addWidget(self.date_label)
        layout.addWidget(self.status_label)
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

        # Determine status from content
        status = self._determine_status(content)
        self.status_label.setText(f"Status: {status}")

        # Apply status coloring
        self._apply_status_color(status)

        # Count issues
        issues = self._count_issues(content)
        self.issues_label.setText(f"Issues: {issues}")

    @staticmethod
    def _determine_status(content: str) -> str:
        """
        Determine report status from content.

        Args:
            content: The report content.

        Returns:
            Status string.
        """
        content_upper = content.upper()

        if "INCOMPLETE" in content_upper:
            return "Incomplete"
        if "UNSOLVED" in content_upper:
            return "Unsolved"
        if "SOLVED" in content_upper:
            return "Solved"
        if "ERROR" in content_upper:
            return "Has Errors"
        return "Analyzed"

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

    def _apply_status_color(self, status: str) -> None:
        """
        Apply color coding based on status.

        Args:
            status: The status string.
        """
        if "Solved" in status:
            self.status_label.setStyleSheet("color: #4CAF50;")  # Green
        elif "Unsolved" in status or "Error" in status:
            self.status_label.setStyleSheet("color: #f44336;")  # Red
        elif "Incomplete" in status:
            self.status_label.setStyleSheet("color: #ff9800;")  # Orange
        else:
            self.status_label.setStyleSheet("color: #2196F3;")  # Blue

    def clear(self) -> None:
        """Clear all metadata displays."""
        self.date_label.setText("Date: N/A")
        self.status_label.setText("Status: N/A")
        self.size_label.setText("Size: N/A")
        self.issues_label.setText("Issues: N/A")
        self.status_label.setStyleSheet("")

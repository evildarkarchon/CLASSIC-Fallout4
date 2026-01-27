"""Custom list widget for managing and displaying scan reports with advanced
features.

This module provides functionality to display, sort, and filter scan reports
using a custom list widget. It also includes utilities for styling and
extracting metadata such as timestamps and statuses from report files.

Note:
    MarkdownViewer and ReportMetadataWidget have been refactored into
    the ClassicLib.Interface.ResultsViewer package. Import from there
    for new code, or continue importing from here for backward compatibility.

"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path  # noqa: TC003

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

# Re-export from refactored modules for backward compatibility
from ClassicLib.core.logger import logger
from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer
from ClassicLib.Interface.widgets.metadata_widget import ReportMetadataWidget


class ReportListWidget(QListWidget):
    """A custom QListWidget subclass for managing and displaying a list of crash
    report files with additional features such as filtering, styling, and metadata
    management.

    This widget allows for:
        - Displaying a list of reports with timestamps and statuses.
        - Filtering the list of reports using a search bar.
        - Applying visual styles to list items based on their statuses.
        - Providing metadata for each report file.

    The class supports manual population of report files and provides methods for
    customizing and interacting with the list.

    Attributes:
        search_box (QLineEdit): Search box to filter reports in the list.

    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize an instance of the class.

        This constructor sets up properties for the widget, including alternating row colors,
        sorting settings, and selection mode. Additionally, it initializes specific behavior by
        creating a search filter and applying styling configurations.

        Args:
            parent (QWidget | None): The parent widget for this class. Defaults to None.

        """
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
        """Initialize and configures a search box for filtering reports.

        This method sets up a QLineEdit widget to serve as a search box. The
        search box includes placeholder text, a connection to filter reports
        based on input text, and the ability to clear the entered text using a
        clear button.

        Raises:
            None

        """
        # Create search box (will be added to layout by parent)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search reports...")
        self.search_box.textChanged.connect(self._filter_reports)
        self.search_box.setClearButtonEnabled(True)

    def _setup_styling(self) -> None:
        """Set up the initial styling for the widget, including configuring the font size
        and minimum width of the widget for better readability and usability.
        """
        # Set font for better readability
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

        # Set minimum size
        self.setMinimumWidth(250)

    def populate_reports(self, reports: list[Path]) -> None:
        """Populate the report list with given report file paths.

        This method clears any existing items in the list and refreshes it with new
        items based on the provided list of file paths. Failed reports (those containing
        parsing errors) are filtered out. It also selects the first item in the list
        if the list is not empty.

        Args:
            reports (list[Path]): A list of Path objects representing report file
                paths to populate the list with.

        """
        # Clear existing items
        self.clear()
        self._report_paths.clear()

        for report_path in reports:
            # Determine status and skip failed reports
            status = self._determine_report_status(report_path)
            if status == "failed":
                logger.debug(f"Filtering out failed report: {report_path.name}")
                continue

            # Create list item with pre-computed status
            item = self._create_report_item(report_path, status)

            # Add to list
            self.addItem(item)

        # Select first item if available
        if self.count() > 0:
            self.setCurrentRow(0)

    def _create_report_item(self, report_path: Path, status: str | None = None) -> QListWidgetItem:
        """Create a QListWidgetItem based on the provided report file path. Extracts metadata
        such as timestamp, status, and file size from the file to enhance the item's
        properties, including tooltip and display text. The status of the report is used
        to apply appropriate styling to the item.

        Args:
            report_path (Path): The path to the report file.
            status (str | None): Optional pre-computed status to avoid reading the file
                again. If None, the status will be determined by reading the file.

        Returns:
            QListWidgetItem: The created list widget item with metadata and applied styling.

        """
        # Extract information from filename
        filename = report_path.stem  # Remove -AUTOSCAN suffix

        # Parse timestamp from filename if possible
        timestamp_str = self._extract_timestamp(filename)

        # Use pre-computed status if provided, otherwise determine it
        if status is None:
            status = self._determine_report_status(report_path)

        # Create item with display text
        # display_text = filename.replace("-AUTOSCAN", "") # looks to be unused.
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
        """Extract a timestamp from the given filename if it follows the specific pattern
        for crash log timestamps, or falls back to `None` if extraction fails.

        The expected pattern for filenames is `crash-YYYY-MM-DD-HHMMSS`. If the filename
        matches this pattern, it extracts and converts the timestamp into a formatted
        datetime string (`YYYY-MM-DD HH:MM:SS`). If the pattern does not match or a
        ValueError occurs during parsing, it will return `None`.

        Args:
            filename (str): The name of the file to extract the timestamp from.

        Returns:
            str | None: A formatted timestamp as a string, or `None` if extraction
            fails.

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
                pass  # Invalid date/time, fall through to file modification time

        # Fallback to file modification time
        return None

    @staticmethod
    def _determine_report_status(report_path: Path) -> str:
        """Determine the status of a report based on its content.

        The method reads the content of a report file and determines its status by
        checking for specific indicators within the text. The possible statuses
        returned are:
        - "failed" if the content contains error indicators like "Error processing log:",
          "UNABLE TO PROPERLY SCAN", "# Processing Error", or "could not be processed"
        - "incomplete" if the content contains "INCOMPLETE"
        - "unsolved" if the content contains "UNSOLVED" or "could not be determined"
        - "solved" if the content contains "SOLVED" or "RECOMMENDATIONS"
        - "unknown" if no matching indicators are found or an error occurs while
          reading the file.

        Args:
            report_path (Path): The path to the report file whose status needs to be
                determined.

        Returns:
            str: A string representing the status of the report ("failed",
                "incomplete", "unsolved", "solved", or "unknown").

        """
        try:
            content = report_path.read_text(encoding="utf-8", errors="ignore")

        except Exception as e:  # noqa: BLE001
            logger.debug(f"Could not determine status for {report_path.name}: {e}")
        else:
            # Check for FAILED indicators first (most specific)
            content_upper = content.upper()
            if (
                "Error processing log:" in content
                or "UNABLE TO PROPERLY SCAN" in content_upper
                or "# PROCESSING ERROR" in content_upper
                or "COULD NOT BE PROCESSED" in content_upper
            ):
                return "failed"

            # Check for status indicators in content
            if "INCOMPLETE" in content.upper():
                return "incomplete"
            if "UNSOLVED" in content.upper() or "could not be determined" in content.lower():
                return "unsolved"
            if "SOLVED" in content.upper() or "RECOMMENDATIONS" in content:
                return "solved"

        return "unknown"

    @staticmethod
    def _apply_status_styling(item: QListWidgetItem, status: str) -> None:
        """Apply specific styling to a QListWidgetItem based on its status. Each status is
        represented by a distinct background and foreground color. The statuses handled
        are "solved", "unsolved", and "incomplete". If the status does not match one of
        these, the default styling remains unchanged.

        Args:
            item (QListWidgetItem): The item to be styled.
            status (str): The status value determining how the item is styled. Possible
                values are "solved", "unsolved", and "incomplete".

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
            pass  # Default styling, no changes needed

    def _filter_reports(self, text: str) -> None:
        """Filter the reports displayed within the current context based on the provided
        text. Items that do not match the criteria will be hidden.

        Args:
            text (str): The text used for filtering items. Matching is case-insensitive
                and checks against both the item's text and tooltip.

        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                # Check if search text is in item text or tooltip
                matches = text.lower() in item.text().lower() or text.lower() in item.toolTip().lower()
                item.setHidden(not matches)

    @staticmethod
    def get_report_path(item: QListWidgetItem) -> Path | None:
        """Get the report path stored in the metadata of the given QListWidgetItem.

        The method accesses the metadata associated with the provided item in the UserRole
        property. If the metadata is a dictionary, it retrieves and returns the value
        associated with the key "path". If the metadata is absent or not a dictionary,
        the method returns None.

        Args:
            item (QListWidgetItem): The list widget item containing the metadata
            to extract the path from.

        Returns:
            Path | None: The path extracted from the item's metadata if available,
            otherwise None.

        """
        # Get the metadata stored in UserRole
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and isinstance(data, dict):
            return data.get("path")  # pyright: ignore[reportUnknownVariableType]
        return None

    def get_search_widget(self) -> QWidget:
        """Create and configures a search widget with a label and search box.

        This method constructs a QWidget containing a horizontal layout. The layout
        includes a label ("Filter:") and a search box, both added to the layout,
        specifically prepared for filtering purposes.

        Returns:
            QWidget: The constructed widget containing the label and search box.

        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 5)

        search_label = QLabel("Filter:")
        layout.addWidget(search_label)
        layout.addWidget(self.search_box)

        return widget


__all__ = [
    "MarkdownViewer",
    "ReportListWidget",
    "ReportMetadataWidget",
]

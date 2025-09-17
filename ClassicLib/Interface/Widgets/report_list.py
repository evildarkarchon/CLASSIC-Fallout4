"""
Report list widget for displaying scan reports.

This module provides a custom QListWidget for displaying and filtering
CLASSIC scan reports with enhanced features.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

if TYPE_CHECKING:
    from pathlib import Path


class ReportListWidget(QListWidget):
    """
    A widget for managing and displaying a list of reports.

    This class extends the functionality of QListWidget to provide an enhanced
    user interface for handling a collection of report files. The widget includes
    features like report searching, dynamic styling, and sorting. It is specifically
    designed for reports stored in a directory as markdown (.md) files.

    Attributes:
        search_box (QLineEdit): Input box for filtering reports in the list.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initializes a custom widget with advanced styling and features like sorting, alternating
        row colors, and a single selection mode. Additionally, sets up a search filter for
        improved usability.

        Args:
            parent (QWidget | None): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        # Store report paths for later retrieval
        self._report_paths: dict[str, Path] = {}

        # Configure list behavior
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # Set up search filter
        self._setup_search_filter()

        # Apply enhanced styling
        self._setup_styling()

    def _setup_search_filter(self) -> None:
        """
        Initializes the search filter functionality for report filtering.

        This method sets up a search box widget and configures its placeholder text.
        It connects the text change event of the search box to the filtering function,
        allowing for dynamic filtering of reports based on the user's input.

        Raises:
            Exception: If there is an error during the setup or connection of the search box.
        """
        # Create search box (will be added to layout by parent)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search reports...")
        self.search_box.textChanged.connect(self._filter_reports)

    def _setup_styling(self) -> None:
        """
        Sets up the styling for the QListWidget by applying a predefined stylesheet.

        This method configures the visual appearance of the QListWidget component
        by setting a stylesheet that defines its border, border radius, and padding.
        """
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
        """)

    def populate_reports(self, reports_dir: Path) -> None:
        """
        Populates the reports in the collection by scanning the provided directory
        for markdown files. The reports are added in the order of their last
        modification time, starting from the most recently modified.

        Args:
            reports_dir: The directory containing markdown report files. Only files
                with a '.md' extension will be considered. If the directory does not
                exist, no action will be performed.
        """
        self.clear()
        self._report_paths.clear()

        if not reports_dir.exists():
            return

        # Find all report files
        report_files = sorted(reports_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

        for report_file in report_files:
            item = self._create_report_item(report_file)
            if item:
                self.addItem(item)

    def _create_report_item(self, report_file: Path) -> QListWidgetItem | None:
        """
        Creates a QListWidgetItem for a given report file.

        The method extracts metadata, formats display text, and associates additional
        data such as tooltips and sorting information with the created item. If an error
        occurs during the process, it logs the issue and safely returns None.

        Args:
            report_file (Path): The path of the report file to create a QListWidgetItem for.

        Returns:
            QListWidgetItem | None: The created QListWidgetItem if successful, or None if
            there is an error.
        """
        try:
            # Extract timestamp from filename or use file modification time
            timestamp = self._extract_timestamp(report_file)

            # Create item with formatted display text
            item_text = report_file.stem  # Remove .md extension
            item = QListWidgetItem(item_text)

            # Store the full path for later retrieval
            self._report_paths[item_text] = report_file

            # Set tooltip with full information
            item.setToolTip(f"Report: {report_file.name}\nCreated: {timestamp}\nClick to view")

            # Set data for sorting by timestamp
            item.setData(Qt.ItemDataRole.UserRole, timestamp)

            return item

        except (OSError, ValueError) as e:
            # Log error but don't crash
            from ClassicLib.Logger import logger

            logger.error(f"Failed to create item for {report_file}: {e}")
            return None

    @staticmethod
    def _extract_timestamp(report_file: Path) -> str:
        """
        Extracts a timestamp from the given report file.

        This method tries to extract a timestamp from the file name of the report,
        assuming it follows a specific format: "GameName_YYYYMMDD_HHMMSS_report.md".
        If the file name does not match the expected format or fails to provide a
        valid timestamp, the method falls back to using the file's modification time.

        Args:
            report_file (Path): The path to the report file from which a timestamp
                is to be extracted.

        Returns:
            str: The extracted timestamp in the format "YYYY-MM-DD HH:MM:SS". If the
            extraction from the file name fails, the file's modification time is used.
        """
        # Try to extract timestamp from filename first
        # Expected format: GameName_YYYYMMDD_HHMMSS_report.md
        filename = report_file.stem
        parts = filename.split("_")

        if len(parts) >= 3:
            try:
                date_part = parts[-3] if parts[-1] == "report" else parts[-2]
                time_part = parts[-2] if parts[-1] == "report" else parts[-1]

                # Validate format
                if len(date_part) == 8 and len(time_part) == 6:
                    year = int(date_part[:4])
                    month = int(date_part[4:6])
                    day = int(date_part[6:8])
                    hour = int(time_part[:2])
                    minute = int(time_part[2:4])
                    second = int(time_part[4:6])

                    dt = datetime(year, month, day, hour, minute, second)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, IndexError):
                pass

        # Fall back to file modification time
        mtime = report_file.stat().st_mtime
        dt = datetime.fromtimestamp(mtime)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _filter_reports(self, text: str) -> None:
        """
        Filters and hides list items based on a case-insensitive search in their text.

        Args:
            text (str): The text to filter list items by. Items that do not contain
                this text (case-insensitive) will be hidden.

        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                # Case-insensitive search in item text
                item.setHidden(text.lower() not in item.text().lower())

    def get_report_path(self, item_text: str) -> Path | None:
        """
        Retrieves the file path for a given item text from the report paths.

        Args:
            item_text: A string representing the text identifier for which the
                file path is retrieved.

        Returns:
            Path | None: The file path associated with the given item text if
            it exists; otherwise, None.
        """
        return self._report_paths.get(item_text)

    def get_search_widget(self) -> QWidget:
        """
        Creates and returns a search widget containing a search box.

        This method initializes a QWidget and sets a QHBoxLayout to it with no margins.
        The provided search box is added to the layout, and the fully configured widget
        is returned.

        Returns:
            QWidget: The search widget containing the search box.
        """
        search_widget = QWidget()
        layout = QHBoxLayout(search_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_box)
        return search_widget

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
    Custom list widget for displaying scan reports with enhanced features.

    Provides sorting, filtering, and custom item display with report metadata.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the report list widget."""
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
        """Set up the search/filter functionality."""
        # Create search box (will be added to layout by parent)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search reports...")
        self.search_box.textChanged.connect(self._filter_reports)

    def _setup_styling(self) -> None:
        """Apply enhanced styling to the list widget."""
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
        """)

    def populate_reports(self, reports_dir: Path) -> None:
        """
        Populate the list with report files from the specified directory.

        Args:
            reports_dir: Directory containing report files
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
        Create a list item for a report file.

        Args:
            report_file: Path to the report file

        Returns:
            Configured list item or None if creation fails
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
        Extract timestamp from report filename or file metadata.

        Args:
            report_file: Path to the report file

        Returns:
            Formatted timestamp string
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
        Filter visible reports based on search text.

        Args:
            text: Search text to filter by
        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                # Case-insensitive search in item text
                item.setHidden(text.lower() not in item.text().lower())

    def get_report_path(self, item_text: str) -> Path | None:
        """
        Get the full path for a report item.

        Args:
            item_text: Text of the list item

        Returns:
            Full path to the report file or None if not found
        """
        return self._report_paths.get(item_text)

    def get_search_widget(self) -> QWidget:
        """
        Get a widget containing the search functionality.

        Returns:
            Widget with search box properly laid out
        """
        search_widget = QWidget()
        layout = QHBoxLayout(search_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_box)
        return search_widget

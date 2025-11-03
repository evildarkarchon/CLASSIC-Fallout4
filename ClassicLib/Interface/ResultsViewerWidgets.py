"""
Custom list widget for managing and displaying scan reports with advanced
features.

This module provides functionality to display, sort, and filter scan reports
using a custom list widget. It also includes utilities for styling and
extracting metadata such as timestamps and statuses from report files.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

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


class ReportListWidget(QListWidget):
    """
    A custom QListWidget subclass for managing and displaying a list of crash
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
        """
        Initializes an instance of the class.

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
        """
        Initializes and configures a search box for filtering reports.

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
        """
        Sets up the initial styling for the widget, including configuring the font size
        and minimum width of the widget for better readability and usability.

        Args:
            self: An instance of the object calling the method.

        Returns:
            None
        """
        # Set font for better readability
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

        # Set minimum size
        self.setMinimumWidth(250)

    def populate_reports(self, reports: list[Path]) -> None:
        """
        Populates the report list with given report file paths.

        This method clears any existing items in the list and refreshes it with new
        items based on the provided list of file paths. It also selects the first item
        in the list if the list is not empty.

        Args:
            reports (list[Path]): A list of Path objects representing report file
                paths to populate the list with.
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
        Creates a QListWidgetItem based on the provided report file path. Extracts metadata
        such as timestamp, status, and file size from the file to enhance the item's
        properties, including tooltip and display text. The status of the report is used
        to apply appropriate styling to the item.

        Args:
            report_path (Path): The path to the report file.

        Returns:
            QListWidgetItem: The created list widget item with metadata and applied styling.
        """
        # Extract information from filename
        filename = report_path.stem  # Remove -AUTOSCAN suffix

        # Parse timestamp from filename if possible
        timestamp_str = self._extract_timestamp(filename)

        # Determine report status
        status = self._determine_report_status(report_path)

        # Create item with display text
        # display_text = filename.replace("-AUTOSCAN", "") # looks to be unused.
        if timestamp_str:
            display_text = f"{timestamp_str}\n{report_path.name}"
        else:
            display_text = report_path.name

        item = QListWidgetItem(display_text)

        # Set tooltip with full path
        item.setToolTip(str(report_path))

        # Apply status-based styling
        self._apply_status_styling(item, status)

        # Store metadata
        item.setData(Qt.ItemDataRole.UserRole, {
            "path": report_path,
            "status": status,
            "timestamp": timestamp_str,
            "size": report_path.stat().st_size
        })

        return item

    @staticmethod
    def _extract_timestamp(filename: str) -> str | None:
        """
        Extracts a timestamp from the given filename if it follows the specific pattern
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
                dt = datetime(int(year), int(month), int(day),
                            int(hour), int(minute), int(second))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        # Fallback to file modification time
        return None

    @staticmethod
    def _determine_report_status(report_path: Path) -> str:
        """
        Determines the status of a report based on its content.

        The method reads the content of a report file and determines its status by
        checking for specific indicators within the text. The possible statuses
        returned are:
        - "incomplete" if the content contains "INCOMPLETE"
        - "unsolved" if the content contains "UNSOLVED" or "could not be determined"
        - "solved" if the content contains "SOLVED" or "RECOMMENDATIONS"
        - "unknown" if no matching indicators are found or an error occurs while
          reading the file.

        Args:
            report_path (Path): The path to the report file whose status needs to be
                determined.

        Returns:
            str: A string representing the status of the report ("incomplete",
                "unsolved", "solved", or "unknown").
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
        Applies specific styling to a QListWidgetItem based on its status. Each status is
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
            # Default styling
            pass

    def _filter_reports(self, text: str) -> None:
        """
        Filters the reports displayed within the current context based on the provided
        text. Items that do not match the criteria will be hidden.

        Args:
            text (str): The text used for filtering items. Matching is case-insensitive
                and checks against both the item's text and tooltip.
        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                # Check if search text is in item text or tooltip
                matches = (text.lower() in item.text().lower() or
                          text.lower() in item.toolTip().lower())
                item.setHidden(not matches)

    @staticmethod
    def get_report_path(item: QListWidgetItem) -> Path | None:
        """
        Gets the report path stored in the metadata of the given QListWidgetItem.

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
            return data.get("path")
        return None

    def get_search_widget(self) -> QWidget:
        """
        Creates and configures a search widget with a label and search box.

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


class MarkdownViewer(QTextBrowser):
    """
    Enhanced text browser for displaying markdown-formatted reports.

    Provides markdown rendering, zoom controls, and custom styling.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initializes a custom QTextBrowser with pre-configured properties and functionality.

        This class is designed to provide a specialized QTextBrowser component with
        support for external links, readonly mode, rich text (Markdown) content,
        and custom styling. Additionally, it initializes with a default zoom level.

        Args:
            parent (QWidget | None): The parent widget of this QTextBrowser. Defaults to None.
        """
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
        """
        Applies custom styling for markdown rendering by setting a default stylesheet. The stylesheet
        specifies aesthetics for various HTML elements such as body, headers, code, lists, tables,
        and various text formatting classes (e.g., .error, .warning).

        Raises:
            None

        Returns:
            None
        """
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
            margin-bottom: 12px;
        }
        h2 {
            color: #81C784;
            border-bottom: 1px solid #81C784;
            padding-bottom: 3px;
            margin-top: 18px;
            margin-bottom: 10px;
        }
        h3 {
            color: #A5D6A7;
            margin-top: 15px;
            margin-bottom: 8px;
        }
        h4, h5, h6 {
            margin-top: 12px;
            margin-bottom: 6px;
        }
        code {
            background-color: #1e1e1e;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Courier New', monospace;
            color: #ce9178;
        }
        p {
            margin-top: 6px;
            margin-bottom: 8px;
        }
        pre {
            background-color: #1e1e1e;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            margin-top: 8px;
            margin-bottom: 12px;
        }
        blockquote {
            border-left: 4px solid #4CAF50;
            padding-left: 10px;
            color: #b0b0b0;
            font-style: italic;
            margin-top: 8px;
            margin-bottom: 8px;
        }
        ul, ol {
            padding-left: 20px;
            margin-top: 6px;
            margin-bottom: 12px;
        }
        li {
            margin: 5px 0;
            line-height: 1.6;
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
        Processes a markdown string, converts it to HTML for improved CSS support,
        and displays the formatted HTML content. The method ensures the content
        is rendered from the beginning by resetting the cursor position.

        Args:
            markdown (str): The markdown string to be processed and displayed.

        Returns:
            None
        """
        # Process markdown for better display (converts **bold** to <b>bold</b>)
        # Qt's markdown parser will preserve the HTML tags we embed
        processed = self._process_markdown(markdown)

        # Convert markdown to HTML using Qt's converter for markdown features
        # (headers, code blocks, lists, etc.) while preserving our HTML tags
        html = self._markdown_to_html(processed)

        # Use HTML rendering instead of markdown for better CSS support
        self.setHtml(html)

        # Scroll to top
        self.moveCursor(QTextCursor.MoveOperation.Start)

    @staticmethod
    def _markdown_to_html(markdown: str) -> str:
        """
        Converts a given markdown string to an HTML string with additional formatting for
        better visual separation. This function uses a QTextDocument for conversion and
        then applies custom styling through regex substitutions to enhance readability.

        Args:
            markdown (str): A string containing markdown content to convert.

        Returns:
            str: The converted and styled HTML string.
        """
        from PySide6.QtGui import QTextDocument

        # Create a temporary document to convert markdown to HTML
        temp_doc = QTextDocument()
        temp_doc.setMarkdown(markdown)
        html = temp_doc.toHtml()

        # Add extra spacing to section headings in the HTML
        import re

        # Add margin-top to section headings that come after content
        # This ensures visual separation between sections
        html = re.sub(
            r'(<h[123][^>]*>)',
            r'<div style="margin-top: 20px;"></div>\1',
            html
        )

        # Add spacing after lists
        html = re.sub(
            r'(</ul>|</ol>)',
            r'\1<div style="margin-bottom: 12px;"></div>',
            html
        )

        # Add spacing after code blocks
        html = re.sub(
            r'(</pre>)',
            r'\1<div style="margin-bottom: 12px;"></div>',
            html
        )

        return html

    @staticmethod
    def _process_markdown(markdown: str) -> str:
        """
        Processes a given markdown string to enhance its readability and formatting
        for display in QTextBrowser, ensuring preservation of line breaks,
        wrapping multiline sections in code blocks, and highlighting messages such
        as errors, warnings, and success messages.

        Args:
            markdown (str): The markdown string to be processed.

        Returns:
            str: A processed markdown string with enhanced formatting.
        """
        # For better line break preservation, wrap content sections in code blocks
        # This ensures QTextBrowser preserves formatting
        processed = markdown

        # Find [!] FOUND sections and wrap multiline content in code blocks
        import re

        def wrap_multiline_content(match):
            header = match.group(1)
            content = match.group(2).rstrip()  # Remove trailing whitespace/newlines
            # Wrap the content in a code block to preserve formatting
            return f"{header}\n```\n{content}\n```\n"

        # Match [!] FOUND : [XX] followed by multiline content that starts with spaces
        # Stop at the first completely empty line or non-indented line
        # noinspection RegExpRedundantEscape
        processed = re.sub(
            r'(\[!\]\s*FOUND\s*:\s*\[[^\]]+\][^\n]*)\n((?:[ \t]+[^\n]+\n)+?)(?=\n|\Z)',
            wrap_multiline_content,
            processed
        )

        # Note: Spacing is now handled by HTML rendering in _markdown_to_html()
        # No need for aggressive newline injection

        # Highlight error messages
        # noinspection RegExpRedundantEscape
        processed = re.sub(
            r'\[!?\s*ERROR\s*\]([^\n]*)',
            r'<span class="error">[ERROR]\1</span>',
            processed,
            flags=re.IGNORECASE
        )

        # Highlight warnings
        # noinspection RegExpRedundantEscape
        processed = re.sub(
            r'\[!?\s*WARNING\s*\]([^\n]*)',
            r'<span class="warning">[WARNING]\1</span>',
            processed,
            flags=re.IGNORECASE
        )

        # Highlight success messages
        # noinspection RegExpRedundantEscape
        processed = re.sub(
            r'\[!?\s*SOLVED\s*\]([^\n]*)',
            r'<span class="success">[SOLVED]\1</span>',
            processed,
            flags=re.IGNORECASE
        )

        # Convert markdown bold syntax to HTML bold tags
        # This ensures proper rendering in Qt viewer without relying on Qt's markdown parser
        processed = re.sub(
            r'\*\*([^*]+)\*\*',
            r'<b>\1</b>',
            processed
        )

        return processed

    def zoom_in(self) -> None:
        """
        Increases the zoom level by 10 units, up to a maximum of 200, and applies
        the updated zoom level.

        Raises:
            None
        """
        self._zoom_level = min(200, self._zoom_level + 10)
        self._apply_zoom()

    def zoom_out(self) -> None:
        """
        Reduces the current zoom level of the application by decrementing it in fixed steps, with a lower limit.

        The `zoom_out` method decreases the zoom level of the application by a predefined value,
        but ensures the zoom level does not fall below a specified minimum threshold. It also
        applies the updated zoom level using an internal mechanism.

        Raises:
            None

        Returns:
            None
        """
        self._zoom_level = max(50, self._zoom_level - 10)
        self._apply_zoom()

    def reset_zoom(self) -> None:
        """
        Resets the zoom level to its default value.

        This method sets the current zoom level to 100%, ensuring the default state of
        zoom is restored, and applies the changes immediately.

        """
        self._zoom_level = 100
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        """
        Adjust the font size based on a zoom level.

        This method modifies the font size by applying a scale factor derived
        from the current zoom level. The zoom level determines how much to
        increase or decrease the font size, with a minimum font size enforced.

        This function has no return value but updates the font settings
        of the object it is called on.

        Raises:
            None
        """
        # Apply zoom by scaling the font size
        font = self.font()
        base_size = 14  # Base font size from CSS
        new_size = int(base_size * (self._zoom_level / 100.0))
        font.setPointSize(max(8, new_size))  # Minimum size of 8pt
        self.setFont(font)

    def get_zoom_level(self) -> int:
        """
        Retrieves the current zoom level of the object.

        This method accesses the internal zoom level of the object and returns its
        value as an integer. The zoom level represents the current scale or magnification
        applied to the object.

        Returns:
            int: The current zoom level of the object.
        """
        return self._zoom_level


class ReportMetadataWidget(QGroupBox):
    """
    Widget for displaying report metadata.

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
        """
        Creates a widget displaying metadata about a report including date, size, and issues.

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
        """
        Applies specific styling to the graphical components using Qt's stylesheet syntax.

        This method configures the appearance of QGroupBox and QLabel elements by setting
        properties such as font weight, borders, margin, and padding. The styling is
        applied through Qt's setStyleSheet function utilizing cascading style sheets (CSS).

        Returns:
            None: This method does not return any value.
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
        Updates metadata display such as date, file size, and issue count for a given report.

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
        """
        Count various issue indicators in a given content.

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
        errors = len(re.findall(r'\[!?\s*ERROR\s*\]', content, re.IGNORECASE))
        warnings = len(re.findall(r'\[!?\s*WARNING\s*\]', content, re.IGNORECASE))

        # Look for issue lists
        issues = len(re.findall(r'^[-*]\s+.+', content, re.MULTILINE))

        if errors > 0:
            return f"{errors} errors, {warnings} warnings"
        if warnings > 0:
            return f"{warnings} warnings"
        if issues > 0:
            return f"{issues} items"
        return "None found"

    def clear(self) -> None:
        """
        Clears the content of the labels displaying date, size, and issues.

        This method resets the text content of `date_label`, `size_label`, and
        `issues_label` to indicate that the values are not available.

        Returns:
            None
        """
        self.date_label.setText("Date: N/A")
        self.size_label.setText("Size: N/A")
        self.issues_label.setText("Issues: N/A")

"""Custom list widget for managing and displaying scan reports with advanced
features.

This module provides functionality to display, sort, and filter scan reports
using a custom list widget. It also includes utilities for styling and
extracting metadata such as timestamps and statuses from report files.
"""

from __future__ import annotations

import html
import re
import textwrap
from datetime import datetime
from pathlib import Path  # noqa: TC003

import markdown2
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
        """Create a QListWidgetItem based on the provided report file path. Extracts metadata
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
                pass

        # Fallback to file modification time
        return None

    @staticmethod
    def _determine_report_status(report_path: Path) -> str:
        """Determine the status of a report based on its content.

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

        except Exception as e:  # noqa: BLE001
            logger.debug(f"Could not determine status for {report_path.name}: {e}")
        else:
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
            # Default styling
            pass

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
            return data.get("path")
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


class MarkdownViewer(QTextBrowser):
    """Enhanced text browser for displaying markdown-formatted reports.

    Provides markdown rendering via markdown2, zoom controls, and custom styling.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize a custom QTextBrowser with pre-configured properties and functionality."""
        super().__init__(parent)

        # Configure viewer properties
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)

        # Initialize zoom level
        self._zoom_level = 100

    def setMarkdown(self, markdown: str) -> None:
        """Process a markdown string, converts it to HTML using markdown2,
        injects custom styling, and displays it.

        Args:
            markdown (str): The markdown string to be processed and displayed.

        """
        # 1. Pre-process special blocks to HTML
        processed_text = self._preprocess_markdown(markdown)

        # 2. Convert to HTML using markdown2
        # "tables" for table support
        # "break-on-newline" to respect line breaks in the log
        # "fenced-code-blocks" for standard code blocks
        html_content = markdown2.markdown(processed_text, extras=["tables", "break-on-newline", "fenced-code-blocks"])

        # 3. Construct full HTML document with CSS
        full_doc = self._wrap_in_html_template(html_content)

        # 4. Set HTML
        self.setHtml(full_doc)

        # Scroll to top
        self.moveCursor(QTextCursor.MoveOperation.Start)

    def _preprocess_markdown(self, text: str) -> str:  # noqa: PLR6301
        """Pre-processes the raw markdown text to identify and wrap specific
        CLASSIC report structures (Suspects, Found Mods, Errors) in HTML.
        """

        # 1. Suspect Found Box
        def suspect_replacer(match: re.Match) -> str:
            full_line = match.group(0)
            # Remove ** and - markers
            clean_line = full_line.replace("**", "").replace("- ", "").strip()

            if "SUSPECT FOUND!" in clean_line:
                parts = clean_line.split("SUSPECT FOUND!")
                title = html.escape(parts[0].strip(" ."))
                info = html.escape("SUSPECT FOUND!" + parts[1])

                return f'<div class="suspect-box"><div class="suspect-title">{title}</div><div class="suspect-info">{info}</div></div>'
            return full_line

        text = re.sub(r"-\s*\*\*Checking for.*SUSPECT FOUND!.*?\*\*", suspect_replacer, text)

        # 2. Found Mod Cards
        # Regex: Match Header, then content until separator -----
        def found_replacer(match: re.Match) -> str:
            header = match.group(1).strip()
            content = match.group(2)  # Keep raw content with whitespace for dedent

            clean_header = html.escape(header.replace("**", "").strip())

            # Dedent content so markdown2 doesn't treat it as a code block
            # But first ensure we don't lose the structure if it's a list
            dedented_content = textwrap.dedent(content)

            return (
                f'<div class="found-box">'
                f'<div class="found-header">{clean_header}</div>'
                f"{dedented_content}"  # markdown2 will parse this
                f"</div>"
            )

        pattern = r"(\*\*\[!\]\s*FOUND\s*:\s*\[[^\]]+\][^\n]*\*\*)([\s\S]*?)(?=\n[ \t]*-{5,})"
        text = re.sub(pattern, found_replacer, text)

        # 3. Status Boxes
        text = re.sub(r"(\*\*Main Error:.*)", lambda m: f'<div class="error-box">{html.escape(m.group(1))}</div>', text)
        text = re.sub(r"(\*\*Detected Buffout 4 Version:.*)", lambda m: f'<div class="info-box">{html.escape(m.group(1))}</div>', text)
        text = re.sub(r"(✅.*)", lambda m: f'<div class="success-text">{html.escape(m.group(1))}</div>', text)

        # 4. Bold conversion (backup)
        return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)

    def _wrap_in_html_template(self, content: str) -> str:
        """Wrap the HTML content in a full document structure with embedded CSS."""
        # Base font size scaled by zoom level
        base_size = 16
        scaled_size = int(base_size * (self._zoom_level / 100.0))

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI Variable', Roboto, Helvetica, Arial, sans-serif;
                    font-size: {scaled_size}px;
                    line-height: 1.6;
                    color: #e0e0e0;
                    background-color: #1e1e1e;
                    margin: 0;
                    padding: 20px;
                }}
                
                /* Headers */
                h1 {{ 
                    color: #4EC9B0; 
                    font-size: {int(scaled_size * 1.6)}px;
                    border-bottom: 2px solid #4EC9B0; 
                    margin-top: 25px;
                    margin-bottom: 15px;
                    padding-bottom: 5px;
                }}
                h2 {{ 
                    color: #4EC9B0; 
                    font-size: {int(scaled_size * 1.3)}px;
                    border-bottom: 1px solid #3E3E42; 
                    margin-top: 20px;
                    margin-bottom: 10px;
                    padding-bottom: 5px;
                }}
                h3 {{ 
                    color: #9CDCFE; 
                    font-size: {int(scaled_size * 1.1)}px;
                    font-weight: bold;
                    margin-top: 15px;
                    margin-bottom: 8px;
                }}
                
                /* Links */
                a {{ color: #3794FF; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                
                /* Code/Pre */
                pre {{
                    background-color: #252526;
                    border: 1px solid #3E3E42;
                    padding: 10px;
                    border-radius: 5px;
                    color: #d4d4d4;
                    font-family: Consolas, 'Courier New', monospace;
                    white-space: pre-wrap;
                }}
                code {{
                    background-color: #2d2d2d;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: Consolas, 'Courier New', monospace;
                    color: #ce9178;
                }}

                /* Tables */
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }}
                th, td {{
                    border: 1px solid #3E3E42;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #252526;
                    color: #4EC9B0;
                }}
                tr:nth-child(even) {{
                    background-color: #252526;
                }}

                /* Custom Components */
                .suspect-box {{
                    background-color: #3c1414;
                    border-left: 4px solid #f44336;
                    padding: 10px;
                    margin: 10px 0;
                }}
                .suspect-title {{ 
                    color: #f44336; 
                    font-weight: bold; 
                    font-size: {scaled_size}px;
                }}
                .suspect-info {{
                    color: #e0e0e0;
                    margin-top: 5px;
                }}

                .found-box {{
                    background-color: #252526;
                    border: 1px solid #3E3E42;
                    border-radius: 5px;
                    padding: 12px;
                    margin: 15px 0;
                }}
                .found-header {{
                    color: #DCDCAA;
                    font-weight: bold;
                    font-size: {int(scaled_size * 1.1)}px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #3E3E42;
                    margin-bottom: 8px;
                }}
                
                .error-box {{
                    background-color: #3c1414;
                    border: 1px solid #f44336;
                    padding: 10px;
                    border-radius: 4px;
                    color: #f44336;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .info-box {{
                    background-color: #1e2e3e;
                    border: 1px solid #3794ff;
                    padding: 10px;
                    border-radius: 4px;
                    color: #3794ff;
                    margin: 10px 0;
                }}
                .success-text {{
                    color: #4EC9B0;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """

    def zoom_in(self) -> None:
        """Increases the zoom level."""
        self._zoom_level = min(200, self._zoom_level + 10)
        self._refresh_display()

    def zoom_out(self) -> None:
        """Decreases the zoom level."""
        self._zoom_level = max(50, self._zoom_level - 10)
        self._refresh_display()

    def reset_zoom(self) -> None:
        """Reset zoom to 100%."""
        self._zoom_level = 100
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the display by re-setting the HTML content.
        This forces the CSS to re-evaluate with the new font size.
        """
        # We can't easily re-process the original markdown here without storing it.
        # However, QTextBrowser has a zoomIn/zoomOut method natively,
        # but we implemented custom CSS font sizing.
        # Ideally we should store the last markdown content.

        # Actually, standard zoom might work if we just rely on it.
        # But our CSS uses fixed pixels.
        # Let's use the native `zoomIn` / `zoomOut` from QTextEdit instead?
        # No, the previous implementation used custom font scaling.

        # To support this properly, we should store the `_last_html_content` (without the template)
        # and re-wrap it.

    # Correcting the above thought:
    # We need to store the processed HTML content to allow efficient re-rendering on zoom.
    # Let's update `setMarkdown` to store `self._last_processed_html`.

    def get_zoom_level(self) -> int:
        """Return the current zoom level."""
        return self._zoom_level


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

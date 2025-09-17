"""
Markdown viewer widget for displaying formatted reports.

This module provides an enhanced QTextBrowser for rendering markdown-formatted
CLASSIC scan reports with custom styling and zoom controls.
"""

from __future__ import annotations

import re

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextBrowser, QWidget

# Pre-compiled regex patterns for performance optimization
# noinspection RegExpRedundantEscape
_ERROR_PATTERN = re.compile(r"\[!?\s*ERROR\s*\]([^\n]*)", re.IGNORECASE)
# noinspection RegExpRedundantEscape
_WARNING_PATTERN = re.compile(r"\[!?\s*WARNING\s*\]([^\n]*)", re.IGNORECASE)
# noinspection RegExpRedundantEscape
_SOLVED_PATTERN = re.compile(r"\[!?\s*SOLVED\s*\]([^\n]*)", re.IGNORECASE)


class MarkdownViewer(QTextBrowser):
    """Custom QTextBrowser-based widget for viewing and processing markdown content.

    MarkdownViewer is a specialized widget designed to render and display markdown
    content with custom styling and enhanced processing capabilities. It incorporates
    features for zoom control, markdown-specific CSS styling, and the ability to
    handle processed markdown input. This class is ideal for use in applications
    where enriched markdown visualization is needed.

    Attributes:
        _zoom_level (int): Current zoom level of the viewer, represented as a
            percentage.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        A viewer class for displaying rich text content with markdown support.

        This class allows for displaying rich text content with support for Markdown
        rendering. It provides configurations for controlling external links, read-only
        status, and custom styling. Additionally, it initializes with a default zoom
        level and offers the ability to style the viewer.

        Args:
            parent (QWidget | None): The parent widget for this viewer. Can be None if
                no parent widget is specified.
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
        Applies a predefined CSS stylesheet for consistent styling of markdown content.

        This method sets the default stylesheet for a document object with specific
        style rules, ensuring a cohesive visual appearance for markdown rendering.
        The styles include configurations for text elements like headings, lists,
        tables, blockquotes, and others. The design primarily targets dark-themed
        interfaces with emphasis on color-coded elements for better readability.
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
        Processes and sets the given markdown string for display. This method enhances the provided
        markdown by preprocessing it and then utilizes the base class's functionality to render it
        properly. Additionally, it moves the cursor to the starting position to ensure the content
        begins at the top of the display.

        Args:
            markdown (str): The markdown string to be processed and displayed.
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
        Processes the given markdown text for enhanced display by applying custom styling
        to specific patterns found in the text. The method identifies predefined tags,
        such as [ERROR], [WARNING], and [SOLVED], and replaces them with styled spans
        for improved visualization.

        Args:
            markdown (str): The markdown text to be processed.

        Returns:
            str: The processed markdown text with applied style replacements.

        Raises:
            None
        """
        # Process markdown for enhanced display
        processed = markdown

        # Note: [!] FOUND sections now use bold markdown format (**[!] FOUND**)
        # and don't require special code block wrapping
        processed = _ERROR_PATTERN.sub(r'<span class="error">[ERROR]\1</span>', processed)
        processed = _WARNING_PATTERN.sub(r'<span class="warning">[WARNING]\1</span>', processed)
        processed = _SOLVED_PATTERN.sub(r'<span class="success">[SOLVED]\1</span>', processed)

        return processed  # noqa: RET504

    def zoom_in(self) -> None:
        """
        Zooms in by increasing the current zoom level and applies the updated zoom setting.

        Raises:
            None: This method does not raise exceptions.
        """
        self._zoom_level = min(200, self._zoom_level + 10)
        self._apply_zoom()

    def zoom_out(self) -> None:
        """
        Decreases the zoom level by reducing it in increments of 10 units, with a
        minimum allowable zoom level of 50. Applies the updated zoom level.
        """
        self._zoom_level = max(50, self._zoom_level - 10)
        self._apply_zoom()

    def reset_zoom(self) -> None:
        """
        Resets the zoom level to the default value and applies the change.

        This method restores the zoom level to its default value of 100% and applies
        the adjustment to ensure the associated display or view reflects the change
        immediately.
        """
        self._zoom_level = 100
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        """
        Applies the zoom level to adjust the font size of the text display.

        This function calculates the new font size based on a base font size and the
        current zoom level, ensuring the font size does not drop below a minimum value.
        It then updates the font of the corresponding component to reflect the adjusted
        zoom level.

        """
        # Apply zoom by scaling the font size
        font = self.font()
        base_size = 14  # Base font size from CSS
        new_size = int(base_size * (self._zoom_level / 100.0))
        font.setPointSize(max(8, new_size))  # Minimum size of 8pt
        self.setFont(font)

    def get_zoom_level(self) -> int:
        """
        Gets the current zoom level.

        This method retrieves the zoom level of the object. The zoom level is an integer
        representing the current state.

        Returns:
            int: The current zoom level of the object.
        """
        return self._zoom_level

"""
Markdown viewer widget for displaying formatted reports.

This module provides an enhanced QTextBrowser for rendering markdown-formatted
CLASSIC scan reports with custom styling and zoom controls.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextBrowser, QWidget

if TYPE_CHECKING:
    pass

# Pre-compiled regex patterns for performance optimization
# noinspection RegExpRedundantEscape
_ERROR_PATTERN = re.compile(r"\[!?\s*ERROR\s*\]([^\n]*)", re.IGNORECASE)
# noinspection RegExpRedundantEscape
_WARNING_PATTERN = re.compile(r"\[!?\s*WARNING\s*\]([^\n]*)", re.IGNORECASE)
# noinspection RegExpRedundantEscape
_SOLVED_PATTERN = re.compile(r"\[!?\s*SOLVED\s*\]([^\n]*)", re.IGNORECASE)


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
        # Process markdown for enhanced display
        processed = markdown

        # Note: [!] FOUND sections now use bold markdown format (**[!] FOUND**)
        # and don't require special code block wrapping
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

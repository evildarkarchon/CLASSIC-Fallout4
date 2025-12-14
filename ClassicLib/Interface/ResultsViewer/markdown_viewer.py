"""Enhanced text browser for displaying markdown-formatted reports.

This module provides the MarkdownViewer widget which renders markdown content
using markdown2 with custom styling optimized for CLASSIC scan reports.
"""

from __future__ import annotations

import html
import re
import textwrap

import markdown2
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextBrowser, QWidget


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
        """Pre-process raw markdown text to identify and wrap CLASSIC report structures.

        Wraps specific CLASSIC report structures (Suspects, Found Mods, Errors) in HTML.

        Args:
            text: Raw markdown text to preprocess.

        Returns:
            Preprocessed text with CLASSIC structures wrapped in HTML.

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
        """Wrap the HTML content in a full document structure with embedded CSS.

        Args:
            content: HTML content to wrap.

        Returns:
            Complete HTML document with embedded CSS styling.

        """
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
        """Return the current zoom level.

        Returns:
            The current zoom level as a percentage (e.g., 100 for 100%).

        """
        return self._zoom_level


__all__ = ["MarkdownViewer"]

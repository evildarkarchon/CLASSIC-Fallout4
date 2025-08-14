"""Output viewer widget for TUI."""

import threading
from collections import deque
from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Input, RichLog, Static

# Pre-compiled format strings for better performance
_TIMESTAMP_FORMAT = "[dim]{timestamp}[/dim] {text}"
_STYLE_FORMATS = {
    "error": "[red]{text}[/red]",
    "warning": "[yellow]{text}[/yellow]",
    "success": "[green]{text}[/green]",
    "info": "[blue]{text}[/blue]",
}


class OutputViewer(Static):
    """Scrollable log output display with search functionality."""

    BINDINGS = [
        Binding("ctrl+f", "start_search", "Find", show=False),
        Binding("f3", "find_next", "Find Next", show=False),
        Binding("shift+f3", "find_previous", "Find Previous", show=False),
        Binding("page_up", "scroll_up_page", "Page Up", show=False),
        Binding("page_down", "scroll_down_page", "Page Down", show=False),
        Binding("home", "scroll_to_top", "Home", show=False),
        Binding("end", "scroll_to_bottom", "End", show=False),
        Binding("ctrl+a", "select_all", "Select All", show=False),
        Binding("ctrl+c", "copy_selection", "Copy", show=False),
    ]

    DEFAULT_CSS = """
    OutputViewer {
        height: 100%;
        layout: vertical;
        border: none;
    }
    
    OutputViewer:focus {
        border: solid $accent;
    }
    
    .output-container {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }
    
    .output-controls {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    
    .search-container {
        dock: top;
        height: 3;
        padding: 0 1;
        background: $panel;
        display: none;
    }
    
    .search-container.visible {
        display: block;
    }
    
    .search-input {
        width: 100%;
    }
    
    .search-results {
        margin-left: 1;
        color: $text-muted;
    }
    """

    show_search = reactive(False)
    search_query = reactive("")
    search_index = reactive(0)
    search_matches: list[int] = []

    def __init__(self, max_lines: int = 10000, auto_scroll: bool = True, show_timestamps: bool = True, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.max_lines = max_lines
        self.auto_scroll = auto_scroll
        self.show_timestamps = show_timestamps
        self._log_widget: RichLog | None = None
        self._output_buffer: deque[str] = deque(maxlen=max_lines)
        self._buffer_lock = threading.Lock()
        self.can_focus = True  # Make the widget focusable

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        # Search bar (hidden by default)
        with Container(classes="search-container", id="search-container"):
            with Horizontal():
                yield Input(placeholder="Search...", id="search-input", classes="search-input")
                yield Static("", id="search-results", classes="search-results")

        with VerticalScroll(classes="output-container"):
            self._log_widget = RichLog(highlight=True, markup=True, wrap=True, max_lines=self.max_lines, classes="output-log")
            yield self._log_widget

        with Horizontal(classes="output-controls"):
            yield Button("Clear", id="clear-output", classes="control-button")
            yield Button("Auto-scroll: ON", id="toggle-scroll", classes="control-button")

    def append_output(self, text: str, style: str | None = None) -> None:
        """Append text to the output viewer.

        Args:
            text: Text to append
            style: Optional style (e.g., "error", "warning", "success")
        """
        # Format the message efficiently
        formatted_text = (
            _TIMESTAMP_FORMAT.format(timestamp=datetime.now().strftime("%H:%M:%S"), text=text) if self.show_timestamps else text
        )

        # Apply style formatting using pre-compiled format strings
        if style and style in _STYLE_FORMATS:
            formatted_text = _STYLE_FORMATS[style].format(text=formatted_text)

        # Add to buffer with minimal lock time
        with self._buffer_lock:
            self._output_buffer.append(text)

        # Write to log widget
        if self._log_widget:
            self._log_widget.write(formatted_text)

            # Auto-scroll if enabled
            if self.auto_scroll:
                self._log_widget.scroll_end(animate=False)

    def clear(self) -> None:
        """Clear the output viewer."""
        with self._buffer_lock:
            self._output_buffer.clear()
        if self._log_widget:
            self._log_widget.clear()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "clear-output":
            self.clear()
        elif event.button.id == "toggle-scroll":
            self.toggle_auto_scroll()

    def search(self, query: str) -> int:
        """Search for text in the output.

        Args:
            query: Text to search for

        Returns:
            Number of matches found
        """
        if not query:
            return 0

        query_lower = query.lower()

        # Use deque.copy() for better performance and minimal lock time
        with self._buffer_lock:
            buffer_copy = self._output_buffer.copy()

        # Use generator expression for memory efficiency
        matches = sum(1 for line in buffer_copy if query_lower in line.lower())

        if matches > 0:
            self.append_output(f"Found {matches} matches for '{query}'", style="info")
        else:
            self.append_output(f"No matches found for '{query}'", style="warning")

        return matches

    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scrolling."""
        self.auto_scroll = enabled

    def set_max_lines(self, max_lines: int) -> None:
        """Set maximum number of lines to keep."""
        self.max_lines = max_lines
        if self._log_widget:
            self._log_widget.max_lines = max_lines

    def start_search(self) -> None:
        """Start search mode."""
        self.show_search = True
        search_container = self.query_one("#search-container", Container)
        search_container.add_class("visible")
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def stop_search(self) -> None:
        """Stop search mode."""
        self.show_search = False
        search_container = self.query_one("#search-container", Container)
        search_container.remove_class("visible")
        self.search_query = ""
        self.search_matches.clear()
        self.search_index = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_query = event.value
            self._perform_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "search-input":
            if self.search_matches:
                # Move to next match
                self.search_index = (self.search_index + 1) % len(self.search_matches)
                self._highlight_match()

    def _perform_search(self) -> None:
        """Perform the search and update results."""
        if not self.search_query:
            self.search_matches.clear()
            results_label = self.query_one("#search-results", Static)
            results_label.update("")
            return

        self.search_matches.clear()
        query_lower = self.search_query.lower()

        # Use deque.copy() for better performance and minimal lock time
        with self._buffer_lock:
            buffer_copy = self._output_buffer.copy()

        # Use list comprehension for better performance
        self.search_matches = [i for i, line in enumerate(buffer_copy) if query_lower in line.lower()]

        # Update results display
        results_label = self.query_one("#search-results", Static)
        if self.search_matches:
            results_label.update(f"Found {len(self.search_matches)} matches")
            self.search_index = 0
            self._highlight_match()
        else:
            results_label.update("No matches found")

    def _highlight_match(self) -> None:
        """Highlight the current search match."""
        if not self.search_matches or self.search_index >= len(self.search_matches):
            return

        # Scroll to the match line
        line_index = self.search_matches[self.search_index]
        if self._log_widget:
            # Approximate scroll position
            self._log_widget.scroll_to(y=line_index, animate=True)

    def toggle_auto_scroll(self) -> None:
        """Toggle auto-scrolling on/off."""
        self.auto_scroll = not self.auto_scroll

        # Update button text if it exists
        try:
            btn = self.query_one("#toggle-scroll", Button)
            btn.label = f"Auto-scroll: {'ON' if self.auto_scroll else 'OFF'}"
        except:
            # Button not yet composed or doesn't exist
            pass

    async def write(self, text: str, style: str | None = None) -> None:
        """Async write method for compatibility."""
        self.append_output(text, style)

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        if event.key == "escape":
            if self.show_search:
                self.stop_search()
                event.stop()
            else:
                # Blur the widget
                self.blur()
                event.stop()
        elif event.key == "up":
            # Scroll up one line
            if self._log_widget:
                self._log_widget.scroll_up(animate=False)
                event.stop()
        elif event.key == "down":
            # Scroll down one line
            if self._log_widget:
                self._log_widget.scroll_down(animate=False)
                event.stop()

    def action_start_search(self) -> None:
        """Start search mode (Ctrl+F)."""
        self.start_search()

    def action_find_next(self) -> None:
        """Find next match (F3)."""
        if self.search_matches:
            self.search_index = (self.search_index + 1) % len(self.search_matches)
            self._highlight_match()

    def action_find_previous(self) -> None:
        """Find previous match (Shift+F3)."""
        if self.search_matches:
            self.search_index = (self.search_index - 1) % len(self.search_matches)
            self._highlight_match()

    def action_scroll_up_page(self) -> None:
        """Scroll up one page (Page Up)."""
        if self._log_widget:
            self._log_widget.scroll_page_up(animate=False)

    def action_scroll_down_page(self) -> None:
        """Scroll down one page (Page Down)."""
        if self._log_widget:
            self._log_widget.scroll_page_down(animate=False)

    def action_scroll_to_top(self) -> None:
        """Scroll to top (Home)."""
        if self._log_widget:
            self._log_widget.scroll_home(animate=False)

    def action_scroll_to_bottom(self) -> None:
        """Scroll to bottom (End)."""
        if self._log_widget:
            self._log_widget.scroll_end(animate=False)

    def action_select_all(self) -> None:
        """Select all text (Ctrl+A)."""
        # This would require implementing text selection in RichLog
        # For now, we'll just pass

    def action_copy_selection(self) -> None:
        """Copy selected text (Ctrl+C)."""
        # This would require implementing text selection and clipboard access
        # For now, we'll just pass

    def on_focus(self) -> None:
        """Handle focus event."""
        # Visual indication is handled by CSS

    def on_blur(self) -> None:
        """Handle blur event."""
        # Stop search if active when losing focus
        if self.show_search:
            self.stop_search()

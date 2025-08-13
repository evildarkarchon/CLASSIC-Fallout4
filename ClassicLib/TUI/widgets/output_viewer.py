"""Output viewer widget for TUI."""

from datetime import datetime
from typing import List, Optional
from textual.widgets import RichLog, Static, Input
from textual.containers import VerticalScroll, Horizontal, Container
from textual.app import ComposeResult
from textual.widgets import Button
from textual.reactive import reactive


class OutputViewer(Static):
    """Scrollable log output display with search functionality."""
    
    DEFAULT_CSS = """
    OutputViewer {
        height: 100%;
    }
    
    .output-container {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    .output-controls {
        dock: bottom;
        height: 3;
        align: center middle;
        margin-top: 1;
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
    search_matches: List[int] = []
    
    def __init__(
        self,
        max_lines: int = 10000,
        auto_scroll: bool = True,
        show_timestamps: bool = True,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.max_lines = max_lines
        self.auto_scroll = auto_scroll
        self.show_timestamps = show_timestamps
        self._log_widget: RichLog | None = None
        self._output_buffer: List[str] = []
    
    def compose(self) -> ComposeResult:
        """Compose the widget."""
        # Search bar (hidden by default)
        with Container(classes="search-container", id="search-container"):
            with Horizontal():
                yield Input(
                    placeholder="Search...",
                    id="search-input",
                    classes="search-input"
                )
                yield Static("", id="search-results", classes="search-results")
        
        with VerticalScroll(classes="output-container"):
            self._log_widget = RichLog(
                highlight=True,
                markup=True,
                wrap=True,
                max_lines=self.max_lines,
                classes="output-log"
            )
            yield self._log_widget
        
        with Horizontal(classes="output-controls"):
            yield Button("Clear", id="clear-output", classes="control-button")
            yield Button("Auto-scroll: ON", id="toggle-scroll", classes="control-button")
    
    def append_output(self, text: str, style: Optional[str] = None) -> None:
        """Append text to the output viewer.
        
        Args:
            text: Text to append
            style: Optional style (e.g., "error", "warning", "success")
        """
        # Format the message
        if self.show_timestamps:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_text = f"[dim]{timestamp}[/dim] {text}"
        else:
            formatted_text = text
        
        # Apply style formatting
        if style:
            if style == "error":
                formatted_text = f"[red]{formatted_text}[/red]"
            elif style == "warning":
                formatted_text = f"[yellow]{formatted_text}[/yellow]"
            elif style == "success":
                formatted_text = f"[green]{formatted_text}[/green]"
            elif style == "info":
                formatted_text = f"[blue]{formatted_text}[/blue]"
        
        # Add to buffer
        self._output_buffer.append(text)
        
        # Write to log widget
        if self._log_widget:
            self._log_widget.write(formatted_text)
            
            # Auto-scroll if enabled
            if self.auto_scroll:
                self._log_widget.scroll_end(animate=False)
    
    def clear(self) -> None:
        """Clear the output viewer."""
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
        
        matches = 0
        query_lower = query.lower()
        
        for line in self._output_buffer:
            if query_lower in line.lower():
                matches += 1
        
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
        
        for i, line in enumerate(self._output_buffer):
            if query_lower in line.lower():
                self.search_matches.append(i)
        
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
    
    async def write(self, text: str, style: Optional[str] = None) -> None:
        """Async write method for compatibility."""
        self.append_output(text, style)
    
    def on_key(self, event) -> None:
        """Handle keyboard events."""
        if event.key == "escape" and self.show_search:
            self.stop_search()
            event.stop()
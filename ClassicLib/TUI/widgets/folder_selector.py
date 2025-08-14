"""Folder selector widget for TUI."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Static


class FolderSelector(Static):
    """Custom folder path input with validation and browse button."""

    BINDINGS = [
        Binding("enter", "submit_path", "Submit Path", show=False),
        Binding("ctrl+b", "browse", "Browse", show=False),
        Binding("ctrl+v", "paste_path", "Paste Path", show=False),
        Binding("escape", "clear_or_blur", "Clear/Blur", show=False),
    ]

    DEFAULT_CSS = """
    FolderSelector {
        height: 3;
        layout: vertical;
        border: none;
    }
    
    FolderSelector:focus-within {
        border: solid $primary;
    }
    
    .folder-selector-container {
        height: 3;
        layout: horizontal;
    }
    
    .folder-input {
        width: 1fr;
        height: 3;
    }
    
    .browse-button {
        width: 10;
        height: 3;
        margin-left: 1;
    }
    
    .error-label {
        height: 1;
        color: $error;
    }
    
    .error-label.hidden {
        display: none;
    }
    """

    path = reactive("")
    valid = reactive(True)

    class PathChanged(Message):
        """Message sent when path changes."""

        def __init__(self, path: str, valid: bool) -> None:
            super().__init__()
            self.path = path
            self.valid = valid

    def __init__(self, placeholder: str = "", initial_path: str = "", validate_exists: bool = True, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.placeholder = placeholder
        self.initial_path = initial_path
        self.validate_exists = validate_exists
        self._input: Input | None = None
        self._error_label: Static | None = None

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        with Horizontal(classes="folder-selector-container"):
            self._input = Input(placeholder=self.placeholder, value=self.initial_path, classes="folder-input")
            yield self._input
            yield Button("Browse", id="browse-btn", classes="browse-button")

        self._error_label = Static("", classes="error-label hidden")
        yield self._error_label

    def on_mount(self) -> None:
        """Initialize on mount."""
        if self.initial_path:
            self.path = self.initial_path
            self._check_path_validity()

        # Make the widget focusable
        self.can_focus = True

    def watch_path(self, old_path: str, new_path: str) -> None:
        """React to path changes."""
        self._check_path_validity()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input == self._input:
            self.path = event.value
            self._check_path_validity()
            self.post_message(self.PathChanged(self.path, self.valid))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle browse button click."""
        if event.button.id == "browse-btn":
            self.action_browse()

    def _check_path_validity(self) -> None:
        """Validate the current path."""
        if not self.path:
            self.valid = True
            self._hide_error()
            return

        if self.validate_exists:
            path_obj = Path(self.path)
            if not path_obj.exists():
                self.valid = False
                self._show_error("Path does not exist")
            elif not path_obj.is_dir():
                self.valid = False
                self._show_error("Path is not a directory")
            else:
                self.valid = True
                self._hide_error()
        else:
            # Just check if it's a valid path format
            try:
                Path(self.path)
                self.valid = True
                self._hide_error()
            except (ValueError, OSError):
                self.valid = False
                self._show_error("Invalid path format")

    def _show_error(self, message: str) -> None:
        """Show error message."""
        if self._error_label:
            self._error_label.update(f"❌ {message}")
            self._error_label.remove_class("hidden")
            if self._input:
                self._input.add_class("error")

    def _hide_error(self) -> None:
        """Hide error message."""
        if self._error_label:
            self._error_label.update("")
            self._error_label.add_class("hidden")
            if self._input:
                self._input.remove_class("error")

    def get_path(self) -> str | None:
        """Get the current valid path."""
        return self.path if self.valid else None

    def set_path(self, path: str) -> None:
        """Set the path programmatically."""
        if self._input:
            self._input.value = path
            self.path = path
            self._check_path_validity()

    @property
    def value(self) -> str:
        """Get the current value (alias for path)."""
        return self.path

    @value.setter
    def value(self, val: str) -> None:
        """Set the current value (alias for path)."""
        self.set_path(val)

    def action_submit_path(self) -> None:
        """Submit the current path (Enter key)."""
        if self.valid and self.path:
            # Move focus to next widget
            self.screen.focus_next()

    def action_browse(self) -> None:
        """Open browse dialog (Ctrl+B)."""
        # In a real implementation, this would open a folder dialog
        # For now, we'll just show a placeholder message
        self._show_error("Browse dialog not yet implemented")

    def action_paste_path(self) -> None:
        """Paste clipboard content to path input (Ctrl+V)."""
        # This is handled by the Input widget itself
        if self._input:
            self._input.focus()

    def action_clear_or_blur(self) -> None:
        """Clear input if not empty, otherwise blur (Escape)."""
        if self.path:
            self.set_path("")
        else:
            self.blur()

    def on_focus(self) -> None:
        """Handle focus event."""
        # Focus the input when the widget gets focus
        if self._input:
            self._input.focus()

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        # Arrow keys navigation within the widget
        if event.key == "tab":
            # Move focus between input and browse button
            if self._input and self._input.has_focus:
                browse_btn = self.query_one("#browse-btn", Button)
                browse_btn.focus()
                event.stop()
            else:
                # Let it bubble up for normal tab navigation
                pass
        elif event.key == "shift+tab":
            # Reverse tab navigation
            browse_btn = self.query_one("#browse-btn", Button)
            if browse_btn.has_focus:
                if self._input:
                    self._input.focus()
                    event.stop()

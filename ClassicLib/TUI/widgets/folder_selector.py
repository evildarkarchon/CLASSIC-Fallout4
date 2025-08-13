"""Folder selector widget for TUI."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Button, Static
from textual.reactive import reactive
from textual.message import Message


class FolderSelector(Static):
    """Custom folder path input with validation and browse button."""
    
    path = reactive("")
    valid = reactive(True)
    
    class PathChanged(Message):
        """Message sent when path changes."""
        def __init__(self, path: str, valid: bool) -> None:
            super().__init__()
            self.path = path
            self.valid = valid
    
    def __init__(
        self,
        placeholder: str = "",
        initial_path: str = "",
        validate_exists: bool = True,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.placeholder = placeholder
        self.initial_path = initial_path
        self.validate_exists = validate_exists
        self._input: Input | None = None
        self._error_label: Static | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the widget."""
        with Horizontal(classes="folder-selector-container"):
            self._input = Input(
                placeholder=self.placeholder,
                value=self.initial_path,
                classes="folder-input"
            )
            yield self._input
            yield Button("Browse", id="browse-btn", classes="browse-button")
        
        self._error_label = Static("", classes="error-label hidden")
        yield self._error_label
    
    def on_mount(self) -> None:
        """Initialize on mount."""
        if self.initial_path:
            self.path = self.initial_path
            self._check_path_validity()
    
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
            # In a real implementation, this would open a folder dialog
            # For now, we'll just show a placeholder message
            self._show_error("Browse dialog not yet implemented")
    
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
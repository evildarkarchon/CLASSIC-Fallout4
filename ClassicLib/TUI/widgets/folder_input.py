"""Folder Input Widget for CLASSIC TUI.

A compound widget for path entry with validation and browse capability.
"""

from pathlib import Path
from typing import override

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Static


class FolderInput(Horizontal):
    """Path input widget with validation and browse button.

    Attributes:
        folder_path: The current path value (reactive).
        is_valid: Whether the current path is valid (reactive).
        placeholder: Placeholder text for the input.
        setting_key: YAML setting key for persistence.
        widget_id: Unique ID for this widget.

    """

    folder_path: reactive[str] = reactive("")
    is_valid: reactive[bool] = reactive(True)

    DEFAULT_CSS = """
    FolderInput {
        height: 3;
    }

    FolderInput Input {
        width: 1fr;
    }

    FolderInput Button {
        min-width: 8;
        margin-left: 1;
    }

    FolderInput .validation-icon {
        width: 3;
        text-align: center;
        margin-left: 1;
    }
    """

    class PathChanged(Message):
        """Emitted when path changes and is valid."""

        def __init__(self, path: Path, widget_id: str) -> None:
            """Initialize PathChanged message.

            Args:
                path: The new valid path.
                widget_id: ID of the FolderInput widget that changed.

            """
            self.path = path
            self.widget_id = widget_id
            super().__init__()

    def __init__(
        self,
        placeholder: str = "Enter folder path...",
        setting_key: str | None = None,
        widget_id: str = "folder-input",
    ) -> None:
        """Initialize the FolderInput widget.

        Args:
            placeholder: Placeholder text for the input field.
            setting_key: Optional YAML setting key for persistence.
            widget_id: Unique ID for this widget instance.

        """
        super().__init__(id=widget_id)
        self.placeholder = placeholder
        self.setting_key = setting_key
        self._widget_id = widget_id

    @override
    def compose(self) -> ComposeResult:
        """Create the folder input layout.

        Yields:
            Input field, browse button, and validation icon.

        """
        yield Input(placeholder=self.placeholder, id="path-input")
        yield Button("📁", id="browse-btn")
        yield Static("", id="validation-icon", classes="validation-icon")

    def on_mount(self) -> None:
        """Load initial value from settings on mount."""
        from ClassicLib.TUI.test_mode import is_test_mode

        if is_test_mode():
            return  # Skip settings load in test mode for stable snapshots

        if self.setting_key:
            from ClassicLib.io.yaml import classic_settings

            saved_path = classic_settings(str, self.setting_key)
            if saved_path:
                self.folder_path = saved_path
                self.query_one("#path-input", Input).value = saved_path
                self._validate_and_update()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input value changes.

        Args:
            event: The input changed event.

        """
        if event.input.id == "path-input":
            self.folder_path = event.value
            self._validate_and_update()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Enter key).

        Args:
            event: The input submitted event.

        """
        if event.input.id == "path-input":
            self._save_to_settings()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle browse button press.

        Args:
            event: The button pressed event.

        """
        if event.button.id == "browse-btn":
            self._open_folder_browser()

    def _validate_and_update(self) -> None:
        """Validate current path and update visual indicators."""
        validation_icon = self.query_one("#validation-icon", Static)
        path_input = self.query_one("#path-input", Input)

        if not self.folder_path:
            # Empty is valid (optional field)
            self.is_valid = True
            validation_icon.update("")
            path_input.remove_class("-valid", "-invalid")
        elif self._validate_path(self.folder_path):
            self.is_valid = True
            validation_icon.update("✓")
            validation_icon.add_class("-valid")
            validation_icon.remove_class("-invalid")
            path_input.add_class("-valid")
            path_input.remove_class("-invalid")
            self.post_message(self.PathChanged(Path(self.folder_path), self._widget_id))
        else:
            self.is_valid = False
            validation_icon.update("✗")
            validation_icon.add_class("-invalid")
            validation_icon.remove_class("-valid")
            path_input.add_class("-invalid")
            path_input.remove_class("-valid")

    @staticmethod
    def _validate_path(path_str: str) -> bool:
        """Validate that path exists and is a directory.

        Args:
            path_str: The path string to validate.

        Returns:
            True if path is a valid directory, False otherwise.

        """
        try:
            path = Path(path_str)
            return path.exists() and path.is_dir()
        except (OSError, ValueError):
            return False

    def _save_to_settings(self) -> None:
        """Save current path to YAML settings if valid."""
        if self.setting_key and self.is_valid and self.folder_path:
            from ClassicLib.core.constants import YAML
            from ClassicLib.io.yaml import yaml_settings

            yaml_settings(str, YAML.Settings, f"CLASSIC_Settings.{self.setting_key}", self.folder_path)

    def _open_folder_browser(self) -> None:
        """Open the folder browser modal."""
        from ClassicLib.TUI.widgets.folder_browser import FolderBrowserModal

        start_path = Path(self.folder_path) if self.folder_path and Path(self.folder_path).exists() else Path.home()
        self.app.push_screen(
            FolderBrowserModal(start_path=start_path),
            callback=self._on_folder_selected,
        )

    def _on_folder_selected(self, selected_path: Path | None) -> None:
        """Handle folder selection from browser modal.

        Args:
            selected_path: The selected path, or None if cancelled.

        """
        if selected_path is not None:
            self.folder_path = str(selected_path)
            self.query_one("#path-input", Input).value = str(selected_path)
            self._validate_and_update()
            self._save_to_settings()

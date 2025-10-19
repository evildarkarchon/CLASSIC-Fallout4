"""Error dialog widget for displaying errors."""

import pyperclip
from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ErrorDialog(ModalScreen):
    """Modal error dialog for displaying errors."""

    DEFAULT_CSS = """
    ErrorDialog {
        align: center middle;
    }

    ErrorDialog > Container {
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }

    ErrorDialog .error-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    ErrorDialog .error-message {
        margin: 1 0;
        color: $text;
    }

    ErrorDialog .error-details {
        margin: 1 0;
        color: $text-muted;
        border: solid $border;
        padding: 1;
        max-height: 10;
        overflow-y: auto;
    }

    ErrorDialog Button {
        margin-top: 1;
        min-width: 20;
    }

    ErrorDialog .button-group {
        align: center middle;
        height: auto;
    }
    """

    def __init__(
        self,
        title: str = "Error",
        message: str = "An error occurred",
        details: str | None = None,
        close_callback: Callable | None = None,
    ) -> None:
        """Initialize the error dialog.

        Args:
            title: Dialog title
            message: Error message
            details: Optional error details/traceback
            close_callback: Optional callback for close action
        """
        super().__init__()
        self.title = title
        self.message = message
        self.details = details
        self.close_callback = close_callback
        self.copy_success = False

    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Container(), Vertical():
            yield Label(f"❌ {self.title}", classes="error-title")
            yield Label(self.message, classes="error-message")
            if self.details:
                yield Label(self.details, classes="error-details")

            # Button group
            from textual.containers import Horizontal
            with Horizontal(classes="button-group"):
                if self.details:
                    yield Button("Copy to Clipboard", variant="primary", id="copy")
                yield Button("Close", variant="error", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "copy":
            self._copy_to_clipboard()
        elif event.button.id == "close":
            if self.close_callback:
                self.close_callback()
            self.dismiss()

    def _copy_to_clipboard(self) -> None:
        """Copy error details to clipboard."""
        try:
            full_text = f"{self.title}\n\n{self.message}"
            if self.details:
                full_text += f"\n\nDetails:\n{self.details}"

            pyperclip.copy(full_text)
            self.copy_success = True

            # Update button text to show confirmation
            copy_button = self.query_one("#copy", Button)
            original_label = copy_button.label
            copy_button.label = "✓ Copied!"

            # Reset button text after 2 seconds
            self.set_timer(2.0, lambda: setattr(copy_button, "label", original_label))
        except Exception as e:
            # If pyperclip fails, show error in the message
            self.notify(f"Failed to copy to clipboard: {e}", severity="error")

    def on_key(self, event) -> None:  # noqa: ANN001
        """Handle keyboard events."""
        if event.key in ["escape", "enter"]:
            if self.close_callback:
                self.close_callback()
            self.dismiss()

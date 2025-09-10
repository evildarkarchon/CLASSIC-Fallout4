"""Error dialog widget for displaying errors."""

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
        align: center middle;
        margin-top: 1;
        min-width: 12;
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

    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Container(), Vertical():
            yield Label(f"❌ {self.title}", classes="error-title")
            yield Label(self.message, classes="error-message")
            if self.details:
                yield Label(self.details, classes="error-details")
            yield Button("Close", variant="error", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: ARG002
        """Handle button press events."""
        if self.close_callback:
            self.close_callback()
        self.dismiss()

    def on_key(self, event) -> None:  # noqa: ANN001
        """Handle keyboard events."""
        if event.key in ["escape", "enter"]:
            if self.close_callback:
                self.close_callback()
            self.dismiss()

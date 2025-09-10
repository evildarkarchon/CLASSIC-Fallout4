"""Progress dialog widget for long-running operations."""

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ProgressDialog(ModalScreen):
    """Modal progress dialog for long-running operations."""

    DEFAULT_CSS = """
    ProgressDialog {
        align: center middle;
    }

    ProgressDialog > Container {
        width: 60;
        height: 10;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ProgressDialog .progress-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ProgressDialog .progress-message {
        margin: 1 0;
        color: $text;
    }

    ProgressDialog .progress-bar {
        margin: 1 0;
        height: 1;
        background: $panel;
        border: solid $border;
    }

    ProgressDialog .progress-fill {
        background: $success;
        height: 1;
    }

    ProgressDialog Button {
        align: center middle;
        margin-top: 1;
        min-width: 12;
    }
    """

    def __init__(
        self,
        title: str = "Processing",
        message: str = "Please wait...",
        can_cancel: bool = True,
        cancel_callback: Callable | None = None,
    ) -> None:
        """Initialize the progress dialog.

        Args:
            title: Dialog title
            message: Progress message
            can_cancel: Whether the operation can be cancelled
            cancel_callback: Optional callback for cancel action
        """
        super().__init__()
        self.title = title
        self.message = message
        self.can_cancel = can_cancel
        self.cancel_callback = cancel_callback
        self.progress = 0

    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Container(), Vertical():
            yield Label(self.title, classes="progress-title")
            yield Label(self.message, id="progress-message", classes="progress-message")
            with Container(classes="progress-bar"):
                yield Container(id="progress-fill", classes="progress-fill")
            if self.can_cancel:
                yield Button("Cancel", variant="warning", id="cancel")

    def update_progress(self, progress: int, message: str | None = None) -> None:
        """Update the progress bar and message.

        Args:
            progress: Progress percentage (0-100)
            message: Optional new message
        """
        self.progress = min(100, max(0, progress))
        try:
            fill = self.query_one("#progress-fill", Container)
            fill.styles.width = f"{self.progress}%"
        except:
            # Widget not yet composed
            pass

        if message:
            try:
                msg_label = self.query_one("#progress-message", Label)
                msg_label.update(message)
            except:
                # Widget not yet composed
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "cancel" and self.cancel_callback:
            self.cancel_callback()
            self.dismiss()

    def on_key(self, event) -> None:  # noqa: ANN001
        """Handle keyboard events."""
        if event.key == "escape" and self.can_cancel:
            if self.cancel_callback:
                self.cancel_callback()
            self.dismiss()

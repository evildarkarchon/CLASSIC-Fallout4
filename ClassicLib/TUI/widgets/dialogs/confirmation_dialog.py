"""Confirmation dialog widget for user confirmations."""

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmationDialog(ModalScreen[bool]):
    """Modal confirmation dialog for user confirmations."""

    DEFAULT_CSS = """
    ConfirmationDialog {
        align: center middle;
    }

    ConfirmationDialog > Container {
        width: 60;
        height: 11;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ConfirmationDialog .dialog-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ConfirmationDialog .dialog-message {
        margin: 1 0;
        color: $text;
    }

    ConfirmationDialog .dialog-buttons {
        margin-top: 1;
        align: center middle;
        height: 3;
    }

    ConfirmationDialog Button {
        margin: 0 1;
        min-width: 12;
    }

    ConfirmationDialog .confirm-button {
        background: $primary;
    }

    ConfirmationDialog .cancel-button {
        background: $secondary;
    }
    """

    def __init__(  # noqa: PLR0913
        self,
        title: str = "Confirm",
        message: str = "Are you sure?",
        confirm_text: str = "Yes",
        cancel_text: str = "No",
        confirm_callback: Callable | None = None,
        cancel_callback: Callable | None = None,
    ) -> None:
        """Initialize the confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message
            confirm_text: Text for confirm button
            cancel_text: Text for cancel button
            confirm_callback: Optional callback for confirm action
            cancel_callback: Optional callback for cancel action
        """
        super().__init__()
        self.title = title
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback

    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Container(), Vertical():
            yield Label(self.title, classes="dialog-title")
            yield Label(self.message, classes="dialog-message")
            with Horizontal(classes="dialog-buttons"):
                yield Button(self.confirm_text, variant="primary", id="confirm", classes="confirm-button")
                yield Button(self.cancel_text, variant="default", id="cancel", classes="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "confirm":
            if self.confirm_callback:
                self.confirm_callback()
            self.dismiss(True)
        else:
            if self.cancel_callback:
                self.cancel_callback()
            self.dismiss(False)

    def on_key(self, event) -> None:  # noqa: ANN001
        """Handle keyboard events."""
        if event.key == "escape":
            if self.cancel_callback:
                self.cancel_callback()
            self.dismiss(False)
        elif event.key == "enter":
            if self.confirm_callback:
                self.confirm_callback()
            self.dismiss(True)

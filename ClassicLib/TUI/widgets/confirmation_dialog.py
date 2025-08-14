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

    def __init__(
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
        with Container():
            with Vertical():
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

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        if event.key == "escape":
            if self.cancel_callback:
                self.cancel_callback()
            self.dismiss(False)
        elif event.key == "enter":
            if self.confirm_callback:
                self.confirm_callback()
            self.dismiss(True)


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
        with Container():
            with Vertical():
                yield Label(f"❌ {self.title}", classes="error-title")
                yield Label(self.message, classes="error-message")
                if self.details:
                    yield Label(self.details, classes="error-details")
                yield Button("Close", variant="error", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if self.close_callback:
            self.close_callback()
        self.dismiss()

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        if event.key in ["escape", "enter"]:
            if self.close_callback:
                self.close_callback()
            self.dismiss()


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
        with Container():
            with Vertical():
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

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        if event.key == "escape" and self.can_cancel:
            if self.cancel_callback:
                self.cancel_callback()
            self.dismiss()

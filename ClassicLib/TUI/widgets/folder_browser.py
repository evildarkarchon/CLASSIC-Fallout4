"""Folder Browser Modal for CLASSIC TUI.

A TUI-native folder browser using DirectoryTree widget.
"""

from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Static


class FolderBrowserModal(ModalScreen[Path | None]):
    """Modal folder browser using DirectoryTree.

    Attributes:
        start_path: Initial directory to display.

    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    DEFAULT_CSS = """
    FolderBrowserModal {
        align: center middle;
    }

    #browser-container {
        width: 70%;
        height: 80%;
        background: #2d2d2d;
        border: solid #3c3c3c;
        padding: 1;
    }

    #browser-title {
        text-style: bold;
        color: #4a9eff;
        margin-bottom: 1;
    }

    #current-path {
        color: #808080;
        margin-bottom: 1;
        padding: 0 1;
        background: #1e1e1e;
    }

    #dir-tree {
        height: 1fr;
        border: solid #3c3c3c;
        margin-bottom: 1;
    }

    #browser-buttons {
        height: 3;
        align: center middle;
    }

    #browser-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, start_path: Path | None = None) -> None:
        """Initialize the folder browser modal.

        Args:
            start_path: Initial directory to display. Defaults to home directory.

        """
        super().__init__()
        self.start_path = start_path or Path.home()
        self._selected_path = self.start_path

    def compose(self) -> ComposeResult:
        """Create the folder browser layout.

        Yields:
            Container with title, current path display, directory tree, and buttons.

        """
        with Vertical(id="browser-container"):
            yield Static("Select Folder", id="browser-title")
            yield Static(str(self.start_path), id="current-path")
            yield DirectoryTree(str(self.start_path), id="dir-tree")
            with Horizontal(id="browser-buttons"):
                yield Button("Select", variant="primary", id="select-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_directory_tree_directory_selected(
        self,
        event: DirectoryTree.DirectorySelected,
    ) -> None:
        """Update current path display when directory is selected.

        Args:
            event: The directory selected event.

        """
        self._selected_path = event.path
        self.query_one("#current-path", Static).update(str(event.path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event.

        """
        if event.button.id == "select-btn":
            self.action_select()
        elif event.button.id == "cancel-btn":
            self.action_cancel()

    def action_select(self) -> None:
        """Confirm selection and return the selected path."""
        self.dismiss(self._selected_path)

    def action_cancel(self) -> None:
        """Cancel and return None."""
        self.dismiss(None)

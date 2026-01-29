"""CLASSIC TUI - Terminal User Interface using Textual.

This module provides a terminal-based interface for CLASSIC that runs in
the console using the Textual framework. It provides feature parity with
the PySide6 GUI while using the shared backend.

Example:
    Run the TUI from command line::

        $ uv run classic-tui
        $ python -m ClassicLib.TUI

"""

from ClassicLib.TUI.app import CLASSICApp
from ClassicLib.TUI.test_mode import initialize_test_mode

__all__ = ["CLASSICApp", "main"]


def main() -> None:
    """Launch the CLASSIC TUI application.

    Creates and runs the CLASSICApp instance. This is the entry point
    used by the `classic-tui` console script.
    """
    initialize_test_mode()
    app = CLASSICApp()
    app.run()

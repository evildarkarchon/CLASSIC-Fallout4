#!/usr/bin/env python
"""CLASSIC Terminal User Interface."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ClassicLib.SetupCoordinator import SetupCoordinator
from ClassicLib.TUI.app import CLASSICTuiApp


def main() -> None:
    """Initialize and run the TUI application."""
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)

    app = CLASSICTuiApp()
    app.run()


if __name__ == "__main__":
    main()

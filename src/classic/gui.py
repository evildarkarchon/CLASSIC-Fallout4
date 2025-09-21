"""GUI entry point for CLASSIC."""

import sys
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import GlobalRegistry and set LOCAL_DIR before any other initialization
from ClassicLib import GlobalRegistry

# Check if we're in development or installed mode
if (project_root / "CLASSIC Data").exists():
    # Development mode - CLASSIC Data exists at project root
    GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, project_root)
else:
    # Installed package mode - let SetupCoordinator handle it
    # or try current working directory
    import os
    cwd = Path.cwd()
    if (cwd / "CLASSIC Data").exists():
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, cwd)


def main():
    """GUI entry point for uvx compatibility."""
    try:
        from PySide6.QtWidgets import QApplication
        from ClassicLib import GlobalRegistry
        from CLASSIC_Interface import MainWindow
    except ImportError as e:
        print(f"Import error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    app = QApplication(sys.argv)

    # Initialize the application before creating the MainWindow
    # This ensures all required settings and paths are configured
    try:
        from ClassicLib.SetupCoordinator import SetupCoordinator

        # Create coordinator and initialize application
        coordinator = SetupCoordinator()
        coordinator.initialize_application(is_gui=True)

        # Don't run initial_setup here - MainWindow doesn't call it anymore either
        # The initialization is handled by initialize_application

        # Create the main window after initialization is complete
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error running GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

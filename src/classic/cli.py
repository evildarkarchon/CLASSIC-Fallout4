"""Command-line interface entry point for CLASSIC."""

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
    cwd = Path.cwd()
    if (cwd / "CLASSIC Data").exists():
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, cwd)

from CLASSIC_ScanLogs import main as scan_main


def main():
    """CLI entry point for uvx compatibility."""
    scan_main()


if __name__ == "__main__":
    main()

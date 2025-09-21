"""CLASSIC-Fallout4: Crash Log Auto-Scanner for Buffout 4."""

__version__ = "8.0.0"
__author__ = "Poet, evildarkarchon, wxMichael"

from pathlib import Path

# Set up data directory path
DATA_DIR = Path(__file__).parent.parent.parent / "CLASSIC Data"

# Ensure data directory exists in package context
if not DATA_DIR.exists():
    # Try relative to package installation
    try:
        import pkg_resources
        DATA_DIR = Path(pkg_resources.resource_filename("classic", "data"))
    except Exception:
        # Fallback to current directory
        DATA_DIR = Path.cwd() / "CLASSIC Data"

"""CLASSIC-Fallout4: Crash Log Auto-Scanner for Buffout 4."""

__version__ = "8.0.0"
__author__ = "Poet, evildarkarchon, wxMichael"

import sys
from pathlib import Path

# Determine project root and set up paths for both editable and installed modes
_current_file = Path(__file__).resolve()

# For editable installs from project root
_project_root = _current_file.parent.parent.parent  # src/classic/__init__.py -> project root
if (_project_root / "CLASSIC Data").exists() and (_project_root / "ClassicLib").exists():
    # We're in editable/development mode
    PROJECT_ROOT = _project_root
    DATA_DIR = _project_root / "CLASSIC Data"

    # Add project root to path so ClassicLib can be imported
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
else:
    # Installed mode - try to find data in package or working directory
    PROJECT_ROOT = Path.cwd()
    DATA_DIR = Path.cwd() / "CLASSIC Data"

    # Fallback paths
    if not DATA_DIR.exists():
        # Try relative to package installation
        try:
            import pkg_resources
            DATA_DIR = Path(pkg_resources.resource_filename("classic", "data"))
        except Exception:
            # Last resort - current directory
            DATA_DIR = Path.cwd() / "CLASSIC Data"

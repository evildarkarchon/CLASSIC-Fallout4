"""Rust Extension Loader with Multi-Path Support.

This module handles loading Rust extensions from multiple possible locations:
1. PyInstaller _internal directory (bundled in executable)
2. Local rust_extensions directory (committed to repo)
3. Package-relative locations (for development)
4. ClassicLib/rust_ext (backward compatibility)

NO pip installation or site-packages required!
"""

import logging
from typing import Any

from ClassicLib.integration.factory import detect_component

logger = logging.getLogger(__name__)


class RustExtensionLoader:
    """Legacy loader wrapper for backward compatibility.

    Delegates to ClassicLib.integration.factory for actual component detection.

    Attributes:
        loaded_module: The loaded Rust module (legacy, unused).
        load_path: Path where module was loaded from (legacy, unused).
        search_paths: List of paths searched (legacy, unused).

    """

    def __init__(self) -> None:
        """Initialize the RustExtensionLoader with default values."""
        self.loaded_module = None
        self.load_path = None
        self.search_paths = []

    @staticmethod
    def is_loaded() -> bool:
        """Check if any Rust components are available.

        Returns:
            True if at least one Rust component is available, False otherwise.

        """
        # Check a representative set of known Rust modules
        _known_modules = ["classic_yaml", "classic_scanlog", "classic_fileio"]
        return any(detect_component(m)[0] for m in _known_modules)

    def get_load_info(self) -> dict[str, Any]:
        """Get load info from detector.

        Returns:
            Dictionary containing load status, path info, and component details
            with keys: loaded, path, search_paths, in_pyinstaller, components, versions.

        """
        _known_modules = ["classic_yaml", "classic_scanlog", "classic_fileio"]
        components = {m: detect_component(m)[0] for m in _known_modules}
        versions: dict[str, str] = {}
        for m in _known_modules:
            avail, mod = detect_component(m)
            if avail and mod is not None:
                versions[m] = getattr(mod, "__version__", "unknown")
        return {
            "loaded": self.is_loaded(),
            "path": "modular_packages",
            "search_paths": [],
            "in_pyinstaller": False,
            "components": components,
            "versions": versions,
        }

    def load_extension(self) -> Any | None:
        """Attempt to detect Rust components.

        Returns:
            True if Rust components are available (to satisfy legacy checks),
            None if no components are available.

        """
        if self.is_loaded():
            return True
        return None


# Global loader instance
_rust_loader = RustExtensionLoader()


def load_rust_extensions() -> bool:
    """Load Rust extensions dynamically during runtime.

    Now delegates to component detection.

    Returns:
        True if any Rust components are available, False otherwise.

    """
    return _rust_loader.is_loaded()


def is_rust_available() -> bool:
    """Determine if the Rust extension is available.

    Returns:
        True if Rust extension is available and loaded, False otherwise.

    """
    return _rust_loader.is_loaded()


def get_rust_info() -> dict[str, Any]:
    """Fetch and return information related to the Rust environment.

    Returns:
        Dictionary with Rust environment info including load status,
        path, available components, and version information.

    """
    return _rust_loader.get_load_info()


# Auto-load on import
load_rust_extensions()

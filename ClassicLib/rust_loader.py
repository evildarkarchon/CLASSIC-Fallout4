"""
Rust Extension Loader with Multi-Path Support.

This module handles loading Rust extensions from multiple possible locations:
1. PyInstaller _internal directory (bundled in executable)
2. Local rust_extensions directory (committed to repo)
3. Package-relative locations (for development)
4. ClassicLib/rust_ext (backward compatibility)

NO pip installation or site-packages required!
"""

import logging
import warnings
from typing import Any

from ClassicLib.integration.detector import detect_rust_components, get_available_components

logger = logging.getLogger(__name__)


class RustExtensionLoader:
    """
    Legacy loader wrapper for backward compatibility.
    Delegates to ClassicLib.integration.detector.
    """

    def __init__(self) -> None:
        self.loaded_module = None
        self.load_path = None
        self.search_paths = []

    def is_loaded(self) -> bool:
        """Check if any Rust components are available."""
        components = detect_rust_components()
        return any(components.values())

    def get_load_info(self) -> dict:
        """Get load info from detector."""
        info = get_available_components()
        return {
            "loaded": self.is_loaded(),
            "path": "modular_packages",
            "search_paths": [],
            "in_pyinstaller": False,
            "components": info.get("components", {}),
            "versions": info.get("versions", {}),
        }

    def load_extension(self) -> Any | None:
        """
        Attempt to detect Rust components.
        Returns a dummy object if successful to satisfy legacy checks.
        """
        if self.is_loaded():
            return True
        return None


# Global loader instance
_rust_loader = RustExtensionLoader()


def load_rust_extensions() -> bool:
    """
    Loads Rust extensions dynamically during runtime.
    Now delegates to component detection.
    """
    return _rust_loader.is_loaded()


def get_rust_module() -> Any | None:
    """
    Retrieves the loaded Rust module.
    DEPRECATED: There is no single Rust module anymore.
    """
    warnings.warn(
        "get_rust_module() is deprecated. Use specific modules (e.g., classic_scanlog) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return None


def is_rust_available() -> bool:
    """
    Determines if the Rust extension is available.
    """
    return _rust_loader.is_loaded()


def get_rust_info() -> dict:
    """
    Fetches and returns information related to the Rust environment.
    """
    return _rust_loader.get_load_info()


# Auto-load on import
load_rust_extensions()

"""
Rust Extension Loader with Multi-Path Support.

This module handles loading Rust extensions from multiple possible locations:
1. PyInstaller _internal directory (bundled in executable)
2. Local rust_extensions directory (committed to repo)
3. Package-relative locations (for development)
4. ClassicLib/rust_ext (backward compatibility)

NO pip installation or site-packages required!
"""

import importlib.util
import sys
import warnings
from pathlib import Path
from typing import Any


class RustExtensionLoader:
    """
    Loader for Rust extensions that searches multiple locations.

    This ensures the Rust extensions work in all scenarios:
    - PyInstaller bundled executables
    - uvx from GitHub
    - Local development
    - Direct Python execution
    """

    def __init__(self):
        self.extension_name = "_rust"
        self.loaded_module = None
        self.load_path = None
        self.search_paths = self._get_search_paths()

    def _get_search_paths(self) -> list[Path]:
        """
        Get all possible paths where Rust extensions might be located.

        Returns:
            List of paths to search, in priority order
        """
        paths = []

        # 1. PyInstaller _internal directory (highest priority for bundled exe)
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            bundle_dir = Path(sys._MEIPASS)
            paths.append(bundle_dir / "_internal" / "rust_extensions")
            paths.append(bundle_dir / "rust_extensions")
            paths.append(bundle_dir)

        # 2. Get the project root (where this file is located)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent  # Go up from ClassicLib/rust_loader.py

        # 3. Committed rust_extensions directory (for uvx and local dev)
        rust_ext_dir = project_root / "rust_extensions"
        if rust_ext_dir.exists():
            paths.append(rust_ext_dir)

        # 4. Classic-rust package location (development build location)
        classic_rust_pkg = project_root / "classic-rust" / "python" / "classic_core"
        if classic_rust_pkg.exists():
            paths.append(classic_rust_pkg)

        # 5. ClassicLib/rust_ext (backward compatibility)
        classiclib_ext = project_root / "ClassicLib" / "rust_ext"
        if classiclib_ext.exists():
            paths.append(classiclib_ext)

        # 6. Current working directory (fallback)
        paths.append(Path.cwd() / "rust_extensions")

        # 7. Relative to this module
        paths.append(current_file.parent / "rust_ext")

        return paths

    def find_extension(self) -> Path | None:
        """
        Find the Rust extension file (.pyd on Windows, .so on Linux).

        Returns:
            Path to the extension file, or None if not found
        """
        # Determine the extension based on the platform
        if sys.platform == "win32":
            patterns = ["*.pyd"]
        elif sys.platform == "darwin":
            patterns = ["*.dylib", "*.so"]
        else:  # Linux and others
            patterns = ["*.so"]

        # Search for the extension with the correct name
        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            for pattern in patterns:
                # Look for files matching classic_core._rust pattern
                for ext_file in search_path.glob(pattern):
                    # Check if this is our extension
                    if "_rust" in ext_file.stem or "classic_core" in ext_file.stem:
                        return ext_file

        return None

    def load_extension(self) -> Any | None:
        """
        Load the Rust extension module.

        Returns:
            The loaded module, or None if loading failed
        """
        if self.loaded_module is not None:
            return self.loaded_module

        ext_path = self.find_extension()
        if ext_path is None:
            warnings.warn(
                "Rust extension not found in any of these locations:\n" +
                "\n".join(f"  - {p}" for p in self.search_paths if p.exists()),
                ImportWarning
            )
            return None

        try:
            # Load the module from the file path
            spec = importlib.util.spec_from_file_location(
                "classic_core._rust",
                ext_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create spec for {ext_path}")

            module = importlib.util.module_from_spec(spec)

            # Add the parent directory to sys.path temporarily
            parent_dir = str(ext_path.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)

            try:
                spec.loader.exec_module(module)
                self.loaded_module = module
                self.load_path = ext_path

                # Also register in sys.modules for import compatibility
                sys.modules["classic_core._rust"] = module
                sys.modules["_rust"] = module  # Alias for backward compatibility

                print(f"Successfully loaded Rust extension from: {ext_path}")
                return module
            finally:
                # Remove the temporarily added path
                if parent_dir in sys.path:
                    sys.path.remove(parent_dir)

        except Exception as e:
            warnings.warn(
                f"Failed to load Rust extension from {ext_path}: {e}",
                ImportWarning
            )
            return None

    def is_loaded(self) -> bool:
        """Check if the Rust extension is loaded."""
        return self.loaded_module is not None

    def get_load_info(self) -> dict:
        """
        Get information about the loading status.

        Returns:
            Dictionary with loading information
        """
        return {
            "loaded": self.is_loaded(),
            "path": str(self.load_path) if self.load_path else None,
            "search_paths": [str(p) for p in self.search_paths if p.exists()],
            "in_pyinstaller": getattr(sys, 'frozen', False),
        }


# Global loader instance
_rust_loader = RustExtensionLoader()


def load_rust_extensions() -> bool:
    """
    Load the Rust extensions.

    Returns:
        True if loaded successfully, False otherwise
    """
    return _rust_loader.load_extension() is not None


def get_rust_module():
    """
    Get the loaded Rust module.

    Returns:
        The Rust module if loaded, None otherwise
    """
    if not _rust_loader.is_loaded():
        _rust_loader.load_extension()
    return _rust_loader.loaded_module


def is_rust_available() -> bool:
    """
    Check if Rust extensions are available.

    Returns:
        True if Rust extensions are available
    """
    if not _rust_loader.is_loaded():
        _rust_loader.load_extension()
    return _rust_loader.is_loaded()


def get_rust_info() -> dict:
    """
    Get information about Rust extension loading.

    Returns:
        Dictionary with loading information
    """
    return _rust_loader.get_load_info()


# Auto-load on import
load_rust_extensions()

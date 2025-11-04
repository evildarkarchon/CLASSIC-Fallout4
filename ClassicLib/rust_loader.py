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
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any

from ClassicLib.MessageHandler import msg_info
from ClassicLib.MessageHandler.enums import MessageTarget


class RustExtensionLoader:
    """
    Loader for Rust extensions that searches multiple locations.

    This ensures the Rust extensions work in all scenarios:
    - PyInstaller bundled executables
    - uvx from GitHub
    - Local development
    - Direct Python execution
    """

    def __init__(self) -> None:
        """
        Initializes an instance of the class.

        This constructor sets up the initial attributes required for the instance,
        including defining the module's extension name, initializing the loaded
        module, and setting the load path. Additionally, it determines the search
        paths for module loading.
        """
        self.extension_name = "_rust"
        self.loaded_module = None
        self.load_path = None
        self.search_paths = self._get_search_paths()

    def _get_search_paths(self) -> list[Path]:  # noqa: PLR6301
        """
        Retrieves search paths for locating rust extension directories.

        This function identifies and prioritizes potential locations to search for
        rust extension directories based on different runtime environments and project
        structures. It accounts for bundled executables, project development setups,
        and fallback locations. The order of the paths reflects their priority for
        searching.

        Returns:
            list[Path]: A list of paths representing potential directories for rust
                extensions, ordered by search priority.
        """
        paths = []

        # 1. PyInstaller _internal directory (highest priority for bundled exe)
        if getattr(sys, "frozen", False):
            # Running in PyInstaller bundle
            bundle_dir = Path(sys._MEIPASS)  # pyright: ignore[reportAttributeAccessIssue]
            paths.extend((bundle_dir / "_internal" / "rust_extensions", bundle_dir / "rust_extensions", bundle_dir))

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
        # 7. Relative to this module
        paths.extend((Path.cwd() / "rust_extensions", current_file.parent / "rust_ext"))

        return paths

    def find_extension(self) -> Path | None:
        """
        Determines the appropriate extension file for the platform and searches for
        it in the specified search paths.

        This method examines the current platform to determine possible extension
        file patterns (e.g., `.pyd` for Windows, `.so` for Linux, and `.dylib` or `.so`
        for macOS) and looks for files in the provided search paths. The method
        specifically searches for files with names containing "_rust" or "classic_core."

        Returns:
            Path | None: The path to the extension file if found; otherwise, None.
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
        Loads a Rust extension module, if available, and registers it for import.

        This method attempts to load a Rust extension module from a specified
        directory path. It adds the directory containing the Rust extension to
        `sys.path` temporarily, and upon successful loading, registers the loaded
        module both under its full name and an alias in `sys.modules`. If the module
        cannot be loaded, it raises a warning and returns `None`.

        Returns:
            Any | None: The loaded Rust extension module if successful, or `None` if
            the extension could not be located or loaded.

        Raises:
            ImportError: If the module spec cannot be created from the extension path.
            ImportWarning: If the Rust extension is not found or if the loading process
            fails due to other exceptions.
        """
        if self.loaded_module is not None:
            return self.loaded_module

        ext_path = self.find_extension()
        if ext_path is None:
            warnings.warn(
                "Rust extension not found in any of these locations:\n" + "\n".join(f"  - {p}" for p in self.search_paths if p.exists()),
                ImportWarning,
                stacklevel=2,
            )
            return None

        def create_module_spec(path: Path) -> ModuleSpec:
            """Create module spec or raise ImportError if creation fails.

            Args:
                path: Path to the extension file to create a spec for.

            Returns:
                ModuleSpec: The module specification for the extension.

            Raises:
                ImportError: If the module spec cannot be created from the path.
            """
            spec = importlib.util.spec_from_file_location("classic_core._rust", path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create spec for {path}")
            return spec

        try:
            # Load the module from the file path
            spec = create_module_spec(ext_path)
            module = importlib.util.module_from_spec(spec)

            # Ensure loader is available (type safety) - runtime check, not assertion
            if spec.loader is None:
                raise ImportError(f"Module spec loader is None for {ext_path}")  # noqa: TRY301

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

                msg_info(f"Successfully loaded Rust extension from: {ext_path}", target=MessageTarget.CONSOLE)
                return module
            finally:
                # Remove the temporarily added path
                if parent_dir in sys.path:
                    sys.path.remove(parent_dir)

        except (ImportError, OSError, AttributeError) as e:
            warnings.warn(f"Failed to load Rust extension from {ext_path}: {e}", ImportWarning, stacklevel=2)
            return None

    def is_loaded(self) -> bool:
        """
        Determines if a module is currently loaded.

        This method checks whether the `loaded_module` attribute has been set
        to a non-None value, indicating that the module has been successfully
        loaded.

        Returns:
            bool: True if a module is loaded (i.e., `loaded_module` is not None),
            otherwise False.
        """
        return self.loaded_module is not None

    def get_load_info(self) -> dict:
        """
        Retrieves detailed information about the load status and associated paths.

        This method returns a dictionary containing the current load state, the
        load path if available, a list of valid search paths, and whether the
        application is running in a PyInstaller packaged environment.

        Returns:
            dict: A dictionary containing the following keys:
                - "loaded": A boolean indicating whether the object is loaded.
                - "path": A string representing the load path if available, otherwise None.
                - "search_paths": A list of strings representing valid search paths.
                - "in_pyinstaller": A boolean indicating if the application is running
                  in a PyInstaller packaged environment.
        """
        return {
            "loaded": self.is_loaded(),
            "path": str(self.load_path) if self.load_path else None,
            "search_paths": [str(p) for p in self.search_paths if p.exists()],
            "in_pyinstaller": getattr(sys, "frozen", False),
        }


# Global loader instance
_rust_loader = RustExtensionLoader()


def load_rust_extensions() -> bool:
    """
    Loads Rust extensions dynamically during runtime.

    This function acts as a bridge to load Rust-based extensions into the system,
    validating whether the operation is successful or not. Rust extensions are
    essential for system integrations requiring high performance.

    Returns:
        bool: True if the Rust extension loads successfully, else False.
    """
    return _rust_loader.load_extension() is not None


def get_rust_module():  # noqa: ANN201
    """
    Retrieves the loaded Rust module, loading it if not already loaded.

    This function initializes and retrieves the Rust module, ensuring the
    underlying extension is loaded before returning the module. The function
    checks the state of the module loader and invokes the necessary loading
    process if the module is not yet loaded.

    Returns:
        Module: The loaded Rust module from the loader.
    """
    if not _rust_loader.is_loaded():
        _rust_loader.load_extension()
    return _rust_loader.loaded_module


def is_rust_available() -> bool:
    """
    Determines if the Rust extension is available.

    Checks whether the Rust extension has been loaded successfully. If it is not
    yet loaded, it attempts to load the extension before returning the result.

    Returns:
        bool: True if the Rust extension is successfully loaded, False otherwise.
    """
    if not _rust_loader.is_loaded():
        _rust_loader.load_extension()
    return _rust_loader.is_loaded()


def get_rust_info() -> dict:
    """
    Fetches and returns information related to the Rust environment.

    This function interacts with the Rust loader to retrieve detailed
    load information, which is then returned as a dictionary.

    Returns:
        dict: A dictionary containing the load information from the
        Rust loader module.
    """
    return _rust_loader.get_load_info()


# Auto-load on import
load_rust_extensions()

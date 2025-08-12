"""
Global registry for sharing objects across modules without circular imports.
This module serves as a central storage location for objects that need to be accessed
from multiple modules throughout the application.
"""

import threading
from pathlib import Path
from typing import Any

# Central storage for all globally accessible objects
_registry: dict[str, Any] = {}
_registry_lock = threading.RLock()


# Define keys for consistent access
class Keys:
    YAML_CACHE = "yaml_cache"
    MANUAL_DOCS_GUI = "manual_docs_gui"
    GAME_PATH_GUI = "game_path_gui"
    GAME_PATH = "game_path"
    DOCS_PATH = "docs_path"
    IS_GUI_MODE = "is_gui_mode"
    OPEN_FILE_FUNC = "open_file_with_encoding"
    VR = "gamevars_vr"
    GAME = "gamevars_game"
    LOCAL_DIR = "local_dir"
    IS_PRERELEASE = "is_prerelease"


def register(key: str, obj: Any) -> None:
    """
    Register an object in the global registry.

    Args:
        key: Unique identifier for the object
        obj: The object to register
    """
    with _registry_lock:
        _registry[key] = obj


def get(key: str) -> Any:
    """
    Retrieve an object from the global registry.

    Args:
        key: The unique identifier of the object

    Returns:
        The registered object or None if not found
    """
    with _registry_lock:
        return _registry.get(key)


def is_registered(key: str) -> bool:
    """
    Check if a key is registered.

    Args:
        key: The unique identifier to check

    Returns:
        True if the key exists in the registry, False otherwise
    """
    with _registry_lock:
        return key in _registry


# Convenience functions for commonly used registry items
def get_yaml_cache() -> Any:
    """Get the YAML settings cache instance."""
    return get(Keys.YAML_CACHE)


def get_manual_docs_gui() -> Any:
    """Get the manual docs GUI component."""
    return get(Keys.MANUAL_DOCS_GUI)


def get_game_path_gui() -> Any:
    """Get the game path GUI component."""
    return get(Keys.GAME_PATH_GUI)


def is_gui_mode() -> bool:
    """Check if the application is running in GUI mode."""
    return get(Keys.IS_GUI_MODE) or False


def open_file_with_encoding(path: Path | str, encoding: str = "utf-8", errors: str = "ignore"):  # noqa: ANN201
    """Open a file with the specified encoding."""
    func = get(Keys.OPEN_FILE_FUNC)
    if func:
        return func(path, encoding, errors)
    raise RuntimeError("open_file_with_encoding function not registered")


def get_vr() -> str:
    """Get the VR setting."""
    if not is_registered(Keys.VR) or (is_registered(Keys.VR) and Keys.VR == ""):
        return ""
    return get(Keys.VR)


def get_game() -> str:
    """Get the game setting."""
    if not is_registered(Keys.GAME) or (is_registered(Keys.GAME) and Keys.GAME == ""):
        return "Fallout4"
    return get(Keys.GAME)


def get_local_dir(as_string: bool = False) -> Path | str:
    """
    Determines and returns the local directory path.

    This function retrieves the local directory path, either as a Path object
    or as a string, based on the input argument. If the local directory is not
    registered or is an empty string, it defaults to the current working
    directory. Otherwise, it retrieves and uses the registered path.

    Parameters:
    as_string: bool
        Determines whether the returned local directory is converted to a
        string. Default is False.

    Returns:
    Path | str
        The local directory path as a Path object (default) or a string
        (if as_string is True).
    """
    if not is_registered(Keys.LOCAL_DIR) or (is_registered(Keys.LOCAL_DIR) and Keys.LOCAL_DIR == ""):
        if as_string:
            return str(Path.cwd())
        return Path.cwd()
    if as_string:
        return str(get(Keys.LOCAL_DIR))
    return get(Keys.LOCAL_DIR)

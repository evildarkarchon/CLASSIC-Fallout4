"""
Global registry for sharing objects across modules without circular imports.

This module serves as a central storage location for objects that need to be accessed
from multiple modules throughout the application.
"""

import os
import threading
from pathlib import Path
from typing import Any

# Central storage for all globally accessible objects
_registry: dict[str, Any] = {}
_registry_lock = threading.RLock()

# Environment variable to enable test-only functionality
_TESTING_MODE_ENV_VAR = "PYTEST_CURRENT_TEST"


# Define keys for consistent access
class Keys:
    """Contains constant keys used in the application.

    This class serves as a centralized definition of various constant strings
    used throughout the application. These constants serve as identifiers
    and configuration keys for various functionalities and settings.

    Attributes:
        YAML_CACHE (str): Key for caching YAML data.
        MANUAL_DOCS_GUI (str): Key representing manual documentation in GUI.
        GAME_PATH_GUI (str): Key representing game path in GUI.
        GAME_PATH (str): Key for storing the game path.
        DOCS_PATH (str): Key for storing the documentation path.
        IS_GUI_MODE (str): Key for checking if the application is in GUI mode.
        OPEN_FILE_FUNC (str): Key for the function to open files with encoding.
        VR (str): Key for VR-related game variables.
        GAME (str): Key for non-VR game variables.
        LOCAL_DIR (str): Key for the local directory path.
        IS_PRERELEASE (str): Key indicating whether the application is a prerelease version.
    """

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
        key: Unique identifier for the object (must be a string)
        obj: The object to register

    Raises:
        TypeError: If key is not a string
    """
    if not isinstance(key, str):
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        _registry[key] = obj


def get(key: str) -> Any:
    """
    Retrieve an object from the global registry.

    Args:
        key: The unique identifier of the object (must be a string)

    Returns:
        The registered object or None if not found

    Raises:
        TypeError: If key is not a string
    """
    if not isinstance(key, str):
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        return _registry.get(key)


def is_registered(key: str) -> bool:
    """
    Check if a key is registered.

    Args:
        key: The unique identifier to check (must be a string)

    Returns:
        True if the key exists in the registry, False otherwise

    Raises:
        TypeError: If key is not a string
    """
    if not isinstance(key, str):
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        return key in _registry


# Convenience functions for commonly used registry items
def get_yaml_cache() -> Any:
    """
    Retrieves the YAML cache from the application's storage.

    Fetches the YAML cache associated with the provided key and returns
    it. This function is typically used to retrieve cached configurations
    or data stored in YAML format.

    Returns:
        Any: The YAML cache retrieved from the storage.

    """
    return get(Keys.YAML_CACHE)


def set_game(game_name: str) -> None:
    """
    Sets the current game name in the system registry. This function ensures that
    a game name is either registered for the first time or updated if different
    from the currently registered game name. The operation is thread-safe due to
    the use of a lock mechanism.

    Args:
        game_name (str): The name of the game to set in the registry.
    """
    with _registry_lock:
        if not is_registered(Keys.GAME) or game_name != _registry[Keys.GAME]:
            register(Keys.GAME, game_name)


def get_manual_docs_gui() -> Any:
    """
    Retrieves the manual documentation GUI by accessing the appropriate key.

    This function fetches the manual documentation GUI value from a designated
    key repository. It leverages an internal mechanism to interact with the key
    management system and ensures the retrieval of the intended value.

    Returns:
        Any: The manual documentation GUI object associated with the specified
        key.
    """
    return get(Keys.MANUAL_DOCS_GUI)


def get_game_path_gui() -> Any:
    """
    Retrieves the value associated with the key `GAME_PATH_GUI` from a certain
    storage or configuration.

    This function uses a predefined constant key to fetch the corresponding value
    from an assumed underlying storage or configuration system.

    Returns:
        Any: The value associated with the `GAME_PATH_GUI` key.

    """
    return get(Keys.GAME_PATH_GUI)


def is_gui_mode() -> bool:
    """
    Determines if the application is running in GUI mode.

    This function checks the current state of the application and determines
    whether it is running with a graphical user interface (GUI) or not.
    The returned value is a boolean that represents this state.

    Returns:
        bool: True if the application is in GUI mode; otherwise, False.
    """
    return get(Keys.IS_GUI_MODE) or False


def open_file_with_encoding(path: Path | str, encoding: str = "utf-8", errors: str = "ignore"):  # noqa: ANN201
    """
    Opens a file with a specified encoding and error handling strategy. The function
    delegates the actual implementation to a registered handler, if available. If
    no handler is registered, raises a RuntimeError.

    Args:
        path: The path to the file to be opened. Can be a string or a Path object.
        encoding: The encoding to use for opening the file. Defaults to "utf-8".
        errors: Specifies the error handling strategy for encoding/decoding errors.
            Defaults to "ignore".

    Returns:
        The result of the registered function for opening the file.

    Raises:
        RuntimeError: If no function is registered to handle file opening.
    """
    func = get(Keys.OPEN_FILE_FUNC)
    if func:
        return func(path, encoding, errors)
    raise RuntimeError("open_file_with_encoding function not registered")


def get_vr() -> str:
    """
    Retrieves the value associated with the VR key if it is registered and non-empty. Otherwise, returns an
    empty string.

    Returns:
        str: The value associated with the VR key if registered and non-empty, or an empty string otherwise.
    """
    if not is_registered(Keys.VR) or (is_registered(Keys.VR) and not Keys.VR):
        return ""
    return get(Keys.VR)


def get_game() -> str:
    """
    Retrieves the name of the game.

    This function checks if a game is registered under the `Keys.GAME` key. If it is not registered or if the registered
    value is an empty string, the function defaults to returning the string "Fallout4". Otherwise, it retrieves and returns
    the registered game name.

    Returns:
        str: The name of the game. Defaults to "Fallout4" if no game is registered or if the registered game name is
        an empty string.
    """
    if not is_registered(Keys.GAME):
        return "Fallout4"

    game_value = get(Keys.GAME)
    # Return default if value is empty/None
    if not game_value:
        return "Fallout4"

    return game_value


def get_local_dir(as_string: bool = False) -> Path | str:
    """Determine and return the local directory path.

    Retrieves the local directory path, either as a Path object or as a
    string. If the local directory is not registered or is empty, defaults
    to the current working directory.

    Args:
        as_string: If True, return as string instead of Path. Default False.

    Returns:
        The local directory path as a Path object (default) or string.
    """
    if not is_registered(Keys.LOCAL_DIR) or (is_registered(Keys.LOCAL_DIR) and not Keys.LOCAL_DIR):
        if as_string:
            return str(Path.cwd())
        return Path.cwd()
    if as_string:
        return str(get(Keys.LOCAL_DIR))
    return get(Keys.LOCAL_DIR)


def clear() -> None:
    """Clear all entries from the global registry.

    This function is intended for use in testing scenarios ONLY to reset
    singleton state between test runs. It clears all registered objects
    from the registry to prevent test pollution.

    **WARNING**: This function will only execute when running under pytest
    (detected via the PYTEST_CURRENT_TEST environment variable). Calling
    this function in production code will raise a RuntimeError.

    This operation is thread-safe and will acquire the registry lock before
    clearing.

    Raises:
        RuntimeError: If called outside of a pytest testing context.

    Example:
        In test fixtures::

            import pytest
            from ClassicLib import GlobalRegistry

            @pytest.fixture(autouse=True)
            def clean_registry():
                GlobalRegistry.clear()
                yield
                GlobalRegistry.clear()

    Note:
        For production code that needs to remove specific entries, use
        targeted removal via direct registry access or implement a
        specific ``unregister()`` function for individual keys.
    """
    # Safety check: only allow clearing in test environments
    if not os.environ.get(_TESTING_MODE_ENV_VAR):
        raise RuntimeError(
            "GlobalRegistry.clear() is only allowed in testing contexts. "
            "The PYTEST_CURRENT_TEST environment variable is not set. "
            "If you need to clear the registry in production, reconsider "
            "your architecture or implement targeted removal methods."
        )

    with _registry_lock:
        _registry.clear()


def unregister(key: str) -> bool:
    """Remove a specific key from the global registry.

    This function removes a single entry from the registry. Unlike clear(),
    this can be used in production code for legitimate cleanup scenarios.

    Args:
        key: The unique identifier of the object to remove (must be a string).

    Returns:
        True if the key was found and removed, False if the key was not present.

    Raises:
        TypeError: If key is not a string.

    Example:
        >>> from ClassicLib import GlobalRegistry
        >>> GlobalRegistry.register("temp_key", "temp_value")
        >>> GlobalRegistry.unregister("temp_key")
        True
        >>> GlobalRegistry.unregister("nonexistent")
        False
    """
    if not isinstance(key, str):
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        if key in _registry:
            del _registry[key]
            return True
        return False

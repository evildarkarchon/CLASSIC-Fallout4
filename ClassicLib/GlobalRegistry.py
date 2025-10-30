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
    """
    Retrieves the YAML cache from the application's storage.

    Fetches the YAML cache associated with the provided key and returns
    it. This function is typically used to retrieve cached configurations
    or data stored in YAML format.

    Returns:
        Any: The YAML cache retrieved from the storage.

    """
    return get(Keys.YAML_CACHE)

def set_game(game_name: str):
    """
    Sets the current game name in the system registry. This function ensures that
    a game name is either registered for the first time or updated if different
    from the currently registered game name. The operation is thread-safe due to
    the use of a lock mechanism.

    Args:
        game_name (str): The name of the game to set in the registry.
    """
    with _registry_lock:
        if not is_registered(Keys.GAME) or not game_name == _registry[Keys.GAME]:
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
    if not is_registered(Keys.LOCAL_DIR) or (is_registered(Keys.LOCAL_DIR) and not Keys.LOCAL_DIR):
        if as_string:
            return str(Path.cwd())
        return Path.cwd()
    if as_string:
        return str(get(Keys.LOCAL_DIR))
    return get(Keys.LOCAL_DIR)

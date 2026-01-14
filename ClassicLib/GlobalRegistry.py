"""Global registry for sharing objects across modules without circular imports.

This module serves as a central storage location for objects that need to be accessed
from multiple modules throughout the application.
"""

from __future__ import annotations

import os
import threading
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from io import TextIOWrapper

    from ClassicLib.VersionRegistry.models import VersionInfo

# Central storage for all globally accessible objects
_registry: dict[str, Any] = {}
_registry_lock = threading.RLock()

# Environment variable to enable test-only functionality
_TESTING_MODE_ENV_VAR = "PYTEST_CURRENT_TEST"

# Type alias for Game Version values
GameVersionValue = Literal["auto", "Original", "NextGen", "AnniversaryEdition", "VR"]


# Define keys for consistent access
class Keys:
    """Contain constant keys used in the application.

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
        VR (str): Key for VR-related game variables (deprecated, use GAME_VERSION).
        GAME_VERSION (str): Key for the current game version (Original, NextGen, VR, or auto).
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
    VR = "gamevars_vr"  # Deprecated: Use GAME_VERSION instead
    GAME_VERSION = "gamevars_version"  # New in v8.0: Replaces VR Mode
    GAME = "gamevars_game"
    LOCAL_DIR = "local_dir"
    IS_PRERELEASE = "is_prerelease"


def register(key: str, obj: Any) -> None:
    """Register an object in the global registry.

    Args:
        key: Unique identifier for the object (must be a string)
        obj: The object to register

    Raises:
        TypeError: If key is not a string

    """
    if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        _registry[key] = obj


def get(key: str) -> Any:
    """Retrieve an object from the global registry.

    Args:
        key: The unique identifier of the object (must be a string)

    Returns:
        The registered object or None if not found

    Raises:
        TypeError: If key is not a string

    """
    if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        return _registry.get(key)


def is_registered(key: str) -> bool:
    """Check if a key is registered.

    Args:
        key: The unique identifier to check (must be a string)

    Returns:
        True if the key exists in the registry, False otherwise

    Raises:
        TypeError: If key is not a string

    """
    if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        return key in _registry


# Convenience functions for commonly used registry items
def get_yaml_cache() -> Any:
    """Retrieve the YAML cache from the application's storage.

    Fetches the YAML cache associated with the provided key and returns
    it. This function is typically used to retrieve cached configurations
    or data stored in YAML format.

    Returns:
        Any: The YAML cache retrieved from the storage.

    """
    return get(Keys.YAML_CACHE)


def set_game(game_name: str) -> None:
    """Set the current game name in the system registry. This function ensures that
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
    """Retrieve the manual documentation GUI by accessing the appropriate key.

    This function fetches the manual documentation GUI value from a designated
    key repository. It leverages an internal mechanism to interact with the key
    management system and ensures the retrieval of the intended value.

    Returns:
        Any: The manual documentation GUI object associated with the specified
        key.

    """
    return get(Keys.MANUAL_DOCS_GUI)


def get_game_path_gui() -> Any:
    """Retrieve the value associated with the key `GAME_PATH_GUI` from a certain
    storage or configuration.

    This function uses a predefined constant key to fetch the corresponding value
    from an assumed underlying storage or configuration system.

    Returns:
        Any: The value associated with the `GAME_PATH_GUI` key.

    """
    return get(Keys.GAME_PATH_GUI)


def is_gui_mode() -> bool:
    """Determine if the application is running in GUI mode.

    This function checks the current state of the application and determines
    whether it is running with a graphical user interface (GUI) or not.
    The returned value is a boolean that represents this state.

    Returns:
        bool: True if the application is in GUI mode; otherwise, False.

    """
    return get(Keys.IS_GUI_MODE) or False


def open_file_with_encoding(path: Path | str, encoding: str = "utf-8", errors: str = "ignore") -> TextIOWrapper:
    """Open a file with a specified encoding and error handling strategy. The function
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


def get_game_version() -> GameVersionValue:
    """Get the currently configured Fallout 4 version.

    This function returns the game version as set in the settings:
    - "auto" - Auto-detect from game files (default)
    - "Original" - Pre-Next-Gen update version (1.10.163)
    - "NextGen" - Next-Gen update version (1.10.984)
    - "AnniversaryEdition" - Anniversary Edition version (1.11.137 - 1.11.191+)
    - "VR" - Fallout 4 VR (1.2.72)

    Returns:
        GameVersionValue: The current game version setting. Defaults to "auto" if not set.

    Example:
        >>> from ClassicLib import GlobalRegistry
        >>> version = GlobalRegistry.get_game_version()
        >>> if version == "VR":
        ...     print("VR mode enabled")

    .. versionadded:: 8.0.0
        Replaces the legacy VR Mode boolean setting with a proper version enum.

    """
    if not is_registered(Keys.GAME_VERSION):
        # Check if legacy VR key is set for backward compatibility
        vr_value = get(Keys.VR) if is_registered(Keys.VR) else ""
        if vr_value == "VR":
            return "VR"
        return "auto"
    game_version = get(Keys.GAME_VERSION)
    if game_version in {"auto", "Original", "NextGen", "AnniversaryEdition", "VR"}:
        return game_version  # type: ignore[return-value]
    return "auto"


def get_vr() -> str:
    """Retrieve the VR suffix for configuration lookups.

    .. deprecated:: 8.0.0
       Use :func:`get_game_version()` instead. VR is now a version variant
       of Fallout 4, not a separate mode.

    This function is maintained for backward compatibility. It derives
    the VR suffix from the new GAME_VERSION setting.

    Returns:
        str: "VR" if game version is VR, otherwise empty string "".

    Example:
        >>> from ClassicLib import GlobalRegistry
        >>> # Old way (deprecated):
        >>> vr_suffix = GlobalRegistry.get_vr()
        >>> config_key = f"Game{vr_suffix}_Info.Setting"
        >>>
        >>> # New way (preferred):
        >>> version = GlobalRegistry.get_game_version()
        >>> if version == "VR":
        ...     config_key = "GameVR_Info.Setting"

    """
    # Issue deprecation warning only in non-test environments to reduce noise
    if not os.environ.get(_TESTING_MODE_ENV_VAR):
        warnings.warn(
            "get_vr() is deprecated, use get_game_version() instead. VR is now a version variant of Fallout 4.",
            DeprecationWarning,
            stacklevel=2,
        )

    # First check the new GAME_VERSION key
    if is_registered(Keys.GAME_VERSION):
        game_version = get(Keys.GAME_VERSION)
        if game_version == "VR":
            return "VR"
        return ""

    # Fall back to legacy VR key for backward compatibility
    if not is_registered(Keys.VR):
        return ""
    vr_value = get(Keys.VR)
    return vr_value or ""


def get_game() -> str:
    """Retrieve the name of the game.

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
    if not is_registered(Keys.LOCAL_DIR):
        if as_string:
            return str(Path.cwd())
        return Path.cwd()

    local_dir_value = get(Keys.LOCAL_DIR)
    if not local_dir_value:
        if as_string:
            return str(Path.cwd())
        return Path.cwd()

    if as_string:
        return str(local_dir_value)
    return local_dir_value


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
    if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    with _registry_lock:
        if key in _registry:
            del _registry[key]
            return True
        return False


def get_version_info() -> VersionInfo | None:
    """Get the VersionInfo from VersionRegistry based on current game version setting.

    This function looks up the current game version in the VersionRegistry and
    returns the corresponding VersionInfo object containing all metadata about
    the version (address library config, XSE config, etc.).

    Returns:
        VersionInfo: The VersionInfo for the current game version, or None if
            the version could not be found in the registry.

    Example:
        >>> from ClassicLib import GlobalRegistry
        >>> info = GlobalRegistry.get_version_info()
        >>> if info:
        ...     print(f"Game version: {info.display_name}")
        ...     if info.address_library:
        ...         print(f"Address Library: {info.address_library.filename}")

    .. versionadded:: 8.0.0
        Uses the VersionRegistry for data-driven version metadata.

    """
    from ClassicLib.VersionRegistry import get_version_registry

    game_version = get_game_version()

    if game_version == "auto":
        # For auto-detect, we can't determine the version without game file analysis
        # Return None and let the caller handle detection
        return None

    registry = get_version_registry()

    # Map the setting value to the short name used in VersionRegistry
    short_name_map = {
        "Original": "OG",
        "NextGen": "NG",
        "AnniversaryEdition": "AE",
        "VR": "VR",
    }
    short_name = short_name_map.get(game_version)
    if short_name:
        return registry.get_by_short_name(short_name)

    return None


def get_config_suffix() -> str:
    """Get the config key suffix based on game version from VersionRegistry.

    This function returns the configuration suffix ("" or "VR") to use when
    building YAML config keys like "Game_Info" or "GameVR_Info". The suffix
    is determined from the VersionRegistry based on the current game version.

    This is the preferred replacement for get_vr() that uses the VersionRegistry
    instead of legacy boolean settings.

    Returns:
        str: "VR" if the current game version is VR, otherwise empty string "".

    Example:
        >>> from ClassicLib import GlobalRegistry
        >>> suffix = GlobalRegistry.get_config_suffix()
        >>> config_key = f"Game{suffix}_Info.Root_Folder_Game"
        >>> # For VR: "GameVR_Info.Root_Folder_Game"
        >>> # For non-VR: "Game_Info.Root_Folder_Game"

    .. versionadded:: 8.0.0
        Replaces get_vr() with VersionRegistry integration.

    """
    game_version = get_game_version()

    # For VR, return "VR" suffix
    if game_version == "VR":
        return "VR"

    # For auto-detect mode, check if a VersionInfo is available from registry
    if game_version == "auto":
        version_info = get_version_info()
        if version_info and version_info.is_vr:
            return "VR"

    # For Original, NextGen, and auto (non-VR), return empty suffix
    return ""


def is_vr_version() -> bool:
    """Check if the current game version is a VR version.

    This function uses the VersionRegistry to determine if the current
    game version is VR.

    Returns:
        bool: True if the current game version is VR, False otherwise.

    Example:
        >>> from ClassicLib import GlobalRegistry
        >>> if GlobalRegistry.is_vr_version():
        ...     print("VR mode is active")
        >>> else:
        ...     print("Standard (non-VR) mode")

    .. versionadded:: 8.0.0
        Uses VersionRegistry for version determination.

    """
    return get_config_suffix() == "VR"

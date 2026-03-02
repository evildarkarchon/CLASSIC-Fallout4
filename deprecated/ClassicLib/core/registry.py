"""Global registry for sharing objects across modules without circular imports.

This module serves as a central storage location for objects that need to be accessed
from multiple modules throughout the application.

Storage is backed by Rust (classic_registry) for thread-safe, lock-free access via DashMap.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import classic_registry as _rust_registry

if TYPE_CHECKING:
    from io import TextIOWrapper

    from ClassicLib.support.versions import VersionInfo

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

    # Validation status flags (Phase 7 - Game Detection)
    XSE_VALID = "xse_validation_passed"
    XSE_VERSION = "xse_detected_version"
    ENB_PRESENT = "enb_binaries_present"
    GAME_VERSION_DETECTED = "game_exe_version"


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
    _rust_registry.register(key, obj)


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
    return _rust_registry.get(key)


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
    return _rust_registry.is_registered(key)


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
        >>> from ClassicLib.core.registry import GlobalRegistry
        >>> GlobalRegistry.register("temp_key", "temp_value")
        >>> GlobalRegistry.unregister("temp_key")
        True
        >>> GlobalRegistry.unregister("nonexistent")
        False

    """
    if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Registry key must be a string, got {type(key).__name__}")
    return _rust_registry.unregister(key)


def clear() -> None:
    """Clear all entries from the global registry.

    This function is intended for use in testing scenarios ONLY to reset
    singleton state between test runs. It clears all registered objects
    from the registry to prevent test pollution.

    **WARNING**: This function will only execute when running under pytest
    (detected via the PYTEST_CURRENT_TEST environment variable). Calling
    this function in production code will raise a RuntimeError.

    Raises:
        RuntimeError: If called outside of a pytest testing context.

    Example:
        In test fixtures::

            import pytest
            from ClassicLib.core.registry import GlobalRegistry

            @pytest.fixture(autouse=True)
            def clean_registry():
                GlobalRegistry.clear()
                yield
                GlobalRegistry.clear()

    """
    # Safety check: only allow clearing in test environments
    if not os.environ.get(_TESTING_MODE_ENV_VAR):
        raise RuntimeError(
            "GlobalRegistry.clear() is only allowed in testing contexts. "
            "The PYTEST_CURRENT_TEST environment variable is not set. "
            "If you need to clear the registry in production, reconsider "
            "your architecture or implement targeted removal methods."
        )
    _rust_registry.clear_all()


# Convenience functions for commonly used registry items
def get_yaml_cache() -> Any:
    """Retrieve the YAML cache from the application's storage.

    Returns:
        Any: The YAML cache retrieved from the storage.

    """
    return get(Keys.YAML_CACHE)


def set_game(game_name: str) -> None:
    """Set the current game name in the system registry.

    Args:
        game_name (str): The name of the game to set in the registry.

    """
    if not is_registered(Keys.GAME) or game_name != get(Keys.GAME):
        register(Keys.GAME, game_name)


def get_manual_docs_gui() -> Any:
    """Retrieve the manual documentation GUI.

    Returns:
        Any: The manual documentation GUI object.

    """
    return get(Keys.MANUAL_DOCS_GUI)


def get_game_path_gui() -> Any:
    """Retrieve the game path GUI value.

    Returns:
        Any: The value associated with the GAME_PATH_GUI key.

    """
    return get(Keys.GAME_PATH_GUI)


def is_gui_mode() -> bool:
    """Determine if the application is running in GUI mode.

    Returns:
        bool: True if the application is in GUI mode; otherwise, False.

    """
    return get(Keys.IS_GUI_MODE) or False


def open_file_with_encoding(path: Path | str, encoding: str = "utf-8", errors: str = "ignore") -> TextIOWrapper:
    """Open a file with a specified encoding and error handling strategy.

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

    Returns:
        str: "VR" if game version is VR, otherwise empty string "".

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

    Returns:
        str: The name of the game. Defaults to "Fallout4" if not set or empty.

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


def get_version_info() -> VersionInfo | None:
    """Get the VersionInfo from VersionRegistry based on current game version setting.

    Returns:
        VersionInfo: The VersionInfo for the current game version, or None if
            the version could not be found in the registry.

    """
    from ClassicLib.support.versions import get_version_registry

    game_version = get_game_version()

    if game_version == "auto":
        return None

    registry = get_version_registry()

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
    """Get the config key suffix based on game version.

    Returns:
        str: "VR" if the current game version is VR, otherwise empty string "".

    """
    game_version = get_game_version()

    if game_version == "VR":
        return "VR"

    if game_version == "auto":
        version_info = get_version_info()
        if version_info and version_info.is_vr:
            return "VR"

    return ""


def is_vr_version() -> bool:
    """Check if the current game version is a VR version.

    Returns:
        bool: True if the current game version is VR, False otherwise.

    """
    return get_config_suffix() == "VR"


class GlobalRegistry:
    """Namespace class providing access to global registry functions.

    All methods are static and delegate to the module-level functions.

    Attributes:
        Keys: Reference to the Keys class for accessing registry key constants.

    """

    Keys = Keys  # Reference to the Keys class

    @staticmethod
    def register(key: str, obj: Any) -> None:
        """Register an object in the global registry.

        See :func:`register` for full documentation.
        """
        return register(key, obj)

    @staticmethod
    def get(key: str) -> Any:
        """Retrieve an object from the global registry.

        See :func:`get` for full documentation.
        """
        return get(key)

    @staticmethod
    def is_registered(key: str) -> bool:
        """Check if a key is registered.

        See :func:`is_registered` for full documentation.
        """
        return is_registered(key)

    @staticmethod
    def get_yaml_cache() -> Any:
        """Retrieve the YAML cache.

        See :func:`get_yaml_cache` for full documentation.
        """
        return get_yaml_cache()

    @staticmethod
    def set_game(game_name: str) -> None:
        """Set the current game name.

        See :func:`set_game` for full documentation.
        """
        return set_game(game_name)

    @staticmethod
    def get_manual_docs_gui() -> Any:
        """Retrieve the manual documentation GUI.

        See :func:`get_manual_docs_gui` for full documentation.
        """
        return get_manual_docs_gui()

    @staticmethod
    def get_game_path_gui() -> Any:
        """Retrieve the game path GUI value.

        See :func:`get_game_path_gui` for full documentation.
        """
        return get_game_path_gui()

    @staticmethod
    def is_gui_mode() -> bool:
        """Check if running in GUI mode.

        See :func:`is_gui_mode` for full documentation.
        """
        return is_gui_mode()

    @staticmethod
    def open_file_with_encoding(path: Path | str, encoding: str = "utf-8", errors: str = "ignore") -> TextIOWrapper:
        """Open a file with specified encoding.

        See :func:`open_file_with_encoding` for full documentation.
        """
        return open_file_with_encoding(path, encoding, errors)

    @staticmethod
    def get_game_version() -> GameVersionValue:
        """Get the current game version.

        See :func:`get_game_version` for full documentation.
        """
        return get_game_version()

    @staticmethod
    def get_vr() -> str:
        """Retrieve the VR suffix (deprecated).

        See :func:`get_vr` for full documentation.
        """
        return get_vr()

    @staticmethod
    def get_game() -> str:
        """Retrieve the current game name.

        See :func:`get_game` for full documentation.
        """
        return get_game()

    @staticmethod
    def get_local_dir(as_string: bool = False) -> Path | str:
        """Get the local directory path.

        See :func:`get_local_dir` for full documentation.
        """
        return get_local_dir(as_string)

    @staticmethod
    def clear() -> None:
        """Clear all registry entries (testing only).

        See :func:`clear` for full documentation.
        """
        return clear()

    @staticmethod
    def unregister(key: str) -> bool:
        """Remove a key from the registry.

        See :func:`unregister` for full documentation.
        """
        return unregister(key)

    @staticmethod
    def get_version_info() -> VersionInfo | None:
        """Get VersionInfo for current game version.

        See :func:`get_version_info` for full documentation.
        """
        return get_version_info()

    @staticmethod
    def get_config_suffix() -> str:
        """Get config key suffix based on game version.

        See :func:`get_config_suffix` for full documentation.
        """
        return get_config_suffix()

    @staticmethod
    def is_vr_version() -> bool:
        """Check if current version is VR.

        See :func:`is_vr_version` for full documentation.
        """
        return is_vr_version()

    @staticmethod
    def is_xse_valid() -> bool:
        """Check if XSE validation passed.

        Returns:
            bool: True if XSE validation passed, False otherwise.

        """
        return get(Keys.XSE_VALID) or False

    @staticmethod
    def is_enb_present() -> bool:
        """Check if ENB binaries are present.

        Returns:
            bool: True if ENB binaries detected, False otherwise.

        """
        return get(Keys.ENB_PRESENT) or False

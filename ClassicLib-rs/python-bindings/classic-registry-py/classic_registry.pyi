"""Type stubs for classic_registry.

Python bindings for classic-registry-core, providing a thread-safe global registry
for storing and retrieving singleton instances and configuration values.

Architecture:
    - classic-registry-core: Business logic (thread-safe registry storage)
    - classic-registry-py: Python bindings (this module - PyO3 adapters)

Features:
    - Thread-safe singleton storage
    - Predefined registry keys for common values
    - Convenience functions for frequently accessed values
    - Type-safe key constants

Usage:
    from classic_registry import Keys, register, get, is_registered

    # Register values
    register(Keys.GAME, "Fallout4")
    register(Keys.IS_GUI_MODE, True)
    register("custom_key", {"data": 123})

    # Retrieve values
    game = get(Keys.GAME)
    if game is not None:
        print(f"Current game: {game}")

    # Check registration
    if is_registered(Keys.GAME):
        print("Game is configured")

    # Use convenience functions
    from classic_registry import get_game, set_game, is_gui_mode
    set_game("Skyrim")
    print(get_game())  # "Skyrim"
    print(is_gui_mode())  # True/False
"""


from typing import Any

__version__: str

class Keys:
    """Predefined registry keys for common values.

    This class provides constants for frequently used registry keys,
    ensuring consistency across the codebase.

    Attributes:
        YAML_CACHE: Key for YAML settings cache instance.
        MANUAL_DOCS_GUI: Key for manual documents GUI widget.
        GAME_PATH_GUI: Key for game path GUI widget.
        GAME_PATH: Key for game installation path.
        DOCS_PATH: Key for documents folder path.
        IS_GUI_MODE: Key for GUI mode flag.
        OPEN_FILE_FUNC: Key for file opening function callback.
        VR: **DEPRECATED** - Key for VR game variant identifier.
            Use GAME_VERSION instead. Will be removed in v9.0.
        GAME: Key for current game name.
        LOCAL_DIR: Key for local application directory.
        IS_PRERELEASE: Key for prerelease version flag.
        GAME_VERSION: Key for Fallout4Version enum (Original/NextGen/Vr).
            Replaces the deprecated VR key with proper version enum support.
        VERSION_AUTO_DETECTED: Key for version auto-detection status boolean.
            True if version was auto-detected from game files.

    Example:
        >>> from classic_registry import Keys, register
        >>> register(Keys.GAME, "Fallout4")
        >>> register(Keys.IS_GUI_MODE, True)
        >>> # New version-aware registration
        >>> register(Keys.GAME_VERSION, "NextGen")
        >>> register(Keys.VERSION_AUTO_DETECTED, True)

    """

    YAML_CACHE: str
    MANUAL_DOCS_GUI: str
    GAME_PATH_GUI: str
    GAME_PATH: str
    DOCS_PATH: str
    IS_GUI_MODE: str
    OPEN_FILE_FUNC: str
    VR: str  # Deprecated - use GAME_VERSION
    GAME: str
    LOCAL_DIR: str
    IS_PRERELEASE: str
    GAME_VERSION: str  # New in v8.0 - replaces VR
    VERSION_AUTO_DETECTED: str  # New in v8.0
    XSE_VALID: str
    XSE_VERSION: str
    ENB_PRESENT: str
    GAME_VERSION_DETECTED: str

def register(key: str, value: Any) -> None:
    """Register a value in the global registry.

    Stores a Python object in the registry under the given key. The value
    can be any Python object and will be accessible until explicitly cleared.

    Args:
        key: The registry key (use Keys constants when possible).
        value: The value to store (any Python object).

    Example:
        >>> from classic_registry import register, Keys
        >>> register(Keys.GAME, "Fallout4")
        >>> register(Keys.IS_GUI_MODE, True)
        >>> register("custom_key", {"data": 123})

    """

def is_registered(key: str) -> bool:
    """Check if a key is registered.

    Args:
        key: The registry key to check.

    Returns:
        True if the key exists in the registry, False otherwise.

    Example:
        >>> from classic_registry import is_registered, Keys
        >>> if is_registered(Keys.GAME):
        ...     print("Game is registered")

    """

def get(key: str) -> Any | None:
    """Retrieve a value from the global registry.

    Args:
        key: The registry key.

    Returns:
        The stored value, or None if not found.

    Example:
        >>> from classic_registry import get, Keys
        >>> game = get(Keys.GAME)
        >>> if game is not None:
        ...     print(f"Current game: {game}")

    """

def clear_all() -> None:
    """Clear all entries from the registry.

    Warning:
        This is primarily for testing. Use with caution in production
        as it will remove all registered values.

    Example:
        >>> from classic_registry import clear_all
        >>> # In test teardown
        >>> clear_all()

    """

def unregister(key: str) -> bool:
    """Remove a key from the global registry.

    Args:
        key: The registry key to remove.

    Returns:
        True if the key was found and removed, False if not present.

    Example:
        >>> from classic_registry import register, unregister
        >>> register("temp", "value")
        >>> unregister("temp")
        True
        >>> unregister("nonexistent")
        False

    """

def get_game() -> str:
    """Get the current game name.

    Returns:
        The game name, defaulting to "Fallout4" if not set.

    Example:
        >>> from classic_registry import get_game
        >>> game = get_game()
        >>> print(f"Current game: {game}")

    """

def set_game(game_name: str) -> None:
    """Set the current game name.

    Args:
        game_name: The game name (e.g., "Fallout4", "Skyrim").

    Example:
        >>> from classic_registry import set_game
        >>> set_game("Skyrim")

    """

def is_gui_mode() -> bool:
    """Check if the application is running in GUI mode.

    Returns:
        True if GUI mode, False for CLI mode.

    Example:
        >>> from classic_registry import is_gui_mode
        >>> if is_gui_mode():
        ...     print("Running in GUI mode")
        >>> else:
        ...     print("Running in CLI mode")

    """

def get_yaml_cache() -> Any | None:
    """Get the YAML settings cache instance.

    Returns:
        The cached YAML settings object, or None if not registered.

    Example:
        >>> from classic_registry import get_yaml_cache
        >>> cache = get_yaml_cache()
        >>> if cache is not None:
        ...     settings = cache.get_settings(...)

    """

def get_manual_docs_gui() -> Any | None:
    """Get the manual documents GUI widget reference.

    Returns:
        The GUI widget, or None if not registered.

    Example:
        >>> from classic_registry import get_manual_docs_gui
        >>> widget = get_manual_docs_gui()
        >>> if widget is not None:
        ...     widget.update_content(...)

    """

def get_game_path_gui() -> Any | None:
    """Get the game path GUI widget reference.

    Returns:
        The GUI widget, or None if not registered.

    Example:
        >>> from classic_registry import get_game_path_gui
        >>> widget = get_game_path_gui()
        >>> if widget is not None:
        ...     widget.set_path(...)

    """

def get_vr() -> str:
    """Get the VR game variant identifier.

    **DEPRECATED**: Use `is_version_auto_detected()` and check GAME_VERSION
    instead. VR is now treated as a version variant of Fallout 4, not a
    separate mode toggle. This function will be removed in v9.0.

    Returns:
        The VR variant suffix ("VR" if VR mode, empty string otherwise).

    Example:
        >>> from classic_registry import get_vr
        >>> vr = get_vr()
        >>> if vr:
        ...     print(f"VR variant: {vr}")

    .. deprecated:: 8.0.0
        Use `get(Keys.GAME_VERSION)` and `is_version_auto_detected()` instead.

    """

def get_local_dir() -> str:
    """Get the local application directory.

    Returns:
        The local directory path as a string.

    Example:
        >>> from classic_registry import get_local_dir
        >>> local_dir = get_local_dir()
        >>> print(f"Local directory: {local_dir}")

    """

def is_version_auto_detected() -> bool:
    """Check if the game version was auto-detected.

    This function returns whether the current game version (Original,
    NextGen, or VR) was automatically detected from game files rather
    than manually selected by the user.

    Returns:
        True if the version was auto-detected from game files,
        False if manually selected or not set.

    Example:
        >>> from classic_registry import is_version_auto_detected, Keys, get
        >>> if is_version_auto_detected():
        ...     print("Version was auto-detected")
        >>> else:
        ...     print("Version was manually selected")
        >>> # Get the actual version
        >>> version = get(Keys.GAME_VERSION)
        >>> print(f"Game version: {version}")

    .. versionadded:: 8.0.0

    """

def get_config_suffix() -> str:
    """Get the config key suffix based on game version.

    Returns "VR" if VR version, empty string otherwise. Used for building
    YAML config keys like "Game_Info" vs "GameVR_Info".

    Returns:
        "VR" if VR version, "" otherwise.

    """

def is_vr_version() -> bool:
    """Check if the current game version is VR.

    Returns:
        True if VR version, False otherwise.

    """

def is_xse_valid() -> bool:
    """Check if XSE validation passed.

    Returns:
        True if XSE validation passed, False otherwise.

    """

def is_enb_present() -> bool:
    """Check if ENB binaries are present.

    Returns:
        True if ENB binaries detected, False otherwise.

    """

def get_game_version_string() -> str:
    """Get the game version as a string.

    Returns:
        The version string, defaulting to "auto" if not set.

    """

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

from __future__ import annotations

from typing import Any, Optional

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
        VR: Key for VR game variant identifier.
        GAME: Key for current game name.
        LOCAL_DIR: Key for local application directory.
        IS_PRERELEASE: Key for prerelease version flag.

    Example:
        >>> from classic_registry import Keys, register
        >>> register(Keys.GAME, "Fallout4")
        >>> register(Keys.IS_GUI_MODE, True)
    """

    YAML_CACHE: str
    MANUAL_DOCS_GUI: str
    GAME_PATH_GUI: str
    GAME_PATH: str
    DOCS_PATH: str
    IS_GUI_MODE: str
    OPEN_FILE_FUNC: str
    VR: str
    GAME: str
    LOCAL_DIR: str
    IS_PRERELEASE: str


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


def get(key: str) -> Optional[Any]:
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


def get_yaml_cache() -> Optional[Any]:
    """Get the YAML settings cache instance.

    Returns:
        The cached YAML settings object, or None if not registered.

    Example:
        >>> from classic_registry import get_yaml_cache
        >>> cache = get_yaml_cache()
        >>> if cache is not None:
        ...     settings = cache.get_settings(...)
    """


def get_manual_docs_gui() -> Optional[Any]:
    """Get the manual documents GUI widget reference.

    Returns:
        The GUI widget, or None if not registered.

    Example:
        >>> from classic_registry import get_manual_docs_gui
        >>> widget = get_manual_docs_gui()
        >>> if widget is not None:
        ...     widget.update_content(...)
    """


def get_game_path_gui() -> Optional[Any]:
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

    Returns:
        The VR variant name, or empty string if not set.

    Example:
        >>> from classic_registry import get_vr
        >>> vr = get_vr()
        >>> if vr:
        ...     print(f"VR variant: {vr}")
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

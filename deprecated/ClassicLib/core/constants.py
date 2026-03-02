"""Constants and enumerations for CLASSIC-Fallout4.

This module provides:
- YAML file path enumeration for configuration files
- Database path resolution for FormID databases
- Game identifier type definitions
- Settings constants for ignore lists
- NULL_VERSION constant for error handling
"""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Iterator

# Removed to fix circular import - GlobalRegistry will be imported when needed

# Null version constant (used for error handling)
NULL_VERSION: Version = Version("0.0.0.0")


type GameID = (
    Literal["Fallout4", "Fallout4VR", "Skyrim", "Starfield"] | str
)  # Entries must correspond to the game's Main ESM or EXE file name.


class YAML(Enum):
    """Enumeration for representing various YAML file paths.

    This Enum class provides identifiers for different YAML file
    configurations used within the system. It maps descriptive enum
    members to their associated auto-generated values, each of which
    corresponds to a specific YAML file path in the application.
    """

    Main = auto()
    """CLASSIC Data/databases/CLASSIC Main.yaml"""
    Settings = auto()
    """CLASSIC Settings.yaml"""
    Ignore = auto()
    """CLASSIC Ignore.yaml"""
    Game = auto()
    """CLASSIC Data/databases/CLASSIC Fallout4.yaml"""
    Game_Local = auto()
    """CLASSIC Data/CLASSIC Fallout4 Local.yaml"""
    TEST = auto()
    """tests/test_settings.yaml"""
    Cache = auto()
    """User config dir/CLASSIC-Fallout4/cache.yaml - Persistent cache for uvx compatibility"""


"""class GameVars(TypedDict):
    game: GameID
    vr: Literal["VR", ""] | str"""


"""gamevars: GameVars = {
    "game": "Fallout4",
    "vr": "",
}"""

SETTINGS_IGNORE_NONE = {
    "SCAN Custom Path",
    "MODS Folder Path",
    "INI Folder Path",
    "Root_Folder_Game",
    "Root_Folder_Docs",
}


# Default FormID databases per game (relative to data directory).
# Used as fallback when YAML settings key is missing.
_DEFAULT_FORMID_DATABASES: dict[str, list[str]] = {
    "Fallout4": ["databases/FOLON FormIDs.db"],
    "Fallout4VR": ["databases/FOLON FormIDs.db"],
    "Skyrim": [],
    "Starfield": [],
}


def _get_hardcoded_db_paths() -> list[Path]:
    """Get always-on hardcoded FormID DB paths for the current game.

    These paths are resolved from ``_DEFAULT_FORMID_DATABASES`` and loaded
    alongside the Main FormID database in ``get_all_db_paths()`` even when
    the user-configured YAML list is empty.

    Returns:
        Existing absolute paths for hardcoded extra databases.

    """
    from ClassicLib.core.registry import GlobalRegistry
    from ClassicLib.support.resources import ResourceLoader

    data_dir = ResourceLoader.get_data_directory()
    game = GlobalRegistry.get_game()
    raw_paths = _DEFAULT_FORMID_DATABASES.get(game, [])

    resolved: list[Path] = []
    for entry in raw_paths:
        p = Path(entry)
        if not p.is_absolute():
            p = data_dir / p
        if p.is_file():
            resolved.append(p)

    return resolved


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """Return paths in original order with duplicates removed."""
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def get_main_db_path() -> Path:
    """Get the absolute path to the Main FormID database for the current game.

    Resolves the path relative to the CLASSIC Data directory found by
    ResourceLoader. This ensures the database works correctly whether
    running from source, installed package, or frozen executable.

    Returns:
        The absolute path to the Main FormID database file.

    """
    from ClassicLib.core.registry import GlobalRegistry
    from ClassicLib.support.resources import ResourceLoader

    data_dir = ResourceLoader.get_data_directory()
    game = GlobalRegistry.get_game()
    return data_dir / "databases" / f"{game} FormIDs Main.db"


def get_user_db_paths() -> list[Path]:
    """Get user-configured FormID database paths from YAML settings.

    Reads the game-specific database list from YAML settings at
    ``CLASSIC_Settings.FormID Databases.<game>``. Relative paths are
    resolved against ``ResourceLoader.get_data_directory()``, while
    absolute paths are used as-is. Missing files are filtered out with
    a warning.

    When the YAML key is absent (returns None), falls back to the
    defaults in ``_DEFAULT_FORMID_DATABASES`` for the current game.

    Returns:
        A list of absolute paths to existing user-configured database files.

    """
    from ClassicLib.core.logger import logger
    from ClassicLib.core.registry import GlobalRegistry
    from ClassicLib.io.yaml.convenience import yaml_settings
    from ClassicLib.support.resources import ResourceLoader

    data_dir = ResourceLoader.get_data_directory()
    game = GlobalRegistry.get_game()

    key_path = f"CLASSIC_Settings.FormID Databases.{game}"
    raw_paths: list[str] | None = yaml_settings(list, YAML.Settings, key_path)

    if raw_paths is None:
        raw_paths = _DEFAULT_FORMID_DATABASES.get(game, [])

    resolved: list[Path] = []
    for entry in raw_paths:
        p = Path(entry)
        if not p.is_absolute():
            p = data_dir / p
        if p.is_file():
            resolved.append(p)
        else:
            logger.warning("FormID database not found, skipping: %s", p)

    return resolved


def get_all_db_paths() -> list[Path]:
    """Get all FormID database paths (Main + hardcoded + user-configured).

    Combines the Main database path with hardcoded game-specific databases
    (e.g. FOLON for Fallout 4) and user-configured paths. The Main database
    is always first in the list regardless of whether it exists on disk
    (existence checking is the caller's responsibility for Main).

    Returns:
        A de-duplicated list with the Main database first, followed by
        hardcoded and user-configured databases.

    """
    return _dedupe_paths([get_main_db_path(), *_get_hardcoded_db_paths(), *get_user_db_paths()])


async def get_user_db_paths_async() -> list[Path]:
    """Async version of get_user_db_paths for use in async contexts.

    Reads the game-specific database list from YAML settings using
    ``yaml_settings_async`` to avoid the sync-in-async guard. Relative
    paths are resolved against ``ResourceLoader.get_data_directory()``.

    Returns:
        A list of absolute paths to existing user-configured database files.

    """
    from ClassicLib.core.logger import logger
    from ClassicLib.core.registry import GlobalRegistry
    from ClassicLib.io.yaml.async_.core import yaml_settings_async
    from ClassicLib.support.resources import ResourceLoader

    data_dir = ResourceLoader.get_data_directory()
    game = GlobalRegistry.get_game()

    key_path = f"CLASSIC_Settings.FormID Databases.{game}"
    raw_paths: list[str] | None = await yaml_settings_async(list, YAML.Settings, key_path)

    if raw_paths is None:
        raw_paths = _DEFAULT_FORMID_DATABASES.get(game, [])

    resolved: list[Path] = []
    for entry in raw_paths:
        p = Path(entry)
        if not p.is_absolute():
            p = data_dir / p
        if p.is_file():
            resolved.append(p)
        else:
            logger.warning("FormID database not found, skipping: %s", p)

    return resolved


async def get_all_db_paths_async() -> list[Path]:
    """Async version of get_all_db_paths for use in async contexts.

    Combines the Main database path with hardcoded game-specific databases
    and user-configured paths. Uses ``yaml_settings_async`` internally so
    it's safe to call from async code.

    Returns:
        A de-duplicated list with the Main database first, followed by
        hardcoded and user-configured databases.

    """
    return _dedupe_paths([get_main_db_path(), *_get_hardcoded_db_paths(), *(await get_user_db_paths_async())])


# For backward compatibility, create a property-like object
class _DBPaths:
    """Backward compatible DB_PATHS that lazily evaluates database paths.

    This class provides a lazy-loading wrapper around get_all_db_paths()
    to maintain backward compatibility with code that accesses DB_PATHS
    as an indexable/iterable collection.

    Note:
        This class has no instance attributes. It delegates all access
        to get_all_db_paths() which returns paths based on GlobalRegistry
        state and YAML settings.

    """

    def __getitem__(self, index: int) -> Path:
        return get_all_db_paths()[index]

    def __iter__(self) -> Iterator[Path]:
        return iter(get_all_db_paths())

    def __len__(self) -> int:
        return len(get_all_db_paths())


DB_PATHS = _DBPaths()

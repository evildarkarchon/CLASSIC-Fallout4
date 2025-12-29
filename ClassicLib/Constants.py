"""Constants and enumerations for CLASSIC-Fallout4.

This module provides:
- Version constants for Fallout 4 and F4SE versions (OG/NG/VR)
- YAML file path enumeration for configuration files
- Database path resolution for FormID databases
- Game identifier type definitions
- Settings constants for ignore lists

.. deprecated::
    The version constants (OG_VERSION, NG_VERSION, VR_VERSION, etc.) are deprecated.
    Use ClassicLib.VersionRegistry instead for data-driven version management:

    >>> from ClassicLib.VersionRegistry import get_version_registry
    >>> registry = get_version_registry()
    >>> og = registry.get_by_id("FO4_OG")
    >>> print(og.version)
    1.10.163.0
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from packaging.version import Version

# Removed to fix circular import - GlobalRegistry will be imported when needed

# Null version constant - NOT deprecated (used for error handling)
NULL_VERSION: Version = Version("0.0.0.0")


# =============================================================================
# DEPRECATED: Use ClassicLib.VersionRegistry instead
#
# These version constants are maintained for backward compatibility.
# New code should use VersionRegistry.get_by_id() or VersionRegistry.match_version().
#
# Example:
#     from ClassicLib.VersionRegistry import get_version_registry
#     registry = get_version_registry()
#     og_info = registry.get_by_id("FO4_OG")
#     ng_info = registry.get_by_id("FO4_NG")
# =============================================================================
class _DeprecatedVersion:
    """Wrapper that emits deprecation warning on access.

    This class wraps Version constants and emits a DeprecationWarning
    when the value is accessed.
    """

    def __init__(self, value: Version, name: str, replacement: str) -> None:
        """Initialize the deprecated version wrapper.

        Args:
            value: The actual Version object
            name: The constant name (for warning message)
            replacement: The suggested replacement code
        """
        self._value = value
        self._name = name
        self._replacement = replacement
        self._warned = False

    def __repr__(self) -> str:
        """Return string representation of the wrapped version."""
        self._warn()
        return repr(self._value)

    def __str__(self) -> str:
        """Return string of the wrapped version."""
        self._warn()
        return str(self._value)

    def __eq__(self, other: object) -> bool:
        """Compare for equality, emitting warning."""
        self._warn()
        if isinstance(other, _DeprecatedVersion):
            return self._value == other._value
        return self._value == other

    def __hash__(self) -> int:
        """Return hash of wrapped version."""
        self._warn()
        return hash(self._value)

    def __lt__(self, other: object) -> bool:
        """Compare for less than."""
        self._warn()
        if isinstance(other, _DeprecatedVersion):
            return self._value < other._value
        return self._value < other  # type: ignore[return-value]

    def __le__(self, other: object) -> bool:
        """Compare for less than or equal."""
        self._warn()
        if isinstance(other, _DeprecatedVersion):
            return self._value <= other._value
        return self._value <= other  # type: ignore[return-value]

    def __gt__(self, other: object) -> bool:
        """Compare for greater than."""
        self._warn()
        if isinstance(other, _DeprecatedVersion):
            return self._value > other._value
        return self._value > other  # type: ignore[return-value]

    def __ge__(self, other: object) -> bool:
        """Compare for greater than or equal."""
        self._warn()
        if isinstance(other, _DeprecatedVersion):
            return self._value >= other._value
        return self._value >= other  # type: ignore[return-value]

    def _warn(self) -> None:
        """Emit deprecation warning once."""
        if not self._warned:
            self._warned = True
            warnings.warn(
                f"{self._name} is deprecated. Use {self._replacement} instead.",
                DeprecationWarning,
                stacklevel=3,
            )

    @property
    def value(self) -> Version:
        """Get the underlying Version object."""
        self._warn()
        return self._value


# Create deprecated version constants with runtime warnings
OG_VERSION: Version = _DeprecatedVersion(  # type: ignore[assignment]
    Version("1.10.163.0"),
    "OG_VERSION",
    "get_version_registry().get_by_id('FO4_OG').version",
)
NG_VERSION: Version = _DeprecatedVersion(  # type: ignore[assignment]
    Version("1.10.984.0"),
    "NG_VERSION",
    "get_version_registry().get_by_id('FO4_NG').version",
)
VR_VERSION: Version = _DeprecatedVersion(  # type: ignore[assignment]
    Version("1.2.72.0"),
    "VR_VERSION",
    "get_version_registry().get_by_id('FO4_VR').version",
)
OG_F4SE_VERSION: Version = _DeprecatedVersion(  # type: ignore[assignment]
    Version("0.6.23"),
    "OG_F4SE_VERSION",
    "get_version_registry().get_by_id('FO4_OG').xse.compatible_version",
)
NG_F4SE_VERSION: Version = _DeprecatedVersion(  # type: ignore[assignment]
    Version("0.7.2"),
    "NG_F4SE_VERSION",
    "get_version_registry().get_by_id('FO4_NG').xse.compatible_version",
)

# These tuples still use the deprecated constants but don't emit warnings themselves
# (warning is emitted when accessing the tuple elements)
FO4_VERSIONS: tuple[Version, Version] = (OG_VERSION, NG_VERSION)  # type: ignore[assignment]
F4SE_VERSIONS: tuple[Version, Version] = (OG_F4SE_VERSION, NG_F4SE_VERSION)  # type: ignore[assignment]
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


# Define paths for both Main and Local databases
# Changed to a function to avoid circular import at module level
def get_db_paths() -> tuple[Path, Path, Path]:
    """Get absolute database paths based on current game.

    Returns absolute paths by resolving relative to CLASSIC Data directory
    found by ResourceLoader. This ensures databases work correctly whether
    running from source, installed package, or frozen executable.

    Returns:
        A tuple containing (main_db_path, local_db_path, and FOLON db path) as Path objects.

    """
    from ClassicLib import GlobalRegistry
    from ClassicLib.ResourceLoader import ResourceLoader

    # Get the CLASSIC Data directory (handles all installation types)
    data_dir = ResourceLoader.get_data_directory()

    # Return absolute paths to database files
    game = GlobalRegistry.get_game()
    return (
        data_dir / "databases" / f"{game} FormIDs Main.db",
        data_dir / "databases" / f"{game} FormIDs Local.db",
        data_dir / "databases" / "FOLON FormIDs.db",
    )


# For backward compatibility, create a property-like object
class _DBPaths:
    """Backward compatible DB_PATHS that lazily evaluates database paths.

    This class provides a lazy-loading wrapper around get_db_paths() to
    maintain backward compatibility with code that accesses DB_PATHS as
    an indexable/iterable collection.

    Note:
        This class has no instance attributes. It delegates all access
        to get_db_paths() which returns paths based on GlobalRegistry state.

    """

    def __getitem__(self, index: int) -> Path:
        return get_db_paths()[index]

    def __iter__(self) -> Iterator[Path]:
        return iter(get_db_paths())

    def __len__(self) -> int:
        return 3


DB_PATHS = _DBPaths()

"""Type stubs for classic_constants.

Python bindings for classic-constants-core, providing zero-cost compile-time constants
and type-safe enumerations used throughout CLASSIC.

Architecture:
    - classic-constants-core: Business logic (constants, enums)
    - classic-constants-py: Python bindings (this module - PyO3 adapters)

Features:
    - Version constants for Fallout 4 and F4SE
    - YAML file enumeration for type-safe file references
    - Game identifiers for supported Bethesda games
    - Settings validation constants

Usage:
    import classic_constants

    # Access version constants
    print(f"OG Version: {classic_constants.FALLOUT4_OG_VERSION}")
    print(f"NG Version: {classic_constants.FALLOUT4_NG_VERSION}")

    # Use YAML file enumeration
    settings = classic_constants.YamlFile.Settings
    print(settings.as_str())  # "Settings"
    print(settings.description())  # "CLASSIC Settings.yaml"

    # Use game identifiers
    game = classic_constants.GameId.Fallout4
    print(game.exe_name())  # "Fallout4.exe"
    print(game.is_vr())  # False

    # Check settings validation
    if classic_constants.must_not_be_none("Root_Folder_Game"):
        print("This setting must have a value")
"""

from __future__ import annotations

from typing import List

__version__: str

# Version Constants
NULL_VERSION: str
FALLOUT4_OG_VERSION: str
FALLOUT4_NG_VERSION: str
FALLOUT4_VR_VERSION: str
F4SE_OG_VERSION: str
F4SE_NG_VERSION: str

# Version Arrays
FALLOUT4_VERSIONS: List[str]
F4SE_VERSIONS: List[str]

# Settings Constants
SETTINGS_IGNORE_NONE: List[str]

class YamlFile:
    """YAML file enumeration for type-safe file references.

    Each variant corresponds to a specific YAML configuration file used by CLASSIC.
    This provides compile-time safety and clear documentation of available config files.

    Note:
        The enum variants are accessed as class attributes, not methods.
        Use `YamlFile.Settings`, not `YamlFile.Settings()`.

    Example:
        >>> from classic_constants import YamlFile
        >>> settings = YamlFile.Settings  # Access as attribute, not method
        >>> print(settings.as_str())
        'Settings'
        >>> print(settings.description())
        'CLASSIC Settings.yaml'
    """

    Main: YamlFile
    """CLASSIC Data/databases/CLASSIC Main.yaml - Main database file."""

    Settings: YamlFile
    """CLASSIC Settings.yaml - Settings configuration file."""

    Ignore: YamlFile
    """CLASSIC Ignore.yaml - Ignore patterns file."""

    Game: YamlFile
    """CLASSIC Data/databases/CLASSIC {Game}.yaml - Game-specific database files."""

    GameLocal: YamlFile
    """CLASSIC Data/CLASSIC {Game} Local.yaml - Local game configuration files."""

    Test: YamlFile
    """tests/test_settings.yaml - Test settings file (for testing only)."""

    Cache: YamlFile
    """User config dir/CLASSIC-Fallout4/cache.yaml - Persistent cache for uvx."""

    def as_str(self) -> str:
        """Get the string representation of the YAML file variant.

        Returns:
            The variant name as a string (e.g., "Main", "Settings").

        Example:
            >>> from classic_constants import YamlFile
            >>> assert YamlFile.Main.as_str() == "Main"
            >>> assert YamlFile.Settings.as_str() == "Settings"
        """

    def description(self) -> str:
        """Get a human-readable description of the YAML file.

        Returns:
            A description string including the typical file path.

        Example:
            >>> from classic_constants import YamlFile
            >>> desc = YamlFile.Main.description()
            >>> assert "CLASSIC Main.yaml" in desc
        """

    def __eq__(self, other: object) -> bool:
        """Check equality with another YamlFile.

        Args:
            other: Another YamlFile instance to compare.

        Returns:
            True if both are the same variant, False otherwise.
        """

    def __hash__(self) -> int:
        """Get hash value for the YamlFile.

        Returns:
            Hash value suitable for use in sets and dicts.
        """


class GameId:
    """Game identifiers for supported Bethesda games.

    Each variant corresponds to a specific Bethesda game supported by CLASSIC.
    Provides methods to query game-specific properties like executable names.

    Note:
        The enum variants are accessed as class attributes, not methods.
        Use `GameId.Fallout4`, not `GameId.Fallout4()`.

    Example:
        >>> from classic_constants import GameId
        >>> game = GameId.Fallout4  # Access as attribute, not method
        >>> print(game.as_str())
        'Fallout4'
        >>> print(game.exe_name())
        'Fallout4.exe'
        >>> print(game.is_vr())
        False
    """

    Fallout4: GameId
    """Fallout 4 (base game) - executable: Fallout4.exe"""

    Fallout4VR: GameId
    """Fallout 4 VR - executable: Fallout4VR.exe"""

    Skyrim: GameId
    """Skyrim Special Edition - executable: SkyrimSE.exe"""

    Starfield: GameId
    """Starfield - executable: Starfield.exe"""

    def as_str(self) -> str:
        """Get the string representation of the game identifier.

        Returns:
            The game name as a string (e.g., "Fallout4", "Skyrim").

        Example:
            >>> from classic_constants import GameId
            >>> assert GameId.Fallout4.as_str() == "Fallout4"
            >>> assert GameId.Fallout4VR.as_str() == "Fallout4VR"
        """

    def exe_name(self) -> str:
        """Get the executable name for this game.

        Returns:
            The game executable filename (e.g., "Fallout4.exe").

        Example:
            >>> from classic_constants import GameId
            >>> assert GameId.Fallout4.exe_name() == "Fallout4.exe"
            >>> assert GameId.Skyrim.exe_name() == "SkyrimSE.exe"
        """

    def is_vr(self) -> bool:
        """Check if this is a VR game.

        Returns:
            True if this is a VR variant, False otherwise.

        Example:
            >>> from classic_constants import GameId
            >>> assert not GameId.Fallout4.is_vr()
            >>> assert GameId.Fallout4VR.is_vr()
        """

    def __eq__(self, other: object) -> bool:
        """Check equality with another GameId.

        Args:
            other: Another GameId instance to compare.

        Returns:
            True if both are the same variant, False otherwise.
        """

    def __hash__(self) -> int:
        """Get hash value for the GameId.

        Returns:
            Hash value suitable for use in sets and dicts.
        """


def must_not_be_none(key: str) -> bool:
    """Check if a settings key should not allow None values.

    This function validates whether a given settings key is in the list
    of keys that must have a value (cannot be None/null).

    Args:
        key: The settings key to check.

    Returns:
        True if the key must not be None, False otherwise.

    Example:
        >>> from classic_constants import must_not_be_none
        >>> assert must_not_be_none("SCAN Custom Path")
        >>> assert must_not_be_none("Root_Folder_Game")
        >>> assert not must_not_be_none("Some Other Setting")
    """

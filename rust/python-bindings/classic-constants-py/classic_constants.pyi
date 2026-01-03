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

__version__: str

# Version Constants
NULL_VERSION: str
FALLOUT4_OG_VERSION: str
FALLOUT4_NG_VERSION: str
FALLOUT4_AE_VERSION: str
FALLOUT4_VR_VERSION: str
F4SE_OG_VERSION: str
F4SE_NG_VERSION: str
F4SE_AE_VERSION: str

# Version Arrays
FALLOUT4_VERSIONS: list[str]
F4SE_VERSIONS: list[str]

# Settings Constants
SETTINGS_IGNORE_NONE: list[str]

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

    def __repr__(self) -> str:
        """Return the debug representation of this YamlFile.

        Returns:
            A string representation suitable for debugging.

        """

    def __str__(self) -> str:
        """Return the string representation of this YamlFile.

        Returns:
            The variant name as a string.

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

    def __repr__(self) -> str:
        """Return the debug representation of this GameId.

        Returns:
            A string representation suitable for debugging.

        """

    def __str__(self) -> str:
        """Return the string representation of this GameId.

        Returns:
            The game identifier as a string.

        """

class Fallout4Version:
    """Fallout 4 version variants enumeration.

    Represents the four main version variants of Fallout 4 that CLASSIC supports.
    This replaces the legacy VR Mode toggle with a proper version enum.

    **MANDATORY**: All version metadata is sourced from the VersionRegistry.
    Methods like `exe_name()`, `docs_folder_name()`, etc. delegate to the
    VersionRegistry for their data. Use `registry_id()` to get the registry
    key for direct VersionRegistry lookups.

    Variants:
        - Original (OG): Pre-Next-Gen update version (1.10.163)
        - NextGen (NG): Next-Gen update version (1.10.984)
        - AnniversaryEdition (AE): Anniversary Edition version (1.11.137+)
        - Vr: Virtual Reality version (1.2.72)

    This enum treats VR as a version variant of Fallout 4 (not a separate game),
    allowing unified handling of game-specific logic with version-aware config.

    Note:
        The enum variants are accessed as class attributes, not methods.
        Use `Fallout4Version.NextGen`, not `Fallout4Version.NextGen()`.

    Example:
        >>> from classic_constants import Fallout4Version
        >>> version = Fallout4Version.NextGen  # Access as attribute, not method
        >>> print(version.display_name())
        'Fallout 4 Next-Gen'
        >>> print(version.is_vr())
        False
        >>> print(version.exe_name())
        'Fallout4.exe'
        >>> # Get registry ID for VersionRegistry lookup
        >>> print(version.registry_id())
        'FO4_NG'

    .. versionadded:: 8.0.0

    """

    Original: Fallout4Version
    """Original (OG) Fallout 4 - pre-Next-Gen Update version (1.10.163).

    This is the classic Fallout 4 version before the April 2024
    Next-Gen Update. Uses standard F4SE (0.6.23).
    """

    NextGen: Fallout4Version
    """Next-Gen (NG) Fallout 4 - post-April 2024 version (1.10.984).

    This is the updated Fallout 4 version from the April 2024
    Next-Gen Update. Uses updated F4SE (0.7.2).
    """

    AnniversaryEdition: Fallout4Version
    """Anniversary Edition (AE) Fallout 4 - version 1.11.137+.

    This is the Anniversary Edition branch which is actively developed.
    Version range starts at 1.11.137 and continues to evolve.
    """

    Vr: Fallout4Version
    """Fallout 4 VR - Virtual Reality version (1.2.72).

    Standalone VR release with different executable and configuration.
    Uses F4SEVR and VR-specific Address Library.
    """

    @staticmethod
    def from_str(s: str) -> Fallout4Version:
        """Create a Fallout4Version from a string.

        Accepts various string formats:
        - Full names: "Original", "NextGen", "AnniversaryEdition", "Vr"
        - Short forms: "OG", "NG", "AE", "VR"
        - Alternate forms: "anniversary", "anniversary-edition"
        - Version numbers: "1.10.163", "1.10.984", "1.11.137", "1.2.72"
        - Version prefixes: "1.11.*" (matches any Anniversary Edition version)
        - Special: "auto" (returns Original)

        Args:
            s: A string identifying the version.

        Returns:
            The corresponding Fallout4Version variant.

        Raises:
            ValueError: If the string doesn't match any known version.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> v1 = Fallout4Version.from_str("NextGen")
            >>> v2 = Fallout4Version.from_str("NG")  # Same as NextGen
            >>> v3 = Fallout4Version.from_str("AE")  # Anniversary Edition
            >>> v4 = Fallout4Version.from_str("VR")

        """

    @staticmethod
    def all() -> list[Fallout4Version]:
        """Get all Fallout 4 version variants.

        Returns:
            A list of all Fallout4Version variants (Original, NextGen, AnniversaryEdition, Vr).

        Example:
            >>> from classic_constants import Fallout4Version
            >>> for version in Fallout4Version.all():
            ...     print(version.display_name())

        """

    def is_vr(self) -> bool:
        """Check if this is the VR version.

        Returns:
            True if this is Fallout 4 VR, False otherwise.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert not Fallout4Version.Original.is_vr()
            >>> assert not Fallout4Version.NextGen.is_vr()
            >>> assert Fallout4Version.Vr.is_vr()

        """

    def is_standard(self) -> bool:
        """Check if this is a standard (non-VR) version.

        Returns:
            True if this is Original or NextGen, False if VR.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.is_standard()
            >>> assert Fallout4Version.NextGen.is_standard()
            >>> assert not Fallout4Version.Vr.is_standard()

        """

    def exe_name(self) -> str:
        """Get the executable name for this version.

        Returns:
            The game executable filename.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.exe_name() == "Fallout4.exe"
            >>> assert Fallout4Version.NextGen.exe_name() == "Fallout4.exe"
            >>> assert Fallout4Version.Vr.exe_name() == "Fallout4VR.exe"

        """

    def docs_folder_name(self) -> str:
        """Get the Documents folder name for this version.

        Returns:
            The folder name under My Documents.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.docs_folder_name() == "Fallout4"
            >>> assert Fallout4Version.Vr.docs_folder_name() == "Fallout4VR"

        """

    def steam_app_id(self) -> int:
        """Get the Steam app ID for this version.

        Returns:
            The Steam application ID.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.steam_app_id() == 377160
            >>> assert Fallout4Version.NextGen.steam_app_id() == 377160
            >>> assert Fallout4Version.Vr.steam_app_id() == 611660

        """

    def version(self) -> str:
        """Get the game version string from the VersionRegistry.

        Returns the 4-component version string from the VersionRegistry.
        The version is fetched dynamically for data-driven configuration.

        Returns:
            The version string (e.g., "1.10.163.0").

        Example:
            >>> from classic_constants import Fallout4Version
            >>> og_version = Fallout4Version.Original.version()
            >>> ng_version = Fallout4Version.NextGen.version()
            >>> vr_version = Fallout4Version.Vr.version()

        """

    def registry_id(self) -> str:
        """Get the VersionRegistry ID for this version variant.

        This is the key used to look up the full VersionInfo from the registry.
        Use this for direct VersionRegistry lookups.

        Returns:
            The registry ID string (e.g., "FO4_OG", "FO4_NG", "FO4_VR").

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.registry_id() == "FO4_OG"
            >>> assert Fallout4Version.NextGen.registry_id() == "FO4_NG"
            >>> assert Fallout4Version.Vr.registry_id() == "FO4_VR"

        """

    def short_name(self) -> str:
        """Get the short name for this version variant.

        Returns:
            The short name (e.g., "OG", "NG", "VR").

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.short_name() == "OG"
            >>> assert Fallout4Version.NextGen.short_name() == "NG"
            >>> assert Fallout4Version.Vr.short_name() == "VR"

        """

    def config_section(self) -> str:
        """Get the YAML config section name for this version.

        Returns:
            The section name in YAML config files.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.config_section() == "Game_Info"
            >>> assert Fallout4Version.Vr.config_section() == "GameVR_Info"

        """

    def config_suffix(self) -> str:
        """Get the config key suffix for this version.

        Returns:
            The suffix used in configuration keys ("" or "VR").

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.config_suffix() == ""
            >>> assert Fallout4Version.Vr.config_suffix() == "VR"

        """

    def xse_acronym(self) -> str:
        """Get the script extender acronym for this version.

        Returns:
            The XSE acronym (e.g., "F4SE" or "F4SEVR").

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.xse_acronym() == "F4SE"
            >>> assert Fallout4Version.Vr.xse_acronym() == "F4SEVR"

        """

    def display_name(self) -> str:
        """Get a human-readable display name from the VersionRegistry.

        Returns:
            The display name from VersionRegistry (e.g., "Fallout 4 Original").

        Example:
            >>> from classic_constants import Fallout4Version
            >>> print(Fallout4Version.Original.display_name())
            'Fallout 4 Original'
            >>> print(Fallout4Version.NextGen.display_name())
            'Fallout 4 Next-Gen'
            >>> print(Fallout4Version.Vr.display_name())
            'Fallout 4 VR'

        """

    def as_str(self) -> str:
        """Get the string representation for serialization and settings.

        Returns:
            A short identifier string for this version.

        Example:
            >>> from classic_constants import Fallout4Version
            >>> assert Fallout4Version.Original.as_str() == "Original"
            >>> assert Fallout4Version.NextGen.as_str() == "NextGen"
            >>> assert Fallout4Version.Vr.as_str() == "VR"

        """

    def __eq__(self, other: object) -> bool:
        """Check equality with another Fallout4Version.

        Args:
            other: Another Fallout4Version instance to compare.

        Returns:
            True if both are the same variant, False otherwise.

        """

    def __hash__(self) -> int:
        """Get hash value for the Fallout4Version.

        Returns:
            Hash value suitable for use in sets and dicts.

        """

    def __repr__(self) -> str:
        """Return the debug representation of this Fallout4Version.

        Returns:
            A string representation suitable for debugging.

        """

    def __str__(self) -> str:
        """Return the string representation of this Fallout4Version.

        Returns:
            The version identifier as a string.

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

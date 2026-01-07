"""Data models for version registry.

This module defines the data structures used to represent game version metadata
loaded from YAML configuration. All models are designed to be serializable and
match the YAML schema defined in CLASSIC Main.yaml Version_Registry section.

Example:
    >>> from ClassicLib.VersionRegistry.models import VersionInfo, AddressLibraryConfig
    >>> addr_lib = AddressLibraryConfig(
    ...     filename="version-1-10-163-0.bin",
    ...     format="bin",
    ...     nexus_url="https://www.nexusmods.com/fallout4/mods/47327"
    ... )
    >>> version = VersionInfo(
    ...     id="FO4_OG",
    ...     game="Fallout4",
    ...     is_vr=False,
    ...     version=Version("1.10.163.0"),
    ...     address_library=addr_lib
    ... )

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003
from typing import Literal

from packaging.version import Version


@dataclass(frozen=True)
class AddressLibraryConfig:
    """Address Library file configuration.

    Contains metadata about the Address Library file required for a specific
    game version. The Address Library is essential for many F4SE plugins to
    function correctly.

    Attributes:
        filename: Name of the Address Library file (e.g., "version-1-10-163-0.bin").
        format: File format, either "bin" (binary) or "csv" (text).
        nexus_url: Download URL for the Address Library on Nexus Mods.

    Example:
        >>> config = AddressLibraryConfig(
        ...     filename="version-1-10-163-0.bin",
        ...     format="bin",
        ...     nexus_url="https://www.nexusmods.com/fallout4/mods/47327"
        ... )
        >>> config.get_path(Path("C:/Games/Fallout4/Data/F4SE/plugins"))
        WindowsPath('C:/Games/Fallout4/Data/F4SE/plugins/version-1-10-163-0.bin')

    """

    filename: str
    format: Literal["bin", "csv"] = "bin"
    nexus_url: str = ""

    def get_path(self, plugins_dir: Path) -> Path:
        """Get full path to Address Library file.

        Args:
            plugins_dir: Path to the F4SE/plugins directory.

        Returns:
            Full path to the Address Library file.

        """
        return plugins_dir / self.filename


@dataclass(frozen=True)
class XseConfig:
    """Script Extender configuration.

    Contains metadata about the Script Extender (F4SE, SKSE, etc.) required
    for a specific game version.

    Attributes:
        acronym: XSE acronym (e.g., "F4SE", "F4SEVR", "SKSE").
        compatible_version: Compatible XSE version string (e.g., "0.6.23").
        loader: Loader executable name (e.g., "f4se_loader.exe").
        script_hashes: SHA-256 hashes for XSE script files (e.g., {"Actor.pex": "abc123..."}).

    Example:
        >>> config = XseConfig(
        ...     acronym="F4SE",
        ...     compatible_version="0.6.23",
        ...     loader="f4se_loader.exe",
        ...     script_hashes={"Actor.pex": "abc123..."}
        ... )

    """

    acronym: str
    compatible_version: str
    loader: str = ""
    script_hashes: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def compatible_version_parsed(self) -> Version:
        """Get the compatible version as a parsed Version object.

        Returns:
            Parsed Version object for comparison operations.

        """
        return Version(self.compatible_version)


@dataclass(frozen=True)
class CompatibleRange:
    """Version range for compatibility matching.

    Defines a range of game versions that are compatible with a particular
    configuration. Used for graceful matching of unknown versions.

    Attributes:
        min_version: Minimum version (inclusive).
        max_version: Maximum version (inclusive).

    Example:
        >>> range_config = CompatibleRange(
        ...     min_version=Version("1.10.163.0"),
        ...     max_version=Version("1.10.163.999")
        ... )
        >>> range_config.contains(Version("1.10.163.0"))
        True
        >>> range_config.contains(Version("1.10.984.0"))
        False

    """

    min_version: Version
    max_version: Version

    def contains(self, version: Version) -> bool:
        """Check if a version falls within this range.

        Args:
            version: The version to check.

        Returns:
            True if the version is within the range (inclusive), False otherwise.

        """
        return self.min_version <= version <= self.max_version

    @classmethod
    def from_strings(cls, min_str: str, max_str: str) -> CompatibleRange:
        """Create a CompatibleRange from version strings.

        Args:
            min_str: Minimum version string.
            max_str: Maximum version string.

        Returns:
            A new CompatibleRange instance.

        """
        return cls(min_version=Version(min_str), max_version=Version(max_str))


@dataclass
class VersionInfo:
    """Complete information about a game version.

    This is the primary data structure returned by the VersionRegistry.
    It contains all metadata needed to configure CLASSIC for a specific
    game version.

    Attributes:
        id: Unique identifier (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
        game: Game identifier (e.g., "Fallout4").
        is_vr: Whether this is a VR version.
        version: Parsed Version object.
        display_name: Human-readable name for UI display.
        short_name: Short identifier (e.g., "OG", "NG", "VR").
        description: Description of this version.
        address_library: Address Library configuration, if applicable.
        xse: Script Extender configuration, if applicable.
        compatible_range: Version range for matching unknown versions.
        priority: Priority for ambiguous matching (higher = preferred).
        deprecated: Whether this version is deprecated.
        exe_hash: SHA-256 hash of the game executable for this version.

    Example:
        >>> info = VersionInfo(
        ...     id="FO4_OG",
        ...     game="Fallout4",
        ...     is_vr=False,
        ...     version=Version("1.10.163.0"),
        ...     display_name="Fallout 4 Original",
        ...     short_name="OG",
        ...     exe_hash="55f57947..."
        ... )
        >>> info.version_string
        '1.10.163.0'

    """

    id: str
    game: str
    is_vr: bool
    version: Version
    display_name: str = ""
    short_name: str = ""
    description: str = ""
    address_library: AddressLibraryConfig | None = None
    xse: XseConfig | None = None
    compatible_range: CompatibleRange | None = None
    priority: int = 100
    deprecated: bool = False
    exe_hash: str | None = None

    @property
    def version_string(self) -> str:
        """Get version as string.

        Returns:
            String representation of the version.

        """
        return str(self.version)

    def is_compatible_with(self, detected: Version) -> bool:
        """Check if detected version is compatible with this version info.

        A version is compatible if:
        1. It falls within the compatible_range (if defined), OR
        2. It exactly matches this version (if no range is defined)

        Args:
            detected: The detected game version to check.

        Returns:
            True if the detected version is compatible, False otherwise.

        """
        if self.compatible_range:
            return self.compatible_range.contains(detected)
        return self.version == detected

    def __hash__(self) -> int:
        """Make VersionInfo hashable by its unique ID.

        Returns:
            Hash of the version ID.

        """
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Compare VersionInfo by ID.

        Args:
            other: Object to compare with.

        Returns:
            True if other is a VersionInfo with the same ID.

        """
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self.id == other.id


@dataclass(frozen=True)
class UnknownVersionHandling:
    """Configuration for handling unknown/unsupported versions.

    Defines the strategy and defaults for when CLASSIC encounters a game
    version not explicitly defined in the registry.

    Attributes:
        strategy: Matching strategy - "nearest_match", "strict", or "default_only".
        defaults: Mapping of game names to default version IDs.
        log_level: Log level for unknown version warnings.

    Example:
        >>> handling = UnknownVersionHandling(
        ...     strategy="nearest_match",
        ...     defaults={"Fallout4": "FO4_NG"},
        ...     log_level="warning"
        ... )

    """

    strategy: Literal["nearest_match", "strict", "default_only"] = "nearest_match"
    defaults: dict[str, str] = field(default_factory=dict)
    log_level: Literal["debug", "warning", "error"] = "warning"

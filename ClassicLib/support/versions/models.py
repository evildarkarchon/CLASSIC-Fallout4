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


@dataclass(frozen=True)
class CrashgenConfig:
    """Crash generator configuration for a specific version.

    Contains metadata about a crash generator (e.g., Buffout 4) including
    its version, name, description, download URL, and optional compatible
    game version range.

    Attributes:
        version: Version string of the crash generator (e.g., "1.28.6", "1.37.0").
        name: Display name (e.g., "Buffout 4", "Buffout 4 NG").
        description: Description of this crash generator version.
        download_url: Nexus Mods or other download URL.
        compatible_range: Optional game version range this crash generator
            is compatible with. If None, the crash generator is valid for
            any game version in the parent VersionInfo.

    Example:
        >>> config = CrashgenConfig(
        ...     version="1.28.6",
        ...     name="Buffout 4",
        ...     description="Legacy version for OG",
        ...     download_url="https://www.nexusmods.com/fallout4/mods/47359"
        ... )
        >>> config.version
        '1.28.6'

        >>> # With compatible range
        >>> og_range = CompatibleRange.from_strings("1.10.163.0", "1.10.163.999")
        >>> config_with_range = CrashgenConfig(
        ...     version="1.28.6",
        ...     name="Buffout 4",
        ...     compatible_range=og_range
        ... )
        >>> config_with_range.is_compatible_with(Version("1.10.163.0"))
        True

    """

    version: str
    name: str = ""
    description: str = ""
    download_url: str = ""
    compatible_range: CompatibleRange | None = None

    def is_compatible_with(self, game_version: Version) -> bool:
        """Check if this crash generator is compatible with a game version.

        If no compatible_range is defined, returns True (compatible with any version).
        Otherwise, checks if the game version falls within the compatible range.

        Args:
            game_version: The game version to check compatibility with.

        Returns:
            True if compatible, False otherwise.

        """
        if self.compatible_range is None:
            return True
        return self.compatible_range.contains(game_version)

    @classmethod
    def from_version_string(cls, version: str) -> CrashgenConfig:
        """Create a CrashgenConfig from just a version string.

        Convenience factory for backward compatibility when crash generator
        versions are specified as simple strings in YAML.

        Args:
            version: The crash generator version string.

        Returns:
            A new CrashgenConfig with only the version field set.

        Example:
            >>> config = CrashgenConfig.from_version_string("1.37.0")
            >>> config.version
            '1.37.0'
            >>> config.name
            ''

        """
        return cls(version=version)


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
        crashgen_versions: Tuple of CrashgenConfig objects for this game version.
            Each CrashgenConfig contains version, name, description, download_url,
            and optional compatible_range. For example, FO4_OG supports both
            Buffout 4 (1.28.6) and Buffout 4 NG (1.37.0), while FO4_NG only
            supports Buffout 4 NG (1.37.0). An empty tuple means no crash
            generator is supported yet.

    Example:
        >>> from ClassicLib.VersionRegistry.models import CrashgenConfig
        >>> crashgens = (
        ...     CrashgenConfig(version="1.28.6", name="Buffout 4"),
        ...     CrashgenConfig(version="1.37.0", name="Buffout 4 NG"),
        ... )
        >>> info = VersionInfo(
        ...     id="FO4_OG",
        ...     game="Fallout4",
        ...     is_vr=False,
        ...     version=Version("1.10.163.0"),
        ...     display_name="Fallout 4 Original",
        ...     short_name="OG",
        ...     exe_hash="55f57947...",
        ...     crashgen_versions=crashgens
        ... )
        >>> info.version_string
        '1.10.163.0'
        >>> info.get_crashgen_version_strings()
        ('1.28.6', '1.37.0')

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
    crashgen_versions: tuple[CrashgenConfig, ...] = field(default_factory=tuple)

    @property
    def version_string(self) -> str:
        """Get version as string.

        Returns:
            String representation of the version.

        """
        return str(self.version)

    def get_crashgen_version_strings(self) -> tuple[str, ...]:
        """Get crash generator versions as simple version strings.

        Provides backward-compatible access to just the version strings
        of the crash generators, without the additional metadata.

        Returns:
            Tuple of version strings from crashgen_versions.

        Example:
            >>> info.crashgen_versions
            (CrashgenConfig(version='1.28.6', ...), CrashgenConfig(version='1.37.0', ...))
            >>> info.get_crashgen_version_strings()
            ('1.28.6', '1.37.0')

        """
        return tuple(config.version for config in self.crashgen_versions)

    def get_crashgen_for_version(self, crashgen_version: str) -> CrashgenConfig | None:
        """Get a specific CrashgenConfig by its version string.

        Args:
            crashgen_version: The crash generator version to look up.

        Returns:
            The CrashgenConfig with the matching version, or None if not found.

        Example:
            >>> config = info.get_crashgen_for_version("1.28.6")
            >>> config.name
            'Buffout 4'

        """
        for config in self.crashgen_versions:
            if config.version == crashgen_version:
                return config
        return None

    def get_compatible_crashgens(self, game_version: Version | None = None) -> tuple[CrashgenConfig, ...]:
        """Get crash generators compatible with a specific game version.

        Filters crashgen_versions by their compatible_range. If a crash generator
        has no compatible_range defined, it is considered compatible with all
        game versions.

        Args:
            game_version: The game version to check compatibility with.
                If None, uses this VersionInfo's version.

        Returns:
            Tuple of CrashgenConfig objects compatible with the game version.

        Example:
            >>> compatible = info.get_compatible_crashgens()
            >>> [c.version for c in compatible]
            ['1.28.6', '1.37.0']

        """
        if game_version is None:
            game_version = self.version
        return tuple(config for config in self.crashgen_versions if config.is_compatible_with(game_version))

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

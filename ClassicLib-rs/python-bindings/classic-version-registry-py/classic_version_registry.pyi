"""Type stubs for classic_version_registry.

Python bindings for classic-version-registry-core, providing game version
detection, matching, and registry lookup powered by Rust.

Architecture:
    - classic-version-registry-core: Business logic (version registry, matching)
    - classic-version-registry-py: Python bindings (this module - PyO3 adapters)

Usage:
    import classic_version_registry

    # Get singleton registry
    registry = classic_version_registry.VersionRegistry()

    # Lookup by ID
    og = registry.get_by_id("FO4_OG")
    print(og.display_name)  # "Fallout 4 Original"
    print(og.version)  # "1.10.163.0"

    # Match unknown version
    result = registry.match_version("1.10.500.0", "Fallout4", False)
    if result.should_warn:
        print(result.message)

    # Convenience function
    result = classic_version_registry.match_version_string("1.10.163.0", "Fallout4", False)
    print(result.version_info.display_name)
"""

__version__: str

class GameVersion:
    """A 4-component game version (major.minor.patch.build).

    Represents game versions like "1.10.163.0" used by Bethesda games.
    Supports parsing, comparison, and semantic distance calculations.

    Example:
        >>> v = GameVersion("1.10.163.0")
        >>> print(v.major, v.minor, v.patch, v.build)
        1 10 163 0

    """

    def __init__(self, version_str: str) -> None:
        """Create a GameVersion from a version string.

        Accepts 3-component ("1.10.163") or 4-component ("1.10.163.0") versions.

        Args:
            version_str: Version string to parse.

        Raises:
            ValueError: If the version string is invalid.

        """

    @property
    def major(self) -> int:
        """Major version component."""

    @property
    def minor(self) -> int:
        """Minor version component."""

    @property
    def patch(self) -> int:
        """Patch version component."""

    @property
    def build(self) -> int:
        """Build version component."""

    def semantic_distance(self, other: GameVersion) -> int:
        """Calculate semantic distance to another version.

        Uses weighted formula: major*1,000,000 + minor*1,000 + patch*1.

        Args:
            other: The other GameVersion to compare against.

        Returns:
            The semantic distance as an integer.

        """

    def same_major(self, other: GameVersion) -> bool:
        """Check if this version has the same major version as another."""

    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
    def __lt__(self, other: GameVersion) -> bool: ...
    def __le__(self, other: GameVersion) -> bool: ...
    def __gt__(self, other: GameVersion) -> bool: ...
    def __ge__(self, other: GameVersion) -> bool: ...

class AddressLibraryConfig:
    """Address Library configuration for a game version.

    Example:
        >>> og = registry.get_by_id("FO4_OG")
        >>> print(og.address_library.filename)
        version-1-10-163-0.bin

    """

    @property
    def filename(self) -> str:
        """Name of the Address Library file (e.g., "version-1-10-163-0.bin")."""

    @property
    def format(self) -> str:
        """File format ("bin" or "csv")."""

    @property
    def nexus_url(self) -> str:
        """Nexus Mods download URL."""

class XseConfig:
    """Script Extender (XSE) configuration for a game version.

    Example:
        >>> og = registry.get_by_id("FO4_OG")
        >>> print(og.xse.acronym)
        F4SE

    """

    @property
    def acronym(self) -> str:
        """XSE acronym (e.g., "F4SE", "F4SEVR")."""

    @property
    def full_name(self) -> str:
        """Full display name (e.g., "Fallout 4 Script Extender (F4SE)")."""

    @property
    def compatible_version(self) -> str:
        """Compatible XSE version string (e.g., "0.6.23")."""

    @property
    def loader(self) -> str:
        """Loader executable name (e.g., "f4se_loader.exe")."""

    @property
    def file_count(self) -> int:
        """Expected number of script files."""

    @property
    def script_hashes(self) -> list[tuple[str, str]]:
        """List of (filename, sha256_hash) pairs for XSE script files."""

class CompatibleRange:
    """Version range for compatibility matching.

    Example:
        >>> og = registry.get_by_id("FO4_OG")
        >>> if og.compatible_range:
        ...     print(og.compatible_range.min_version)

    """

    @property
    def min_version(self) -> str:
        """Minimum version string (inclusive)."""

    @property
    def max_version(self) -> str:
        """Maximum version string (inclusive)."""

    def contains(self, version_str: str) -> bool:
        """Check if a version string falls within this range.

        Args:
            version_str: Version string to check.

        Returns:
            True if the version is within the range (inclusive).

        Raises:
            ValueError: If the version string is invalid.

        """

class CrashgenConfig:
    """Crash generator configuration for a specific version.

    Example:
        >>> configs = registry.get_crashgen_configs("FO4_OG")
        >>> for c in configs:
        ...     print(f"{c.name} v{c.version}")

    """

    @property
    def version(self) -> str:
        """Version string of the crash generator (e.g., "1.28.6")."""

    @property
    def name(self) -> str:
        """Display name (e.g., "Buffout 4")."""

    @property
    def acronym(self) -> str:
        """Short identifier/acronym (e.g., "BO4", "BO4 NG")."""

    @property
    def dll_file(self) -> str:
        """DLL filename (e.g., "buffout4.dll")."""

    @property
    def description(self) -> str:
        """Description of this crash generator version."""

    @property
    def download_url(self) -> str:
        """Nexus Mods or other download URL."""

    @property
    def compatible_range(self) -> CompatibleRange | None:
        """Optional game version range restriction."""

    def is_compatible_with(self, version_str: str) -> bool:
        """Check if this crash generator is compatible with a game version.

        Args:
            version_str: Game version string to check.

        Returns:
            True if compatible (or no range restriction).

        Raises:
            ValueError: If the version string is invalid.

        """

class UnknownVersionHandling:
    """Configuration for handling unknown/unsupported versions.

    Example:
        >>> handling = registry.unknown_version_handling
        >>> print(handling.strategy)
        nearest_match

    """

    @property
    def strategy(self) -> str:
        """Matching strategy ("nearest_match", "strict", or "default_only")."""

    @property
    def log_level(self) -> str:
        """Log level for warnings ("debug", "warning", or "error")."""

    @property
    def defaults(self) -> dict[str, str]:
        """All defaults as a dictionary."""

    def get_default(self, game: str) -> str | None:
        """Get the default version ID for a game.

        Args:
            game: Game identifier (e.g., "Fallout4").

        Returns:
            Default version ID string, or None.

        """

class MatchConfidence:
    """Confidence level for version matching results.

    Values:
        EXACT: Exact version match found in registry.
        RANGE: Version falls within a defined compatible_range.
        NEAREST: Matched to nearest known version by semantic distance.
        DEFAULT: Using default fallback version for the game.
        UNKNOWN: No suitable match found.

    Example:
        >>> result = registry.match_version("1.10.163.0", "Fallout4", False)
        >>> result.confidence == MatchConfidence.EXACT
        True

    """

    EXACT: str
    RANGE: str
    NEAREST: str
    DEFAULT: str
    UNKNOWN: str

    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence match (Exact or Range)."""

    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class MatchResult:
    """Result of version matching.

    Example:
        >>> result = registry.match_version("1.10.163.0", "Fallout4", False)
        >>> result.is_exact
        True
        >>> result.version_info.id
        'FO4_OG'

    """

    @property
    def version_info(self) -> VersionInfo | None:
        """The matched VersionInfo, or None."""

    @property
    def confidence(self) -> str:
        """Confidence level string ("exact", "range", "nearest", "default", "unknown")."""

    @property
    def confidence_enum(self) -> MatchConfidence:
        """Confidence level as a MatchConfidence object."""

    @property
    def detected(self) -> str:
        """The originally detected version string."""

    @property
    def message(self) -> str:
        """Human-readable message about the match."""

    @property
    def is_exact(self) -> bool:
        """Whether this was an exact match."""

    @property
    def is_fallback(self) -> bool:
        """Whether this was a fallback match (Nearest, Default, or Unknown)."""

    @property
    def should_warn(self) -> bool:
        """Whether the user should be warned about this match."""

    @property
    def is_valid(self) -> bool:
        """Whether this is a valid match (version_info present and not Unknown)."""

class VersionInfo:
    """Complete version information for a game version.

    Example:
        >>> og = registry.get_by_id("FO4_OG")
        >>> print(og.display_name)
        Fallout 4 Original
        >>> print(og.version)
        1.10.163.0

    """

    @property
    def id(self) -> str:
        """Unique identifier (e.g., "FO4_OG", "FO4_NG", "FO4_VR")."""

    @property
    def game(self) -> str:
        """Game identifier (e.g., "Fallout4")."""

    @property
    def is_vr(self) -> bool:
        """Whether this is a VR version."""

    @property
    def version(self) -> str:
        """Version string (e.g., "1.10.163.0")."""

    @property
    def version_string(self) -> str:
        """Version string (alias for compatibility)."""

    @property
    def display_name(self) -> str:
        """Human-readable display name."""

    @property
    def short_name(self) -> str:
        """Short identifier (e.g., "OG", "NG", "VR")."""

    @property
    def description(self) -> str:
        """Description of this version."""

    @property
    def address_library(self) -> AddressLibraryConfig | None:
        """Address Library configuration, if applicable."""

    @property
    def xse(self) -> XseConfig | None:
        """Script Extender configuration, if applicable."""

    @property
    def compatible_range(self) -> CompatibleRange | None:
        """Version range for matching, if applicable."""

    @property
    def priority(self) -> int:
        """Priority for matching (higher = preferred)."""

    @property
    def deprecated(self) -> bool:
        """Whether this version is deprecated."""

    @property
    def docs_name(self) -> str:
        """My Documents subfolder name (e.g., "Fallout4", "Fallout4VR")."""

    @property
    def steam_id(self) -> int:
        """Steam application ID (e.g., 377160, 611660)."""

    @property
    def exe_hash(self) -> str | None:
        """SHA-256 hash of the game executable, or None."""

    @property
    def crashgen_versions(self) -> list[CrashgenConfig]:
        """List of CrashgenConfig objects."""

    def get_crashgen_version_strings(self) -> list[str]:
        """Get crash generator versions as simple version strings.

        Returns:
            List of version strings.

        """

    def get_crashgen_for_version(self, crashgen_version: str) -> CrashgenConfig | None:
        """Get a specific CrashgenConfig by its version string.

        Args:
            crashgen_version: The crash generator version to look up.

        Returns:
            The CrashgenConfig, or None if not found.

        """

    def get_compatible_crashgens(
        self, game_version_str: str | None = None
    ) -> list[CrashgenConfig]:
        """Get crash generators compatible with a specific game version.

        Args:
            game_version_str: Game version string, or None to use this version's own version.

        Returns:
            List of compatible CrashgenConfig objects.

        Raises:
            ValueError: If the game version string is invalid.

        """

    def is_compatible_with(self, version_str: str) -> bool:
        """Check if a detected version is compatible with this version.

        Args:
            version_str: Detected version string to check.

        Returns:
            True if compatible.

        Raises:
            ValueError: If the version string is invalid.

        """

    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class VersionRegistry:
    """Singleton version registry for game version metadata.

    The registry is automatically initialized on first access and loads
    version data from YAML configuration with fallback to hardcoded defaults.

    Example:
        >>> import classic_version_registry
        >>> registry = classic_version_registry.VersionRegistry()
        >>> og = registry.get_by_id("FO4_OG")
        >>> print(og.display_name)
        Fallout 4 Original

    """

    def __init__(self) -> None:
        """Create a VersionRegistry instance.

        This is a lightweight handle to the Rust singleton -- no data is
        copied. Multiple instances share the same underlying registry.

        """

    # === Lookup API ===

    def get_by_id(self, version_id: str) -> VersionInfo | None:
        """Get version info by ID.

        Args:
            version_id: The version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR").

        Returns:
            The VersionInfo, or None if not found.

        """

    def get_by_version(self, version_str: str) -> VersionInfo | None:
        """Get version info by exact version string.

        Args:
            version_str: The exact game version string (e.g., "1.10.163.0").

        Returns:
            The VersionInfo, or None if not found.

        Raises:
            ValueError: If the version string is invalid.

        """

    def get_by_short_name(self, short_name: str) -> VersionInfo | None:
        """Get version info by short name.

        Args:
            short_name: The short name (e.g., "OG", "NG", "VR").

        Returns:
            The VersionInfo, or None if not found.

        """

    # === Filtering API ===

    def get_all(self) -> list[VersionInfo]:
        """Get all registered versions, sorted by priority (descending).

        Returns:
            List of VersionInfo objects.

        """

    def get_all_for_game(
        self, game: str, is_vr: bool | None = None
    ) -> list[VersionInfo]:
        """Get all versions for a specific game.

        Args:
            game: Game identifier (e.g., "Fallout4").
            is_vr: Optional VR filter. If None, returns all versions.

        Returns:
            List of matching VersionInfo objects, sorted by priority (descending).

        """

    def get_correct_versions(self, is_vr: bool) -> list[VersionInfo]:
        """Get correct versions for current mode (VR or non-VR).

        Args:
            is_vr: Whether VR mode is active.

        Returns:
            List of versions matching the VR mode.

        """

    def get_wrong_versions(self, is_vr: bool) -> list[VersionInfo]:
        """Get wrong versions for current mode (opposite of is_vr).

        Args:
            is_vr: Whether VR mode is active.

        Returns:
            List of versions NOT matching the VR mode.

        """

    # === Matching API ===

    def match_version(
        self,
        version_str: str,
        game: str = "Fallout4",
        is_vr: bool = False,
    ) -> MatchResult:
        """Match a detected version string to the registry.

        Uses intelligent matching with fallback:
        1. Exact match
        2. Compatible range match
        3. Nearest match (same major version)
        4. Default fallback

        Args:
            version_str: Detected game version string (e.g., "1.10.163.0").
            game: Game identifier (default: "Fallout4").
            is_vr: Whether VR mode is active (default: False).

        Returns:
            MatchResult with matched version and confidence level.

        Raises:
            ValueError: If the version string is invalid.

        """

    def get_address_library_filename(
        self, version_str: str, is_vr: bool = False
    ) -> str | None:
        """Get Address Library filename for a version.

        Args:
            version_str: Game version string.
            is_vr: Whether VR mode is active (default: False).

        Returns:
            The Address Library filename, or None.

        Raises:
            ValueError: If the version string is invalid.

        """

    # === Crashgen API ===

    def get_crashgen_configs(self, version_id: str) -> list[CrashgenConfig]:
        """Get crash generator configurations for a version ID.

        Args:
            version_id: The version ID (e.g., "FO4_OG").

        Returns:
            List of CrashgenConfig objects.

        """

    def get_crashgen_versions(self, version_id: str) -> list[str]:
        """Get crash generator versions as simple version strings.

        Args:
            version_id: The version ID (e.g., "FO4_OG").

        Returns:
            List of version strings.

        """

    def get_crashgen_for_version(
        self, version_id: str, crashgen_version: str
    ) -> CrashgenConfig | None:
        """Get a specific crash generator by version ID and crashgen version.

        Args:
            version_id: The version ID (e.g., "FO4_OG").
            crashgen_version: The crash generator version (e.g., "1.28.6").

        Returns:
            The CrashgenConfig, or None if not found.

        """

    # === Hash API ===

    def get_all_exe_hashes(
        self, game: str = "Fallout4", is_vr: bool | None = None
    ) -> set[str]:
        """Get all known exe hashes for a game.

        Args:
            game: Game identifier (default: "Fallout4").
            is_vr: Optional VR filter. If None, returns all versions.

        Returns:
            Set of valid SHA-256 hashes.

        """

    def get_all_script_hashes(
        self, game: str = "Fallout4", is_vr: bool | None = None
    ) -> dict[str, set[str]]:
        """Get all valid script hashes for all versions of a game.

        Args:
            game: Game identifier (default: "Fallout4").
            is_vr: Optional VR filter. If None, returns all versions.

        Returns:
            Dictionary mapping script filenames to sets of valid SHA-256 hashes.

        """

    def get_script_hashes_for_version(self, version_id: str) -> dict[str, str]:
        """Get script hashes for a specific version.

        Args:
            version_id: The version ID (e.g., "FO4_OG").

        Returns:
            Dictionary mapping script filenames to expected SHA-256 hashes.
            Empty dict if version not found or has no script hashes.

        """

    # === Unknown Version Handling ===

    @property
    def unknown_version_handling(self) -> UnknownVersionHandling:
        """Gets the unknown version handling configuration."""

def match_version_string(
    version_str: str,
    game: str = "Fallout4",
    is_vr: bool = False,
) -> MatchResult:
    """Match a version string to the registry.

    This is a module-level function that creates a temporary registry handle
    and delegates to it. Useful for one-off matching without holding a reference.

    Args:
        version_str: Detected game version string (e.g., "1.10.163.0").
        game: Game identifier (default: "Fallout4").
        is_vr: Whether VR mode is active (default: False).

    Returns:
        MatchResult with matched version and confidence level.

    Raises:
        ValueError: If the version string is invalid.

    """

def get_version_registry() -> VersionRegistry:
    """Get the singleton registry instance.

    Returns:
        A VersionRegistry instance (lightweight handle to Rust singleton).

    """

"""VersionRegistry - Data-driven game version management.

This module provides a YAML-driven version registry that allows adding new game
versions without code changes. Version metadata is loaded from the Version_Registry
section of CLASSIC Main.yaml.

Key Components:
    - VersionRegistry: Singleton that loads and manages version metadata
    - VersionInfo: Complete information about a game version
    - AddressLibraryConfig: Address Library file configuration
    - XseConfig: Script Extender configuration
    - VersionMatcher: Intelligent version matching with fallback strategies
    - MatchResult: Result of version matching with confidence levels

Basic Usage:
    >>> from ClassicLib.VersionRegistry import get_version_registry
    >>> registry = get_version_registry()
    >>> og = registry.get_by_id("FO4_OG")
    >>> print(og.address_library.filename)
    version-1-10-163-0.bin

Matching Unknown Versions:
    >>> from packaging.version import Version
    >>> from ClassicLib.VersionRegistry import get_version_registry
    >>> registry = get_version_registry()
    >>> result = registry.match_version(Version("1.10.500.0"), "Fallout4", is_vr=False)
    >>> if result.should_warn:
    ...     print(f"Warning: {result.message}")
    >>> print(result.version_info.display_name)
    Fallout 4 Next-Gen

Adding New Versions:
    To add a new game version, edit CLASSIC Main.yaml and add an entry to
    the Version_Registry.versions list:

    ```yaml
    Version_Registry:
      versions:
        - id: FO4_NEW_PATCH
          game: Fallout4
          is_vr: false
          version: "1.10.999.0"
          display_name: Fallout 4 New Patch
          short_name: PATCH
          address_library:
            filename: version-1-10-999-0.bin
            format: bin
          xse:
            acronym: F4SE
            compatible_version: "0.7.3"
          compatible_range:
            min: "1.10.999.0"
            max: "1.10.999.999"
          priority: 300
    ```

    No code changes are required - the registry automatically loads new versions.
"""

from ClassicLib.support.versions.core import (
    VersionRegistry,
    get_detected_version_info,
    get_version_registry,
)
from ClassicLib.support.versions.crashgen_checker import (
    CrashgenVersionResult,
    CrashgenVersionStatus,
    check_crashgen_version,
    check_crashgen_version_for_detected_game,
    get_matching_crashgen_config,
)
from ClassicLib.support.versions.matching import (
    MatchConfidence,
    MatchResult,
    VersionMatcher,
)
from ClassicLib.support.versions.models import (
    AddressLibraryConfig,
    CompatibleRange,
    CrashgenConfig,
    UnknownVersionHandling,
    VersionInfo,
    XseConfig,
)

__all__ = [
    # Core registry
    "VersionRegistry",
    "get_version_registry",
    "get_detected_version_info",
    # Data models
    "VersionInfo",
    "AddressLibraryConfig",
    "XseConfig",
    "CompatibleRange",
    "CrashgenConfig",
    "UnknownVersionHandling",
    # Matching
    "VersionMatcher",
    "MatchResult",
    "MatchConfidence",
    # Crashgen version checking
    "CrashgenVersionStatus",
    "CrashgenVersionResult",
    "check_crashgen_version",
    "check_crashgen_version_for_detected_game",
    "get_matching_crashgen_config",
]

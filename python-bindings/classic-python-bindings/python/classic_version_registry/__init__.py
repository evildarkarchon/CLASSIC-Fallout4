"""Python module for CLASSIC version registry.

Provides game version detection, matching, and registry lookup
powered by Rust for performance and reliability.

Core Classes:
    VersionRegistry: this module's registry snapshot for game version metadata
    GameVersion: 4-component game version (major.minor.patch.build)
    VersionInfo: Complete version information for a game version
    MatchResult: Result of version matching with confidence level
    MatchConfidence: Confidence level enum for version matching

Example:
    >>> import classic_version_registry
    >>> registry = classic_version_registry.VersionRegistry()
    >>> og = registry.get_by_id("FO4_OG")
    >>> print(og.version)
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_version_registry import (
    AddressLibraryConfig,
    CompatibleRange,
    CrashgenConfig,
    Fallout4Version,
    GameVersion,
    MatchConfidence,
    MatchResult,
    NULL_VERSION,
    UnknownVersionHandling,
    VersionInfo,
    VersionRegistry,
    XseConfig,
    __debug_registered__,
    __version__,
    get_version_registry,
    match_version_string,
)

__all__ = [
    "AddressLibraryConfig",
    "CompatibleRange",
    "CrashgenConfig",
    "Fallout4Version",
    "GameVersion",
    "MatchConfidence",
    "MatchResult",
    "NULL_VERSION",
    "UnknownVersionHandling",
    "VersionInfo",
    "VersionRegistry",
    "XseConfig",
    "__debug_registered__",
    "__version__",
    "get_version_registry",
    "match_version_string",
]

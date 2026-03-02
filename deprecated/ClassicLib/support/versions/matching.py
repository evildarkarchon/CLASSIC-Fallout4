"""Version matching algorithms -- delegates to Rust via classic_version_registry.

This module provides the MatchConfidence enum and MatchResult dataclass for
version matching results. The actual matching logic now lives in Rust; the
VersionMatcher class is a thin delegation wrapper for backward compatibility.

Example:
    >>> from ClassicLib.support.versions.matching import MatchConfidence
    >>> from ClassicLib.support.versions import get_version_registry
    >>> registry = get_version_registry()
    >>> result = registry.match_version(Version("1.10.163.0"), "Fallout4", is_vr=False)
    >>> result.confidence
    MatchConfidence.EXACT

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import classic_version_registry as _rust

if TYPE_CHECKING:
    from packaging.version import Version

    from ClassicLib.support.versions.core import VersionRegistry
    from ClassicLib.support.versions.models import VersionInfo


class MatchConfidence(Enum):
    """Confidence level for version match.

    Attributes:
        EXACT: Exact version match.
        RANGE: Version falls within a defined compatible range.
        NEAREST: Matched to nearest known version by distance calculation.
        DEFAULT: Using default fallback for the game.
        UNKNOWN: No match found at all.

    """

    EXACT = auto()
    RANGE = auto()
    NEAREST = auto()
    DEFAULT = auto()
    UNKNOWN = auto()


# Map Rust confidence strings to our enum values
_CONFIDENCE_MAP: dict[str, MatchConfidence] = {
    "exact": MatchConfidence.EXACT,
    "range": MatchConfidence.RANGE,
    "nearest": MatchConfidence.NEAREST,
    "default": MatchConfidence.DEFAULT,
    "unknown": MatchConfidence.UNKNOWN,
}


@dataclass
class MatchResult:
    """Result of version matching.

    Can be constructed from a Rust PyMatchResult or directly (for tests).

    Attributes:
        version_info: Matched VersionInfo (may be None if UNKNOWN).
        confidence: How confident the match is.
        detected: Original detected version.
        message: Human-readable explanation of the match.

    """

    version_info: VersionInfo | None
    confidence: MatchConfidence
    detected: Version
    message: str = ""

    @property
    def is_exact(self) -> bool:
        """Check if this was an exact match."""
        return self.confidence == MatchConfidence.EXACT

    @property
    def is_fallback(self) -> bool:
        """Check if this was a fallback match."""
        return self.confidence in {
            MatchConfidence.NEAREST,
            MatchConfidence.DEFAULT,
            MatchConfidence.UNKNOWN,
        }

    @property
    def should_warn(self) -> bool:
        """Check if user should be warned about this match."""
        return self.confidence in {
            MatchConfidence.NEAREST,
            MatchConfidence.DEFAULT,
        }

    @property
    def is_valid(self) -> bool:
        """Check if a valid version was matched."""
        return self.version_info is not None and self.confidence != MatchConfidence.UNKNOWN

    @classmethod
    def _from_rust(cls, rust_result: _rust.MatchResult, detected: Version) -> MatchResult:
        """Create a MatchResult from a Rust PyMatchResult."""
        from ClassicLib.support.versions.models import VersionInfo

        confidence = _CONFIDENCE_MAP.get(rust_result.confidence, MatchConfidence.UNKNOWN)

        rust_vi = rust_result.version_info
        version_info: VersionInfo | None = None
        if rust_vi is not None:
            version_info = VersionInfo(_rust_obj=rust_vi)

        return cls(
            version_info=version_info,
            confidence=confidence,
            detected=detected,
            message=rust_result.message,
        )


class VersionMatcher:
    """Intelligent version matching -- delegates to Rust.

    Preserved for backward compatibility. The actual matching logic now
    runs in Rust via the classic_version_registry binding.

    """

    def __init__(self, registry: VersionRegistry) -> None:  # noqa: ARG002
        self._rust_registry = _rust.VersionRegistry()

    def match(
        self,
        detected: Version,
        game: str = "Fallout4",
        is_vr: bool = False,
    ) -> MatchResult:
        """Match detected version to a known version in the registry."""
        rust_result = self._rust_registry.match_version(str(detected), game, is_vr)
        return MatchResult._from_rust(rust_result, detected)

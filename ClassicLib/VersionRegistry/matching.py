"""Version matching algorithms with graceful degradation.

This module provides intelligent matching of detected game versions to known
versions in the registry, with configurable fallback strategies for unknown
versions.

The matching algorithm follows this priority order:
1. Exact match - Version string matches exactly
2. Range match - Version falls within a defined compatible_range
3. Nearest match - Same major version, closest minor/patch
4. Default fallback - Use highest priority version for the game

Example:
    >>> from ClassicLib.VersionRegistry.matching import VersionMatcher, MatchConfidence
    >>> from ClassicLib.VersionRegistry import get_version_registry
    >>> registry = get_version_registry()
    >>> matcher = VersionMatcher(registry)
    >>> result = matcher.match(Version("1.10.163.0"), "Fallout4", is_vr=False)
    >>> result.confidence
    <MatchConfidence.EXACT: 1>

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from packaging.version import Version

    from ClassicLib.VersionRegistry.core import VersionRegistry
    from ClassicLib.VersionRegistry.models import VersionInfo


class MatchConfidence(Enum):
    """Confidence level for version match.

    Indicates how confident the matching algorithm is about the result.
    Higher confidence means a more reliable match.

    Attributes:
        EXACT: Exact version match - highest confidence.
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


@dataclass
class MatchResult:
    """Result of version matching.

    Contains the matched version information along with metadata about
    the match quality and any relevant messages for the user.

    Attributes:
        version_info: Matched VersionInfo (may be None if UNKNOWN).
        confidence: How confident the match is.
        detected: Original detected version.
        message: Human-readable explanation of the match.

    Example:
        >>> result = MatchResult(
        ...     version_info=some_version_info,
        ...     confidence=MatchConfidence.EXACT,
        ...     detected=Version("1.10.163.0"),
        ...     message="Exact match: Fallout 4 Original"
        ... )
        >>> result.is_exact
        True
        >>> result.should_warn
        False

    """

    version_info: VersionInfo | None
    confidence: MatchConfidence
    detected: Version
    message: str = ""

    @property
    def is_exact(self) -> bool:
        """Check if this was an exact match.

        Returns:
            True if the match confidence is EXACT, False otherwise.

        """
        return self.confidence == MatchConfidence.EXACT

    @property
    def is_fallback(self) -> bool:
        """Check if this was a fallback match.

        A fallback match is one where the detected version was not found
        directly and a best-effort match was made.

        Returns:
            True if this was a fallback match (NEAREST, DEFAULT, or UNKNOWN).

        """
        return self.confidence in {
            MatchConfidence.NEAREST,
            MatchConfidence.DEFAULT,
            MatchConfidence.UNKNOWN,
        }

    @property
    def should_warn(self) -> bool:
        """Check if user should be warned about this match.

        Warnings are appropriate when the match is not exact or within
        a defined range, indicating potential compatibility issues.

        Returns:
            True if the user should be warned about this match.

        """
        return self.confidence in {
            MatchConfidence.NEAREST,
            MatchConfidence.DEFAULT,
        }

    @property
    def is_valid(self) -> bool:
        """Check if a valid version was matched.

        Returns:
            True if version_info is not None and confidence is not UNKNOWN.

        """
        return self.version_info is not None and self.confidence != MatchConfidence.UNKNOWN


class VersionMatcher:
    """Intelligent version matching with multiple fallback strategies.

    The matcher tries to find the best matching version for a detected
    game version, using the following order of preference:
    1. Exact version match
    2. Compatible range match
    3. Nearest major.minor version
    4. Default fallback for game

    Attributes:
        registry: The VersionRegistry instance to match against.

    Example:
        >>> from ClassicLib.VersionRegistry import get_version_registry
        >>> registry = get_version_registry()
        >>> matcher = VersionMatcher(registry)
        >>> result = matcher.match(Version("1.10.500.0"), "Fallout4", False)
        >>> result.confidence
        <MatchConfidence.NEAREST: 3>

    """

    def __init__(self, registry: VersionRegistry) -> None:
        """Initialize the VersionMatcher.

        Args:
            registry: The VersionRegistry instance to use for matching.

        """
        self._registry: VersionRegistry = registry

    def match(
        self,
        detected: Version,
        game: str = "Fallout4",
        is_vr: bool = False,
    ) -> MatchResult:
        """Match detected version to a known version in the registry.

        Attempts to find the best match for the detected version using
        multiple strategies in order of preference.

        Args:
            detected: The detected game version to match.
            game: Game identifier (e.g., "Fallout4").
            is_vr: Whether VR mode is active.

        Returns:
            MatchResult containing the matched version and confidence level.

        """
        # 1. Try exact match
        exact = self._registry.get_by_version(detected)
        if exact and exact.game == game and exact.is_vr == is_vr:
            return MatchResult(
                version_info=exact,
                confidence=MatchConfidence.EXACT,
                detected=detected,
                message=f"Exact match: {exact.display_name}",
            )

        # 2. Try compatible range match
        candidates = self._registry.get_all_for_game(game, is_vr)
        for candidate in candidates:
            if candidate.is_compatible_with(detected):
                return MatchResult(
                    version_info=candidate,
                    confidence=MatchConfidence.RANGE,
                    detected=detected,
                    message=f"Range match: {candidate.display_name} (compatible with {detected})",
                )

        # 3. Try nearest major.minor match
        nearest = self._find_nearest(detected, candidates)
        if nearest:
            logger.warning(f"Unknown version {detected} matched to nearest: {nearest.display_name}")
            return MatchResult(
                version_info=nearest,
                confidence=MatchConfidence.NEAREST,
                detected=detected,
                message=f"Nearest match: {nearest.display_name} (detected: {detected})",
            )

        # 4. Use default fallback
        if candidates:
            default = candidates[0]  # Highest priority (sorted by priority desc)
            logger.warning(f"Unknown version {detected} using default: {default.display_name}")
            return MatchResult(
                version_info=default,
                confidence=MatchConfidence.DEFAULT,
                detected=detected,
                message=f"Default fallback: {default.display_name} (detected: {detected})",
            )

        # 5. No match found
        logger.error(f"No version match found for {detected}")
        return MatchResult(
            version_info=None,
            confidence=MatchConfidence.UNKNOWN,
            detected=detected,
            message=f"No matching version found for {detected}",
        )

    def _find_nearest(  # noqa: PLR6301
        self,
        detected: Version,
        candidates: Sequence[VersionInfo],
    ) -> VersionInfo | None:
        """Find nearest version by semantic distance calculation.

        The distance is calculated as:
        - Major version difference * 1,000,000
        - Minor version difference * 1,000
        - Patch version difference * 1

        This ensures major version differences are heavily weighted.

        Args:
            detected: The detected version to find a match for.
            candidates: List of candidate versions to search.

        Returns:
            The nearest matching VersionInfo, or None if no reasonable match.

        """
        if not candidates:
            return None

        def distance(v: Version) -> float:
            """Calculate semantic version distance."""
            d_major = abs(detected.major - v.major) * 1_000_000
            d_minor = abs(detected.minor - v.minor) * 1_000
            d_patch = abs(detected.micro - v.micro)
            return d_major + d_minor + d_patch

        # Sort by distance, then by priority (higher priority = lower sort key)
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (distance(c.version), -c.priority),
        )

        # Only return if reasonably close (same major version)
        best = sorted_candidates[0]
        if best.version.major == detected.major:
            return best

        return None

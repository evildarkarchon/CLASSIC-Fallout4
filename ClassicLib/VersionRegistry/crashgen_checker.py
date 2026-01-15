"""Crash generator version validation utilities.

This module provides utilities for validating crash generator versions against
the valid versions defined in the VersionRegistry. It replaces the legacy
single-version comparison with a list-based approach that handles multiple
valid versions per game version (e.g., FO4_OG supports both 1.28.6 and 1.37.0).

Example:
    >>> from ClassicLib.VersionRegistry.crashgen_checker import (
    ...     CrashgenVersionStatus,
    ...     check_crashgen_version,
    ... )
    >>> from packaging.version import Version
    >>> result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
    >>> result.status
    <CrashgenVersionStatus.VALID: 'valid'>

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from packaging.version import Version


class CrashgenVersionStatus(Enum):
    """Status of a crash generator version relative to valid versions.

    Attributes:
        VALID: The version is in the list of valid versions.
        OUTDATED: The version is older than all valid versions.
        NEWER_THAN_KNOWN: The version is newer than the highest known valid version.
        NO_SUPPORTED_VERSION: No crash generator is supported for this game version.
        UNKNOWN_GAME_VERSION: The game version ID was not found in the registry.

    """

    VALID = "valid"
    OUTDATED = "outdated"
    NEWER_THAN_KNOWN = "newer_than_known"
    NO_SUPPORTED_VERSION = "no_supported_version"
    UNKNOWN_GAME_VERSION = "unknown_game_version"


@dataclass(frozen=True)
class CrashgenVersionResult:
    """Result of crash generator version validation.

    Attributes:
        status: The validation status.
        detected_version: The detected crash generator version.
        valid_versions: Tuple of valid versions for the game version.
        game_version_id: The game version ID used for validation.
        message: Human-readable message describing the result.

    Example:
        >>> result = CrashgenVersionResult(
        ...     status=CrashgenVersionStatus.VALID,
        ...     detected_version=Version("1.28.6"),
        ...     valid_versions=("1.28.6", "1.37.0"),
        ...     game_version_id="FO4_OG",
        ...     message="You have a valid version of Buffout 4!"
        ... )

    """

    status: CrashgenVersionStatus
    detected_version: Version
    valid_versions: tuple[str, ...]
    game_version_id: str
    message: str

    @property
    def is_valid(self) -> bool:
        """Check if the version is valid (either VALID or NEWER_THAN_KNOWN).

        Returns:
            True if the version is valid or newer than known.

        """
        return self.status in {
            CrashgenVersionStatus.VALID,
            CrashgenVersionStatus.NEWER_THAN_KNOWN,
        }

    @property
    def needs_update(self) -> bool:
        """Check if the version needs to be updated.

        Returns:
            True if the version is outdated.

        """
        return self.status == CrashgenVersionStatus.OUTDATED


def check_crashgen_version(
    detected_version: Version,
    game_version_id: str,
    crashgen_name: str = "Buffout 4",
) -> CrashgenVersionResult:
    """Check crash generator version against valid versions for a game version ID.

    This function validates the detected crash generator version against the list
    of valid versions defined in the VersionRegistry for the specified game version.

    Args:
        detected_version: The detected crash generator version (parsed).
        game_version_id: The game version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
        crashgen_name: Name of the crash generator for messages (default: "Buffout 4").

    Returns:
        CrashgenVersionResult with status, valid versions, and message.

    Example:
        >>> from packaging.version import Version
        >>> result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        >>> result.status
        <CrashgenVersionStatus.VALID: 'valid'>
        >>> result = check_crashgen_version(Version("1.26.0"), "FO4_OG")
        >>> result.status
        <CrashgenVersionStatus.OUTDATED: 'outdated'>

    """
    from ClassicLib.VersionRegistry.core import get_version_registry

    registry = get_version_registry()
    valid_versions = registry.get_crashgen_versions(game_version_id)

    return _check_version_against_list(
        detected_version=detected_version,
        valid_versions=valid_versions,
        game_version_id=game_version_id,
        crashgen_name=crashgen_name,
    )


def check_crashgen_version_for_detected_game(
    detected_crashgen: Version,
    detected_game_version: Version,
    is_vr: bool = False,
    crashgen_name: str = "Buffout 4",
) -> CrashgenVersionResult:
    """Check crash generator version for a detected game version.

    This function matches the detected game version to a known version in the
    registry and validates the crash generator version against the valid versions
    for that matched version.

    Args:
        detected_crashgen: The detected crash generator version (parsed).
        detected_game_version: The detected game version (parsed).
        is_vr: Whether VR mode is active.
        crashgen_name: Name of the crash generator for messages.

    Returns:
        CrashgenVersionResult with status, valid versions, and message.

    Example:
        >>> from packaging.version import Version
        >>> result = check_crashgen_version_for_detected_game(
        ...     Version("1.28.6"),
        ...     Version("1.10.163.0"),
        ...     is_vr=False
        ... )
        >>> result.status
        <CrashgenVersionStatus.VALID: 'valid'>

    """
    from ClassicLib.VersionRegistry.core import get_version_registry

    registry = get_version_registry()
    match_result = registry.match_version(detected_game_version, "Fallout4", is_vr)

    if match_result.version_info is None:
        return CrashgenVersionResult(
            status=CrashgenVersionStatus.UNKNOWN_GAME_VERSION,
            detected_version=detected_crashgen,
            valid_versions=(),
            game_version_id="",
            message=f"Unknown game version: {detected_game_version}",
        )

    version_id = match_result.version_info.id
    valid_versions = match_result.version_info.crashgen_versions

    return _check_version_against_list(
        detected_version=detected_crashgen,
        valid_versions=valid_versions,
        game_version_id=version_id,
        crashgen_name=crashgen_name,
    )


def _check_version_against_list(
    detected_version: Version,
    valid_versions: tuple[str, ...],
    game_version_id: str,
    crashgen_name: str,
) -> CrashgenVersionResult:
    """Check a version against a list of valid versions.

    Args:
        detected_version: The detected crash generator version.
        valid_versions: Tuple of valid version strings.
        game_version_id: The game version ID for the result.
        crashgen_name: Name of the crash generator for messages.

    Returns:
        CrashgenVersionResult with appropriate status and message.

    """
    # Handle no supported version case
    if not valid_versions:
        return CrashgenVersionResult(
            status=CrashgenVersionStatus.NO_SUPPORTED_VERSION,
            detected_version=detected_version,
            valid_versions=valid_versions,
            game_version_id=game_version_id,
            message=f"No supported crash log generator for {game_version_id} yet.",
        )

    # Parse valid versions for comparison
    parsed_valid_versions = [Version(v) for v in valid_versions]
    detected_str = str(detected_version)

    # Check if version is in the valid list (exact match)
    if detected_str in valid_versions or detected_version in parsed_valid_versions:
        return CrashgenVersionResult(
            status=CrashgenVersionStatus.VALID,
            detected_version=detected_version,
            valid_versions=valid_versions,
            game_version_id=game_version_id,
            message=f"You have a valid version of {crashgen_name}!",
        )

    # Check if version is newer than all known versions
    max_valid = max(parsed_valid_versions)
    if detected_version > max_valid:
        return CrashgenVersionResult(
            status=CrashgenVersionStatus.NEWER_THAN_KNOWN,
            detected_version=detected_version,
            valid_versions=valid_versions,
            game_version_id=game_version_id,
            message=f"Your {crashgen_name} version ({detected_version}) is newer than known versions.",
        )

    # Version is outdated (older than at least one valid version)
    return CrashgenVersionResult(
        status=CrashgenVersionStatus.OUTDATED,
        detected_version=detected_version,
        valid_versions=valid_versions,
        game_version_id=game_version_id,
        message=f"Your {crashgen_name} is outdated! Please update to a valid version.",
    )

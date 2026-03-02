"""Crash generator version validation utilities.

This module provides utilities for validating crash generator versions against
the valid versions defined in the VersionRegistry. It uses a list-based approach
that handles multiple valid versions per game version (e.g., FO4_OG supports
both Buffout 4 v1.28.6 and Buffout 4 NG v1.37.0).

Data access (crashgen configs, version matching) is backed by the Rust
classic_version_registry binding. The comparison logic (VALID/OUTDATED/NEWER)
remains in Python since it produces Python-typed results consumed by callers.

Example:
    >>> from ClassicLib.support.versions.crashgen_checker import (
    ...     CrashgenVersionStatus,
    ...     check_crashgen_version,
    ...     get_matching_crashgen_config,
    ... )
    >>> from packaging.version import Version
    >>> result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
    >>> result.status
    <CrashgenVersionStatus.VALID: 'valid'>
    >>> result.matched_config.name
    'Buffout 4'

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from packaging.version import Version

if TYPE_CHECKING:
    from ClassicLib.support.versions.models import CrashgenConfig


class CrashgenVersionStatus(Enum):
    """Status of a crash generator version relative to valid versions."""

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
        valid_versions: Tuple of valid version strings for the game version.
        game_version_id: The game version ID used for validation.
        message: Human-readable message describing the result.
        matched_config: The CrashgenConfig that matched the detected version,
            or None if no match was found. Only populated when status is VALID.

    """

    status: CrashgenVersionStatus
    detected_version: Version
    valid_versions: tuple[str, ...]
    game_version_id: str
    message: str
    matched_config: CrashgenConfig | None = None

    @property
    def is_valid(self) -> bool:
        """Check if the version is valid (either VALID or NEWER_THAN_KNOWN)."""
        return self.status in {
            CrashgenVersionStatus.VALID,
            CrashgenVersionStatus.NEWER_THAN_KNOWN,
        }

    @property
    def needs_update(self) -> bool:
        """Check if the version needs to be updated."""
        return self.status == CrashgenVersionStatus.OUTDATED


def check_crashgen_version(
    detected_version: Version,
    game_version_id: str,
    crashgen_name: str = "Buffout 4",
) -> CrashgenVersionResult:
    """Check crash generator version against valid versions for a game version ID.

    Args:
        detected_version: The detected crash generator version (parsed).
        game_version_id: The game version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
        crashgen_name: Name of the crash generator for messages (default: "Buffout 4").

    Returns:
        CrashgenVersionResult with status, valid versions, matched_config, and message.

    """
    from ClassicLib.support.versions.core import get_version_registry

    registry = get_version_registry()
    crashgen_configs = registry.get_crashgen_configs(game_version_id)

    return _check_version_against_configs(detected_version, crashgen_configs, game_version_id, crashgen_name)


def check_crashgen_version_for_detected_game(
    detected_crashgen: Version,
    detected_game_version: Version,
    is_vr: bool = False,
    crashgen_name: str = "Buffout 4",
) -> CrashgenVersionResult:
    """Check crash generator version for a detected game version.

    Matches the detected game version to a known version in the registry,
    then validates the crash generator version against valid versions for
    that matched version.

    Args:
        detected_crashgen: The detected crash generator version (parsed).
        detected_game_version: The detected game version (parsed).
        is_vr: Whether VR mode is active.
        crashgen_name: Name of the crash generator for messages.

    Returns:
        CrashgenVersionResult with status, valid versions, matched_config, and message.

    """
    from ClassicLib.support.versions.core import get_version_registry

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
    crashgen_configs = match_result.version_info.crashgen_versions

    return _check_version_against_configs(detected_crashgen, crashgen_configs, version_id, crashgen_name)


def get_matching_crashgen_config(
    detected_version: Version,
    game_version_id: str,
) -> CrashgenConfig | None:
    """Get the CrashgenConfig matching the detected version.

    Uses the Rust VersionRegistry for O(1) lookup by version string.

    Args:
        detected_version: The detected crash generator version (parsed).
        game_version_id: The game version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR").

    Returns:
        The matching CrashgenConfig, or None if no match found.

    """
    from ClassicLib.support.versions.core import get_version_registry

    registry = get_version_registry()
    version_info = registry.get_by_id(game_version_id)
    if version_info is None:
        return None
    return version_info.get_crashgen_for_version(str(detected_version))


def _check_version_against_configs(
    detected_version: Version,
    crashgen_configs: tuple[CrashgenConfig, ...],
    game_version_id: str,
    crashgen_name: str,
) -> CrashgenVersionResult:
    """Check a version against a tuple of CrashgenConfig objects.

    Args:
        detected_version: The detected crash generator version.
        crashgen_configs: Tuple of CrashgenConfig objects.
        game_version_id: The game version ID for the result.
        crashgen_name: Name of the crash generator for messages.

    Returns:
        CrashgenVersionResult with appropriate status, message, and matched_config.

    """
    valid_versions = tuple(config.version for config in crashgen_configs)

    if not crashgen_configs:
        return CrashgenVersionResult(
            status=CrashgenVersionStatus.NO_SUPPORTED_VERSION,
            detected_version=detected_version,
            valid_versions=valid_versions,
            game_version_id=game_version_id,
            message=f"No supported crash log generator for {game_version_id} yet.",
            matched_config=None,
        )

    # Use string matching (routes through Rust get_crashgen_for_version when available)
    detected_str = str(detected_version)
    matched_config: CrashgenConfig | None = None
    for config in crashgen_configs:
        if config.version == detected_str:
            matched_config = config
            break

    if matched_config is not None:
        display_name = matched_config.name or crashgen_name
        return CrashgenVersionResult(
            status=CrashgenVersionStatus.VALID,
            detected_version=detected_version,
            valid_versions=valid_versions,
            game_version_id=game_version_id,
            message=f"You have a valid version of {display_name}!",
            matched_config=matched_config,
        )

    # Compare against all known versions
    parsed_valid = [Version(config.version) for config in crashgen_configs]
    if detected_version > max(parsed_valid):
        return CrashgenVersionResult(
            status=CrashgenVersionStatus.NEWER_THAN_KNOWN,
            detected_version=detected_version,
            valid_versions=valid_versions,
            game_version_id=game_version_id,
            message=f"Your {crashgen_name} version ({detected_version}) is newer than known versions.",
            matched_config=None,
        )

    return CrashgenVersionResult(
        status=CrashgenVersionStatus.OUTDATED,
        detected_version=detected_version,
        valid_versions=valid_versions,
        game_version_id=game_version_id,
        message=f"Your {crashgen_name} is outdated! Please update to a valid version.",
        matched_config=None,
    )

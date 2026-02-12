"""Core VersionRegistry implementation -- delegates to Rust via classic_version_registry.

The registry is backed by the Rust singleton from classic_version_registry.
All lookup, filtering, and matching operations delegate to Rust. The Python
class preserves the same public API for backward compatibility.

Example:
    >>> from ClassicLib.support.versions.core import get_version_registry
    >>> registry = get_version_registry()
    >>> og = registry.get_by_id("FO4_OG")
    >>> print(og.address_library.filename)
    version-1-10-163-0.bin

"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, ClassVar

import classic_version_registry as _rust

from ClassicLib.support.versions.matching import MatchResult
from ClassicLib.support.versions.models import (
    CrashgenConfig,
    UnknownVersionHandling,
    VersionInfo,
)

if TYPE_CHECKING:
    from packaging.version import Version


class VersionRegistry:
    """Data-driven version registry backed by Rust singleton.

    All methods delegate to the Rust classic_version_registry binding.
    The Python singleton pattern is preserved for API compatibility
    (reset_instance, get_instance).

    """

    _instance: ClassVar[VersionRegistry | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._rust = _rust.VersionRegistry()

    @classmethod
    def get_instance(cls) -> VersionRegistry:
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only)."""
        with cls._lock:
            cls._instance = None

    # === Lookup API ===

    def get_by_id(self, version_id: str) -> VersionInfo | None:
        """Get version info by ID."""
        rust_vi = self._rust.get_by_id(version_id)
        if rust_vi is None:
            return None
        return VersionInfo(_rust_obj=rust_vi)

    def get_by_version(self, version: Version) -> VersionInfo | None:
        """Get version info by exact version match."""
        rust_vi = self._rust.get_by_version(str(version))
        if rust_vi is None:
            return None
        return VersionInfo(_rust_obj=rust_vi)

    def get_by_short_name(self, short_name: str) -> VersionInfo | None:
        """Get version info by short name."""
        rust_vi = self._rust.get_by_short_name(short_name)
        if rust_vi is None:
            return None
        return VersionInfo(_rust_obj=rust_vi)

    # === Matching API ===

    def match_version(
        self,
        detected: Version,
        game: str = "Fallout4",
        is_vr: bool = False,
    ) -> MatchResult:
        """Match a detected version to registry, with graceful fallback."""
        rust_result = self._rust.match_version(str(detected), game, is_vr)
        return MatchResult._from_rust(rust_result, detected)

    # === Filtering API ===

    def get_all(self) -> list[VersionInfo]:
        """Get all registered versions, sorted by priority (descending)."""
        return [VersionInfo(_rust_obj=v) for v in self._rust.get_all()]

    def get_all_for_game(
        self,
        game: str,
        is_vr: bool | None = None,
    ) -> list[VersionInfo]:
        """Get all versions for a specific game."""
        return [VersionInfo(_rust_obj=v) for v in self._rust.get_all_for_game(game, is_vr)]

    def get_correct_versions(self, is_vr: bool) -> list[VersionInfo]:
        """Get correct versions for current mode (VR or non-VR)."""
        return [VersionInfo(_rust_obj=v) for v in self._rust.get_correct_versions(is_vr)]

    def get_wrong_versions(self, is_vr: bool) -> list[VersionInfo]:
        """Get wrong versions for current mode (opposite of is_vr)."""
        return [VersionInfo(_rust_obj=v) for v in self._rust.get_wrong_versions(is_vr)]

    # === Hash API ===

    def get_all_exe_hashes(self, game: str = "Fallout4", is_vr: bool | None = None) -> set[str]:
        """Get all known exe hashes for a game."""
        return self._rust.get_all_exe_hashes(game, is_vr)

    def get_all_script_hashes(self, game: str = "Fallout4", is_vr: bool | None = None) -> dict[str, set[str]]:
        """Get all valid script hashes for all versions of a game."""
        return self._rust.get_all_script_hashes(game, is_vr)

    @staticmethod
    def get_script_hashes_for_version(version_info: VersionInfo | None) -> dict[str, str]:
        """Get script hashes for a specific game version."""
        if version_info is None or version_info.xse is None:
            return {}
        return dict(version_info.xse.script_hashes)

    # === Address Library API ===

    def get_address_library_filename(
        self,
        version: Version,
        is_vr: bool = False,
    ) -> str | None:
        """Get Address Library filename for a version."""
        return self._rust.get_address_library_filename(str(version), is_vr)

    # === Crashgen API ===

    def get_crashgen_versions(self, version_id: str) -> tuple[str, ...]:
        """Get valid crash generator version strings for a game version ID."""
        return tuple(self._rust.get_crashgen_versions(version_id))

    def get_crashgen_configs(self, version_id: str) -> tuple[CrashgenConfig, ...]:
        """Get crash generator configurations for a game version ID."""
        return tuple(CrashgenConfig(_rust_obj=c) for c in self._rust.get_crashgen_configs(version_id))

    def get_crashgen_versions_for_detected(
        self,
        detected: Version,
        game: str = "Fallout4",
        is_vr: bool = False,
    ) -> tuple[str, ...]:
        """Get valid crash generator versions for a detected game version."""
        result = self.match_version(detected, game, is_vr)
        if result.version_info is None:
            return ()
        return result.version_info.get_crashgen_version_strings()

    def get_crashgen_configs_for_detected(
        self,
        detected: Version,
        game: str = "Fallout4",
        is_vr: bool = False,
    ) -> tuple[CrashgenConfig, ...]:
        """Get crash generator configurations for a detected game version."""
        result = self.match_version(detected, game, is_vr)
        if result.version_info is None:
            return ()
        return result.version_info.crashgen_versions

    @property
    def unknown_version_handling(self) -> UnknownVersionHandling:
        """Get the configuration for unknown version handling."""
        return UnknownVersionHandling(_rust_obj=self._rust.unknown_version_handling)


def get_version_registry() -> VersionRegistry:
    """Get the singleton VersionRegistry instance."""
    return VersionRegistry.get_instance()


def get_detected_version_info() -> VersionInfo | None:
    """Get the VersionInfo for the currently detected/configured game version.

    This function determines the game version by:
    1. Checking if the user has explicitly set a version (Original, NextGen, VR)
    2. If "auto", detecting the version from the game executable

    Returns:
        VersionInfo for the detected game version, or None if detection fails.

    """
    from pathlib import Path

    from ClassicLib.core.constants import NULL_VERSION, YAML
    from ClassicLib.core.registry import GlobalRegistry
    from ClassicLib.io.yaml import yaml_settings
    from ClassicLib.Utils.version_utils import read_game_exe_version

    # First check if user has explicitly set a version
    version_info = GlobalRegistry.get_version_info()
    if version_info is not None:
        return version_info

    # Auto mode - detect from game executable
    registry = get_version_registry()
    vr_suffix = GlobalRegistry.get_vr()
    is_vr = vr_suffix == "VR"

    # Get the game executable path
    exe_path_str: str | None = yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_EXE")
    if not exe_path_str:
        return None

    exe_path = Path(exe_path_str)
    if not exe_path.exists():
        return None

    # Get version from executable
    game_version = read_game_exe_version(exe_path)
    if game_version == NULL_VERSION:
        return None

    # Match to known version
    match_result = registry.match_version(game_version, "Fallout4", is_vr=is_vr)
    return match_result.version_info

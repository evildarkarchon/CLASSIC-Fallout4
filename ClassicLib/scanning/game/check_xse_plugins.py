"""Module to verify and ensure the correct Address Library version and plugins compatibility
for specific game setups.

Delegates the core validation to the Rust ``classic_scangame.XseChecker`` for
high-performance file existence checks and message formatting.  Python resolves
paths and settings from YAML, then hands off to Rust.

Legacy types (``AddressLibVersionInfo``, ``ALL_ADDRESS_LIB_INFO``) are preserved
for backward compatibility with callers that inspect version metadata directly.
"""

from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import ItemsView, Iterator, KeysView, ValuesView

from ClassicLib.core.constants import NULL_VERSION, YAML, Version
from ClassicLib.io.yaml import classic_settings, yaml_settings
from ClassicLib.support.versions import VersionInfo, get_version_registry
from ClassicLib.Utils.version_utils import read_game_exe_version


class AddressLibVersionInfo(TypedDict):
    """Structured information about an Address Library version."""

    version_const: Version
    filename: str
    description: str
    url: str


def _version_info_to_address_lib_info(version_info: VersionInfo) -> AddressLibVersionInfo:
    """Convert a VersionInfo from the registry to AddressLibVersionInfo."""
    addr_lib = version_info.address_library
    return {
        "version_const": version_info.version,
        "filename": addr_lib.filename if addr_lib else "",
        "description": version_info.display_name or version_info.description,
        "url": addr_lib.nexus_url if addr_lib else "",
    }


def get_all_address_lib_info() -> dict[str, AddressLibVersionInfo]:
    """Get all Address Library info from the VersionRegistry."""
    registry = get_version_registry()
    return {v.short_name: _version_info_to_address_lib_info(v) for v in registry.get_all() if v.address_library}


# Legacy lazy proxy (preserved for backward compatibility)
_ALL_ADDRESS_LIB_INFO_CACHE: dict[str, AddressLibVersionInfo] | None = None


def _get_all_address_lib_info_lazy() -> dict[str, AddressLibVersionInfo]:
    """Lazy loader for ALL_ADDRESS_LIB_INFO."""
    global _ALL_ADDRESS_LIB_INFO_CACHE  # noqa: PLW0603 - Intentional lazy initialization pattern
    if _ALL_ADDRESS_LIB_INFO_CACHE is None:
        _ALL_ADDRESS_LIB_INFO_CACHE = get_all_address_lib_info()
    return _ALL_ADDRESS_LIB_INFO_CACHE


class _LazyAddressLibInfo:
    """Lazy proxy for ALL_ADDRESS_LIB_INFO dict access."""

    def __getitem__(self, key: str) -> AddressLibVersionInfo:
        return _get_all_address_lib_info_lazy()[key]

    def __contains__(self, key: object) -> bool:
        return key in _get_all_address_lib_info_lazy()

    def __iter__(self) -> "Iterator[str]":
        return iter(_get_all_address_lib_info_lazy())

    @staticmethod
    def keys() -> "KeysView[str]":
        """Return dictionary keys view."""
        return _get_all_address_lib_info_lazy().keys()

    @staticmethod
    def values() -> "ValuesView[AddressLibVersionInfo]":
        """Return dictionary values view."""
        return _get_all_address_lib_info_lazy().values()

    @staticmethod
    def items() -> "ItemsView[str, AddressLibVersionInfo]":
        """Return dictionary items view."""
        return _get_all_address_lib_info_lazy().items()

    @staticmethod
    def get(key: str, default: AddressLibVersionInfo | None = None) -> AddressLibVersionInfo | None:
        """Get value by key with optional default."""
        return _get_all_address_lib_info_lazy().get(key, default)


ALL_ADDRESS_LIB_INFO: dict[str, AddressLibVersionInfo] = _LazyAddressLibInfo()  # type: ignore[assignment]


def _determine_relevant_versions(is_vr_mode: bool) -> tuple[list[AddressLibVersionInfo], list[AddressLibVersionInfo]]:
    """Determine correct and wrong address library versions based on VR mode."""
    registry = get_version_registry()

    correct_versions: list[AddressLibVersionInfo] = [
        _version_info_to_address_lib_info(v) for v in registry.get_correct_versions(is_vr_mode) if v.address_library
    ]

    wrong_versions: list[AddressLibVersionInfo] = [
        _version_info_to_address_lib_info(v) for v in registry.get_wrong_versions(is_vr_mode) if v.address_library
    ]

    return correct_versions, wrong_versions


# ---------------------------------------------------------------------------
# Version mapping for Rust XseChecker
# ---------------------------------------------------------------------------

# Known game version strings mapped to Rust GameVersion enum values.
# The Version objects come from read_game_exe_version() as packaging.version.Version.
_GAME_VERSION_THRESHOLDS = {
    "1.2.72": "Vr",
    "1.10.163": "Original",
    "1.10.984": "NextGen",
}


def _detect_rust_game_version(game_version: Version, is_vr: bool) -> str:
    """Map a packaging.version.Version to a Rust GameVersion enum name.

    Returns one of: 'Null', 'Original', 'NextGen', 'AnniversaryEdition', 'Vr'.
    """
    if game_version == NULL_VERSION:
        return "Null"
    if is_vr:
        return "Vr"

    ver_str = str(game_version)
    # Check known version prefixes
    for prefix, rust_name in _GAME_VERSION_THRESHOLDS.items():
        if ver_str.startswith(prefix):
            return rust_name

    # Versions >= 1.11 are Anniversary Edition
    if game_version >= Version("1.11.0"):
        return "AnniversaryEdition"

    # Default to Original for unknown non-VR versions
    return "Original"


def check_xse_plugins() -> str:
    """Check XSE plugins for compatibility via the Rust ``XseChecker``.

    Resolves plugins path, game exe, and VR mode from YAML settings,
    then delegates validation to the Rust backend.

    Returns:
        str: A formatted message with the validation result.

    """
    from classic_scangame import GameVersion as RustGameVersion
    from classic_scangame import XseChecker

    plugins_path: Path | None = yaml_settings(Path, YAML.Game_Local, "Game_Info.Game_Folder_Plugins")

    game_exe_path_str: str | None = yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_EXE")
    if not game_exe_path_str:
        # Rust XseChecker handles VersionNotDetected, but we need plugins_path for it.
        # Fall back to Rust with Null version if we have plugins_path.
        if plugins_path and plugins_path.exists():
            checker = XseChecker(plugins_path, False, RustGameVersion.Null)
            return checker.validate()
        return "❌ ERROR: Could not locate plugins folder path in settings\n-----\n"

    game_version: Version = read_game_exe_version(Path(game_exe_path_str))

    if not plugins_path or not plugins_path.exists():
        if game_version == NULL_VERSION:
            # Create checker with temp path just for VersionNotDetected message
            # Since Rust requires an existing path, use game exe dir as fallback
            checker = XseChecker(Path(game_exe_path_str).parent, False, RustGameVersion.Null)
            return checker.validate()
        return "❌ ERROR: Could not locate plugins folder path in settings\n-----\n"

    is_vr_mode: bool = classic_settings(bool, "VR Mode") or False

    # Map Python Version to Rust GameVersion enum
    rust_version_name = _detect_rust_game_version(game_version, is_vr_mode)
    rust_game_version = getattr(RustGameVersion, rust_version_name)

    checker = XseChecker(plugins_path, is_vr_mode, rust_game_version)
    return checker.validate()

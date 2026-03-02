"""Data models for version registry.

This module re-exports data model types from the Rust classic_version_registry
binding. The Rust types provide the same attribute interface as the original
Python frozen dataclasses.

For callers that construct these types directly (e.g., tests), thin adapter
classes preserve the old constructor signatures.

Example:
    >>> from ClassicLib.support.versions.models import VersionInfo
    >>> registry = get_version_registry()
    >>> og = registry.get_by_id("FO4_OG")
    >>> print(og.version_string)
    1.10.163.0

"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import classic_version_registry as _rust  # noqa: TC002 - used at runtime for _rust_obj access
from packaging.version import Version

if TYPE_CHECKING:
    from typing import Literal


# ---------------------------------------------------------------------------
# AddressLibraryConfig
# ---------------------------------------------------------------------------
class AddressLibraryConfig:
    """Address Library file configuration.

    Wraps the Rust AddressLibraryConfig when returned from the registry, or
    can be constructed directly for testing/defaults.

    Attributes:
        filename: Name of the Address Library file.
        format: File format ("bin" or "csv").
        nexus_url: Download URL for the Address Library on Nexus Mods.

    """

    __slots__ = ("_filename", "_format", "_nexus_url", "_rust_obj")

    def __init__(
        self,
        filename: str = "",
        format: Literal["bin", "csv"] = "bin",  # noqa: A002
        nexus_url: str = "",
        *,
        _rust_obj: _rust.AddressLibraryConfig | None = None,
    ) -> None:
        self._rust_obj = _rust_obj
        self._filename = filename
        self._format = format
        self._nexus_url = nexus_url

    @property
    def filename(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.filename
        return self._filename

    @property
    def format(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.format
        return self._format

    @property
    def nexus_url(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.nexus_url
        return self._nexus_url

    def get_path(self, plugins_dir: Path) -> Path:
        """Get full path to Address Library file."""
        return plugins_dir / self.filename


# ---------------------------------------------------------------------------
# XseConfig
# ---------------------------------------------------------------------------
class XseConfig:
    """Script Extender configuration.

    Attributes:
        acronym: XSE acronym (e.g., "F4SE").
        compatible_version: Compatible XSE version string.
        loader: Loader executable name.
        script_hashes: Tuples of (filename, sha256_hash).
        full_name: Full display name of the script extender (e.g., "Fallout 4 Script Extender").
        file_count: Expected number of XSE files to validate installation.

    """

    __slots__ = ("_acronym", "_compatible_version", "_file_count", "_full_name", "_loader", "_rust_obj", "_script_hashes")

    def __init__(
        self,
        acronym: str = "",
        compatible_version: str = "",
        loader: str = "",
        script_hashes: tuple[tuple[str, str], ...] = (),
        full_name: str = "",
        file_count: int = 0,
        *,
        _rust_obj: _rust.XseConfig | None = None,
    ) -> None:
        self._rust_obj = _rust_obj
        self._acronym = acronym
        self._compatible_version = compatible_version
        self._loader = loader
        self._script_hashes = script_hashes
        self._full_name = full_name
        self._file_count = file_count

    @property
    def acronym(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.acronym
        return self._acronym

    @property
    def compatible_version(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.compatible_version
        return self._compatible_version

    @property
    def loader(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.loader
        return self._loader

    @property
    def script_hashes(self) -> tuple[tuple[str, str], ...]:
        if self._rust_obj is not None:
            return tuple(self._rust_obj.script_hashes)
        return self._script_hashes

    @property
    def full_name(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.full_name
        return self._full_name

    @property
    def file_count(self) -> int:
        if self._rust_obj is not None:
            return self._rust_obj.file_count
        return self._file_count

    @property
    def compatible_version_parsed(self) -> Version:
        """Get the compatible version as a parsed Version object."""
        return Version(self.compatible_version)


# ---------------------------------------------------------------------------
# CompatibleRange
# ---------------------------------------------------------------------------
class CompatibleRange:
    """Version range for compatibility matching.

    Attributes:
        min_version: Minimum version (inclusive).
        max_version: Maximum version (inclusive).

    """

    __slots__ = ("_max_version", "_min_version", "_rust_obj")

    def __init__(
        self,
        min_version: Version | None = None,
        max_version: Version | None = None,
        *,
        _rust_obj: _rust.CompatibleRange | None = None,
    ) -> None:
        self._rust_obj = _rust_obj
        self._min_version = min_version
        self._max_version = max_version

    @property
    def min_version(self) -> Version:
        if self._rust_obj is not None:
            return Version(self._rust_obj.min_version)
        assert self._min_version is not None
        return self._min_version

    @property
    def max_version(self) -> Version:
        if self._rust_obj is not None:
            return Version(self._rust_obj.max_version)
        assert self._max_version is not None
        return self._max_version

    def contains(self, version: Version) -> bool:
        """Check if a version falls within this range (inclusive)."""
        if self._rust_obj is not None:
            return self._rust_obj.contains(str(version))
        return self.min_version <= version <= self.max_version

    @classmethod
    def from_strings(cls, min_str: str, max_str: str) -> CompatibleRange:
        """Create a CompatibleRange from version strings."""
        return cls(min_version=Version(min_str), max_version=Version(max_str))


# ---------------------------------------------------------------------------
# CrashgenConfig
# ---------------------------------------------------------------------------
class CrashgenConfig:
    """Crash generator configuration for a specific version.

    Attributes:
        version: Version string of the crash generator.
        name: Display name.
        description: Description of this crash generator version.
        download_url: Download URL.
        compatible_range: Optional game version range restriction.
        acronym: Short acronym for the crash generator (e.g., "B4").
        dll_file: DLL filename for the crash generator (e.g., "Buffout4.dll").

    """

    __slots__ = ("_acronym", "_compatible_range", "_description", "_dll_file", "_download_url", "_name", "_rust_obj", "_version")

    def __init__(
        self,
        version: str = "",
        name: str = "",
        description: str = "",
        download_url: str = "",
        compatible_range: CompatibleRange | None = None,
        acronym: str = "",
        dll_file: str = "",
        *,
        _rust_obj: _rust.CrashgenConfig | None = None,
    ) -> None:
        self._rust_obj = _rust_obj
        self._version = version
        self._name = name
        self._description = description
        self._download_url = download_url
        self._compatible_range = compatible_range
        self._acronym = acronym
        self._dll_file = dll_file

    @property
    def version(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.version
        return self._version

    @property
    def name(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.name
        return self._name

    @property
    def description(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.description
        return self._description

    @property
    def download_url(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.download_url
        return self._download_url

    @property
    def acronym(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.acronym
        return self._acronym

    @property
    def dll_file(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.dll_file
        return self._dll_file

    @property
    def compatible_range(self) -> CompatibleRange | None:
        if self._rust_obj is not None:
            rust_range = self._rust_obj.compatible_range
            if rust_range is None:
                return None
            return CompatibleRange(_rust_obj=rust_range)
        return self._compatible_range

    def is_compatible_with(self, game_version: Version) -> bool:
        """Check if this crash generator is compatible with a game version."""
        if self._rust_obj is not None:
            return self._rust_obj.is_compatible_with(str(game_version))
        if self._compatible_range is None:
            return True
        return self._compatible_range.contains(game_version)

    @classmethod
    def from_version_string(cls, version: str) -> CrashgenConfig:
        """Create a CrashgenConfig from just a version string."""
        return cls(version=version)


# ---------------------------------------------------------------------------
# VersionInfo
# ---------------------------------------------------------------------------
class VersionInfo:
    """Complete information about a game version.

    Wraps the Rust VersionInfo when returned from the registry. Can also be
    constructed directly (for tests or hardcoded defaults).

    Attributes:
        docs_name: Documentation-friendly name for this version (e.g., "Fallout4 OG").
        steam_id: Steam application ID for this game version.

    """

    __slots__ = (
        "_address_library",
        "_compatible_range",
        "_crashgen_versions",
        "_deprecated",
        "_description",
        "_display_name",
        "_docs_name",
        "_exe_hash",
        "_game",
        "_id",
        "_is_vr",
        "_priority",
        "_rust_obj",
        "_short_name",
        "_steam_id",
        "_version",
        "_xse",
    )

    def __init__(
        self,
        id: str = "",  # noqa: A002
        game: str = "",
        is_vr: bool = False,
        version: Version | None = None,
        display_name: str = "",
        short_name: str = "",
        description: str = "",
        docs_name: str = "",
        steam_id: int = 0,
        address_library: AddressLibraryConfig | None = None,
        xse: XseConfig | None = None,
        compatible_range: CompatibleRange | None = None,
        priority: int = 100,
        deprecated: bool = False,
        exe_hash: str | None = None,
        crashgen_versions: tuple[CrashgenConfig, ...] = (),
        *,
        _rust_obj: _rust.VersionInfo | None = None,
    ) -> None:
        self._rust_obj = _rust_obj
        self._id = id
        self._game = game
        self._is_vr = is_vr
        self._version = version
        self._display_name = display_name
        self._short_name = short_name
        self._description = description
        self._docs_name = docs_name
        self._steam_id = steam_id
        self._address_library = address_library
        self._xse = xse
        self._compatible_range = compatible_range
        self._priority = priority
        self._deprecated = deprecated
        self._exe_hash = exe_hash
        self._crashgen_versions = crashgen_versions

    @property
    def id(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.id
        return self._id

    @property
    def game(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.game
        return self._game

    @property
    def is_vr(self) -> bool:
        if self._rust_obj is not None:
            return self._rust_obj.is_vr
        return self._is_vr

    @property
    def version(self) -> Version:
        if self._rust_obj is not None:
            return Version(self._rust_obj.version)
        assert self._version is not None
        return self._version

    @property
    def version_string(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.version_string
        assert self._version is not None
        return str(self._version)

    @property
    def display_name(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.display_name
        return self._display_name

    @property
    def short_name(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.short_name
        return self._short_name

    @property
    def description(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.description
        return self._description

    @property
    def docs_name(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.docs_name
        return self._docs_name

    @property
    def steam_id(self) -> int:
        if self._rust_obj is not None:
            return self._rust_obj.steam_id
        return self._steam_id

    @property
    def address_library(self) -> AddressLibraryConfig | None:
        if self._rust_obj is not None:
            rust_al = self._rust_obj.address_library
            if rust_al is None:
                return None
            return AddressLibraryConfig(_rust_obj=rust_al)
        return self._address_library

    @property
    def xse(self) -> XseConfig | None:
        if self._rust_obj is not None:
            rust_xse = self._rust_obj.xse
            if rust_xse is None:
                return None
            return XseConfig(_rust_obj=rust_xse)
        return self._xse

    @property
    def compatible_range(self) -> CompatibleRange | None:
        if self._rust_obj is not None:
            rust_cr = self._rust_obj.compatible_range
            if rust_cr is None:
                return None
            return CompatibleRange(_rust_obj=rust_cr)
        return self._compatible_range

    @property
    def priority(self) -> int:
        if self._rust_obj is not None:
            return self._rust_obj.priority
        return self._priority

    @property
    def deprecated(self) -> bool:
        if self._rust_obj is not None:
            return self._rust_obj.deprecated
        return self._deprecated

    @property
    def exe_hash(self) -> str | None:
        if self._rust_obj is not None:
            return self._rust_obj.exe_hash
        return self._exe_hash

    @property
    def crashgen_versions(self) -> tuple[CrashgenConfig, ...]:
        if self._rust_obj is not None:
            return tuple(CrashgenConfig(_rust_obj=c) for c in self._rust_obj.crashgen_versions)
        return self._crashgen_versions

    def get_crashgen_version_strings(self) -> tuple[str, ...]:
        """Get crash generator versions as simple version strings."""
        if self._rust_obj is not None:
            return tuple(self._rust_obj.get_crashgen_version_strings())
        return tuple(config.version for config in self._crashgen_versions)

    def get_crashgen_for_version(self, crashgen_version: str) -> CrashgenConfig | None:
        """Get a specific CrashgenConfig by its version string."""
        if self._rust_obj is not None:
            rust_cfg = self._rust_obj.get_crashgen_for_version(crashgen_version)
            if rust_cfg is None:
                return None
            return CrashgenConfig(_rust_obj=rust_cfg)
        for config in self._crashgen_versions:
            if config.version == crashgen_version:
                return config
        return None

    def get_compatible_crashgens(self, game_version: Version | None = None) -> tuple[CrashgenConfig, ...]:
        """Get crash generators compatible with a specific game version."""
        if self._rust_obj is not None:
            gv_str = str(game_version) if game_version is not None else None
            return tuple(CrashgenConfig(_rust_obj=c) for c in self._rust_obj.get_compatible_crashgens(gv_str))
        if game_version is None:
            game_version = self.version
        return tuple(config for config in self._crashgen_versions if config.is_compatible_with(game_version))

    def is_compatible_with(self, detected: Version) -> bool:
        """Check if detected version is compatible with this version info."""
        if self._rust_obj is not None:
            return self._rust_obj.is_compatible_with(str(detected))
        if self._compatible_range:
            return self._compatible_range.contains(detected)
        assert self._version is not None
        return self._version == detected

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self.id == other.id


# ---------------------------------------------------------------------------
# UnknownVersionHandling
# ---------------------------------------------------------------------------
class UnknownVersionHandling:
    """Configuration for handling unknown/unsupported versions.

    Attributes:
        strategy: Matching strategy.
        defaults: Mapping of game names to default version IDs.
        log_level: Log level for unknown version warnings.

    """

    __slots__ = ("_defaults", "_log_level", "_rust_obj", "_strategy")

    def __init__(
        self,
        strategy: Literal["nearest_match", "strict", "default_only"] = "nearest_match",
        defaults: dict[str, str] | None = None,
        log_level: Literal["debug", "warning", "error"] = "warning",
        *,
        _rust_obj: _rust.UnknownVersionHandling | None = None,
    ) -> None:
        self._rust_obj = _rust_obj
        self._strategy = strategy
        self._defaults = defaults if defaults is not None else {}
        self._log_level = log_level

    @property
    def strategy(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.strategy
        return self._strategy

    @property
    def defaults(self) -> dict[str, str]:
        if self._rust_obj is not None:
            return self._rust_obj.defaults
        return self._defaults

    @property
    def log_level(self) -> str:
        if self._rust_obj is not None:
            return self._rust_obj.log_level
        return self._log_level

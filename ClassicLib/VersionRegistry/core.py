"""Core VersionRegistry implementation.

This module provides the main VersionRegistry class that loads game version
metadata from YAML configuration and provides lookup and matching functionality.

The registry is implemented as a thread-safe singleton that loads version data
from CLASSIC Main.yaml on first access. It provides methods for:
- Looking up versions by ID or exact version string
- Matching unknown versions to the nearest known version
- Filtering versions by game and VR mode

Example:
    >>> from ClassicLib.VersionRegistry.core import get_version_registry
    >>> registry = get_version_registry()
    >>> og = registry.get_by_id("FO4_OG")
    >>> print(og.address_library.filename)
    version-1-10-163-0.bin

"""

from __future__ import annotations

import threading
from typing import Any, ClassVar

import ruamel.yaml
from packaging.version import InvalidVersion, Version

from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.VersionRegistry.matching import MatchResult, VersionMatcher
from ClassicLib.VersionRegistry.models import (
    AddressLibraryConfig,
    CompatibleRange,
    UnknownVersionHandling,
    VersionInfo,
    XseConfig,
)


class VersionRegistry:
    """Data-driven version registry loaded from YAML.

    This class provides:
    - Loading version metadata from YAML configuration
    - Looking up version info by exact version or ID
    - Matching unknown versions to nearest known version
    - Filtering versions by game/VR mode

    Thread-safe singleton implementation. Use get_instance() or the module-level
    get_version_registry() function to access.

    Attributes:
        _instance: Class-level singleton instance.
        _lock: Class-level lock for thread-safe initialization.

    Example:
        >>> registry = VersionRegistry.get_instance()
        >>> info = registry.get_by_id("FO4_OG")
        >>> print(info.address_library.filename)
        version-1-10-163-0.bin

    """

    _instance: ClassVar[VersionRegistry | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Initialize the registry (use get_instance() instead).

        The registry is not loaded until explicitly called with _load().
        This allows for proper singleton behavior and lazy initialization.
        """
        self._versions: dict[str, VersionInfo] = {}
        self._by_version: dict[str, VersionInfo] = {}
        self._matcher: VersionMatcher | None = None
        self._unknown_handling: UnknownVersionHandling | None = None
        self._loaded = False
        self._init_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> VersionRegistry:
        """Get or create the singleton instance.

        Thread-safe method to get the singleton VersionRegistry instance.
        The registry is automatically loaded on first access.

        Returns:
            The singleton VersionRegistry instance.

        Example:
            >>> registry = VersionRegistry.get_instance()

        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._load()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only).

        Clears the singleton instance, allowing a fresh registry to be
        created on the next access. This should only be used in tests.
        """
        with cls._lock:
            cls._instance = None

    def _load(self) -> None:
        """Load version data from YAML configuration.

        Attempts to load version metadata from the Version_Registry section
        of CLASSIC Main.yaml. Falls back to hardcoded defaults if loading fails.
        """
        with self._init_lock:
            if self._loaded:
                return

            try:
                from ClassicLib.YamlSettings import yaml_settings

                # Load version registry from YAML
                versions_data = yaml_settings(list, YAML.Main, "Version_Registry.versions")

                if not versions_data:
                    logger.warning("No versions found in Version_Registry, using defaults")
                    self._load_defaults()
                    return

                for v_data in versions_data:
                    version_info = self._parse_version_data(v_data)
                    self._versions[version_info.id] = version_info
                    self._by_version[version_info.version_string] = version_info

                # Load unknown version handling config
                handling_data = yaml_settings(dict, YAML.Main, "Version_Registry.unknown_version_handling")
                if handling_data:
                    self._unknown_handling = UnknownVersionHandling(
                        strategy=handling_data.get("strategy", "nearest_match"),
                        defaults=handling_data.get("defaults", {}),
                        log_level=handling_data.get("log_level", "warning"),
                    )

                self._loaded = True
                logger.debug(f"Loaded {len(self._versions)} versions from registry")

            except (
                KeyError,
                TypeError,
                ValueError,
                InvalidVersion,
                OSError,
                RuntimeError,
                AttributeError,
                ImportError,
                ruamel.yaml.YAMLError,
            ) as e:
                logger.warning(f"Failed to load version registry: {e}, using defaults")
                self._load_defaults()

    @staticmethod
    def _parse_version_data(data: dict[str, Any]) -> VersionInfo:
        """Parse version data from YAML dict.

        Args:
            data: Dictionary containing version data from YAML.

        Returns:
            Parsed VersionInfo object.

        """
        # Parse Address Library config
        addr_lib = None
        if "address_library" in data:
            al = data["address_library"]
            addr_lib = AddressLibraryConfig(
                filename=al.get("filename", ""),
                format=al.get("format", "bin"),
                nexus_url=al.get("nexus_url", ""),
            )

        # Parse XSE config
        xse = None
        if "xse" in data:
            x = data["xse"]
            xse = XseConfig(
                acronym=x.get("acronym", ""),
                compatible_version=x.get("compatible_version", ""),
                loader=x.get("loader", ""),
            )

        # Parse compatible range
        compat_range = None
        if "compatible_range" in data:
            cr = data["compatible_range"]
            compat_range = CompatibleRange.from_strings(
                cr.get("min", "0.0.0"),
                cr.get("max", "999.999.999"),
            )

        return VersionInfo(
            id=data.get("id", ""),
            game=data.get("game", ""),
            is_vr=data.get("is_vr", False),
            version=Version(data.get("version", "0.0.0")),
            display_name=data.get("display_name", ""),
            short_name=data.get("short_name", ""),
            description=data.get("description", ""),
            address_library=addr_lib,
            xse=xse,
            compatible_range=compat_range,
            priority=data.get("priority", 100),
            deprecated=data.get("deprecated", False),
        )

    def _load_defaults(self) -> None:
        """Load hardcoded defaults as fallback.

        Used when YAML loading fails or Version_Registry section is empty.
        Provides the three standard Fallout 4 versions: OG, NG, and VR.
        """
        # OG Version
        og = VersionInfo(
            id="FO4_OG",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            display_name="Fallout 4 Original",
            short_name="OG",
            description="Pre-Next-Gen Update version",
            address_library=AddressLibraryConfig(
                filename="version-1-10-163-0.bin",
                format="bin",
                nexus_url="https://www.nexusmods.com/fallout4/mods/47327?tab=files",
            ),
            xse=XseConfig(
                acronym="F4SE",
                compatible_version="0.6.23",
                loader="f4se_loader.exe",
            ),
            priority=100,
        )
        self._versions[og.id] = og
        self._by_version[og.version_string] = og

        # NG Version
        ng = VersionInfo(
            id="FO4_NG",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.984.0"),
            display_name="Fallout 4 Next-Gen",
            short_name="NG",
            description="Next-Gen Update version",
            address_library=AddressLibraryConfig(
                filename="version-1-10-984-0.bin",
                format="bin",
                nexus_url="https://www.nexusmods.com/fallout4/mods/47327?tab=files",
            ),
            xse=XseConfig(
                acronym="F4SE",
                compatible_version="0.7.2",
                loader="f4se_loader.exe",
            ),
            priority=200,
        )
        self._versions[ng.id] = ng
        self._by_version[ng.version_string] = ng

        # VR Version
        vr = VersionInfo(
            id="FO4_VR",
            game="Fallout4",
            is_vr=True,
            version=Version("1.2.72.0"),
            display_name="Fallout 4 VR",
            short_name="VR",
            description="Virtual Reality version",
            address_library=AddressLibraryConfig(
                filename="version-1-2-72-0.csv",
                format="csv",
                nexus_url="https://www.nexusmods.com/fallout4/mods/64879?tab=files",
            ),
            xse=XseConfig(
                acronym="F4SEVR",
                compatible_version="0.6.20",
                loader="f4sevr_loader.exe",
            ),
            priority=100,
        )
        self._versions[vr.id] = vr
        self._by_version[vr.version_string] = vr

        # Set default unknown handling
        self._unknown_handling = UnknownVersionHandling(
            strategy="nearest_match",
            defaults={"Fallout4": "FO4_NG", "Fallout4VR": "FO4_VR"},
            log_level="warning",
        )

        self._loaded = True
        logger.debug("Loaded default version registry")

    # === Public API ===

    def get_by_id(self, version_id: str) -> VersionInfo | None:
        """Get version info by ID.

        Args:
            version_id: The version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR").

        Returns:
            The VersionInfo for the specified ID, or None if not found.

        Example:
            >>> registry = get_version_registry()
            >>> og = registry.get_by_id("FO4_OG")
            >>> print(og.version)
            1.10.163.0

        """
        return self._versions.get(version_id)

    def get_by_version(self, version: Version) -> VersionInfo | None:
        """Get version info by exact version match.

        Args:
            version: The exact game version to look up.

        Returns:
            The VersionInfo for the specified version, or None if not found.

        Example:
            >>> registry = get_version_registry()
            >>> info = registry.get_by_version(Version("1.10.163.0"))
            >>> print(info.id)
            FO4_OG

        """
        return self._by_version.get(str(version))

    def get_by_short_name(self, short_name: str) -> VersionInfo | None:
        """Get version info by short name.

        Args:
            short_name: The short name (e.g., "OG", "NG", "VR").

        Returns:
            The VersionInfo for the specified short name, or None if not found.

        Example:
            >>> registry = get_version_registry()
            >>> og = registry.get_by_short_name("OG")
            >>> print(og.version)
            1.10.163.0

        """
        for version_info in self._versions.values():
            if version_info.short_name == short_name:
                return version_info
        return None

    def match_version(
        self,
        detected: Version,
        game: str = "Fallout4",
        is_vr: bool = False,
    ) -> MatchResult:
        """Match a detected version to registry, with graceful fallback.

        Uses the VersionMatcher to find the best matching version for
        the detected game version. If no exact match is found, falls
        back to nearest match or default.

        Args:
            detected: The detected game version.
            game: Game identifier.
            is_vr: Whether VR mode is active.

        Returns:
            MatchResult with matched version and confidence level.

        Example:
            >>> registry = get_version_registry()
            >>> result = registry.match_version(Version("1.10.500.0"), "Fallout4", False)
            >>> print(result.confidence)
            MatchConfidence.NEAREST

        """
        if self._matcher is None:
            self._matcher = VersionMatcher(self)
        return self._matcher.match(detected, game, is_vr)

    def get_all(self) -> list[VersionInfo]:
        """Get all registered versions.

        Returns:
            List of all VersionInfo objects, sorted by priority (descending).

        """
        return sorted(
            self._versions.values(),
            key=lambda x: x.priority,
            reverse=True,
        )

    def get_all_for_game(
        self,
        game: str,
        is_vr: bool | None = None,
    ) -> list[VersionInfo]:
        """Get all versions for a specific game.

        Args:
            game: Game identifier (e.g., "Fallout4").
            is_vr: Optional VR filter. If None, returns all versions for the game.

        Returns:
            List of matching versions, sorted by priority (descending).

        """
        result = [v for v in self._versions.values() if v.game == game and (is_vr is None or v.is_vr == is_vr)]
        return sorted(result, key=lambda x: x.priority, reverse=True)

    def get_correct_versions(self, is_vr: bool) -> list[VersionInfo]:
        """Get correct versions for current mode (VR or non-VR).

        Used by CheckXsePlugins to determine which Address Library versions
        are appropriate for the current game mode.

        Args:
            is_vr: Whether VR mode is active.

        Returns:
            List of versions matching the VR mode.

        """
        return [v for v in self._versions.values() if v.is_vr == is_vr]

    def get_wrong_versions(self, is_vr: bool) -> list[VersionInfo]:
        """Get wrong versions for current mode (opposite of is_vr).

        Used by CheckXsePlugins to identify Address Library versions that
        are incorrect for the current game mode.

        Args:
            is_vr: Whether VR mode is active.

        Returns:
            List of versions NOT matching the VR mode.

        """
        return [v for v in self._versions.values() if v.is_vr != is_vr]

    def get_address_library_filename(
        self,
        version: Version,
        is_vr: bool = False,
    ) -> str | None:
        """Get Address Library filename for a version.

        Convenience method to get just the Address Library filename
        for a given game version.

        Args:
            version: The game version.
            is_vr: Whether VR mode is active.

        Returns:
            The Address Library filename, or None if not found.

        Example:
            >>> registry = get_version_registry()
            >>> filename = registry.get_address_library_filename(
            ...     Version("1.10.163.0"), is_vr=False
            ... )
            >>> print(filename)
            version-1-10-163-0.bin

        """
        result = self.match_version(version, "Fallout4", is_vr)
        if result.version_info and result.version_info.address_library:
            return result.version_info.address_library.filename
        return None

    @property
    def unknown_version_handling(self) -> UnknownVersionHandling:
        """Get the configuration for unknown version handling.

        Returns:
            The UnknownVersionHandling configuration.

        """
        if self._unknown_handling is None:
            return UnknownVersionHandling()
        return self._unknown_handling


def get_version_registry() -> VersionRegistry:
    """Get the singleton VersionRegistry instance.

    Convenience function for accessing the version registry.

    Returns:
        The singleton VersionRegistry instance.

    Example:
        >>> registry = get_version_registry()
        >>> og = registry.get_by_id("FO4_OG")

    """
    return VersionRegistry.get_instance()

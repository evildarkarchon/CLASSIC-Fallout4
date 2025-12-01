"""Type stubs for classic_config.

Python bindings for classic-config-core, providing high-performance YAML configuration
management for CLASSIC. This module wraps YamlDataCore from the business logic layer
and converts Rust types to Python types.

Architecture:
    - classic-config-core: Business logic (YamlDataCore, configuration loading)
    - classic-config-py: Python bindings (this module - PyO3 adapters)

Usage:
    from classic_config import YamlData, create_yamldata

    # Create YamlData instance
    yaml_data = create_yamldata()

    # Access configuration properties
    game_version = yaml_data.game_version
    plugins = yaml_data.game_ignore_plugins
    records = yaml_data.game_ignore_records
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

__version__: str

class YamlData:
    """Python wrapper for YamlDataCore.

    This is a thin adapter that:
    1. Calls YamlDataCore::load_from_yaml_files (business logic in classic-config-core)
    2. Converts Rust types (Vec, HashMap) to Python types (PyList, PyDict)
    3. Exposes fields as Python properties

    The YamlData class provides access to all CLASSIC configuration loaded from
    YAML files including game settings, mod lists, ignore lists, and version information.

    All properties are read-only and loaded during initialization. Configuration is
    cached and shared across instances for performance.
    """

    def __init__(self, yaml_dirs: Sequence[str | Path], game: str, vr_mode: bool) -> None:
        """Create a new YamlData instance by loading all YAML configuration files.

        Args:
            yaml_dirs: List of directories containing YAML configuration files.
                      Accepts both string paths and pathlib.Path objects.
            game: Game name (e.g., "Fallout4", "Skyrim")
            vr_mode: Whether to load VR-specific configuration

        Raises:
            FileNotFoundError: If required YAML files are missing
            ValueError: If YAML data is malformed or invalid

        Example:
            >>> from pathlib import Path
            >>> # Using Path objects
            >>> yaml_data = YamlData([Path("YAML/Main")], "Fallout4", False)
            >>> # Using strings
            >>> yaml_data = YamlData(["YAML/Main"], "Fallout4", False)
            >>> # Mixed
            >>> yaml_data = YamlData([Path("YAML/Main"), "YAML/Local"], "Fallout4", False)
        """

    @staticmethod
    def from_yaml_content(
        main_content: str,
        game_content: str,
        ignore_content: str,
        game: str,
        vr_mode: bool,
    ) -> YamlData:
        """Create YamlData from YAML content strings (for testing without file I/O).

        This constructor is useful for unit tests and integration tests where you want
        to test YamlData parsing without needing actual YAML files on disk.

        Args:
            main_content: Content of the main YAML configuration file
            game_content: Content of the game-specific YAML configuration file
            ignore_content: Content of the ignore list YAML configuration file
            game: Game identifier (e.g., "Fallout4", "Skyrim")
            vr_mode: Whether to load VR-specific configuration

        Returns:
            YamlData instance with parsed configuration

        Raises:
            RustConfigParseError: If any YAML content fails to parse

        Example:
            >>> main_yaml = '''
            ... CLASSIC_Info:
            ...   version: "7.31.0"
            ... '''
            >>> game_yaml = '''
            ... Game_Info:
            ...   XSE_Acronym: "F4SE"
            ... '''
            >>> ignore_yaml = '''
            ... CLASSIC_Ignore_Fallout4: []
            ... '''
            >>> config = YamlData.from_yaml_content(
            ...     main_yaml, game_yaml, ignore_yaml, "Fallout4", False
            ... )
        """

    # CLASSIC version information
    @property
    def classic_version(self) -> str:
        """CLASSIC version string (e.g., '8.0.0')."""

    @property
    def classic_version_date(self) -> str:
        """CLASSIC release date string."""

    # Game configuration
    @property
    def game_version(self) -> str:
        """Current game version string."""

    @property
    def game_version_new(self) -> str:
        """Latest available game version string."""

    @property
    def game_version_vr(self) -> str:
        """VR game version string."""

    # Crash generator settings
    @property
    def crashgen_name(self) -> str:
        """Crash generator/logger name (e.g., 'Buffout 4')."""

    @property
    def crashgen_latest_og(self) -> str:
        """Latest crash generator version for regular game."""

    @property
    def crashgen_latest_vr(self) -> str:
        """Latest crash generator version for VR game."""

    # Script extender configuration
    @property
    def xse_acronym(self) -> str:
        """Script extender acronym (e.g., 'F4SE' for Fallout 4)."""

    # Ignore lists
    @property
    def ignore_list(self) -> list[str]:
        """List of general patterns to ignore during analysis.

        Returns:
            List of ignore pattern strings
        """

    @property
    def game_ignore_plugins(self) -> list[str]:
        """List of plugins to ignore during analysis.

        These plugins are typically harmless or generate false positives.

        Returns:
            List of plugin names to ignore
        """

    @property
    def game_ignore_records(self) -> list[str]:
        """List of record types to ignore during analysis.

        These record types are typically not relevant for crash analysis.

        Returns:
            List of record type strings
        """

    @property
    def crashgen_ignore(self) -> set[str]:
        """Set of crash generator-specific patterns to ignore.

        Returns:
            Set of ignore pattern strings
        """

    # Mod detection lists
    @property
    def game_mods_core(self) -> dict[str, Any]:
        """Core/essential mods configuration.

        Returns:
            Dictionary mapping mod names to detection patterns
        """

    @property
    def game_mods_core_folon(self) -> dict[str, Any]:
        """Fallout London (FOLON) specific mods configuration.

        Returns:
            Dictionary mapping FOLON mod names to detection patterns
        """

    @property
    def game_mods_freq(self) -> dict[str, Any]:
        """Frequently problematic mods configuration.

        Returns:
            Dictionary mapping mod names to detection patterns
        """

    @property
    def game_mods_solu(self) -> dict[str, Any]:
        """Solution/fix mods configuration.

        Returns:
            Dictionary mapping solution mod names to detection patterns
        """

    @property
    def game_mods_opc2(self) -> dict[str, Any]:
        """Optimization/performance mods configuration (OPC2).

        Returns:
            Dictionary mapping optimization mod names to detection patterns
        """

    @property
    def game_mods_conf(self) -> dict[str, Any]:
        """Configuration mods.

        Returns:
            Dictionary mapping config mod names to detection patterns
        """

    # Records configuration
    @property
    def classic_records_list(self) -> list[str]:
        """List of all known record types for the game.

        Returns:
            List of record type strings (e.g., ['TES4', 'GRUP', 'ACHR', ...])
        """

    # Suspect detection lists
    @property
    def suspects_error_list(self) -> dict[str, Any]:
        """Suspect patterns for error detection.

        Returns:
            Dictionary mapping error categories to detection patterns
        """

    @property
    def suspects_stack_list(self) -> dict[str, Any]:
        """Suspect patterns for callstack analysis.

        Returns:
            Dictionary mapping callstack categories to detection patterns
        """

    # Warning messages
    @property
    def warn_noplugins(self) -> str:
        """Warning message for when no plugins are detected.

        Returns:
            Warning message string
        """

    @property
    def warn_outdated(self) -> str:
        """Warning message for outdated software.

        Returns:
            Warning message string
        """

    # UI text
    @property
    def autoscan_text(self) -> str:
        """UI text for autoscan feature.

        Returns:
            Autoscan description text
        """

    @property
    def classic_game_hints(self) -> list[str]:
        """Game-specific hints and tips for CLASSIC usage.

        Returns:
            List of hint strings
        """

def clear_yaml_cache() -> None:
    """Clear the global YAML configuration cache.

    Forces the next YamlData initialization to reload from disk.
    """

class RustConfigIOError(Exception):
    """Error raised when YAML files cannot be read."""

class RustConfigParseError(Exception):
    """Error raised when YAML content is invalid."""

def create_yamldata(yaml_dirs: Sequence[str | Path], game: str, vr_mode: bool) -> YamlData:
    """Factory function to create a YamlData instance.

    This is a convenience function that creates and returns a new YamlData instance.
    Equivalent to calling YamlData() directly.

    Args:
        yaml_dirs: List of directories containing YAML configuration files.
                  Accepts both string paths and pathlib.Path objects.
        game: Game name (e.g., "Fallout4", "Skyrim")
        vr_mode: Whether to load VR-specific configuration

    Returns:
        Configured YamlData instance with all YAML data loaded

    Raises:
        RustConfigIOError: If required YAML files are missing
        RustConfigParseError: If YAML data is malformed or invalid

    Example:
        >>> from classic_config import create_yamldata
        >>> from pathlib import Path
        >>> # Now this won't cause type errors:
        >>> yaml_data = create_yamldata([Path("YAML/Main")], "Fallout4", False)
        >>> print(yaml_data.classic_version)
        '8.0.0'
    """

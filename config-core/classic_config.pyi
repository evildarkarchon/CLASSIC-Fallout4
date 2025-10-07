"""Type stubs for classic_config Rust extension module.

This standalone module provides high-performance YAML configuration loading
with 15-30x speedup over Python's ruamel.yaml through:
- yaml-rust2 for parsing (pure Rust, YAML 1.2 compliant)
- Parallel file I/O with Tokio
- Efficient memory representation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__version__: str

class YamlData:
    """Rust equivalent of ClassicScanLogsInfo.

    This class mirrors the Python dataclass fields exactly to ensure
    API compatibility when used from Python code.

    Provides 15-30x faster configuration loading compared to Python
    ruamel.yaml implementation.
    """

    # Game configuration
    classic_game_hints: list[str]
    classic_records_list: list[str]
    classic_version: str
    classic_version_date: str

    # Crashgen configuration
    crashgen_name: str
    crashgen_latest_og: str
    crashgen_latest_vr: str
    crashgen_ignore: set[str]

    # Warnings
    warn_noplugins: str
    warn_outdated: str

    # XSE configuration
    xse_acronym: str

    # Ignore lists
    game_ignore_plugins: list[str]
    game_ignore_records: list[str]
    ignore_list: list[str]

    # Suspect patterns
    suspects_error_list: dict[str, str]
    suspects_stack_list: dict[str, list[str]]

    # Mod databases
    game_mods_conf: dict[str, str]
    game_mods_core: dict[str, str]
    game_mods_core_folon: dict[str, str]
    game_mods_freq: dict[str, str]
    game_mods_opc2: dict[str, str]
    game_mods_solu: dict[str, str]

    # UI configuration
    autoscan_text: str

    # Game versions (stored as strings, converted to Version in Python)
    game_version: str
    game_version_new: str
    game_version_vr: str

    def __init__(
        self,
        yaml_dirs: list[Path] | list[str],
        game: str,
        vr_mode: bool
    ) -> None:
        """Create YamlData by loading configuration from YAML files.

        Loads all necessary YAML files in parallel for maximum performance:
        - CLASSIC Main.yaml - Core configuration
        - CLASSIC {game}.yaml - Game-specific configuration
        - CLASSIC_Ignore.yaml - Ignore lists
        - CLASSIC_{game}_Suspects.yaml - Suspect patterns
        - CLASSIC_{game}_Mods_*.yaml - Mod databases

        Args:
            yaml_dirs: List of YAML directory paths to search
            game: Game name ("Fallout4" or "Skyrim")
            vr_mode: Whether VR mode is enabled

        Raises:
            IOError: If required YAML files cannot be read
            ValueError: If YAML parsing fails

        Example:
            >>> from pathlib import Path
            >>> yaml_dirs = [Path("YAML"), Path("YAML/Fallout4")]
            >>> yamldata = YamlData(yaml_dirs, "Fallout4", False)
            >>> print(yamldata.classic_version)
            '3.0.0'
        """
        ...

    def __repr__(self) -> str:
        """Return string representation of YamlData.

        Returns:
            String showing game, version, and configuration counts
        """
        ...

    def get_crashgen_latest(self, vr_mode: bool) -> str:
        """Get the latest crashgen version for the specified mode.

        Args:
            vr_mode: Whether to get VR version

        Returns:
            Latest crashgen version string
        """
        ...

    def get_game_version_str(self, vr_mode: bool = False) -> str:
        """Get game version as string.

        Args:
            vr_mode: Whether to get VR version

        Returns:
            Game version string
        """
        ...

    def is_plugin_ignored(self, plugin: str) -> bool:
        """Check if a plugin should be ignored.

        Args:
            plugin: Plugin name to check

        Returns:
            True if plugin is in ignore list
        """
        ...

    def is_record_ignored(self, record: str) -> bool:
        """Check if a record should be ignored.

        Args:
            record: Record name to check

        Returns:
            True if record is in ignore list
        """
        ...

    def get_mod_info(self, mod_name: str) -> dict[str, str]:
        """Get information about a specific mod.

        Searches all mod databases (core, freq, conf, solu, opc2, folon).

        Args:
            mod_name: Name of mod to find

        Returns:
            Dictionary with mod information, empty if not found
        """
        ...

    def get_all_mods(self) -> dict[str, str]:
        """Get all mods from all databases.

        Returns:
            Combined dictionary of all mods
        """
        ...

    def get_suspect_pattern(self, key: str) -> str | None:
        """Get suspect pattern by key.

        Searches both error and stack pattern lists.

        Args:
            key: Pattern key to find

        Returns:
            Pattern string or None if not found
        """
        ...

    def validate_configuration(self) -> tuple[bool, list[str]]:
        """Validate that all required configuration is present.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        ...


def create_yamldata(
    yaml_dirs: list[Path] | list[str],
    game: str,
    vr_mode: bool
) -> YamlData:
    """Factory function to create YamlData instance.

    This is a convenience function that's equivalent to calling
    YamlData() constructor directly.

    Args:
        yaml_dirs: List of YAML directory paths
        game: Game name ("Fallout4" or "Skyrim")
        vr_mode: Whether VR mode is enabled

    Returns:
        Configured YamlData instance

    Raises:
        IOError: If required YAML files cannot be read
        ValueError: If YAML parsing fails

    Example:
        >>> from pathlib import Path
        >>> yamldata = create_yamldata(
        ...     [Path("YAML"), Path("YAML/Fallout4")],
        ...     "Fallout4",
        ...     False
        ... )
    """
    ...

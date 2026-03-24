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

    def __init__(
        self, yaml_dirs: Sequence[str | Path], game: str, game_version: str
    ) -> None:
        """Create a new YamlData instance by loading all YAML configuration files.

        Args:
            yaml_dirs: List of directories containing YAML configuration files.
                      Accepts both string paths and pathlib.Path objects.
            game: Game name (e.g., "Fallout4", "Skyrim")
            game_version: Selected mode
                ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")

        Raises:
            FileNotFoundError: If required YAML files are missing
            ValueError: If YAML data is malformed or invalid

        Example:
            >>> from pathlib import Path
            >>> # Using Path objects
            >>> yaml_data = YamlData([Path("YAML/Main")], "Fallout4", "auto")
            >>> # Using strings
            >>> yaml_data = YamlData(["YAML/Main"], "Fallout4", "auto")
            >>> # Mixed
            >>> yaml_data = YamlData([Path("YAML/Main"), "YAML/Local"], "Fallout4", "auto")

        """

    @staticmethod
    def from_yaml_content(
        main_content: str,
        game_content: str,
        ignore_content: str,
        game: str,
        game_version: str,
    ) -> YamlData:
        """Create YamlData from YAML content strings (for testing without file I/O).

        This constructor is useful for unit tests and integration tests where you want
        to test YamlData parsing without needing actual YAML files on disk.

        Args:
            main_content: Content of the main YAML configuration file
            game_content: Content of the game-specific YAML configuration file
            ignore_content: Content of the ignore list YAML configuration file
            game: Game identifier (e.g., "Fallout4", "Skyrim")
            game_version: Selected mode
                ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")

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
            ...     main_yaml, game_yaml, ignore_yaml, "Fallout4", "auto"
            ... )

        """

    def __repr__(self) -> str:
        """Return a compact representation for debugging."""

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

    # Crash generator settings
    @property
    def crashgen_name(self) -> str:
        """Crash generator/logger name for OG/non-VR (e.g., 'Buffout 4')."""

    @property
    def crashgen_latest_og(self) -> str:
        """Latest crash generator version for regular game."""

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
        """Set of crash generator-specific patterns to ignore (OG/non-VR).

        Returns:
            Set of ignore pattern strings

        """

    @property
    def crashgen_registry(self) -> dict[str, dict[str, Any]]:
        """Per-crashgen settings registry loaded from game YAML.

        Maps crashgen names (including ``"default"``) to entry dictionaries
        with keys ``display_section`` (str), ``ignore_keys`` (list[str]),
        ``checks`` (list[str]), ``settings_rules_version`` (int|None), and
        ``settings_rules`` (dict|None).
        """

    # Game root names
    @property
    def game_root_name(self) -> str:
        """Game root name (OG/non-VR, from Game_Info.Main_Root_Name)."""

    # Mod detection lists
    @property
    def game_mods_core(self) -> list[dict[str, str | None]]:
        """Core/essential mods configuration.

        Returns:
            List of dicts with keys: detect, name, description, gpu (optional)

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
    def game_mods_conf(self) -> list[dict[str, str | None]]:
        """Mod conflict entries.

        Returns:
            List of mod conflict entry dicts with keys:
                mod_a, mod_b, name_a, name_b, description, fix, link (optional)

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
    def suspects_stack_list(self) -> dict[str, list[str]]:
        """Suspect patterns for callstack analysis.

        Returns:
            Dictionary mapping callstack categories to pattern lists

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

class PathConfig:
    """Path configuration for game directories and scan inputs."""

    def __init__(
        self,
        ini_folder: str | None = None,
        scan_custom: str | None = None,
        mods_folder: str | None = None,
        game_root: str = "",
        docs_root: str | None = None,
    ) -> None:
        """Create a path configuration object."""

    @property
    def ini_folder(self) -> str | None:
        """Path to the INI folder, if configured."""

    @ini_folder.setter
    def ini_folder(self, value: str | None) -> None: ...
    @property
    def scan_custom(self) -> str | None:
        """Path to a custom scan folder, if configured."""

    @scan_custom.setter
    def scan_custom(self, value: str | None) -> None: ...
    @property
    def mods_folder(self) -> str | None:
        """Path to the mods folder, if configured."""

    @mods_folder.setter
    def mods_folder(self, value: str | None) -> None: ...
    @property
    def game_root(self) -> str:
        """Path to the game root directory."""

    @game_root.setter
    def game_root(self, value: str) -> None: ...
    @property
    def docs_root(self) -> str | None:
        """Path to the documents root directory, if configured."""

    @docs_root.setter
    def docs_root(self, value: str | None) -> None: ...
    def __repr__(self) -> str: ...

class YamlSource:
    """Enum-like YAML source identifier."""

    MAIN: YamlSource
    SETTINGS: YamlSource
    IGNORE: YamlSource
    GAME: YamlSource
    GAME_LOCAL: YamlSource
    TEST: YamlSource
    CACHE: YamlSource

    def path(self, game: str) -> str:
        """Resolve the source path for a game."""

    def display_name(self) -> str:
        """Return the generic display name."""

    def display_name_with_game(self, game: str) -> str:
        """Return the game-specific display name."""

    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...

class ClassicConfig:
    """Runtime CLASSIC settings configuration."""

    def __init__(self) -> None:
        """Create a default runtime configuration."""

    @staticmethod
    def load_from_yaml(path: str | Path) -> ClassicConfig:
        """Load a configuration from a YAML file."""

    @staticmethod
    def load_or_default() -> ClassicConfig:
        """Load configuration from the default path or return defaults."""

    def save_to_yaml(self, path: str | Path) -> None:
        """Save the configuration to a YAML file."""

    def get_config_path(self) -> str:
        """Get the default config filename."""

    def validate_paths(self) -> None:
        """Validate configured filesystem paths."""

    def load_local_yaml_paths(self, game: str) -> None:
        """Load `game_root` and `docs_root` from the game's Local YAML."""

    @property
    def fcx_mode(self) -> bool:
        """Whether FCX mode is enabled."""

    @fcx_mode.setter
    def fcx_mode(self, value: bool) -> None: ...
    @property
    def show_formid_values(self) -> bool:
        """Whether FormID values are shown."""

    @show_formid_values.setter
    def show_formid_values(self, value: bool) -> None: ...
    @property
    def stat_logging(self) -> bool:
        """Whether statistical logging is enabled."""

    @stat_logging.setter
    def stat_logging(self, value: bool) -> None: ...
    @property
    def move_unsolved_logs(self) -> bool:
        """Whether unsolved logs are moved after scanning."""

    @move_unsolved_logs.setter
    def move_unsolved_logs(self, value: bool) -> None: ...
    @property
    def simplify_logs(self) -> bool:
        """Whether logs are simplified."""

    @simplify_logs.setter
    def simplify_logs(self, value: bool) -> None: ...
    @property
    def update_check(self) -> bool:
        """Whether startup update checks are enabled."""

    @update_check.setter
    def update_check(self, value: bool) -> None: ...
    @property
    def game_version(self) -> str:
        """Selected game version mode."""

    @game_version.setter
    def game_version(self, value: str) -> None: ...
    @property
    def update_source(self) -> str:
        """Configured update source."""

    @update_source.setter
    def update_source(self, value: str) -> None: ...
    @property
    def auto_switch_to_results(self) -> bool:
        """Whether UI should switch to results automatically."""

    @auto_switch_to_results.setter
    def auto_switch_to_results(self, value: bool) -> None: ...
    @property
    def auto_refresh_interval_ms(self) -> int:
        """Auto-refresh interval in milliseconds."""

    @auto_refresh_interval_ms.setter
    def auto_refresh_interval_ms(self, value: int) -> None: ...
    @property
    def paths(self) -> PathConfig:
        """Path configuration."""

    @paths.setter
    def paths(self, value: PathConfig) -> None: ...
    @property
    def formid_databases(self) -> dict[str, list[str]]:
        """Configured FormID database paths by game."""

    @formid_databases.setter
    def formid_databases(self, value: dict[str, list[str]]) -> None: ...
    def __repr__(self) -> str: ...

def clear_yaml_cache() -> None:
    """Clear the global YAML configuration cache.

    Forces the next YamlData initialization to reload from disk.
    """

def create_yamldata(
    yaml_dirs: Sequence[str | Path], game: str, game_version: str
) -> YamlData:
    """Create via factory create a YamlData instance.

    This is a convenience function that creates and returns a new YamlData instance.
    Equivalent to calling YamlData() directly.

    Args:
        yaml_dirs: List of directories containing YAML configuration files.
                  Accepts both string paths and pathlib.Path objects.
        game: Game name (e.g., "Fallout4", "Skyrim")
        game_version: Selected mode ("auto", "Original", "NextGen", "VR")

    Returns:
        Configured YamlData instance with all YAML data loaded

    Raises:
        IOError: If required YAML files are missing
        ValueError: If YAML data is malformed or invalid

    Example:
        >>> from classic_config import create_yamldata
        >>> from pathlib import Path
        >>> # Now this won't cause type errors:
        >>> yaml_data = create_yamldata([Path("YAML/Main")], "Fallout4", "auto")
        >>> print(yaml_data.classic_version)
        '8.0.0'

    """

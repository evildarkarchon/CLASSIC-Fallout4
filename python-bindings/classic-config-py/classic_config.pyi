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
        """Bare SemVer string from `CLASSIC_Info.version` (e.g., 'v9.1.0' or '8.0.0').

        Consumers that need a display-decorated form (e.g., 'CLASSIC v9.1.0')
        should prepend the product-name prefix at format time; the YAML stores
        the raw SemVer per schema_version 2.0.
        """

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
        ``checks`` (deprecated inert list[str]), ``settings_rules_version`` (int|None), and
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
    def game_mods_freq(self) -> list[dict[str, Any]]:
        """Frequently problematic mods configuration.

        Returns:
            List of structured mod entries with `id`, `criteria`, `exceptions`, `name`,
            and `description`

        """

    @property
    def game_mods_solu(self) -> list[dict[str, Any]]:
        """Solution/fix mods configuration.

        Returns:
            Ordered list of dicts with keys:
                id, criteria, exceptions, name, description

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

    # Suspect detection rules
    @property
    def suspect_error_rules(self) -> list[dict[str, Any]]:
        """Structured suspect rules for main-error detection.

        Returns:
            List of dicts with keys: id, name, severity, main_error_contains_any

        """

    @property
    def suspect_stack_rules(self) -> list[dict[str, Any]]:
        """Structured suspect rules for callstack analysis.

        Returns:
            List of dicts with keys: id, name, severity, main_error_required_any,
            main_error_optional_any, stack_contains_any,
            exclude_if_stack_contains_any, stack_contains_at_least

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

class YamlSource:
    """Enum-like YAML source identifier."""

    MAIN: YamlSource
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

def clear_yaml_cache() -> None:
    """Clear the global YAML configuration cache.

    Forces the next YamlData initialization to reload from disk.
    """

class ExplicitYamlDataGame:
    """Typed game identity for deterministic explicit YAML Data loading."""

    FALLOUT4: ExplicitYamlDataGame
    FALLOUT4_VR: ExplicitYamlDataGame
    SKYRIM: ExplicitYamlDataGame
    STARFIELD: ExplicitYamlDataGame

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...

class ExplicitYamlDataPaths:
    """Exact caller-selected Main, game, and Local Ignore files."""

    def __init__(
        self,
        main_path: str | Path,
        game_path: str | Path,
        ignore_path: str | Path,
    ) -> None: ...

    @property
    def main_path(self) -> Path: ...
    @property
    def game_path(self) -> Path: ...
    @property
    def ignore_path(self) -> Path: ...

class YamlDataContentIdentity:
    """SHA-256 and byte length derived from exact retained file bytes."""

    @property
    def sha256(self) -> str: ...
    @property
    def byte_len(self) -> int: ...

class ExplicitYamlDataSnapshot:
    """Immutable deterministic YAML Data snapshot with exact identities."""

    @property
    def game(self) -> ExplicitYamlDataGame: ...
    @property
    def game_data_role(self) -> str: ...
    @property
    def yaml_data(self) -> YamlData: ...
    @property
    def main_identity(self) -> YamlDataContentIdentity: ...
    @property
    def game_identity(self) -> YamlDataContentIdentity: ...
    @property
    def ignore_identity(self) -> YamlDataContentIdentity: ...

class ExplicitYamlDataLoadError(Exception):
    """Base class for deterministic explicit YAML Data load failures."""

    code: str
    yaml_role: str | None
    path: str | None

class ExplicitYamlDataUnsupportedGameError(ExplicitYamlDataLoadError): ...
class ExplicitYamlDataReadError(ExplicitYamlDataLoadError): ...
class ExplicitYamlDataInvalidUtf8Error(ExplicitYamlDataLoadError): ...
class ExplicitYamlDataParseError(ExplicitYamlDataLoadError): ...
class ExplicitYamlDataInvalidRoleDataError(ExplicitYamlDataLoadError): ...

def load_explicit_yaml_data(
    paths: ExplicitYamlDataPaths,
    game: ExplicitYamlDataGame,
    selected_game_version: str,
) -> ExplicitYamlDataSnapshot:
    """Load only the exact supplied files without cache or mutation policy."""

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

def persist_game_local_paths(
    local_yaml_path: str | Path,
    game_root: str | Path | None = None,
    docs_root: str | Path | None = None,
) -> None:
    """Persist supplied runtime paths to a Game Local YAML document.

    ``None`` leaves the corresponding key unchanged. Existing unrelated Game
    Local content is preserved, and the User Settings document is not accessed.

    Args:
        local_yaml_path: Explicit Game Local YAML document path.
        game_root: Optional game-root update.
        docs_root: Optional documents-root update.

    Raises:
        RustConfigIOError: If the document cannot be created or saved.
        RustConfigParseError: If an existing Game Local document is malformed.
    """

def set_application_dir(path: str | Path) -> None:
    """Override the directory used by independent application-local YAML helpers.

    User Settings APIs always take an explicit CLASSIC root and do not consult
    this registry value.

    Args:
        path: Absolute path to the desired application directory.
    """

def get_application_dir() -> str | None:
    """Return the current application directory override, or ``None``."""

# ---------------------------------------------------------------------------
# Schema-gated CLASSIC Main.yaml version reader
# ---------------------------------------------------------------------------

class ClassicMainYamlVersionError(Exception):
    """Base class for :func:`load_main_yaml_version` failures.

    Consumers that want to catch any failure use
    ``except ClassicMainYamlVersionError``. Callers that want to branch on
    the specific cause (e.g. "re-show the installer" vs "prompt to upgrade
    CLASSIC") catch one of the subclasses below.
    """

class ClassicMainYamlVersionLoadError(ClassicMainYamlVersionError):
    """CLASSIC Main.yaml could not be loaded or passed the schema gate.

    Raised when neither the per-user cache copy nor the bundled
    install-tree copy is both loadable and compatible with
    ``client_schemas.MAIN_YAML``. Typical causes: file missing from
    disk, YAML parse failure, or a ``schema_version`` header that is
    outside the client's accepted MAJOR/MINOR range (e.g. a stale
    ``schema_version: 1.x`` payload still carrying the legacy
    ``CLASSIC v…`` decoration).
    """

class ClassicMainYamlVersionKeyMissingError(ClassicMainYamlVersionError):
    """``CLASSIC_Info.version`` (or the ``CLASSIC_Info`` section) is absent.

    The YAML loaded and passed the schema gate, but the specific key
    the reader wants is not present in the document.
    """

class ClassicMainYamlVersionEmptyError(ClassicMainYamlVersionError):
    """``CLASSIC_Info.version`` is present but empty or whitespace-only.

    Trimming the value produced an empty string; the reader refuses to
    propagate this through to ``QApplication.applicationVersion()`` (or
    its Python equivalent) because downstream update-check
    classification would silently degrade to ``"unknown"``.
    """

class ClassicMainYamlVersionNotStringError(ClassicMainYamlVersionError):
    """``CLASSIC_Info.version`` is present but not a YAML scalar string.

    For example, a YAML sequence or mapping where a string was
    expected. Distinct from :class:`ClassicMainYamlVersionKeyMissingError`
    so callers can emit a more actionable diagnostic.
    """

class ClassicMainYamlVersionInvalidError(ClassicMainYamlVersionError):
    """``CLASSIC_Info.version`` is a non-empty string but its shape does
    not match the schema-2.0 contract.

    The schema-2.0 contract is an optional leading ``v``/``V`` followed
    by strict release SemVer (``MAJOR.MINOR.PATCH`` only, no prerelease
    suffix, no build metadata, no legacy ``CLASSIC `` decoration).
    CLASSIC ships release-only versions by policy; the loader enforces
    that here so a malformed publish fails fast instead of silently
    degrading to ``Classification.UNKNOWN`` in
    :func:`check_app_notification`.
    """

def load_main_yaml_version(bundled_yaml_dir: str | None = None) -> str:
    """Load ``CLASSIC Main.yaml`` and return ``CLASSIC_Info.version``, schema-gated.

    The loader enforces ``client_schemas.MAIN_YAML`` so a stale
    ``schema_version: 1.x`` file with the legacy ``CLASSIC v…`` decoration
    is rejected at this boundary instead of flowing through to
    downstream update-check classification. Callers MUST NOT fall back
    to a raw YAML read on error — that reintroduces the silent-
    degradation behavior this reader exists to prevent.

    Both the per-user YAML cache (``yaml_cache_dir``) and the bundled
    copy under ``<bundled_yaml_dir>/CLASSIC Main.yaml`` are considered,
    preferring a compatible cache copy over an older bundled copy.

    Args:
        bundled_yaml_dir: Directory that contains ``CLASSIC Main.yaml``
            (typically ``<install>/CLASSIC Data/databases``). ``None``
            or ``""`` keeps the default relative path resolved against
            the process working directory, which is unreliable for
            Python hosts run from arbitrary cwds — prefer an explicit
            path in that case.

    Returns:
        The trimmed ``CLASSIC_Info.version`` value. Never empty.

    Raises:
        ClassicMainYamlVersionLoadError: Both the cache and bundled
            copies failed to load or passed the schema gate.
        ClassicMainYamlVersionKeyMissingError: ``CLASSIC_Info.version``
            (or the ``CLASSIC_Info`` section) is absent.
        ClassicMainYamlVersionEmptyError: ``CLASSIC_Info.version`` is
            present but empty or whitespace-only.
        ClassicMainYamlVersionNotStringError: ``CLASSIC_Info.version``
            is present but not a YAML scalar string.
        ClassicMainYamlVersionInvalidError: ``CLASSIC_Info.version`` is
            a non-empty string but its shape does not match the
            schema-2.0 contract (legacy ``CLASSIC `` prefix, prerelease
            suffix, build metadata, or non-semver garbage).
    """

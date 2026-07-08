"""Type stubs for classic_scangame.

Python bindings for classic-scangame-core, providing Rust-accelerated game scanning
and validation with 20-100x performance improvements over pure Python.

Architecture:
    - classic-scangame-core: Business logic (config detection, file scanning, validation)
    - classic-scangame-py: Python bindings (this module - PyO3 adapters)

Features:
    - BA2 archive handling (40-100x faster with memory mapping)
    - Config duplicate detection (20-50x faster)
    - Unpacked file scanning (30-80x faster with parallel I/O)
    - Log processing (error detection and reporting)
    - INI validation (10-30x faster with cached parsing)
    - TOML validation (CheckCrashgen)
    - XSE plugin checking (F4SE/SKSE version validation)
    - Game integrity checking (20-40x faster with native SHA256)

Usage:
    import classic_scangame
    from pathlib import Path

    # BA2 archive scanning
    scanner = classic_scangame.BA2Scanner()
    issues = scanner.scan_archive(Path("MyMod.ba2"))

    # Config duplicate detection
    detector = classic_scangame.ConfigDuplicateDetector()
    duplicates = detector.detect_duplicates(Path("C:/Games/Fallout4"))

    # Game integrity checking
    config = classic_scangame.IntegrityConfig(
        Path("C:/Games/Fallout4/Fallout4.exe"),
        "old_version_hash",
        "new_version_hash",
        "Fallout 4"
    )
    checker = classic_scangame.GameIntegrityChecker(config)
    message = checker.run_full_check()
"""

from enum import Enum
from pathlib import Path

__version__: str
__debug_registered__: bool

# ============================================================================
# BA2 Archive Handling
# ============================================================================

class BA2Issues:
    """Issues found in BA2 archive scanning.

    Attributes:
        tex_dims: Texture dimension issues (odd-numbered dimensions).
        tex_frmt: Texture format issues (non-DDS textures).
        snd_frmt: Sound format issues (MP3/M4A instead of XWM).
        xse_file: XSE script files detected in archive.

    """

    tex_dims: list[str]
    tex_frmt: list[str]
    snd_frmt: list[str]
    xse_file: list[str]

    def has_issues(self) -> bool:
        """Check if any issues were found.

        Returns:
            True if any issue list is non-empty.

        """

    def total_count(self) -> int:
        """Get total count of all issues.

        Returns:
            Sum of all issue list lengths.

        """

class BA2Scanner:
    """Scans BA2 archive files for issues and validates their contents.

    40-100x faster than Python implementations.

    Example:
        >>> scanner = BA2Scanner()
        >>> ba2_files = scanner.find_ba2_files(Path("/path/to/game/Data"))
        >>> for ba2_file in ba2_files:
        ...     issues = scanner.scan_archive(ba2_file)
        ...     if issues.has_issues():
        ...         print(f"Issues in {ba2_file}")

    """

    def __init__(self) -> None:
        """Create a new BA2Scanner instance."""

    def find_ba2_files(self, root_path: Path) -> list[Path]:
        """Find all BA2 archive files in a directory.

        Args:
            root_path: Root directory to search (typically game Data folder).

        Returns:
            List of BA2 archive file paths.

        """

    def scan_archive(self, archive_path: Path) -> BA2Issues:
        """Scan a single BA2 archive for issues.

        Args:
            archive_path: Path to BA2 archive file.

        Returns:
            BA2Issues object containing lists of problematic entries.

        """

    def scan_archives_batch(
        self, archive_paths: list[Path]
    ) -> list[tuple[Path, BA2Issues]]:
        """Scan multiple BA2 archives in batch.

        Args:
            archive_paths: List of BA2 archive paths to scan.

        Returns:
            List of tuples (archive_path, BA2Issues) for each archive.

        """

def scan_all_ba2_archives(root_path: Path) -> list[tuple[Path, BA2Issues]]:
    """Provide convenience wrapper to find and scan all BA2 archives in a directory.

    Args:
        root_path: Root directory to search.

    Returns:
        List of tuples (archive_path, BA2Issues) for all BA2 files found.

    """

# ============================================================================
# Config Duplicate Detection
# ============================================================================

class DuplicateGroup:
    """Group of duplicate configuration files.

    Attributes:
        original: Original file path (canonical).
        duplicates: List of duplicate file paths.

    """

    original: Path
    duplicates: list[Path]

class ConfigDuplicateDetector:
    """Detects duplicate configuration files in a directory tree.

    20-50x faster than Python implementations.

    Example:
        >>> detector = ConfigDuplicateDetector()
        >>> duplicates = detector.detect_duplicates(Path("/path/to/config"))
        >>> for group in duplicates:
        ...     print(f"Original: {group.original}")
        ...     for dup in group.duplicates:
        ...         print(f"  Duplicate: {dup}")

    """

    def __init__(self) -> None:
        """Create a new ConfigDuplicateDetector instance."""

    def detect_duplicates(self, root_path: Path) -> list[DuplicateGroup]:
        """Detect duplicate configuration files in the specified directory.

        Args:
            root_path: Root directory path to scan.

        Returns:
            List of DuplicateGroup objects containing original and duplicate paths.

        """

    def get_duplicate_map(self, root_path: Path) -> dict[str, list[Path]]:
        """Get dictionary mapping of lowercase filenames to lists of paths.

        Args:
            root_path: Root directory path to scan.

        Returns:
            Dictionary where keys are lowercase filenames and values are lists of paths.

        """

def detect_config_duplicates(root_path: Path) -> list[DuplicateGroup]:
    """Provide convenience wrapper to detect duplicates without creating detector instance.

    Args:
        root_path: Root directory path to scan.

    Returns:
        List of DuplicateGroup objects.

    """

# ============================================================================
# Unpacked File Scanning
# ============================================================================

class UnpackedIssues:
    """Issues found in unpacked file scanning.

    Attributes:
        animdata: Animation data directories detected.
        tex_frmt: Texture format issues (TGA/PNG instead of DDS).
        snd_frmt: Sound format issues (MP3/M4A instead of XWM).
        xse_file: XSE script files detected.
        previs: Previs/Precombine files detected.
        dds_files: DDS files found (for batch dimension checking).

    """

    animdata: list[str]
    tex_frmt: list[str]
    snd_frmt: list[str]
    xse_file: list[str]
    previs: list[str]
    dds_files: list[Path]

    def has_issues(self) -> bool:
        """Check if any issues were found.

        Returns:
            True if any issue list is non-empty.

        """

    def total_count(self) -> int:
        """Get total count of all issues.

        Returns:
            Sum of all issue list lengths (excluding dds_files).

        """

class UnpackedScanner:
    """Scans directories for unpacked files that should be in BA2 archives.

    30-80x faster than Python implementations with parallel I/O.

    Example:
        >>> scanner = UnpackedScanner()
        >>> issues = scanner.scan_directory(Path("/path/to/game/Data"), ["f4se.dll"])
        >>> if issues.has_issues():
        ...     print(f"Found {issues.total_count()} issues")

    """

    def __init__(self) -> None:
        """Create a new UnpackedScanner instance."""

    def scan_directory(
        self, root_path: Path, xse_scriptfiles: list[str]
    ) -> UnpackedIssues:
        """Scan a directory for unpacked file issues.

        Args:
            root_path: Root directory to scan (typically game Data folder).
            xse_scriptfiles: List of XSE script filenames to detect (e.g., ["f4se.dll"]).

        Returns:
            UnpackedIssues object containing lists of problematic files.

        """

def scan_unpacked_files(root_path: Path, xse_scriptfiles: list[str]) -> UnpackedIssues:
    """Provide convenience wrapper to scan unpacked files without creating scanner instance.

    Args:
        root_path: Root directory path to scan.
        xse_scriptfiles: List of XSE script filenames to detect.

    Returns:
        UnpackedIssues object.

    """

# ============================================================================
# Log Processing
# ============================================================================

class LogErrorEntry:
    """Error entry from log file processing.

    Attributes:
        file_path: Path to the log file.
        errors: Error lines found in the log (limited to last 50).
        total_errors: Total number of errors found (before truncation).

    """

    file_path: Path
    errors: list[str]
    total_errors: int

class LogProcessor:
    """Scans directories for log files and detects errors based on configurable patterns.

    Example:
        >>> processor = LogProcessor(
        ...     catch_errors=["error", "fatal", "crash"],
        ...     ignore_files=["debug.log"],
        ...     ignore_errors=["ignored error"]
        ... )
        >>> report = processor.process_logs(Path("/path/to/logs"))
        >>> print(report)

    """

    def __init__(
        self, catch_errors: list[str], ignore_files: list[str], ignore_errors: list[str]
    ) -> None:
        """Create a new LogProcessor instance.

        Args:
            catch_errors: List of error patterns to catch.
            ignore_files: List of file patterns to ignore.
            ignore_errors: List of error patterns to ignore.

        """

    def process_logs(self, log_dir: Path) -> str:
        """Process log files in the specified directory and return formatted error report.

        Args:
            log_dir: Directory containing log files to scan.

        Returns:
            Formatted error report as string.

        """

def process_logs(
    log_dir: Path,
    catch_errors: list[str],
    ignore_files: list[str],
    ignore_errors: list[str],
) -> str:
    """Provide convenience wrapper to process logs without creating processor instance.

    Args:
        log_dir: Directory containing log files.
        catch_errors: List of error patterns to catch.
        ignore_files: List of file patterns to ignore.
        ignore_errors: List of error patterns to ignore.

    Returns:
        Formatted error report as string.

    """

# ============================================================================
# INI Validation
# ============================================================================

class IssueSeverity(Enum):
    """Severity level for configuration issues."""

    Info = "Info"
    Warning = "Warning"
    Error = "Error"

class ConfigIssue:
    """Configuration issue found in INI file.

    Attributes:
        file_path: Path to the configuration file.
        section: Section name in the INI file.
        setting: Setting name.
        current_value: Current value of the setting.
        recommended_value: Recommended value to fix the issue.
        description: Description of the issue.
        severity: Severity level.

    """

    file_path: Path
    section: str
    setting: str
    current_value: str
    recommended_value: str
    description: str
    severity: IssueSeverity

class IniValidator:
    """Validates game configuration INI files for common issues.

    10-30x faster than Python implementations with cached parsing.

    Example:
        >>> validator = IniValidator("Fallout4")
        >>> report = validator.validate_inis(Path("/path/to/game"))
        >>> print(report)

    """

    def __init__(self, game_name: str) -> None:
        """Create a new IniValidator instance.

        Args:
            game_name: Name of the game (e.g., "Fallout4").

        """

    def validate_inis(self, game_root: Path) -> str:
        """Validate INI files in a game directory.

        Args:
            game_root: Root directory of the game installation.

        Returns:
            Formatted validation report string.

        """

    def detect_all_issues(self, config_files: dict[str, Path]) -> list[ConfigIssue]:
        """Detect all configuration issues in the loaded files.

        Args:
            config_files: Dictionary mapping config names to file paths.

        Returns:
            List of ConfigIssue objects.

        """

# ============================================================================
# TOML/Crashgen Validation
# ============================================================================

class TomlIssueSeverity(Enum):
    """Severity level for TOML configuration issues."""

    Info = "Info"
    Warning = "Warning"
    Error = "Error"

class TomlConfigIssue:
    """TOML configuration issue found.

    Attributes:
        file_path: Path to the TOML configuration file.
        section: Section name in the TOML file.
        setting: Setting name.
        current_value: Current value of the setting.
        recommended_value: Recommended value to fix the issue.
        description: Description of the issue.
        severity: Severity level.

    """

    file_path: Path
    section: str
    setting: str
    current_value: str
    recommended_value: str
    description: str
    severity: TomlIssueSeverity

class CrashgenChecker:
    """Validates Buffout4/crash generator TOML configuration files.

    Example:
        >>> checker = CrashgenChecker(Path("/path/to/plugins"), "Buffout4")
        >>> message, issues = checker.check()
        >>> print(message)
        >>> for issue in issues:
        ...     print(f"{issue.description}")

    """

    def __init__(
        self,
        plugins_path: Path,
        crashgen_name: str,
        settings_rules: dict[str, object] | None = None,
    ) -> None:
        """Create a new CrashgenChecker instance.

        Args:
            plugins_path: Path to plugins directory.
            crashgen_name: Name of crash generator (e.g., "Buffout4").

        """

    def check(self) -> tuple[str, list[TomlConfigIssue]]:
        """Check TOML configuration for issues.

        Returns:
            Tuple of (message_string, list of TomlConfigIssue objects).

        """

def check_crashgen_config(
    plugins_path: Path,
    crashgen_name: str,
    settings_rules: dict[str, object] | None = None,
) -> tuple[str, list[TomlConfigIssue]]:
    """Provide convenience wrapper to check crashgen config without creating checker instance.

    Args:
        plugins_path: Path to plugins directory.
        crashgen_name: Name of crash generator.

    Returns:
        Tuple of (message_string, list of TomlConfigIssue objects).

    """

# ============================================================================
# Crashgen Orchestrator
# ============================================================================

class CrashgenReport:
    """Structured report returned by CrashgenCheckOrchestrator."""

    message: str
    issues: list[TomlConfigIssue]
    crashgen_name: str
    config_path: Path | None
    installed_plugins: list[str]

class CrashgenCheckOrchestrator:
    """High-level crashgen settings orchestrator."""

    def __init__(self) -> None:
        """Create a new CrashgenCheckOrchestrator instance."""

    @staticmethod
    def check(
        plugins_path: Path,
        crashgen_name: str,
        settings_rules: dict[str, object] | None = None,
    ) -> CrashgenReport:
        """Run full crashgen settings validation."""

    @staticmethod
    def detect_plugins(plugins_path: Path) -> list[str]:
        """Detect installed crashgen plugin DLL names."""

    @staticmethod
    def resolve_config_path(plugins_path: Path) -> Path | None:
        """Resolve crashgen TOML config path, if present."""

def check_crashgen_settings(
    plugins_path: Path,
    crashgen_name: str,
    settings_rules: dict[str, object] | None = None,
) -> tuple[str, list[TomlConfigIssue]]:
    """Convenience wrapper for crashgen settings validation."""

# ============================================================================
# Config Cache and Mod INI Scanning
# ============================================================================

class VsyncEntry:
    """VSync-enabled setting discovered in a config file."""

    file_path: Path
    setting: str

class DuplicateEntry:
    """Duplicate config filename with all discovered paths."""

    file_name: str
    paths: list[Path]

class ModIniScanResult:
    """Structured mod INI scan output."""

    message: str
    issues: list[ConfigIssue]
    vsync_files: list[VsyncEntry]
    duplicates: list[DuplicateEntry]

class RustConfigFileCache:
    """Encoding-aware Rust config file cache."""

    def __init__(
        self, game_root: Path, duplicate_whitelist: list[str] | None = ...
    ) -> None:
        """Create a new RustConfigFileCache instance."""

    def contains(self, file_name_lower: str) -> bool:
        """Check if file exists in cache."""

    def get_path(self, file_name_lower: str) -> Path | None:
        """Get path for a cached config file."""

    def get_str(self, file_name_lower: str, section: str, setting: str) -> str | None:
        """Get string value."""

    def get_bool(self, file_name_lower: str, section: str, setting: str) -> bool | None:
        """Get boolean value."""

    def get_int(self, file_name_lower: str, section: str, setting: str) -> int | None:
        """Get integer value."""

    def get_float(
        self, file_name_lower: str, section: str, setting: str
    ) -> float | None:
        """Get float value."""

    def has_setting(self, file_name_lower: str, section: str, setting: str) -> bool:
        """Check whether setting exists."""

    def config_files(self) -> dict[str, Path]:
        """Return config file map (lowercase filename -> path)."""

    def get_duplicates(self) -> dict[str, list[Path]]:
        """Return duplicate file map."""

class RustModIniScanner:
    """Rust scanner for mod INI validation and duplicate checks."""

    def __init__(self) -> None:
        """Create a new RustModIniScanner instance."""

    @staticmethod
    def scan(game_root: Path, game_name: str) -> ModIniScanResult:
        """Run a mod INI scan."""

def scan_mod_inis(game_root: Path, game_name: str) -> str:
    """Convenience wrapper returning formatted mod INI scan report."""

# ============================================================================
# Wrye Bash Parsing
# ============================================================================

class WryeSeverity(Enum):
    """Severity level for Wrye Bash issues."""

    Info = "Info"
    Warning = "Warning"
    Error = "Error"

class WryeIssue:
    """Issue extracted from Wrye Bash ModChecker report."""

    section_title: str
    plugins: list[str]
    warning_message: str | None
    severity: WryeSeverity

class WryeBashParser:
    """Parser for Wrye Bash Plugin Checker HTML reports."""

    def __init__(self, wrye_warnings: dict[str, str] | None = ...) -> None:
        """Create a new WryeBashParser instance."""

    def parse(self, html_content: str) -> list[WryeIssue]:
        """Parse HTML report into structured issues."""

    @staticmethod
    def format_report(issues: list[WryeIssue]) -> str:
        """Format structured issues as a report string."""

def parse_wrye_report(
    html_content: str, wrye_warnings: dict[str, str] | None = ...
) -> str:
    """Convenience wrapper to parse and format a Wrye report."""

# ============================================================================
# XSE Plugin Checking
# ============================================================================

class GameVersion(Enum):
    """Game version enum for XSE validation."""

    Null = "Null"
    Original = "Original"
    NextGen = "NextGen"
    AnniversaryEdition = "AnniversaryEdition"
    Vr = "Vr"

class ValidationResult(Enum):
    """Result of XSE plugin validation."""

    CorrectVersion = "CorrectVersion"
    WrongVersion = "WrongVersion"
    NotFound = "NotFound"
    VersionNotDetected = "VersionNotDetected"
    PluginsPathNotFound = "PluginsPathNotFound"

class AddressLibInfo:
    """Information about Address Library for a specific game version.

    Attributes:
        version: Version constant.
        filename: Filename of the Address Library file.
        description: Human-readable description.
        url: Nexus Mods URL for download.

    """

    version: GameVersion
    filename: str
    description: str
    url: str

    @staticmethod
    def vr() -> AddressLibInfo:
        """Get Address Library info for VR version.

        Returns:
            AddressLibInfo for VR.

        """

    @staticmethod
    def original() -> AddressLibInfo:
        """Get Address Library info for Original version.

        Returns:
            AddressLibInfo for Original.

        """

    @staticmethod
    def next_gen() -> AddressLibInfo:
        """Get Address Library info for Next-Gen version.

        Returns:
            AddressLibInfo for Next-Gen.

        """

class XseChecker:
    """Validates Address Library installation for F4SE/SKSE plugins.

    Example:
        >>> # Simplest usage (defaults to Original mode)
        >>> checker = XseChecker(Path("/path/to/plugins"))
        >>> result = checker.check()
        >>> message = checker.validate()
        >>> print(message)
        >>>
        >>> # Or specify game version explicitly
        >>> checker = XseChecker(
        ...     Path("/path/to/plugins"),
        ...     game_version=GameVersion.NextGen
        ... )

    """

    def __init__(
        self,
        plugins_path: Path,
        game_version: GameVersion = ...,
    ) -> None:
        """Create a new XseChecker instance.

        Args:
            plugins_path: Path to plugins directory.
            game_version: Game version enum (uses Original if not specified).

        """

    def check(self) -> ValidationResult:
        """Perform the validation check.

        Returns:
            ValidationResult indicating the status of the Address Library installation.

        """

    def validate(self) -> str:
        """Perform validation and return formatted message.

        Returns:
            Formatted validation message string.

        """

def check_xse_plugins(plugins_path: Path, game_version: GameVersion) -> str:
    """Provide convenience wrapper to validate XSE plugins without creating checker instance.

    Args:
        plugins_path: Path to F4SE/SKSE plugins directory.
        game_version: Detected game version.

    Returns:
        Formatted validation message.

    """

# ============================================================================
# ENB Detection
# ============================================================================

class EnbResult(Enum):
    """Result of ENB binary check."""

    Present = "Present"
    Partial = "Partial"
    NotInstalled = "NotInstalled"

class EnbConfigResult(Enum):
    """Result of ENB config check."""

    Valid = "Valid"
    NotFound = "NotFound"
    Unreadable = "Unreadable"

class EnbValidationResult:
    """Combined result of ENB validation.

    Attributes:
        binaries: Whether ENB binaries are present.
        config: Whether ENB config is valid.

    """

    binaries: EnbResult
    config: EnbConfigResult

    def is_present(self) -> bool:
        """Check if ENB is present (binaries exist).

        Returns:
            True if ENB binaries are Present or Partial.

        """

    def is_fully_configured(self) -> bool:
        """Check if ENB is fully configured (binaries + config).

        Returns:
            True if binaries are Present and config is Valid.

        """

class EnbChecker:
    """Checks for ENB installation in a game directory.

    Example:
        >>> checker = EnbChecker("C:/Games/Fallout4")
        >>> result = checker.validate()
        >>> if result.is_present():
        ...     print("ENB detected")

    """

    def __init__(self, game_path: str) -> None:
        """Create a new EnbChecker instance.

        Args:
            game_path: Path to the game root directory.

        """

    def check_binaries(self) -> EnbResult:
        """Check if ENB binaries exist.

        Returns:
            EnbResult indicating the status of ENB binaries.

        """

    def check_config(self) -> EnbConfigResult:
        """Check if ENB config exists.

        Returns:
            EnbConfigResult indicating the status of ENB config.

        """

    def validate(self) -> EnbValidationResult:
        """Perform combined validation.

        Returns:
            EnbValidationResult with binaries and config status.

        """

    def format_message(self, result: EnbValidationResult) -> str:
        """Format a user-friendly message.

        Args:
            result: Validation result to format.

        Returns:
            Formatted message string.

        """

def check_enb(game_path: str) -> EnbValidationResult:
    """Check ENB installation.

    Args:
        game_path: Path to the game root directory.

    Returns:
        EnbValidationResult with binaries and config status.

    """

# ============================================================================
# Game Integrity Checking
# ============================================================================

class CheckType:
    """Type of integrity check performed."""

    @staticmethod
    def executable_version() -> CheckType:
        """Create ExecutableVersion check type."""

    @staticmethod
    def installation_location() -> CheckType:
        """Create InstallationLocation check type."""

    def is_executable_version(self) -> bool:
        """Check if this is an ExecutableVersion check."""

    def is_installation_location(self) -> bool:
        """Check if this is an InstallationLocation check."""

class IntegrityCheckResult:
    """Result of a single integrity check.

    Attributes:
        check_type: Type of check performed.
        is_valid: Whether the check passed.
        message: Detailed message about the check result.

    """

    check_type: CheckType
    is_valid: bool
    message: str

class IntegrityConfig:
    """Configuration for game integrity checking.

    Contains all settings needed to perform comprehensive game integrity checks
    including executable verification, INI validation, and version detection.
    """

    def __init__(
        self, executable_path: Path, valid_exe_hashes: list[str], game_name: str
    ) -> None:
        """Create a new integrity check configuration.

        Args:
            executable_path: Path to the game executable.
            valid_exe_hashes: List of valid SHA256 hashes for known game versions.
            game_name: Display name of the game.

        """

    @property
    def game_exe_path(self) -> Path:
        """Get the game executable path."""

    @property
    def valid_exe_hashes(self) -> list[str]:
        """Get the list of valid executable hashes."""

    @property
    def root_name(self) -> str:
        """Get the game root name."""

    @property
    def steam_ini_path(self) -> Path | None:
        """Get the Steam INI file path."""

    @property
    def root_warn(self) -> str | None:
        """Get the root warning message."""

    def with_steam_ini(self, ini_path: Path) -> IntegrityConfig:
        """Set the Steam INI file path (builder pattern).

        Args:
            ini_path: Path to steam_api.ini or similar.

        Returns:
            Self for method chaining.

        """

    def with_root_warn(self, root_warn: str) -> IntegrityConfig:
        """Set the root warning message (builder pattern).

        Args:
            root_warn: Warning message for Program Files installation.

        Returns:
            Self for method chaining.

        """

class GameIntegrityChecker:
    """Game integrity checker for comprehensive game validation.

    Performs multiple checks including:
    - Executable hash verification
    - Version detection
    - INI file validation
    - File structure integrity

    20-40x faster than Python implementations.
    """

    def __init__(self, config: IntegrityConfig) -> None:
        """Create a new game integrity checker.

        Args:
            config: Configuration for integrity checks.

        """

    def check_executable_version(self) -> IntegrityCheckResult:
        """Check executable version.

        Returns:
            IntegrityCheckResult for executable version verification.

        """

    def check_installation_location(self) -> IntegrityCheckResult:
        """Check installation location.

        Returns:
            IntegrityCheckResult for installation location check.

        """

    def run_all_checks(self) -> list[IntegrityCheckResult]:
        """Run all integrity checks and return individual results.

        Returns:
            List of IntegrityCheckResult objects for each check performed.

        Example:
            >>> checker = GameIntegrityChecker(config)
            >>> results = checker.run_all_checks()
            >>> for result in results:
            ...     print(f"{result.check_type}: {result.is_valid}")

        """

    def run_full_check(self) -> str:
        """Run all integrity checks and return formatted message.

        Returns:
            A formatted message string with all check results.

        Example:
            >>> checker = GameIntegrityChecker(config)
            >>> message = checker.run_full_check()
            >>> print(message)

        """

# ============================================================================
# Game Scan Orchestrator
# ============================================================================

class CheckResult:
    """Single game-check output block."""

    name: str
    output: str

class GameScanResult:
    """Output of orchestrated game checks."""

    report: str
    check_results: list[CheckResult]
    errors: list[str]

    @property
    def config_issues(self) -> list[ConfigIssue]:
        """Structured config issues discovered during checks."""

class ModScanResult:
    """Output of orchestrated mod scans."""

    report: str
    unpacked_issue_count: int
    archived_issue_count: int
    errors: list[str]

class GameScanConfig:
    """Configuration for GameScanOrchestrator."""

    def __init__(
        self,
        game_path: Path,
        xse_acronym: str,
        crashgen_name: str,
        game_name: str,
        docs_path: Path | None = ...,
        mods_path: Path | None = ...,
        xse_scriptfiles: dict[str, list[str]] | None = ...,
        plugins_path: Path | None = ...,
        is_vr: bool = False,
        game_version: GameVersion | None = ...,
        wrye_warnings: dict[str, str] | None = ...,
        log_catch_errors: list[str] | None = ...,
        log_exclude_files: list[str] | None = ...,
        log_exclude_errors: list[str] | None = ...,
        crashgen_settings_rules: dict[str, object] | None = ...,
        game_target: str | None = ...,
    ) -> None:
        """Create a new game scan configuration."""

    @property
    def game_path(self) -> Path:
        """Get game root path."""

    @property
    def xse_acronym(self) -> str:
        """Get XSE acronym."""

    @property
    def game_name(self) -> str:
        """Get game name."""

class GameScanOrchestrator:
    """Coordinates concurrent game checks and mod scans."""

    def __init__(self, config: GameScanConfig) -> None:
        """Create a new GameScanOrchestrator."""

    def run_game_checks(self) -> GameScanResult:
        """Run game checks."""

    def run_mod_scans(self) -> ModScanResult:
        """Run mod scans."""

    def run_full_scan(self) -> tuple[GameScanResult, ModScanResult]:
        """Run full scan pipeline."""

# ============================================================================
# Game Setup Intake
# ============================================================================

class GameSetupIntake:
    """Read-only request for resolving and validating game setup inputs."""

    def __init__(
        self,
        game_id: str,
        game_version: str = ...,
        game_root: Path | None = ...,
        docs_root: Path | None = ...,
        xse_log_path: Path | None = ...,
    ) -> None:
        """Create a new Game Setup Intake request."""

    @property
    def game_id(self) -> str:
        """Stable game identifier."""

    @property
    def game_version(self) -> str:
        """Selected game version."""

    @property
    def game_root(self) -> str | None:
        """Saved or caller-provided game root."""

    @property
    def docs_root(self) -> str | None:
        """Saved or caller-provided documents root."""

    @property
    def xse_log_path(self) -> str | None:
        """Optional XSE log path used as a detection hint."""

class GameSetupCheck:
    """Typed Game Setup Check result."""

    kind: str
    state: str
    message: str
    details: list[str]

class GameSetupIntakeResult:
    """Rendered and typed result from Game Setup Intake."""

    rendered_report: str
    status: str
    has_errors: bool
    total_checks: int
    failed_checks: int
    action_count: int
    path_update_count: int
    game_root: str | None
    docs_root: str | None
    checks: list[GameSetupCheck]

    def combined(self) -> str:
        """Return the rendered report."""

def run_game_setup_intake(intake: GameSetupIntake) -> GameSetupIntakeResult:
    """Run Game Setup Intake."""

def normalize_game_setup_version_selection(game_version: str | None = ...) -> str:
    """Normalize a raw Game Setup Intake version selection."""

def game_setup_needs_path_detection(
    game_path: str | None = ..., docs_path: str | None = ...
) -> tuple[bool, bool]:
    """Return whether game/docs paths require Game Setup Intake detection."""

# ============================================================================
# Game Report Builders
# ============================================================================

def get_scan_issue_messages(xse_acronym: str, mode: str) -> dict[str, list[str]]:
    """Get issue message templates for scan reports."""

def build_unpacked_report(
    issue_lists: dict[str, list[str] | set[str] | tuple[str, ...]],
    xse_acronym: str,
) -> str:
    """Build report for unpacked (loose) files scan."""

def build_archived_report(
    issue_lists: dict[str, list[str] | set[str] | tuple[str, ...]],
    xse_acronym: str,
) -> str:
    """Build report for archived (BA2) files scan."""

def build_combined_scan_report(
    unpacked_issues: dict[str, list[str] | set[str] | tuple[str, ...]],
    archived_issues: dict[str, list[str] | set[str] | tuple[str, ...]],
    xse_acronym: str,
) -> str:
    """Build combined unpacked + archived scan report."""

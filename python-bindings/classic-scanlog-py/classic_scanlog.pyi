"""Type stubs for classic_scanlog Rust extension module.

This standalone module provides high-performance crash log analysis with:
- Fast log parsing with pattern matching (150x speedup)
- FormID extraction and validation (50x speedup)
- Plugin and record detection (30-40x speedup)
- Aggregate semantic Mod Guidance analysis
- Independent batch analysis helpers
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from classic_shared import GameId

__version__: str

# =============================================================================
# Crashgen Version Helpers
# =============================================================================

class CrashgenVersion:
    """Parsed crash generator version."""

    def __init__(self, version_str: str) -> None:
        """Parse a crash generator version string."""

    @property
    def major(self) -> int:
        """Major version component."""

    @property
    def minor(self) -> int:
        """Minor version component."""

    @property
    def patch(self) -> int:
        """Patch version component."""

    @property
    def original(self) -> str:
        """Original input string."""

    def to_tuple(self) -> tuple[int, int, int]:
        """Return ``(major, minor, patch)``."""

    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class CrashgenVersionStatus:
    """Enum-like crash generator version validation status."""

    VALID: str
    OUTDATED: str
    NEWER_THAN_KNOWN: str
    NO_SUPPORTED_VERSION: str

def parse_crashgen_version(version_str: str) -> CrashgenVersion | None:
    """Parse a crash generator version string."""

def check_crashgen_version_status(
    detected_version: str, valid_versions: list[str]
) -> CrashgenVersionStatus:
    """Check a crash generator version against a list of valid versions."""

# =============================================================================
# Cancellation Support
# =============================================================================

class FormIDAnalyzer:
    """Pure Rust FormID analyzer implementation.

    This is a direct Rust implementation without Python fallback,
    providing maximum performance for FormID operations.
    """
    def __init__(self) -> None:
        """Create Rust FormID analyzer."""

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """Extract FormIDs from callstack segment.

        Args:
            segment_callstack: List of callstack lines to search

        Returns:
            List of FormID strings

        """

    def parse_formid(self, formid: str) -> int | None:
        """Parse and validate a FormID string.

        Args:
            formid: FormID string (hex format)

        Returns:
            Parsed FormID as integer or None if invalid

        """

    def analyze_batch(
        self, formids: list[str], plugins: dict[str, str]
    ) -> list[tuple[str, str | None]]:
        """Batch analyze FormIDs with plugin resolution.

        Args:
            formids: List of FormID strings to analyze
            plugins: Dictionary mapping plugin names to details

        Returns:
            List of (formid, resolved_plugin_name) tuples

        """

    def clear_cache(self) -> None:
        """Clear all caches."""

    def cache_stats(self) -> tuple[int, int]:
        """Get cache statistics.

        Returns:
            Tuple of (cache_entries, cache_size_bytes)

        """

# =============================================================================
# Log Parsing
# =============================================================================

class LogParser:
    """High-performance log parser (150x speedup).

    Parses crash logs and extracts all relevant segments including
    main error, callstack, plugins, system info, and more.
    """

    def __init__(self, custom_boundaries: list[tuple[str, str]] | None = None) -> None:
        """Create a new LogParser instance.

        Args:
            custom_boundaries: Optional list of (start_marker, end_marker) tuples defining
                custom log segment boundaries.

        """

    def add_pattern(self, name: str, pattern: str) -> None:
        """Add a custom regex pattern for matching."""

    def clear_caches(self) -> None:
        """Clear all caches to free memory."""

    def parse_segments_parallel(
        self, lines: list[str], chunk_size: int | None = None
    ) -> dict[str, list[str]]:
        """Parse segments in parallel for large logs.

        .. deprecated::
            Use :meth:`parse_all_sections` instead, which returns ``dict[str, list[str]]``.

        """

    def find_patterns(self, lines: list[str]) -> list[tuple[int, str, str]]:
        """Find all pattern matches in parallel with caching."""

    def find_patterns_chunked(
        self, lines: list[str], chunk_size: int | None = None
    ) -> list[tuple[int, str, str]]:
        """Find patterns in parallel chunks for better performance."""

    def extract_section(
        self, lines: list[str], start_marker: str, end_marker: str
    ) -> list[str] | None:
        """Extract section from log."""

    def extract_sections_batch(
        self, lines: list[str], markers: list[tuple[str, str]]
    ) -> list[list[str] | None]:
        """Extract multiple sections batch."""

    def parse_crash_header(self, lines: list[str]) -> dict[str, str]:
        """Parse crash header information."""

    def get_section(self, lines: list[str], section_name: str) -> list[str] | None:
        """Get specific section by name."""

    def parse_all_sections(self, lines: list[str]) -> dict[str, list[str]]:
        """Parse and extract all important sections at once."""

    def parse_complete(
        self,
        lines: list[str],
    ) -> ScanOutput:
        """Optimized batch operation: complete log analysis in single FFI call.

        Returns:
            ScanOutput object containing metadata and segments.

        """

    def get_segment_sizes(self, lines: list[str]) -> dict[str, int]:
        """Count lines in each segment for analysis."""

    def get_stats(self) -> dict[str, int]:
        """Get performance statistics."""

    def extract_formids(self, lines: list[str]) -> list[str]:
        """Find all FormIDs in the log."""

    def extract_plugins(self, lines: list[str]) -> list[tuple[str, str]]:
        """Find all plugins mentioned in the log."""

    def extract_addresses(self, lines: list[str]) -> list[str]:
        """Find all memory addresses in the log."""

    def find_errors(self, lines: list[str]) -> list[tuple[int, str]]:
        """Find error and exception patterns."""

    def benchmark(self, lines: list[str], iterations: int) -> dict[str, float]:
        """Benchmark parsing performance on given data."""

    def detect_vr_log(self, content: str) -> bool:
        """Detect if a crash log is from Fallout 4 VR.

        Args:
            content: Crash log content string

        Returns:
            True if VR indicators are found

        """

class ScanOutput:
    """Result of optimized complete log parsing.

    ``segments`` is a ``dict[str, list[str]]`` with all 8 named keys always
    present: ``settings``, ``system``, ``callstack``, ``modules``,
    ``xse_modules``, ``plugins``, ``registers``, ``stack_dump``.
    """

    game_version: str
    crashgen_version: str
    main_error: str
    segments: dict[str, list[str]]

# =============================================================================
# Pattern Matching
# =============================================================================

class PatternMatcher:
    """Pattern matching with compiled regex patterns.

    Pre-compiles patterns for efficient repeated matching operations
    with automatic caching.
    """

    def __init__(self, patterns: list[str]) -> None:
        """Create pattern matcher with compiled patterns.

        Args:
            patterns: List of regex pattern strings to compile

        Raises:
            ValueError: If any pattern has invalid regex syntax

        """

    def find_all(self, text: str) -> list[tuple[int, str]]:
        """Find all matches in text.

        Args:
            text: Text to search

        Returns:
            List of (position, matched_text) tuples

        """

    def has_match(self, text: str) -> bool:
        """Check if text has any match.

        Args:
            text: Text to search

        Returns:
            True if at least one pattern matches

        """

    def find_first(self, text: str) -> tuple[int, str] | None:
        """Find first match in text.

        Args:
            text: Text to search

        Returns:
            (position, matched_text) tuple or None if no match

        """

    def replace_all(self, text: str, replacement: str) -> str:
        """Replace all matches with replacement string.

        Args:
            text: Text to process
            replacement: Replacement string

        Returns:
            Text with all matches replaced

        """

    def clear_cache(self) -> None:
        """Clear pattern cache."""

    def get_stats(self) -> tuple[int, int]:
        """Get cache statistics.

        Returns:
            Tuple of (pattern_count, cache_size)

        """

# =============================================================================
# Plugin Analysis
# =============================================================================

class PluginAnalyzer:
    """Load-order parsing, limit validation, filtering, and batch utilities.

    Semantic call-stack matching is owned by PluginEvidenceAnalyzer.
    """

    def __init__(
        self,
        game_ignore_plugins: list[str],
        ignore_list: list[str],
        crashgen_name: str,
        game_version: str = "",
        game_version_vr: str = "",
    ) -> None:
        """Create plugin analyzer.

        Args:
            game_ignore_plugins: Legacy compatibility input; semantic ignores are configured on PluginEvidenceAnalyzer
            ignore_list: Additional custom plugins to ignore
            crashgen_name: Legacy compatibility input; Autoscan Report Assembly owns report prose
            game_version: Base game version string (default: empty)
            game_version_vr: VR version string if applicable (default: empty)

        """

    def loadorder_scan_log(
        self,
        segment_plugins: list[str],
        game_version: str | None = None,
        version_current: str | None = None,
    ) -> tuple[dict[str, str], bool, bool]:
        """Scan log for plugins and check limits.

        Scans segment plugins and extracts plugin information, returning a mapping of
        plugin names to their load order IDs/status along with plugin limit flags.

        Args:
            segment_plugins: List of plugin segment lines from crash log
            game_version: Optional game version for plugin limit detection
            version_current: Optional crashgen version for plugin limit detection

        Returns:
            Tuple containing:
                - Dict mapping plugin names to IDs/status
                - Boolean flag for plugin limit triggered
                - Boolean flag for limit check disabled

        """

    def check_plugin_limit(
        self, segment_plugins: list[str], game_version: str, version_current: str
    ) -> tuple[bool, bool]:
        """Check plugin limit.

        Args:
            segment_plugins: List of plugin segment lines
            game_version: Game version string
            version_current: Current crashgen version string

        Returns:
            Tuple of (plugin_limit_triggered, limit_check_disabled)

        """

    def filter_ignored_plugins(self, plugins: dict[str, str]) -> dict[str, str]:
        """Filter ignored plugins from crash log plugin list.

        Args:
            plugins: HashMap of plugin names to load order IDs

        Returns:
            HashMap with ignored plugins removed

        """

# =============================================================================
# Record Scanning
# =============================================================================

class RecordScanner:
    """Record scanning (40x speedup).

    Scans crash logs for specific named records using optimized
    pattern matching algorithms.
    """

    def __init__(self, target_records: list[str], ignore_records: list[str]) -> None:
        """Create record scanner.

        Args:
            target_records: List of target record names to scan for
            ignore_records: List of record names to ignore during scanning
        """

    def extract_records(self, segment_callstack: list[str]) -> list[str]:
        """Extract records from callstack segment.

        Extracts all matching records from the callstack without formatting.

        Args:
            segment_callstack: List of callstack lines to scan

        Returns:
            List of matched record names

        """

    def clear_cache(self) -> None:
        """Clear the scanner's internal cache.

        Clears any cached data used for optimizing repeated scans.
        """

class ScanRunConfiguration:
    """Explicit facts shared by Standard and Targeted scan requests."""

    def __init__(
        self,
        installation_root: str,
        game: GameId,
        game_version: str,
        show_formid_values: bool,
        simplify_logs: bool,
        formid_database_paths: list[str],
        unsolved_logs_destination: str | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        """Create scan facts with a typed ``classic_shared.GameId``.

        Raises:
            TypeError: If ``game`` is not a shared typed game identifier.
            ValueError: If ``game`` is an unrecognized typed identifier value.
            ImportError: If ``classic_shared`` cannot be imported.

        """

class ScanRunStandardSource:
    """Explicit Standard discovery inputs."""

    def __init__(
        self,
        base_directory: str,
        custom_scan_directory: str | None = None,
        configured_documents_root: str | None = None,
    ) -> None: ...

class ScanRunTargetedSource:
    """Explicit Targeted candidates in caller order."""

    def __init__(self, inputs: list[str]) -> None: ...

class ScanRunSetupContext:
    """Explicit run-scoped FCX setup facts."""

    game_root: str | None
    docs_root: str | None
    game_exe_path: str | None
    xse_log_path: str | None

    def __init__(
        self,
        game_root: str | None = None,
        docs_root: str | None = None,
        game_exe_path: str | None = None,
        xse_log_path: str | None = None,
    ) -> None: ...

class ScanRunUnsolvedLogs:
    """Opaque Standard-only Unsolved Logs policy."""

    @staticmethod
    def leave_in_place() -> ScanRunUnsolvedLogs: ...
    @staticmethod
    def move_to_configured_or_default() -> ScanRunUnsolvedLogs: ...
    @staticmethod
    def move_to_custom(destination: str) -> ScanRunUnsolvedLogs: ...

class ScanRunRequest:
    """Opaque invariant-preserving Standard or Targeted request."""

    intent: Literal["standard", "targeted"]

    @staticmethod
    def standard(
        configuration: ScanRunConfiguration,
        source: ScanRunStandardSource,
        unsolved_logs: ScanRunUnsolvedLogs,
    ) -> ScanRunRequest: ...
    @staticmethod
    def standard_with_fcx(
        configuration: ScanRunConfiguration,
        source: ScanRunStandardSource,
        unsolved_logs: ScanRunUnsolvedLogs,
        setup_context: ScanRunSetupContext,
    ) -> ScanRunRequest: ...
    @staticmethod
    def targeted(
        configuration: ScanRunConfiguration,
        source: ScanRunTargetedSource,
    ) -> ScanRunRequest: ...
    @staticmethod
    def targeted_with_fcx(
        configuration: ScanRunConfiguration,
        source: ScanRunTargetedSource,
        setup_context: ScanRunSetupContext,
    ) -> ScanRunRequest: ...

class ScanRunCancellation:
    """Opaque monotonic cancellation control for one scan run."""

    is_cancelled: bool

    def __init__(self) -> None: ...
    def cancel(self) -> None: ...

class ScanRunRejectedInput:
    """One Targeted candidate rejected during discovery."""

    path: str
    reason: str

class ScanRunDiscoveryResult:
    """Complete retained discovery data."""

    source: Literal["standard", "targeted"]
    accepted_logs: list[str]
    rejected_inputs: list[ScanRunRejectedInput]
    searched_locations: list[str]

class ScanRunSetupCheck:
    """One typed FCX setup check."""

    kind: str
    state: str
    message: str
    details: list[str]

class ScanRunSetupPathUpdate:
    """One proposed setup path update."""

    kind: str
    path: str

class ScanRunSetupResult:
    """Run-scoped FCX setup result."""

    status: str
    message: str | None
    rendered_report: str
    checks: list[ScanRunSetupCheck]
    path_updates: list[ScanRunSetupPathUpdate]
    configuration_issues: list[ConfigIssue]
    actions: list[str]
    fatal_errors: list[str]

class ScanRunLogFailure:
    """One structured processing or finalization failure."""

    stage: Literal["analysis", "report_write", "unsolved_logs_finalization"]
    message: str

class ScanRunLogResult:
    """Complete durable terminal result for one discovered Crash Log."""

    discovery_index: int
    crash_log: str
    autoscan_report: str | None
    disposition: Literal["succeeded", "failed", "cancelled_before_start"]
    failures: list[ScanRunLogFailure]
    message: str | None
    moved_to_unsolved_logs: bool
    processing_time_us: int
    processing_time_ms: int
    formid_count: int
    plugin_count: int
    suspect_count: int

class ScanRunYamlDataContentIdentity:
    """Exact-byte identity retained for one Installed YAML Data file."""

    sha256: str
    byte_len: int

class ScanRunInspectedYamlDataFile:
    """Selected metadata for one update-eligible Main or game file."""

    role: Literal["main", "game"]
    provenance: Literal["updated", "previous", "bundled"]
    schema_major: int
    schema_minor: int
    sha256: str
    byte_length: int

class ScanRunInstalledYamlDataDiagnostic:
    """One structured selection, fallback, validation, or generation diagnostic."""

    role: Literal["main", "game"] | None
    candidate: Literal["updated", "previous", "bundled"] | None
    path: Path | None
    kind: Literal[
        "cache_unavailable",
        "missing",
        "read",
        "invalid_utf8",
        "parse",
        "invalid_schema",
        "incompatible_schema",
        "invalid_role_data",
        "local_ignore_generated",
    ]
    message: str

class ScanRunInstalledYamlDataRunData:
    """Installed YAML Data metadata retained from one immutable run snapshot."""

    main: ScanRunInspectedYamlDataFile
    game_file: ScanRunInspectedYamlDataFile
    local_ignore_state: Literal[
        "existing",
        "generated",
        "recovery_required",
        "proceed_without_ignore",
    ]
    local_ignore_identity: ScanRunYamlDataContentIdentity
    diagnostics: list[ScanRunInstalledYamlDataDiagnostic]

class ScanRunLocalIgnoreRecoveryDecision:
    """Explicit Rust-owned choice for resuming Local Ignore recovery."""

    ProceedWithoutIgnore: ScanRunLocalIgnoreRecoveryDecision

class ScanRunContinuation:
    """Opaque process-local carrier for one paused Crash Log Scan Run."""

class ScanRunContinuationConsumedError(RuntimeError):
    """Raised when a recovery continuation is consumed more than once."""

    code: Literal["scan_run_continuation_consumed"]

class ScanRunResult:
    """Complete terminal Crash Log Scan Run result."""

    status: Literal[
        "completed",
        "no_crash_logs_found",
        "setup_failed",
        "local_ignore_recovery_required",
        "cancelled_before_discovery",
        "cancelled",
    ]
    discovery: ScanRunDiscoveryResult | None
    setup: ScanRunSetupResult | None
    installed_yaml_data: ScanRunInstalledYamlDataRunData | None
    continuation: ScanRunContinuation | None
    effective_concurrency: int | None
    message: str | None
    total: int
    succeeded: int
    failed: int
    cancelled: int
    logs: list[ScanRunLogResult]

class ScanRunInfrastructureError:
    """Typed run-wide failure that prevents a meaningful result."""

    stage: Literal[
        "request_validation",
        "discovery",
        "intake",
        "formid_database_access",
        "initialization",
        "internal_invariant",
    ]
    message: str
    path: str | None

class ScanRunLogEvent:
    """Common facts for one log-scoped observer event."""

    discovery_index: int
    crash_log: str
    completed: int
    total: int

class ScanRunEvent:
    """One tagged serialized observer event."""

    kind: Literal[
        "discovery_completed",
        "effective_concurrency_selected",
        "log_queued",
        "log_started",
        "log_phase",
        "log_finished",
    ]
    discovery: ScanRunDiscoveryResult | None
    effective_concurrency: int | None
    log: ScanRunLogEvent | None
    phase: Literal["setup", "parse", "analyze", "finalize"] | None
    disposition: Literal["succeeded", "failed", "cancelled_before_start"] | None

class ScanRunExecution:
    """Final operation envelope with adapter-only observer failure data."""

    result: ScanRunResult | None
    error: ScanRunInfrastructureError | None
    observer_error: str | None

def scan_run_execute(
    request: ScanRunRequest,
    cancellation: ScanRunCancellation,
    observer: Callable[[ScanRunEvent], None] | None = None,
    cancel_on_observer_error: bool = False,
) -> ScanRunExecution:
    """Execute one final-contract Crash Log Scan Run."""

def scan_run_resume(
    continuation: ScanRunContinuation,
    decision: ScanRunLocalIgnoreRecoveryDecision,
    cancellation: ScanRunCancellation,
    observer: Callable[[ScanRunEvent], None] | None = None,
    cancel_on_observer_error: bool = False,
) -> ScanRunExecution:
    """Resume retained work without repeating discovery or YAML Data selection."""


# =============================================================================
# Standalone Functions
# =============================================================================

def extract_formids_batch(segments: list[list[str]]) -> list[list[str]]:
    """Extract FormIDs from multiple callstack segments in parallel.

    Uses rayon for parallel processing across all segments.

    Args:
        segments: List of callstack segments, where each segment is a list of strings

    Returns:
        List of FormID lists for each segment

    """

def is_valid_formid(formid: str) -> bool:
    """Check if a FormID string is valid.

    Args:
        formid: FormID string to validate (hex format)

    Returns:
        True if valid FormID format (8-char hex)

    """

def validate_formids_batch(formids: list[str]) -> list[bool]:
    """Validate multiple FormIDs in parallel.

    Args:
        formids: List of FormID strings

    Returns:
        List of validation results (True for valid, False for invalid)

    """

def scan_records_batch(
    texts: list[list[str]], record_list: list[str], ignore_records: list[str]
) -> list[list[str]]:
    """Scan for records in multiple texts.

    Args:
        texts: List of texts to scan
        record_list: List of record names to find
        ignore_records: List of record names to ignore

    Returns:
        List of found records for each text

    """

def contains_record(
    text: str, target_records: list[str], ignore_records: list[str]
) -> bool:
    """Check if text contains a specific record.

    Args:
        text: Text to search
        target_records: List of record names to find
        ignore_records: List of record names to ignore

    Returns:
        True if record found in text

    """

def detect_plugins_batch(texts: list[str], plugin_list: list[str]) -> list[list[str]]:
    """Detect plugins in multiple texts.

    Args:
        texts: List of texts to search
        plugin_list: List of plugin names to detect

    Returns:
        List of detected plugins for each text

    """

def contains_plugin(text: str, plugin: str) -> bool:
    """Check if text contains a specific plugin reference.

    Args:
        text: Text to search
        plugin: Plugin name to find

    Returns:
        True if plugin found in text

    """

# =============================================================================
# Settings Validation (Phase 2)
# =============================================================================

class AnalyzerKind:
    """Stable focused-analyzer identifier."""

    CrashgenSettings: AnalyzerKind
    CrashSuspect: AnalyzerKind
    ModGuidance: AnalyzerKind
    PluginEvidence: AnalyzerKind
    FormIdFinding: AnalyzerKind
    NamedRecordFinding: AnalyzerKind

    @property
    def code(self) -> str:
        """Return the stable cross-language analyzer token."""

class CrashgenExpectationKind:
    """Semantic kind of a Crashgen Expectation outcome."""

    Notice: CrashgenExpectationKind
    Issue: CrashgenExpectationKind
    Success: CrashgenExpectationKind

    @property
    def value(self) -> str:
        """Return ``notice``, ``issue``, or ``success``."""

class AnalyzerSeverity:
    """Severity attached to a Crashgen Expectation outcome."""

    Info: AnalyzerSeverity
    Warning: AnalyzerSeverity
    Error: AnalyzerSeverity

    @property
    def value(self) -> str:
        """Return the stable lowercase severity token."""

class AutoscanReportPlacement:
    """YAML-owned destination for a Crashgen Expectation outcome."""

    Settings: AutoscanReportPlacement
    ErrorInformation: AutoscanReportPlacement

    @property
    def value(self) -> str:
        """Return ``settings`` or ``error_information``."""

class AnalyzerError(RuntimeError):
    """Typed focused-analyzer construction or execution failure."""

    analyzer_kind: AnalyzerKind
    code: str
    message: str

class ModGuidanceMatchState:
    """Semantic state shared by aggregate Mod Guidance result families."""

    Matched: ModGuidanceMatchState
    Missing: ModGuidanceMatchState
    GpuMismatch: ModGuidanceMatchState

    @property
    def value(self) -> str:
        """Return the stable cross-language match-state token."""

class ModGuidanceCriteriaKind:
    """Grouped match strategy for a frequent-crash or solution rule."""

    Any: ModGuidanceCriteriaKind
    All: ModGuidanceCriteriaKind

    @property
    def value(self) -> str:
        """Return ``any`` or ``all``."""

class ModGuidanceConflictRule:
    """Immutable owned conflict rule."""

    def __init__(
        self,
        mod_a: str,
        mod_b: str,
        name_a: str,
        name_b: str,
        description: str,
        fix: str,
        link: str | None = None,
    ) -> None: ...
    @property
    def mod_a(self) -> str: ...
    @property
    def mod_b(self) -> str: ...
    @property
    def name_a(self) -> str: ...
    @property
    def name_b(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def fix(self) -> str: ...
    @property
    def link(self) -> str | None: ...

class ModGuidanceSolutionRule:
    """Immutable owned frequent-crash or solution rule."""

    def __init__(
        self,
        id: str,
        criteria_kind: ModGuidanceCriteriaKind,
        criteria: list[str],
        exceptions: list[str],
        name: str,
        description: str,
    ) -> None: ...
    @property
    def id(self) -> str: ...
    @property
    def criteria_kind(self) -> ModGuidanceCriteriaKind: ...
    @property
    def criteria(self) -> list[str]: ...
    @property
    def exceptions(self) -> list[str]: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...

class ModGuidanceImportantModRule:
    """Immutable owned important-mod rule."""

    def __init__(
        self,
        detect: str,
        name: str,
        description: str,
        gpu: str | None = None,
        gpu_mismatch_warning: str | None = None,
        exclude_when_plugin_any: list[str] | None = None,
    ) -> None: ...
    @property
    def detect(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def gpu(self) -> str | None: ...
    @property
    def gpu_mismatch_warning(self) -> str | None: ...
    @property
    def exclude_when_plugin_any(self) -> list[str] | None: ...

class ModGuidanceAnalysisInput:
    """Immutable owned facts for one aggregate Mod Guidance call."""

    def __init__(
        self,
        plugins: dict[str, str],
        user_gpu: str | None = None,
        xse_modules: set[str] = ...,
    ) -> None: ...

class ModConflictGuidance:
    """Immutable semantic conflict result."""

    @property
    def state(self) -> ModGuidanceMatchState: ...
    @property
    def mod_a(self) -> str: ...
    @property
    def mod_b(self) -> str: ...
    @property
    def name_a(self) -> str: ...
    @property
    def name_b(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def fix(self) -> str: ...
    @property
    def link(self) -> str | None: ...

class ModSolutionGuidance:
    """Immutable semantic frequent-crash or solution result."""

    @property
    def state(self) -> ModGuidanceMatchState: ...
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def matched_plugin_ids(self) -> list[str]: ...

class ImportantModGuidance:
    """Immutable semantic important-mod result."""

    @property
    def state(self) -> ModGuidanceMatchState: ...
    @property
    def detect(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def gpu(self) -> str | None: ...
    @property
    def gpu_mismatch_warning(self) -> str | None: ...

class ModGuidanceAnalysisResult:
    """Completed aggregate analysis, including explicit empty success."""

    @property
    def conflicts(self) -> list[ModConflictGuidance]: ...
    @property
    def frequent_crashes(self) -> list[ModSolutionGuidance]: ...
    @property
    def solutions(self) -> list[ModSolutionGuidance]: ...
    @property
    def important_mods(self) -> list[ImportantModGuidance]: ...

class ModGuidanceAnalyzer:
    """Immutable analyzer over validated aggregate Mod Guidance rules."""

    def __init__(
        self,
        conflicts: list[ModGuidanceConflictRule],
        frequent_crashes: list[ModGuidanceSolutionRule],
        solutions: list[ModGuidanceSolutionRule],
        important_mods: list[ModGuidanceImportantModRule],
    ) -> None: ...
    @property
    def kind(self) -> AnalyzerKind: ...
    def analyze(self, input: ModGuidanceAnalysisInput) -> ModGuidanceAnalysisResult:
        """Run aggregate semantic analysis without producing report lines."""

class CrashSuspectFindingKind:
    """Evidence source that produced one Crash Suspect Finding."""

    MainErrorRule: CrashSuspectFindingKind
    StackRule: CrashSuspectFindingKind
    DllInvolvement: CrashSuspectFindingKind

    @property
    def value(self) -> str:
        """Return the stable cross-language finding-kind token."""

class CrashSuspectStackCountRule:
    """Immutable minimum-occurrence stack condition."""

    def __init__(self, substring: str, count: int) -> None: ...
    @property
    def substring(self) -> str: ...
    @property
    def count(self) -> int: ...

class CrashSuspectMainErrorRule:
    """Immutable owned main-error rule."""

    def __init__(
        self, id: str, name: str, severity: int, main_error_contains_any: list[str]
    ) -> None: ...
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def severity(self) -> int: ...
    @property
    def main_error_contains_any(self) -> list[str]: ...

class CrashSuspectStackRule:
    """Immutable owned stack rule."""

    def __init__(
        self,
        id: str,
        name: str,
        severity: int,
        main_error_required_any: list[str],
        main_error_optional_any: list[str],
        stack_contains_any: list[str],
        exclude_if_stack_contains_any: list[str],
        stack_contains_at_least: list[CrashSuspectStackCountRule],
    ) -> None: ...
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def severity(self) -> int: ...
    @property
    def main_error_required_any(self) -> list[str]: ...
    @property
    def main_error_optional_any(self) -> list[str]: ...
    @property
    def stack_contains_any(self) -> list[str]: ...
    @property
    def exclude_if_stack_contains_any(self) -> list[str]: ...
    @property
    def stack_contains_at_least(self) -> list[CrashSuspectStackCountRule]: ...

class CrashSuspectAnalysisInput:
    """Immutable owned input for one aggregate Crash Suspect analysis call."""

    def __init__(self, main_error: str, call_stack: str) -> None: ...

class CrashSuspectFinding:
    """Immutable semantic Crash Suspect Finding."""

    @property
    def kind(self) -> CrashSuspectFindingKind: ...
    @property
    def rule_id(self) -> str | None: ...
    @property
    def name(self) -> str | None: ...
    @property
    def severity(self) -> int | None: ...

class CrashSuspectAnalysisResult:
    """Completed analysis; an empty list explicitly means no findings."""

    @property
    def findings(self) -> list[CrashSuspectFinding]: ...

class CrashSuspectAnalyzer:
    """Immutable analyzer with validated, compiled Crash Suspect rules."""

    def __init__(
        self,
        main_error_rules: list[CrashSuspectMainErrorRule],
        stack_rules: list[CrashSuspectStackRule],
    ) -> None: ...
    @property
    def kind(self) -> AnalyzerKind: ...
    def analyze(self, input: CrashSuspectAnalysisInput) -> CrashSuspectAnalysisResult:
        """Run aggregate semantic analysis without producing report lines."""

class PluginEvidenceAnalysisInput:
    """Immutable owned input for one aggregate Plugin Evidence analysis call."""

    def __init__(self, call_stack: list[str], plugins: list[str]) -> None: ...

class PluginEvidence:
    """Immutable typed plugin identity and occurrence count."""

    @property
    def plugin(self) -> str: ...
    @property
    def occurrences(self) -> int: ...

class PluginEvidenceAnalysisResult:
    """Completed analysis; an empty list explicitly means no evidence."""

    @property
    def evidence(self) -> list[PluginEvidence]: ...

class PluginEvidenceAnalyzer:
    """Immutable analyzer with validated Plugin Evidence ignore configuration."""

    def __init__(self, ignored_plugins: list[str]) -> None: ...
    @property
    def kind(self) -> AnalyzerKind: ...
    def analyze(self, input: PluginEvidenceAnalysisInput) -> PluginEvidenceAnalysisResult:
        """Run aggregate semantic analysis without producing report lines."""

class FormIDFindingLookupReplyKind:
    """Callback-free deterministic lookup reply category."""

    Missing: FormIDFindingLookupReplyKind
    Found: FormIDFindingLookupReplyKind
    OperationalFailure: FormIDFindingLookupReplyKind

class FormIDFindingLookupEntry:
    """Immutable owned deterministic FormID lookup reply."""

    def __init__(
        self,
        formid: str,
        plugin: str,
        reply_kind: FormIDFindingLookupReplyKind,
        value: str | None = None,
        error_message: str | None = None,
    ) -> None: ...

class FormIDPlugin:
    """Immutable plugin identity and load-order prefix."""

    def __init__(self, name: str, prefix: str) -> None: ...

class FormIDFindingAnalysisInput:
    """Immutable owned input for one aggregate FormID Finding call."""

    def __init__(self, crash_lines: list[str], plugins: list[FormIDPlugin]) -> None: ...

class FormIDValueLookupStatus:
    """Semantic state of optional FormID Value Lookup."""

    NotApplicable: FormIDValueLookupStatus
    Disabled: FormIDValueLookupStatus
    Missing: FormIDValueLookupStatus
    Found: FormIDValueLookupStatus

class FormIDFinding:
    """Immutable distinct FormID Finding including unresolved identifiers."""

    @property
    def identifier(self) -> str: ...
    @property
    def occurrences(self) -> int: ...
    @property
    def plugin(self) -> str | None: ...
    @property
    def value_lookup_status(self) -> FormIDValueLookupStatus: ...
    @property
    def value(self) -> str | None: ...

class FormIDFindingAnalysisResult:
    """Completed semantic analysis, including explicit empty success."""

    @property
    def findings(self) -> list[FormIDFinding]: ...

class FormIDFindingAnalyzer:
    """Immutable aggregate FormID Finding analyzer."""

    def __init__(self) -> None: ...
    @staticmethod
    def in_memory(entries: list[FormIDFindingLookupEntry]) -> FormIDFindingAnalyzer: ...
    @staticmethod
    def sqlite(database_path: str, game_table: str) -> FormIDFindingAnalyzer: ...
    @property
    def kind(self) -> AnalyzerKind: ...
    def analyze(self, input: FormIDFindingAnalysisInput) -> FormIDFindingAnalysisResult:
        """Run async Rust analysis on the shared runtime while releasing the GIL."""

class NamedRecordFindingAnalysisInput:
    """Immutable owned input for one aggregate Named Record Finding analysis call."""

    def __init__(self, crash_lines: list[str]) -> None: ...

class NamedRecordFinding:
    """Immutable distinct named record and exact occurrence count."""

    @property
    def record(self) -> str: ...
    @property
    def occurrences(self) -> int: ...

class NamedRecordFindingAnalysisResult:
    """Completed analysis; an empty list explicitly means no findings."""

    @property
    def findings(self) -> list[NamedRecordFinding]: ...

class NamedRecordFindingAnalyzer:
    """Immutable analyzer with validated, compiled Named Record Finding configuration."""

    def __init__(
        self, target_records: list[str], ignored_records: list[str]
    ) -> None: ...
    @property
    def kind(self) -> AnalyzerKind: ...
    def analyze(
        self, input: NamedRecordFindingAnalysisInput
    ) -> NamedRecordFindingAnalysisResult:
        """Run aggregate semantic analysis without producing report lines."""

class CrashgenExpectationOutcome:
    """Immutable semantic result from one YAML-backed expectation."""

    @property
    def rule_id(self) -> str: ...
    @property
    def kind(self) -> CrashgenExpectationKind: ...
    @property
    def severity(self) -> AnalyzerSeverity: ...
    @property
    def message(self) -> str: ...
    @property
    def fix(self) -> str | None: ...
    @property
    def placement(self) -> AutoscanReportPlacement: ...
    @property
    def section(self) -> str | None: ...
    @property
    def setting(self) -> str | None: ...
    @property
    def expected(self) -> str | None: ...
    @property
    def actual(self) -> str | None: ...

class DisabledSettingNotice:
    """Immutable semantic notice for one non-ignored disabled setting."""

    @property
    def setting_name(self) -> str: ...

class CrashgenSettingsAnalysisInput:
    """Immutable owned input for one aggregate Crashgen Settings Analysis call."""

    def __init__(
        self,
        settings: dict[str, dict[str, str]],
        installed_plugins: set[str],
        crashgen_version: tuple[int, int, int] | None = None,
        config_layout: str | None = None,
    ) -> None:
        """Own settings, plugin, version, and layout facts for analysis."""

class CrashgenSettingsAnalysisResult:
    """Completed analysis; empty lists explicitly mean no findings."""

    @property
    def expectation_outcomes(self) -> list[CrashgenExpectationOutcome]: ...
    @property
    def disabled_setting_notices(self) -> list[DisabledSettingNotice]: ...

class CrashgenSettingsAnalyzer:
    """Immutable analyzer with validated, compiled Crashgen configuration."""

    def __init__(self, crashgen_name: str, crashgen_entry: dict[str, Any]) -> None:
        """Validate configuration and construct the shared analyzer handle."""

    @property
    def kind(self) -> AnalyzerKind:
        """Return ``AnalyzerKind.CrashgenSettings``."""

    def analyze(self, input: CrashgenSettingsAnalysisInput) -> CrashgenSettingsAnalysisResult:
        """Run aggregate semantic analysis without producing report lines."""

# =============================================================================
# GPU Detection (Phase 2)
# =============================================================================

class GpuVendor:
    """GPU vendor/manufacturer enumeration.

    Represents GPU vendors: AMD, Nvidia, Intel, or Unknown.
    """

    def __init__(self, vendor_name: str) -> None:
        """Create a new GpuVendor from vendor name string.

        Args:
            vendor_name: Vendor name (case-insensitive: "AMD", "NVIDIA", "INTEL")

        """

class GpuInfo:
    """Detected GPU information from crash log.

    Contains primary/secondary GPU details, manufacturer, and potential
    rival vendor for multi-GPU systems.
    """

    def __init__(self) -> None:
        """Create a new empty GpuInfo instance."""

    @property
    def primary(self) -> str:
        """Primary GPU name."""

    @property
    def secondary(self) -> str | None:
        """Secondary GPU name if present (for multi-GPU systems)."""

    @property
    def manufacturer(self) -> str:
        """GPU manufacturer/vendor name."""

    @property
    def rival(self) -> str | None:
        """Rival GPU vendor if detected (for multi-vendor systems)."""

    def to_dict(self) -> dict[str, str | None]:
        """Convert GPU info to a dictionary representation.

        Returns:
            Dictionary with keys: 'primary', 'secondary', 'manufacturer', 'rival'

        """

class GpuDetector:
    """GPU vendor detection from system info.

    Detects GPU information from crash log system specification sections.
    """

    def __init__(self) -> None:
        """Create GPU detector."""

    def extract_gpu_info(self, segment_system: list[str]) -> GpuInfo:
        """Extract GPU information from system specification.

        Args:
            segment_system: System specification lines from crash log

        Returns:
            Detected GPU information

        """

    def extract_gpu_info_batch(self, system_segments: list[list[str]]) -> list[GpuInfo]:
        """Batch extract GPU info from multiple logs.

        Args:
            system_segments: List of system specification segments from multiple logs

        Returns:
            List of GPU information for each log

        """

# =============================================================================
# FCX Mode Handler (Phase 2)
# =============================================================================

class ConfigIssue:
    """Represents a configuration issue detected during FCX mode checks.

    Used to report INI/TOML settings that deviate from recommended values
    for optimal game stability.
    """

    def __init__(
        self,
        file_path: str,
        section: str | None,
        setting: str,
        current_value: str,
        recommended_value: str,
        description: str,
        severity: str = "warning",
    ) -> None:
        """Create a new configuration issue.

        Args:
            file_path: Path to the configuration file
            section: INI section name (None for TOML or non-sectioned files)
            setting: Setting/key name
            current_value: Current value in the file
            recommended_value: Recommended value to fix the issue
            description: Human-readable description of the issue
            severity: Issue severity level ("error", "warning", "info")

        """

    @property
    def file_path(self) -> str:
        """Path to the configuration file."""

    @property
    def section(self) -> str | None:
        """INI section name (None for TOML or non-sectioned files)."""

    @property
    def setting(self) -> str:
        """Setting/key name."""

    @property
    def current_value(self) -> str:
        """Current value in the file."""

    @property
    def recommended_value(self) -> str:
        """Recommended value to fix the issue."""

    @property
    def description(self) -> str:
        """Human-readable description of the issue."""

    @property
    def severity(self) -> str:
        """Issue severity level ('error', 'warning', 'info')."""

# =============================================================================
# Test Classes
# =============================================================================

# =============================================================================
# Papyrus Log Analysis
# =============================================================================

class PapyrusError(Exception):
    """Raised on Papyrus log analysis failures.

    Phase 3 Plan 04 (Wave 3a): stub mirrors the Rust
    ``classic_scanlog_core::papyrus::PapyrusError`` enum so the parity
    contract row can resolve ``classic_scanlog.PapyrusError`` through
    ``classic_scanlog.pyi``. At runtime, current Papyrus error paths in
    :class:`PapyrusAnalyzer` still raise the standard Python
    ``FileNotFoundError`` / ``IOError`` / ``RuntimeError`` variants that
    the PyO3 wrapper converts from the underlying Rust enum. Callers that
    want a typed catch class can still ``except classic_scanlog.PapyrusError``
    once a future phase wires the create_exception! macro for it.
    """


class PapyrusStats:
    """Statistics from Papyrus log analysis.

    Provides metrics about Papyrus script execution including dumps,
    stacks, warnings, errors, and severity assessment.
    """

    def __init__(self) -> None:
        """Create a new empty statistics instance."""

    @property
    def dumps(self) -> int:
        """Number of 'Dumping Stacks' entries (plural)."""

    @property
    def stacks(self) -> int:
        """Number of 'Dumping Stack' entries (singular)."""

    @property
    def warnings(self) -> int:
        """Number of warning messages."""

    @property
    def errors(self) -> int:
        """Number of error messages."""

    @property
    def lines_processed(self) -> int:
        """Total lines processed from the log."""

    def dumps_to_stacks_ratio(self) -> float:
        """Calculate the dumps to stacks ratio.

        Returns:
            Ratio of dumps to stacks, or 0.0 if no dumps/stacks

        """

class PapyrusAnalyzer:
    """Analyzer for Papyrus script logs.

    Provides both one-time analysis and continuous monitoring (tail -f)
    capabilities for Papyrus.0.log files.
    """

    def __init__(self, log_path: str) -> None:
        """Create a new Papyrus analyzer for the given log file.

        Args:
            log_path: Path to the Papyrus.0.log file

        """

    def log_exists(self) -> bool:
        """Check if the log file exists.

        Returns:
            True if log file exists and is readable

        """

    def log_path(self) -> str:
        """Get the log file path.

        Returns:
            Path to the log file as string

        """

    def stats(self) -> PapyrusStats:
        """Get current statistics.

        Returns:
            Current PapyrusStats snapshot

        """

    def reset(self) -> None:
        """Reset statistics and position (start monitoring from beginning)."""

    def analyze_full(self) -> PapyrusStats:
        """Perform a full analysis of the log file from the beginning.

        This reads the entire file and calculates statistics.

        Returns:
            The collected statistics

        Raises:
            FileNotFoundError: If log file doesn't exist
            IOError: If failed to read the file

        """

    def analyze_to_string(self) -> str:
        """Analyze the log file and return formatted summary text.

        Returns:
            Formatted string with statistics, or error message if log not found

        """

    def start_monitoring(self) -> None:
        """Start monitoring from the END of the file (ignore prior history).

        This positions the analyzer at the end of the current file so that
        only NEW lines added after this point will be tracked.
        This implements true "tail -f" behavior for monitoring sessions.

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If can't read file metadata

        """

    def check_for_updates(self) -> tuple[list[str], PapyrusStats] | None:
        """Read and process only new lines added since last check (tail -f behavior).

        This implements incremental monitoring by only reading new content
        that has been appended to the file since the last read.

        Returns:
            Tuple of (new lines, updated statistics) if changes detected,
            None if no changes

        Raises:
            IOError: If failed to read the file or file was truncated

        """

def papyrus_logging(log_path: str) -> tuple[str, int]:
    """Provide convenience wrapper to analyze a Papyrus log file.

    This is equivalent to creating a PapyrusAnalyzer and calling
    analyze_to_string(), with the addition of returning the dumps count.

    Args:
        log_path: Path to the Papyrus.0.log file

    Returns:
        Tuple containing:
            - Formatted string with log analysis details
            - Total count of dumps extracted from the log

    Example:
        >>> from classic_scanlog import papyrus_logging
        >>> summary, dumps_count = papyrus_logging("/path/to/Papyrus.0.log")
        >>> print(summary)
        >>> print(f"Total dumps: {dumps_count}")

    """

"""Type stubs for classic_scanlog Rust extension module.

This standalone module provides high-performance crash log analysis with:
- Fast log parsing with pattern matching (150x speedup)
- FormID extraction and validation (50x speedup)
- Plugin and record detection (30-40x speedup)
- Mod detection algorithms (35x speedup)
- Parallel batch processing
- Report generation (75x speedup)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__version__: str

# =============================================================================
# FormID Analysis
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

    def analyze_batch(self, formids: list[str], plugins: dict[str, str]) -> list[tuple[str, str | None]]:
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

class FormIDAnalyzerCore:
    """Core FormID analysis functionality with optimizations.

    Provides high-performance FormID extraction, validation, and matching
    with zero-copy optimizations and plugin caching for repeated operations.
    """

    def __init__(
        self,
        show_formid_values: bool,
        crashgen_name: str,
        important_mods: dict[str, str],
        mods_single: dict[str, str],
        mods_double: dict[str, str],
    ) -> None:
        """Create FormID analyzer core.

        Args:
            show_formid_values: Whether to show FormID values in output
            crashgen_name: Name of the crash generator (e.g., "Buffout 4")
            important_mods: Dictionary of important/problematic plugins
            mods_single: Single-pass mod detection database
            mods_double: Double-pass mod detection database

        """

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """Extract FormIDs from callstack segment.

        Standard extraction method that processes a callstack segment
        and returns all found FormIDs.

        Args:
            segment_callstack: List of callstack lines to search

        Returns:
            List of FormID strings found in the segment

        """

    def extract_formids_nocopy(self, segment_callstack: list[str]) -> list[str]:
        """Extract FormIDs using zero-copy optimization.

        Optimized extraction that avoids unnecessary data copies by
        directly processing Python list strings.

        Args:
            segment_callstack: List of callstack lines to search

        Returns:
            List of FormID strings found in the segment

        """

    def cache_plugins(self, cache_key: str, plugins: dict[str, str]) -> None:
        """Cache plugin mappings for efficient repeated use.

        Stores plugin data on the Rust side to avoid repeated conversions
        from Python dictionaries. Use a stable cache_key to identify the
        plugin set.

        Args:
            cache_key: Unique identifier for this plugin set (e.g., MD5 hash)
            plugins: Dictionary mapping plugin names to paths/details

        """

    def process_formids_cached(self, formids: list[str], cache_key: str) -> list[str]:
        """Process FormIDs using cached plugin mappings.

        Uses previously cached plugins for efficient FormID matching and
        report generation without Python/Rust boundary overhead.

        Args:
            formids: List of FormID strings to process
            cache_key: Cache key from previous cache_plugins() call

        Returns:
            List of formatted report lines for the FormID matches

        """

    def formid_match(self, formids: list[str], plugins: dict[str, str], report: Any) -> None:
        """Match FormIDs to plugins and update report.

        Analyzes FormIDs against the plugin list and adds matching
        information to the report object.

        Args:
            formids: List of FormID strings to match
            plugins: Dictionary mapping plugin names to paths/details
            report: Report object to update with match results

        """

    def is_valid_formid(self, formid: str) -> bool:
        """Check if FormID string is valid.

        Args:
            formid: FormID string to validate

        Returns:
            True if valid hex FormID

        """

    def parse_formid(self, formid: str) -> int | None:
        """Parse FormID string to integer.

        Args:
            formid: FormID string (hex format)

        Returns:
            Parsed FormID integer or None if invalid

        """

    def extract_plugin_index(self, formid: str) -> int | None:
        """Extract plugin index from FormID.

        Args:
            formid: FormID string

        Returns:
            Plugin index (0-255) or None if invalid

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

    def parse_segments(self, lines: list[str]) -> list[list[str]]:
        """Parse log into segments using SIMD-optimized boundary detection."""

    def parse_segments_parallel(self, lines: list[str], chunk_size: int | None = None) -> list[list[str]]:
        """Parse segments in parallel for large logs."""

    def find_patterns(self, lines: list[str]) -> list[tuple[int, str, str]]:
        """Find all pattern matches in parallel with caching."""

    def find_patterns_chunked(self, lines: list[str], chunk_size: int | None = None) -> list[tuple[int, str, str]]:
        """Find patterns in parallel chunks for better performance."""

    def extract_section(self, lines: list[str], start_marker: str, end_marker: str) -> list[str] | None:
        """Extract section from log."""

    def extract_sections_batch(self, lines: list[str], markers: list[tuple[str, str]]) -> list[list[str] | None]:
        """Extract multiple sections batch."""

    def parse_crash_header(self, lines: list[str]) -> dict[str, str]:
        """Parse crash header information."""

    def get_section(self, lines: list[str], section_name: str) -> list[str] | None:
        """Get specific section by name."""

    def parse_all_sections(self, lines: list[str]) -> dict[str, list[str]]:
        """Parse and extract all important sections at once."""

    def parse_complete(self, lines: list[str], segment_boundaries: list[tuple[str, str]], xse_acronym: str) -> ScanOutput:
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
    """Result of optimized complete log parsing."""

    game_version: str
    crashgen_version: str
    main_error: str
    segments: list[list[str]]

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
    """Plugin matching and analysis (30x speedup).

    Analyzes plugin lists against configuration data to detect
    problematic plugins, conflicts, and missing dependencies.
    """

    def __init__(
        self,
        game_ignore_plugins: list[str],
        ignore_list: list[str],
        crashgen_name: str,
        game_version: str = "",
        game_version_vr: str = "",
        game_version_new: str = "",
    ) -> None:
        """Create plugin analyzer.

        Args:
            game_ignore_plugins: List of game-specific plugins to ignore during analysis
            ignore_list: Additional custom plugins to ignore
            crashgen_name: Name of the crash generator (e.g., "Buffout4", "Crash Logger")
            game_version: Base game version string (default: empty)
            game_version_vr: VR version string if applicable (default: empty)
            game_version_new: Next-gen/updated version string if applicable (default: empty)

        """

    def loadorder_scan_log(
        self, segment_plugins: list[str], game_version: str | None = None, version_current: str | None = None
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

    def check_plugin_limit(self, segment_plugins: list[str], game_version: str, version_current: str) -> tuple[bool, bool]:
        """Check plugin limit.

        Args:
            segment_plugins: List of plugin segment lines
            game_version: Game version string
            version_current: Current crashgen version string

        Returns:
            Tuple of (plugin_limit_triggered, limit_check_disabled)

        """

    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str]) -> list[str]:
        """Match plugins found in crash call stack.

        Args:
            segment_callstack_lower: Lowercase call stack lines
            crashlog_plugins_lower: Set of lowercase plugin names from crash log

        Returns:
            List of formatted report lines for plugin matches

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

    def __init__(self, target_records: list[str], ignore_records: list[str], crashgen_name: str) -> None:
        """Create record scanner.

        Args:
            target_records: List of target record names to scan for
            ignore_records: List of record names to ignore during scanning
            crashgen_name: Name of the crash generator (e.g., "Buffout4", "Crash Logger")

        """

    def scan_named_records(self, segment_callstack: list[str]) -> tuple[list[str], list[str]]:
        """Scan named records from callstack segment.

        Scans the callstack segment for configured named records and returns
        both the formatted report lines and the list of matched record names.

        Args:
            segment_callstack: List of callstack lines to scan

        Returns:
            Tuple containing:
                - List of formatted report lines
                - List of matched record names

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

# =============================================================================
# Orchestration
# =============================================================================

class Orchestrator:
    """End-to-end crash log analysis orchestration.

    Coordinates all analysis components with 10-100x performance improvements
    over the Python implementation. Provides both single-file and batch
    processing with automatic parallelization.
    """

    def __init__(self, config: AnalysisConfig) -> None:
        """Create a new orchestrator instance.

        Args:
            config: Analysis configuration containing game info and settings

        """

    def process_log(self, log_path: str) -> AnalysisResult:
        """Process a single crash log.

        Performs complete end-to-end analysis including:
        - Log parsing
        - Plugin analysis
        - FormID extraction and matching
        - Suspect detection
        - Settings validation
        - Mod detection
        - Report generation

        Args:
            log_path: Path to crash log file

        Returns:
            Complete analysis result

        Raises:
            IOError: If log file cannot be read
            ValueError: If log format is invalid

        """

    def process_logs_parallel(
        self, log_paths: list[str], max_concurrent: int = 10, progress_callback: Callable[[str], None] | None = None
    ) -> list[AnalysisResult]:
        """Process multiple crash logs in parallel.

        Uses rayon for CPU-bound parallel processing with proper GIL
        management. Automatically scales to available CPU cores.

        Args:
            log_paths: List of log file paths to process
            max_concurrent: Maximum concurrent operations (default: 10)
            progress_callback: Optional callback for progress updates,
                             called with log_path for each started operation

        Returns:
            List of analysis results (one per log)

        Raises:
            IOError: If log files cannot be read
            ValueError: If log format is invalid

        """

    def process_logs_batch(
        self,
        log_paths: list[str],
        max_concurrent: int | None = None,
    ) -> list[AnalysisResult]:
        """Process multiple crash logs in batch mode with configurable parallelism.

        Batch processes multiple crash logs with parallel execution. The level of
        parallelism can be controlled via `max_concurrent`, or left to auto-detect
        based on CPU cores and batch size.

        Args:
            log_paths: List of log file paths to process
            max_concurrent: Optional maximum number of concurrent processing tasks.
                If None, uses adaptive concurrency based on CPU count and batch size.
                If specified, uses exactly that many concurrent tasks (minimum 1).

        Returns:
            List of analysis results (one per log). Note that results may not be
            in the same order as input due to parallel processing.

        Raises:
            IOError: If log files cannot be read
            ValueError: If log format is invalid

        """

    def is_feature_complete(self) -> bool:
        """Check if the orchestrator has all features required for Rust-first processing.

        A feature-complete orchestrator can replace Python's OrchestratorCore for
        both single-log and batch processing.

        Returns:
            True if all required features are available

        """

    def has_database_pool(self) -> bool:
        """Check if this orchestrator has a database pool attached.

        Returns:
            True if database pool is available for FormID lookups

        """

    def is_initialized(self) -> bool:
        """Check if the orchestrator has been initialized via async_enter.

        Returns:
            True if initialized

        """

    def write_reports_batch(self, reports: list[tuple[str, list[str], bool]]) -> list[str]:
        """Write batch reports to files.

        This operation writes multiple report files concurrently, generating
        autoscan filenames (e.g., crash.log -> crash-AUTOSCAN.md).

        Args:
            reports: List of tuples: (log_path, report_lines, scan_failed)

        Returns:
            List of paths to successfully written reports

        """

    @staticmethod
    def check_loadorder_exists(dir_path: str) -> bool:
        """Check if a loadorder.txt file exists in the specified directory.

        Args:
            dir_path: Directory path to check

        Returns:
            True if loadorder.txt exists

        """

    def load_loadorder(self, loadorder_path: str) -> tuple[dict[str, str], list[str]]:
        """Load plugins from a loadorder.txt file.

        Args:
            loadorder_path: Path to the loadorder.txt file

        Returns:
            Tuple of (plugins_dict, info_lines) where plugins_dict maps plugin names
            to their origin marker ("LO")

        """

    def detect_folon(self, plugins: dict[str, str]) -> bool:
        """Detect if FOLON (Fallout: London) is loaded based on plugins.

        Args:
            plugins: Dictionary of plugin names to data

        Returns:
            True if londonworldspace.esm is detected

        """

class AnalysisConfig:
    """Analysis configuration.

    Contains all necessary configuration data for analyzing crash logs,
    including game info, mod databases, ignore lists, and pattern definitions.
    """

    game: str
    vr_mode: bool
    crashgen_name: str
    crashgen_latest: str
    crashgen_latest_vr: str  # VR version of crashgen
    game_version: str
    game_version_vr: str
    game_version_new: str
    xse_acronym: str
    game_root_name: str  # Root name (e.g., "Fallout4")
    classic_version: str  # CLASSIC version string
    ignore_plugins: list[str]
    ignore_records: list[str]
    ignore_list: list[str]
    show_formid_values: bool
    fcx_mode: bool  # FCX mode enabled
    simplify_logs: bool  # Whether to simplify logs
    remove_list: list[str]  # Strings to remove when simplifying
    suspects_error: dict[str, str]
    suspects_stack: dict[str, list[str]]
    mods_core: dict[str, str]
    mods_freq: dict[str, str]
    mods_conf: dict[str, str]
    mods_solu: dict[str, str]
    mods_opc2: dict[str, str]
    mods_core_folon: dict[str, str]  # FOLON-specific mods
    classic_records_list: list[str]  # Named records to scan
    crashgen_ignore: list[str]  # Settings to ignore during validation

    def __init__(self, game: str, vr_mode: bool = False) -> None:
        """Create analysis config.

        Args:
            game: Game name (e.g., "Fallout4", "Skyrim")
            vr_mode: Whether VR mode is enabled (default: False)

        """

    @staticmethod
    def from_yamldata(yamldata: Any) -> AnalysisConfig:
        """Create AnalysisConfig from YamlData.

        Converts a YamlData object (from classic_config) into an
        AnalysisConfig for use with Orchestrator.

        Args:
            yamldata: YamlData object from classic_config module

        Returns:
            Configured AnalysisConfig instance

        Example:
            >>> from classic_config import YamlData
            >>> from classic_scanlog import AnalysisConfig
            >>> yamldata = YamlData([...], "Fallout4", False)
            >>> config = AnalysisConfig.from_yamldata(yamldata)

        """

class AnalysisResult:
    """Analysis result for a single crash log.

    Contains all analysis results including the generated report,
    statistics, and any errors encountered during processing.
    """

    log_path: str
    report_lines: list[str]
    success: bool
    error: str | None
    processing_time_us: int  # Processing time in microseconds (for sub-millisecond precision)
    processing_time_ms: int  # Processing time in milliseconds (minimum 1ms for non-zero processing)
    plugin_count: int
    formid_count: int
    suspect_count: int
    # Statistics for Python compatibility (Counter[str] style)
    scanned: int  # Number of logs successfully scanned (1 for success, 0 for failure)
    incomplete: int  # Number of logs detected as incomplete (missing plugin segment)
    failed: int  # Number of logs that failed to scan
    trigger_scan_failed: bool  # Whether scan triggered a failure condition

    def __init__(self, log_path: str) -> None:
        """Create analysis result.

        Args:
            log_path: Path to the analyzed log file

        """

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String showing key statistics

        """

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of all fields

        """

    def get_report_text(self) -> str:
        """Get report as single string.

        Returns:
            Complete report text with newlines

        """

# =============================================================================
# Report Generation
# =============================================================================

class StringPool:
    """Shared string pool for report generation.

    Reduces memory usage by deduplicating common strings across reports.
    """

    def __init__(self) -> None:
        """Create string pool."""

    def intern(self, text: str) -> str:
        """Intern a string.

        Args:
            text: String to intern

        Returns:
            Interned string reference (may be same object for duplicates)

        """

    def intern_batch(self, strings: list[str]) -> list[str]:
        """Intern multiple strings in parallel.

        Args:
            strings: List of strings to intern

        Returns:
            List of interned strings

        """

    def get_stats(self) -> tuple[int, int, int, int]:
        """Get pool statistics.

        Returns:
            Tuple of (total_strings, unique_strings, memory_saved, current_size)

        """

    def clear(self) -> None:
        """Clear the string pool."""

class ReportFragment:
    """A fragment of a report.

    Represents a section of the final report with priority for ordering.
    """

    def __init__(self, lines: list[str] | None = None) -> None:
        """Create report fragment.

        Args:
            lines: Optional list of lines to initialize the fragment with

        """

    @staticmethod
    def empty() -> ReportFragment:
        """Create an empty report fragment.

        Returns:
            Empty ReportFragment instance

        """

    @staticmethod
    def from_lines(lines: list[str]) -> ReportFragment:
        """Create a report fragment from a list of lines.

        Args:
            lines: List of string lines for the fragment

        Returns:
            ReportFragment initialized with the given lines

        """

    def with_header(self, header_lines: list[str]) -> ReportFragment:
        """Add a header to this fragment.

        Args:
            header_lines: List of header lines to prepend

        Returns:
            New ReportFragment with header added

        """

    def combine(self, other: ReportFragment) -> ReportFragment:
        """Combine two fragments.

        Args:
            other: Another ReportFragment to combine with this one

        Returns:
            New ReportFragment containing both fragments

        """

    def to_list(self) -> list[str]:
        """Convert to a list of strings.

        Returns:
            List of string lines in the fragment

        """

    def len(self) -> int:
        """Get the number of lines.

        Returns:
            Number of lines in the fragment

        """

    def is_empty(self) -> bool:
        """Check if empty.

        Returns:
            True if fragment has no lines

        """

class ReportComposer:
    """Composes report fragments into final report.

    Manages fragment ordering, deduplication, and final composition.
    """

    def __init__(self) -> None:
        """Create report composer."""

    def add(self, fragment: ReportFragment) -> None:
        """Add a report fragment.

        Args:
            fragment: Fragment to add to composition

        """

    def add_many(self, fragments: list[ReportFragment]) -> None:
        """Add multiple fragments at once.

        Args:
            fragments: List of fragments to add

        """

    def compose(self) -> list[str]:
        """Compose final report.

        Sorts fragments by priority and composes into final report.

        Returns:
            Report lines (markdown format)

        """

    def compose_optimized(self) -> list[str]:
        """Compose final report with optimization.

        Uses optimized composition algorithm for better performance.

        Returns:
            Report lines (markdown format)

        """

    def build_string(self) -> str:
        """Build as a single string.

        Returns:
            Complete report as a single string

        """

    def fragment_count(self) -> int:
        """Get number of fragments.

        Returns:
            Number of fragments currently in the composer

        """

    def pool_stats(self) -> tuple[int, int, int, int]:
        """Get string pool statistics.

        Returns:
            Tuple of (pool_size, lookups, hits, insertions):
                - pool_size: Number of unique interned strings
                - lookups: Total number of intern attempts
                - hits: Number of cache hits (string already in pool)
                - insertions: Number of new strings added to pool

        """

class ReportGenerator:
    """High-performance report generation (75x speedup).

    Generates markdown-formatted crash analysis reports with all
    relevant information organized by section. Output is identical
    to Python's ReportGeneratorFragments.
    """

    def __init__(self) -> None:
        """Create report generator with default configuration."""

    @staticmethod
    def with_config(classic_version: str, crashgen_name: str) -> ReportGenerator:
        """Create report generator with custom configuration.

        Args:
            classic_version: CLASSIC version string (e.g., "CLASSIC v8.0.0")
            crashgen_name: Crash generator name (e.g., "Buffout 4")

        Returns:
            Configured ReportGenerator instance

        """

    def generate_header(self, crashlog_filename: str) -> ReportFragment:
        """Generate header fragment.

        Args:
            crashlog_filename: Name of the crash log file

        Returns:
            ReportFragment containing the header section

        """

    def generate_error_section(self, main_error: str, crashgen_version: str, is_outdated: bool) -> ReportFragment:
        """Generate error section.

        Args:
            main_error: Main error message from crash log
            crashgen_version: Version of crash generator detected
            is_outdated: Whether the crashgen version is outdated

        Returns:
            ReportFragment containing the error section

        """

    def generate_suspect_section_header(self) -> ReportFragment:
        """Generate suspect section header.

        Returns:
            ReportFragment containing the suspect section header

        """

    def generate_suspect_found_footer(self, found_suspect: bool) -> ReportFragment:
        """Generate suspect found footer.

        Args:
            found_suspect: Whether any suspects were detected

        Returns:
            ReportFragment containing the footer message

        """

    def generate_settings_section_header(self) -> ReportFragment:
        """Generate settings section header.

        Returns:
            ReportFragment containing the settings section header

        """

    def generate_mod_check_header(self, check_type: str) -> ReportFragment:
        """Generate mod check header.

        Args:
            check_type: Description of what mods are being checked

        Returns:
            ReportFragment containing the mod check header

        """

    def generate_plugin_suspect_header(self) -> ReportFragment:
        """Generate plugin suspect header.

        Returns:
            ReportFragment containing the plugin suspect header

        """

    def generate_formid_section_header(self) -> ReportFragment:
        """Generate FormID section header.

        Returns:
            ReportFragment containing the FormID section header

        """

    def generate_record_section_header(self) -> ReportFragment:
        """Generate record section header.

        Returns:
            ReportFragment containing the record section header

        """

    def generate_footer(self) -> ReportFragment:
        """Generate report footer.

        Returns:
            ReportFragment containing the report footer

        """

    def generate_suspect_section(self, found_suspects: list[str]) -> ReportFragment:
        """Generate suspect section (legacy method for backward compatibility).

        Args:
            found_suspects: List of suspect lines to include

        Returns:
            ReportFragment containing the suspect section

        """

class ParallelReportProcessor:
    """Parallel report processing.

    Processes multiple analysis results into reports in parallel,
    utilizing all available CPU cores.
    """

    def __init__(self) -> None:
        """Create parallel processor."""

    @staticmethod
    def process_batch(reports: list[list[str]], processor_fn: Any) -> list[list[str]]:
        """Process multiple reports in parallel.

        Args:
            reports: List of report fragments (each is a list of strings)
            processor_fn: Processing function to apply

        Returns:
            List of processed report fragments

        """

    @staticmethod
    def combine_fragments(fragments: list[ReportFragment]) -> ReportFragment:
        """Combine multiple report fragments in parallel.

        Args:
            fragments: List of ReportFragment instances to combine

        Returns:
            Single combined ReportFragment

        """

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

def scan_records_batch(texts: list[list[str]], record_list: list[str], ignore_records: list[str]) -> list[list[str]]:
    """Scan for records in multiple texts.

    Args:
        texts: List of texts to scan
        record_list: List of record names to find
        ignore_records: List of record names to ignore

    Returns:
        List of found records for each text

    """

def contains_record(text: str, target_records: list[str], ignore_records: list[str]) -> bool:
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

def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> list[str]:
    """Detect mods using single-pass algorithm.

    Fast detection for simple mod identification.

    Args:
        yaml_dict: Mod database dictionary {mod_signature: warning_message}
        crashlog_plugins: Dictionary of plugins from crash log {plugin_name: details}

    Returns:
        List of warning messages for detected mods

    """

def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> list[str]:
    """Detect mods using double-pass algorithm.

    More accurate detection using two-stage matching for conflict detection.

    Args:
        yaml_dict: Mod conflict database dictionary {mod1+mod2: warning_message}
        crashlog_plugins: Dictionary of plugins from crash log {plugin_name: details}

    Returns:
        List of warning messages for detected mod conflicts

    """

def detect_mods_important(
    yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], gpu_rival: str | None = None, xse_modules: set[str] = ...
) -> list[str]:
    """Detect important mods (core mods, framework mods).

    Prioritizes detection of essential mods that affect stability.

    Args:
        yaml_dict: Important mods database dictionary {mod_signature: warning_message}
        crashlog_plugins: Dictionary of plugins from crash log {plugin_name: details}
        gpu_rival: Optional GPU vendor filter ("nvidia" or "amd")
        xse_modules: Set of XSE module names for additional checking

    Returns:
        List of warning messages for detected important mods

    """

def detect_mods_batch(yaml_dict: dict[str, str], crashlog_plugins_list: list[dict[str, str]]) -> list[list[str]]:
    """Detect mods in multiple crash logs (35x speedup).

    Parallel mod detection across multiple crash logs.

    Args:
        yaml_dict: Mod database dictionary {mod_signature: warning_message}
        crashlog_plugins_list: List of plugin dictionaries, one per crash log

    Returns:
        List of warning message lists, one per crash log

    """

# =============================================================================
# Suspect Scanning (Phase 2)
# =============================================================================

class SuspectScanner:
    """Suspect pattern matching with signal modifiers (40x speedup).

    Supports three pattern modifier types:
    - ME-REQ: Main error required (must match in main error)
    - ME-OPT: Main error optional (bonus if in main error)
    - NOT: Negative pattern (excludes if matched)
    """

    def __init__(self, suspects_error_list: dict[str, str], suspects_stack_list: dict[str, list[str]]) -> None:
        """Create suspect scanner.

        Args:
            suspects_error_list: Dictionary mapping error patterns to descriptions
            suspects_stack_list: Dictionary mapping stack patterns to descriptions

        """

    def suspect_scan_mainerror(self, crashlog_mainerror: str, max_warn_length: int) -> tuple[list[str], bool]:
        """Scan main error for suspects.

        Args:
            crashlog_mainerror: Main error message from crash log
            max_warn_length: Maximum warning length for output

        Returns:
            Tuple of (suspect_lines, found_suspect)

        """

    def suspect_scan_stack(self, crashlog_mainerror: str, segment_callstack_intact: str, max_warn_length: int) -> tuple[list[str], bool]:
        """Scan call stack for suspects.

        Uses signal modifier logic to match patterns across
        main error and callstack.

        Args:
            crashlog_mainerror: Main error message
            segment_callstack_intact: Call stack text
            max_warn_length: Maximum warning length for output

        Returns:
            Tuple of (suspect_lines, found_suspect)

        """

    def scan_suspects_batch(self, crash_logs: list[tuple[str, str]], max_warn_length: int) -> list[tuple[list[str], bool]]:
        """Batch scan multiple crash logs.

        Args:
            crash_logs: List of (main_error, callstack) tuples
            max_warn_length: Maximum warning length for output

        Returns:
            List of (suspect_lines, found_suspect) tuples

        """

    @staticmethod
    def check_dll_crash(crashlog_mainerror: str) -> list[str]:
        """Check for DLL-related crashes.

        Args:
            crashlog_mainerror: Main error message

        Returns:
            List of DLL crash indicators

        """

# =============================================================================
# Settings Validation (Phase 2)
# =============================================================================

class SettingsValidator:
    """Settings validation (checks crashgen configuration).

    Validates:
    - Memory management settings
    - Achievements settings
    - Archive limit settings
    - LooksMenu settings
    """

    def __init__(self, crashgen_name: str, crashgen_ignore: list[str]) -> None:
        """Create settings validator.

        Args:
            crashgen_name: Name of crash generator (e.g., "Buffout 4")
            crashgen_ignore: List of settings to ignore during validation

        """

    def scan_buffout_achievements_setting(self, xsemodules: set[str], crashgen: dict[str, str]) -> list[str]:
        """Scan Buffout achievements setting.

        Args:
            xsemodules: Set of XSE module names
            crashgen: Crashgen settings (all values as strings)

        Returns:
            List of report lines for achievements issues

        """

    def scan_buffout_memorymanagement_settings(
        self, crashgen: dict[str, str], has_xcell: bool, has_old_xcell: bool, has_baka_scrapheap: bool
    ) -> list[str]:
        """Scan Buffout memory management settings.

        Args:
            crashgen: Crashgen settings (all values as strings)
            has_xcell: Whether xCell is present
            has_old_xcell: Whether old xCell is present
            has_baka_scrapheap: Whether Baka ScrapHeap is present

        Returns:
            List of report lines for memory management issues

        """

    def scan_archivelimit_setting(self, crashgen: dict[str, str], crashgen_version: Any = None) -> list[str]:
        """Scan archive limit setting.

        Args:
            crashgen: Crashgen settings (all values as strings)
            crashgen_version: Optional crashgen version

        Returns:
            List of report lines for archive limit issues

        """

    def scan_buffout_looksmenu_setting(self, crashgen: dict[str, str], xsemodules: set[str]) -> list[str]:
        """Scan Buffout LooksMenu setting.

        Args:
            crashgen: Crashgen settings (all values as strings)
            xsemodules: Set of XSE module names

        Returns:
            List of report lines for LooksMenu issues

        """

    def check_disabled_settings(self, crashgen: dict[str, str]) -> list[str]:
        """Scan for disabled crash generator settings.

        Checks for settings that have been explicitly disabled and
        reports potential issues or conflicts.

        Args:
            crashgen: Crashgen settings (all values as strings)

        Returns:
            List of report lines for disabled settings issues

        """

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

    def __str__(self) -> str:
        """Return string representation of the vendor."""

    def __repr__(self) -> str:
        """Python repr() representation."""

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

    def __str__(self) -> str:
        """Return string representation of GPU info."""

    def __repr__(self) -> str:
        """Python repr() representation."""

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

    def format_report(self) -> str:
        """Format issue as human-readable report section.

        Returns:
            Formatted markdown string describing the issue

        """

    def __repr__(self) -> str:
        """Return string representation."""

class FcxModeHandler:
    """FCX mode state management.

    Manages FCX (First Crash eXpert) mode state, configuration checks,
    and detected issues reporting.
    """

    def __init__(self, enabled: bool = False) -> None:
        """Create FCX mode handler.

        Args:
            enabled: Whether FCX mode is enabled

        """

    def check_fcx_mode(self) -> None:
        """Check and update FCX mode state by calling Python code.

        This method imports Python modules and runs file checks,
        then stores the results in the handler.

        IMPORTANT: This method assumes game paths have already been generated
        via game_generate_paths() before being called.
        """

    def set_main_files_result(self, result: str) -> None:
        """Set main files check result."""

    def set_game_files_result(self, result: str) -> None:
        """Set game files check result."""

    def get_fcx_messages(self) -> list[str]:
        """Generate FCX mode messages.

        Returns:
            List of FCX-related report messages

        """

    def get_fcx_status_message(self) -> str:
        """Get FCX mode status message.

        Returns:
            Status message string

        """

    def has_results(self) -> bool:
        """Check if FCX mode has any results to display.

        Returns:
            True if there are results to show

        """

    @property
    def fcx_mode(self) -> bool:
        """Get FCX mode enabled state."""

    @fcx_mode.setter
    def fcx_mode(self, value: bool) -> None:
        """Set FCX mode enabled state."""

    def add_issue(self, issue: ConfigIssue) -> None:
        """Add a detected configuration issue.

        Args:
            issue: ConfigIssue to add to detected issues list

        """

    def set_detected_issues(self, issues: list[ConfigIssue]) -> None:
        """Set detected configuration issues (replaces existing list).

        Args:
            issues: List of ConfigIssue objects

        """

    def get_detected_issues(self) -> list[ConfigIssue]:
        """Get detected configuration issues.

        Returns:
            List of detected ConfigIssue objects

        """

    def reset(self) -> None:
        """Reset all FCX check results."""

    @classmethod
    def reset_fcx_checks(cls) -> None:
        """Reset the global FCX handler state (class method).

        This class method resets the shared global FCX handler state
        between scan sessions. It provides API compatibility with the
        Python implementation where FCXModeHandler.reset_fcx_checks()
        is called as a class method.

        Example:
            >>> from classic_scanlog import FcxModeHandler
            >>> # Reset global FCX state before starting a new scan
            >>> FcxModeHandler.reset_fcx_checks()

        """

# =============================================================================
# Test Classes
# =============================================================================

# =============================================================================
# Papyrus Log Analysis
# =============================================================================

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

    def total_issues(self) -> int:
        """Get the total number of issues (warnings + errors).

        Returns:
            Sum of warnings and errors

        """

    def error_to_warning_ratio(self) -> float:
        """Calculate the error to warning ratio.

        Returns:
            Ratio of errors to warnings, or 0.0 if no warnings

        """

    def severity_level(self) -> str:
        """Determine the severity level based on error/warning counts.

        Returns:
            "OK" if no errors or errors < 25% of warnings
            "Warning" if errors are 25-100% of warnings
            "Critical" if errors exceed warnings

        """

    def __repr__(self) -> str:
        """Return string representation of statistics."""

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

    def __repr__(self) -> str:
        """Return string representation."""

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

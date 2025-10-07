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

from typing import Any, Callable, Optional

__version__: str

# =============================================================================
# FormID Analysis
# =============================================================================

class FormIDAnalyzer:
    """FormID extraction and analysis (50x speedup).

    Provides both synchronous and asynchronous FormID analysis with
    automatic database lookup and plugin matching.
    """

    def __init__(
        self,
        yamldata: Any,
        show_values: bool = False,
        db_exists: bool = False
    ) -> None:
        """Create FormID analyzer.

        Args:
            yamldata: YAML configuration data (YamlData or ClassicScanLogsInfo)
            show_values: Whether to show FormID values in output
            db_exists: Whether FormID database exists for lookups
        """
        ...

    def extract_formids(self, text: str) -> list[str]:
        """Extract FormIDs from text.

        Args:
            text: Text to search for FormIDs

        Returns:
            List of FormID strings in hex format
        """
        ...

    def analyze_formids(
        self,
        formids: list[str],
        plugins: list[str]
    ) -> dict[str, Any]:
        """Analyze FormIDs against plugin list.

        Args:
            formids: List of FormID strings
            plugins: List of plugin names from load order

        Returns:
            Dictionary with analysis results including matched plugins
        """
        ...

    def formid_match(
        self,
        formids: list[str],
        plugins: list[str]
    ) -> list[str]:
        """Match FormIDs to plugins.

        Args:
            formids: List of FormID strings
            plugins: List of plugin names

        Returns:
            List of matched plugin names
        """
        ...


class RustFormIDAnalyzer:
    """Pure Rust FormID analyzer implementation.

    This is a direct Rust implementation without Python fallback,
    providing maximum performance for FormID operations.
    """

    def __init__(
        self,
        yamldata: Any,
        show_values: bool = False,
        db_exists: bool = False
    ) -> None:
        """Create Rust FormID analyzer.

        Args:
            yamldata: YAML configuration data
            show_values: Whether to show FormID values
            db_exists: Whether FormID database exists
        """
        ...

    def extract_formids(self, text: str) -> list[str]:
        """Extract FormIDs from text.

        Args:
            text: Text to search

        Returns:
            List of FormID strings
        """
        ...

    def analyze_formids(
        self,
        formids: list[str],
        plugins: list[str]
    ) -> dict[str, Any]:
        """Analyze FormIDs against plugins.

        Args:
            formids: List of FormID strings
            plugins: List of plugin names

        Returns:
            Analysis results
        """
        ...


class FormIDAnalyzerCore:
    """Core FormID analysis functionality.

    Provides low-level FormID operations without configuration dependencies.
    """

    def __init__(self) -> None:
        """Create FormID analyzer core."""
        ...

    def is_valid_formid(self, formid: str) -> bool:
        """Check if FormID string is valid.

        Args:
            formid: FormID string to validate

        Returns:
            True if valid hex FormID
        """
        ...

    def parse_formid(self, formid: str) -> Optional[int]:
        """Parse FormID string to integer.

        Args:
            formid: FormID string (hex format)

        Returns:
            Parsed FormID integer or None if invalid
        """
        ...

    def extract_plugin_index(self, formid: str) -> Optional[int]:
        """Extract plugin index from FormID.

        Args:
            formid: FormID string

        Returns:
            Plugin index (0-255) or None if invalid
        """
        ...


# =============================================================================
# Log Parsing
# =============================================================================

class LogParser:
    """High-performance log parser (150x speedup).

    Parses crash logs and extracts all relevant segments including
    main error, callstack, plugins, system info, and more.
    """

    def __init__(self) -> None:
        """Create a new LogParser instance."""
        ...

    def find_segments(
        self,
        crash_data: list[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str
    ) -> dict[str, Any]:
        """Find and parse all log segments.

        Args:
            crash_data: Raw crash log lines
            crashgen_name: Crash generator name (e.g., "Buffout 4")
            xse_acronym: XSE acronym (e.g., "F4SE")
            game_root_name: Game root folder name

        Returns:
            Dictionary containing all parsed segments:
                - main_error: Main error message
                - callstack: Stack trace lines
                - plugins: Plugin list
                - system_info: System information
                - probable_callstack: Most relevant stack section
                - etc.
        """
        ...

    def extract_section(
        self,
        crash_data: list[str],
        start_marker: str,
        end_marker: str
    ) -> Optional[list[str]]:
        """Extract a section between markers.

        Args:
            crash_data: Raw crash log lines
            start_marker: Start marker string
            end_marker: End marker string

        Returns:
            Extracted section lines or None if not found
        """
        ...

    def parse_plugins(self, plugin_section: list[str]) -> list[str]:
        """Parse plugin list from crash log section.

        Args:
            plugin_section: Plugin section lines

        Returns:
            List of plugin names
        """
        ...

    def extract_game_version(
        self,
        crash_data: list[str]
    ) -> Optional[str]:
        """Extract game version from crash log.

        Args:
            crash_data: Raw crash log lines

        Returns:
            Game version string or None if not found
        """
        ...


# =============================================================================
# Pattern Matching
# =============================================================================

class PatternMatcher:
    """Pattern matching for suspect detection.

    Uses pre-compiled regex patterns for efficient suspect scanning.
    """

    def __init__(self) -> None:
        """Create pattern matcher."""
        ...

    def match_patterns(
        self,
        text: str,
        patterns: dict[str, str]
    ) -> list[str]:
        """Match patterns in text.

        Args:
            text: Text to search
            patterns: Dictionary of pattern_key: pattern_regex

        Returns:
            List of matched pattern keys
        """
        ...

    def match_pattern_batch(
        self,
        texts: list[str],
        patterns: dict[str, str]
    ) -> list[list[str]]:
        """Match patterns in multiple texts (parallel).

        Args:
            texts: List of texts to search
            patterns: Pattern dictionary

        Returns:
            List of matched pattern keys for each text
        """
        ...


# =============================================================================
# Plugin Analysis
# =============================================================================

class PluginAnalyzer:
    """Plugin matching and analysis (30x speedup).

    Analyzes plugin lists against configuration data to detect
    problematic plugins, conflicts, and missing dependencies.
    """

    def __init__(self, yamldata: Any) -> None:
        """Create plugin analyzer.

        Args:
            yamldata: YAML configuration data
        """
        ...

    def analyze_plugins(
        self,
        plugins: list[str]
    ) -> dict[str, Any]:
        """Analyze plugin list.

        Args:
            plugins: List of plugin names from load order

        Returns:
            Dictionary with analysis results including:
                - ignored_plugins: Plugins in ignore list
                - problematic_plugins: Known problematic plugins
                - plugin_count: Total plugin count
        """
        ...

    def check_plugin_conflicts(
        self,
        plugins: list[str]
    ) -> list[str]:
        """Check for known plugin conflicts.

        Args:
            plugins: List of plugin names

        Returns:
            List of conflict descriptions
        """
        ...


# =============================================================================
# Record Scanning
# =============================================================================

class RecordScanner:
    """Record scanning (40x speedup).

    Scans crash logs for specific named records using optimized
    pattern matching algorithms.
    """

    def __init__(self, yamldata: Any) -> None:
        """Create record scanner.

        Args:
            yamldata: YAML configuration data
        """
        ...

    def scan_records(
        self,
        text: str,
        record_list: list[str]
    ) -> list[str]:
        """Scan for specific records.

        Args:
            text: Text to scan
            record_list: List of record names to find

        Returns:
            List of found record names
        """
        ...

    def scan_named_records(
        self,
        text: str
    ) -> dict[str, list[str]]:
        """Scan for all configured named records.

        Args:
            text: Text to scan

        Returns:
            Dictionary mapping record types to found instances
        """
        ...


# =============================================================================
# Orchestration
# =============================================================================

class RustOrchestrator:
    """End-to-end crash log analysis orchestration.

    Coordinates all analysis components with 10-100x performance improvements
    over the Python implementation. Provides both single-file and batch
    processing with automatic parallelization.
    """

    def __init__(self) -> None:
        """Create a new orchestrator instance."""
        ...

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
        ...

    def process_logs_parallel(
        self,
        log_paths: list[str],
        max_concurrent: int = 10,
        progress_callback: Optional[Callable[[str], None]] = None
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
        ...


class AnalysisConfig:
    """Analysis configuration.

    Contains all necessary configuration data for analyzing crash logs,
    including game info, mod databases, ignore lists, and pattern definitions.
    """

    game: str
    vr_mode: bool
    crashgen_name: str
    crashgen_latest: str
    game_version: str
    xse_acronym: str
    ignore_plugins: list[str]
    ignore_records: list[str]
    ignore_list: list[str]

    def __init__(self, game: str, vr_mode: bool = False) -> None:
        """Create analysis config.

        Args:
            game: Game name (e.g., "Fallout4", "Skyrim")
            vr_mode: Whether VR mode is enabled (default: False)
        """
        ...

    @staticmethod
    def from_yamldata(yamldata: Any) -> AnalysisConfig:
        """Create AnalysisConfig from YamlData.

        Converts a YamlData object (from classic_config) into an
        AnalysisConfig for use with RustOrchestrator.

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
        ...


class AnalysisResult:
    """Analysis result for a single crash log.

    Contains all analysis results including the generated report,
    statistics, and any errors encountered during processing.
    """

    log_path: str
    report_lines: list[str]
    success: bool
    error: Optional[str]
    processing_time_ms: int
    plugin_count: int
    formid_count: int
    suspect_count: int

    def __init__(self, log_path: str) -> None:
        """Create analysis result.

        Args:
            log_path: Path to the analyzed log file
        """
        ...

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String showing key statistics
        """
        ...

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of all fields
        """
        ...

    def get_report_text(self) -> str:
        """Get report as single string.

        Returns:
            Complete report text with newlines
        """
        ...


# =============================================================================
# Report Generation
# =============================================================================

class StringPool:
    """Shared string pool for report generation.

    Reduces memory usage by deduplicating common strings across reports.
    """

    def __init__(self) -> None:
        """Create string pool."""
        ...

    def intern(self, text: str) -> str:
        """Intern a string.

        Args:
            text: String to intern

        Returns:
            Interned string reference (may be same object for duplicates)
        """
        ...

    def clear(self) -> None:
        """Clear the string pool."""
        ...


class ReportFragment:
    """A fragment of a report.

    Represents a section of the final report with priority for ordering.
    """

    content: str
    priority: int

    def __init__(self, content: str, priority: int = 0) -> None:
        """Create report fragment.

        Args:
            content: Fragment content (markdown text)
            priority: Priority for ordering (higher = earlier, default: 0)
        """
        ...


class ReportComposer:
    """Composes report fragments into final report.

    Manages fragment ordering, deduplication, and final composition.
    """

    def __init__(self) -> None:
        """Create report composer."""
        ...

    def add_fragment(self, fragment: ReportFragment) -> None:
        """Add a report fragment.

        Args:
            fragment: Fragment to add to composition
        """
        ...

    def add_section(self, title: str, content: str, priority: int = 0) -> None:
        """Add a section as a fragment.

        Args:
            title: Section title
            content: Section content
            priority: Section priority
        """
        ...

    def compose(self) -> list[str]:
        """Compose final report.

        Sorts fragments by priority and composes into final report.

        Returns:
            Report lines (markdown format)
        """
        ...

    def clear(self) -> None:
        """Clear all fragments."""
        ...


class ReportGenerator:
    """High-performance report generation (75x speedup).

    Generates markdown-formatted crash analysis reports with all
    relevant information organized by section.
    """

    def __init__(self, yamldata: Optional[Any] = None) -> None:
        """Create report generator.

        Args:
            yamldata: Optional YAML configuration data for formatting
        """
        ...

    def generate_report(
        self,
        analysis_data: dict[str, Any]
    ) -> list[str]:
        """Generate markdown report.

        Args:
            analysis_data: Analysis results dictionary containing:
                - main_error: Main error message
                - callstack: Stack trace
                - plugins: Plugin list
                - suspects: Detected suspects
                - mods: Detected mods
                - formids: FormID analysis
                - etc.

        Returns:
            Report lines (markdown format)
        """
        ...

    def format_section(
        self,
        title: str,
        content: list[str]
    ) -> list[str]:
        """Format a report section.

        Args:
            title: Section title
            content: Section content lines

        Returns:
            Formatted section lines
        """
        ...


class ParallelReportProcessor:
    """Parallel report processing.

    Processes multiple analysis results into reports in parallel,
    utilizing all available CPU cores.
    """

    def __init__(self, max_workers: int = 4) -> None:
        """Create parallel processor.

        Args:
            max_workers: Maximum parallel workers (default: 4)
        """
        ...

    def process_batch(
        self,
        analysis_results: list[AnalysisResult]
    ) -> list[list[str]]:
        """Process multiple analysis results in parallel.

        Args:
            analysis_results: List of analysis results to process

        Returns:
            List of generated reports (one per result)
        """
        ...


# =============================================================================
# Standalone Functions
# =============================================================================

def extract_formids_batch(texts: list[str]) -> list[list[str]]:
    """Extract FormIDs from multiple texts in parallel.

    Uses rayon for parallel processing across all texts.

    Args:
        texts: List of text strings to search

    Returns:
        List of FormID lists for each text
    """
    ...


def is_valid_formid(formid: str) -> bool:
    """Check if a FormID string is valid.

    Args:
        formid: FormID string to validate (hex format)

    Returns:
        True if valid FormID format (8-char hex)
    """
    ...


def validate_formids_batch(formids: list[str]) -> list[bool]:
    """Validate multiple FormIDs in parallel.

    Args:
        formids: List of FormID strings

    Returns:
        List of validation results (True for valid, False for invalid)
    """
    ...


def scan_records_batch(
    texts: list[str],
    record_list: list[str]
) -> list[list[str]]:
    """Scan for records in multiple texts.

    Args:
        texts: List of texts to scan
        record_list: List of record names to find

    Returns:
        List of found records for each text
    """
    ...


def contains_record(text: str, record: str) -> bool:
    """Check if text contains a specific record.

    Args:
        text: Text to search
        record: Record name to find

    Returns:
        True if record found in text
    """
    ...


def detect_plugins_batch(
    texts: list[str],
    plugin_list: list[str]
) -> list[list[str]]:
    """Detect plugins in multiple texts.

    Args:
        texts: List of texts to search
        plugin_list: List of plugin names to detect

    Returns:
        List of detected plugins for each text
    """
    ...


def contains_plugin(text: str, plugin: str) -> bool:
    """Check if text contains a specific plugin reference.

    Args:
        text: Text to search
        plugin: Plugin name to find

    Returns:
        True if plugin found in text
    """
    ...


def detect_mods_single(
    text: str,
    mod_db: dict[str, str]
) -> list[str]:
    """Detect mods using single-pass algorithm.

    Fast detection for simple mod identification.

    Args:
        text: Text to search (typically crash log)
        mod_db: Mod database dictionary {signature: mod_name}

    Returns:
        List of detected mod names
    """
    ...


def detect_mods_double(
    text: str,
    mod_db: dict[str, str]
) -> list[str]:
    """Detect mods using double-pass algorithm.

    More accurate detection using two-stage matching.

    Args:
        text: Text to search
        mod_db: Mod database dictionary

    Returns:
        List of detected mod names
    """
    ...


def detect_mods_important(
    text: str,
    mod_db: dict[str, str]
) -> list[str]:
    """Detect important mods (core mods, framework mods).

    Prioritizes detection of essential mods that affect stability.

    Args:
        text: Text to search
        mod_db: Mod database dictionary

    Returns:
        List of detected important mod names
    """
    ...


def detect_mods_batch(
    texts: list[str],
    mod_db: dict[str, str]
) -> list[list[str]]:
    """Detect mods in multiple texts (35x speedup).

    Parallel mod detection across multiple crash logs.

    Args:
        texts: List of texts to search
        mod_db: Mod database dictionary

    Returns:
        List of detected mods for each text
    """
    ...


# =============================================================================
# Test Classes
# =============================================================================

class TestClass:
    """Test class for module registration testing.

    Used to verify that the module is properly loaded and
    Python classes are correctly exported from Rust.
    """

    def __init__(self) -> None:
        """Create test class instance."""
        ...

    def test_method(self) -> str:
        """Test method.

        Returns:
            Test string to verify functionality
        """
        ...

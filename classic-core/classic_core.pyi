"""Type stubs for classic_core Rust extension module.

This module provides high-performance Rust implementations for CLASSIC with
10-150x speedups over pure Python implementations.

Architecture (Post-Modularization):
    - classic-shared: Foundation (runtime, errors, utilities)
    - classic-yaml: YAML operations
    - classic-database: SQLite operations
    - classic-file-io: File I/O operations
    - classic-scanlog: Log parsing & analysis
    - classic-core (this crate): Facade that re-exports everything
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, Protocol

__version__: str

# =============================================================================
# Root Module - Legacy Classes
# =============================================================================

class FileReader:
    """High-performance file reader using async I/O internally.

    Note: This is a legacy class maintained for backward compatibility.
    Use classic_core.file_io.RustFileIOCore for new code.
    """

    def __init__(self) -> None:
        """Create a new FileReader instance."""
        ...

    def read_file(self, path: str) -> str:
        """Read a file synchronously (but uses async I/O internally).

        Args:
            path: Path to the file to read

        Returns:
            File contents as string

        Raises:
            IOError: If file cannot be read
        """
        ...

    def read_files_batch(self, paths: list[str]) -> list[Optional[str]]:
        """Read multiple files in parallel.

        Args:
            paths: List of file paths to read

        Returns:
            List of file contents (None for failed reads)
        """
        ...


class FormIDProcessor:
    """Fast FormID processor using parallel computation.

    Note: This is a legacy class maintained for backward compatibility.
    Use classic_core.scanlog functions for new code.
    """

    def __init__(self) -> None:
        """Create a new FormIDProcessor instance."""
        ...

    def process_batch(self, formids: list[str]) -> list[Optional[int]]:
        """Process FormIDs in parallel.

        Args:
            formids: List of FormID strings (hex format)

        Returns:
            List of parsed FormID integers (None for invalid)
        """
        ...

    def lookup_formids(
        self,
        db_path: str,
        formids: list[str]
    ) -> list[Optional[str]]:
        """Async database lookup exposed as sync.

        Args:
            db_path: Path to FormID database
            formids: List of FormID strings to look up

        Returns:
            List of plugin names (None for not found)

        Raises:
            IOError: If database cannot be read
        """
        ...


def count_patterns_in_file(path: str, pattern: str) -> int:
    """Pattern matcher with async file operations.

    Args:
        path: Path to file to search
        pattern: Pattern string to count

    Returns:
        Number of pattern occurrences

    Raises:
        IOError: If file cannot be read
    """
    ...


# =============================================================================
# utils Submodule (from classic-shared)
# =============================================================================

class utils:
    """Utility functions from classic-shared crate."""

    class StringProcessor:
        """High-performance string processing utilities."""

        def __init__(self) -> None: ...

        def normalize_whitespace(self, text: str) -> str:
            """Normalize whitespace in text.

            Args:
                text: Input text

            Returns:
                Text with normalized whitespace
            """
            ...

        def strip_ansi_codes(self, text: str) -> str:
            """Strip ANSI color codes from text.

            Args:
                text: Text with ANSI codes

            Returns:
                Text without ANSI codes
            """
            ...

    class PathHandler:
        """Path handling utilities."""

        def __init__(self) -> None: ...

        def normalize_path(self, path: str) -> str:
            """Normalize a file path.

            Args:
                path: Input path

            Returns:
                Normalized path
            """
            ...

        def is_valid_path(self, path: str) -> bool:
            """Check if path is valid.

            Args:
                path: Path to check

            Returns:
                True if path is valid
            """
            ...

    class RustPerformanceMonitor:
        """Performance monitoring for Rust components."""

        def __init__(self) -> None: ...

        def start_timing(self, operation: str) -> None:
            """Start timing an operation.

            Args:
                operation: Operation name
            """
            ...

        def end_timing(self, operation: str) -> float:
            """End timing and get duration.

            Args:
                operation: Operation name

            Returns:
                Duration in seconds
            """
            ...

        def get_stats(self) -> dict[str, Any]:
            """Get performance statistics.

            Returns:
                Dictionary of operation stats
            """
            ...


# =============================================================================
# scanlog Submodule (from classic-scanlog)
# =============================================================================

class scanlog:
    """Scanlog analysis components from classic-scanlog crate.

    Provides 10-150x performance improvements for crash log analysis.
    """

    class FormIDAnalyzer:
        """FormID extraction and analysis (50x speedup)."""

        def __init__(
            self,
            yamldata: Any,
            show_values: bool = False,
            db_exists: bool = False
        ) -> None:
            """Create FormID analyzer.

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
                Analysis results dictionary
            """
            ...

    class RustFormIDAnalyzer:
        """Pure Rust FormID analyzer implementation."""

        def __init__(
            self,
            yamldata: Any,
            show_values: bool = False,
            db_exists: bool = False
        ) -> None: ...

    class FormIDAnalyzerCore:
        """Core FormID analysis functionality."""

        def __init__(self) -> None: ...

    class LogParser:
        """High-performance log parser (150x speedup)."""

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
            """Find and parse log segments.

            Args:
                crash_data: Raw crash log lines
                crashgen_name: Crash generator name
                xse_acronym: XSE acronym (e.g., "F4SE")
                game_root_name: Game root folder name

            Returns:
                Dictionary of parsed segments
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
                Extracted section lines or None
            """
            ...

    class PatternMatcher:
        """Pattern matching for suspect detection."""

        def __init__(self) -> None: ...

        def match_patterns(
            self,
            text: str,
            patterns: dict[str, str]
        ) -> list[str]:
            """Match patterns in text.

            Args:
                text: Text to search
                patterns: Pattern dictionary

            Returns:
                List of matched pattern keys
            """
            ...

    class PluginAnalyzer:
        """Plugin matching and analysis (30x speedup)."""

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
                plugins: List of plugin names

            Returns:
                Analysis results
            """
            ...

    class RecordScanner:
        """Record scanning (40x speedup)."""

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
                record_list: List of record names

            Returns:
                List of found records
            """
            ...

    class RustOrchestrator:
        """End-to-end crash log analysis orchestration.

        Coordinates all analysis components with 10-100x performance improvements.
        """

        def __init__(self) -> None:
            """Create a new orchestrator instance."""
            ...

        def process_log(self, log_path: str) -> AnalysisResult:
            """Process a single crash log.

            Args:
                log_path: Path to crash log file

            Returns:
                Analysis result

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

            Args:
                log_paths: List of log file paths
                max_concurrent: Maximum concurrent operations (default: 10)
                progress_callback: Optional callback for progress updates

            Returns:
                List of analysis results

            Raises:
                IOError: If log files cannot be read
                ValueError: If log format is invalid
            """
            ...

    class AnalysisConfig:
        """Analysis configuration.

        Contains all necessary configuration data for analyzing crash logs.
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
                game: Game name (e.g., "Fallout4")
                vr_mode: Whether VR mode is enabled (default: False)
            """
            ...

        @staticmethod
        def from_yamldata(yamldata: Any) -> AnalysisConfig:
            """Create AnalysisConfig from YamlData.

            Args:
                yamldata: YamlData object from config-core

            Returns:
                Configured AnalysisConfig instance
            """
            ...

    class AnalysisResult:
        """Analysis result for a single crash log.

        Contains all analysis results including the generated report,
        statistics, and any errors encountered.
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

        def __repr__(self) -> str: ...

    class StringPool:
        """Shared string pool for report generation."""

        def __init__(self) -> None: ...

        def intern(self, text: str) -> str:
            """Intern a string.

            Args:
                text: String to intern

            Returns:
                Interned string reference
            """
            ...

    class ReportFragment:
        """A fragment of a report."""

        def __init__(self, content: str, priority: int = 0) -> None:
            """Create report fragment.

            Args:
                content: Fragment content
                priority: Priority for ordering (default: 0)
            """
            ...

    class ReportComposer:
        """Composes report fragments into final report."""

        def __init__(self) -> None: ...

        def add_fragment(self, fragment: ReportFragment) -> None:
            """Add a report fragment.

            Args:
                fragment: Fragment to add
            """
            ...

        def compose(self) -> list[str]:
            """Compose final report.

            Returns:
                Report lines
            """
            ...

    class ReportGenerator:
        """High-performance report generation (75x speedup)."""

        def __init__(self, yamldata: Optional[Any] = None) -> None:
            """Create report generator.

            Args:
                yamldata: Optional YAML configuration data
            """
            ...

        def generate_report(
            self,
            analysis_data: dict[str, Any]
        ) -> list[str]:
            """Generate markdown report.

            Args:
                analysis_data: Analysis results

            Returns:
                Report lines
            """
            ...

    class ParallelReportProcessor:
        """Parallel report processing."""

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
                analysis_results: List of analysis results

            Returns:
                List of generated reports
            """
            ...

    class MinimalTest:
        """Minimal test class for module registration testing."""

        def __init__(self) -> None: ...

        def test_method(self) -> str:
            """Test method.

            Returns:
                Test string
            """
            ...

    # Standalone functions

    def extract_formids_batch(texts: list[str]) -> list[list[str]]:
        """Extract FormIDs from multiple texts in parallel.

        Args:
            texts: List of text strings to search

        Returns:
            List of FormID lists for each text
        """
        ...

    def is_valid_formid(formid: str) -> bool:
        """Check if a FormID string is valid.

        Args:
            formid: FormID string to validate

        Returns:
            True if valid FormID format
        """
        ...

    def validate_formids_batch(formids: list[str]) -> list[bool]:
        """Validate multiple FormIDs in parallel.

        Args:
            formids: List of FormID strings

        Returns:
            List of validation results
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
            True if record found
        """
        ...

    def detect_plugins_batch(
        texts: list[str],
        plugin_list: list[str]
    ) -> list[list[str]]:
        """Detect plugins in multiple texts.

        Args:
            texts: List of texts to search
            plugin_list: List of plugin names

        Returns:
            List of detected plugins for each text
        """
        ...

    def contains_plugin(text: str, plugin: str) -> bool:
        """Check if text contains a specific plugin.

        Args:
            text: Text to search
            plugin: Plugin name to find

        Returns:
            True if plugin found
        """
        ...

    def detect_mods_single(
        text: str,
        mod_db: dict[str, str]
    ) -> list[str]:
        """Detect mods using single-pass algorithm.

        Args:
            text: Text to search
            mod_db: Mod database

        Returns:
            List of detected mod names
        """
        ...

    def detect_mods_double(
        text: str,
        mod_db: dict[str, str]
    ) -> list[str]:
        """Detect mods using double-pass algorithm.

        Args:
            text: Text to search
            mod_db: Mod database

        Returns:
            List of detected mod names
        """
        ...

    def detect_mods_important(
        text: str,
        mod_db: dict[str, str]
    ) -> list[str]:
        """Detect important mods.

        Args:
            text: Text to search
            mod_db: Mod database

        Returns:
            List of detected important mod names
        """
        ...

    def detect_mods_batch(
        texts: list[str],
        mod_db: dict[str, str]
    ) -> list[list[str]]:
        """Detect mods in multiple texts (35x speedup).

        Args:
            texts: List of texts to search
            mod_db: Mod database

        Returns:
            List of detected mods for each text
        """
        ...


# =============================================================================
# database Submodule (from classic-database)
# =============================================================================

class database:
    """Database operations from classic-database crate."""

    class RustDatabasePool:
        """High-performance database connection pool (25x speedup)."""

        def __init__(
            self,
            max_connections: int = 10,
            cache_ttl_seconds: int = 300
        ) -> None:
            """Create database pool.

            Args:
                max_connections: Maximum connections (default: 10)
                cache_ttl_seconds: Cache TTL in seconds (default: 300)
            """
            ...

        def query(self, sql: str) -> list[dict[str, Any]]:
            """Execute SQL query.

            Args:
                sql: SQL query string

            Returns:
                Query results as list of dictionaries

            Raises:
                RuntimeError: If query fails
            """
            ...

        def lookup_formid(self, formid: str) -> Optional[str]:
            """Look up FormID in database.

            Args:
                formid: FormID string

            Returns:
                Plugin name or None
            """
            ...

        def lookup_formids_batch(
            self,
            formids: list[str]
        ) -> list[Optional[str]]:
            """Look up multiple FormIDs in parallel.

            Args:
                formids: List of FormID strings

            Returns:
                List of plugin names (None for not found)
            """
            ...


# =============================================================================
# file_io Submodule (from classic-file-io)
# =============================================================================

class file_io:
    """File I/O operations from classic-file-io crate."""

    class RustFileIOCore:
        """High-performance file I/O (10-20x file ops, 30-40x DDS processing)."""

        def __init__(
            self,
            encoding: str = "utf-8",
            errors: str = "ignore"
        ) -> None:
            """Create file I/O core.

            Args:
                encoding: Text encoding (default: "utf-8")
                errors: Error handling mode (default: "ignore")
            """
            ...

        def read_file(self, path: str) -> str:
            """Read file as text.

            Args:
                path: File path

            Returns:
                File contents

            Raises:
                IOError: If file cannot be read
            """
            ...

        def read_file_bytes(self, path: str) -> bytes:
            """Read file as bytes.

            Args:
                path: File path

            Returns:
                File contents as bytes

            Raises:
                IOError: If file cannot be read
            """
            ...

        def write_file(self, path: str, content: str) -> None:
            """Write text to file.

            Args:
                path: File path
                content: Content to write

            Raises:
                IOError: If file cannot be written
            """
            ...

        def read_files_batch(
            self,
            paths: list[str]
        ) -> list[Optional[str]]:
            """Read multiple files in parallel.

            Args:
                paths: List of file paths

            Returns:
                List of file contents (None for failed reads)
            """
            ...

        def write_files_batch(
            self,
            path_content_pairs: list[tuple[str, str]]
        ) -> list[bool]:
            """Write multiple files in parallel.

            Args:
                path_content_pairs: List of (path, content) tuples

            Returns:
                List of success flags
            """
            ...

        def parse_dds_header(self, path: str) -> dict[str, Any]:
            """Parse DDS texture header (40x speedup).

            Args:
                path: Path to DDS file

            Returns:
                DDS header information

            Raises:
                IOError: If file cannot be read
                ValueError: If not a valid DDS file
            """
            ...

    class EncodingDetector:
        """Text encoding detection."""

        def __init__(self) -> None: ...

        def detect_encoding(self, data: bytes) -> str:
            """Detect text encoding.

            Args:
                data: Raw bytes

            Returns:
                Detected encoding name
            """
            ...


# =============================================================================
# yaml Submodule (from classic-yaml)
# =============================================================================

class yaml:
    """YAML operations from classic-yaml crate."""

    class RustYamlOperations:
        """High-performance YAML operations (15-30x parsing, 10-20x writing).

        Uses yaml-rust2 for YAML 1.2 compliant parsing.
        """

        def __init__(self) -> None:
            """Create YAML operations instance."""
            ...

        def parse_yaml(self, yaml_str: str) -> Any:
            """Parse YAML string.

            Args:
                yaml_str: YAML content

            Returns:
                Parsed YAML data

            Raises:
                ValueError: If YAML is invalid
            """
            ...

        def parse_yaml_file(self, path: str) -> Any:
            """Parse YAML file.

            Args:
                path: Path to YAML file

            Returns:
                Parsed YAML data

            Raises:
                IOError: If file cannot be read
                ValueError: If YAML is invalid
            """
            ...

        def dump_yaml(self, data: Any) -> str:
            """Convert data to YAML string.

            Args:
                data: Data to serialize

            Returns:
                YAML string
            """
            ...

        def dump_yaml_file(self, path: str, data: Any) -> None:
            """Write data to YAML file.

            Args:
                path: Output file path
                data: Data to serialize

            Raises:
                IOError: If file cannot be written
            """
            ...

        def get_value(self, data: Any, key: str) -> Optional[Any]:
            """Get value by key path.

            Args:
                data: Parsed YAML data
                key: Dot-separated key path (e.g., "section.subsection.key")

            Returns:
                Value or None if not found
            """
            ...

        def set_value(self, data: Any, key: str, value: Any) -> Any:
            """Set value by key path.

            Args:
                data: Parsed YAML data
                key: Dot-separated key path
                value: Value to set

            Returns:
                Modified data
            """
            ...

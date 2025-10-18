"""Type stubs for classic_core.

CLASSIC's main Rust-Python facade module that re-exports all Rust-accelerated components.
This module provides high-performance implementations of core CLASSIC functionality including
YAML operations, database pooling, file I/O, and log scanning.

Architecture (Post-Modularization - 2025-10-08):
    - classic-shared: Foundation (runtime, errors, utilities)
    - classic-yaml-core + classic-yaml-py: YAML operations
    - classic-database-core + classic-database-py: SQLite operations
    - classic-file-io-core + classic-file-io-py: File I/O operations
    - classic-scanlog-core + classic-scanlog-py: Log parsing & analysis
    - classic-config-core + classic-config-py: Configuration management
    - classic-core (this crate): Facade that re-exports everything

Usage:
    from classic_core import yaml, database, file_io, scanlog

    # Use submodules for specific functionality
    yaml_ops = yaml.RustYamlOperations()
    db_pool = database.RustDatabasePool()
    io_core = file_io.RustFileIOCore()
"""

from __future__ import annotations
from typing import Any, Optional, Callable
from pathlib import Path

__version__: str

# =============================================================================
# Root Module - Legacy Classes (Backward Compatibility)
# =============================================================================

class FileReader:
    """Legacy file reader - prefer file_io.RustFileIOCore.

    Note: Maintained for backward compatibility only.
    """

    def __init__(self) -> None:
        """Create a new FileReader instance."""
        ...

    def read_file(self, path: str | Path) -> str:
        """Read a file synchronously.

        Args:
            path: Path to the file to read

        Returns:
            File contents as string

        Raises:
            IOError: If file cannot be read
        """
        ...

class FormIDProcessor:
    """Legacy FormID processor - prefer scanlog.FormIDAnalyzer.

    Note: Maintained for backward compatibility only.
    """

    def __init__(self) -> None:
        """Create a new FormIDProcessor instance."""
        ...

    def process_formid(self, formid: str) -> dict[str, Any]:
        """Process a single FormID.

        Args:
            formid: FormID string to process

        Returns:
            Processed FormID data
        """
        ...

def count_patterns_in_file(file_path: str | Path, pattern: str) -> int:
    """Count occurrences of a regex pattern in a file.

    Args:
        file_path: Path to the file to search
        pattern: Regex pattern to match

    Returns:
        Number of matches found

    Raises:
        IOError: If file cannot be read
    """
    ...

# =============================================================================
# yaml Submodule (from classic-yaml-py)
# =============================================================================

class yaml:
    """YAML operations submodule with Rust acceleration.

    Provides high-performance YAML parsing, loading, and manipulation using yaml-rust2.
    Offers 15-30x speedup over ruamel.yaml for large YAML files.
    """

    class RustYamlOperations:
        """Main YAML operations handler using yaml-rust2.

        High-performance YAML parser and manipulator. Supports multi-document YAML files,
        anchor/alias resolution, and caching.

        Features:
            - YAML 1.2 compliant parsing
            - Multi-document support
            - Anchor/alias resolution
            - Insertion order preservation
            - 15-30x speedup over ruamel.yaml
        """

        def __init__(self) -> None:
            """Create a new YAML operations handler with empty cache."""
            ...

        def load_yaml_file(self, path: str | Path) -> dict[str, Any]:
            """Load and parse a YAML file.

            Args:
                path: Path to the YAML file

            Returns:
                Parsed YAML content as a dictionary

            Raises:
                FileNotFoundError: If file doesn't exist
                ValueError: If YAML is malformed
            """
            ...

        def parse_yaml(self, content: str) -> dict[str, Any]:
            """Parse YAML content from a string.

            Args:
                content: YAML content as string

            Returns:
                Parsed YAML as dictionary

            Raises:
                ValueError: If YAML is malformed
            """
            ...

        def dump_yaml(self, data: dict[str, Any]) -> str:
            """Convert Python dictionary to YAML string.

            Args:
                data: Python dictionary to serialize

            Returns:
                YAML formatted string
            """
            ...

        def save_yaml_file(self, path: str | Path, data: dict[str, Any]) -> None:
            """Save dictionary as YAML file.

            Args:
                path: Destination file path
                data: Dictionary to save

            Raises:
                IOError: If file cannot be written
            """
            ...

        def get_setting(self, key: str, default: Any = None) -> Any:
            """Get a setting value from cached YAML data.

            Args:
                key: Setting key to retrieve
                default: Default value if key not found

            Returns:
                Setting value or default
            """
            ...

        def set_setting(self, key: str, value: Any) -> None:
            """Set a setting value in cached YAML data.

            Args:
                key: Setting key to set
                value: Value to assign
            """
            ...

        def clear_cache(self) -> None:
            """Clear the YAML cache to free memory."""
            ...

        def get_cache_stats(self) -> dict[str, int]:
            """Get cache statistics.

            Returns:
                Dictionary with 'entries' and 'memory_bytes' keys
            """
            ...

# =============================================================================
# database Submodule (from classic-database-py)
# =============================================================================

class database:
    """Database operations submodule with connection pooling.

    Provides high-performance SQLite database access with connection pooling,
    TTL-based caching, and batch operations for FormID lookups.
    """

    class RustDatabasePool:
        """High-performance database pool with TTL caching.

        Thread-safe SQLite connection pool optimized for FormID lookups and batch queries.
        Includes automatic cache management and query optimization.

        Features:
            - Connection pooling for concurrency
            - TTL-based query caching
            - Batch query optimization
            - Thread-safe operations
            - 25x speedup over Python SQLite
        """

        def __init__(self, db_path: str | Path, max_connections: int = 4) -> None:
            """Create a new database pool.

            Args:
                db_path: Path to the SQLite database file
                max_connections: Maximum number of pooled connections
            """
            ...

        def initialize(self) -> None:
            """Initialize the database pool and prepare connections."""
            ...

        def close(self) -> None:
            """Close all database connections and clear cache."""
            ...

        def get_entry(self, formid: str) -> Optional[dict[str, Any]]:
            """Lookup a single FormID in the database.

            Args:
                formid: FormID to lookup (e.g., "00012E46")

            Returns:
                Database entry as dictionary, or None if not found
            """
            ...

        def batch_lookup(self, formids: list[str]) -> dict[str, dict[str, Any]]:
            """Lookup multiple FormIDs in a single optimized query.

            Args:
                formids: List of FormIDs to lookup

            Returns:
                Dictionary mapping FormIDs to their database entries
            """
            ...

        def get_entries_batch(self, formids: list[str]) -> list[Optional[dict[str, Any]]]:
            """Get entries for multiple FormIDs, preserving order.

            Args:
                formids: List of FormIDs to lookup

            Returns:
                List of entries (None for missing FormIDs)
            """
            ...

        def get_game_table(self) -> str:
            """Get the current game table name being queried.

            Returns:
                Current game table name
            """
            ...

        def set_game_table(self, table_name: str) -> None:
            """Set the game table to query (e.g., 'fallout4', 'skyrim').

            Args:
                table_name: Database table name for the game
            """
            ...

        def clear_cache(self) -> None:
            """Clear the query cache to free memory."""
            ...

        def set_cache_ttl(self, ttl_seconds: int) -> None:
            """Set cache entry time-to-live.

            Args:
                ttl_seconds: Cache TTL in seconds (0 to disable)
            """
            ...

        def optimize(self) -> None:
            """Run database optimization (VACUUM, ANALYZE)."""
            ...

        def get_stats(self) -> dict[str, Any]:
            """Get pool and cache statistics.

            Returns:
                Dictionary with connection count, cache hits, cache size, etc.
            """
            ...

# =============================================================================
# file_io Submodule (from classic-file-io-py)
# =============================================================================

class file_io:
    """File I/O operations submodule with encoding detection.

    Provides high-performance file reading/writing with automatic encoding detection,
    DDS texture header parsing, and intelligent caching.
    """

    class RustFileIOCore:
        """High-performance file I/O core with caching and encoding detection.

        Optimized file operations with 10x speedup over Python I/O through parallel
        reading, SIMD-accelerated encoding detection, and intelligent caching.

        Features:
            - Automatic encoding detection
            - Parallel file operations
            - DDS texture header parsing (40x speedup)
            - Intelligent caching
            - 10x speedup for file I/O
        """

        def __init__(self) -> None:
            """Create a new file I/O core with empty cache."""
            ...

        def read_file(self, path: str | Path, encoding: Optional[str] = None) -> str:
            """Read entire file as string with automatic encoding detection.

            Args:
                path: File path to read
                encoding: Explicit encoding (auto-detected if None)

            Returns:
                File contents as string

            Raises:
                FileNotFoundError: If file doesn't exist
                IOError: If read fails
            """
            ...

        def read_lines(self, path: str | Path, encoding: Optional[str] = None) -> list[str]:
            """Read file as list of lines.

            Args:
                path: File path to read
                encoding: Explicit encoding (auto-detected if None)

            Returns:
                List of lines (without newline terminators)
            """
            ...

        def read_bytes(self, path: str | Path) -> bytes:
            """Read entire file as raw bytes.

            Args:
                path: File path to read

            Returns:
                File contents as bytes

            Raises:
                FileNotFoundError: If file doesn't exist
                IOError: If read fails
            """
            ...

        def write_file(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
            """Write string content to file.

            Args:
                path: Destination file path
                content: String content to write
                encoding: Text encoding (default UTF-8)

            Raises:
                IOError: If write fails
            """
            ...

        def write_lines(self, path: str | Path, lines: list[str], encoding: str = "utf-8") -> None:
            """Write list of lines to file.

            Args:
                path: Destination file path
                lines: Lines to write (newlines added automatically)
                encoding: Text encoding (default UTF-8)

            Raises:
                IOError: If write fails
            """
            ...

        def write_bytes(self, path: str | Path, data: bytes) -> None:
            """Write raw bytes to file.

            Args:
                path: Destination file path
                data: Bytes to write

            Raises:
                IOError: If write fails
            """
            ...

        def append_file(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
            """Append string content to file.

            Args:
                path: File path to append to
                content: String content to append
                encoding: Text encoding (default UTF-8)

            Raises:
                IOError: If append fails
            """
            ...

        def file_exists(self, path: str | Path) -> bool:
            """Check if file exists.

            Args:
                path: File path to check

            Returns:
                True if file exists, False otherwise
            """
            ...

        def get_file_size(self, path: str | Path) -> int:
            """Get file size in bytes.

            Args:
                path: File path to check

            Returns:
                File size in bytes

            Raises:
                FileNotFoundError: If file doesn't exist
            """
            ...

        def read_dds_header(self, path: str | Path) -> Optional[dict[str, Any]]:
            """Parse DDS texture file header (40x speedup).

            Args:
                path: Path to DDS file

            Returns:
                Dictionary with width, height, format, mipmap_count, or None if invalid
            """
            ...

        def read_dds_headers_batch(self, paths: list[str | Path]) -> list[Optional[dict[str, Any]]]:
            """Parse multiple DDS headers in parallel.

            Args:
                paths: List of DDS file paths

            Returns:
                List of header dictionaries (None for invalid files)
            """
            ...

        def clear_cache(self) -> None:
            """Clear the file content cache to free memory."""
            ...

    class EncodingDetector:
        """Encoding detection utility using chardet.

        Detects text file encoding through statistical analysis.
        """

        @staticmethod
        def detect(data: bytes) -> Optional[str]:
            """Detect encoding of byte data.

            Args:
                data: Bytes to analyze

            Returns:
                Detected encoding name (e.g., 'utf-8', 'windows-1252'), or None
            """
            ...

        @staticmethod
        def detect_file(path: str | Path) -> Optional[str]:
            """Detect encoding of a file.

            Args:
                path: File path to analyze

            Returns:
                Detected encoding name, or None
            """
            ...

    class PyLogCollector:
        """Log file collector and organizer.

        Manages crash log files from multiple locations:
        - Copies logs from XSE folder (My Games) to Crash Logs
        - Moves logs from working directory to Crash Logs
        - Collects logs from custom scan directories

        Provides 10x faster file operations through Rust acceleration.
        """

        def __init__(
            self,
            base_folder: str | Path,
            xse_folder: Optional[str | Path] = None,
            custom_folder: Optional[str | Path] = None
        ) -> None:
            """Create a new LogCollector.

            Args:
                base_folder: Working directory where Crash Logs folder will be created
                xse_folder: Optional path to game's XSE folder (e.g., My Games/Fallout4/F4SE)
                custom_folder: Optional path to custom scan directory
            """
            ...

        def collect_all(self) -> list[str]:
            """Execute full log collection workflow.

            Performs all log collection steps:
            1. Ensure directory structure exists
            2. Move logs from base folder to Crash Logs
            3. Copy logs from XSE folder to Crash Logs
            4. Collect all crash log paths for processing

            Returns:
                List of paths to all crash log files ready for processing
            """
            ...

        def move_from_base_folder(self) -> int:
            """Move crash logs and AUTOSCAN reports from base folder to Crash Logs directory.

            Returns:
                Number of files moved
            """
            ...

        def copy_from_xse_folder(self) -> int:
            """Copy crash logs from game's XSE folder to Crash Logs.

            Returns:
                Number of files copied
            """
            ...

        def collect_crash_logs(self) -> list[str]:
            """Collect all crash log file paths for processing.

            Searches for crash-*.log files in:
            - Crash Logs directory (after moving/copying operations)
            - Custom scan folder (if configured)

            Returns:
                List of paths to all crash log files found
            """
            ...

        def crash_logs_dir(self) -> str:
            """Get the path to the Crash Logs directory.

            Returns:
                Path to Crash Logs directory as a string
            """
            ...

        def pastebin_dir(self) -> str:
            """Get the path to the Pastebin subdirectory.

            Returns:
                Path to Pastebin directory as a string
            """
            ...

# =============================================================================
# scanlog Submodule (from classic-scanlog-py)
# =============================================================================

class scanlog:
    """Log scanning operations submodule.

    Provides high-performance crash log parsing, FormID analysis, pattern matching,
    and report generation with 40-150x speedup over Python implementations.

    Features:
        - SIMD-accelerated log parsing (10x speedup)
        - FormID extraction and analysis (25x speedup)
        - Pattern matching with caching (20x speedup)
        - Record scanning (40x speedup)
        - GPU detection
        - Complete orchestration pipeline
    """

    # =============================================================================
    # Main Orchestrator
    # =============================================================================

    class RustOrchestrator:
        """Python wrapper for OrchestratorCore.

        High-level orchestration of log analysis pipeline including parsing,
        FormID extraction, plugin detection, and report generation.
        """

        def __init__(self, config: AnalysisConfig) -> None:
            """Create orchestrator with analysis configuration.

            Args:
                config: Configuration for analysis operations
            """
            ...

        def config(self) -> AnalysisConfig:
            """Get the current analysis configuration.

            Returns:
                Current AnalysisConfig instance
            """
            ...

        def process_log(self, log_path: str | Path) -> AnalysisResult:
            """Analyze a single crash log file.

            Args:
                log_path: Path to the crash log file

            Returns:
                Analysis results with report lines, counts, and timing
            """
            ...

        def process_logs_batch(self, log_paths: list[str | Path]) -> list[AnalysisResult]:
            """Analyze multiple crash logs in parallel.

            Args:
                log_paths: List of crash log file paths

            Returns:
                List of analysis results for each log
            """
            ...

    # =============================================================================
    # Configuration Classes
    # =============================================================================

    class AnalysisConfig:
        """Python wrapper for AnalysisConfig.

        Configuration for crash log analysis including game settings,
        ignore lists, and version information.
        """

        def __init__(
            self,
            game: str,
            game_version: str,
            crashgen_name: str,
            crashgen_latest: str,
            xse_acronym: str,
            vr_mode: bool = False,
            ignore_list: Optional[list[str]] = None,
            ignore_plugins: Optional[list[str]] = None,
            ignore_records: Optional[list[str]] = None,
        ) -> None:
            """Create analysis configuration.

            Args:
                game: Game name (e.g., 'Fallout4', 'Skyrim')
                game_version: Game version string
                crashgen_name: Crash generator name
                crashgen_latest: Latest crash generator version
                xse_acronym: Script extender acronym (F4SE, SKSE)
                vr_mode: Whether analyzing VR game logs
                ignore_list: List of patterns to ignore
                ignore_plugins: List of plugins to ignore
                ignore_records: List of record types to ignore
            """
            ...

        @property
        def game(self) -> str:
            """Game name."""
            ...

        @property
        def game_version(self) -> str:
            """Game version string."""
            ...

        @property
        def crashgen_name(self) -> str:
            """Crash generator name."""
            ...

        @property
        def crashgen_latest(self) -> str:
            """Latest crash generator version."""
            ...

        @property
        def xse_acronym(self) -> str:
            """Script extender acronym."""
            ...

        @property
        def vr_mode(self) -> bool:
            """Whether VR mode is enabled."""
            ...

        @property
        def ignore_list(self) -> list[str]:
            """List of patterns to ignore."""
            ...

        @property
        def ignore_plugins(self) -> list[str]:
            """List of plugins to ignore."""
            ...

        @property
        def ignore_records(self) -> list[str]:
            """List of record types to ignore."""
            ...

    class AnalysisResult:
        """Python wrapper for AnalysisResult.

        Results of crash log analysis including report content,
        statistics, and error information.
        """

        @property
        def success(self) -> bool:
            """Whether analysis completed successfully."""
            ...

        @property
        def log_path(self) -> str:
            """Path to the analyzed log file."""
            ...

        @property
        def report_lines(self) -> list[str]:
            """Generated report lines."""
            ...

        @property
        def formid_count(self) -> int:
            """Number of FormIDs found."""
            ...

        @property
        def plugin_count(self) -> int:
            """Number of plugins detected."""
            ...

        @property
        def suspect_count(self) -> int:
            """Number of suspect entries found."""
            ...

        @property
        def processing_time_ms(self) -> int:
            """Processing time in milliseconds."""
            ...

        @property
        def error(self) -> Optional[str]:
            """Error message if analysis failed."""
            ...

    # =============================================================================
    # Core Parsing and Analysis Classes
    # =============================================================================

    class LogParser:
        """Python-facing log parser wrapper.

        SIMD-accelerated log parsing with segment detection, pattern matching,
        and section extraction. Offers 10x speedup over Python regex parsing.
        """

        def __init__(self) -> None:
            """Create a new LogParser instance."""
            ...

        def parse_segments(self, content: str) -> dict[str, str]:
            """Parse log into segments using SIMD-optimized boundary detection.

            Args:
                content: Full log file content

            Returns:
                Dictionary mapping segment names to content
            """
            ...

        def parse_segments_parallel(self, content: str, chunk_size: int = 10000) -> dict[str, str]:
            """Parse segments in parallel for large logs.

            Args:
                content: Full log file content
                chunk_size: Size of chunks for parallel processing

            Returns:
                Dictionary mapping segment names to content
            """
            ...

        def extract_formids(self, content: str) -> list[str]:
            """Find all FormIDs in the log using optimized pattern matching.

            Args:
                content: Log content to search

            Returns:
                List of FormID strings (e.g., ['00012E46', 'FF000800'])
            """
            ...

        def extract_plugins(self, content: str) -> list[str]:
            """Find all plugins mentioned in the log.

            Args:
                content: Log content to search

            Returns:
                List of plugin names
            """
            ...

        def extract_addresses(self, content: str) -> list[str]:
            """Find all memory addresses in the log.

            Args:
                content: Log content to search

            Returns:
                List of memory address strings
            """
            ...

        def find_patterns(self, content: str, patterns: list[str]) -> dict[str, list[str]]:
            """Find all pattern matches in parallel with caching.

            Args:
                content: Content to search
                patterns: List of regex patterns

            Returns:
                Dictionary mapping patterns to their matches
            """
            ...

        def find_patterns_chunked(
            self,
            content: str,
            patterns: list[str],
            chunk_size: int = 10000
        ) -> dict[str, list[str]]:
            """Find patterns in parallel chunks for better performance.

            Args:
                content: Content to search
                patterns: List of regex patterns
                chunk_size: Size of chunks for parallel processing

            Returns:
                Dictionary mapping patterns to their matches
            """
            ...

        def find_errors(self, content: str) -> list[str]:
            """Find error and exception patterns.

            Args:
                content: Content to search

            Returns:
                List of error/exception lines
            """
            ...

        def get_section(self, content: str, section_name: str) -> Optional[str]:
            """Get specific section by name (commonly used sections).

            Args:
                content: Full log content
                section_name: Section name (e.g., 'MODULES', 'CALLSTACK')

            Returns:
                Section content or None if not found
            """
            ...

        def extract_section(self, content: str, section_name: str) -> Optional[str]:
            """Extract section from log (Python-exposed method).

            Args:
                content: Full log content
                section_name: Section name to extract

            Returns:
                Section content or None
            """
            ...

        def extract_sections_batch(
            self,
            content: str,
            section_names: list[str]
        ) -> dict[str, Optional[str]]:
            """Extract multiple sections batch (Python-exposed method).

            Args:
                content: Full log content
                section_names: List of section names to extract

            Returns:
                Dictionary mapping section names to content (None if not found)
            """
            ...

        def parse_crash_header(self, content: str) -> dict[str, Any]:
            """Parse crash header (Python-exposed method).

            Args:
                content: Crash log content

            Returns:
                Dictionary with crash header fields
            """
            ...

        def parse_all_sections(self, content: str) -> dict[str, str]:
            """Parse and extract all important sections at once.

            Args:
                content: Full log content

            Returns:
                Dictionary mapping section names to content
            """
            ...

        def parse_complete(self, content: str) -> dict[str, Any]:
            """Optimized batch operation: complete log analysis in single FFI call.

            Args:
                content: Full log content

            Returns:
                Dictionary with all parsed data (segments, formids, plugins, etc.)
            """
            ...

        def get_segment_sizes(self, content: str) -> dict[str, int]:
            """Count lines in each segment for analysis.

            Args:
                content: Full log content

            Returns:
                Dictionary mapping segment names to line counts
            """
            ...

        def add_pattern(self, name: str, pattern: str) -> None:
            """Add a custom regex pattern for matching.

            Args:
                name: Pattern name
                pattern: Regex pattern string
            """
            ...

        def clear_caches(self) -> None:
            """Clear all caches to free memory."""
            ...

        def get_stats(self) -> dict[str, Any]:
            """Get performance statistics.

            Returns:
                Dictionary with cache hits, misses, sizes, etc.
            """
            ...

        def benchmark(self, content: str, iterations: int = 100) -> dict[str, float]:
            """Benchmark parsing performance on given data.

            Args:
                content: Content to benchmark
                iterations: Number of iterations

            Returns:
                Dictionary with timing statistics
            """
            ...

    class FormIDAnalyzer:
        """Python wrapper for FormIDAnalyzer (backward compatibility).

        FormID parsing, validation, and batch analysis with plugin resolution.
        Offers 25x speedup over Python implementations.
        """

        def __init__(self) -> None:
            """Create a new FormIDAnalyzer instance."""
            ...

        def parse_formid(self, formid_str: str) -> Optional[dict[str, Any]]:
            """Parse and validate a FormID string.

            Args:
                formid_str: FormID string (e.g., '00012E46')

            Returns:
                Dictionary with parsed FormID components, or None if invalid
            """
            ...

        def extract_formids(self, content: str) -> list[str]:
            """Extract FormIDs from a callstack segment.

            Args:
                content: Callstack or log content

            Returns:
                List of valid FormID strings
            """
            ...

        def analyze_batch(self, formids: list[str], plugins: list[str]) -> dict[str, Any]:
            """Batch analyze FormIDs with plugin resolution.

            Args:
                formids: List of FormIDs to analyze
                plugins: List of available plugins

            Returns:
                Dictionary with analysis results
            """
            ...

        def clear_cache(self) -> None:
            """Clear all caches."""
            ...

        def cache_stats(self) -> dict[str, int]:
            """Get cache statistics.

            Returns:
                Dictionary with cache size and hit rate
            """
            ...

    class RustFormIDAnalyzer:
        """Rust-accelerated FormID analyzer (new implementation)."""

        def __init__(self) -> None:
            """Create a new RustFormIDAnalyzer instance."""
            ...

    class FormIDAnalyzerCore:
        """Core FormID analysis engine."""

        def __init__(self) -> None:
            """Create a new FormIDAnalyzerCore instance."""
            ...

    class PatternMatcher:
        """Python wrapper for PatternMatcher.

        High-performance regex pattern matching with caching and parallel execution.
        """

        def __init__(self) -> None:
            """Create a new PatternMatcher instance."""
            ...

        def find_all(self, text: str, pattern: str) -> list[str]:
            """Find all matches in text.

            Args:
                text: Text to search
                pattern: Regex pattern

            Returns:
                List of match strings
            """
            ...

        def find_first(self, text: str, pattern: str) -> Optional[str]:
            """Find first match in text.

            Args:
                text: Text to search
                pattern: Regex pattern

            Returns:
                First match or None
            """
            ...

        def has_match(self, text: str, pattern: str) -> bool:
            """Check if text has any match.

            Args:
                text: Text to search
                pattern: Regex pattern

            Returns:
                True if pattern matches
            """
            ...

        def replace_all(self, text: str, pattern: str, replacement: str) -> str:
            """Replace all matches with replacement string.

            Args:
                text: Text to process
                pattern: Regex pattern
                replacement: Replacement string

            Returns:
                Text with replacements
            """
            ...

        def clear_cache(self) -> None:
            """Clear pattern cache."""
            ...

        def get_stats(self) -> dict[str, int]:
            """Get cache statistics (pattern_count, cache_size).

            Returns:
                Dictionary with statistics
            """
            ...

    class RecordScanner:
        """Python wrapper for RecordScanner.

        Fast record type scanning in callstack segments with caching.
        """

        def __init__(self) -> None:
            """Create a new RecordScanner instance."""
            ...

        def extract_records(self, content: str) -> list[str]:
            """Extract records from callstack segment.

            Args:
                content: Callstack content

            Returns:
                List of record type strings
            """
            ...

        def scan_named_records(self, content: str, record_names: list[str]) -> dict[str, int]:
            """Scan named records from callstack segment.

            Args:
                content: Callstack content
                record_names: List of record type names to find

            Returns:
                Dictionary mapping record names to counts
            """
            ...

        def clear_cache(self) -> None:
            """Clear scanner cache."""
            ...

    class GpuDetector:
        """Python wrapper for GpuDetector.

        GPU information extraction from system specification strings.
        """

        def __init__(self) -> None:
            """Create a new GpuDetector instance."""
            ...

        def extract_gpu_info(self, sysinfo: str) -> Optional[GpuInfo]:
            """Extract GPU information from system specification.

            Args:
                sysinfo: System information string

            Returns:
                GPU information or None if not found
            """
            ...

        def extract_gpu_info_batch(self, sysinfos: list[str]) -> list[Optional[GpuInfo]]:
            """Batch extract GPU info from multiple logs.

            Args:
                sysinfos: List of system information strings

            Returns:
                List of GPU information (None for entries without GPU)
            """
            ...

    class GpuInfo:
        """GPU information container."""

        @property
        def name(self) -> str:
            """GPU name/model."""
            ...

        @property
        def vendor(self) -> GpuVendor:
            """GPU vendor."""
            ...

        @property
        def memory_mb(self) -> Optional[int]:
            """GPU memory in MB."""
            ...

    class GpuVendor:
        """GPU vendor enumeration."""

        NVIDIA: int
        AMD: int
        INTEL: int
        UNKNOWN: int

    # =============================================================================
    # Additional Analysis Components
    # =============================================================================

    class PluginAnalyzer:
        """Plugin analysis and detection."""

        def __init__(self) -> None:
            """Create a new PluginAnalyzer instance."""
            ...

    class SuspectScanner:
        """Suspect pattern scanning."""

        def __init__(self) -> None:
            """Create a new SuspectScanner instance."""
            ...

    class SettingsValidator:
        """Settings validation."""

        def __init__(self) -> None:
            """Create a new SettingsValidator instance."""
            ...

    class ReportGenerator:
        """Report generation orchestration."""

        def __init__(self) -> None:
            """Create a new ReportGenerator instance."""
            ...

    class ReportComposer:
        """Report composition and formatting."""

        def __init__(self) -> None:
            """Create a new ReportComposer instance."""
            ...

    class ReportFragment:
        """Report fragment container."""

        def __init__(self) -> None:
            """Create a new ReportFragment instance."""
            ...

    class ParallelReportProcessor:
        """Parallel report processing."""

        def __init__(self) -> None:
            """Create a new ParallelReportProcessor instance."""
            ...

    class FcxModeHandler:
        """FCX mode handling."""

        def __init__(self) -> None:
            """Create a new FcxModeHandler instance."""
            ...

    class StringPool:
        """String pooling for memory efficiency."""

        def __init__(self) -> None:
            """Create a new StringPool instance."""
            ...

    # =============================================================================
    # Standalone Utility Functions
    # =============================================================================

    def is_valid_formid(formid: str) -> bool:
        """Check if a string is a valid FormID.

        Args:
            formid: String to validate

        Returns:
            True if valid FormID format
        """
        ...

    def extract_formids_batch(contents: list[str]) -> list[list[str]]:
        """Extract FormIDs from multiple content strings in parallel.

        Args:
            contents: List of content strings to search

        Returns:
            List of FormID lists for each content string
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

    def scan_records_batch(contents: list[str]) -> list[list[str]]:
        """Scan for records in multiple content strings.

        Args:
            contents: List of content strings

        Returns:
            List of record lists for each content
        """
        ...

    def contains_plugin(content: str, plugin_name: str) -> bool:
        """Check if content contains a plugin reference.

        Args:
            content: Content to search
            plugin_name: Plugin name to find

        Returns:
            True if plugin found
        """
        ...

    def contains_record(content: str, record_type: str) -> bool:
        """Check if content contains a record type.

        Args:
            content: Content to search
            record_type: Record type to find

        Returns:
            True if record type found
        """
        ...

    def detect_mods_single(content: str, mod_patterns: list[str]) -> list[str]:
        """Detect mods using single pattern matching.

        Args:
            content: Content to search
            mod_patterns: List of mod patterns

        Returns:
            List of detected mod names
        """
        ...

    def detect_mods_double(content: str, mod_patterns: list[tuple[str, str]]) -> list[str]:
        """Detect mods using double pattern matching.

        Args:
            content: Content to search
            mod_patterns: List of (pattern1, pattern2) tuples

        Returns:
            List of detected mod names
        """
        ...

    def detect_mods_important(content: str, important_mods: dict[str, list[str]]) -> list[str]:
        """Detect important mods from priority list.

        Args:
            content: Content to search
            important_mods: Dictionary of mod categories to patterns

        Returns:
            List of detected important mod names
        """
        ...

    def detect_mods_batch(contents: list[str], mod_patterns: list[str]) -> list[list[str]]:
        """Batch detect mods across multiple contents.

        Args:
            contents: List of content strings
            mod_patterns: List of mod patterns

        Returns:
            List of detected mod lists for each content
        """
        ...

    def detect_plugins_batch(contents: list[str]) -> list[list[str]]:
        """Batch detect plugins across multiple contents.

        Args:
            contents: List of content strings

        Returns:
            List of plugin lists for each content
        """
        ...

# =============================================================================
# utils Submodule (from classic-shared)
# =============================================================================

class utils:
    """Utility functions submodule from classic-shared."""
    ...

"""
Python compatibility adapters for Rust extensions.

These classes provide drop-in replacements for existing Python implementations,
maintaining full API compatibility while leveraging Rust performance.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for AsyncBridge import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from ClassicLib.AsyncBridge import AsyncBridge
except ImportError:
    # Fallback AsyncBridge implementation if not in CLASSIC environment
    class AsyncBridge:
        @staticmethod
        def get_instance():
            return AsyncBridge()

        def run_async(self, coro):
            return asyncio.run(coro)

# Import Rust modules
from . import _rust


class FileIOCore:
    """
    Drop-in replacement for Python FileIOCore with Rust performance.

    Provides async file I/O operations with encoding detection and caching.
    """

    def __init__(self):
        """Initialize the Rust FileIOCore."""
        self._rust_core = _rust.file_io.RustFileIOCore()
        self._bridge = AsyncBridge.get_instance()

    async def read_file(self, path: Path) -> str:
        """
        Read a file asynchronously with encoding detection.

        Args:
            path: Path to the file to read

        Returns:
            File contents as string
        """
        return await self._rust_core.read_file(str(path))

    def read_file_sync(self, path: Path) -> str:
        """
        Synchronous wrapper for read_file.

        Args:
            path: Path to the file to read

        Returns:
            File contents as string
        """
        return self._bridge.run_async(self.read_file(path))

    async def write_file(self, path: Path, content: str) -> None:
        """
        Write a file asynchronously.

        Args:
            path: Path to write to
            content: Content to write
        """
        await self._rust_core.write_file(str(path), content)

    def write_file_sync(self, path: Path, content: str) -> None:
        """
        Synchronous wrapper for write_file.

        Args:
            path: Path to write to
            content: Content to write
        """
        self._bridge.run_async(self.write_file(path, content))

    async def clear_cache(self) -> None:
        """Clear the internal read cache."""
        await self._rust_core.clear_cache()


class FormIDAnalyzer:
    """
    Drop-in replacement for Python FormIDAnalyzer with Rust performance.

    Provides ultra-fast FormID parsing and validation.
    """

    def __init__(self):
        """Initialize the Rust FormIDAnalyzer."""
        self._rust_analyzer = _rust.scanlog.FormIDAnalyzer()

    def parse_formid(self, formid: str) -> int | None:
        """
        Parse and validate a FormID string.

        Args:
            formid: FormID string to parse

        Returns:
            Parsed FormID as integer, or None if invalid
        """
        return self._rust_analyzer.parse_formid(formid)

    def analyze_batch(
        self, formids: list[str], plugins: dict[str, str]
    ) -> list[tuple[str, str | None]]:
        """
        Batch analyze FormIDs with plugin resolution.

        Args:
            formids: List of FormID strings
            plugins: Dictionary mapping plugin indices to names

        Returns:
            List of tuples (formid, resolved_plugin_name)
        """
        return self._rust_analyzer.analyze_batch(formids, plugins)

    def clear_cache(self) -> None:
        """Clear all internal caches."""
        self._rust_analyzer.clear_cache()

    def cache_stats(self) -> tuple[int, int]:
        """Get cache statistics."""
        return self._rust_analyzer.cache_stats()


class LogParser:
    """
    Drop-in replacement for Python log parser with Rust performance.

    Provides high-speed log parsing and segment extraction.
    """

    def __init__(self):
        """Initialize the Rust LogParser."""
        self._rust_parser = _rust.scanlog.LogParser()

    def parse_segments(self, lines: list[str]) -> list[list[str]]:
        """
        Parse log into segments.

        Args:
            lines: Log lines to parse

        Returns:
            List of segments, each containing lines
        """
        return self._rust_parser.parse_segments(lines)

    def find_patterns(self, lines: list[str]) -> list[tuple[int, str, str]]:
        """
        Find all pattern matches in log lines.

        Args:
            lines: Log lines to search

        Returns:
            List of tuples (line_number, pattern, matching_line)
        """
        return self._rust_parser.find_patterns(lines)

    def extract_section(
        self, lines: list[str], start_marker: str, end_marker: str
    ) -> list[str] | None:
        """
        Extract a specific section from log.

        Args:
            lines: Log lines
            start_marker: Section start marker
            end_marker: Section end marker

        Returns:
            Extracted section lines, or None if not found
        """
        return self._rust_parser.extract_section(lines, start_marker, end_marker)


class PatternMatcher:
    """
    Drop-in replacement for Python pattern matcher with Rust performance.

    Uses Aho-Corasick algorithm for efficient multi-pattern matching.
    """

    def __init__(self, patterns: list[str]):
        """
        Initialize the Rust PatternMatcher.

        Args:
            patterns: List of patterns to match
        """
        self._rust_matcher = _rust.scanlog.PatternMatcher(patterns)

    def find_all(self, text: str) -> list[tuple[int, str]]:
        """
        Find all pattern matches in text.

        Args:
            text: Text to search

        Returns:
            List of tuples (position, matching_pattern)
        """
        return self._rust_matcher.find_all(text)

    def has_match(self, text: str) -> bool:
        """
        Check if any pattern matches.

        Args:
            text: Text to check

        Returns:
            True if any pattern matches
        """
        return self._rust_matcher.has_match(text)

    def find_first(self, text: str) -> tuple[int, str] | None:
        """
        Find first pattern match.

        Args:
            text: Text to search

        Returns:
            Tuple (position, pattern) or None if no match
        """
        return self._rust_matcher.find_first(text)

    def replace_all(self, text: str, replacement: str) -> str:
        """
        Replace all pattern matches.

        Args:
            text: Text to process
            replacement: Replacement string

        Returns:
            Text with replacements
        """
        return self._rust_matcher.replace_all(text, replacement)

    def clear_cache(self) -> None:
        """Clear the match cache."""
        self._rust_matcher.clear_cache()


class DatabasePool:
    """
    Drop-in replacement for Python database pool with Rust performance.

    Provides connection pooling and cached queries for SQLite databases.
    """

    def __init__(self):
        """Initialize the Rust DatabasePool."""
        self._rust_pool = _rust.database.RustDatabasePool()
        self._bridge = AsyncBridge.get_instance()

    async def get_connection(self, db_path: Path) -> None:
        """
        Get or create a database connection.

        Args:
            db_path: Path to database file
        """
        await self._rust_pool.get_connection(str(db_path))

    async def batch_lookup(
        self, db_path: Path, table: str, keys: list[str]
    ) -> list[str | None]:
        """
        Execute batch lookup queries.

        Args:
            db_path: Path to database
            table: Table name
            keys: List of keys to look up

        Returns:
            List of values (None for missing keys)
        """
        return await self._rust_pool.batch_lookup(str(db_path), table, keys)

    def batch_lookup_sync(
        self, db_path: Path, table: str, keys: list[str]
    ) -> list[str | None]:
        """
        Synchronous wrapper for batch_lookup.

        Args:
            db_path: Path to database
            table: Table name
            keys: List of keys to look up

        Returns:
            List of values (None for missing keys)
        """
        return self._bridge.run_async(self.batch_lookup(db_path, table, keys))

    def clear_cache(self) -> None:
        """Clear query cache."""
        self._rust_pool.clear_cache()

    def get_stats(self) -> tuple[int, int]:
        """Get pool statistics (connections, cached_queries)."""
        return self._rust_pool.get_stats()

    async def close_all(self) -> None:
        """Close all database connections."""
        await self._rust_pool.close_all()


class StringProcessor:
    """
    Drop-in replacement for Python string processor with Rust performance.

    Provides optimized string operations with interning and parallel processing.
    """

    def __init__(self):
        """Initialize the Rust StringProcessor."""
        self._rust_processor = _rust.utils.StringProcessor()

    def intern(self, s: str) -> str:
        """
        Intern a string for memory efficiency.

        Args:
            s: String to intern

        Returns:
            Interned string
        """
        return self._rust_processor.intern(s)

    def process_batch(self, strings: list[str], operation: str) -> list[str]:
        """
        Process multiple strings in parallel.

        Args:
            strings: Strings to process
            operation: Operation to apply (upper, lower, trim, normalize)

        Returns:
            Processed strings
        """
        return self._rust_processor.process_batch(strings, operation)

    def common_prefix(self, strings: list[str]) -> str:
        """
        Find common prefix of multiple strings.

        Args:
            strings: List of strings

        Returns:
            Common prefix
        """
        return self._rust_processor.common_prefix(strings)

    def split_lines(self, text: str) -> list[str]:
        """
        Split text into lines efficiently.

        Args:
            text: Text to split

        Returns:
            List of lines
        """
        return self._rust_processor.split_lines(text)

    def join_lines(self, lines: list[str], separator: str = "\n") -> str:
        """
        Join lines with a separator.

        Args:
            lines: Lines to join
            separator: Separator string

        Returns:
            Joined text
        """
        return self._rust_processor.join_lines(lines, separator)

    def pool_stats(self) -> int:
        """Get string pool size."""
        return self._rust_processor.pool_stats()

    def clear_pool(self) -> None:
        """Clear the string pool."""
        self._rust_processor.clear_pool()

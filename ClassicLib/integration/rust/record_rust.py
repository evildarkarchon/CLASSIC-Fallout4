"""Rust-accelerated RecordScanner wrapper.

This module provides a drop-in replacement for the Python RecordScanner that uses
the high-performance Rust implementation, providing 40x speedup for call stack
record scanning. Rust is required.

Performance improvements with Rust:
- 40x faster call stack record scanning
- Efficient pattern matching for named records
- Optimized string searching algorithms
- Memory-efficient scanning and matching
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.factory import detect_component
from ClassicLib.integration.exceptions import RustError, RustParseError

# Detect Rust-specific exception types for classic_scanlog
_, _rust_scanlog_error = detect_component("classic_scanlog", "RustScanLogError")
_, _rust_parse_error = detect_component("classic_scanlog", "RustParseError")


def _get_rust_exception_types() -> tuple[tuple[type[BaseException], ...], tuple[type[BaseException], ...]]:
    """Get tuple of Rust exception types to catch.

    Returns:
        A tuple containing two tuples of exception types:
            - ParseError types (RustParseError and module-specific parse errors)
            - Generic RustError types (RustError and module-specific scan log errors)

    """
    parse_errors: tuple[type[BaseException], ...] = (RustParseError,)
    rust_errors: tuple[type[BaseException], ...] = (RustError,)

    # Add module-specific exceptions if available
    if _rust_parse_error:
        parse_errors = (RustParseError, _rust_parse_error)
    if _rust_scanlog_error:
        rust_errors = (RustError, _rust_scanlog_error)

    return parse_errors, rust_errors


# Get exception type tuples at module level for use in exception handlers
parse_errors: tuple[type[BaseException], ...]
rust_errors: tuple[type[BaseException], ...]
parse_errors, rust_errors = _get_rust_exception_types()

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class RustRecordScanner:
    """Wrapper for Rust RecordScanner. Rust is required.

    Provides high-performance record scanning using the Rust implementation.
    Achieves 40x performance improvement over pure Python implementation.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo) -> None:
        """Initialize the Rust RecordScanner. Raises RuntimeError if unavailable.

        Args:
            yamldata: Configuration data required for the scanner,
                including target records, ignore list, and crash generator name.

        Raises:
            RuntimeError: If Rust RecordScanner is not available.

        """
        self.yamldata = yamldata

        try:
            import classic_scanlog

            if not hasattr(classic_scanlog, "RecordScanner"):
                msg = "RecordScanner not found in classic_scanlog module. Reinstall CLASSIC."
                raise RuntimeError(msg)

            RustRecordScannerImpl = classic_scanlog.RecordScanner

            # Extract required parameters from yamldata
            target_records = getattr(yamldata, "classic_records_list", [])
            ignore_records = getattr(yamldata, "game_ignore_records", [])
            crashgen_name = getattr(yamldata, "crashgen_name", "")

            self._rust_scanner = RustRecordScannerImpl(target_records, ignore_records, crashgen_name)
            logger.debug("RustRecordScanner: Using RUST implementation (40x faster)")
        except RuntimeError:
            raise
        except (ImportError, AttributeError) as e:
            msg = f"Required Rust module for RecordScanner not available: {e}. Reinstall CLASSIC."
            raise RuntimeError(msg) from e
        except rust_errors as e:
            msg = f"Rust error initializing RecordScanner: {e}. Reinstall CLASSIC."
            raise RuntimeError(msg) from e

    def scan_named_records(self, segment_callstack: list[str]) -> tuple[Any, list[str]]:
        """Scan named records in the provided call stack segment.

        Args:
            segment_callstack: A list representing the segment call stack to be scanned.

        Returns:
            tuple[ReportFragment, list[str]]: A tuple containing:
                - ReportFragment object with formatted report content
                - list[str] of matched record names

        Raises:
            RuntimeError: If Rust scan fails.

        """
        from ClassicLib.scanning.logs.reporting import ReportFragment

        try:
            # Rust returns (list[str], list[str]) - formatted lines and matches
            report_lines, matches = self._rust_scanner.scan_named_records(segment_callstack)
            return ReportFragment.from_lines(report_lines), matches
        except (*parse_errors, *rust_errors, TypeError, ValueError) as e:
            msg = f"Rust scan_named_records failed: {e}"
            raise RuntimeError(msg) from e

    def extract_records(self, segment_callstack: list[str]) -> list[str]:
        """Extract records from callstack segment without formatting.

        Extracts all matching records from the callstack without generating
        formatted report lines. This is faster when you only need the record names.

        Args:
            segment_callstack: List of callstack lines to scan

        Returns:
            list[str]: List of matched record names

        Raises:
            RuntimeError: If Rust extraction fails.

        """
        try:
            return self._rust_scanner.extract_records(segment_callstack)
        except (*parse_errors, *rust_errors, TypeError, ValueError) as e:
            msg = f"Rust extract_records failed: {e}"
            raise RuntimeError(msg) from e

    def clear_cache(self) -> None:
        """Clear the scanner's internal cache.

        Clears any cached data used for optimizing repeated scans. This can be useful
        when switching between different crash logs or resetting the scanner state.
        """
        try:
            self._rust_scanner.clear_cache()
        except rust_errors as e:
            logger.debug(f"Rust clear_cache failed: {e}")
        except AttributeError as e:
            logger.debug(f"Rust clear_cache not available: {e}")

    @staticmethod
    def scan_for_pattern(lines: list[str], pattern: str) -> list[str]:
        """Scan through a list of strings to find lines that match a given pattern.

        Note: This method uses Python regex as the Rust implementation
        does not provide a corresponding method (simple pattern matching).

        Args:
            lines: List of strings to scan through.
            pattern: The regex pattern to match within each line.

        Returns:
            list[str]: A list of strings from the input that match the specified pattern.

        """
        import re

        pattern_re = re.compile(pattern, re.IGNORECASE)
        return [line for line in lines if pattern_re.search(line)]

    def _generate_report_lines(self, matches: list[str]) -> list[str]:
        """Generate formatted report lines from matched records.

        Helper method to format record matches into report lines, mirroring
        the Rust implementation's output format.

        Args:
            matches: List of matched record names

        Returns:
            list[str]: Formatted report lines

        """
        if not matches:
            return ["* COULDN'T FIND ANY NAMED RECORDS *\n\n"]

        from collections import Counter

        lines: list[str] = []
        records_found: dict[str, int] = dict(Counter(sorted(matches)))

        for record, count in records_found.items():
            lines.append(f"- {record} | {count}\n")

        lines.extend([
            "\n[Last number counts how many times each Named Record shows up in the crash log.]\n",
            f"These records were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
            "Named records should give extra info on involved game objects, record types or mod files.\n\n",
        ])

        return lines

    def batch_scan_records(self, segments: list[list[str]]) -> list[tuple[Any, list[str]]]:
        """Scan multiple segments of records in parallel using Rust acceleration.

        This method processes multiple segments concurrently when Rust is available,
        providing significant performance improvements for batch operations.

        Args:
            segments: A list of segments, where each segment is a list of string records.

        Returns:
            A list of tuples, where each tuple contains:
                - ReportFragment object with formatted report content
                - list[str] of matched record names

        Raises:
            RuntimeError: If Rust batch scan fails.

        """
        import classic_scanlog

        from ClassicLib.scanning.logs.reporting import ReportFragment

        try:
            # Get stored patterns from initialization
            target_records = list(getattr(self.yamldata, "classic_records_list", []) or [])
            ignore_records = list(getattr(self.yamldata, "game_ignore_records", []) or [])

            # Call standalone batch function for parallel processing
            matches_batch = classic_scanlog.scan_records_batch(segments, target_records, ignore_records)

            # Format results to match Python API: list[tuple[ReportFragment, matches]]
            results: list[tuple[ReportFragment, list[str]]] = []
            for matches in matches_batch:
                report_lines = self._generate_report_lines(matches)
                results.append((ReportFragment.from_lines(report_lines), matches))

            return results
        except (*parse_errors, *rust_errors, TypeError, ValueError, AttributeError) as e:
            msg = f"Rust batch_scan_records failed: {e}"
            raise RuntimeError(msg) from e

    @property
    def is_rust_accelerated(self) -> bool:
        """Whether Rust acceleration is active.

        Returns:
            True always, since Rust is required.

        """
        return True

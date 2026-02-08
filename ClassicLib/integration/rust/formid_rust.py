"""Rust-accelerated FormIDAnalyzer wrapper.

Thin delegation layer: uses Rust for FormID extraction and matching.
All methods are synchronous. Use AsyncBridge for GUI contexts.
Rust is required.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.exceptions import RustError, RustParseError
from ClassicLib.integration.factory import detect_component

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class FormIDAnalyzer:
    """Wrapper for Rust FormID extraction. Rust is required.

    Uses Rust for extract_formids (50x speedup) and formid_match.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo, show_formid_values: bool, formid_db_exists: bool) -> None:
        """Initialize the Rust FormIDAnalyzer. Raises RuntimeError if unavailable.

        Args:
            yamldata: Scan log configuration data.
            show_formid_values: Whether to display FormID values.
            formid_db_exists: Whether the FormID database exists.

        Raises:
            RuntimeError: If Rust FormIDAnalyzerCore is not available.

        """
        # Store configuration
        self.yamldata = yamldata
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists

        # Try Rust FormIDAnalyzerCore (optimized version with yamldata params)
        rust_available, FormIDAnalyzerCore = detect_component("classic_scanlog", "FormIDAnalyzerCore")
        if not rust_available or FormIDAnalyzerCore is None:
            msg = "FormIDAnalyzerCore not found in classic_scanlog module. Reinstall CLASSIC."
            raise RuntimeError(msg)

        try:
            self._rust_analyzer = FormIDAnalyzerCore(
                show_formid_values,
                getattr(yamldata, "crashgen_name", ""),
                getattr(yamldata, "problematic_plugins", {}),
                getattr(yamldata, "mods_single", {}),
                getattr(yamldata, "mods_double", {}),
            )
            logger.debug("FormIDAnalyzer: Using RUST FormIDAnalyzerCore")
        except (RustError, TypeError, ValueError) as e:
            msg = f"Failed to initialize Rust FormIDAnalyzer: {e}. Reinstall CLASSIC."
            raise RuntimeError(msg) from e

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """Extract FormIDs from a callstack segment.

        Args:
            segment_callstack: Callstack lines to search.

        Returns:
            List of extracted FormID strings.

        Raises:
            RuntimeError: If Rust extraction fails.

        """
        try:
            return self._rust_analyzer.extract_formids(segment_callstack)
        except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
            msg = f"Rust FormID extraction failed: {e}"
            raise RuntimeError(msg) from e

    def formid_match(self, formids: list[str], plugins: dict[str, str], report: Any) -> None:
        """Match FormIDs against plugins and add results to report.

        Args:
            formids: Extracted FormID strings.
            plugins: Plugin name to load order ID mapping.
            report: Report object with add_fragment method.

        Raises:
            RuntimeError: If Rust formid_match fails.

        """
        fragment = self.formid_match_sync(formids, plugins)
        report.add_fragment(fragment)

    def formid_match_sync(self, formids: list[str], plugins: dict[str, str]) -> Any:
        """Match FormIDs against plugins and return ReportFragment.

        Args:
            formids: Extracted FormID strings.
            plugins: Plugin name to load order ID mapping.

        Returns:
            ReportFragment with match results.

        Raises:
            RuntimeError: If Rust formid_match fails.

        """
        from ClassicLib.scanning.logs.reporting import ReportFragment

        try:
            lines = self._rust_analyzer.formid_match(formids, plugins)
            return ReportFragment.from_lines(lines)
        except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
            msg = f"Rust formid_match failed: {e}"
            raise RuntimeError(msg) from e

    def extract_formids_batch(self, segments: list[list[str]]) -> list[list[str]]:
        """Extract FormIDs from multiple segments.

        Args:
            segments: List of callstack segments.

        Returns:
            List of FormID lists, one per segment.

        Raises:
            RuntimeError: If Rust batch extraction fails.

        """
        try:
            rust_available, extract_batch = detect_component("classic_scanlog", "extract_formids_batch")
            if rust_available and extract_batch:
                return extract_batch(segments)
        except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
            msg = f"Rust batch extraction failed: {e}"
            raise RuntimeError(msg) from e

        # Fallback to sequential processing with Rust
        return [self.extract_formids(segment) for segment in segments]

    @property
    def is_rust_accelerated(self) -> bool:
        """Whether Rust acceleration is active.

        Returns:
            True always, since Rust is required.

        """
        return True

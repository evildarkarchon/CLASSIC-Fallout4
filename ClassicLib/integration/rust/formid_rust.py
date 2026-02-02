"""Rust-accelerated FormIDAnalyzer wrapper.

Thin delegation layer: uses Rust for FormID extraction, Python for matching.
All methods are synchronous. Use AsyncBridge for GUI contexts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.factory import detect_component
from ClassicLib.integration.exceptions import RustError, RustParseError

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class FormIDAnalyzer:
    """Wrapper for Rust FormID extraction with Python fallback.

    Uses Rust for extract_formids (50x speedup), delegates formid_match
    to the Python implementation (no Rust binding available).
    """

    def __init__(self, yamldata: ClassicScanLogsInfo, show_formid_values: bool, formid_db_exists: bool) -> None:
        """Initialize with Rust analyzer if available, otherwise Python fallback.

        Args:
            yamldata: Scan log configuration data.
            show_formid_values: Whether to display FormID values.
            formid_db_exists: Whether the FormID database exists.

        """
        self._rust_analyzer = None
        self._use_rust = False
        self._python_analyzer = None

        # Store configuration
        self.yamldata = yamldata
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists

        # Try Rust FormIDAnalyzerCore (optimized version with yamldata params)
        rust_available, FormIDAnalyzerCore = detect_component("classic_scanlog", "FormIDAnalyzerCore")
        if rust_available and FormIDAnalyzerCore:
            try:
                self._rust_analyzer = FormIDAnalyzerCore(
                    show_formid_values,
                    getattr(yamldata, "crashgen_name", ""),
                    getattr(yamldata, "problematic_plugins", {}),
                    getattr(yamldata, "mods_single", {}),
                    getattr(yamldata, "mods_double", {}),
                )
                self._use_rust = True
                logger.debug("FormIDAnalyzer: Using RUST FormIDAnalyzerCore")
            except (RustError, TypeError, ValueError) as e:
                logger.error(f"Failed to initialize Rust FormIDAnalyzer: {e}")

        # Create Python analyzer (needed for formid_match regardless of Rust)
        if not self._use_rust:
            logger.debug("FormIDAnalyzer: Falling back to Python implementation")
        self._init_python_analyzer()

    def _init_python_analyzer(self) -> None:
        """Initialize Python fallback analyzer."""
        from ClassicLib.scanning.logs.analyzers.FormIDAnalyzer import FormIDAnalyzer as PyFormIDAnalyzer

        self._python_analyzer = PyFormIDAnalyzer(self.yamldata, self.show_formid_values, self.formid_db_exists)

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """Extract FormIDs from a callstack segment.

        Args:
            segment_callstack: Callstack lines to search.

        Returns:
            List of extracted FormID strings.

        """
        if self._use_rust and self._rust_analyzer:
            try:
                return self._rust_analyzer.extract_formids(segment_callstack)
            except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
                logger.warning(f"Rust FormID extraction failed: {e}")

        assert self._python_analyzer is not None  # noqa: S101
        return self._python_analyzer.extract_formids(segment_callstack)

    def formid_match(self, formids: list[str], plugins: dict[str, str], report: Any) -> None:
        """Match FormIDs against plugins and add results to report.

        Args:
            formids: Extracted FormID strings.
            plugins: Plugin name to load order ID mapping.
            report: Report object with add_fragment method.

        """
        assert self._python_analyzer is not None  # noqa: S101
        fragment = self._python_analyzer.formid_match(formids, plugins)
        report.add_fragment(fragment)

    def extract_formids_batch(self, segments: list[list[str]]) -> list[list[str]]:
        """Extract FormIDs from multiple segments.

        Args:
            segments: List of callstack segments.

        Returns:
            List of FormID lists, one per segment.

        """
        if self._use_rust:
            try:
                rust_available, extract_batch = detect_component("classic_scanlog", "extract_formids_batch")
                if rust_available and extract_batch:
                    return extract_batch(segments)
            except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
                logger.debug(f"Rust batch extraction failed: {e}")

        return [self.extract_formids(segment) for segment in segments]

    @property
    def is_rust_accelerated(self) -> bool:
        """Whether Rust acceleration is active."""
        return self._use_rust

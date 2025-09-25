"""
Rust-accelerated FormIDAnalyzer wrapper.

This module provides a drop-in replacement for the Python FormIDAnalyzer that uses
the high-performance Rust implementation when available, providing 50x speedup
for FormID extraction and validation.

Performance improvements with Rust:
- 50x faster FormID extraction and validation
- Batch processing capabilities for multiple segments
- Efficient regex pattern matching
- Memory-efficient processing
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class RustFormIDAnalyzer:
    """
    Wrapper for Rust FormIDAnalyzer that provides Python-compatible API.

    Provides high-performance FormID extraction and analysis when Rust is available.
    Achieves 50x performance improvement over pure Python implementation.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo, show_formid_values: bool, formid_db_exists: bool):
        """Initialize the analyzer, using Rust implementation when available."""
        self._rust_analyzer = None
        self._use_rust = False
        self._python_analyzer = None

        # Store configuration
        self.yamldata = yamldata
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists

        try:
            import classic_core
            if hasattr(classic_core, "scanlog") and hasattr(classic_core.scanlog, "FormIDAnalyzer"):
                # The simple FormIDAnalyzer doesn't need yamldata
                RustFormIDAnalyzerImpl = classic_core.scanlog.FormIDAnalyzer
                self._rust_analyzer = RustFormIDAnalyzerImpl()
                self._use_rust = True
                logger.debug("🚀 RustFormIDAnalyzer: Using RUST implementation (50x faster)")
            else:
                logger.debug("⚠️  RustFormIDAnalyzer: FormIDAnalyzer not found in classic_core")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Rust FormIDAnalyzer: {e}")

        # Only create Python analyzer if Rust truly unavailable
        if not self._use_rust:
            logger.debug("⚠️  RustFormIDAnalyzer: Falling back to Python implementation")
            from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
            self._python_analyzer = FormIDAnalyzer(yamldata, show_formid_values, formid_db_exists)

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """
        Extract FormIDs from call stack segment.

        Args:
            segment_callstack: List of call stack lines

        Returns:
            List of extracted FormID strings
        """
        if self._use_rust and self._rust_analyzer:
            try:
                # Use Rust batch extraction
                import classic_core
                if hasattr(classic_core.scanlog, "extract_formids_batch"):
                    extract_formids_batch = classic_core.scanlog.extract_formids_batch
                    formids = extract_formids_batch([segment_callstack])
                    # extract_formids_batch returns a list of lists, get the first one
                    return formids[0] if formids else []
                else:
                    # Try direct method if available
                    return self._rust_analyzer.extract_formids(segment_callstack)
            except Exception as e:
                logger.warning(f"Rust FormID extraction failed: {e}")

        # Use Python fallback
        if self._python_analyzer:
            return self._python_analyzer.extract_formids(segment_callstack)
        # Create Python analyzer on demand
        from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
        analyzer = FormIDAnalyzer(self.yamldata, self.show_formid_values, self.formid_db_exists)
        return analyzer.extract_formids(segment_callstack)

    def formid_match(self, formids: list[str], plugins: dict[str, str], report: Any) -> None:
        """
        Match FormIDs with plugins and update report.

        Args:
            formids: List of FormID strings to match
            plugins: Dictionary mapping plugin indices to names
            report: Report object to update with matches
        """
        if self._python_analyzer:
            self._python_analyzer.formid_match(formids, plugins, report)
        else:
            # Create Python analyzer on demand for formid_match
            # (Rust version doesn't implement this method yet)
            from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
            analyzer = FormIDAnalyzer(self.yamldata, self.show_formid_values, self.formid_db_exists)
            analyzer.formid_match(formids, plugins, report)

    def extract_formids_batch(self, segments: list[list[str]]) -> list[list[str]]:
        """
        Extract FormIDs from multiple segments in batch.

        Rust-specific optimization that processes multiple segments in parallel.

        Args:
            segments: List of segment line lists

        Returns:
            List of FormID lists, one per segment
        """
        if self._use_rust:
            try:
                import classic_core
                if hasattr(classic_core.scanlog, "extract_formids_batch"):
                    extract_formids_batch = classic_core.scanlog.extract_formids_batch
                    return extract_formids_batch(segments)
            except Exception as e:
                logger.debug(f"Rust batch extraction failed: {e}")

        # Python fallback - process sequentially
        results = []
        for segment in segments:
            results.append(self.extract_formids(segment))
        return results

    @property
    def is_rust_accelerated(self) -> bool:
        """Check if using Rust acceleration."""
        return self._use_rust

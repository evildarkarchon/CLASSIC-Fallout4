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

Async/Sync Behavior:
    All methods in FormIDAnalyzer are SYNCHRONOUS (blocking):
    - extract_formids() - Blocks while extracting FormIDs with Rust
    - formid_match() - Blocks while matching FormIDs against database
    - extract_formids_batch() - Blocks with parallel batch processing

    These methods call synchronous Rust functions. Use them directly in sync contexts.

AsyncBridge Usage (GUI Applications Only):
    For Qt GUI applications, wrap with AsyncBridge:

    ```python
    from ClassicLib.AsyncBridge import AsyncBridge
    from ClassicLib.rust.formid_rust import FormIDAnalyzer

    analyzer = FormIDAnalyzer(yamldata, show_formid_values, formid_db_exists)
    bridge = AsyncBridge.get_instance()

    # Wrap blocking analyzer calls
    formids = bridge.run_async(lambda: analyzer.extract_formids(segment_callstack))
    ```

CLI Usage:
    For CLI applications, use directly without AsyncBridge:

    ```python
    from ClassicLib.rust.formid_rust import FormIDAnalyzer

    analyzer = FormIDAnalyzer(yamldata, show_formid_values, formid_db_exists)
    formids = analyzer.extract_formids(segment_callstack)
    analyzer.formid_match(formids, plugins, report)
    ```
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.detector import detect_component
from ClassicLib.integration.exceptions import RustDatabaseError, RustError, RustParseError

# Detect Rust-specific exception types
_, _rust_scanlog_error = detect_component("classic_scanlog", "RustScanLogError")
_, _rust_parse_error = detect_component("classic_scanlog", "RustParseError")
_, _rust_db_error = detect_component("classic_database", "RustDatabaseError")


def _get_rust_exception_types() -> tuple[tuple[type[BaseException], ...], tuple[type[BaseException], ...], tuple[type[BaseException], ...]]:
    """Get tuple of Rust exception types to catch.

    Returns:
        A tuple containing three tuples of exception types:
            - ParseError types (RustParseError and module-specific parse errors)
            - DatabaseError types (RustDatabaseError and module-specific DB errors)
            - Generic RustError types (RustError and module-specific scan log errors)
    """
    parse_errors: tuple[type[BaseException], ...] = (RustParseError,)
    db_errors: tuple[type[BaseException], ...] = (RustDatabaseError,)
    rust_errors: tuple[type[BaseException], ...] = (RustError,)

    # Add module-specific exceptions if available
    if _rust_parse_error:
        parse_errors = (RustParseError, _rust_parse_error)
    if _rust_db_error:
        db_errors = (RustDatabaseError, _rust_db_error)
    if _rust_scanlog_error:
        rust_errors = (RustError, _rust_scanlog_error)

    return parse_errors, db_errors, rust_errors


# Get exception type tuples at module level for use in exception handlers
parse_errors: tuple[type[BaseException], ...]
db_errors: tuple[type[BaseException], ...]
rust_errors: tuple[type[BaseException], ...]
parse_errors, db_errors, rust_errors = _get_rust_exception_types()

if TYPE_CHECKING:
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class FormIDAnalyzer:
    """
    Wrapper for Rust FormIDAnalyzer that provides Python-compatible API.

    Provides high-performance FormID extraction and analysis when Rust is available.
    Achieves 50x performance improvement over pure Python implementation.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo, show_formid_values: bool, formid_db_exists: bool) -> None:
        """
        Initializes a form ID analyzer with a preference for optimized Rust implementations and a fallback
        to a Python implementation. This class attempts to utilize Rust-based analyzers if available,
        providing enhanced performance and optimizations.

        Args:
            yamldata: An instance of ClassicScanLogsInfo containing essential scan log data.
            show_formid_values: A boolean indicating whether form ID values should be displayed.
            formid_db_exists: A boolean specifying if the FormID database already exists.
        """
        self._rust_analyzer = None
        self._rust_core_analyzer = None
        self._use_rust = False
        self._use_rust_core = False
        self._python_analyzer = None
        self._plugin_cache_key = None

        # Store configuration
        self.yamldata = yamldata
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists

        try:
            import classic_scanlog

            # Try to use FormIDAnalyzerCore (optimized version) first
            if hasattr(classic_scanlog, "FormIDAnalyzerCore"):
                FormIDAnalyzerCore = classic_scanlog.FormIDAnalyzerCore

                # Extract required data from yamldata
                crashgen_name = getattr(yamldata, "crashgen_name", "")
                important_mods = getattr(yamldata, "problematic_plugins", {})
                mods_single = getattr(yamldata, "mods_single", {})
                mods_double = getattr(yamldata, "mods_double", {})

                self._rust_core_analyzer = FormIDAnalyzerCore(show_formid_values, crashgen_name, important_mods, mods_single, mods_double)
                self._use_rust_core = True
                logger.debug("🚀 FormIDAnalyzer: Using RUST FormIDAnalyzerCore (zero-copy optimizations)")
            elif hasattr(classic_scanlog, "FormIDAnalyzer"):
                # Fallback to simple FormIDAnalyzer
                FormIDAnalyzerImpl = classic_scanlog.FormIDAnalyzer
                self._rust_analyzer = FormIDAnalyzerImpl()
                self._use_rust = True
                logger.debug("🚀 FormIDAnalyzer: Using RUST FormIDAnalyzer (50x faster)")
            else:
                logger.debug("⚠️  FormIDAnalyzer: FormIDAnalyzer not found in classic_scanlog")
        except rust_errors as e:
            logger.error(f"❌ Rust error initializing FormIDAnalyzer: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Rust FormIDAnalyzer: {e}")

        # Only create Python analyzer if Rust truly unavailable
        if not self._use_rust and not self._use_rust_core:
            logger.debug("⚠️  FormIDAnalyzer: Falling back to Python implementation")
            from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer

            self._python_analyzer = FormIDAnalyzer(yamldata, show_formid_values, formid_db_exists)

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """
        Extracts a list of Form IDs from the given segment call stack using multiple possible analyzers.

        The method attempts to use a Rust-based zero-copy extraction method if available. If that fails,
        or if Rust analyzers are not enabled, it falls back to a Python-based Form ID analyzer.

        Args:
            segment_callstack (list[str]): The call stack segment from which to extract Form IDs.

        Returns:
            list[str]: A list of extracted Form IDs found within the provided call stack segment.
        """
        if self._use_rust_core and self._rust_core_analyzer:
            try:
                # Use zero-copy method if available
                if hasattr(self._rust_core_analyzer, "extract_formids_nocopy"):
                    # Pass Python list directly for zero-copy operation
                    return self._rust_core_analyzer.extract_formids_nocopy(segment_callstack)
                # Fallback to standard method
                return self._rust_core_analyzer.extract_formids(segment_callstack)
            except parse_errors as e:
                logger.warning(f"Rust parse error in FormIDAnalyzerCore extraction: {e}")
            except rust_errors as e:
                logger.warning(f"Rust FormIDAnalyzerCore extraction failed: {e}")
            except Exception as e:
                logger.warning(f"FormIDAnalyzerCore extraction error: {e}")
        elif self._use_rust and self._rust_analyzer:
            try:
                # Use simple Rust analyzer
                import classic_scanlog

                if hasattr(classic_scanlog, "extract_formids_batch"):
                    extract_formids_batch = classic_scanlog.extract_formids_batch
                    formids = extract_formids_batch([segment_callstack])
                    # extract_formids_batch returns a list of lists, get the first one
                    return formids[0] if formids else []
                # Try direct method if available
                return self._rust_analyzer.extract_formids(segment_callstack)
            except parse_errors as e:
                logger.warning(f"Rust parse error in FormID extraction: {e}")
            except rust_errors as e:
                logger.warning(f"Rust FormID extraction failed: {e}")
            except Exception as e:
                logger.warning(f"FormID extraction error: {e}")

        # Use Python fallback
        if self._python_analyzer:
            return self._python_analyzer.extract_formids(segment_callstack)
        # Create Python analyzer on demand
        from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer

        analyzer = FormIDAnalyzer(self.yamldata, self.show_formid_values, self.formid_db_exists)
        return analyzer.extract_formids(segment_callstack)

    def formid_match(self, formids: list[str], plugins: dict[str, str], report: Any) -> None:
        """
        Matches form IDs with given plugins and generates a structured report, relying on either Rust
        or Python-based analyzers depending on the configuration.

        This method utilizes a Rust-based core for optimized processing when available, falling
        back to the Python-based analyzer if necessary. Plugin configurations are cached for efficiency
        in Rust-based processing. The resulting matches are converted into report fragments to be appended
        to the provided report.

        Args:
            formids (list[str]): A list of form IDs to be analyzed and matched.
            plugins (dict[str, str]): A dictionary mapping plugin names to their respective paths or
                details.
            report (Any): A writable report object where the analysis results will be stored.

        """
        if self._use_rust_core and self._rust_core_analyzer:
            try:
                # Cache plugins once per session for efficiency
                import hashlib

                cache_key = hashlib.md5(str(sorted(plugins.items())).encode()).hexdigest()

                if cache_key != self._plugin_cache_key and hasattr(self._rust_core_analyzer, "cache_plugins"):
                    # Cache the plugins on Rust side
                    self._rust_core_analyzer.cache_plugins(cache_key, plugins)
                    self._plugin_cache_key = cache_key
                    logger.debug("🚀 Cached plugin mappings in Rust (avoids repeated conversions)")

                # Use optimized formid_match if available
                if hasattr(self._rust_core_analyzer, "process_formids_cached"):
                    # Use cached version - returns a list of formatted strings
                    result_lines = self._rust_core_analyzer.process_formids_cached(formids, cache_key)
                    # Create ReportFragment from the result lines
                    if result_lines:
                        from ClassicLib.ScanLog.fragments import ReportFragment

                        fragment = ReportFragment.from_lines(result_lines)
                        report.add_fragment(fragment)
                else:
                    # Use regular formid_match
                    self._rust_core_analyzer.formid_match(formids, plugins, report)
            except db_errors as e:
                logger.warning(f"Rust database error in formid_match: {e}, using Python fallback")
            except rust_errors as e:
                logger.warning(f"Rust formid_match failed: {e}, using Python fallback")
            except Exception as e:
                logger.warning(f"formid_match error: {e}, using Python fallback")
            else:
                return

        if self._python_analyzer:
            fragment = self._python_analyzer.formid_match(formids, plugins)
            report.add_fragment(fragment)
        else:
            # Create Python analyzer on demand for formid_match
            from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer

            analyzer = FormIDAnalyzer(self.yamldata, self.show_formid_values, self.formid_db_exists)
            fragment = analyzer.formid_match(formids, plugins)
            report.add_fragment(fragment)

    def extract_formids_batch(self, segments: list[list[str]]) -> list[list[str]]:
        """
        Extracts form IDs in batches from the provided list of segments.

        This method attempts to use a Rust-based implementation for batch extraction
        of form IDs if available. If the Rust module is unavailable or fails to process
        the data, a Python fallback mechanism is used, processing each segment sequentially.

        Args:
            segments (list[list[str]]): A list of lists where each inner list contains
                segments to be processed for extracting form IDs.

        Returns:
            list[list[str]]: A list of lists where each inner list contains extracted
                form IDs corresponding to the input segments.
        """
        if self._use_rust:
            try:
                import classic_scanlog

                if hasattr(classic_scanlog, "extract_formids_batch"):
                    extract_formids_batch = classic_scanlog.extract_formids_batch
                    return extract_formids_batch(segments)
            except parse_errors as e:
                logger.debug(f"Rust parse error in batch extraction: {e}")
            except rust_errors as e:
                logger.debug(f"Rust batch extraction failed: {e}")
            except Exception as e:
                logger.debug(f"Batch extraction error: {e}")

        # Python fallback - process sequentially
        return [self.extract_formids(segment) for segment in segments]

    @property
    def is_rust_accelerated(self) -> bool:
        """
        Checks if Rust acceleration is enabled.

        This property determines whether Rust acceleration is enabled based on the
        values of the underlying private attributes.

        Returns:
            bool: True if Rust acceleration is enabled, False otherwise.
        """
        return self._use_rust or self._use_rust_core

"""
Rust-accelerated PluginAnalyzer wrapper.

This module provides a drop-in replacement for the Python PluginAnalyzer that uses
the high-performance Rust implementation when available, providing 30x speedup
for plugin load order analysis.

Performance improvements with Rust:
- 30x faster plugin load order parsing
- Efficient hex index conversion
- Optimized string processing
- Memory-efficient plugin tracking
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.detector import detect_component
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
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class RustPluginAnalyzer:
    """
    Wrapper for Rust PluginAnalyzer that provides Python-compatible API.

    Provides high-performance plugin analysis when Rust is available.
    Achieves 30x performance improvement over pure Python implementation.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo) -> None:
        """
        Initializes the analyzer by deciding whether to use the Rust implementation of the
        PluginAnalyzer from the classic_scanlog module or a fallback Python implementation.

        This constructor tries to locate and utilize the Rust-based PluginAnalyzer if it is
        available in the classic_scanlog module. If the Rust implementation is successfully initialized,
        it is preferred as it offers significant performance advantages. If unavailable, the
        Python implementation of PluginAnalyzer is initialized as a fallback.

        Args:
            yamldata (ClassicScanLogsInfo): Contains configuration and parameters needed for
                initializing the analyzers, such as game version, crash generation name, and
                ignore plugin lists.
        """
        self._rust_analyzer = None
        self._use_rust = False
        self._python_analyzer = None
        self.yamldata = yamldata

        try:
            import classic_scanlog

            if hasattr(classic_scanlog, "PluginAnalyzer"):
                RustPluginAnalyzerImpl = classic_scanlog.PluginAnalyzer

                # Extract required parameters from yamldata
                game_ignore_plugins = getattr(yamldata, "game_ignore_plugins", [])
                ignore_list = getattr(yamldata, "ignore_list", [])
                crashgen_name = str(getattr(yamldata, "crashgen_name", ""))
                # Convert Version objects to strings for Rust compatibility
                game_version = str(getattr(yamldata, "game_version", ""))
                game_version_vr = str(getattr(yamldata, "game_version_vr", ""))
                game_version_new = str(getattr(yamldata, "game_version_new", ""))

                self._rust_analyzer = RustPluginAnalyzerImpl(
                    game_ignore_plugins, ignore_list, crashgen_name, game_version, game_version_vr, game_version_new
                )
                self._use_rust = True
                logger.debug("🚀 RustPluginAnalyzer: Using RUST implementation (30x faster)")
            else:
                logger.debug("⚠️  RustPluginAnalyzer: PluginAnalyzer not found in classic_scanlog")
        except rust_errors as e:
            logger.error(f"❌ Rust error initializing PluginAnalyzer: {e}")
        except (ImportError, AttributeError) as e:
            logger.error(f"❌ Failed to initialize Rust PluginAnalyzer: {e}")

        # Only create Python analyzer if Rust truly unavailable
        if not self._use_rust:
            logger.debug("⚠️  RustPluginAnalyzer: Falling back to Python implementation")
            from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer

            self._python_analyzer = PluginAnalyzer(yamldata)

    def loadorder_scan_log(
        self, segment_plugins: list[str], game_version: Any = None, version_current: Any = None
    ) -> tuple[dict[str, str], bool, bool]:
        """
        Scans the load order log from the provided plugins segment. The function processes
        the load order using either Rust or Python-based analyzers, depending on availability
        and configuration. It returns the processed plugins in a structured dictionary format
        along with flags that indicate whether plugin limits have been exceeded or plugin
        limit checks are disabled.

        Args:
            segment_plugins (list[str]): A list of plugin names to be scanned for load
                order processing.
            game_version (Any, optional): The version of the game for which the plugin
                limits need to be checked. Defaults to None.
            version_current (Any, optional): The current version information to perform
                compatibility checks. Defaults to None.

        Returns:
            tuple[dict[str, str], bool, bool]: A tuple containing:
                - A dictionary mapping plugin names to hexadecimal index strings.
                - A boolean indicating if the plugin limit was triggered.
                - A boolean indicating if the plugin limit checks are disabled.
        """
        if self._use_rust and self._rust_analyzer:
            try:
                # Rust now returns (HashMap, bool, bool) with correct structure
                # Convert Version objects to strings if needed
                game_ver_str = str(game_version) if game_version else None
                version_cur_str = str(version_current) if version_current else None

                plugins_dict, plugin_limit_triggered, limit_check_disabled = self._rust_analyzer.loadorder_scan_log(
                    segment_plugins, game_version=game_ver_str, version_current=version_cur_str
                )
            except parse_errors as e:
                logger.warning(f"Rust parse error in loadorder scan: {e}")
            except rust_errors as e:
                logger.warning(f"Rust loadorder scan failed: {e}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Rust loadorder scan error: {e}")
            else:
                return plugins_dict, plugin_limit_triggered, limit_check_disabled

        # Use Python fallback
        if self._python_analyzer:
            return self._python_analyzer.loadorder_scan_log(segment_plugins, game_version, version_current)
        from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer

        analyzer = PluginAnalyzer(self.yamldata)
        return analyzer.loadorder_scan_log(segment_plugins, game_version, version_current)

    def check_plugin_limit(self, segment_plugins: list[str], game_version: Any = None, version_current: Any = None) -> tuple[bool, bool]:
        """
        This function checks if the plugin count has exceeded the allowed limit for a specified configuration. It uses
        either a pre-configured analyzer or creates an instance of `PluginAnalyzer` to perform the verification.

        Args:
            segment_plugins (list[str]): A list of plugins to analyze.
            game_version (Any, optional): The version of the game. Defaults to None.
            version_current (Any, optional): The current plugin version. Defaults to None.

        Returns:
            tuple[bool, bool]: A tuple containing two boolean values. The first indicates whether the plugin limit
                was triggered, and the second indicates if the limit checks are disabled.
        """
        if self._use_rust and self._rust_analyzer:
            try:
                # Convert Version objects to strings for Rust compatibility
                game_ver_str = str(game_version) if game_version else ""
                version_cur_str = str(version_current) if version_current else ""

                # Call Rust implementation
                plugin_limit_triggered, limit_check_disabled = self._rust_analyzer.check_plugin_limit(
                    segment_plugins, game_ver_str, version_cur_str
                )
            except parse_errors as e:
                logger.warning(f"Rust parse error in check_plugin_limit: {e}")
            except rust_errors as e:
                logger.warning(f"Rust check_plugin_limit failed: {e}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Rust check_plugin_limit error: {e}")
            else:
                return plugin_limit_triggered, limit_check_disabled

        # Use Python fallback
        if self._python_analyzer:
            return self._python_analyzer.check_plugin_limit(segment_plugins, game_version, version_current)
        from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer

        analyzer = PluginAnalyzer(self.yamldata)
        return analyzer.check_plugin_limit(segment_plugins, game_version, version_current)

    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str]) -> Any:
        """
        Matches plugins found in crash call stack and generates a suspect report with counts.

        Args:
            segment_callstack_lower: Lowercase call stack lines
            crashlog_plugins_lower: Set of lowercase plugin names from crash log

        Returns:
            ReportFragment with plugin match results
        """
        from ClassicLib.ScanLog.fragments import ReportFragment

        if self._use_rust and self._rust_analyzer:
            try:
                # Rust returns list[str], convert to ReportFragment
                lines = self._rust_analyzer.plugin_match(segment_callstack_lower, crashlog_plugins_lower)
                return ReportFragment.from_lines(lines)
            except parse_errors as e:
                logger.warning(f"Rust parse error in plugin_match: {e}, falling back to Python")
            except rust_errors as e:
                logger.warning(f"Rust plugin_match failed: {e}, falling back to Python")
            except (TypeError, ValueError) as e:
                logger.warning(f"Rust plugin_match error: {e}, falling back to Python")

        # Python fallback
        if self._python_analyzer:
            return self._python_analyzer.plugin_match(segment_callstack_lower, crashlog_plugins_lower)

        from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer

        analyzer = PluginAnalyzer(self.yamldata)
        return analyzer.plugin_match(segment_callstack_lower, crashlog_plugins_lower)

    def filter_ignored_plugins(self, crashlog_plugins: dict[str, str]) -> dict[str, str]:
        """
        Filters out ignored plugins from crash log plugin list using configured ignore lists.

        Args:
            crashlog_plugins: HashMap of plugin names to load order IDs

        Returns:
            HashMap with ignored plugins removed
        """
        if self._use_rust and self._rust_analyzer:
            try:
                return self._rust_analyzer.filter_ignored_plugins(crashlog_plugins)
            except parse_errors as e:
                logger.warning(f"Rust parse error in filter_ignored_plugins: {e}, falling back to Python")
            except rust_errors as e:
                logger.warning(f"Rust filter_ignored_plugins failed: {e}, falling back to Python")
            except (TypeError, ValueError) as e:
                logger.warning(f"Rust filter_ignored_plugins error: {e}, falling back to Python")

        # Python fallback
        if self._python_analyzer:
            return self._python_analyzer.filter_ignored_plugins(crashlog_plugins)

        from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer

        analyzer = PluginAnalyzer(self.yamldata)
        return analyzer.filter_ignored_plugins(crashlog_plugins)

    @staticmethod
    def parse_plugin_line(line: str) -> tuple[str, str] | None:
        """
        Parses a single line of plugin data and extracts relevant information.

        This function parses a line containing plugin information, extracting a
        hexadecimal ID and associated data from the input line if possible.

        Note: This method uses Python regex parsing as the Rust implementation
        does not provide a corresponding method (it's a simple operation).

        Args:
            line (str): The input line containing plugin data to be parsed.

        Returns:
            tuple[str, str] | None: A tuple containing the extracted hexadecimal ID
            (as an uppercase string) and the associated data string if parsing is
            successful. Returns None if the line does not match the expected format.
        """
        # Python implementation (Rust doesn't provide parse_plugin_line)
        import re

        match = re.match(r"\s*\[([0-9A-Fa-f]+)\]\s+(.+)", line)
        if match:
            return match.group(1).upper(), match.group(2).strip()
        return None

    @property
    def is_rust_accelerated(self) -> bool:
        """
        Checks if Rust acceleration is enabled.

        This property returns a boolean value indicating whether the Rust
        acceleration feature is currently in use.

        Returns:
            bool: True if Rust acceleration is enabled, False otherwise.
        """
        return self._use_rust

"""Rust-accelerated PluginAnalyzer wrapper.

This module provides a drop-in replacement for the Python PluginAnalyzer that uses
the high-performance Rust implementation, providing 30x speedup for plugin load
order analysis. Rust is required.

Performance improvements with Rust:
- 30x faster plugin load order parsing
- Efficient hex index conversion
- Optimized string processing
- Memory-efficient plugin tracking
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


class RustPluginAnalyzer:
    """Wrapper for Rust PluginAnalyzer. Rust is required.

    Provides high-performance plugin analysis using the Rust implementation.
    Achieves 30x performance improvement over pure Python implementation.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo) -> None:
        """Initialize the Rust PluginAnalyzer. Raises RuntimeError if unavailable.

        Args:
            yamldata: Contains configuration and parameters needed for
                initializing the analyzer, such as game version, crash generation name, and
                ignore plugin lists.

        Raises:
            RuntimeError: If Rust PluginAnalyzer is not available.

        """
        self.yamldata = yamldata

        try:
            import classic_scanlog

            if not hasattr(classic_scanlog, "PluginAnalyzer"):
                msg = "PluginAnalyzer not found in classic_scanlog module. Reinstall CLASSIC."
                raise RuntimeError(msg)

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
            logger.debug("RustPluginAnalyzer: Using RUST implementation (30x faster)")
        except RuntimeError:
            raise
        except (ImportError, AttributeError) as e:
            msg = f"Required Rust module for PluginAnalyzer not available: {e}. Reinstall CLASSIC."
            raise RuntimeError(msg) from e
        except rust_errors as e:
            msg = f"Rust error initializing PluginAnalyzer: {e}. Reinstall CLASSIC."
            raise RuntimeError(msg) from e

    def loadorder_scan_log(
        self, segment_plugins: list[str], game_version: Any = None, version_current: Any = None
    ) -> tuple[dict[str, str], bool, bool]:
        """Scan the load order log from the provided plugins segment.

        Args:
            segment_plugins: A list of plugin names to be scanned for load
                order processing.
            game_version: The version of the game for which the plugin
                limits need to be checked. Defaults to None.
            version_current: The current version information to perform
                compatibility checks. Defaults to None.

        Returns:
            A tuple containing:
                - A dictionary mapping plugin names to hexadecimal index strings.
                - A boolean indicating if the plugin limit was triggered.
                - A boolean indicating if the plugin limit checks are disabled.

        Raises:
            RuntimeError: If Rust loadorder scan fails.

        """
        # Convert Version objects to strings if needed
        game_ver_str = str(game_version) if game_version else None
        version_cur_str = str(version_current) if version_current else None

        try:
            plugins_dict, plugin_limit_triggered, limit_check_disabled = self._rust_analyzer.loadorder_scan_log(
                segment_plugins, game_version=game_ver_str, version_current=version_cur_str
            )
        except (*parse_errors, *rust_errors, TypeError, ValueError) as e:
            msg = f"Rust loadorder scan failed: {e}"
            raise RuntimeError(msg) from e

        return plugins_dict, plugin_limit_triggered, limit_check_disabled

    def check_plugin_limit(self, segment_plugins: list[str], game_version: Any = None, version_current: Any = None) -> tuple[bool, bool]:
        """Check if the plugin count has exceeded the allowed limit.

        Args:
            segment_plugins: A list of plugins to analyze.
            game_version: The version of the game. Defaults to None.
            version_current: The current plugin version. Defaults to None.

        Returns:
            A tuple containing two boolean values. The first indicates whether the plugin limit
                was triggered, and the second indicates if the limit checks are disabled.

        Raises:
            RuntimeError: If Rust check_plugin_limit fails.

        """
        # Convert Version objects to strings for Rust compatibility
        game_ver_str = str(game_version) if game_version else ""
        version_cur_str = str(version_current) if version_current else ""

        try:
            plugin_limit_triggered, limit_check_disabled = self._rust_analyzer.check_plugin_limit(
                segment_plugins, game_ver_str, version_cur_str
            )
        except (*parse_errors, *rust_errors, TypeError, ValueError) as e:
            msg = f"Rust check_plugin_limit failed: {e}"
            raise RuntimeError(msg) from e

        return plugin_limit_triggered, limit_check_disabled

    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str]) -> Any:
        """Match plugins found in crash call stack and generates a suspect report with counts.

        Args:
            segment_callstack_lower: Lowercase call stack lines
            crashlog_plugins_lower: Set of lowercase plugin names from crash log

        Returns:
            ReportFragment with plugin match results

        Raises:
            RuntimeError: If Rust plugin_match fails.

        """
        from ClassicLib.scanning.logs.reporting import ReportFragment

        try:
            # Rust returns list[str], convert to ReportFragment
            lines = self._rust_analyzer.plugin_match(segment_callstack_lower, crashlog_plugins_lower)
            return ReportFragment.from_lines(lines)
        except (*parse_errors, *rust_errors, TypeError, ValueError) as e:
            msg = f"Rust plugin_match failed: {e}"
            raise RuntimeError(msg) from e

    def filter_ignored_plugins(self, crashlog_plugins: dict[str, str]) -> dict[str, str]:
        """Filter out ignored plugins from crash log plugin list using configured ignore lists.

        Args:
            crashlog_plugins: HashMap of plugin names to load order IDs

        Returns:
            HashMap with ignored plugins removed

        Raises:
            RuntimeError: If Rust filter_ignored_plugins fails.

        """
        try:
            return self._rust_analyzer.filter_ignored_plugins(crashlog_plugins)
        except (*parse_errors, *rust_errors, TypeError, ValueError) as e:
            msg = f"Rust filter_ignored_plugins failed: {e}"
            raise RuntimeError(msg) from e

    @staticmethod
    def parse_plugin_line(line: str) -> tuple[str, str] | None:
        """Parse a single line of plugin data and extracts relevant information.

        This function parses a line containing plugin information, extracting a
        hexadecimal ID and associated data from the input line if possible.

        Note: This method uses Python regex parsing as the Rust implementation
        does not provide a corresponding method (it's a simple operation).

        Args:
            line: The input line containing plugin data to be parsed.

        Returns:
            A tuple containing the extracted hexadecimal ID
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
        """Whether Rust acceleration is active.

        Returns:
            True always, since Rust is required.

        """
        return True

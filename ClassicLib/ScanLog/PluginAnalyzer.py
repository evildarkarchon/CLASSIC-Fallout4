"""
Plugin analyzer module for CLASSIC.

This module handles all plugin-related operations including:
- Loading plugins from loadorder.txt or crash logs
- Matching plugins in call stacks
- Filtering ignored plugins
- Managing plugin status classification
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import regex as re
from packaging.version import Version

from ClassicLib.ScanLog.ReportFragment import ReportFragment
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class PluginAnalyzer:
    """Handles plugin analysis and matching operations."""

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initialize the plugin analyzer.

        Args:
            yamldata: Configuration data containing plugin-related settings
        """
        self.yamldata: ClassicScanLogsInfo = yamldata
        self.pluginsearch: re.Pattern[str] = re.compile(
            r"\s*\[(FE:([0-9A-F]{3})|[0-9A-F]{2})\]\s*(.+?(?:\.es[pml])+)",
            flags=re.IGNORECASE,
        )
        self.lower_plugins_ignore: set[str] = {ignore.lower() for ignore in yamldata.game_ignore_plugins}
        self.ignore_plugins_list: set[str] = {item.lower() for item in yamldata.ignore_list} if yamldata.ignore_list else set()

    @staticmethod
    def loadorder_scan_loadorder_txt() -> tuple[dict[str, str], bool, ReportFragment]:
        """
        Loads and processes the "loadorder.txt" file from the main "CLASSIC" folder, if available.

        Returns:
            Tuple of (dict of plugin names to origin markers, bool indicating if plugins loaded, ReportFragment).
        """
        lines = []
        loadorder_origin = "LO"  # Origin marker for plugins from loadorder.txt
        loadorder_path = Path("loadorder.txt")

        lines.append("* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n")
        lines.append("CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n")
        lines.append("[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n")

        loadorder_plugins: dict = {}

        try:
            with loadorder_path.open(encoding="utf-8", errors="ignore") as loadorder_file:
                loadorder_data: list[str] = loadorder_file.readlines()

            # Skip the header line (first line) of the loadorder.txt file
            if len(loadorder_data) > 1:
                for plugin_entry in loadorder_data[1:]:
                    plugin_entry: str = plugin_entry.strip()
                    if plugin_entry and plugin_entry not in loadorder_plugins:
                        loadorder_plugins[plugin_entry] = loadorder_origin
        except OSError as e:
            # Log file access error but continue execution
            lines.append(f"Error reading loadorder.txt: {e!s}")

        # Check if any plugins were loaded
        plugins_loaded = bool(loadorder_plugins)

        return loadorder_plugins, plugins_loaded, ReportFragment.from_lines(lines)

    def loadorder_scan_log(
        self, segment_plugins: list[str], game_version: Version, version_current: Version
    ) -> tuple[dict[str, str], bool, bool]:
        """
        Scans and processes the plugin load order from the provided segment plugins.

        This function analyzes a list of segment plugins to extract their details and
        builds a mapping of plugin names to their identifiers or classification. It
        also identifies if a plugin limit was triggered based on certain marker patterns
        and evaluates version-related conditions regarding the game's behavior with
        specific plugin configurations.

        Arguments:
            segment_plugins: A list of strings representing the loaded plugins, where
                each string includes plugin identifiers or related markers.
            game_version: The current detected version of the game.
            version_current: The current software version of the application or handler.

        Returns:
            A tuple containing:
                - A dictionary mapping plugin names to their corresponding identifiers
                  or classifications.
                - A boolean flag indicating if a plugin limit marker was detected
                  and triggered specific processing logic.
                - A boolean flag indicating if specific plugin limit-related checks
                  were disabled under the given conditions.
        """
        # Early return for empty input
        if not segment_plugins:
            return {}, False, False

        # Constants for plugin status
        plugin_status_dll = "DLL"
        plugin_status_unknown = "???"
        plugin_limit_marker = "[FF]"

        # Determine game version characteristics
        is_original_game = game_version in (self.yamldata.game_version, self.yamldata.game_version_vr)
        is_new_game_crashgen_pre_137 = game_version >= self.yamldata.game_version_new and version_current < Version("1.37.0")

        # Initialize return values
        plugin_map: dict = {}
        plugin_limit_triggered = False
        limit_check_disabled = False

        # Process each plugin entry
        for entry in segment_plugins:
            # Check for plugin limit markers
            if plugin_limit_marker in entry:
                if is_original_game:
                    plugin_limit_triggered = True
                elif is_new_game_crashgen_pre_137:
                    limit_check_disabled = True

            # Extract plugin information using regex
            plugin_match: re.Match[str] | None = self.pluginsearch.match(entry, concurrent=True)
            if plugin_match is None:
                continue

            # Extract plugin details
            plugin_id: str | Any = plugin_match.group(1)
            plugin_name: str | Any = plugin_match.group(3)

            # Skip if plugin name is empty or already processed
            if not plugin_name or plugin_name in plugin_map:
                continue

            # Classify the plugin
            if plugin_id is not None:
                plugin_map[plugin_name] = plugin_id.replace(":", "")
            elif "dll" in plugin_name.lower():
                plugin_map[plugin_name] = plugin_status_dll
            else:
                plugin_map[plugin_name] = plugin_status_unknown

        return plugin_map, plugin_limit_triggered, limit_check_disabled

    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str]) -> ReportFragment:
        """
        Analyzes crash logs for relevant plugin references.

        Args:
            segment_callstack_lower: A list of lowercased strings representing the crash stack.
            crashlog_plugins_lower: A set of lowercased plugin names from the crash log.

        Returns:
            ReportFragment containing plugin match results.
        """
        from collections import Counter

        lines = []

        # Pre-filter call stack lines that won't match
        relevant_lines: list[str] = [line for line in segment_callstack_lower if "modified by:" not in line]

        # Use Counter directly instead of list + Counter conversion
        plugins_matches: Counter[str] = Counter()

        # Optimize the matching algorithm
        for line in relevant_lines:
            for plugin in crashlog_plugins_lower:
                # Skip plugins that are in the ignore list
                if plugin in self.lower_plugins_ignore:
                    continue

                if plugin in line:
                    plugins_matches[plugin] += 1

        if plugins_matches:
            lines.append("The following PLUGINS were found in the CRASH STACK:\n")
            # Sort by count (descending) then by name for consistent output
            for plugin, count in sorted(plugins_matches.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"- {plugin} | {count}\n")
            lines.append("\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n")
            lines.append(
                f"These Plugins were caught by {self.yamldata.crashgen_name} and some of them might be responsible for this crash.\n"
            )
            lines.append(
                "You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n"
            )
        else:
            lines.append("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n")

        return ReportFragment.from_lines(lines)

    def filter_ignored_plugins(self, crashlog_plugins: dict[str, str]) -> dict[str, str]:
        """
        Filters out ignored plugins from a dictionary of crash log plugins.

        This method removes plugins listed in the `ignore_plugins_list` from the
        provided `crashlog_plugins` dictionary. It performs a case-insensitive
        comparison of plugin names, ensuring that ignored plugins are removed
        regardless of their case.

        Parameters:
            crashlog_plugins: dict[str, str]
                The dictionary containing plugin names as keys and their associated
                values. The dictionary may include plugins that need to be filtered
                out based on the `ignore_plugins_list`.

        Returns:
            dict[str, str]: A dictionary of crash log plugins with the ignored plugins
            removed.
        """
        if not self.ignore_plugins_list:
            return crashlog_plugins

        # Create lowercase version for comparison
        crashlog_plugins_lower: dict[str, str] = {k.lower(): k for k in crashlog_plugins}

        # Remove ignored plugins
        for signal in self.ignore_plugins_list:
            if signal in crashlog_plugins_lower:
                original_key: str = crashlog_plugins_lower[signal]
                del crashlog_plugins[original_key]

        return crashlog_plugins

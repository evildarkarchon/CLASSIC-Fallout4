"""
Pure Python implementation of plugin analysis.

This module provides the fallback Python implementation for plugin-related
operations when Rust acceleration is not available. It handles loading plugins,
matching them in call stacks, and filtering operations.
"""

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packaging.version import Version

    from ClassicLib.ScanLog.ReportFragment import ReportFragment
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class PythonPluginAnalyzer:
    """
    Pure Python implementation for analyzing plugins and their crash log relationships.

    This class provides the fallback implementation for plugin-related operations,
    including identifying plugin references in crash logs, parsing plugin load order files,
    and implementing filtering logic to exclude ignored plugins.

    Attributes:
        yamldata: Configuration object containing plugin settings and game version details.
        pluginsearch: Regular expression to match plugin identifiers and names.
        lower_plugins_ignore: Set of ignored plugins in lowercase for case-insensitive comparisons.
        ignore_plugins_list: Set of plugins specifically excluded from analysis.
    """

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initializes an instance to handle scanning and processing of plugins information
        from the provided YAML data.

        Args:
            yamldata (ClassicScanLogsInfo): An object containing YAML configuration
                data. This data includes information about plugins such as game ignored
                plugins (`game_ignore_plugins`) and an optional ignore list
                (`ignore_list`).
        """
        self.yamldata = yamldata
        # noinspection RegExpRedundantEscape
        self.pluginsearch = re.compile(
            r"\s*\[(FE:([0-9A-F]{3})|[0-9A-F]{2})\]\s*(.+?(?:\.es[pml])+)",
            flags=re.IGNORECASE,
        )
        self.lower_plugins_ignore = {ignore.lower() for ignore in yamldata.game_ignore_plugins}
        self.ignore_plugins_list = {item.lower() for item in yamldata.ignore_list} if yamldata.ignore_list else set()

    @staticmethod
    def loadorder_scan_loadorder_txt() -> tuple[dict[str, str], bool, "ReportFragment"]:
        """
        Parses the loadorder.txt file to detect and load plugin data.

        This method attempts to read the loadorder.txt file and extract a list of plugins.
        Detected plugins are marked with their origin. This feature enables tracking
        plugins only from the specified file and ignoring others in crash logs.

        Returns:
            tuple containing:
                - A dictionary mapping plugin names to their origin.
                - A boolean indicating if any plugins were successfully loaded.
                - A ReportFragment object containing logs of the operation.
        """
        from ClassicLib.ScanLog.ReportFragment import ReportFragment

        lines = []
        loadorder_origin = "LO"  # Origin marker for plugins from loadorder.txt
        loadorder_path = Path("loadorder.txt")

        lines.extend((
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n",
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n",
        ))

        loadorder_plugins = {}

        try:
            with loadorder_path.open(encoding="utf-8", errors="ignore") as loadorder_file:
                loadorder_data = loadorder_file.readlines()

            # Skip the header line (first line) of the loadorder.txt file
            if len(loadorder_data) > 1:
                for plugin_entry in loadorder_data[1:]:
                    plugin_entry = plugin_entry.strip()
                    if plugin_entry and plugin_entry not in loadorder_plugins:
                        loadorder_plugins[plugin_entry] = loadorder_origin
        except OSError as e:
            # Log file access error but continue execution
            lines.append(f"Error reading loadorder.txt: {e!s}")

        # Check if any plugins were loaded
        plugins_loaded = bool(loadorder_plugins)

        return loadorder_plugins, plugins_loaded, ReportFragment.from_lines(lines)

    def check_plugin_limit(
        self, segment_plugins: list[str], game_version: "Version | None" = None, version_current: "Version | None" = None
    ) -> tuple[bool, bool]:
        """
        Checks if a plugin limit has been triggered or if the limit check is disabled.

        This function analyzes a list of segment plugins to determine if any plugin contains
        specific markers indicating a limit. It adjusts the check behavior based on the
        provided game version and current version. The results indicate whether a limit
        has been triggered and whether the limit check has been disabled.

        Args:
            segment_plugins (list[str]): The list of plugins to be checked for limit markers.
            game_version (Version | None): The game version being analyzed. If None, the limit
                check is considered not triggered.
            version_current (Version | None): The currently running version. If None, the
                limit check is considered not triggered.

        Returns:
            tuple[bool, bool]: A tuple where the first value indicates if the plugin limit is
                triggered, and the second value indicates if the limit check is disabled.
        """
        if not game_version or not version_current:
            return False, False

        from packaging.version import Version

        plugin_limit_marker = "[FF]"
        plugin_limit_triggered = False
        limit_check_disabled = False

        # Determine game version characteristics
        is_original_game = game_version in {self.yamldata.game_version, self.yamldata.game_version_vr}
        is_new_game_crashgen_pre_137 = game_version >= self.yamldata.game_version_new and version_current < Version("1.37.0")

        # Check for plugin limit markers
        for entry in segment_plugins:
            if plugin_limit_marker in entry:
                if is_original_game:
                    plugin_limit_triggered = True
                elif is_new_game_crashgen_pre_137:
                    limit_check_disabled = True
                break  # No need to check further once found

        return plugin_limit_triggered, limit_check_disabled

    def loadorder_scan_log(
        self, segment_plugins: list[str], game_version: "Version | None" = None, version_current: "Version | None" = None
    ) -> tuple[dict[str, str], bool, bool]:
        """
        Scans and processes the plugin load order from the provided segment plugins.

        This function analyzes a list of segment plugins to extract their details and
        builds a mapping of plugin names to their identifiers or classification.
        The core load order parsing is universal across all Bethesda games.

        Args:
            segment_plugins: A list of strings representing the loaded plugins.
            game_version: Optional game version for plugin limit detection.
            version_current: Optional crashgen version for plugin limit detection.

        Returns:
            A tuple containing:
                - A dictionary mapping plugin names to their hex indices or status.
                - A boolean flag for plugin limit triggered.
                - A boolean flag for limit check disabled.
        """
        # Early return for empty input
        if not segment_plugins:
            return {}, False, False

        # Constants for plugin status
        plugin_status_dll = "DLL"
        plugin_status_unknown = "???"

        # Initialize plugin map
        plugin_map = {}

        # Check plugin limits separately if version info provided
        plugin_limit_triggered = False
        limit_check_disabled = False
        if game_version and version_current:
            plugin_limit_triggered, limit_check_disabled = self.check_plugin_limit(
                segment_plugins, game_version, version_current
            )

        # Process each plugin entry (universal parsing logic)
        for entry in segment_plugins:
            # Extract plugin information using regex
            plugin_match = self.pluginsearch.match(entry)
            if plugin_match is None:
                continue

            # Extract plugin details
            plugin_id = plugin_match.group(1)
            plugin_name = plugin_match.group(3)

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

    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str]) -> "ReportFragment":
        """
        Matches plugins to call stack lines and generates a report fragment.

        This function analyzes the provided call stack segment and identifies plugins
        present within the crash log. It optimizes the matching process by pre-filtering
        irrelevant lines, skips ignored plugins, and counts occurrences of each matched plugin.

        Args:
            segment_callstack_lower: A list of call stack lines in lowercase to analyze.
            crashlog_plugins_lower: A set of plugin names in lowercase to match against.

        Returns:
            ReportFragment: A report fragment with the matched plugins and their occurrences.
        """
        from ClassicLib.ScanLog.ReportFragment import ReportFragment

        lines = []

        # Pre-filter call stack lines that won't match
        relevant_lines = [line for line in segment_callstack_lower if "modified by:" not in line]

        # Use Counter directly instead of list + Counter conversion
        plugins_matches = Counter()

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
            lines.extend((
                "\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n",
                f"These Plugins were caught by {self.yamldata.crashgen_name} and some of them might be responsible for this crash.\n",
                "You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n",
            ))
        else:
            lines.append("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n")

        return ReportFragment.from_lines(lines)

    def filter_ignored_plugins(self, crashlog_plugins: dict[str, str]) -> dict[str, str]:
        """
        Filters out plugins listed in the ignore list from the given crashlog plugins.

        This method takes a dictionary of crashlog plugins and removes any plugin whose name
        matches an entry in the ignore plugins list. Matching is case-insensitive.

        Args:
            crashlog_plugins: A dictionary of crashlog plugins with plugin names as keys.

        Returns:
            dict[str, str]: A dictionary of crashlog plugins with ignored plugins removed.
        """
        if not self.ignore_plugins_list:
            return crashlog_plugins

        # Create lowercase version for comparison
        crashlog_plugins_lower = {k.lower(): k for k in crashlog_plugins}

        # Remove ignored plugins
        for signal in self.ignore_plugins_list:
            if signal in crashlog_plugins_lower:
                original_key = crashlog_plugins_lower[signal]
                del crashlog_plugins[original_key]

        return crashlog_plugins

# Alias for compatibility
PluginAnalyzer = PythonPluginAnalyzer

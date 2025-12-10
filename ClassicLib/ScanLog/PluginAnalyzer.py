"""
Plugin analyzer module for CLASSIC.

This module handles all plugin-related operations including:
- Loading plugins from loadorder.txt or crash logs
- Matching plugins in call stacks
- Filtering ignored plugins
- Managing plugin status classification
"""

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import regex as re
from packaging.version import Version

from ClassicLib.rust.report_rust import ReportFragment
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

if TYPE_CHECKING:
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo


@lru_cache(maxsize=128)
def _compile_plugin_pattern(plugins: frozenset[str]) -> re.Pattern[str]:
    """
    Compiles a regex pattern from a frozenset of plugin names with caching.

    This function creates a single compiled regex pattern that matches any of the
    provided plugin names using word boundaries for accurate matching. Results
    are cached for performance when processing multiple crash logs with the same
    plugin set.

    Args:
        plugins: A frozenset of plugin names to match (must be hashable for caching).

    Returns:
        A compiled regex pattern for matching plugin names.
    """
    if not plugins:
        # Return a pattern that never matches
        return re.compile(r"(?!.*)", re.IGNORECASE)

    # Escape special regex characters and build alternation pattern
    # Use word boundaries to avoid partial matches
    patterns = [re.escape(plugin) for plugin in sorted(plugins)]
    return re.compile("|".join(patterns), re.IGNORECASE)


class PluginAnalyzer:
    """
    Analyzes plugins and manages their relationships with crash logs by processing plugin data,
    scanning load orders, detecting issues, and filtering ignored plugins.

    The class specializes in handling plugin-related operations, including identifying plugin
    references in crash logs, parsing plugin load order files, and implementing filtering logic
    to exclude ignored plugins. It utilizes regex patterns for efficient data extraction and
    provides feedback for troubleshooting plugin-related crashes.

    Attributes:
        yamldata (ClassicScanLogsInfo): Configuration object containing plugin settings
            and game version details.
        pluginsearch (re.Pattern[str]): Regular expression to match plugin identifiers and names.
        lower_plugins_ignore (set[str]): Set of ignored plugins in lowercase for case-insensitive
            comparisons.
        ignore_plugins_list (set[str]): Set of plugins specifically excluded from analysis, derived
            from the provided configuration.
    """

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initializes the object with provided YAML data and processes plugin-related
        information.

        Args:
            yamldata (ClassicScanLogsInfo): An object containing YAML configuration
                information, which includes game-related plugin ignore lists and
                other relevant data.

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
        Parses the `loadorder.txt` file in the main CLASSIC folder to detect and load plugin data.

        This method attempts to read the `loadorder.txt` file and extract a list of plugins.
        Detected plugins are marked with their origin. If the file cannot be accessed, an error
        message is logged. This feature enables CLASSIC to selectively track plugins only from
        the specified file and ignore others in crash logs. The parsing skips the header line of
        the file and processes the remaining entries.

        Returns:
            tuple[dict[str, str], bool, ReportFragment]: A tuple containing:
                - A dictionary mapping plugin names to their origin.
                - A boolean indicating if any plugins were successfully loaded.
                - A `ReportFragment` object containing logs of the operation.
        """
        lines = []
        loadorder_origin = "LO"  # Origin marker for plugins from loadorder.txt
        loadorder_path = Path("loadorder.txt")

        lines.extend((
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n",
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n",
        ))

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

    def check_plugin_limit(
        self, segment_plugins: list[str], game_version: Version | None = None, version_current: Version | None = None
    ) -> tuple[bool, bool]:
        """
        Checks if the plugin limit is triggered or if the limit check is disabled based on the provided
        segment_plugins and game version.

        This function evaluates specific conditions depending on the game version and version characteristics,
        and checks for a plugin limit marker within the provided list of segment_plugins. Depending on these
        conditions, it determines whether the plugin limit has been triggered or if the limit check is
        disabled.

        Args:
            segment_plugins: A list of strings, where each string represents a plugin entry. These may
                include specific markers used for checks.
            game_version: The Version object representing the game version, or None if not provided.
            version_current: The Version object representing the current version, or None if not provided.

        Returns:
            tuple[bool, bool]: A tuple where the first boolean indicates whether the plugin limit is triggered
                and the second boolean indicates whether the limit check is disabled.
        """
        if not game_version or not version_current:
            return False, False

        plugin_limit_marker = "[FF]"
        plugin_limit_triggered = False
        limit_check_disabled = False

        # Handle Version vs string comparison for game_version
        if isinstance(game_version, str):
            is_original_game = game_version in {str(self.yamldata.game_version), str(self.yamldata.game_version_vr)}
            # Simple string comparison for new game check (fallback)
            is_new_game_crashgen_pre_137 = (
                game_version >= str(self.yamldata.game_version_new) and isinstance(version_current, str) and version_current < "1.37.0"
            )
        else:
            is_original_game = str(game_version) in {str(self.yamldata.game_version), str(self.yamldata.game_version_vr)}
            # Use Version objects for inequality checks
            is_new_game_crashgen_pre_137 = (
                game_version >= self.yamldata.game_version_new
                and version_current < Version("1.37.0")
                and version_current >= Version("1.30.0")
            )

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
        self, segment_plugins: list[str], game_version: Version | None = None, version_current: Version | None = None
    ) -> tuple[dict[str, str], bool, bool]:
        """
        Scans and processes the plugin load order from the provided segment plugins.

        This function analyzes a list of segment plugins to extract their details and
        builds a mapping of plugin names to their identifiers or classification.

        Note: The core load order parsing is universal across all Bethesda games.
        The game_version and version_current parameters are optional and only used
        for plugin limit detection (backward compatibility).

        Arguments:
            segment_plugins: A list of strings representing the loaded plugins.
            game_version: Optional game version for plugin limit detection.
            version_current: Optional crashgen version for plugin limit detection.

        Returns:
            A tuple containing:
                - A dictionary mapping plugin names to their hex indices or status.
                - A boolean flag for plugin limit triggered (requires version params).
                - A boolean flag for limit check disabled (requires version params).
        """
        # Early return for empty input
        if not segment_plugins:
            return {}, False, False

        # Constants for plugin status
        plugin_status_dll = "DLL"
        plugin_status_unknown = "???"

        # Initialize plugin map
        plugin_map: dict = {}

        # Check plugin limits separately if version info provided
        plugin_limit_triggered = False
        limit_check_disabled = False
        if game_version and version_current:
            plugin_limit_triggered, limit_check_disabled = self.check_plugin_limit(segment_plugins, game_version, version_current)

        # Process each plugin entry (universal parsing logic)
        for entry in segment_plugins:
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
        Matches plugins to call stack lines and generates a report fragment.

        This function analyzes the provided call stack segment and identifies plugins
        present within the crash log. It optimizes the matching process by pre-filtering
        irrelevant lines, skips ignored plugins, and counts occurrences of each matched
        plugin. Finally, it generates a report fragment detailing the results of the
        analysis.

        Args:
            segment_callstack_lower (list[str]): A list of call stack lines in lowercase
                to analyze for plugin matches.
            crashlog_plugins_lower (set[str]): A set of plugin names in lowercase to
                match against the call stack lines.

        Returns:
            ReportFragment: A report fragment consolidating the matched plugins and
            their occurrences in the analyzed crash log segment.
        """
        from collections import Counter

        lines = []

        # Pre-filter call stack lines that won't match
        relevant_lines: list[str] = [line for line in segment_callstack_lower if "modified by:" not in line]

        # Filter out ignored plugins before pattern compilation
        plugins_to_match = frozenset(plugin for plugin in crashlog_plugins_lower if plugin not in self.lower_plugins_ignore)

        # Early return if no plugins to match
        if not plugins_to_match:
            lines.append("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n")
            return ReportFragment.from_lines(lines)

        # Get cached compiled pattern for all plugins
        plugin_pattern = _compile_plugin_pattern(plugins_to_match)

        # Use Counter directly instead of list + Counter conversion
        plugins_matches: Counter[str] = Counter()

        # Optimized matching using single compiled regex pattern
        for line in relevant_lines:
            # Find all plugin matches in this line
            matches = plugin_pattern.findall(line)
            # Count each unique match
            plugins_matches.update(match.lower() for match in matches)

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
            crashlog_plugins (dict[str, str]): A dictionary of crashlog plugins with plugin names
                as keys and corresponding values.

        Returns:
            dict[str, str]: A dictionary of crashlog plugins with ignored plugins removed.
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

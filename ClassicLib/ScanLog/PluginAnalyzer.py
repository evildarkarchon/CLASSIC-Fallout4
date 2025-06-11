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

from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.Util import append_or_extend

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
    def loadorder_scan_loadorder_txt(autoscan_report: list[str]) -> tuple[dict[str, str], bool]:
        """
        Process the loadorder.txt file to generate a mapping of plugins.
        
        Args:
            autoscan_report: List to append informational messages
            
        Returns:
            Tuple containing:
            - Dictionary mapping plugin names to origin markers
            - Boolean indicating if any plugins were loaded
        """
        loadorder_messages = (
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n",
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n",
        )
        loadorder_origin = "LO"  # Origin marker for plugins from loadorder.txt
        loadorder_path = Path("loadorder.txt")
        
        append_or_extend(loadorder_messages, autoscan_report)
        
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
            error_msg: str = f"Error reading loadorder.txt: {e!s}"
            append_or_extend(error_msg, autoscan_report)
            
        # Check if any plugins were loaded
        plugins_loaded = bool(loadorder_plugins)
        
        return loadorder_plugins, plugins_loaded
        
    def loadorder_scan_log(
        self, segment_plugins: list[str], game_version: Version, version_current: Version
    ) -> tuple[dict[str, str], bool, bool]:
        """
        Analyze and process a list of plugins from crash log.
        
        Args:
            segment_plugins: List of plugin data segments to process
            game_version: The version of the game
            version_current: The current crash generator version
            
        Returns:
            Tuple containing:
            - Dictionary mapping plugin names to their classified statuses
            - Boolean indicating if plugin limit marker was detected
            - Boolean indicating if limit check has been disabled
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
        
    def plugin_match(
        self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str], autoscan_report: list[str]
    ) -> None:
        """
        Match plugins in the call stack against crashlog plugins.
        
        Args:
            segment_callstack_lower: Lowercase call stack lines
            crashlog_plugins_lower: Set of lowercase plugin names
            autoscan_report: List to append match results
        """
        from collections import Counter
        
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
            append_or_extend("The following PLUGINS were found in the CRASH STACK:\n", autoscan_report)
            # Sort by count (descending) then by name for consistent output
            for plugin, count in sorted(plugins_matches.items(), key=lambda x: (-x[1], x[0])):
                append_or_extend(f"- {plugin} | {count}\n", autoscan_report)
            append_or_extend(
                (
                    "\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n",
                    f"These Plugins were caught by {self.yamldata.crashgen_name} and some of them might be responsible for this crash.\n",
                    "You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n", autoscan_report)
            
    def filter_ignored_plugins(self, crashlog_plugins: dict[str, str]) -> dict[str, str]:
        """
        Filter out ignored plugins from the plugin dictionary.
        
        Args:
            crashlog_plugins: Dictionary of plugins to filter
            
        Returns:
            Filtered plugin dictionary
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
"""
FormID analyzer module for CLASSIC.

This module manages FormID extraction and lookup operations including:
- Extracting FormIDs from crash logs
- Matching FormIDs to plugins
- Looking up FormID values in databases
- Formatting FormID reports
"""

from collections import Counter
from typing import TYPE_CHECKING, Any

import regex as re

from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.ScanLog.Util import get_entry
from ClassicLib.Util import append_or_extend

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class FormIDAnalyzer:
    """Handles FormID analysis and lookup operations."""
    
    def __init__(self, yamldata: "ClassicScanLogsInfo", show_formid_values: bool, formid_db_exists: bool) -> None:
        """
        Initialize the FormID analyzer.
        
        Args:
            yamldata: Configuration data
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
        """
        self.yamldata: ClassicScanLogsInfo = yamldata
        self.show_formid_values: bool = show_formid_values
        self.formid_db_exists: bool = formid_db_exists
        
        # Pattern to match FormID format in crash logs
        self.formid_pattern: re.Pattern[str] = re.compile(
            r"^\s*Form ID:\s*0x([0-9A-F]{8})",
            re.IGNORECASE,
        )
        
    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """
        Extract FormIDs from the call stack segment.
        
        Args:
            segment_callstack: List of call stack lines
            
        Returns:
            List of FormID strings found
        """
        formids_matches: list[str] = []
        
        if not segment_callstack:
            return formids_matches
            
        for line in segment_callstack:
            match: re.Match[str] | None = self.formid_pattern.search(line)
            if match:
                formid_id: str | Any = match.group(1).upper()  # Get the hex part without 0x
                # Skip if it starts with FF (plugin limit)
                if not formid_id.startswith("FF"):
                    formids_matches.append(f"Form ID: {formid_id}")
                    
        return formids_matches
        
    def formid_match(
        self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]
    ) -> None:
        """
        Process and analyze Form IDs, matching them against crash log plugins.
        
        Args:
            formids_matches: List of FormID strings
            crashlog_plugins: Dictionary mapping plugin names to IDs
            autoscan_report: List to append analysis results
        """
        if formids_matches:
            formids_found: dict[str, int] = dict(Counter(sorted(formids_matches)))
            for formid_full, count in formids_found.items():
                formid_split: list[str] | None = formid_full.split(": ", 1)
                if len(formid_split) < 2:
                    continue
                    
                for plugin, plugin_id in crashlog_plugins.items():
                    if plugin_id != formid_split[1][:2]:
                        continue
                        
                    if self.show_formid_values and self.formid_db_exists:
                        report: str | None = get_entry(formid_split[1][2:], plugin)
                        if report:
                            append_or_extend(f"- {formid_full} | [{plugin}] | {report} | {count}\n", autoscan_report)
                            continue
                            
                    append_or_extend(f"- {formid_full} | [{plugin}] | {count}\n", autoscan_report)
                    break
                    
            append_or_extend(
                (
                    "\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
                    f"These Form IDs were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
                    "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend("* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n", autoscan_report)
            
    def lookup_formid_value(self, formid: str, plugin: str) -> str | None:
        """
        Look up a FormID value in the database.
        
        Args:
            formid: The FormID to look up (without plugin prefix)
            plugin: The plugin name
            
        Returns:
            The FormID description if found, None otherwise
        """
        if not self.formid_db_exists:
            return None
            
        return get_entry(formid, plugin)
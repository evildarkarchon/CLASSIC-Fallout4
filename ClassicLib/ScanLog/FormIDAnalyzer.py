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

# Module-level regex pattern cache to avoid recompilation
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}

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

        # Pattern to match FormID format in crash logs (cached)
        pattern_key = "formid_pattern"
        if pattern_key not in _PATTERN_CACHE:
            _PATTERN_CACHE[pattern_key] = re.compile(
                r"^\s*Form ID:\s*0x([0-9A-F]{8})",
                re.IGNORECASE,
            )
        self.formid_pattern = _PATTERN_CACHE[pattern_key]

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """
        Extracts Form IDs from a given call stack.

        This method processes each line in the provided call stack, searching for
        and extracting Form IDs that match a predefined pattern. Extracted Form IDs
        that do not adhere to certain criteria (e.g., starting with "FF") are skipped.
        Matches are then appended to the result list prefixed with "Form ID:".
        If the call stack is empty, an empty list is returned.

        Args:
            segment_callstack (list[str]): A list of strings representing the
                call stack to be processed.

        Returns:
            list[str]: A list containing all extracted and formatted Form IDs
                that meet the criteria.
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

    def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """
        Processes and appends reports based on Form ID matches retrieved from crash logs and a scan report.

        This method analyzes Form ID matches, compares them with plugins listed in the crash log,
        and optionally retrieves additional data from a Form ID database. It generates and appends
        a formatted report to a provided list. If no matches are identified, it appends a default
        report indicating no Form ID suspects were found. The method also supports additional
        context and instructions for interpreting the results, depending on the configuration
        stored in the instance.

        Arguments:
            formids_matches (list[str]): A list of Form ID matches extracted from the crash log.
            crashlog_plugins (dict[str, str]): A dictionary mapping plugin filenames to plugin IDs
                found in the crash log.
            autoscan_report (list[str]): A mutable list to which the generated or default report
                will be appended.

        Returns:
            None
        """
        if formids_matches:
            formids_found: dict[str, int] = dict(Counter(sorted(formids_matches)))
            for formid_full, count in formids_found.items():
                formid_split: list[str] = formid_full.split(": ", 1)
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
        Look up the value associated with a given form ID and plugin in the database.

        This method retrieves the value corresponding to the provided form ID and plugin
        from the database. If the database does not exist, it returns None. Otherwise,
        it uses the `get_entry` function to fetch the value.

        Args:
            formid: A string representing the form ID to look up.
            plugin: A string representing the plugin name associated with the form ID.

        Returns:
            A string containing the value associated with the form ID and plugin if
            found in the database, or None if the database does not exist or the
            value is not found.
        """
        if not self.formid_db_exists:
            return None

        return get_entry(formid, plugin)

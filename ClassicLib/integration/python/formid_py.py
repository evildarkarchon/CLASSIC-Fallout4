"""Pure Python implementation of FormID analysis.

This module provides the fallback Python implementation for FormID extraction
and analysis when Rust acceleration is not available. It maintains full
compatibility with the FormIDAnalyzer API.
"""

import asyncio
import re
from collections import Counter
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ClassicLib.io.database import AsyncDatabasePool
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo
    from ClassicLib.scanning.logs.reporting import ReportFragment

# Module-level regex pattern cache to avoid recompilation
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


# LRU cache for FormID lookup results to avoid repeated database queries
@lru_cache(maxsize=512)
def _cached_formid_lookup(formid: str, plugin: str) -> str | None:
    """Cache the lookup result of a FormID and its associated plugin.

    This function performs a cached lookup to retrieve the entry
    associated with the given `formid` and `plugin`. It uses an
    LRU cache to optimize repeated lookups for the same
    FormID-plugin pairs, with a maximum cache size of 512 entries.

    Args:
        formid (str): The unique identifier of the form to look up.
        plugin (str): The plugin name associated with the form ID.

    Returns:
        str | None: The retrieved entry associated with the given
        form ID and plugin, or None if no entry is found.

    """
    from ClassicLib.scanning.logs.util_legacy import get_entry

    return get_entry(formid, plugin)


class PythonFormIDAnalyzer:
    """Pure Python implementation for processing and interpreting Form IDs in crash logs.

    This class provides the fallback Python implementation for extracting, matching,
    and analyzing Form IDs when Rust acceleration is not available. Form IDs are
    unique identifiers found in crash logs that refer to specific records within plugins.

    Attributes:
        yamldata: Configuration data for the scan logs analyzer.
        show_formid_values: Controls whether FormID details are displayed in the analysis.
        formid_db_exists: Indicates if a FormID database is available for lookups.
        db_pool: Optional async database connection pool for lookups.
        formid_pattern: Compiled regex pattern for matching FormID formats in logs.

    """

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        show_formid_values: bool,
        formid_db_exists: bool,
        db_pool: "AsyncDatabasePool | None" = None,
    ) -> None:
        """Initialize a new instance of the FormID analyzer.

        This ensures certain patterns and configurations are ready for operations
        with provided data.

        Args:
            yamldata: Parsed YAML data containing crash log information for processing.
            show_formid_values: Flag to indicate whether FormID values should be displayed.
            formid_db_exists: Indicates the presence of a FormID database.
            db_pool: Optional asynchronous database pool for data operations.

        """
        self.yamldata = yamldata
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists
        self.db_pool = db_pool

        # Pattern to match FormID format in crash logs (cached)
        pattern_key = "formid_pattern"
        if pattern_key not in _PATTERN_CACHE:
            _PATTERN_CACHE[pattern_key] = re.compile(
                r"^\s*Form ID:\s*0x([0-9A-F]{8})",
                re.IGNORECASE,
            )
        self.formid_pattern = _PATTERN_CACHE[pattern_key]

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """Extract and processes Form IDs from a given list of callstack strings.

        This method scans through each entry in the provided callstack, identifies and
        extracts the Form IDs adhering to specific criteria, and compiles them into a list.
        It only includes Form IDs that do not start with "FF" while preserving "00000000"
        for error reporting.

        Args:
            segment_callstack: A list of strings representing the callstack to be scanned.

        Returns:
            list[str]: A list of processed Form IDs in the format "Form ID: <ID>".

        """
        formids_matches: list[str] = []

        if not segment_callstack:
            return formids_matches

        for line in segment_callstack:
            match = self.formid_pattern.search(line)
            if match:
                formid_id = match.group(1).upper()  # Get the hex part without 0x
                # Skip if it starts with FF (plugin limit)
                # Note: NULL FormIDs (00000000) are intentionally kept as they indicate errors
                if not formid_id.startswith("FF"):
                    formids_matches.append(f"Form ID: {formid_id}")

        return formids_matches

    async def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str]) -> "ReportFragment":
        """Async-first implementation for FormID matching with optional concurrent database lookups.

        This method analyzes FormID matches, compares them with plugins listed in the crash log,
        and optionally retrieves additional data from a FormID database. If a database pool is
        available, it performs concurrent lookups for improved performance.

        Args:
            formids_matches: List of FormID strings extracted from the crash log
            crashlog_plugins: Dictionary mapping plugin filenames to plugin IDs

        Returns:
            ReportFragment containing the FormID analysis results

        """
        from ClassicLib.scanning.logs.reporting import ReportFragment

        if not formids_matches:
            return ReportFragment.from_lines(["* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n"])

        lines = []
        formids_found = dict(Counter(sorted(formids_matches)))

        # Prepare all lookup tasks
        lookup_tasks = []

        for formid_full, count in formids_found.items():
            formid_split = formid_full.split(": ", 1)
            if len(formid_split) < 2:
                continue

            formid_value = formid_split[1]
            formid_prefix = formid_value[:2]
            formid_suffix = formid_value[2:]

            # Find matching plugins
            for plugin, plugin_id in crashlog_plugins.items():
                if plugin_id == formid_prefix:
                    lookup_tasks.append((formid_full, formid_suffix, plugin, count))
                    break

        # Execute database lookups
        if self.show_formid_values and self.formid_db_exists and self.db_pool and lookup_tasks:
            # Use async database pool for concurrent lookups
            await self._perform_async_lookups(lookup_tasks, lines)  # pyright: ignore[reportUnknownArgumentType]
        elif self.show_formid_values and self.formid_db_exists and lookup_tasks:
            # Fallback to sync database lookups
            await self._perform_sync_lookups(lookup_tasks, lines)  # pyright: ignore[reportUnknownArgumentType]
        else:
            # No database lookups needed
            for formid_full, _formid_suffix, plugin, count in lookup_tasks:  # pyright: ignore[reportUnknownVariableType]
                lines.append(f"- {formid_full} | [{plugin}] | {count}\n")

        # Add footer information
        lines.extend([
            "\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
            f"These Form IDs were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
            "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n",
        ])

        return ReportFragment.from_lines(lines)  # pyright: ignore[reportUnknownArgumentType]

    async def _perform_async_lookups(self, lookup_tasks: list[tuple[str, str, str, int]], lines: list[str]) -> None:
        """Perform asynchronous database lookups for the given tasks and appends the processed
        results to the provided list of lines. If no database connection pool is available,
        a fallback mechanism is used to add basic formatted strings to the lines.

        Args:
            lookup_tasks (list[tuple[str, str, str, int]]): A list of tuples where each tuple
                contains the following elements:
                - The full FormID (str).
                - The short FormID (str).
                - The plugin name (str).
                - The FormID count (int).
            lines (list[str]): A list of strings to which the results of the lookup are appended.

        """
        if not self.db_pool:
            # Fallback if no database pool available
            for full_formid, _, plugin_name, formid_count in lookup_tasks:
                lines.append(f"- {full_formid} | [{plugin_name}] | {formid_count}\n")
            return

        # Extract FormID/plugin pairs for batch lookup
        formid_plugin_pairs = [(task[1], task[2]) for task in lookup_tasks]

        # Perform batch database lookup
        batch_results = await self.db_pool.get_entries_batch(formid_plugin_pairs)

        # Format results
        for full_formid, formid, plugin_name, formid_count in lookup_tasks:
            cache_key = (formid, plugin_name)
            report = batch_results.get(cache_key)

            if report:
                lines.append(f"- {full_formid} | [{plugin_name}] | {report} | {formid_count}\n")
            else:
                lines.append(f"- {full_formid} | [{plugin_name}] | {formid_count}\n")

    @staticmethod
    async def _perform_sync_lookups(lookup_tasks: list[tuple[str, str, str, int]], lines: list[str]) -> None:
        """Perform synchronous lookups for provided tasks and modifies the given list of lines with the results.

        This method asynchronously handles a list of lookup tasks, each consisting of attributes for
        form ID details and associated plugin information, and appends formatted results to the `lines` list.
        It uses a cached synchronous database lookup function to optimize repeated queries.

        Args:
            lookup_tasks (list[tuple[str, str, str, int]]): A list of tuples containing form ID full
                reference, form ID suffix, plugin name, and count for each lookup task.
            lines (list[str]): A list to which the method will append formatted output strings containing
                the results of the lookup operations.

        """
        for formid_full, formid_suffix, plugin, count in lookup_tasks:
            # Use cached sync database lookup to avoid repeated queries
            report = await asyncio.to_thread(_cached_formid_lookup, formid_suffix, plugin)
            if report:
                lines.append(f"- {formid_full} | [{plugin}] | {report} | {count}\n")
            else:
                lines.append(f"- {formid_full} | [{plugin}] | {count}\n")

    async def lookup_formid_value(self, formid: str, plugin: str) -> str | None:
        """Look up the value associated with the given `formid` and `plugin` within
        the form ID database. Returns the value if found, or `None` if the database
        does not exist or the entry is not present.

        This function first checks if the form ID database exists and proceeds only
        if it does. It uses an asynchronous database pool for the lookup, if
        available. As a fallback mechanism, it performs a lookup via a synchronous
        cached method in a separate thread.

        Args:
            formid: The unique form ID to look up in the database.
            plugin: The plugin or namespace associated with the form ID.

        Returns:
            str | None: The associated value as a string if found, otherwise `None`.

        """
        if not self.formid_db_exists:
            return None

        if self.db_pool:
            # Use async database pool
            return await self.db_pool.get_entry(formid, plugin)
        # Fallback to cached sync lookup in thread
        return await asyncio.to_thread(_cached_formid_lookup, formid, plugin)


# Alias for compatibility
FormIDAnalyzer = PythonFormIDAnalyzer

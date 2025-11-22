"""
Async-first core implementation for FormID analysis.

This module provides the primary async implementation for FormID analysis,
consolidating the functionality of both FormIDAnalyzer and AsyncFormIDAnalyzer
into a single async-first design.
"""

import asyncio
from collections import Counter
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import regex as re

from ClassicLib.AsyncBridge import run_async
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool
from ClassicLib.ScanLog.Util import get_entry

if TYPE_CHECKING:
    from ClassicLib.ScanLog.fragments import ReportFragment
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

# Module-level regex pattern cache to avoid recompilation
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


# LRU cache for FormID lookup results to avoid repeated database queries
@lru_cache(maxsize=512)
def _cached_formid_lookup(formid: str, plugin: str) -> str | None:
    """
    Caches and retrieves a specific form ID associated with a given plugin. This function leverages an
    LRU (Least Recently Used) cache mechanism to enhance performance by storing up to a specified
    number of recent form ID lookups.

    Args:
        formid (str): The identifier of the form to look up.
        plugin (str): The plugin associated with the specified form ID.

    Returns:
        str | None: The cached or retrieved string form ID if found, otherwise None.
    """
    return get_entry(formid, plugin)


class FormIDAnalyzerCore:
    """
    Core analysis functionality for processing and interpreting Form IDs in crash logs.

    This class provides utilities for extracting, matching, and analyzing Form IDs.
    Form IDs are unique identifiers often found in crash logs that refer to specific
    records within plugins. The main goal of this class is to facilitate the analysis
    of these identifiers, optionally using an asynchronous database for enhanced
    insights. The class supports both synchronous and asynchronous operations for
    flexibility of use.

    Attributes:
        yamldata (ClassicScanLogsInfo): Configuration data for the scan logs analyzer.
        show_formid_values (bool): Controls whether FormID details are displayed in the analysis.
        formid_db_exists (bool): Indicates if a FormID database is available for lookups.
        db_pool (AsyncDatabasePool | None): Optional async database connection pool for lookups.
        formid_pattern (Pattern): Compiled regex pattern for matching FormID formats in logs, cached for reuse.
    """

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        show_formid_values: bool,
        formid_db_exists: bool,
        db_pool: AsyncDatabasePool | None = None,
    ) -> None:
        """
        Initializes a new instance of the class, parsing and preparing information
        about crash logs. This ensures certain patterns and configurations are
        ready for operations with provided data.

        Args:
            yamldata (ClassicScanLogsInfo): Parsed YAML data containing crash log
                information for processing.
            show_formid_values (bool): Flag to indicate whether FormID values should
                be displayed in outputs or logs.
            formid_db_exists (bool): Indicates the presence of a FormID database
                in the current context or configuration.
            db_pool (AsyncDatabasePool | None): Optional asynchronous database pool
                used for various data fetching or writing operations.
        """
        self.yamldata = yamldata
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists
        self.db_pool = db_pool

        # Pattern to match FormID format in crash logs (cached)
        pattern_key = "formid_pattern"
        if pattern_key not in _PATTERN_CACHE:
            _PATTERN_CACHE[pattern_key] = re.compile(
                r"Form\s*ID:?\s*0x([0-9A-F]{8})\b",
                re.IGNORECASE,
            )
        self.formid_pattern = _PATTERN_CACHE[pattern_key]

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """
        Extracts and processes Form IDs from a given list of callstack strings.

        This method scans through each entry in the provided callstack, identifies and extracts the
        Form IDs adhering to specific criteria, and compiles them into a list. It only includes
        Form IDs that do not start with "FF" while preserving "00000000" for error reporting.

        Args:
            segment_callstack (list[str]): A list of strings representing the callstack to be scanned
                for Form IDs.

        Returns:
            list[str]: A list of processed Form IDs in the format "Form ID: <ID>".
        """
        formids_matches: list[str] = []

        if not segment_callstack:
            return formids_matches

        for line in segment_callstack:
            match: re.Match[str] | None = self.formid_pattern.search(line)
            if match:
                formid_id: str | Any = match.group(1).upper()  # Get the hex part without 0x
                # Skip if it starts with FF (plugin limit)
                # Note: NULL FormIDs (00000000) are intentionally kept as they indicate errors
                if not formid_id.startswith("FF"):
                    formids_matches.append(f"Form ID: {formid_id}")

        return formids_matches

    async def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str]) -> "ReportFragment":
        """
        Async-first implementation for FormID matching with optional concurrent database lookups.

        This method analyzes FormID matches, compares them with plugins listed in the crash log,
        and optionally retrieves additional data from a FormID database. If a database pool is
        available, it performs concurrent lookups for improved performance.

        Args:
            formids_matches: List of FormID strings extracted from the crash log
            crashlog_plugins: Dictionary mapping plugin filenames to plugin IDs

        Returns:
            ReportFragment containing the FormID analysis results
        """
        from ClassicLib.ScanLog.fragments import ReportFragment

        if not formids_matches:
            return ReportFragment.from_lines(["* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n"])

        lines = []
        formids_found: dict[str, int] = dict(Counter(sorted(formids_matches)))

        # Prepare all lookup tasks
        lookup_tasks: list[tuple[str, str, str, int]] = []

        for formid_full, count in formids_found.items():
            formid_split: list[str] = formid_full.split(": ", 1)
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
            await self._perform_async_lookups(lookup_tasks, lines)
        elif self.show_formid_values and self.formid_db_exists and lookup_tasks:
            # Fallback to sync database lookups
            await self._perform_sync_lookups(lookup_tasks, lines)
        else:
            # No database lookups needed
            for formid_full, _formid_suffix, plugin, count in lookup_tasks:
                lines.append(f"- {formid_full} | [{plugin}] | {count}\n")

        # Add footer information
        lines.extend([
            "\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
            f"These Form IDs were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
            "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n",
        ])

        return ReportFragment.from_lines(lines)

    async def _perform_async_lookups(self, lookup_tasks: list[tuple[str, str, str, int]], lines: list[str]) -> None:
        """
        Performs asynchronous lookups for provided tasks and formats the results.

        Uses batch database queries to efficiently fetch multiple FormID entries in a single
        database round-trip, dramatically reducing query overhead and improving performance.

        Args:
            lookup_tasks (list[tuple[str, str, str, int]]): A list of tuples, where each tuple
                contains information for a lookup task. The tuple includes:
                - full_formid (str): The complete FormID string.
                - formid (str): The sub-section of the FormID relevant to the lookup.
                - plugin_name (str): The name of the plugin associated with the FormID.
                - formid_count (int): Count or occurrence of the specific FormID.
            lines (list[str]): A list to which the formatted output results will be appended.
        """
        if not self.db_pool:
            # Fallback if no database pool available
            for full_formid, _, plugin_name, formid_count in lookup_tasks:
                lines.append(f"- {full_formid} | [{plugin_name}] | {formid_count}\n")
            return

        # Extract FormID/plugin pairs for batch lookup
        formid_plugin_pairs = [(task[1], task[2]) for task in lookup_tasks]

        # Perform batch database lookup (3-5x performance improvement)
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
        """
        Performs synchronous database lookups in an asynchronous context using a thread pool.

        This method processes a list of lookup tasks that involve retrieving data from a
        database in a synchronous manner and appends the result to the specified lines.

        Args:
            lookup_tasks (list[tuple[str, str, str, int]]): A list of tuples where each tuple contains:
                - formid_full (str): Full form identifier.
                - formid_suffix (str): Suffix for the form identifier.
                - plugin (str): Plugin associated with the form identifier.
                - count (int): Count or occurrence related to the form.
            lines (list[str]): A list to which the formatted lookup results will be appended.
        """
        for formid_full, formid_suffix, plugin, count in lookup_tasks:
            # Use cached sync database lookup to avoid repeated queries
            report = await asyncio.to_thread(_cached_formid_lookup, formid_suffix, plugin)
            if report:
                lines.append(f"- {formid_full} | [{plugin}] | {report} | {count}\n")
            else:
                lines.append(f"- {formid_full} | [{plugin}] | {count}\n")

    async def lookup_formid_value(self, formid: str, plugin: str) -> str | None:
        """
        Performs a lookup for a formid value in the database or cache.

        If the database is present, it will try to use the async database
        connection pool to retrieve the formid entry associated with the
        provided formid and plugin. If the async database pool is unavailable,
        it falls back to a cached synchronous lookup running in a thread.

        Args:
            formid (str): The formid to look up.
            plugin (str): The plugin associated with the formid.

        Returns:
            str | None: The value associated with the formid and plugin if found,
            otherwise None.
        """
        if not self.formid_db_exists:
            return None

        if self.db_pool:
            # Use async database pool
            return await self.db_pool.get_entry(formid, plugin)
        # Fallback to cached sync lookup in thread
        return await asyncio.to_thread(_cached_formid_lookup, formid, plugin)

    # Synchronous wrapper methods for backwards compatibility
    def formid_match_sync(self, formids_matches: list[str], crashlog_plugins: dict[str, str]) -> "ReportFragment":
        """
        Synchronous wrapper for formid_match.

        This method provides backwards compatibility for sync callers.

        Returns:
            ReportFragment containing the FormID analysis results
        """
        return run_async(self.formid_match(formids_matches, crashlog_plugins))

    def lookup_formid_value_sync(self, formid: str, plugin: str) -> str | None:
        """
        Synchronously retrieves the value for a given form ID and plugin.

        This method serves as a synchronous wrapper around an asynchronous function
        to retrieve the value associated with a particular form ID and plugin. If
        no value is found, the method will return None.

        Args:
            formid (str): The form ID to look up.
            plugin (str): The plugin associated with the form ID.

        Returns:
            str | None: The value associated with the form ID and plugin, or
            None if no value is found.
        """
        return run_async(self.lookup_formid_value(formid, plugin))

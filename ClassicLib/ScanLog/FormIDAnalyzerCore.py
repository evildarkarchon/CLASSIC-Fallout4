"""
Async-first core implementation for FormID analysis.

This module provides the primary async implementation for FormID analysis,
consolidating the functionality of both FormIDAnalyzer and AsyncFormIDAnalyzer
into a single async-first design.
"""

import asyncio
from collections import Counter
from typing import TYPE_CHECKING, Any

import regex as re

from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool
from ClassicLib.ScanLog.Util import get_entry
from ClassicLib.Util import append_or_extend

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

# Module-level regex pattern cache to avoid recompilation
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


class FormIDAnalyzerCore:
    """Async-first core implementation for FormID analysis."""

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        show_formid_values: bool,
        formid_db_exists: bool,
        db_pool: AsyncDatabasePool | None = None,
    ) -> None:
        """
        Initialize the FormID analyzer core.

        Args:
            yamldata: Configuration data
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
            db_pool: Optional async database connection pool for async operations
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
        """
        Extract FormIDs from the call stack segment.

        This method remains synchronous as regex operations are CPU-bound
        and don't benefit from async execution.

        Args:
            segment_callstack: Lines from the call stack segment

        Returns:
            List of FormID strings formatted as "Form ID: XXXXXXXX"
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

    async def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """
        Async-first implementation for FormID matching with optional concurrent database lookups.

        This method analyzes FormID matches, compares them with plugins listed in the crash log,
        and optionally retrieves additional data from a FormID database. If a database pool is
        available, it performs concurrent lookups for improved performance.

        Args:
            formids_matches: List of FormID strings extracted from the crash log
            crashlog_plugins: Dictionary mapping plugin filenames to plugin IDs
            autoscan_report: List to append analysis results to
        """
        if not formids_matches:
            append_or_extend("* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n", autoscan_report)
            return

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
            await self._perform_async_lookups(lookup_tasks, autoscan_report)
        elif self.show_formid_values and self.formid_db_exists and lookup_tasks:
            # Fallback to sync database lookups
            await self._perform_sync_lookups(lookup_tasks, autoscan_report)
        else:
            # No database lookups needed
            for formid_full, _formid_suffix, plugin, count in lookup_tasks:
                append_or_extend(f"- {formid_full} | [{plugin}] | {count}\n", autoscan_report)

        # Add footer information
        append_or_extend(
            (
                "\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
                f"These Form IDs were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
                "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n",
            ),
            autoscan_report,
        )

    async def _perform_async_lookups(self, lookup_tasks: list[tuple[str, str, str, int]], autoscan_report: list[str]) -> None:
        """
        Perform concurrent database lookups using async database pool.

        Args:
            lookup_tasks: List of tuples containing (formid_full, formid_suffix, plugin, count)
            autoscan_report: List to append results to
        """

        async def lookup_and_format(full_formid: str, formid: str, plugin_name: str, formid_count: int) -> str:
            """Perform database lookup and format result."""
            if self.db_pool:
                report = await self.db_pool.get_entry(formid, plugin_name)
                if report:
                    return f"- {full_formid} | [{plugin_name}] | {report} | {formid_count}\n"
            return f"- {full_formid} | [{plugin_name}] | {formid_count}\n"

        # Run all lookups concurrently
        lookup_coroutines = [
            lookup_and_format(formid_full, formid_suffix, plugin, count) for formid_full, formid_suffix, plugin, count in lookup_tasks
        ]

        results = await asyncio.gather(*lookup_coroutines)

        # Append all results
        for result in results:
            append_or_extend(result, autoscan_report)

    async def _perform_sync_lookups(self, lookup_tasks: list[tuple[str, str, str, int]], autoscan_report: list[str]) -> None:
        """
        Perform synchronous database lookups wrapped in async.

        This is used when no async database pool is available but database
        lookups are still needed.

        Args:
            lookup_tasks: List of tuples containing (formid_full, formid_suffix, plugin, count)
            autoscan_report: List to append results to
        """
        for formid_full, formid_suffix, plugin, count in lookup_tasks:
            # Use sync database lookup
            report = await asyncio.to_thread(get_entry, formid_suffix, plugin)
            if report:
                append_or_extend(f"- {formid_full} | [{plugin}] | {report} | {count}\n", autoscan_report)
            else:
                append_or_extend(f"- {formid_full} | [{plugin}] | {count}\n", autoscan_report)

    async def lookup_formid_value(self, formid: str, plugin: str) -> str | None:
        """
        Async lookup of FormID value in database.

        Args:
            formid: FormID to look up (without prefix)
            plugin: Plugin name

        Returns:
            FormID description if found, None otherwise
        """
        if not self.formid_db_exists:
            return None

        if self.db_pool:
            # Use async database pool
            return await self.db_pool.get_entry(formid, plugin)
        # Fallback to sync lookup in thread
        return await asyncio.to_thread(get_entry, formid, plugin)

    # Synchronous wrapper methods for backwards compatibility
    def formid_match_sync(self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """
        Synchronous wrapper for formid_match.

        This method provides backwards compatibility for sync callers.
        """
        asyncio.run(self.formid_match(formids_matches, crashlog_plugins, autoscan_report))

    def lookup_formid_value_sync(self, formid: str, plugin: str) -> str | None:
        """
        Synchronous wrapper for lookup_formid_value.

        This method provides backwards compatibility for sync callers.
        """
        return asyncio.run(self.lookup_formid_value(formid, plugin))

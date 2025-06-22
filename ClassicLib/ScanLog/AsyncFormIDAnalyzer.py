"""
Async FormID analyzer module for crash log scanning.

This module provides an async version of FormID analysis with concurrent
database lookups for improved performance.
"""

import asyncio
from collections import Counter
from typing import TYPE_CHECKING, Any

import regex as re

from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool
from ClassicLib.ScanLog.FormIDAnalyzer import _PATTERN_CACHE
from ClassicLib.Util import append_or_extend

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class AsyncFormIDAnalyzer:
    """Async version of FormID analyzer with concurrent database lookups."""

    def __init__(
        self, yamldata: "ClassicScanLogsInfo", show_formid_values: bool, formid_db_exists: bool, db_pool: AsyncDatabasePool
    ) -> None:
        """
        Initialize the async FormID analyzer.

        Args:
            yamldata: Configuration data
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
            db_pool: Async database connection pool
        """
        self.yamldata = yamldata
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists
        self.db_pool = db_pool

        # Reuse cached regex pattern
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

        This method remains synchronous as regex operations are CPU-bound.

        Args:
            segment_callstack: Lines from the call stack segment

        Returns:
            List of FormID strings
        """
        formids_matches: list[str] = []

        for line in segment_callstack:
            match: re.Match[str] | None = self.formid_pattern.search(line)
            if match:
                formid_id: str | Any = match.group(1).upper()
                # Skip if it starts with FF (plugin limit)
                if not formid_id.startswith("FF"):
                    formids_matches.append(f"Form ID: {formid_id}")

        return formids_matches

    async def formid_match_async(self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """
        Async version of FormID matching with concurrent database lookups.

        Args:
            formids_matches: List of FormID strings
            crashlog_plugins: Dictionary mapping plugin_name names to IDs
            autoscan_report: List to append analysis results
        """
        if not formids_matches:
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

        # Execute all database lookups concurrently
        if self.show_formid_values and self.formid_db_exists and lookup_tasks:

            async def lookup_and_format(full_formid: str, formid: str, plugin_name: str, formid_count: int) -> str | None:
                """Perform database lookup and format result."""
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
                if result:
                    append_or_extend(result, autoscan_report)
        else:
            # Fallback to non-database version
            for formid_full, _formid_suffix, plugin, count in lookup_tasks:
                append_or_extend(f"- {formid_full} | [{plugin}] | {count}\n", autoscan_report)

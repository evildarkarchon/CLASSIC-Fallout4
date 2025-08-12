"""
FormID analyzer module for CLASSIC.

This module provides a synchronous interface for FormID extraction and lookup operations.
It acts as a sync adapter that delegates to the async-first FormIDAnalyzerCore implementation.

NOTE: This is now a thin sync adapter for backwards compatibility.
New code should use FormIDAnalyzerCore directly for async operations.
"""

import asyncio
from typing import TYPE_CHECKING

from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class FormIDAnalyzer:
    """Sync adapter for FormIDAnalyzerCore - provides backwards compatibility."""

    def __init__(self, yamldata: "ClassicScanLogsInfo", show_formid_values: bool, formid_db_exists: bool) -> None:
        """
        Initialize the sync FormID analyzer adapter.

        Args:
            yamldata: Configuration data
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
        """
        # Create core analyzer without async database pool for sync operations
        self._core = FormIDAnalyzerCore(yamldata, show_formid_values, formid_db_exists, db_pool=None)

        # Expose core attributes for backwards compatibility
        self.yamldata = self._core.yamldata
        self.show_formid_values = self._core.show_formid_values
        self.formid_db_exists = self._core.formid_db_exists
        self.formid_pattern = self._core.formid_pattern

    def extract_formids(self, segment_callstack: list[str]) -> list[str]:
        """
        Sync adapter for FormID extraction.

        Extracts Form IDs from a given call stack. This method processes each line
        in the provided call stack, searching for and extracting Form IDs that match
        a predefined pattern.

        Args:
            segment_callstack: A list of strings representing the call stack to be processed.

        Returns:
            A list containing all extracted and formatted Form IDs that meet the criteria.
        """
        # Delegate to core (this method is already synchronous in core)
        return self._core.extract_formids(segment_callstack)

    def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """
        Sync adapter for FormID matching.

        Processes and appends reports based on Form ID matches retrieved from crash logs.
        This method analyzes Form ID matches, compares them with plugins listed in the crash log,
        and optionally retrieves additional data from a Form ID database.

        Args:
            formids_matches: A list of Form ID matches extracted from the crash log.
            crashlog_plugins: A dictionary mapping plugin filenames to plugin IDs found in the crash log.
            autoscan_report: A mutable list to which the generated or default report will be appended.
        """
        # Run async method synchronously
        asyncio.run(self._core.formid_match(formids_matches, crashlog_plugins, autoscan_report))

    def lookup_formid_value(self, formid: str, plugin: str) -> str | None:
        """
        Sync adapter for FormID value lookup.

        Look up the value associated with a given form ID and plugin in the database.

        Args:
            formid: A string representing the form ID to look up.
            plugin: A string representing the plugin name associated with the form ID.

        Returns:
            A string containing the value associated with the form ID and plugin if
            found in the database, or None if the database does not exist or the
            value is not found.
        """
        # Run async method synchronously
        return asyncio.run(self._core.lookup_formid_value(formid, plugin))

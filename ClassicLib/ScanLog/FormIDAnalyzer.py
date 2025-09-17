"""
FormID analyzer module for CLASSIC.

This module provides a synchronous interface for FormID extraction and lookup operations.
It acts as a sync adapter that delegates to the async-first FormIDAnalyzerCore implementation.

NOTE: This is now a thin sync adapter for backwards compatibility.
New code should use FormIDAnalyzerCore directly for async operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.AsyncBridge import run_async
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ReportFragment import ReportFragment
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class FormIDAnalyzer:
    """
    Analyzes FormID data and integrates with crash logs for synchronization and reporting.

    This class provides synchronous functionality for processing and analyzing FormID data,
    including extracting Form IDs from call stacks, matching them with crash logs, and
    retrieving additional information when applicable. It supports operations such as
    form ID extraction and matching with plugins listed in crash logs and synchronous
    database lookups for FormID values.

    Attributes:
        yamldata (ClassicScanLogsInfo): Configuration data for the analyzer.
        show_formid_values (bool): Whether to display the FormID values in the output.
        formid_db_exists (bool): Indicates whether a FormID database exists.
        formid_pattern (str): A predefined pattern used for FormID extraction.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo, show_formid_values: bool, formid_db_exists: bool) -> None:
        """
        Initializes the core analyzer for synchronous operations without an async database pool.

        Args:
            yamldata: Contains information regarding classic scan logs.
            show_formid_values: Indicates whether to display form ID values.
            formid_db_exists: Specifies if the form ID database exists.

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

    def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str]) -> ReportFragment:
        """
        Sync adapter for FormID matching.

        Processes and returns a report fragment based on Form ID matches retrieved from crash logs.
        This method analyzes Form ID matches, compares them with plugins listed in the crash log,
        and optionally retrieves additional data from a Form ID database.

        Args:
            formids_matches: A list of Form ID matches extracted from the crash log.
            crashlog_plugins: A dictionary mapping plugin filenames to plugin IDs found in the crash log.

        Returns:
            ReportFragment containing the FormID analysis results.
        """
        # Run async method using AsyncBridge
        return run_async(self._core.formid_match(formids_matches, crashlog_plugins))

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
        # Run async method using AsyncBridge
        return run_async(self._core.lookup_formid_value(formid, plugin))

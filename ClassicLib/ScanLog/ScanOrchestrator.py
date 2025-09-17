"""
Scan orchestrator module for CLASSIC.

This module provides a synchronous interface for crash log scanning coordination.
It acts as a sync adapter that delegates to the async-first OrchestratorCore implementation.

NOTE: This is now a thin sync adapter for backwards compatibility.
New code should use OrchestratorCore directly for async operations.
"""

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from ClassicLib.AsyncBridge import run_async
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache


class ScanOrchestrator:
    """Orchestrates scanning processes and provides an interface for various scanning-related operations.

    This class acts as the orchestrator for handling scan processes. It relies on a core scanning module
    to perform actual operations and exposes its attributes and functionalities for easier interaction.
    It is typically used to manage crash logs, update scan-related statistics, and generate reports.

    Attributes:
        yamldata (ClassicScanLogsInfo): Configuration data for scan operations.
        crashlogs (ThreadSafeLogCache): Thread-safe cache for managing crash logs.
        plugin_analyzer: Interface for analyzing plugin data.
        formid_analyzer: Interface for analyzing FormID data.
        suspect_scanner: Scanner for identifying suspect elements in scan logs.
        record_scanner: Scanner for analyzing and processing specific records.
        settings_scanner: Scanner for reading and processing scan-related settings.
        report_generator: Interface for generating scan result reports.
        fcx_handler: Handler for managing operations in FCX mode.
        game_root_name: Name of the root folder of the game being scanned.
        last_formids (list): List of the most recent FormIDs processed.
        last_plugins (dict): Dictionary of the most recent plugins processed.
    """

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        crashlogs: "ThreadSafeLogCache",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """
        Initialize the sync orchestrator adapter.

        Args:
            yamldata: Configuration data
            crashlogs: Thread-safe log cache
            fcx_mode: Whether FCX mode is enabled
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
        """
        # Create core orchestrator
        self._core = OrchestratorCore(yamldata, crashlogs, fcx_mode, show_formid_values, formid_db_exists)

        # Expose core attributes for backwards compatibility
        self.yamldata = self._core.yamldata
        self.crashlogs = self._core.crashlogs
        self.plugin_analyzer = self._core.plugin_analyzer
        self.formid_analyzer = self._core.formid_analyzer
        self.suspect_scanner = self._core.suspect_scanner
        self.record_scanner = self._core.record_scanner
        self.settings_scanner = self._core.settings_scanner
        self.report_generator = self._core.report_generator
        self.fcx_handler = self._core.fcx_handler
        self.game_root_name = self._core.game_root_name

        # For FormID state tracking
        self.last_formids = []
        self.last_plugins = {}

    # noinspection PyProtectedMember
    def process_crash_log(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Sync adapter for async process_crash_log.

        Processes a crash log file to extract data, generate a report, and update local statistics.
        Checks for incomplete or failed logs and handles their processing accordingly.

        Parameters:
        crashlog_file (Path): Path to the crash log file to be processed.

        Returns:
        tuple[Path, list[str], bool, Counter[str]]: A tuple containing the path of the crash log file,
        the generated report as a list of strings, a boolean indicating if the scan failed, and a
        Counter object containing local statistics related to the scanning process.
        """
        # Run async method synchronously
        result = run_async(self._core.process_crash_log(crashlog_file))

        # Update last FormIDs and plugins for backwards compatibility
        self.last_formids = [] if not self._core._last_formids else self._core._last_formids.copy()
        self.last_plugins = self._core._last_plugins.copy() if self._core._last_plugins else {}

        return result

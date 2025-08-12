"""
Async-first core implementation for scan orchestration.

This module provides the primary async implementation for crash log orchestration,
consolidating the functionality of both ScanOrchestrator and AsyncScanOrchestrator
into a single async-first design.
"""

import asyncio
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from packaging.version import Version

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool, write_file_async
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandler
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore
from ClassicLib.ScanLog.GPUDetector import get_gpu_info
from ClassicLib.ScanLog.Parser import extract_module_names, find_segments
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.RecordScanner import RecordScanner
from ClassicLib.ScanLog.ReportGenerator import ReportGenerator
from ClassicLib.ScanLog.SettingsScanner import SettingsScanner
from ClassicLib.ScanLog.SuspectScanner import SuspectScanner
from ClassicLib.Util import crashgen_version_gen
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache


class OrchestratorCore:
    """Async-first core implementation for crash log orchestration."""

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        crashlogs: "ThreadSafeLogCache",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """
        Initialize the orchestrator core.

        Args:
            yamldata: Configuration data
            crashlogs: Thread-safe log cache
            fcx_mode: Whether FCX mode is enabled
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
        """
        self.yamldata: ClassicScanLogsInfo = yamldata
        self.crashlogs: ThreadSafeLogCache = crashlogs
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists

        # Initialize all modules
        self.plugin_analyzer = PluginAnalyzer(yamldata)
        self.formid_analyzer = FormIDAnalyzer(yamldata, show_formid_values or False, formid_db_exists)
        self.suspect_scanner = SuspectScanner(yamldata)
        self.record_scanner = RecordScanner(yamldata)
        self.settings_scanner = SettingsScanner(yamldata)
        self.report_generator = ReportGenerator(yamldata)
        self.fcx_handler = FCXModeHandler(fcx_mode)

        # Get game info
        self.game_root_name: str | None = yaml_settings(str, YAML.Game, f"Game_{GlobalRegistry.get_vr()}Info.Main_Root_Name")

        # Async-specific attributes
        self._db_pool: AsyncDatabasePool | None = None
        self._async_formid_analyzer: FormIDAnalyzerCore | None = None
        self._state_lock = asyncio.Lock()

        # Store last FormIDs and plugins for async processing
        self._last_formids: list[str] = []
        self._last_plugins: dict[str, str] = {}

    async def __aenter__(self) -> "OrchestratorCore":
        """Async context manager entry."""
        # Initialize database pool
        self._db_pool = AsyncDatabasePool()
        await self._db_pool.initialize()

        # Create async FormID analyzer
        self._async_formid_analyzer = FormIDAnalyzerCore(
            self.yamldata, self.show_formid_values or False, self.formid_db_exists, self._db_pool
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._db_pool:
            await self._db_pool.close()

    async def process_crash_log(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Async-first implementation for processing a crash log file.

        Args:
            crashlog_file: Path to the crash log file to be processed

        Returns:
            Tuple containing:
            - Path of the crash log file
            - Generated report as list of strings
            - Boolean indicating if the scan failed
            - Counter with local statistics
        """
        autoscan_report: list[str] = []
        trigger_scan_failed = False
        local_stats: Counter[str] = Counter(scanned=1, incomplete=0, failed=0)

        # Read crash data (could be made async in the future)
        crash_data: list[str] = self.crashlogs.read_log(crashlog_file.name)

        # Generate report header
        self.report_generator.generate_header(crashlog_file.name, autoscan_report)

        # Parse crash log segments
        (crashlog_gameversion, crashlog_crashgen, crashlog_mainerror, segments) = find_segments(
            crash_data, self.yamldata.crashgen_name, self.yamldata.xse_acronym, self.game_root_name or ""
        )

        # Unpack segments
        (
            segment_crashgen,
            segment_system,
            segment_callstack,
            segment_allmodules,
            segment_xsemodules,
            segment_plugins,
        ) = segments

        # Check for incomplete/failed logs
        if not segment_plugins:
            local_stats["incomplete"] += 1
        if len(crash_data) < 20:
            local_stats["scanned"] -= 1
            local_stats["failed"] += 1
            trigger_scan_failed = True

        # Process crash log sections
        await self._process_log_sections_async(
            crashlog_gameversion,
            crashlog_crashgen,
            crashlog_mainerror,
            segment_crashgen,
            segment_system,
            segment_callstack,
            segment_allmodules,
            segment_xsemodules,
            segment_plugins,
            autoscan_report,
        )

        # Generate footer
        self.report_generator.generate_footer(autoscan_report)

        return crashlog_file, autoscan_report, trigger_scan_failed, local_stats

    async def _process_log_sections_async(  # noqa: PLR0913
        self,
        crashlog_gameversion: str,
        crashlog_crashgen: str,
        crashlog_mainerror: str,
        segment_crashgen: list[str],
        segment_system: list[str],
        segment_callstack: list[str],
        segment_allmodules: list[str],
        segment_xsemodules: list[str],
        segment_plugins: list[str],
        autoscan_report: list[str],
    ) -> None:
        """Process all sections of the crash log asynchronously."""
        # Version checking
        game_version: Version = crashgen_version_gen(crashlog_gameversion)
        version_current: Version = crashgen_version_gen(crashlog_crashgen)
        version_latest: Version = crashgen_version_gen(self.yamldata.crashgen_latest_og)
        version_latest_vr: Version = crashgen_version_gen(self.yamldata.crashgen_latest_vr)

        # Generate error section
        self.report_generator.generate_error_section(
            crashlog_mainerror, crashlog_crashgen, version_current, version_latest, version_latest_vr, autoscan_report
        )

        # Extract module names
        xsemodules: set[str] = extract_module_names(set(segment_xsemodules))

        # Parse crashgen settings
        crashgen: dict[str, bool | int | str] = self._parse_crashgen_settings(segment_crashgen)

        # Check GPU
        gpu_info = get_gpu_info(segment_system)
        rival_value = gpu_info["rival"]
        crashlog_gpu_rival: Literal["nvidia", "amd"] | None = (
            cast("Literal['nvidia', 'amd']", rival_value) if rival_value in ("nvidia", "amd") else None
        )

        # Process plugins
        crashlog_plugins, trigger_plugin_limit, trigger_limit_check_disabled, trigger_plugins_loaded = self._process_plugins(
            segment_plugins, segment_allmodules, segment_callstack, game_version, version_current, xsemodules, autoscan_report
        )

        # Store for async FormID processing
        async with self._state_lock:
            self._last_plugins = crashlog_plugins.copy()

        # Run suspect scanning
        self._run_suspect_scanning(crashlog_mainerror, segment_callstack, autoscan_report)

        # Check FCX mode and settings
        self._check_fcx_and_settings(
            xsemodules,
            crashgen,
            crashlog_crashgen,
            trigger_plugin_limit,
            trigger_limit_check_disabled,
            trigger_plugins_loaded,
            autoscan_report,
        )

        # Run mod detection with async FormID analysis if available
        await self._run_mod_detection_async(crashlog_plugins, trigger_plugins_loaded, crashlog_gpu_rival, autoscan_report)

        # Scan for specific suspects
        self._scan_specific_suspects(segment_callstack, crashlog_plugins, autoscan_report)

    async def _run_mod_detection_async(
        self,
        crashlog_plugins: dict[str, str],
        trigger_plugins_loaded: bool,
        crashlog_gpu_rival: Literal["nvidia", "amd"] | None,
        autoscan_report: list[str],
    ) -> None:
        """Run mod detection with async FormID analysis."""
        # TODO: Implement proper mod detection
        # Record scanner doesn't have detect_mods method - needs investigation

        # Use async FormID analyzer if available
        if self._async_formid_analyzer and self._last_formids:
            # Find FormID section in report and replace with async version
            formid_section_start = -1
            for i, line in enumerate(autoscan_report):
                if "FORM IDs" in line:
                    formid_section_start = i
                    break

            if formid_section_start >= 0:
                # Find end of FormID section
                formid_section_end = formid_section_start + 1
                for i in range(formid_section_start + 1, len(autoscan_report)):
                    if not autoscan_report[i].startswith("-"):
                        formid_section_end = i
                        break

                # Replace with async analysis
                new_formid_section = []
                await self._async_formid_analyzer.formid_match(self._last_formids, crashlog_plugins, new_formid_section)

                # Replace section in report
                autoscan_report[formid_section_start + 1 : formid_section_end] = new_formid_section

    async def process_crash_logs_batch(self, crashlog_files: list[Path]) -> list[tuple[Path, list[str], bool, Counter[str]]]:
        """
        Process a batch of crash log files asynchronously.

        Args:
            crashlog_files: List of crash log file paths

        Returns:
            List of processing results for each file
        """
        # Process logs in batches to avoid overwhelming the system
        batch_size = 10
        results = []

        for i in range(0, len(crashlog_files), batch_size):
            batch = crashlog_files[i : i + batch_size]

            # Process batch concurrently
            batch_tasks = [self.process_crash_log(log_file) for log_file in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle results
            for result in batch_results:
                if isinstance(result, Exception):
                    # Create error result
                    results.append((Path("error.log"), [f"Error: {result}"], True, Counter(scanned=0, incomplete=0, failed=1)))
                elif isinstance(result, tuple):
                    results.append(result)

        return results

    async def write_reports_batch(self, reports: list[tuple[Path, list[str], bool]]) -> None:
        """
        Write a batch of reports asynchronously.

        Args:
            reports: List of reports to write
        """
        write_tasks = []

        for crashlog_file, autoscan_report, _trigger_scan_failed in reports:
            autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
            autoscan_output: str = "".join(autoscan_report)

            # Create write task
            write_tasks.append(write_file_async(autoscan_path, autoscan_output))

        # Execute all writes concurrently
        await asyncio.gather(*write_tasks, return_exceptions=True)

    # Synchronous helper methods (remain unchanged from original)
    @staticmethod
    def _parse_crashgen_settings(segment_crashgen: list[str]) -> dict[str, bool | int | str]:
        """Parse crashgen configuration from segment."""
        crashgen = {}
        if segment_crashgen:
            for elem in segment_crashgen:
                if ":" in elem:
                    key, value = elem.split(":", 1)
                    crashgen[key] = (
                        True
                        if value == " true"
                        else False
                        if value == " false"
                        else int(value)
                        if value.strip().isdecimal()
                        else value.strip()
                    )
        return crashgen

    def _process_plugins(  # noqa: PLR0913
        self,
        segment_plugins: list[str],
        segment_allmodules: list[str],
        segment_callstack: list[str],
        game_version: Version,
        version_current: Version,
        xsemodules: set[str],
        autoscan_report: list[str],
    ) -> tuple[dict[str, str], bool, bool, bool]:
        """Process plugin information from crash log."""
        plugins: dict[str, str] = {}
        trigger_plugin_limit = False
        trigger_limit_check_disabled = False
        trigger_plugins_loaded = False

        # Check if plugins loaded
        esm_name: str = f"{GlobalRegistry.get_game()}.esm"
        if any(esm_name in elem for elem in segment_plugins):
            trigger_plugins_loaded = True

        # Check for loadorder.txt
        loadorder_path = Path("loadorder.txt")
        if loadorder_path.exists():
            loadorder_plugins, trigger_plugins_loaded = self.plugin_analyzer.loadorder_scan_loadorder_txt(autoscan_report)
            plugins = plugins | loadorder_plugins
        else:
            log_plugins, plugin_limit, limit_check_disabled = self.plugin_analyzer.loadorder_scan_log(
                segment_plugins, game_version, version_current
            )
            plugins = plugins | log_plugins
            trigger_plugin_limit = plugin_limit
            trigger_limit_check_disabled = limit_check_disabled

        # Extract FormIDs if analyzer available
        if self._async_formid_analyzer:
            formids_matches = self._async_formid_analyzer.extract_formids(segment_callstack)
            self._last_formids = formids_matches

        return plugins, trigger_plugin_limit, trigger_limit_check_disabled, trigger_plugins_loaded

    def _run_suspect_scanning(self, crashlog_mainerror: str, segment_callstack: list[str], autoscan_report: list[str]) -> None:
        """Run suspect scanning on crash log."""
        # Scan main error for suspects
        self.suspect_scanner.suspect_scan_mainerror(autoscan_report, crashlog_mainerror, 50)

        # Scan call stack for suspects (convert list to string)
        segment_callstack_intact = "\n".join(segment_callstack)
        self.suspect_scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, autoscan_report, 50)

        # Check for DLL crashes
        self.suspect_scanner.check_dll_crash(crashlog_mainerror, autoscan_report)

    def _check_fcx_and_settings(
        self,
        xsemodules: set[str],
        crashgen: dict[str, bool | int | str],
        crashlog_crashgen: str,
        trigger_plugin_limit: bool,
        trigger_limit_check_disabled: bool,
        trigger_plugins_loaded: bool,
        autoscan_report: list[str],
    ) -> None:
        """Check FCX mode and scan settings."""
        # Check FCX mode
        self.fcx_handler.check_fcx_mode()
        self.fcx_handler.get_fcx_messages(autoscan_report)

        # Scan basic settings - simplified for now
        # TODO: Implement proper settings scanning with required mod detection
        self.settings_scanner.scan_buffout_achievements_setting(autoscan_report, xsemodules, crashgen)
        self.settings_scanner.scan_archivelimit_setting(autoscan_report, crashgen)
        self.settings_scanner.scan_buffout_looksmenu_setting(crashgen, autoscan_report, xsemodules)

    def _scan_specific_suspects(self, segment_callstack: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """Scan for specific suspects in crash log."""
        # This method appears to be redundant with _run_suspect_scanning
        # Left as a placeholder for potential future specific suspect scanning

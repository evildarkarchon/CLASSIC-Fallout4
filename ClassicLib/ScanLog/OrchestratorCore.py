"""
Fragment-based async-first core implementation for scan orchestration.

This module provides the refactored async implementation for crash log orchestration,
using immutable fragments throughout instead of mutable lists.
"""

import asyncio
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from packaging.version import Version

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool, write_file_async
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore
from ClassicLib.ScanLog.GPUDetector import get_gpu_info
from ClassicLib.ScanLog.Parser import extract_module_names, find_segments
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.RecordScanner import RecordScanner
from ClassicLib.ScanLog.ReportComposition import ConditionalSection, ReportComposer
from ClassicLib.ScanLog.ReportFragment import ReportFragment
from ClassicLib.ScanLog.ReportGenerator import ReportGeneratorFragments
from ClassicLib.ScanLog.SettingsScanner import SettingsScannerFragments
from ClassicLib.ScanLog.SuspectScanner import SuspectScanner
from ClassicLib.Util import crashgen_version_gen
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache


class OrchestratorCore:
    """Fragment-based async-first core implementation for crash log orchestration."""

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

        # Initialize all modules (using refactored versions where available)
        self.plugin_analyzer = PluginAnalyzer(yamldata)
        self.formid_analyzer = FormIDAnalyzer(yamldata, show_formid_values or False, formid_db_exists)
        self.suspect_scanner = SuspectScanner(yamldata)
        self.record_scanner = RecordScanner(yamldata)
        self.settings_scanner = SettingsScannerFragments(yamldata)
        self.report_generator = ReportGeneratorFragments(yamldata)
        self.fcx_handler = FCXModeHandlerFragments(fcx_mode)

        # Get game info
        self.game_root_name: str | None = yaml_settings(str, YAML.Game, f"Game_{GlobalRegistry.get_vr()}Info.Main_Root_Name")

        # Async-specific attributes
        self._db_pool: AsyncDatabasePool | None = None
        self._async_formid_analyzer: FormIDAnalyzerCore | None = None
        self._state_lock: Any = None  # asyncio.Lock - initialized in __aenter__

        # Store last FormIDs and plugins for async processing
        self._last_formids: list[str] = []
        self._last_plugins: dict[str, str] = {}

    async def __aenter__(self) -> "OrchestratorCore":
        """Async context manager entry."""
        # Initialize asyncio.Lock
        self._state_lock = asyncio.Lock()

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
        Fragment-based async implementation for processing a crash log file.

        Args:
            crashlog_file: Path to the crash log file to be processed

        Returns:
            Tuple containing:
            - Path of the crash log file
            - Generated report as list of strings (converted from fragments)
            - Boolean indicating if the scan failed
            - Counter with local statistics
        """
        trigger_scan_failed = False
        local_stats: Counter[str] = Counter(scanned=1, incomplete=0, failed=0)

        # Read crash data
        crash_data: list[str] = self.crashlogs.read_log(crashlog_file.name)

        # Create report composer
        composer = ReportComposer()

        # Generate report header
        composer.add(self.report_generator.generate_header(crashlog_file.name))

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

        # Process crash log sections and compose fragments
        section_fragments = await self._process_log_sections_async(
            crashlog_gameversion,
            crashlog_crashgen,
            crashlog_mainerror,
            segment_crashgen,
            segment_system,
            segment_callstack,
            segment_xsemodules,
            segment_plugins,
        )

        composer.add(section_fragments)

        # Generate footer
        composer.add(self.report_generator.generate_footer())

        # Convert final composed fragment to list
        autoscan_report = composer.to_list()

        return crashlog_file, autoscan_report, trigger_scan_failed, local_stats

    async def _process_log_sections_async(  # noqa: PLR0913
        self,
        crashlog_gameversion: str,
        crashlog_crashgen: str,
        crashlog_mainerror: str,
        segment_crashgen: list[str],
        segment_system: list[str],
        segment_callstack: list[str],
        segment_xsemodules: list[str],
        segment_plugins: list[str],
    ) -> ReportFragment:
        """Process all sections of the crash log asynchronously and return composed fragment."""
        composer = ReportComposer()

        # Version checking
        game_version: Version = crashgen_version_gen(crashlog_gameversion)
        version_current: Version = crashgen_version_gen(crashlog_crashgen)
        version_latest: Version = crashgen_version_gen(self.yamldata.crashgen_latest_og)
        version_latest_vr: Version = crashgen_version_gen(self.yamldata.crashgen_latest_vr)

        # Generate error section
        composer.add(
            self.report_generator.generate_error_section(
                crashlog_mainerror, crashlog_crashgen, version_current, version_latest, version_latest_vr
            )
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
            segment_plugins, segment_callstack, game_version, version_current
        )

        # Store for async FormID processing
        async with self._state_lock:
            self._last_plugins = crashlog_plugins.copy()

        # Run suspect scanning
        suspect_fragments = self._run_suspect_scanning(crashlog_mainerror, segment_callstack)
        composer.add(suspect_fragments)

        # Check FCX mode and settings
        fcx_and_settings_fragments = self._check_fcx_and_settings(
            xsemodules,
            crashgen,
            version_current,
        )
        composer.add(fcx_and_settings_fragments)

        # Run mod detection with async FormID analysis if available
        mod_detection_fragments = await self._run_mod_detection_async(
            crashlog_plugins, segment_callstack, trigger_plugins_loaded, crashlog_gpu_rival
        )
        composer.add(mod_detection_fragments)

        # Scan for specific suspects (named records)
        record_fragments = self._scan_specific_suspects(segment_callstack)
        composer.add(record_fragments)

        return composer.build()

    async def _run_mod_detection_async(
        self,
        crashlog_plugins: dict[str, str],
        segment_callstack: list[str],
        trigger_plugins_loaded: bool,
        crashlog_gpu_rival: Literal["nvidia", "amd"] | None,
    ) -> ReportFragment:
        """Run mod detection with async FormID analysis and return composed fragments."""
        from ClassicLib.ScanLog.DetectMods import detect_mods_double, detect_mods_important, detect_mods_single

        composer = ReportComposer()

        # Run mod detection based on plugins loaded status
        if trigger_plugins_loaded:
            # Check for conflicting mods with conditional header
            conflict_fragment = ConditionalSection.with_header(
                lambda: detect_mods_double(self.yamldata.game_mods_conf, crashlog_plugins), "CONFLICT (TOGETHER)"
            )
            composer.add(conflict_fragment)

            # Check for frequently problematic mods with conditional header
            freq_fragment = ConditionalSection.with_header(
                lambda: detect_mods_single(self.yamldata.game_mods_freq, crashlog_plugins), "FREQUENTLY CRASH"
            )
            composer.add(freq_fragment)

            # Check for mods with known solutions with conditional header
            solution_fragment = ConditionalSection.with_header(
                lambda: detect_mods_single(self.yamldata.game_mods_solu, crashlog_plugins), "HAVE SOLUTIONS"
            )
            composer.add(solution_fragment)

            # Check FOLON-specific mods if Fallout: London is loaded
            is_folon_loaded = any("londonworldspace.esm" in plugin_name.lower() for plugin_name in crashlog_plugins)
            if is_folon_loaded and self.yamldata.game_mods_core_folon:
                important_fragment = detect_mods_important(self.yamldata.game_mods_core_folon, crashlog_plugins, crashlog_gpu_rival)
            else:
                # Check for important core mods with GPU considerations
                important_fragment = detect_mods_important(self.yamldata.game_mods_core, crashlog_plugins, crashlog_gpu_rival)
            composer.add(important_fragment)

            # Check for OPC2 mods with conditional header
            opc2_fragment = ConditionalSection.with_header(
                lambda: detect_mods_single(self.yamldata.game_mods_opc2, crashlog_plugins),
                "ARE OUTDATED, REDUNDANT, OR HAVE COMMUNITY PATCHES",
            )
            composer.add(opc2_fragment)

        # Plugin suspect scanning (plugins found in crash stack)
        if trigger_plugins_loaded and crashlog_plugins:
            # Convert callstack to lowercase for matching
            segment_callstack_lower = [line.lower() for line in segment_callstack]
            # Convert plugins to lowercase set for matching
            crashlog_plugins_lower = {plugin.lower() for plugin in crashlog_plugins}

            # Run plugin matching and add with conditional header
            plugin_fragment = ConditionalSection.with_header(
                lambda: self.plugin_analyzer.plugin_match(segment_callstack_lower, crashlog_plugins_lower),
                header_text=None,  # plugin_match has its own header logic
                header_generator=lambda: self.report_generator.generate_plugin_suspect_header(),
            )
            composer.add(plugin_fragment)

        # Use async FormID analyzer if available
        if self._async_formid_analyzer and self._last_formids:
            # Add FormID section header and results
            composer.add(self.report_generator.generate_formid_section_header())
            formid_fragment = await self._async_formid_analyzer.formid_match(self._last_formids, crashlog_plugins)
            composer.add(formid_fragment)

        return composer.build()

    def _run_suspect_scanning(self, crashlog_mainerror: str, segment_callstack: list[str]) -> ReportFragment:
        """Run suspect scanning on crash log and return composed fragments."""
        composer = ReportComposer()

        # Add suspect section header
        composer.add(self.report_generator.generate_suspect_section_header())

        # Scan main error for suspects
        main_error_fragment, found_main_suspect = self.suspect_scanner.suspect_scan_mainerror(crashlog_mainerror, 50)
        composer.add(main_error_fragment)

        # Scan call stack for suspects
        segment_callstack_intact = "\n".join(segment_callstack)
        stack_fragment, found_stack_suspect = self.suspect_scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, 50)
        composer.add(stack_fragment)

        # Check for DLL crashes
        dll_fragment = self.suspect_scanner.check_dll_crash(crashlog_mainerror)
        composer.add(dll_fragment)

        # Add suspect footer based on whether any suspects were found
        found_suspect = found_main_suspect or found_stack_suspect
        composer.add(self.report_generator.generate_suspect_found_footer(found_suspect))

        return composer.build()

    def _check_fcx_and_settings(
        self,
        xsemodules: set[str],
        crashgen: dict[str, bool | int | str],
        crashgen_version: Version,
    ) -> ReportFragment:
        """Check FCX mode and scan settings, return composed fragments."""
        composer = ReportComposer()

        # Check FCX mode
        self.fcx_handler.check_fcx_mode()
        composer.add(self.fcx_handler.get_fcx_messages())

        # Add settings section header
        composer.add(self.report_generator.generate_settings_section_header())

        # Scan settings with required mod detection
        # Check for X-Cell and Baka ScrapHeap mods for memory management settings
        has_xcell = "x-cell-fo4.dll" in xsemodules or "x-cell-og.dll" in xsemodules or "x-cell-ng2.dll" in xsemodules
        has_old_xcell = "x-cell-fo4.dll" in xsemodules
        has_baka_scrapheap = "bakascrapheap.dll" in xsemodules

        # Scan all settings
        composer.add(self.settings_scanner.scan_buffout_achievements_setting(xsemodules, crashgen))
        composer.add(self.settings_scanner.scan_buffout_memorymanagement_settings(crashgen, has_xcell, has_old_xcell, has_baka_scrapheap))
        composer.add(self.settings_scanner.scan_archivelimit_setting(crashgen, crashgen_version))
        composer.add(self.settings_scanner.scan_buffout_looksmenu_setting(crashgen, xsemodules))

        return composer.build()

    def _scan_specific_suspects(self, segment_callstack: list[str]) -> ReportFragment:
        """Scan for named records in crash log and return composed fragments."""
        composer = ReportComposer()

        # Add section header
        composer.add(self.report_generator.generate_record_section_header())

        # Scan for named records
        record_fragment, records_matches = self.record_scanner.scan_named_records(segment_callstack)
        composer.add(record_fragment)

        return composer.build()

    def _process_plugins(
        self,
        segment_plugins: list[str],
        segment_callstack: list[str],
        game_version: Version,
        version_current: Version,
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
            loadorder_plugins, trigger_plugins_loaded, _loadorder_fragment = self.plugin_analyzer.loadorder_scan_loadorder_txt()
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

    @staticmethod
    async def write_reports_batch(reports: list[tuple[Path, list[str], bool]]) -> None:
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

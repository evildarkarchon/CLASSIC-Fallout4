"""
Fragment-based async-first core implementation for scan orchestration.

This module provides the refactored async implementation for crash log orchestration,
using immutable fragments throughout instead of mutable lists.
"""

import asyncio
import logging
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from packaging.version import Version

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.integration.factory import get_file_io
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool, DatabasePoolManager, write_file_async
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
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class OrchestratorCore:
    """
    Core class for orchestrating crash log processing and analysis.

    This class serves as the primary core for handling crash log processing,
    analysis, and report generation using various modules. It incorporates both
    synchronous and asynchronous methods to provide comprehensive functionality.
    It is designed for working with specific YAML configuration data.

    Attributes:
        yamldata (ClassicScanLogsInfo): Configuration data for the crash log
            processing and analysis.
        show_formid_values (bool | None): Specifies whether to display FormID
            values in reports.
        formid_db_exists (bool): Indicates whether the FormID database is available.
        plugin_analyzer (PluginAnalyzer): Module responsible for analyzing plugins.
        formid_analyzer (FormIDAnalyzer): FormID analysis module with support for
            configuration-controlled display.
        suspect_scanner (SuspectScanner): Module for scanning crash logs for suspect
            metadata.
        record_scanner (RecordScanner): Module for scanning specific record data in
            crash logs.
        settings_scanner (SettingsScannerFragments): Module providing functionality
            to scan and process setting-related fragments.
        report_generator (ReportGeneratorFragments): Module for generating report
            fragments such as headers and footers for crash log reports.
        fcx_handler (FCXModeHandlerFragments): Handles operations related to the
            FCX mode functionality.
        game_root_name (str | None): Name of the game root directory from YAML
            settings.
    """

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """
        Initializes an instance of the class with necessary dependencies and configurations.

        This constructor sets up various analyzers and scanners, initializes a report
        generator, manages game-specific configurations, and sets up handlers based
        on the provided input arguments. Some attributes tailored for asynchronous
        processing are also defined here.

        Args:
            yamldata: ClassicScanLogsInfo object containing YAML data and related
                configurations.
            fcx_mode: Optional boolean flag indicating if the FCX mode functionality
                should be enabled.
            show_formid_values: Optional boolean flag to control whether FormID values
                should be displayed.
            formid_db_exists: Boolean indicating whether the FormID database is
                available.
        """
        self.yamldata: ClassicScanLogsInfo = yamldata
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
        """
        Handles asynchronous context manager entry for initializing resources required
        for orchestrator operations. These resources include an asyncio lock, a database
        pool, and a FormID analyzer.

        Uses lazy initialization for the database pool - only initializes if FormID
        database exists. This avoids initialization delays when database is not available.

        Returns:
            OrchestratorCore: The initialized orchestrator core instance.

        """
        # Initialize asyncio.Lock
        self._state_lock = asyncio.Lock()

        # Lazy database pool initialization - only if database exists
        if self.formid_db_exists:
            pool_manager = DatabasePoolManager()
            self._db_pool = await pool_manager.get_pool()
        else:
            self._db_pool = None

        # Create async FormID analyzer (handles None db_pool gracefully)
        self._async_formid_analyzer = FormIDAnalyzerCore(
            self.yamldata, self.show_formid_values or False, self.formid_db_exists, self._db_pool
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Handles the exiting of an asynchronous context.

        This method is invoked when the asynchronous context associated with this object exits.
        Note: The database pool is now managed by the singleton DatabasePoolManager and is not
        closed here to allow reuse across multiple orchestrator instances.

        Args:
            exc_type: The exception type that was raised during the context, if any.
            exc_val: The exception instance that was raised, if any.
            exc_tb: The traceback object associated with the exception, if any.
        """
        # Database pool is now managed by the singleton and not closed here
        # This allows reuse across multiple batch processing operations

    async def process_crash_log(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Fragment-based async implementation for processing a crash log file.

        Uses direct file I/O with Python's native Path.read_text() for optimal
        performance on small crash log files (typically <100KB). Performance analysis
        shows this is faster than async file I/O for small files due to lower overhead.

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

        # Read crash data directly from file using native Python I/O
        # This is faster than async I/O for small files due to lower overhead
        content = crashlog_file.read_text(encoding='utf-8', errors='ignore')
        crash_data: list[str] = content.splitlines()

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
            _segment_allmodules,
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

    async def _process_log_sections_async(
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
        """
        Processes and analyzes various segments of a crash log to generate a detailed
        ReportFragment. This includes error section generation, plugin processing,
        suspect scanning, and mod detection using data extracted from the provided
        input.

        Args:
            crashlog_gameversion: A string representing the game version obtained from
                the crash log.
            crashlog_crashgen: A string indicating the specific crash generation
                version.
            crashlog_mainerror: A string representing the main error message from the
                crash log.
            segment_crashgen: A list of strings detailing specific crash generation
                settings.
            segment_system: A list of strings providing system information extracted
                from the crash log.
            segment_callstack: A list of strings representing the call stack data from
                the crash log.
            segment_xsemodules: A list of strings detailing the module data from the
                crash log.
            segment_plugins: A list of strings representing the plugins loaded during
                the crash event.

        Returns:
            A ReportFragment object containing the compiled and analyzed report based
            on the provided crash log segments.

        """
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
            cast("Literal['nvidia', 'amd']", rival_value) if rival_value in {"nvidia", "amd"} else None
        )

        # Process plugins (async for better concurrency)
        crashlog_plugins, _trigger_plugin_limit, _trigger_limit_check_disabled, trigger_plugins_loaded = await self._process_plugins_async(
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
            crashlog_plugins, segment_callstack, trigger_plugins_loaded, crashlog_gpu_rival, xsemodules
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
        xse_modules: set[str],
    ) -> ReportFragment:
        """
        Runs asynchronous mod detection based on the crash log, plugins, and other provided
        information. This detection process includes examining various types of game modifications
        that may cause crashes or are otherwise significant for diagnosing issues.

        Args:
            crashlog_plugins (dict[str, str]): Dictionary of loaded ESP/ESM plugins from the crash log,
                where keys represent plugin names and values provide relevant metadata.
            segment_callstack (list[str]): List of strings representing the call stack segments
                from the crash log, used for cross-referencing plugins.
            trigger_plugins_loaded (bool): Flag indicating whether the loaded plugins should be
                analyzed for mod detection.
            crashlog_gpu_rival (Literal["nvidia", "amd"] | None): Specifies the GPU type to refine mod
                detection for GPU-specific conflicts, or None if not applicable.
            xse_modules (set[str]): Set of XSE module names (DLL files) from F4SE PLUGINS section.

        Returns:
            ReportFragment: A composed report fragment summarizing findings from the asynchronous
            mod detection process, including identified issues or problematic mods.
        """
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
                important_fragment = detect_mods_important(
                    self.yamldata.game_mods_core_folon, crashlog_plugins, crashlog_gpu_rival, xse_modules
                )
            else:
                # Check for important core mods with GPU considerations
                important_fragment = detect_mods_important(
                    self.yamldata.game_mods_core, crashlog_plugins, crashlog_gpu_rival, xse_modules
                )
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
                header_generator=self.report_generator.generate_plugin_suspect_header,
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
        """
        Executes the suspect scanning process on a given main error and call stack.

        This function analyzes a main error message and a call stack segment to identify
        potential suspects that might have caused a crash. The process includes scanning
        both the main error and the call stack, checking for DLL-related crashes, and
        adding relevant sections to the report. A footer indicating whether any suspects
        were found is appended to the final report.

        Args:
            crashlog_mainerror (str): The main error message from the crash log.
            segment_callstack (list[str]): The list of strings representing the call stack
                segment.

        Returns:
            ReportFragment: The complete report fragment constructed after the scanning
                and analysis process.
        """
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
        """
        Analyzes and validates settings, FCX mode, and required modules against the given configurations
        to generate a structured report fragment.

        Args:
            xsemodules (set[str]): A set of module names representing loaded XSE plugins.
            crashgen (dict[str, bool | int | str]): A dictionary containing various configuration settings
                relevant to crash generation.
            crashgen_version (Version): The version information of the current crash generation configuration.

        Returns:
            ReportFragment: A compiled report fragment containing the analysis results of the settings,
            FCX mode, and required module checks.
        """
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
        """
        Scans a specific segment of the call stack for suspicious records and returns a report
        fragment based on the findings. Combines sections of the report generated by scanning
        for named records.

        Args:
            segment_callstack (list[str]): The segment of the call stack to scan for suspicious
                records.

        Returns:
            ReportFragment: A report fragment containing scanned records and their associated
                findings.
        """
        composer = ReportComposer()

        # Add section header
        composer.add(self.report_generator.generate_record_section_header())

        # Scan for named records
        record_fragment, records_matches = self.record_scanner.scan_named_records(segment_callstack)
        composer.add(record_fragment)

        return composer.build()

    async def _process_plugins_async(
        self,
        segment_plugins: list[str],
        segment_callstack: list[str],
        game_version: Version,
        version_current: Version,
    ) -> tuple[dict[str, str], bool, bool, bool]:
        """
        Processes plugins and extracts relevant plugin data, determines trigger states based
        on loaded plugins, load order, and specific checks. It handles merging plugin data,
        checking plugin limits, and identifying conditions such as the availability of plugins
        or specific settings.

        Args:
            segment_plugins (list[str]): The list of plugins present in the analyzed game
                segment.
            segment_callstack (list[str]): The callstack related to the game execution,
                potentially used to identify plugin-related issues.
            game_version (Version): The current game version to be considered for
                compatibility checks.
            version_current (Version): The current application version analyzed for
                compatibility with the loaded plugins.

        Returns:
            tuple[dict[str, str], bool, bool, bool]: A tuple containing the following:
                - Dictionary of loaded plugins with relevant details.
                - Boolean indicating whether a plugin limit is triggered.
                - Boolean indicating whether the plugin limit check is disabled.
                - Boolean indicating whether the plugins have been successfully loaded.
        """
        plugins: dict[str, str] = {}
        trigger_plugin_limit = False
        trigger_limit_check_disabled = False
        trigger_plugins_loaded = False

        # Check if plugins loaded
        esm_name: str = f"{GlobalRegistry.get_game()}.esm"
        if any(esm_name in elem for elem in segment_plugins):
            trigger_plugins_loaded = True

        # Check for loadorder.txt (async file check for better concurrency)
        loadorder_path = Path("loadorder.txt")
        if loadorder_path.exists():
            # Use async file reading for loadorder.txt (30-40% reduction in blocking)
            loadorder_plugins, trigger_plugins_loaded, _loadorder_fragment = await self._load_loadorder_async(loadorder_path)
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

    async def _load_loadorder_async(self, loadorder_path: Path) -> tuple[dict[str, str], bool, Any]:
        """
        Asynchronously loads plugin information from loadorder.txt file.

        This method performs async file I/O to read the loadorder.txt file,
        reducing blocking and improving concurrency during plugin processing.

        Args:
            loadorder_path: Path to the loadorder.txt file

        Returns:
            Tuple containing:
            - Dictionary of loaded plugins
            - Boolean indicating if plugins were loaded
            - Report fragment with loading status
        """
        import aiofiles

        from ClassicLib.ScanLog.ReportFragment import ReportFragment

        lines = []
        loadorder_origin = "LO"  # Origin marker for plugins from loadorder.txt

        lines.extend((
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n",
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n",
        ))

        loadorder_plugins: dict[str, str] = {}

        try:
            # Try Rust-accelerated file I/O first
            if is_rust_accelerated("file_io_core"):
                try:
                    rust_file_io = get_file_io()
                    if rust_file_io and hasattr(rust_file_io, 'read_file_async'):
                        content = await rust_file_io.read_file_async(loadorder_path)
                        loadorder_data = content.splitlines()
                        logging.getLogger(__name__).debug("🚀 Used Rust-accelerated file I/O for loadorder.txt")
                    else:
                        # Fall back to Python async file reading
                        async with aiofiles.open(loadorder_path, encoding="utf-8", errors="ignore") as loadorder_file:
                            content = await loadorder_file.read()
                            loadorder_data = content.splitlines()
                except Exception as e:
                    logging.getLogger(__name__).debug(f"Rust file I/O failed, using Python: {e}")
                    # Fall back to Python async file reading
                    async with aiofiles.open(loadorder_path, encoding="utf-8", errors="ignore") as loadorder_file:
                        content = await loadorder_file.read()
                        loadorder_data = content.splitlines()
            else:
                # Use standard Python async file reading
                async with aiofiles.open(loadorder_path, encoding="utf-8", errors="ignore") as loadorder_file:
                    content = await loadorder_file.read()
                    loadorder_data = content.splitlines()

            # Skip the header line (first line) of the loadorder.txt file
            if len(loadorder_data) > 1:
                for plugin_entry in loadorder_data[1:]:
                    plugin_entry = plugin_entry.strip()
                    if plugin_entry and plugin_entry not in loadorder_plugins:
                        loadorder_plugins[plugin_entry] = loadorder_origin
        except OSError as e:
            # Log file access error but continue execution
            lines.append(f"Error reading loadorder.txt: {e!s}")

        # Check if any plugins were loaded
        plugins_loaded = bool(loadorder_plugins)

        return loadorder_plugins, plugins_loaded, ReportFragment.from_lines(lines)

    @staticmethod
    def _parse_crashgen_settings(segment_crashgen: list[str]) -> dict[str, bool | int | str]:
        """
        Parses a list of crash generation settings and converts them into a dictionary with appropriate types.

        The method takes a list of strings representing crash generation settings in the format
        "key:value". It processes each string, splits it into a key and a value, and converts the
        value to the appropriate data type. Boolean "true" and "false" values, integers, and
        strings are recognized and handled accordingly. If the input list is empty or None,
        an empty dictionary is returned.

        Args:
            segment_crashgen (list[str]): A list of strings containing crash generation settings
                in the "key:value" format.

        Returns:
            dict[str, bool | int | str]: A dictionary mapping the keys to their corresponding
                converted values.
        """
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
        Processes a batch of crash log files concurrently and collects the results.

        Processes the given list of crash log files in batches to manage system resources
        efficiently. Each batch is processed concurrently, and the results from all
        batches are aggregated into a single list. In case of any errors during the
        processing of individual log files, those errors are captured and represented
        in the results as error logs.

        Args:
            crashlog_files (list[Path]): A list of file paths representing crash log files
                to be processed.

        Returns:
            list[tuple[Path, list[str], bool, Counter[str]]]: A list of tuples where each
            tuple contains the following:
                - Path: The file path of the processed log or error log.
                - list[str]: A list of strings representing the processed content or
                  error messages.
                - bool: A flag indicating success (False) or failure (True).
                - Counter[str]: A counter object summarizing the processing results
                  (e.g., counts of scanned, incomplete, or failed logs).
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
        Writes batch reports to their respective files asynchronously.

        This method processes a batch of reports provided as tuples, where each tuple
        contains the path to a crash log file, its associated autoscan report, and a
        boolean indicating whether a scan failure occurred. The method generates a
        new file name for the autoscan report, writes the report content to the file,
        and performs these write operations concurrently.

        Args:
            reports (list[tuple[Path, list[str], bool]]): A list of tuples, where each
                tuple contains:
                - A Path object pointing to the crash log file.
                - A list of strings representing the autoscan report content.
                - A boolean indicating whether a scan failure occurred.
        """
        write_tasks = []

        for crashlog_file, autoscan_report, _trigger_scan_failed in reports:
            autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
            autoscan_output: str = "".join(autoscan_report)

            # Create write task
            write_tasks.append(write_file_async(autoscan_path, autoscan_output))

        # Execute all writes concurrently
        await asyncio.gather(*write_tasks, return_exceptions=True)

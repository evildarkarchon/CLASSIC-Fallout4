"""
Scan orchestrator module for CLASSIC.

This module coordinates all crash log scanning components:
- Managing the scanning workflow
- Coordinating between analyzer modules
- Handling statistics tracking
- Providing high-level API for crash log processing
"""

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from packaging.version import Version

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandler
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.GPUDetector import get_gpu_info
from ClassicLib.ScanLog.Parser import extract_module_names, find_segments
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.RecordScanner import RecordScanner
from ClassicLib.ScanLog.ReportGenerator import ReportGenerator
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.SettingsScanner import SettingsScanner
from ClassicLib.ScanLog.SuspectScanner import SuspectScanner
from ClassicLib.Util import append_or_extend, crashgen_version_gen
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache


class ScanOrchestrator:
    """Orchestrates all crash log scanning components."""

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        crashlogs: "ThreadSafeLogCache",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """
        Initialize the scan orchestrator.

        Args:
            yamldata: Configuration data
            crashlogs: Thread-safe log cache
            fcx_mode: Whether FCX mode is enabled
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
        """
        self.yamldata: ClassicScanLogsInfo = yamldata
        self.crashlogs: ThreadSafeLogCache = crashlogs

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

    def process_crash_log(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Processes a crash log file to extract data, generate a report, and update local statistics. Checks for incomplete or
        failed logs and handles their processing accordingly.

        Parameters:
        crashlog_file (Path): Path to the crash log file to be processed.

        Returns:
        tuple[Path, list[str], bool, Counter[str]]: A tuple containing the path of the crash log file, the generated report as
        a list of strings, a boolean indicating if the scan failed, and a Counter object containing local statistics related to
        the scanning process.
        """
        autoscan_report: list[str] = []
        trigger_scan_failed = False
        local_stats: Counter[str] = Counter(scanned=1, incomplete=0, failed=0)

        # Read crash data
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

        # Process crash log
        self._process_log_sections(
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

    def _process_log_sections(  # noqa: PLR0913
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
        """Process all sections of the crash log."""
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
        # Ensure type compatibility for mod detection
        crashlog_gpu_rival: Literal["nvidia", "amd"] | None = (
            cast("Literal['nvidia', 'amd']", rival_value) if rival_value in ("nvidia", "amd") else None
        )

        # Process plugins
        crashlog_plugins, trigger_plugin_limit, trigger_limit_check_disabled, trigger_plugins_loaded = self._process_plugins(
            segment_plugins, segment_allmodules, game_version, version_current, xsemodules, autoscan_report
        )

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

        # Run mod detection
        self._run_mod_detection(crashlog_plugins, trigger_plugins_loaded, crashlog_gpu_rival, autoscan_report)

        # Scan for specific suspects
        self._scan_specific_suspects(segment_callstack, crashlog_plugins, autoscan_report)

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

        # Add XSE modules as DLLs
        # Convert to set for O(1) lookups instead of O(n*m) nested loops
        existing_plugin_names = set(plugins.keys())
        for elem in xsemodules:
            # Check if elem is a substring of any existing plugin
            if not any(elem in plugin_name for plugin_name in existing_plugin_names):
                plugins[elem] = "DLL"

        # Add vulkan if found
        for elem in segment_allmodules if segment_allmodules else []:
            if "vulkan" in elem.lower():
                elem_parts: list[str] = elem.strip().split(" ", 1)
                plugins.update({elem_parts[0]: "DLL"})

        # Filter ignored plugins
        plugins = self.plugin_analyzer.filter_ignored_plugins(plugins)

        return plugins, trigger_plugin_limit, trigger_limit_check_disabled, trigger_plugins_loaded

    def _run_suspect_scanning(self, crashlog_mainerror: str, segment_callstack: list[str], autoscan_report: list[str]) -> None:
        """Run suspect scanning on crash log."""
        self.report_generator.generate_suspect_section_header(autoscan_report)

        # Check for DLL crash
        self.suspect_scanner.check_dll_crash(crashlog_mainerror, autoscan_report)

        # Scan for suspects
        segment_callstack_intact: str = "".join(segment_callstack)
        max_warn_length = 30

        trigger_suspect_found = any((
            self.suspect_scanner.suspect_scan_mainerror(autoscan_report, crashlog_mainerror, max_warn_length),
            self.suspect_scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, autoscan_report, max_warn_length),
        ))

        self.report_generator.generate_suspect_found_footer(trigger_suspect_found, autoscan_report)

    def _run_mod_detection(
        self,
        crashlog_plugins: dict[str, str],
        trigger_plugins_loaded: bool,
        crashlog_gpu_rival: Literal["nvidia", "amd"] | None,
        autoscan_report: list[str],
    ) -> None:
        """Run mod detection checks."""
        # Import at runtime to avoid circular imports
        from ClassicLib.ScanLog.DetectMods import detect_mods_double, detect_mods_important, detect_mods_single

        # Check for frequent crash mods
        self.report_generator.generate_mod_check_header("CAN CAUSE FREQUENT CRASHES", autoscan_report)
        if trigger_plugins_loaded:
            detect_mods_single(self.yamldata.game_mods_freq, crashlog_plugins, autoscan_report)
        else:
            append_or_extend(self.report_generator.generate_plugins_loading_failure_message(), autoscan_report)

        # Check for conflicting mods
        self.report_generator.generate_mod_check_header("CONFLICT WITH OTHER MODS", autoscan_report)
        if trigger_plugins_loaded:
            if detect_mods_double(self.yamldata.game_mods_conf, crashlog_plugins, autoscan_report):
                append_or_extend(
                    (
                        "# [!] CAUTION : FOUND MODS THAT ARE INCOMPATIBLE OR CONFLICT WITH YOUR OTHER MODS # \n",
                        "* YOU SHOULD CHOOSE WHICH MOD TO KEEP AND DISABLE OR COMPLETELY REMOVE THE OTHER MOD * \n\n",
                    ),
                    autoscan_report,
                )
            else:
                append_or_extend("# FOUND NO MODS THAT ARE INCOMPATIBLE OR CONFLICT WITH YOUR OTHER MODS # \n\n", autoscan_report)
        else:
            append_or_extend(self.yamldata.warn_noplugins, autoscan_report)

        # Check for mods with solutions
        self.report_generator.generate_mod_check_header("HAVE SOLUTIONS & COMMUNITY PATCHES", autoscan_report)
        if trigger_plugins_loaded:
            if detect_mods_single(self.yamldata.game_mods_solu, crashlog_plugins, autoscan_report):
                append_or_extend(
                    (
                        "# [!] CAUTION : FOUND PROBLEMATIC MODS WITH SOLUTIONS AND COMMUNITY PATCHES # \n",
                        "[Due to limitations, CLASSIC will show warnings for some mods even if fixes or patches are already installed.] \n",
                        "[To hide these warnings, you can add their plugin names to the CLASSIC Ignore.yaml file. ONE PLUGIN PER LINE.] \n\n",
                    ),
                    autoscan_report,
                )
            else:
                append_or_extend("# FOUND NO PROBLEMATIC MODS WITH AVAILABLE SOLUTIONS AND COMMUNITY PATCHES # \n\n", autoscan_report)
        else:
            append_or_extend(self.yamldata.warn_noplugins, autoscan_report)

        # Check OPC mods (Fallout 4 only)
        if GlobalRegistry.get_game() == "Fallout4":
            self.report_generator.generate_mod_check_header("ARE PATCHED THROUGH OPC INSTALLER", autoscan_report)
            if trigger_plugins_loaded:
                if detect_mods_single(self.yamldata.game_mods_opc2, crashlog_plugins, autoscan_report):
                    append_or_extend(
                        (
                            "\n* FOR PATCH REPOSITORY THAT PREVENTS CRASHES AND FIXES PROBLEMS IN THESE AND OTHER MODS,* \n",
                            "* VISIT OPTIMIZATION PATCHES COLLECTION: https://www.nexusmods.com/fallout4/mods/54872 * \n\n",
                        ),
                        autoscan_report,
                    )
                else:
                    append_or_extend(
                        "# FOUND NO PROBLEMATIC MODS THAT ARE ALREADY PATCHED THROUGH THE OPC INSTALLER # \n\n", autoscan_report
                    )
            else:
                append_or_extend(self.yamldata.warn_noplugins, autoscan_report)

        # Check important patches
        self.report_generator.generate_mod_check_header("IF IMPORTANT PATCHES & FIXES ARE INSTALLED", autoscan_report)
        if trigger_plugins_loaded:
            if any("londonworldspace" in plugin.lower() for plugin in crashlog_plugins):
                detect_mods_important(self.yamldata.game_mods_core_folon, crashlog_plugins, autoscan_report, crashlog_gpu_rival)
            else:
                detect_mods_important(self.yamldata.game_mods_core, crashlog_plugins, autoscan_report, crashlog_gpu_rival)
        else:
            append_or_extend(self.yamldata.warn_noplugins, autoscan_report)

    def _check_fcx_and_settings(  # noqa: PLR0913
        self,
        xsemodules: set[str],
        crashgen: dict[str, bool | int | str],
        crashlog_crashgen: str,
        trigger_plugin_limit: bool,
        trigger_limit_check_disabled: bool,
        trigger_plugins_loaded: bool,
        autoscan_report: list[str],
    ) -> None:
        """Check FCX mode and various settings and configurations."""
        # Check FCX mode
        self.fcx_handler.check_fcx_mode()

        # Generate settings header
        self.report_generator.generate_settings_section_header(autoscan_report)
        self.fcx_handler.get_fcx_messages(autoscan_report)
        # Check for X-Cell and Baka ScrapHeap
        has_x_cell = "x-cell-fo4.dll" in xsemodules or "x-cell-og.dll" in xsemodules or "x-cell-ng2.dll" in xsemodules
        has_baka_scrapheap = "bakascrapheap.dll" in xsemodules

        # Update ignore list if needed
        if has_x_cell:
            self.yamldata.crashgen_ignore.update(("MemoryManager", "HavokMemorySystem", "ScaleformAllocator", "SmallBlockAllocator"))
        elif has_baka_scrapheap:
            self.yamldata.crashgen_ignore.add("MemoryManager")

        # Check disabled settings
        if crashgen:
            self.settings_scanner.check_disabled_settings(crashgen, autoscan_report, self.yamldata.crashgen_ignore)

            # Check specific settings
            self.settings_scanner.scan_buffout_achievements_setting(autoscan_report, xsemodules, crashgen)
            self.settings_scanner.scan_buffout_memorymanagement_settings(autoscan_report, crashgen, has_x_cell, has_baka_scrapheap)

            # Check ArchiveLimit
            if crashgen_version_gen(self.yamldata.crashgen_latest_og) <= crashgen_version_gen(crashlog_crashgen) >= Version("1.27.0"):
                self.settings_scanner.scan_archivelimit_setting(autoscan_report, crashgen)

            # Check LooksMenu
            self.settings_scanner.scan_buffout_looksmenu_setting(crashgen, autoscan_report, xsemodules)

        # Check plugin limit
        self.report_generator.generate_plugin_limit_warning(
            trigger_plugin_limit, trigger_limit_check_disabled, trigger_plugins_loaded, autoscan_report
        )

    def _scan_specific_suspects(self, segment_callstack: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """Scan for specific suspects in the crash log."""
        self.report_generator.generate_plugin_suspect_header(autoscan_report)

        # Plugin matching
        segment_callstack_lower = [line.lower() for line in segment_callstack]
        crashlog_plugins_lower = {plugin.lower() for plugin in crashlog_plugins}
        self.plugin_analyzer.plugin_match(segment_callstack_lower, crashlog_plugins_lower, autoscan_report)

        # FormID matching
        self.report_generator.generate_formid_section_header(autoscan_report)
        formids_matches = self.formid_analyzer.extract_formids(segment_callstack)

        # Store FormID data for potential async processing
        self.last_formids = formids_matches
        self.last_plugins = crashlog_plugins

        self.formid_analyzer.formid_match(formids_matches, crashlog_plugins, autoscan_report)

        # Record scanning
        self.report_generator.generate_record_section_header(autoscan_report)
        records_matches: list[str] = []
        self.record_scanner.scan_named_records(segment_callstack, records_matches, autoscan_report)

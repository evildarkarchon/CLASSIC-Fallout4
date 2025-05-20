import os
import random
import shutil
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

import regex as re
from packaging.version import Version

from CLASSIC_Main import initialize, main_combined_result
from CLASSIC_ScanGame import game_combined_result
from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.Util import crashlogs_get_files, crashlogs_reformat, get_entry
from ClassicLib.Util import append_or_extend, crashgen_version_gen
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


# noinspection PyUnresolvedReferences
class ClassicScanLogs:
    _fcx_lock: threading.RLock = threading.RLock()
    _fcx_checks_run: bool = False
    _main_files_result: str = ""
    _game_files_result: str = ""

    def __init__(self) -> None:
        """
        Initializes the class and performs the setup required for crash log scanning and processing.

        This method initializes several attributes and settings required for scanning and
        processing crash log files. It compiles a regex pattern for plugin searches, retrieves
        the list of crash log files, loads settings for excluding certain log records, and
        applies transformations and checks for various conditions. Additionally, it sets up
        the environment necessary to process the crash logs, including loading YAML data,
        checking database states, and preparing to move unsolved logs if required.

        Attributes:
            pluginsearch (regex.Pattern): Compiled regex pattern to search for plugins within the crash logs.
            crashlog_list (list[Path]): List of crash log files to be processed, retrieved using crashlogs_get_files().
            remove_list (tuple[str]): List of log records to exclude, fetched from the YAML settings.
            yamldata (ClassicScanLogsInfo): Instance containing classic scan logs info fetched from YAML.
            xse_acronym (str): Lowercase representation of the XSE acronym from the YAML data.
            fcx_mode (bool): Whether the FCX mode is enabled, fetched from the classic settings.
            show_formid_values (bool): Indicates whether FormID values should be displayed, fetched from classic settings.
            formid_db_exists (bool): True if at least one database exists in the specified DB paths.
            move_unsolved_logs (bool): Whether unsolved logs should be moved, based on classic settings.
            lower_records (set[str]): Set of lowercase record entries from the classic records in the YAML data.
            lower_ignore (set[str]): Set of lowercase game ignore records from the YAML data.
            lower_plugins_ignore (set[str]): Set of lowercase ignore plugins from the YAML data.
            ignore_plugins_list (set[str]): Set of lowercase plugins from the YAML ignore list, if any.
            scan_start_time (float): Timestamp indicating the start time of the scan, in seconds since the epoch.
            crashlogs (ThreadSafeLogCache): SQLiteReader instance initialized with the crash log files.
            main_files_check (str): Placeholder for main files check-related information.
            game_files_check (str): Placeholder for game files check-related information.
            scan_failed_list (list[str]): List of crash log files that failed to scan.
            user_folder (Path): Path to the user's home directory.
            crashlog_stats (Counter): Counter for various statistics of the scan (currently scanned, incomplete, and failed).
        """
        self.pluginsearch = re.compile(
            r"\s*\[(FE:([0-9A-F]{3})|[0-9A-F]{2})\]\s*(.+?(?:\.es[pml])+)",
            flags=re.IGNORECASE,  # pyrefly: ignore
        )
        self.crashlog_list = crashlogs_get_files()
        print("REFORMATTING CRASH LOGS, PLEASE WAIT...\n")
        self.remove_list = yaml_settings(tuple[str], YAML.Main, "exclude_log_records") or ("",)
        crashlogs_reformat(self.crashlog_list, self.remove_list)
        self.yamldata = ClassicScanLogsInfo()
        self.xse_acronym = self.yamldata.xse_acronym.lower()
        self.fcx_mode = classic_settings(bool, "FCX Mode")
        self.show_formid_values = classic_settings(bool, "Show FormID Values")
        self.formid_db_exists = any(db.is_file() for db in DB_PATHS)
        self.move_unsolved_logs = classic_settings(bool, "Move Unsolved Logs")
        self.lower_records = {record.lower() for record in self.yamldata.classic_records_list} or set()
        self.lower_ignore = {record.lower() for record in self.yamldata.game_ignore_records} or set()
        self.lower_plugins_ignore = {ignore.lower() for ignore in self.yamldata.game_ignore_plugins}
        self.ignore_plugins_list = {item.lower() for item in self.yamldata.ignore_list} if self.yamldata.ignore_list else set()
        print("SCANNING CRASH LOGS, PLEASE WAIT...\n")
        self.scan_start_time = time.perf_counter()
        self.crashlogs = ThreadSafeLogCache(self.crashlog_list)
        self.main_files_check = ""
        self.game_files_check = ""
        self.scan_failed_list: list[str] = []
        self.user_folder = Path.home()
        self.crashlog_stats = Counter(scanned=0, incomplete=0, failed=0)
        logger.info(f"- - - INITIATED CRASH LOG FILE SCAN >>> CURRENTLY SCANNING {len(self.crashlog_list)} FILES")

    def close_database(self) -> None:
        """Close the SQLite database."""
        self.crashlogs.close()

    def fcx_mode_check(self) -> None:
        """
        Checks the FCX mode status and performs corresponding file integrity checks.

        If FCX mode is enabled, this method performs integrity checks for the main
        files and game files by invoking the respective methods (but only once per scan session).
        If FCX mode is disabled, it sets the results to indicate that checks are skipped.

        Thread-safe implementation using a lock to ensure multiple threads don't run the
        expensive checks simultaneously.

        Attributes:
            main_files_check (str): The result of the main files check. If FCX mode is
                disabled, it contains a message indicating the check was skipped.
            game_files_check (str): The result of the game files check. If FCX mode is
                disabled, it is set to an empty string.
        """
        if self.fcx_mode:
            # Use a class-level lock to ensure thread safety
            with ClassicScanLogs._fcx_lock:
                # Check if we've already run the FCX checks in this scan session
                if not hasattr(ClassicScanLogs, "_fcx_checks_run") or not ClassicScanLogs._fcx_checks_run:
                    # Run the checks once and store results in class variables
                    ClassicScanLogs._main_files_result = main_combined_result()
                    ClassicScanLogs._game_files_result = game_combined_result()
                    ClassicScanLogs._fcx_checks_run = True

            # Always assign the stored results to instance variables
            self.main_files_check = ClassicScanLogs._main_files_result
            self.game_files_check = ClassicScanLogs._game_files_result
        else:
            self.main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
            self.game_files_check = ""

    # noinspection PyPep8Naming
    def find_segments(self, crash_data: list[str], crashgen_name: str) -> tuple[str, str, str, list[list[str]]]:
        """
        Finds and extracts segments from crash data text and extracts metadata including game version, crash
        generator version, and main error message. This method also processes the segments for whitespace
        trimming and ensures completeness by adding placeholders for any missing segments.

        Args:
            crash_data (list[str]): List of strings representing lines of the crash data.
            crashgen_name (str): Name of the crash generator to be identified in the crash data.

        Returns:
            tuple[str, str, str, list[list[str]]]: A tuple containing the following elements:
                - Game version (str), extracted from the crash data or UNKNOWN if not found.
                - Crash generator version (str), extracted from the crash data or UNKNOWN if not found.
                - Main error message (str), extracted from the crash data or UNKNOWN if not found.
                - Processed segments (list[list[str]]), where each inner list represents a segment with
                  whitespace stripped.
        """
        # Define constants
        UNKNOWN = "UNKNOWN"
        EOF_MARKER = "EOF"

        # Get required information from configuration
        xse = self.yamldata.xse_acronym.upper()
        game_root_name = yaml_settings(str, YAML.Game, f"Game_{GlobalRegistry.get_vr()}Info.Main_Root_Name")

        # Define segment boundaries
        segment_boundaries = [
            ("	[Compatibility]", "SYSTEM SPECS:"),  # segment_crashgen
            ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),  # segment_system
            ("PROBABLE CALL STACK:", "MODULES:"),  # segment_callstack
            ("MODULES:", f"{xse} PLUGINS:"),  # segment_allmodules
            (f"{xse} PLUGINS:", "PLUGINS:"),  # segment_xsemodules
            ("PLUGINS:", EOF_MARKER),  # segment_plugins
        ]

        # Initialize metadata variables
        game_version: str | None = None
        crashgen_version: str | None = None
        main_error: str | None = None

        # Parse segments
        segments = self._extract_segments(crash_data, segment_boundaries, EOF_MARKER)

        # Extract metadata from crash data
        for line in crash_data:
            if game_version is None and game_root_name and line.startswith(game_root_name):
                game_version = line.strip()
            elif crashgen_version is None and line.startswith(crashgen_name):
                crashgen_version = line.strip()
            elif main_error is None and line.startswith("Unhandled exception"):
                main_error = line.replace("|", "\n", 1)

        # Process segments to strip whitespace
        processed_segments = [[line.strip() for line in segment] for segment in segments] if segments else segments

        # Ensure all expected segments exist (add empty lists for missing segments)
        missing_segments_count = len(segment_boundaries) - len(processed_segments)
        if missing_segments_count > 0:
            processed_segments.extend([[]] * missing_segments_count)

        return game_version or UNKNOWN, crashgen_version or UNKNOWN, main_error or UNKNOWN, processed_segments

    @staticmethod
    def _extract_segments(crash_data: list[str], segment_boundaries: list[tuple[str, str]], eof_marker: str) -> list[list[str]]:
        """
        Extract segments from crash data based on defined boundaries.

        Args:
            crash_data: The raw crash report data
            segment_boundaries: List of tuples with (start_marker, end_marker) for each segment
            eof_marker: The marker used to indicate end of file

        Returns:
            A list of segments where each segment is a list of lines
        """
        segments: list[list[str]] = []
        total_lines = len(crash_data)
        current_index = 0
        segment_index = 0
        collecting = False
        segment_start_index = 0
        current_boundary = segment_boundaries[0][0]  # Start with first boundary

        while current_index < total_lines:
            line = crash_data[current_index]

            # Check if we've hit a boundary
            if line.startswith(current_boundary):
                if collecting:
                    # End of current segment
                    segment_end_index = current_index - 1 if current_index > 0 else current_index
                    segments.append(crash_data[segment_start_index:segment_end_index])
                    segment_index += 1

                    # Check if we've processed all segments
                    if segment_index == len(segment_boundaries):
                        break
                else:
                    # Start of a new segment
                    segment_start_index = current_index + 1 if total_lines > current_index else current_index

                # Toggle collection state and update boundary
                collecting = not collecting
                current_boundary = segment_boundaries[segment_index][int(collecting)]

                # Handle special cases
                if collecting and current_boundary == eof_marker:
                    # Add all remaining lines
                    segments.append(crash_data[segment_start_index:])
                    break

                if not collecting:
                    # Don't increment index in case the current line is also the next start boundary
                    current_index -= 1

            # Check if we've reached the end while still collecting
            if collecting and current_index == total_lines - 1:
                segments.append(crash_data[segment_start_index:])

            current_index += 1

        return segments

    # noinspection PyPep8Naming
    @staticmethod
    def loadorder_scan_loadorder_txt(autoscan_report: list[str]) -> tuple[dict[str, str], bool]:
        """
        Processes the "loadorder.txt" file within a specific folder to generate a mapping of plugins
        to their origin and determines if any plugins were successfully loaded.

        This method attempts to read the `loadorder.txt` for plugin entries, processes its content,
        and builds a dictionary mapping plugin names to a specified origin marker. If any issues
        occur during file reading, an error message is appended to the `autoscan_report`. The method
        also determines if the file has at least one valid plugin entry.

        Args:
            autoscan_report (list[str]): A list to which informational or error messages regarding the
                operation will be appended.

        Returns:
            tuple[dict[str, str], bool]: A tuple where the first element is a dictionary mapping
                plugin names to their origin markers, and the second element is a boolean indicating
                whether any plugins were successfully loaded.
        """
        LOADORDER_MESSAGES = (
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n",
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n",
        )
        LOADORDER_ORIGIN = "LO"  # Origin marker for plugins from loadorder.txt
        LOADORDER_PATH = Path("loadorder.txt")

        append_or_extend(LOADORDER_MESSAGES, autoscan_report)

        loadorder_plugins = {}

        try:
            with LOADORDER_PATH.open(encoding="utf-8", errors="ignore") as loadorder_file:
                loadorder_data = loadorder_file.readlines()

            # Skip the header line (first line) of the loadorder.txt file
            if len(loadorder_data) > 1:
                for plugin_entry in loadorder_data[1:]:
                    plugin_entry = plugin_entry.strip()
                    if plugin_entry and plugin_entry not in loadorder_plugins:
                        loadorder_plugins[plugin_entry] = LOADORDER_ORIGIN
        except OSError as e:
            # Log file access error but continue execution
            error_msg = f"Error reading loadorder.txt: {e!s}"
            append_or_extend(error_msg, autoscan_report)

        # Check if any plugins were loaded
        plugins_loaded = bool(loadorder_plugins)

        return loadorder_plugins, plugins_loaded

    # noinspection PyPep8Naming
    def loadorder_scan_log(
        self, segment_plugins: list[str], game_version: Version, version_current: Version
    ) -> tuple[dict[str, str], bool, bool]:
        """
        Analyzes and processes a list of plugins for a given game version, determining specific conditions
        and identifying plugin statuses. Returns a mapping of plugin names to their statuses, alongside
        flags indicating the detection of specific conditions related to plugin limits.

        Args:
            segment_plugins (list[str]): A list of plugin data segments to process.
            game_version (Version): The version of the game for determining behavior.
            version_current (Version): The current version to be compared against thresholds.

        Returns:
            tuple: A tuple containing:
                - dict[str, str]: A mapping of plugin names to their classified statuses.
                - bool: A flag indicating whether a plugin limit marker has been triggered.
                - bool: A flag indicating whether the limit check has been disabled.
        """
        # Early return for empty input
        if not segment_plugins:
            return {}, False, False

        # Constants for plugin status
        PLUGIN_STATUS_DLL = "DLL"
        PLUGIN_STATUS_UNKNOWN = "???"
        PLUGIN_LIMIT_MARKER = "[FF]"

        # Determine game version characteristics
        is_original_game = game_version in (self.yamldata.game_version, self.yamldata.game_version_vr)
        is_new_game_crashgen_pre_137 = game_version >= self.yamldata.game_version_new and version_current < Version("1.37.0")

        # Initialize return values
        plugin_map: dict[str, str] = {}
        plugin_limit_triggered = False
        limit_check_disabled = False

        # Process each plugin entry
        for entry in segment_plugins:
            # Check for plugin limit markers
            if PLUGIN_LIMIT_MARKER in entry:
                if is_original_game:
                    plugin_limit_triggered = True
                elif is_new_game_crashgen_pre_137:
                    limit_check_disabled = True

            # Extract plugin information using regex
            plugin_match: re.Match[str] | None = self.pluginsearch.match(entry, concurrent=True)
            if plugin_match is None:
                continue

            # Extract plugin details
            plugin_id = plugin_match.group(1)
            plugin_name = plugin_match.group(3)

            # Skip if plugin name is empty or already processed
            if not plugin_name or plugin_name in plugin_map:
                continue

            # Classify the plugin
            if plugin_id is not None:
                plugin_map[plugin_name] = plugin_id.replace(":", "")
            elif "dll" in plugin_name.lower():
                plugin_map[plugin_name] = PLUGIN_STATUS_DLL
            else:
                plugin_map[plugin_name] = PLUGIN_STATUS_UNKNOWN

        return plugin_map, plugin_limit_triggered, limit_check_disabled

    def suspect_scan_mainerror(self, autoscan_report: list[str], crashlog_mainerror: str, max_warn_length: int) -> bool:
        """
        Scans for main errors in the autoscan report based on a list of suspect errors and
        signals. Matches errors in the crash log main error with predefined suspect signals
        and adds detailed error information to the autoscan report if a match is found.

        Args:
            autoscan_report (list[str]): A list containing lines of the autoscan report
                where detected errors will be appended.
            crashlog_mainerror (str): A string containing the main error log which is
                checked for suspect signals.
            max_warn_length (int): The maximum allowed length of the warning label in
                the autoscan report.

        Returns:
            bool: True if any suspect error was found in the crash log main error;
                False otherwise.
        """
        found_suspect = False

        for error_key, signal in self.yamldata.suspects_error_list.items():
            # Skip checking if signal not in crash log
            if signal not in crashlog_mainerror:
                continue

            # Parse error information
            error_severity, error_name = error_key.split(" | ", 1)

            # Format the error name for report
            formatted_error_name = error_name.ljust(max_warn_length, ".")

            # Add the error to the report
            report_entry = f"# Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n"
            append_or_extend(report_entry, autoscan_report)

            # Update suspect found status
            found_suspect = True

        return found_suspect

    def suspect_scan_stack(
        self, crashlog_mainerror: str, segment_callstack_intact: str, autoscan_report: list[str], max_warn_length: int
    ) -> bool:
        """
        Scans a crash log's main error and call stack for patterns defined in the suspects
        stack list to identify potential issues and appends relevant findings to the autoscan
        report if any suspects are found.

        The function evaluates signals specified in the suspects stack list, which are categorized
        by modifiers such as "ME-REQ", "ME-OPT", "NOT", or numerical counts. The analysis determines
        whether required or optional patterns are matched, or specific conditions exist in the
        call stack segment. Based on these conditions, the report is updated with findings.

        Args:
            crashlog_mainerror (str): The main error string from the crash log to be analyzed
                against the suspects stack list.
            segment_callstack_intact (str): Complete call stack segment as a string to identify
                patterns or conditions specified in the suspects stack list.
            autoscan_report (list[str]): A list to store detailed findings and results of the
                scan for suspects for further review.
            max_warn_length (int): Maximum length used to format suspect issue names or warnings
                when appending them to the report.

        Returns:
            bool: True if at least one suspect is found based on the analysis; otherwise, False.
        """
        # Constants for signal modifiers - these define the matching criteria
        # ME-REQ: Signal must be found in the main error
        # ME-OPT: Signal can be found in the main error but isn't required
        # NOT: Signal should NOT be present in the callstack

        any_suspect_found = False

        for error_key, signal_list in self.yamldata.suspects_stack_list.items():
            # Parse error information
            error_severity, error_name = error_key.split(" | ", 1)

            # Initialize match status tracking dictionary
            match_status = {"has_required_item": False, "error_req_found": False, "error_opt_found": False, "stack_found": False}

            # Process each signal in the list
            should_skip_error = False
            for signal in signal_list:
                # Process the signal and update match_status accordingly
                # Returns True if we need to skip this error (e.g., a NOT condition was matched)
                if self._process_signal(signal, crashlog_mainerror, segment_callstack_intact, match_status):
                    should_skip_error = True
                    break

            # Skip this error if a condition indicates we should
            if should_skip_error:
                continue

            # Determine if we have a match based on the processed signals
            if self._is_suspect_match(match_status):
                # Add the suspect to the report and update the found status
                self._add_suspect_to_report(error_name, error_severity, max_warn_length, autoscan_report)
                any_suspect_found = True

        return any_suspect_found

    # noinspection PyPep8Naming
    @staticmethod
    def _process_signal(signal: str, crashlog_mainerror: str, segment_callstack_intact: str, match_status: dict[str, bool]) -> bool:
        """
        Process an individual signal and update match status accordingly.

        Returns True if processing should stop (NOT condition met).
        """
        # Constants for signal modifiers
        MAIN_ERROR_REQUIRED = "ME-REQ"
        MAIN_ERROR_OPTIONAL = "ME-OPT"
        CALLSTACK_NEGATIVE = "NOT"

        if "|" not in signal:
            # Simple case: direct string match in callstack
            if signal in segment_callstack_intact:
                match_status["stack_found"] = True
            return False

        signal_modifier, signal_string = signal.split("|", 1)

        # Process based on signal modifier
        if signal_modifier == MAIN_ERROR_REQUIRED:
            match_status["has_required_item"] = True
            if signal_string in crashlog_mainerror:
                match_status["error_req_found"] = True
        elif signal_modifier == MAIN_ERROR_OPTIONAL:
            if signal_string in crashlog_mainerror:
                match_status["error_opt_found"] = True
        elif signal_modifier == CALLSTACK_NEGATIVE:
            # Return True to break out of the loop if NOT condition is met
            return signal_string in segment_callstack_intact
        elif signal_modifier.isdecimal():
            # Check for minimum occurrences
            min_occurrences = int(signal_modifier)
            if segment_callstack_intact.count(signal_string) >= min_occurrences:
                match_status["stack_found"] = True

        return False

    @staticmethod
    def _is_suspect_match(match_status: dict[str, bool]) -> bool:
        """Determine if current error conditions constitute a suspect match."""
        if match_status["has_required_item"]:
            return match_status["error_req_found"]
        return match_status["error_opt_found"] or match_status["stack_found"]

    @staticmethod
    def _add_suspect_to_report(error_name: str, error_severity: str, max_warn_length: int, autoscan_report: list[str]) -> None:
        """Add a found suspect to the report with proper formatting."""
        formatted_error_name = error_name.ljust(max_warn_length, ".")
        message = f"# Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n"
        append_or_extend(message, autoscan_report)

    def scan_buffout_achievements_setting(
        self, autoscan_report: list[str], xsemodules: set[str], crashgen: dict[str, bool | int | str]
    ) -> None:
        """
        Validates the configuration of the Achievements parameter in the crash generator settings file
        (crashgen) against installed modules in XSE (xsemodules) and updates the autoscan report with
        findings, including necessary fixes if a conflict is detected.

        Args:
            autoscan_report: The report list where messages about the configuration status are
                appended or extended.
            xsemodules: A set of strings representing the names of installed XSE modules.
            crashgen: A dictionary containing configuration values for the crash generator, where
                the key is a configuration parameter, and the value is its corresponding setting.

        """
        crashgen_achievements = crashgen.get("Achievements")
        if crashgen_achievements and ("achievements.dll" in xsemodules or "unlimitedsurvivalmode.dll" in xsemodules):
            append_or_extend(
                (
                    "# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change Achievements to FALSE, this prevents conflicts with {self.yamldata.crashgen_name}.\n-----\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend(
                f"✔️ Achievements parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                autoscan_report,
            )

    def scan_buffout_memorymanagement_settings(
        self, autoscan_report: list[str], crashgen: dict[str, bool | int | str], has_xcell: bool, has_baka_scrapheap: bool
    ) -> None:
        """
        Validates and scans the memory management settings in the configuration file for conflicts with
        X-Cell and the Baka ScrapHeap Mod. Generates a report based on the findings, providing guidance on
        necessary fixes if parameters are incorrectly configured.
        Args:
            autoscan_report (list[str]): A list to store findings and recommendations based on the memory
                management settings validation.
            crashgen (dict[str, bool | int | str]): A dictionary containing current CrashGen configuration
                settings, including memory management parameters and other related properties.
            has_xcell (bool): A flag indicating whether the X-Cell mod is installed.
            has_baka_scrapheap (bool): A flag indicating whether the Baka ScrapHeap mod is installed.
        """
        # Constants for messages and settings
        separator = "\n-----\n"
        success_prefix = "✔️ "
        warning_prefix = "# ❌ CAUTION : "
        fix_prefix = " FIX: "
        crashgen_name = self.yamldata.crashgen_name

        def add_success_message(message: str) -> None:
            """Add a success message to the report."""
            append_or_extend(f"{success_prefix}{message}{separator}", autoscan_report)

        def add_warning_message(warning: str, fix: str) -> None:
            """Add a warning message with fix instructions to the report."""
            append_or_extend((f"{warning_prefix}{warning} # \n", f"{fix_prefix}{fix}{separator}"), autoscan_report)

        # Check main MemoryManager setting
        mem_manager_enabled = crashgen.get("MemoryManager", False)

        # Handle main memory manager configuration
        if mem_manager_enabled:
            if has_xcell:
                add_warning_message(
                    "X-Cell is installed, but MemoryManager parameter is set to TRUE",
                    f"Open {crashgen_name}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with X-Cell.",
                )
            elif has_baka_scrapheap:
                add_warning_message(
                    f"The Baka ScrapHeap Mod is installed, but is redundant with {crashgen_name}",
                    f"Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {crashgen_name}.",
                )
            else:
                add_success_message(f"Memory Manager parameter is correctly configured in your {crashgen_name} settings!")
        elif has_xcell:
            if has_baka_scrapheap:
                add_warning_message(
                    "The Baka ScrapHeap Mod is installed, but is redundant with X-Cell",
                    "Uninstall the Baka ScrapHeap Mod, this prevents conflicts with X-Cell.",
                )
            else:
                add_success_message(
                    f"Memory Manager parameter is correctly configured for use with X-Cell in your {crashgen_name} settings!"
                )
        elif has_baka_scrapheap:
            add_warning_message(
                f"The Baka ScrapHeap Mod is installed, but is redundant with {crashgen_name}",
                f"Uninstall the Baka ScrapHeap Mod and open {crashgen_name}'s TOML file and change MemoryManager to TRUE, this improves performance.",
            )

        # Check additional memory settings for X-Cell compatibility
        if has_xcell:
            memory_settings = {
                "HavokMemorySystem": "Havok Memory System",
                "BSTextureStreamerLocalHeap": "BSTextureStreamerLocalHeap",
                "ScaleformAllocator": "Scaleform Allocator",
                "SmallBlockAllocator": "Small Block Allocator",
            }

            for setting_key, display_name in memory_settings.items():
                if crashgen.get(setting_key):
                    add_warning_message(
                        f"X-Cell is installed, but {setting_key} parameter is set to TRUE",
                        f"Open {crashgen_name}'s TOML file and change {setting_key} to FALSE, this prevents conflicts with X-Cell.",
                    )
                else:
                    add_success_message(
                        f"{display_name} parameter is correctly configured for use with X-Cell in your {crashgen_name} settings!"
                    )

    def scan_archivelimit_setting(self, autoscan_report: list[str], crashgen: dict[str, bool | int | str]) -> None:
        """
        Scans the 'ArchiveLimit' setting in the crashgen configuration and appends either
        a warning or confirmation message to the autoscan_report.

        This method evaluates the 'ArchiveLimit' parameter of the crashgen configuration;
        if the parameter is enabled (True), it adds a cautionary message to the report,
        notifying the user of its potential instability and providing guidance for
        disabling it. Conversely, if the parameter is disabled (False or not set), it
        adds a confirmation message to the report, indicating that the setting is
        correctly configured.

        Args:
            autoscan_report (list[str]): A list where logging or reporting messages are
                appended to indicate issues or validation details during the scan.
            crashgen (dict[str, bool | int | str]): A dictionary representing the
                crashgen configuration, which is evaluated to determine the value of
                the 'ArchiveLimit' parameter.
        """
        crashgen_archivelimit = crashgen.get("ArchiveLimit")
        if crashgen_archivelimit:
            append_or_extend(
                (
                    "# ❌ CAUTION : ArchiveLimit is set to TRUE, this setting is known to cause instability. # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change ArchiveLimit to FALSE.\n-----\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend(
                f"✔️ ArchiveLimit parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                autoscan_report,
            )

    def scan_buffout_looksmenu_setting(
        self, crashgen: dict[str, bool | int | str], autoscan_report: list[str], xsemodules: set[str]
    ) -> None:
        """
        Scans the Buffout 4 settings for the correct configuration of the Looks Menu (F4EE)
        parameter under the `[Compatibility]` section and appends the corresponding
        messages to the autoscan report.

        This function checks if the F4EE parameter in the crashgen configuration is
        set appropriately based on the presence of `f4ee.dll` in the installed modules. If the
        parameter is incorrectly configured, it provides specific instructions for fixing the
        configuration in the TOML file. Otherwise, it confirms that the parameter is correct.

        Args:
            crashgen (dict[str, bool | int | str]): The settings dictionary containing
                configuration parameters, including the F4EE parameter under the `[Compatibility]`.
            autoscan_report (list[str]): The list used to store diagnostic messages
                regarding the scan results.
            xsemodules (set[str]): The set of installed module filenames in the current
                environment used to determine compatibility requirements.

        Returns:
            None
        """
        crashgen_f4ee = crashgen.get("F4EE")
        if crashgen_f4ee is not None:
            if not crashgen_f4ee and "f4ee.dll" in xsemodules:
                append_or_extend(
                    (
                        "# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under [Compatibility] is set to FALSE # \n",
                        f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change F4EE to TRUE, this prevents bugs and crashes from Looks Menu.\n-----\n",
                    ),
                    autoscan_report,
                )
            else:
                append_or_extend(
                    f"✔️ F4EE (Looks Menu) parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                    autoscan_report,
                )

    def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """
        Processes and analyzes Form IDs from the provided data sources, matching them
        against crash log plugins and generating a report based on the findings. This
        method identifies potentially relevant Form IDs present in the crash log and
        provides insights using a database, if available.

        Args:
            formids_matches (list[str]): A list of Form ID strings identified
                from the crash log.
            crashlog_plugins (dict[str, str]): A dictionary mapping plugin names
                to their associated plugin IDs.
            autoscan_report (list[str]): A list to which the method appends
                formatted analysis results.
        """
        if formids_matches:
            formids_found = dict(Counter(sorted(formids_matches)))
            for formid_full, count in formids_found.items():
                formid_split = formid_full.split(": ", 1)
                if len(formid_split) < 2:
                    continue
                for plugin, plugin_id in crashlog_plugins.items():
                    if plugin_id != formid_split[1][:2]:
                        continue

                    if self.show_formid_values and self.formid_db_exists:
                        report = get_entry(formid_split[1][2:], plugin)
                        if report:
                            append_or_extend(f"- {formid_full} | [{plugin}] | {report} | {count}\n", autoscan_report)
                            continue

                    append_or_extend(f"- {formid_full} | [{plugin}] | {count}\n", autoscan_report)
                    break
            append_or_extend(
                (
                    "\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
                    f"These Form IDs were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
                    "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend("* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n", autoscan_report)

    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str], autoscan_report: list[str]) -> None:
        """
        Matches plugins in the given segment callstack against the crashlog plugins and appends the result
        to the autoscan report. The method identifies plugins in the crash log that correspond to the given
        plugin list, filtering based on relevance and ignoring specific plugins as configured in the class.

        Args:
            segment_callstack_lower (list[str]): Lowercase representation of the segment callstack,
                containing lines to be analyzed for potential plugin matches.
            crashlog_plugins_lower (set[str]): Set of lowercase plugin names extracted from the crash log,
                used as a reference for matching against the callstack lines.
            autoscan_report (list[str]): List where the method will append strings documenting plugin matches
                or the absence of matches. This is modified in-place.
        """
        # Pre-filter call stack lines that won't match
        relevant_lines = [line for line in segment_callstack_lower if "modified by:" not in line]

        # Use Counter directly instead of list + Counter conversion
        plugins_matches: Counter[str] = Counter()

        # Optimize the matching algorithm
        for line in relevant_lines:
            for plugin in crashlog_plugins_lower:
                # Skip plugins that are in the ignore list
                if plugin in self.lower_plugins_ignore:
                    continue

                if plugin in line:
                    plugins_matches[plugin] += 1

        if plugins_matches:
            append_or_extend("The following PLUGINS were found in the CRASH STACK:\n", autoscan_report)
            # Sort by count (descending) then by name for consistent output
            for plugin, count in sorted(plugins_matches.items(), key=lambda x: (-x[1], x[0])):
                append_or_extend(f"- {plugin} | {count}\n", autoscan_report)
            append_or_extend(
                (
                    "\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n",
                    f"These Plugins were caught by {self.yamldata.crashgen_name} and some of them might be responsible for this crash.\n",
                    "You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n", autoscan_report)

    @staticmethod
    def scan_log_gpu(segment_system: list[str]) -> tuple[str, Literal["nvidia", "amd"] | None]:
        """
        Scans the log to determine the GPU information and its rival.

        This method analyzes a list of system log segments to identify the primary
        graphics processing unit (GPU) being used. It also determines the rival GPU
        manufacturer based on the GPU identified. If the GPU information cannot be
        determined, the method returns "Unknown" and the rival GPU is set to None.

        Args:
            segment_system (list[str]): A list of log segments containing system
                information. Each log segment is expected to contain details about
                hardware components including GPUs.

        Returns:
            tuple[str, Literal["nvidia", "amd"] | None]: A tuple containing the GPU
                name and the rival GPU manufacturer. The first element is a string
                that represents the GPU name ("AMD", "Nvidia", or "Unknown"). The
                second element is a Literal that specifies the rival GPU
                manufacturer ("nvidia", "amd"), or None if no rival is identified.
        """
        gpu: str
        gpu_rival: Literal["nvidia", "amd"] | None
        if any("GPU #1" in elem and "AMD" in elem for elem in segment_system):
            gpu = "AMD"
            gpu_rival = "nvidia"
        elif any("GPU #1" in elem and "Nvidia" in elem for elem in segment_system):
            gpu = "Nvidia"
            gpu_rival = "amd"
        else:
            gpu = "Unknown"
            gpu_rival = None
        return gpu, gpu_rival

    # noinspection PyPep8Naming
    def scan_named_records(self, segment_callstack: list[str], records_matches: list[str], autoscan_report: list[str]) -> None:
        """
        Scans a given call stack segment to identify and record named records, and appends
        relevant information about the findings to the autoscan report.

        This method processes the `segment_callstack` to identify specific patterns for "named
        records" while respecting the specified ignore list. If any matches are found, it
        counts occurrences, formats findings, and appends suitable annotations or information
        to the autoscan report, summarizing potential crash-related data for further analysis.

        Args:
            segment_callstack (list[str]): List of strings representing the call stack segment
                to be analyzed for named records.
            records_matches (list[str]): List to store the matched named records identified during
                the scan.
            autoscan_report (list[str]): List to which the analysis summary or findings about
                named records will be appended.
        """
        # Constants
        RSP_MARKER = "[RSP+"
        RSP_OFFSET = 30

        # Find matching records
        self._find_matching_records(segment_callstack, records_matches, RSP_MARKER, RSP_OFFSET)

        # Report results
        if records_matches:
            self._report_found_records(records_matches, autoscan_report)
        else:
            append_or_extend("* COULDN'T FIND ANY NAMED RECORDS *\n\n", autoscan_report)

    def _find_matching_records(self, segment_callstack: list[str], records_matches: list[str], rsp_marker: str, rsp_offset: int) -> None:
        """Extract matching records from the call stack and add them to records_matches."""
        for line in segment_callstack:
            lower_line = line.lower()

            # Check if line contains any target record and doesn't contain any ignored terms
            if any(item in lower_line for item in self.lower_records) and all(record not in lower_line for record in self.lower_ignore):
                # Extract the relevant part of the line based on format
                if rsp_marker in line:
                    records_matches.append(line[rsp_offset:].strip())
                else:
                    records_matches.append(line.strip())

    def _report_found_records(self, records_matches: list[str], autoscan_report: list[str]) -> None:
        """Format and add report entries for the found records."""
        # Count and sort the records
        records_found = dict(Counter(sorted(records_matches)))

        # Add each record with its count
        for record, count in records_found.items():
            append_or_extend(f"- {record} | {count}\n", autoscan_report)

        # Add explanatory notes
        explanatory_notes = (
            "\n[Last number counts how many times each Named Record shows up in the crash log.]\n",
            f"These records were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
            "Named records should give extra info on involved game objects, record types or mod files.\n\n",
        )
        append_or_extend(explanatory_notes, autoscan_report)

    @staticmethod
    def extract_module_names(module_texts: set[str]) -> set[str]:
        if not module_texts:
            return set()

        # Pattern matches module name potentially followed by version
        pattern = re.compile(r"(.*?\.dll)\s*v?.*", re.IGNORECASE)  # pyrefly: ignore

        result = set()
        for text in module_texts:
            text = text.strip()
            match = pattern.match(text)
            if match:
                result.add(match.group(1))
            else:
                result.add(text)

        return result


# ================================================
# CRASH LOG SCAN START
# ================================================
# noinspection PyUnusedLocal
def process_crashlog(scanner: ClassicScanLogs, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
    """
    Process a single crash log file and generate a report.

    This function processes a crash log file, analyzing its contents to identify potential issues,
    checking for known crash suspects, and generating a detailed report.

    Args:
        scanner: The ClassicScanLogs instance used for scanning the crash log.
        crashlog_file: The path to the crash log file to be processed.

    Returns:
        tuple: Contains the crash log file path, the generated report as a list of strings,
              a boolean indicating if the scan failed, and a Counter with updated statistics.
    """
    yamldata = scanner.yamldata
    autoscan_report: list[str] = []
    trigger_plugin_limit = trigger_limit_check_disabled = trigger_plugins_loaded = trigger_scan_failed = False
    # Local stats counter to avoid thread synchronization issues
    local_stats = Counter(scanned=1, incomplete=0, failed=0)  # Start with 1 scanned

    crash_data = scanner.crashlogs.read_log(crashlog_file.name)

    append_or_extend(
        (
            f"{crashlog_file.name} -> AUTOSCAN REPORT GENERATED BY {yamldata.classic_version} \n",
            "# FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR # \n",
            "# PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES # \n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    # ================================================
    # 1) GENERATE REQUIRED SEGMENTS FROM THE CRASH LOG
    # ================================================
    (
        crashlog_gameversion,
        crashlog_crashgen,
        crashlog_mainerror,
        (
            segment_crashgen,
            segment_system,
            segment_callstack,
            segment_allmodules,
            segment_xsemodules,
            segment_plugins,
        ),
    ) = scanner.find_segments(crash_data, yamldata.crashgen_name)
    segment_callstack_intact = "".join(segment_callstack)

    game_version = crashgen_version_gen(crashlog_gameversion)

    # SOME IMPORTANT DLLs HAVE A VERSION, REMOVE IT
    xsemodules = ClassicScanLogs.extract_module_names(set(segment_xsemodules))

    crashgen: dict[str, bool | int | str] = {}
    if segment_crashgen:
        for elem in segment_crashgen:
            if ":" in elem:
                key, value = elem.split(":", 1)
                crashgen[key] = (
                    True if value == " true" else False if value == " false" else int(value) if value.isdecimal() else value.strip()
                )

    if not segment_plugins:
        local_stats["incomplete"] += 1
    if len(crash_data) < 20:
        local_stats["scanned"] -= 1
        local_stats["failed"] += 1
        trigger_scan_failed = True

    # ================== MAIN ERROR ==================
    # =============== CRASHGEN VERSION ===============
    version_current = crashgen_version_gen(crashlog_crashgen)
    version_latest = crashgen_version_gen(yamldata.crashgen_latest_og)
    version_latest_vr = crashgen_version_gen(yamldata.crashgen_latest_vr)
    append_or_extend(
        (
            f"\nMain Error: {crashlog_mainerror}\n",
            f"Detected {yamldata.crashgen_name} Version: {crashlog_crashgen} \n",
            (
                f"* You have the latest version of {yamldata.crashgen_name}! *\n\n"
                if version_current >= version_latest or version_current >= version_latest_vr
                else f"{yamldata.warn_outdated} \n"
            ),
        ),
        autoscan_report,
    )

    # ======= REQUIRED LISTS, DICTS AND CHECKS =======

    crashlog_plugins: dict[str, str] = {}
    trigger_plugin_limit = False  # Initialize the variable here

    esm_name = f"{GlobalRegistry.get_game()}.esm"
    if any(esm_name in elem for elem in segment_plugins):
        trigger_plugins_loaded = True
    else:
        local_stats["incomplete"] += 1

    # ================================================
    # 2) CHECK EACH SEGMENT AND CREATE REQUIRED VALUES
    # ================================================

    # CHECK GPU TYPE FOR CRASH LOG
    crashlog_gpu, crashlog_gpu_rival = scanner.scan_log_gpu(segment_system)

    # IF LOADORDER FILE EXISTS, USE ITS PLUGINS
    loadorder_path = Path("loadorder.txt")
    if loadorder_path.exists():
        loadorder_plugins, trigger_plugins_loaded = scanner.loadorder_scan_loadorder_txt(autoscan_report)
        crashlog_plugins = crashlog_plugins | loadorder_plugins
    else:  # OTHERWISE, USE PLUGINS FROM CRASH LOG
        log_plugins, plugin_limit, trigger_limit_check_disabled = scanner.loadorder_scan_log(segment_plugins, game_version, version_current)
        crashlog_plugins = crashlog_plugins | log_plugins
        trigger_plugin_limit = plugin_limit  # Update the trigger_plugin_limit variable

    crashlog_plugins.update({elem: "DLL" for elem in xsemodules if all(elem not in item for item in crashlog_plugins)})

    for elem in segment_allmodules:
        # SOME IMPORTANT DLLs ONLY APPEAR UNDER ALL MODULES
        if "vulkan" in elem.lower():
            elem_parts = elem.strip().split(" ", 1)
            crashlog_plugins.update({elem_parts[0]: "DLL"})

    crashlog_plugins_lower = {plugin.lower() for plugin in crashlog_plugins}

    # CHECK IF THERE ARE ANY PLUGINS IN THE IGNORE YAML
    if scanner.ignore_plugins_list:
        for signal in scanner.ignore_plugins_list:
            if signal in crashlog_plugins_lower:
                del crashlog_plugins[signal]

    append_or_extend(
        (
            "====================================================\n",
            "CHECKING IF LOG MATCHES ANY KNOWN CRASH SUSPECTS...\n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    crashlog_mainerror_lower = crashlog_mainerror.lower()
    if ".dll" in crashlog_mainerror_lower and "tbbmalloc" not in crashlog_mainerror_lower:
        append_or_extend(
            (
                "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \n",
                "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n-----\n",
            ),
            autoscan_report,
        )
    max_warn_length = 30
    trigger_suspect_found = any((
        scanner.suspect_scan_mainerror(autoscan_report, crashlog_mainerror, max_warn_length),
        scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, autoscan_report, max_warn_length),
    ))

    if trigger_suspect_found:
        append_or_extend(
            (
                "* FOR DETAILED DESCRIPTIONS AND POSSIBLE SOLUTIONS TO ANY ABOVE DETECTED CRASH SUSPECTS *\n",
                "* SEE: https://docs.google.com/document/d/17FzeIMJ256xE85XdjoPvv_Zi3C5uHeSTQh6wOZugs4c *\n\n",
            ),
            autoscan_report,
        )
    else:
        append_or_extend(
            (
                "# FOUND NO CRASH ERRORS / SUSPECTS THAT MATCH THE CURRENT DATABASE #\n",
                "Check below for mods that can cause frequent crashes and other problems.\n\n",
            ),
            autoscan_report,
        )

    # ================================================
    # 4) IMPORT AND RUN DETECT MODS FROM EXTERNAL MODULE
    # ================================================
    # Import at runtime to avoid circular imports
    from ClassicLib.ScanLog.DetectMods import detect_mods_double, detect_mods_important, detect_mods_single

    # ================================================
    # 5) CHECK SETTINGS AFTER MOD CHECKS
    # ================================================
    append_or_extend(
        (
            "====================================================\n",
            "CHECKING IF NECESSARY FILES/SETTINGS ARE CORRECT...\n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    has_x_cell: bool = "x-cell-fo4.dll" in xsemodules or "x-cell-og.dll" in xsemodules or "x-cell-ng2.dll" in xsemodules
    has_baka_scrapheap: bool = "bakascrapheap.dll" in xsemodules

    if scanner.fcx_mode:
        append_or_extend(
            (
                "* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n",
                "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n",
            ),
            autoscan_report,
        )
        append_or_extend(scanner.main_files_check, autoscan_report)
        append_or_extend(scanner.game_files_check, autoscan_report)
    else:
        append_or_extend(
            (
                "* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n",
                "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n",
            ),
            autoscan_report,
        )
        if has_x_cell:
            yamldata.crashgen_ignore.update(("MemoryManager", "HavokMemorySystem", "ScaleformAllocator", "SmallBlockAllocator"))
        elif has_baka_scrapheap:
            # To prevent two messages mentioning this parameter.
            yamldata.crashgen_ignore.add("MemoryManager")
    # Check important CrashGen settings
    if crashgen:
        for setting_name, setting_value in crashgen.items():
            if setting_value is False and setting_name not in yamldata.crashgen_ignore:
                append_or_extend(
                    f"* NOTICE : {setting_name} is disabled in your {yamldata.crashgen_name} settings, is this intentional? * \n-----\n",
                    autoscan_report,
                )
        # Check the crashgen Achievements setting
        scanner.scan_buffout_achievements_setting(autoscan_report, xsemodules, crashgen)

        # Check memory management settings
        scanner.scan_buffout_memorymanagement_settings(autoscan_report, crashgen, has_x_cell, has_baka_scrapheap)

        # Check ArchiveLimit setting
        if crashgen_version_gen(scanner.yamldata.crashgen_latest_og) <= crashgen_version_gen(crashlog_crashgen) >= Version("1.27.0"):
            scanner.scan_archivelimit_setting(autoscan_report, crashgen)

        # Check LooksMenu (F4EE) setting
        scanner.scan_buffout_looksmenu_setting(crashgen, autoscan_report, xsemodules)

    # Now run the plugin-dependent checks with proper conditionals
    append_or_extend(
        (
            "====================================================\n",
            "CHECKING FOR MODS THAT CAN CAUSE FREQUENT CRASHES...\n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    plugins_loading_failure_message = (
        "* [!] NOTICE : BUFFOUT 4 WAS NOT ABLE TO LOAD THE PLUGIN LIST FOR THIS CRASH LOG! *\n"
        "  CLASSIC cannot perform the full scan. Provide or scan a different crash log\n"
        "  OR copy-paste your *loadorder.txt* into your main CLASSIC folder.\n"
    )

    if trigger_plugins_loaded:
        # Detect problematic mods
        detect_mods_single(yamldata.game_mods_freq, crashlog_plugins, autoscan_report)
    else:
        append_or_extend(plugins_loading_failure_message, autoscan_report)

    append_or_extend(
        (
            "====================================================\n",
            "CHECKING FOR MODS THAT CONFLICT WITH OTHER MODS...\n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    if trigger_plugins_loaded:
        if detect_mods_double(yamldata.game_mods_conf, crashlog_plugins, autoscan_report):
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
        append_or_extend(yamldata.warn_noplugins, autoscan_report)

    append_or_extend(
        (
            "====================================================\n",
            "CHECKING FOR MODS WITH SOLUTIONS & COMMUNITY PATCHES\n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    if trigger_plugins_loaded:
        if detect_mods_single(yamldata.game_mods_solu, crashlog_plugins, autoscan_report):
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
        append_or_extend(yamldata.warn_noplugins, autoscan_report)

    if GlobalRegistry.get_game() == "Fallout4":
        append_or_extend(
            (
                "====================================================\n",
                "CHECKING FOR MODS PATCHED THROUGH OPC INSTALLER...\n",
                "====================================================\n",
            ),
            autoscan_report,
        )

        if trigger_plugins_loaded:
            if detect_mods_single(yamldata.game_mods_opc2, crashlog_plugins, autoscan_report):
                append_or_extend(
                    (
                        "\n* FOR PATCH REPOSITORY THAT PREVENTS CRASHES AND FIXES PROBLEMS IN THESE AND OTHER MODS,* \n",
                        "* VISIT OPTIMIZATION PATCHES COLLECTION: https://www.nexusmods.com/fallout4/mods/54872 * \n\n",
                    ),
                    autoscan_report,
                )
            else:
                append_or_extend("# FOUND NO PROBLEMATIC MODS THAT ARE ALREADY PATCHED THROUGH THE OPC INSTALLER # \n\n", autoscan_report)
        else:
            append_or_extend(yamldata.warn_noplugins, autoscan_report)

    append_or_extend(
        (
            "====================================================\n",
            "CHECKING IF IMPORTANT PATCHES & FIXES ARE INSTALLED\n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    if trigger_plugins_loaded:
        if any("londonworldspace" in plugin.lower() for plugin in crashlog_plugins):
            detect_mods_important(yamldata.game_mods_core_folon, crashlog_plugins, autoscan_report, crashlog_gpu_rival)
        else:
            detect_mods_important(yamldata.game_mods_core, crashlog_plugins, autoscan_report, crashlog_gpu_rival)
    else:
        append_or_extend(yamldata.warn_noplugins, autoscan_report)

    # Check if plugin limit may be reached
    if trigger_plugin_limit and not trigger_limit_check_disabled and trigger_plugins_loaded:
        append_or_extend(
            ("# \U0001f480 CRITICAL : THE '[FF]' PLUGIN MEANS YOU REACHED THE PLUGIN LIMIT OF 255-ish PLUGINS # \n",), autoscan_report
        )
    elif trigger_plugin_limit and trigger_limit_check_disabled and trigger_plugins_loaded:
        append_or_extend(
            (
                "# ⚠️ WARNING : THE '[FF]' PLUGIN WAS DETECTED BUT PLUGIN LIMIT CHECK IS DISABLED. # \n",
                "This could indicates that your version of Buffout 4 NG is out of date. \n",
                "Recommendation: Consider updating Buffout 4 NG to the latest version. \n-----\n",
            ),
            autoscan_report,
        )

    # ================================================
    # 6) SCAN FOR SPECIFIC SUSPECTS AT THE END
    # ================================================
    append_or_extend(
        (
            "====================================================\n",
            "SCANNING THE LOG FOR SPECIFIC (POSSIBLE) SUSPECTS...\n",
            "====================================================\n",
        ),
        autoscan_report,
    )

    # Scan for plugins in call stack
    append_or_extend(("# LIST OF (POSSIBLE) PLUGIN SUSPECTS #\n",), autoscan_report)

    # Convert callstack to lowercase for case-insensitive matching
    segment_callstack_lower = [line.lower() for line in segment_callstack]
    scanner.plugin_match(segment_callstack_lower, crashlog_plugins_lower, autoscan_report)

    # Scan for Form IDs
    append_or_extend(("\n# LIST OF (POSSIBLE) FORM ID SUSPECTS #\n",), autoscan_report)
    formids_matches: list[str] = []
    if segment_callstack:
        formid_pattern: re.Pattern[str] = re.compile(
            r"^(?!.*0xFF)(?=.*id:).*Form ID: ([0-9A-F]{8})",
            re.IGNORECASE | re.MULTILINE,  # pyrefly: ignore
        )
        for line in segment_callstack:
            match: re.Match[str] | None = formid_pattern.search(line)
            if match:
                formids_matches.append(f"Form ID: {match.group(1).strip().replace('0x', '')}")

    scanner.formid_match(formids_matches, crashlog_plugins, autoscan_report)

    # Scan for named records
    append_or_extend(("\n# LIST OF DETECTED (NAMED) RECORDS #\n",), autoscan_report)
    records_matches: list[str] = []
    scanner.scan_named_records(segment_callstack, records_matches, autoscan_report)

    if GlobalRegistry.get_game().replace(" ", "") == "Fallout4":
        append_or_extend(yamldata.autoscan_text, autoscan_report)
    append_or_extend(f"{yamldata.classic_version} | {yamldata.classic_version_date} | END OF AUTOSCAN \n", autoscan_report)

    return crashlog_file, autoscan_report, trigger_scan_failed, local_stats


def write_report_to_file(crashlog_file: Path, autoscan_report: list[str], trigger_scan_failed: bool, scanner: ClassicScanLogs) -> None:
    """
    Write the autoscan report to a file and handle failed logs.

    Args:
        crashlog_file: The path to the crash log file.
        autoscan_report: The generated report as a list of strings.
        trigger_scan_failed: A boolean indicating if the scan failed.
        scanner: The ClassicScanLogs instance.
    """
    autoscan_path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    with autoscan_path.open("w", encoding="utf-8", errors="ignore") as autoscan_file:
        logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
        autoscan_output: str = "".join(autoscan_report)
        autoscan_file.write(autoscan_output)

    if trigger_scan_failed and scanner.move_unsolved_logs:
        backup_path: Path = Path("CLASSIC Backup/Unsolved Logs")
        backup_path.mkdir(parents=True, exist_ok=True)
        autoscan_filepath: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        crash_move: Path = backup_path / crashlog_file.name
        scan_move: Path = backup_path / autoscan_filepath.name

        if crashlog_file.exists():
            shutil.copy2(crashlog_file, crash_move)
        if autoscan_filepath.exists():
            shutil.copy2(autoscan_filepath, scan_move)


def crashlogs_scan() -> None:
    """
    Scans crash log files to generate reports, identify issues, and provide insights into the cause of crashes. This
    function uses crash log data, plugin configurations, and system segments to correlate crash events with probable
    causes and generate detailed reports that include warnings, errors, and potential solutions.

    The function performs a sequence of actions:
    1) Collects and processes crash log segments, such as system information, stack traces, and plugin lists.
    2) Analyzes crash-generation details, checks for specific errors, and identifies potential crash suspects.
    3) Evaluates system and game configurations, scans for missing files or conflicting plugins, and suggests fixes.
    4) Produces an autoscan report summarizing the findings, which can assist in troubleshooting and resolving crash issues.

    Raises:
        RuntimeError: If a critical error occurs during crash log scanning or data processing.
    """
    scanner: ClassicScanLogs = ClassicScanLogs()
    ClassicScanLogs._fcx_checks_run = False  # Correctly target class variable to reset guard

    # Perform FCX checks once for the entire session if FCX mode is enabled.
    # This populates scanner.main_files_check and scanner.game_files_check
    # and sets ClassicScanLogs._fcx_checks_run to True.
    if scanner.fcx_mode:
        scanner.fcx_mode_check()

    yamldata = scanner.yamldata
    scan_failed_list: list[str] = []

    # Number of worker threads - adjust based on system capabilities
    # Using CPU count * 2 is a common heuristic, but we'll use min function to avoid too many threads
    max_workers: int = min(os.cpu_count() or 4, 8)  # Default to 4 if cpu_count returns None, max of 8

    try:
        # Process crash logs in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all crash log processing tasks
            futures = [executor.submit(process_crashlog, scanner, crashlog_file) for crashlog_file in scanner.crashlog_list]

            # Process results as they complete
            for future in as_completed(futures):
                try:
                    crashlog_file, autoscan_report, trigger_scan_failed, local_stats = future.result()

                    # Update the main statistics counter atomically
                    for key, value in local_stats.items():
                        scanner.crashlog_stats[key] += value

                    # Write the report to a file
                    write_report_to_file(crashlog_file, autoscan_report, trigger_scan_failed, scanner)

                    # Add to failed list if needed
                    if trigger_scan_failed:
                        scan_failed_list.append(crashlog_file.name)

                except Exception as e:  # noqa: BLE001
                    logger.error(f"Error processing crash log: {e!s}")
                    scanner.crashlog_stats["failed"] += 1

        # CHECK FOR FAILED OR INVALID CRASH LOGS
        scan_invalid_list = sorted(Path.cwd().glob("crash-*.txt"))
        if scan_failed_list or scan_invalid_list:
            print("❌ NOTICE : CLASSIC WAS UNABLE TO PROPERLY SCAN THE FOLLOWING LOG(S):")
            print("\n".join(scan_failed_list))
            if scan_invalid_list:
                for file in scan_invalid_list:
                    print(f"{file}\n")
            print("===============================================================================")
            print("Most common reason for this are logs being incomplete or in the wrong format.")
            print("Make sure that your crash log files have the .log file format, NOT .txt! \n")

        # ================================================
        # CRASH LOG SCAN COMPLETE / TERMINAL OUTPUT
        # ================================================
        logger.info("- - - COMPLETED CRASH LOG FILE SCAN >>> ALL AVAILABLE LOGS SCANNED")
        print("SCAN COMPLETE! (IT MIGHT TAKE SEVERAL SECONDS FOR SCAN RESULTS TO APPEAR)")
        print("SCAN RESULTS ARE AVAILABLE IN FILES NAMED crash-date-and-time-AUTOSCAN.md \n")
        print(f"{random.choice(yamldata.classic_game_hints)}\n-----")
        print(f"Scanned all available logs in {str(time.perf_counter() - 0.5 - scanner.scan_start_time)[:5]} seconds.")
        print(f"Number of Scanned Logs (No Autoscan Errors): {scanner.crashlog_stats['scanned']}")
        print(f"Number of Incomplete Logs (No Plugins List): {scanner.crashlog_stats['incomplete']}")
        print(f"Number of Failed Logs (Autoscan Can't Scan): {scanner.crashlog_stats['failed']}\n-----")
        if GlobalRegistry.get_game() == "Fallout4":
            print(yamldata.autoscan_text)
        if scanner.crashlog_stats["scanned"] == 0 and scanner.crashlog_stats["incomplete"] == 0:
            print("\n❌ CLASSIC found no crash logs to scan or the scan failed.")
            print("    There are no statistics to show (at this time).\n")
    finally:
        # Ensure database is closed regardless of any exceptions
        scanner.close_database()


if __name__ == "__main__":
    initialize()

    # noinspection PyUnresolvedReferences
    from tap import Tap

    class Args(Tap):
        """Command-line arguments for CLASSIC's Command Line Interface"""

        fcx_mode: bool = False
        """Enable FCX mode"""

        show_fid_values: bool = False
        """Show FormID values"""

        stat_logging: bool = False
        """Enable statistical logging"""

        move_unsolved: bool = False
        """Move unsolved logs"""

        ini_path: Path | None = None
        """Path to the INI file"""

        scan_path: Path | None = None
        """Path to the scan directory"""

        mods_folder_path: Path | None = None
        """Path to the mods folder"""

        simplify_logs: bool = False
        """Simplify the logs"""

    args = Args().parse_args()

    if isinstance(args.fcx_mode, bool) and args.fcx_mode != classic_settings(bool, "FCX Mode"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", args.fcx_mode)

    if isinstance(args.show_fid_values, bool) and args.show_fid_values != classic_settings(bool, "Show FormID Values"):
        yaml_settings(bool, YAML.Settings, "Show FormID Values", args.show_fid_values)

    if isinstance(args.move_unsolved, bool) and args.move_unsolved != classic_settings(bool, "Move Unsolved Logs"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved", args.move_unsolved)

    if (
        isinstance(args.ini_path, Path)
        and args.ini_path.resolve().is_dir()
        and str(args.ini_path) != classic_settings(str, "INI Folder Path")
    ):
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", str(args.ini_path.resolve()))

    if (
        isinstance(args.scan_path, Path)
        and args.scan_path.resolve().is_dir()
        and str(args.scan_path) != classic_settings(str, "SCAN Custom Path")
    ):
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(args.scan_path.resolve()))

    if (
        isinstance(args.mods_folder_path, Path)
        and args.mods_folder_path.resolve().is_dir()
        and str(args.mods_folder_path) != classic_settings(str, "MODS Folder Path")
    ):
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", str(args.mods_folder_path.resolve()))

    if isinstance(args.simplify_logs, bool) and args.simplify_logs != classic_settings(bool, "Simplify Logs"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Simplify Logs", args.simplify_logs)

    crashlogs_scan()
    os.system("pause")

import os
import random
import shutil
import sqlite3
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import regex as re
import requests

import CLASSIC_Main as CMain
import CLASSIC_ScanGame as CGame

query_cache: dict[tuple[str, str], str] = {}

# ================================================
# ASSORTED FUNCTIONS
# ================================================
def pastebin_fetch(url: str) -> None:
    if urlparse(url).netloc == "pastebin.com" and "/raw" not in url:
        url = url.replace("pastebin.com", "pastebin.com/raw")
    response = requests.get(url)
    if response.status_code == requests.codes.ok:
        pastebin_path = Path("Crash Logs/Pastebin")
        if not pastebin_path.is_dir():
            pastebin_path.mkdir(parents=True, exist_ok=True)
        outfile = pastebin_path / f"crash-{urlparse(url).path.split("/")[-1]}.log"
        outfile.write_text(response.text, encoding="utf-8", errors="ignore")
    else:
        response.raise_for_status()

def get_entry(formid: str, plugin: str) -> str | None:
    if (entry := query_cache.get((formid, plugin))) is not None:
        return entry

    # Define paths for both Main and Local databases
    db_paths = [
        Path(f"CLASSIC Data/databases/{CMain.gamevars["game"]} FormIDs Main.db"),
        Path(f"CLASSIC Data/databases/{CMain.gamevars["game"]} FormIDs Local.db"),
    ]

    for db_path in db_paths:
        if db_path.is_file():
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute(f"SELECT entry FROM {CMain.gamevars["game"]} WHERE formid=? AND plugin=? COLLATE nocase", (formid, plugin))
                entry = c.fetchone()
                if entry:
                    query_cache[(formid, plugin)] = entry[0]
                    return entry[0]

    return None

# ================================================
# INITIAL REFORMAT FOR CRASH LOG FILES
# ================================================
def crashlogs_get_files() -> list[Path]:
    """Optimized version: Get paths of all available crash logs."""
    CMain.logger.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION")

    CLASSIC_folder = Path.cwd()
    CLASSIC_logs = CLASSIC_folder / "Crash Logs"
    CUSTOM_folder_setting = CMain.classic_settings("SCAN Custom Path")
    XSE_folder_setting = CMain.yaml_settings(CMain.YAML.Game_Local, "Game_Info.Docs_Folder_XSE")

    CUSTOM_folder = Path(CUSTOM_folder_setting) if isinstance(CUSTOM_folder_setting, str) else None
    XSE_folder = Path(XSE_folder_setting) if isinstance(XSE_folder_setting, str) else None

    # Ensure Crash Logs directory exists
    CLASSIC_logs.mkdir(parents=True, exist_ok=True)

    # Rename or copy files to Crash Logs directory
    files_to_process = list(CLASSIC_folder.glob("crash-*.log")) + list(CLASSIC_folder.glob("crash-*-AUTOSCAN.md"))
    if len(files_to_process) > 0:
        for file in files_to_process:
            destination_file = CLASSIC_logs / file.name
            if not destination_file.exists():
                file.rename(destination_file)
            else:
                file.unlink()

    # Copy XSE crash logs if applicable
    if XSE_folder and XSE_folder.is_dir():
        for crash_file in XSE_folder.glob("crash-*.log"):
            destination_file = CLASSIC_logs / crash_file.name
            if not destination_file.exists():
                shutil.copy2(crash_file, destination_file)

    # Gather all crash log files from specified directories
    crash_files = list(CLASSIC_logs.rglob("crash-*.log")) # rglob this one for eventual pastebin support

    if CUSTOM_folder and CUSTOM_folder.is_dir():
        crash_files.extend(CUSTOM_folder.glob("crash-*.log"))

    return crash_files


def crashlogs_reformat() -> None:
    """Reformat plugin lists in crash logs, so that old and new CRASHGEN formats match."""
    CMain.logger.debug("- - - INITIATED CRASH LOG FILE REFORMAT")
    xse_acronym: str = CMain.yaml_settings(CMain.YAML.Game, f"Game{CMain.gamevars["vr"]}_Info.XSE_Acronym") # type: ignore
    remove_list: list[str] = CMain.yaml_settings(CMain.YAML.Main, "exclude_log_records") # type: ignore
    simple_logs = CMain.classic_settings("Simplify Logs")

    for file in crashlogs_get_files():
        with file.open(encoding="utf-8", errors="ignore") as crash_log:
            crash_data = crash_log.readlines()
        try:
            index_plugins = next(index for index, item in enumerate(crash_data) if xse_acronym and xse_acronym not in item and "PLUGINS:" in item)
        except StopIteration:
            index_plugins = 1

        for index, line in enumerate(crash_data):
            if simple_logs and any(string in line for string in remove_list):
                crash_data.pop(index)  # Remove *useless* lines from crash log if Simplify Logs is enabled.
            elif index > index_plugins:  # Replace all white space chars inside [ ] brackets with the 0 char.
                formatted_line = re.sub(r"\[(.*?)]", lambda x: "[" + re.sub(r"\s", "0", x.group(1)) + "]", line)
                crash_data[index] = formatted_line
        with file.open("w", encoding="utf-8", errors="ignore") as crash_log:
            crash_log.writelines(crash_data)

brackets_pattern = re.compile(r"\[(.*?)]")
whitespace_pattern = re.compile(r"\s")

def crashlogs_reformat_optimized(log_path: Path, remove_list: list[str]) -> None:
    """Optimized crashlogs reformat function that extracts metadata and reformats in a single pass."""
    index_plugins = -1
    simple_logs = False
    reformatted_data = []

    if not isinstance(remove_list, list):
        raise TypeError(f"Invalid remove_list type: {type(remove_list)}")

    # Precompile the regex outside the loop for performance improvement
    brackets_pattern = re.compile(r"\[(.*?)]")
    whitespace_pattern = re.compile(r"\s")

    def replace_whitespace(match: re.Match) -> str:
        content = match.group(1)
        return f"[{whitespace_pattern.sub('0', content)}]"

    with log_path.open(encoding="utf-8", errors="ignore") as file:
        for index, line in enumerate(file):
            line_lower = line.lower()

            # Extract metadata during processing
            if index_plugins == -1 and "plugins:" in line_lower:
                index_plugins = index

            if "simplify_logs_marker" in line_lower:
                simple_logs = True

            # Remove lines if "simplify logs" is enabled
            if simple_logs and any(remove_item in line_lower for remove_item in remove_list):
                continue

            # Only apply regex substitution after index_plugins
            if index > index_plugins:
                line = brackets_pattern.sub(replace_whitespace, line)

            reformatted_data.append(line)

    # Use a single write operation at the end for efficiency
    with log_path.open("w", encoding="utf-8", errors="ignore") as file:
        file.writelines(reformatted_data)
def crashlogs_reformat_parallel(log_paths: list[Path], remove_list: list[str]) -> None:
    """Parallel reformatting of multiple crash logs."""

    def process_log(log_path: Path) -> None:
        """Process a single log file."""
        crashlogs_reformat_optimized(log_path, remove_list)

    # Use ThreadPoolExecutor to run the log reformatting in parallel
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_log, log_path): log_path for log_path in log_paths}

        for future in as_completed(futures):
            log_path = futures[future]
            try:
                future.result()
            except Exception as e:  # noqa: BLE001
                print(f"Error processing {log_path}: {e}")

# ================================================
# CRASH LOG SCAN START
# ================================================
def crashlogs_scan() -> None:
    pluginsearch = re.compile(r"\s*\[(FE:([0-9A-F]{3})|[0-9A-F]{2})\]\s*([[\]()+%,&'.\w\s-]+?(?:\.es[pml])+)", flags=re.IGNORECASE)

    print("REFORMATTING CRASH LOGS, PLEASE WAIT...\n")
    # crashlogs_reformat()
    crashlog_list = crashlogs_get_files()
    remove_list: list[str] = CMain.yaml_settings(CMain.YAML.Main, "exclude_log_records") # type: ignore
    crashlogs_reformat_parallel(crashlog_list, remove_list) # type: ignore

    print("SCANNING CRASH LOGS, PLEASE WAIT...\n")
    scan_start_time = time.perf_counter()
    # ================================================
    # Grabbing YAML values is time expensive, so keep these out of the main file loop.
    classic_game_hints: list[str] = CMain.yaml_settings(CMain.YAML.Game, "Game_Hints")  # type: ignore
    classic_records_list: list[str] = CMain.yaml_settings(CMain.YAML.Main, "catch_log_records")  # type: ignore
    classic_version: str = CMain.yaml_settings(CMain.YAML.Main, "CLASSIC_Info.version")  # type: ignore
    classic_version_date: str = CMain.yaml_settings(CMain.YAML.Main, "CLASSIC_Info.version_date")  # type: ignore

    crashgen_name: str = CMain.yaml_settings(CMain.YAML.Game, "Game_Info.CRASHGEN_LogName")  # type: ignore
    crashgen_latest_og: str = CMain.yaml_settings(CMain.YAML.Game, "Game_Info.CRASHGEN_LatestVer")  # type: ignore
    crashgen_latest_vr: str = CMain.yaml_settings(CMain.YAML.Game, "GameVR_Info.CRASHGEN_LatestVer")  # type: ignore
    crashgen_ignore: list[str] = CMain.yaml_settings(CMain.YAML.Game, f"Game{CMain.gamevars["vr"]}_Info.CRASHGEN_Ignore")  # type: ignore

    warn_noplugins: str = CMain.yaml_settings(CMain.YAML.Game, "Warnings_CRASHGEN.Warn_NOPlugins")  # type: ignore
    warn_outdated: str = CMain.yaml_settings(CMain.YAML.Game, "Warnings_CRASHGEN.Warn_Outdated")  # type: ignore
    xse_acronym: str = CMain.yaml_settings(CMain.YAML.Game, "Game_Info.XSE_Acronym")  # type: ignore

    game_ignore_plugins: list[str] = CMain.yaml_settings(CMain.YAML.Game, "Crashlog_Plugins_Exclude")  # type: ignore
    game_ignore_records: list[str] = CMain.yaml_settings(CMain.YAML.Game, "Crashlog_Records_Exclude")  # type: ignore
    suspects_error_list: dict[str, str] = CMain.yaml_settings(CMain.YAML.Game, "Crashlog_Error_Check")  # type: ignore
    suspects_stack_list: dict[str, list[str]] = CMain.yaml_settings(CMain.YAML.Game, "Crashlog_Stack_Check")  # type: ignore

    autoscan_text: str = CMain.yaml_settings(CMain.YAML.Main, f"CLASSIC_Interface.autoscan_text_{CMain.gamevars["game"]}")  # type: ignore
    remove_list: list[str] = CMain.yaml_settings(CMain.YAML.Main, "exclude_log_records")  # type: ignore
    ignore_list: list[str] = CMain.yaml_settings(CMain.YAML.Ignore, f"CLASSIC_Ignore_{CMain.gamevars["game"]}")  # type: ignore

    game_mods_conf: dict[str, str] = CMain.yaml_settings(CMain.YAML.Game, "Mods_CONF")  # type: ignore
    game_mods_core: dict[str, str] = CMain.yaml_settings(CMain.YAML.Game, "Mods_CORE")  # type: ignore
    games_mods_core_folon: dict[str, str] = CMain.yaml_settings(CMain.YAML.Game, "Mods_CORE_FOLON")  # type: ignore
    game_mods_freq: dict[str, str] = CMain.yaml_settings(CMain.YAML.Game, "Mods_FREQ")  # type: ignore
    game_mods_opc2: dict[str, str] = CMain.yaml_settings(CMain.YAML.Game, "Mods_OPC2")  # type: ignore
    game_mods_solu: dict[str, str] = CMain.yaml_settings(CMain.YAML.Game, "Mods_SOLU")  # type: ignore

    ignore_list: list[str] = CMain.yaml_settings(CMain.YAML.Ignore, f"CLASSIC_Ignore_{CMain.gamevars["game"]}")  # type: ignore
    # ================================================
    if CMain.classic_settings("FCX Mode"):
        main_files_check = CMain.main_combined_result()
        game_files_check = CGame.game_combined_result()
    else:
        main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
        game_files_check = ""

    def detect_mods_single(yaml_dict: dict[str, str]) -> bool:
        """Optimized detection of single mods by checking plugin names."""
        trigger_mod_found = False

        # Precompute a lowercased set of all plugin names for fast lookups
        plugin_names_lower = {plugin_name.lower() for plugin_name in crashlog_plugins}

        for mod_name, mod_warn in yaml_dict.items():
            mod_name_lower = mod_name.lower()

            # Check if the mod exists in plugin names using set intersection
            if any(mod_name_lower in plugin for plugin in plugin_names_lower):
                # Handle case where mod_name is not in crashlog_plugins dictionary
                plugin_name_in_log = next(
                    (plugin for plugin in crashlog_plugins if mod_name_lower in plugin.lower()), None
                )
                if plugin_name_in_log:
                    # If no warning is present, raise an exception
                    if mod_warn:
                        autoscan_report.append(f"[!] FOUND : [{crashlog_plugins[plugin_name_in_log]}] {mod_warn}")
                    else:
                        raise ValueError(f"ERROR: {mod_name} has no warning in the database!")

                # Set mod_found trigger
                trigger_mod_found = True

        return trigger_mod_found

    def detect_mods_double(yaml_dict: dict[str, str]) -> bool:
        """Optimized detection of mods with split names, checking two parts."""
        trigger_mod_found = False

        # Precompute a lowercased set of all plugin names for fast lookups
        plugin_names_lower = {plugin_name.lower() for plugin_name in crashlog_plugins}

        for mod_name, mod_warn in yaml_dict.items():
            # Split the mod name into two parts
            mod_split = mod_name.lower().split(" | ", 1)
            if len(mod_split) != 2:
                raise ValueError(f"Invalid mod format: {mod_name}")

            # Check if both parts of the mod are in plugin names
            mod1_found = any(mod_split[0] in plugin for plugin in plugin_names_lower)
            mod2_found = any(mod_split[1] in plugin for plugin in plugin_names_lower)

            if mod1_found and mod2_found:
                if mod_warn:
                    autoscan_report.append(f"[!] CAUTION : {mod_warn}")
                else:
                    raise ValueError(f"ERROR: {mod_name} has no warning in the database!")
                trigger_mod_found = True

        return trigger_mod_found

    def detect_mods_important(yaml_dict: dict[str, str]) -> None:
        """Optimized detection of important mods without Vulkan Renderer or GPU rival checks."""

        # Precompute a lowercased set of all plugin names for fast lookups
        plugin_names_lower = {plugin_name.lower() for plugin_name in crashlog_plugins}

        for mod_name, mod_warn in yaml_dict.items():
            # Split mod name into two parts if it contains a " | " separator
            mod_split = mod_name.split(" | ", 1)

            # Check if the first part of the mod name is found in plugin names
            mod_found = any(mod_split[0].lower() in plugin for plugin in plugin_names_lower)

            if mod_found:
                autoscan_report.append(f"✔️ {mod_split[1]} is installed!\n\n")
            else:
                autoscan_report.append(f"❌ {mod_split[1]} is not installed!\n{mod_warn}\n")


    def crashlog_generate_segment(segment_start: str, segment_end: str, crash_data: list[str]) -> list[str]:
        segment_start = segment_start.lower()
        segment_end = segment_end.lower()
        start_index = -1
        end_index = len(crash_data)

        # Single pass to identify start and end indices
        for index, line in enumerate(crash_data):
            line_lower = line.lower()

            # Identify start index if not already found
            if start_index == -1 and segment_start in line_lower:
                start_index = index + 1  # Start after the line containing segment_start

            # Identify end index once start has been found
            elif start_index != -1 and segment_end in line_lower:
                end_index = index
                break  # We can exit early once the end index is found

        # If start_index was never found, return an empty list
        if start_index == -1:
            return []

        # Extract the segment while filtering unwanted lines
        return [
            s_line.strip()
            for s_line in crash_data[start_index:end_index]
            if all(item.lower() not in s_line.lower() for item in remove_list)
        ]

    scan_failed_list: list[str] = []
    user_folder = Path.home()
    stats_crashlog_scanned = stats_crashlog_incomplete = stats_crashlog_failed = 0
    CMain.logger.info(f"- - - INITIATED CRASH LOG FILE SCAN >>> CURRENTLY SCANNING {len(crashlog_list)} FILES")
    for crashlog_file in crashlog_list:
        autoscan_report = []
        trigger_plugin_limit = trigger_plugins_loaded = trigger_scan_failed = False
        with crashlog_file.open(encoding="utf-8", errors="ignore") as crash_log:
            crash_data = crash_log.readlines()

        autoscan_report.extend([f"{crashlog_file.name} -> AUTOSCAN REPORT GENERATED BY {classic_version} \n",
                                "# FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR # \n",
                                "# PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES # \n",
                                "====================================================\n"])

        # ================================================
        # 1) CHECK EXISTENCE AND INDEXES OF EACH SEGMENT
        # ================================================

        # Set default index values incase actual index is not found.
        try:
            index_crashgenver = next(index for index, item in enumerate(crash_data) if index < 10 and crashgen_name and crashgen_name.lower() in item.lower())
        except StopIteration:
            index_crashgenver = 1
        try:
            index_mainerror = next(index for index, item in enumerate(crash_data) if index < 10 and "unhandled exception" in item.lower())
        except StopIteration:
            index_mainerror = 3

        # ================================================
        # 2) GENERATE REQUIRED SEGMENTS FROM THE CRASH LOG
        # ================================================
        segment_allmodules = crashlog_generate_segment("modules:", f"{xse_acronym.lower()} plugins:", crash_data)  # noqa: F841
        segment_xsemodules = crashlog_generate_segment(f"{xse_acronym.lower()} plugins:", "plugins:", crash_data)
        segment_callstack = crashlog_generate_segment("probable call stack:", "modules:", crash_data)
        segment_crashgen = crashlog_generate_segment("[compatibility]", "system specs:", crash_data)
        segment_system = crashlog_generate_segment("system specs:", "probable call stack:", crash_data)
        segment_plugins = crashlog_generate_segment("plugins:", "???????", crash_data)  # Non-existent value makes it go to last line.
        segment_callstack_intact = "".join(segment_callstack)
        if not segment_plugins:
            stats_crashlog_incomplete += 1
        if len(crash_data) < 20:
            stats_crashlog_scanned -= 1
            stats_crashlog_failed += 1
            trigger_scan_failed = True

        # ================== MAIN ERROR ==================
        try:
            crashlog_mainerror = crash_data[index_mainerror]
            if "|" in crashlog_mainerror:
                crashlog_errorsplit = crashlog_mainerror.split("|", 1)
                autoscan_report.append(f"\nMain Error: {crashlog_errorsplit[0]}\n{crashlog_errorsplit[1]}\n")
            else:
                autoscan_report.append(f"\nMain Error: {crashlog_mainerror}\n")
        except IndexError:
            crashlog_mainerror = "UNKNOWN"
            autoscan_report.append(f"\nMain Error: {crashlog_mainerror}\n")

        # =============== CRASHGEN VERSION ===============
        crashlog_crashgen = crash_data[index_crashgenver].strip()
        autoscan_report.append(f"Detected {crashgen_name} Version: {crashlog_crashgen} \n")
        if crashlog_crashgen in (crashgen_latest_og, crashgen_latest_vr):
            autoscan_report.append(f"* You have the latest version of {crashgen_name}! *\n\n")
        else:
            autoscan_report.append(f"{warn_outdated} \n")

        # ======= REQUIRED LISTS, DICTS AND CHECKS =======
        ignore_plugins_list = [item.lower() for item in ignore_list] if ignore_list else []

        crashlog_GPUAMD = crashlog_GPUNV = False
        crashlog_plugins: dict[str, str] = {}
        plugin_names_lower = {plugin_name.lower() for plugin_name in crashlog_plugins}

        if any(f"{CMain.gamevars["game"]}.esm" in elem for elem in segment_plugins):
            trigger_plugins_loaded = True
        else:
            stats_crashlog_incomplete += 1

        # ================================================
        # 3) CHECK EACH SEGMENT AND CREATE REQUIRED VALUES
        # ================================================

        # CHECK GPU TYPE FOR CRASH LOG
        crashlog_GPUAMD = any("GPU #1" in elem and "AMD" in elem for elem in segment_system)
        crashlog_GPUNV = any("GPU #1" in elem and "Nvidia" in elem for elem in segment_system)

        # IF LOADORDER FILE EXISTS, USE ITS PLUGINS
        loadorder_path = Path("loadorder.txt")
        if loadorder_path.exists():
            autoscan_report.extend([
                "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n",
                "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
                "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n"
            ])

            # Read loadorder.txt efficiently and pre-lowercase data for faster comparisons
            with loadorder_path.open(encoding="utf-8", errors="ignore") as loadorder_file:
                loadorder_data = [line.strip().lower() for line in loadorder_file.readlines()]

            # Efficient plugin check with early exit for all() usage
            for elem in loadorder_data[1:]:  # Ignore the first line
                if not any(elem in item.lower() for item in crashlog_plugins):
                    crashlog_plugins[elem] = "LO"

            trigger_plugins_loaded = True

        else:  # OTHERWISE, USE PLUGINS FROM CRASH LOG
            for elem in segment_plugins:
                if "[FF]" in elem:
                    trigger_plugin_limit = True

                # Perform regex search with precompiled regex if possible
                pluginmatch = pluginsearch.match(elem)

                if pluginmatch is not None:
                    plugin_fid = pluginmatch.group(1)
                    plugin_name = pluginmatch.group(3).lower()  # Pre-lowercase for faster comparisons

                    if plugin_fid is not None and not any(plugin_name in item.lower() for item in crashlog_plugins):
                        crashlog_plugins[plugin_name] = plugin_fid.replace(":", "")
                    elif plugin_name and "dll" in plugin_name:
                        crashlog_plugins[plugin_name] = "DLL"
                    else:
                        crashlog_plugins[plugin_name] = "???"


        for elem in segment_xsemodules:
            # SOME IMPORTANT DLLs HAVE A VERSION, REMOVE IT
            elem = elem.strip()
            if ".dll v" in elem:
                elem_parts = elem.split(" v", 1)
                elem = elem_parts[0]
            if all(elem not in item for item in crashlog_plugins):
                crashlog_plugins[elem] = "DLL"

        """for elem in segment_allmodules:
            # SOME IMPORTANT DLLs ONLY APPEAR UNDER ALL MODULES
            if "vulkan" in elem.lower():
                elem_parts = elem.strip().split(" ", 1)
                elem_parts[1] = "DLL"
                if all(elem_parts[0] not in item for item in crashlog_plugins):
                    crashlog_plugins[elem_parts[0]] = elem_parts[1]"""

        # CHECK IF THERE ARE ANY PLUGINS IN THE IGNORE TOML
        if ignore_plugins_list:
            ignore_plugins_lower = {item.lower() for item in ignore_plugins_list or []}  # type: ignore # Pre-lower the ignore list once
            plugins_to_remove = [plugin for plugin in crashlog_plugins if plugin.lower() in ignore_plugins_lower]
            for plugin in plugins_to_remove:
                del crashlog_plugins[plugin]

        # Append autoscan report
        autoscan_report.extend([
            "====================================================\n",
            "CHECKING IF LOG MATCHES ANY KNOWN CRASH SUSPECTS...\n",
            "====================================================\n"
        ])

        # Check for DLL involvement in crash
        if ".dll" in crashlog_mainerror.lower() and "tbbmalloc" not in crashlog_mainerror.lower():
            autoscan_report.extend([
                "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \n",
                "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n-----\n"
            ])

        # Set maximum warning length and check for suspects in error list
        max_warn_length = 30
        trigger_suspect_found = False

        # Optimized suspect search in crashlog_mainerror
        for error in suspects_error_list:
            error_split = error.split(" | ", 1)
            if error_split[1] in crashlog_mainerror:
                error_split[1] = error_split[1].ljust(max_warn_length, ".")
                autoscan_report.append(f"# Checking for {error_split[1]} SUSPECT FOUND! > Severity : {error_split[0]} # \n-----\n")
                trigger_suspect_found = True

        # Check for suspects in the call stack
        for key in suspects_stack_list:
            key_split = key.split(" | ", 1)
            error_req_found = error_opt_found = stack_found = False
            item_list = suspects_stack_list.get(key, [])

            if not isinstance(item_list, list):
                raise TypeError

            has_required_item = any("ME-REQ|" in elem for elem in item_list)

            # Optimize the search through the item list
            for item in item_list:
                if "|" in item:
                    item_split = item.split("|", 1)
                    item_type, item_value = item_split[0], item_split[1]

                    if item_type == "ME-REQ" and item_value in crashlog_mainerror:
                        error_req_found = True
                    elif item_type == "ME-OPT" and item_value in crashlog_mainerror:
                        error_opt_found = True
                    elif item_type.isdecimal():
                        if segment_callstack_intact.count(item_value) >= int(item_type):
                            stack_found = True
                    elif item_type == "NOT" and item_value in segment_callstack_intact:
                        break  # Exit early if the NOT condition is found
                elif item in segment_callstack_intact:
                    stack_found = True

            # print(f"TEST: {error_req_found} | {error_opt_found} | {stack_found}")
            if has_required_item:
                if error_req_found:
                    key_split[1] = key_split[1].ljust(max_warn_length, ".")
                    autoscan_report.append(f"# Checking for {key_split[1]} SUSPECT FOUND! > Severity : {key_split[0]} # \n-----\n")
                    trigger_suspect_found = True
            elif error_opt_found or stack_found:
                key_split[1] = key_split[1].ljust(max_warn_length, ".")
                autoscan_report.append(f"# Checking for {key_split[1]} SUSPECT FOUND! > Severity : {key_split[0]} # \n-----\n")
                trigger_suspect_found = True

        if trigger_suspect_found:
            autoscan_report.extend(["* FOR DETAILED DESCRIPTIONS AND POSSIBLE SOLUTIONS TO ANY ABOVE DETECTED CRASH SUSPECTS *\n",
                                    "* SEE: https://docs.google.com/document/d/17FzeIMJ256xE85XdjoPvv_Zi3C5uHeSTQh6wOZugs4c *\n\n"])
        else:
            autoscan_report.extend(["# FOUND NO CRASH ERRORS / SUSPECTS THAT MATCH THE CURRENT DATABASE #\n",
                                    "Check below for mods that can cause frequent crashes and other problems.\n\n"])

        autoscan_report.extend(["====================================================\n",
                                "CHECKING IF NECESSARY FILES/SETTINGS ARE CORRECT...\n",
                                "====================================================\n"])

        # Precompute lowercase values to avoid repeated .lower() calls
        segment_xsemodules_lower = [elem.lower() for elem in segment_xsemodules]
        crashlog_mainerror_lower = crashlog_mainerror.lower()  # noqa: F841

        Is_XCellPresent = any("x-cell-fo4.dll" in elem for elem in segment_xsemodules_lower)
        Is_BakaScrapheapPresent = any("bakascrapheap.dll" in elem for elem in segment_xsemodules_lower)

        if not CMain.classic_settings("FCX Mode"):
            autoscan_report.extend([
                "* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n",
                "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n"
            ])

            if Is_XCellPresent:
                crashgen_ignore.extend(["havokmemorysystem", "scaleformallocator", "smallblockallocator"])

            for line in segment_crashgen:
                line_lower = line.lower()  # Lowercase the line once and reuse

                if "false" in line_lower and all(elem not in line_lower for elem in crashgen_ignore):
                    line_split = line.split(":", 1)
                    autoscan_report.append(f"* NOTICE : {line_split[0].strip()} is disabled in your {crashgen_name} settings, is this intentional? * \n-----\n")

                if "achievements:" in line_lower:
                    if "true" in line_lower and any(dll in elem for dll in ("achievements.dll", "unlimitedsurvivalmode.dll") for elem in segment_xsemodules_lower):
                        autoscan_report.extend([
                            "# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE # \n",
                            f" FIX: Open {crashgen_name}'s TOML file and change Achievements to FALSE, this prevents conflicts with {crashgen_name}.\n-----\n"
                        ])
                    else:
                        autoscan_report.append(f"✔️ Achievements parameter is correctly configured in your {crashgen_name} settings! \n-----\n")

                if "memorymanager:" in line_lower:
                    if "true" in line_lower and Is_BakaScrapheapPresent and not Is_XCellPresent:
                        autoscan_report.extend([
                            "# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but MemoryManager parameter is set to TRUE # \n",
                            f" FIX: Open {crashgen_name}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with {crashgen_name}.\n-----\n"
                        ])
                    elif "true" in line_lower and Is_XCellPresent and not Is_BakaScrapheapPresent:
                        autoscan_report.extend([
                            "# ❌ CAUTION : X-Cell is installed, but MemoryManager parameter is set to TRUE # \n",
                            f" FIX: Open {crashgen_name}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with X-Cell.\n-----\n"
                        ])
                    elif "false" in line_lower and Is_XCellPresent and not Is_BakaScrapheapPresent:
                        autoscan_report.extend([f"✔️ Memory Manager parameter is correctly configured for use with X-Cell in your {crashgen_name} settings! \n-----\n"])
                    else:
                        autoscan_report.append(f"✔️ Memory Manager parameter is correctly configured in your {crashgen_name} settings! \n-----\n")

                # Common check function for BSTextureStreamerLocalHeap and similar options
                def check_setting(setting_name: str, line_lower: str, is_true_case: bool, true_message: str, false_message: str, autoscan_report: list[str]) -> None:  # noqa: PLR0913
                    if setting_name in line_lower:
                        if "true" in line_lower and is_true_case:
                            autoscan_report.extend([f"# ❌ CAUTION : X-Cell is installed, but {setting_name} parameter is set to TRUE # \n", true_message])
                        elif "false" in line_lower and is_true_case:
                            autoscan_report.append(false_message)

                check_setting(
                    "bstexturestreamerlocalheap:",
                    line_lower,
                    Is_XCellPresent,
                    f" FIX: Open {crashgen_name}'s TOML file and change BSTextureStreamerLocalHeap to FALSE, this prevents conflicts with X-Cell.\n-----\n",
                    f"✔️ BSTextureStreamerLocalHeap parameter is correctly configured for use with X-Cell in your {crashgen_name} settings! \n-----\n",
                    autoscan_report
                )

                check_setting(
                    "havokmemorysystem:",
                    line_lower,
                    Is_XCellPresent,
                    f" FIX: Open {crashgen_name}'s TOML file and change HavokMemorySystem to FALSE, this prevents conflicts with X-Cell.\n-----\n",
                    f"✔️ HavokMemorySystem parameter is correctly configured for use with X-Cell in your {crashgen_name} settings! \n-----\n",
                    autoscan_report
                )

                check_setting(
                    "scaleformallocator:",
                    line_lower,
                    Is_XCellPresent,
                    f" FIX: Open {crashgen_name}'s TOML file and change ScaleformAllocator to FALSE, this prevents conflicts with X-Cell.\n-----\n",
                    f"✔️ ScaleformAllocator parameter is correctly configured for use with X-Cell in your {crashgen_name} settings! \n-----\n",
                    autoscan_report
                )

                check_setting(
                    "smallblockallocator:",
                    line_lower,
                    Is_XCellPresent,
                    f" FIX: Open {crashgen_name}'s TOML file and change SmallBlockAllocator to FALSE, this prevents conflicts with X-Cell.\n-----\n",
                    f"✔️ SmallBlockAllocator parameter is correctly configured for use with X-Cell in your {crashgen_name} settings! \n-----\n",
                    autoscan_report
                )

                if "f4ee:" in line_lower:
                    if "false" in line_lower and any("f4ee.dll" in elem for elem in segment_xsemodules_lower):
                        autoscan_report.extend([
                            "# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under [Compatibility] is set to FALSE # \n",
                            f" FIX: Open {crashgen_name}'s TOML file and change F4EE to TRUE, this prevents bugs and crashes from Looks Menu.\n-----\n"
                        ])
                    else:
                        autoscan_report.append(f"✔️ F4EE (Looks Menu) parameter is correctly configured in your {crashgen_name} settings! \n-----\n")



        else:
            autoscan_report.extend(["* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n",
                                    "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n"])

        autoscan_report.append(main_files_check)
        if game_files_check:
            autoscan_report.append(game_files_check)

        autoscan_report.extend(["====================================================\n",
                                "CHECKING FOR MODS THAT CAN CAUSE FREQUENT CRASHES...\n",
                                "====================================================\n"])

        if trigger_plugins_loaded:
            if detect_mods_single(game_mods_freq):
                autoscan_report.extend(["# [!] CAUTION : ANY ABOVE DETECTED MODS HAVE A MUCH HIGHER CHANCE TO CRASH YOUR GAME! #\n",
                                        "* YOU CAN DISABLE ANY / ALL OF THEM TEMPORARILY TO CONFIRM THEY CAUSED THIS CRASH. * \n\n"])
            else:
                autoscan_report.extend(["# FOUND NO PROBLEMATIC MODS THAT MATCH THE CURRENT DATABASE FOR THIS CRASH LOG #\n",
                                        "THAT DOESN'T MEAN THERE AREN'T ANY! YOU SHOULD RUN PLUGIN CHECKER IN WRYE BASH \n",
                                        "Plugin Checker Instructions: https://www.nexusmods.com/fallout4/articles/4141 \n\n"])
        else:
            autoscan_report.append(warn_noplugins)

        autoscan_report.extend(["====================================================\n",
                                "CHECKING FOR MODS THAT CONFLICT WITH OTHER MODS...\n",
                                "====================================================\n"])

        if trigger_plugins_loaded:
            if detect_mods_double(game_mods_conf):
                autoscan_report.extend(["# [!] CAUTION : FOUND MODS THAT ARE INCOMPATIBLE OR CONFLICT WITH YOUR OTHER MODS # \n",
                                        "* YOU SHOULD CHOOSE WHICH MOD TO KEEP AND DISABLE OR COMPLETELY REMOVE THE OTHER MOD * \n\n"])
            else:
                autoscan_report.append("# FOUND NO MODS THAT ARE INCOMPATIBLE OR CONFLICT WITH YOUR OTHER MODS # \n\n")
        else:
            autoscan_report.append(warn_noplugins)

        autoscan_report.extend(["====================================================\n",
                                "CHECKING FOR MODS WITH SOLUTIONS & COMMUNITY PATCHES\n",
                                "====================================================\n"])

        if trigger_plugins_loaded:
            if detect_mods_single(game_mods_solu):
                autoscan_report.extend(["# [!] CAUTION : FOUND PROBLEMATIC MODS WITH SOLUTIONS AND COMMUNITY PATCHES # \n",
                                        "[Due to limitations, CLASSIC will show warnings for some mods even if fixes or patches are already installed.] \n",
                                        "[To hide these warnings, you can add their plugin names to the CLASSIC Ignore.yaml file. ONE PLUGIN PER LINE.] \n\n"])
            else:
                autoscan_report.append("# FOUND NO PROBLEMATIC MODS WITH AVAILABLE SOLUTIONS AND COMMUNITY PATCHES # \n\n")
        else:
            autoscan_report.append(warn_noplugins)

        if CMain.gamevars["game"] == "Fallout4":
            autoscan_report.extend(["====================================================\n",
                                    "CHECKING FOR MODS PATCHED THROUGH OPC INSTALLER...\n",
                                    "====================================================\n"])

            if trigger_plugins_loaded:
                if detect_mods_single(game_mods_opc2):
                    autoscan_report.extend(["\n* FOR PATCH REPOSITORY THAT PREVENTS CRASHES AND FIXES PROBLEMS IN THESE AND OTHER MODS,* \n",
                                            "* VISIT OPTIMIZATION PATCHES COLLECTION: https://www.nexusmods.com/fallout4/mods/54872 * \n\n"])
                else:
                    autoscan_report.append("# FOUND NO PROBLEMATIC MODS THAT ARE ALREADY PATCHED THROUGH THE OPC INSTALLER # \n\n")
            else:
                autoscan_report.append(warn_noplugins)

        autoscan_report.extend(["====================================================\n",
                                "CHECKING IF IMPORTANT PATCHES & FIXES ARE INSTALLED\n",
                                "====================================================\n"])

        if trigger_plugins_loaded:
            if any("londonworldspace" in plugin.lower() for plugin in crashlog_plugins):
                detect_mods_important(games_mods_core_folon)
            else:
                detect_mods_important(game_mods_core)
        else:
            autoscan_report.append(warn_noplugins)

        autoscan_report.extend(["====================================================\n",
                                "SCANNING THE LOG FOR SPECIFIC (POSSIBLE) SUSPECTS...\n",
                                "====================================================\n"])

        if trigger_plugin_limit:
            warn_plugin_limit: str = CMain.yaml_settings(CMain.YAML.Main, "Mods_Warn.Mods_Plugin_Limit") # type: ignore
            autoscan_report.append(warn_plugin_limit)

        # ================================================

        autoscan_report.append("# LIST OF (POSSIBLE) PLUGIN SUSPECTS #\n")

        # Pre-lowercase crashlog_plugins and game_ignore_plugins once
        crashlog_plugins_lower = {plugin.lower() for plugin in crashlog_plugins}
        game_ignore_plugins_lower = {ignore.lower() for ignore in game_ignore_plugins}

        # Use a list comprehension to find plugin matches
        plugins_matches = [
            plugin for line in map(str.lower, segment_callstack)
            for plugin in crashlog_plugins_lower
            if plugin in line and "modified by:" not in line and all(ignore not in plugin for ignore in game_ignore_plugins_lower)
        ]

        # If plugin matches are found, build the report
        if plugins_matches:
            plugins_found = dict(Counter(plugins_matches))
            if plugins_found:
                autoscan_report.extend([f"- {plugin} | {count}\n" for plugin, count in plugins_found.items()])
                autoscan_report.extend([
                    "\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n",
                    f"These Plugins were caught by {crashgen_name} and some of them might be responsible for this crash.\n",
                    "You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n"
                ])
        else:
            autoscan_report.append("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n")

        # ================================================
        autoscan_report.append("# LIST OF (POSSIBLE) FORM ID SUSPECTS #\n")

        # Filter and clean the segment_callstack in one step
        formids_matches = [line.replace("0x", "").strip() for line in segment_callstack if "id:" in line.lower() and "0xFF" not in line]

        if formids_matches:
            formids_found = dict(Counter(sorted(formids_matches)))

            # Precompute paths to avoid checking in every loop iteration
            game_name = CMain.gamevars["game"]
            formid_main_db = Path(f"CLASSIC Data/databases/{game_name} FormIDs Main.db")
            formid_local_db = Path(f"CLASSIC Data/databases/{game_name} FormIDs Local.db")
            db_exists = formid_main_db.exists() or formid_local_db.exists()

            show_formid_values = CMain.classic_settings("Show FormID Values")

            for formid_full, count in formids_found.items():
                formid_split = formid_full.split(": ", 1)

                if len(formid_split) < 2:
                    continue  # Skip if the formid doesn't split correctly

                formid_prefix = formid_split[1][:2]  # Extract formid prefix once
                formid_suffix = formid_split[1][2:]  # Extract the rest of the formid

                # Match the plugin by formid prefix
                for plugin, plugin_id in crashlog_plugins.items():
                    if str(plugin_id) == formid_prefix:
                        # If Show FormID Values is enabled and the database exists
                        if show_formid_values and db_exists:
                            report = get_entry(formid_suffix, plugin)
                            if report:
                                autoscan_report.append(f"- {formid_full} | [{plugin}] | {report} | {count}\n")
                            else:
                                autoscan_report.append(f"- {formid_full} | [{plugin}] | {count}\n")
                            break  # Break after finding the matching plugin

                        # If Show FormID Values is disabled or no database exists
                        autoscan_report.append(f"- {formid_full} | [{plugin}] | {count}\n")
                        break  # Break after finding the matching plugin

            autoscan_report.extend([
                "\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
                f"These Form IDs were caught by {crashgen_name} and some of them might be related to this crash.\n",
                "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n"
            ])
        else:
            autoscan_report.append("* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n")


        # ================================================

        autoscan_report.append("# LIST OF DETECTED (NAMED) RECORDS #\n")

        # Pre-lowercase classic_records_list and game_ignore_records for efficient comparison
        classic_records_lower = {item.lower() for item in classic_records_list}
        game_ignore_records_lower = {record.lower() for record in game_ignore_records}

        # Use list comprehension for filtering matches in segment_callstack
        records_matches = [
            line[30:].strip() if "[RSP+" in line else line.strip()
            for line in segment_callstack
            if any(item in line.lower() for item in classic_records_lower)
            and all(record not in line.lower() for record in game_ignore_records_lower)
        ]

        # If records are found, count and display them
        if records_matches:
            records_found = dict(Counter(sorted(records_matches)))
            autoscan_report.extend([f"- {record} | {count}\n" for record, count in records_found.items()])

            autoscan_report.extend([
                "\n[Last number counts how many times each Named Record shows up in the crash log.]\n",
                f"These records were caught by {crashgen_name} and some of them might be related to this crash.\n",
                "Named records should give extra info on involved game objects, record types or mod files.\n\n"
            ])
        else:
            autoscan_report.append("* COULDN'T FIND ANY NAMED RECORDS *\n\n")


        # ============== AUTOSCAN REPORT END ==============
        if CMain.gamevars["game"] == "Fallout4":
            autoscan_report.append(autoscan_text)
        autoscan_report.append(f"{classic_version} | {classic_version_date} | END OF AUTOSCAN \n")

        # CHECK IF SCAN FAILED
        stats_crashlog_scanned += 1
        if trigger_scan_failed:
            scan_failed_list.append(crashlog_file.name)

        # HIDE PERSONAL USERNAME
        for line in autoscan_report:
            if user_folder.name in line:
                line.replace(f"{user_folder.parent}\\{user_folder.name}", "******").replace(f"{user_folder.parent}/{user_folder.name}", "******")

        # WRITE AUTOSCAN REPORT TO FILE
        autoscan_path = crashlog_file.with_name(crashlog_file.stem + "-AUTOSCAN.md")
        with autoscan_path.open("w", encoding="utf-8", errors="ignore") as autoscan_file:
            CMain.logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
            autoscan_output = "".join(autoscan_report)
            autoscan_file.write(autoscan_output)

        if trigger_scan_failed and CMain.classic_settings("Move Unsolved Logs"):
            backup_path = Path("CLASSIC Backup/Unsolved Logs")
            backup_path.mkdir(parents=True, exist_ok=True)
            autoscan_filepath = crashlog_file.with_name(crashlog_file.stem + "-AUTOSCAN.md")
            crash_move = backup_path / crashlog_file.name
            scan_move = backup_path / autoscan_file.name

            if crashlog_file.exists():
                shutil.copy2(crashlog_file, crash_move)
            if autoscan_filepath.exists():
                shutil.copy2(autoscan_filepath, scan_move)

    # CHECK FOR FAILED OR INVALID CRASH LOGS
    scan_invalid_list = list(Path.cwd().glob("crash-*.txt"))
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
    CMain.logger.info("- - - COMPLETED CRASH LOG FILE SCAN >>> ALL AVAILABLE LOGS SCANNED")
    print("SCAN COMPLETE! (IT MIGHT TAKE SEVERAL SECONDS FOR SCAN RESULTS TO APPEAR)")
    print("SCAN RESULTS ARE AVAILABLE IN FILES NAMED crash-date-and-time-AUTOSCAN.md \n")
    print(f"{random.choice(classic_game_hints)}\n-----")
    print(f"Scanned all available logs in {str(time.perf_counter() - 0.5 - scan_start_time)[:5]} seconds.")
    print(f"Number of Scanned Logs (No Autoscan Errors): {stats_crashlog_scanned}")
    print(f"Number of Incomplete Logs (No Plugins List): {stats_crashlog_incomplete}")
    print(f"Number of Failed Logs (Autoscan Can't Scan): {stats_crashlog_failed}\n-----")
    if CMain.gamevars["game"] == "Fallout4":
        print(autoscan_text)
    if stats_crashlog_scanned == 0 and stats_crashlog_incomplete == 0:
        print("\n❌ CLAS found no crash logs to scan or the scan failed.")
        print("    There are no statistics to show (at this time).\n")


if __name__ == "__main__":
    CMain.initialize()
    import argparse

    parser = argparse.ArgumentParser(prog="Crash Log Auto Scanner & Setup Integrity Checker (CLASSIC)", description="All terminal options are saved to the YAML file.")
    # Argument values will simply change INI values since that requires the least refactoring
    # I will figure out a better way in a future iteration, this iteration simply mimics the GUI. - evildarkarchon
    parser.add_argument("--fcx-mode", action=argparse.BooleanOptionalAction, help="Enable (or disable) FCX mode")
    parser.add_argument("--show-fid-values", action=argparse.BooleanOptionalAction, help="Enable (or disable) IMI mode")
    parser.add_argument("--stat-logging", action=argparse.BooleanOptionalAction, help="Enable (or disable) Stat Logging")
    parser.add_argument("--move-unsolved", action=argparse.BooleanOptionalAction, help="Enable (or disable) moving unsolved logs to a separate directory")
    parser.add_argument("--ini-path", type=Path, help="Set the directory that stores the game's INI files.")
    parser.add_argument("--scan-path", type=Path, help="Set which custom directory to scan crash logs from.")
    parser.add_argument("--mods-folder-path", type=Path, help="Set the directory where your mod manager stores your mods (Optional).")
    parser.add_argument("--simplify-logs", action=argparse.BooleanOptionalAction, help="Enable (or disable) Simplify Logs")
    args = parser.parse_args()

    scan_path: Path = args.scan_path  # VSCode gives me type errors because args.* is set at runtime (doesn't know what types it's dealing with).
    ini_path: Path = args.ini_path  # Using intermediate variables with type annotations to satisfy it.
    mods_folder_path: Path = args.mods_folder_path

    # Default output value for an argparse.BooleanOptionalAction is None, and so fails the isinstance check.
    # So it will respect current INI values if not specified on the command line.
    if isinstance(args.fcx_mode, bool) and args.fcx_mode != CMain.classic_settings("FCX Mode"):
        CMain.yaml_settings(CMain.YAML.Settings, "CLASSIC_Settings.FCX Mode", args.fcx_mode)

    if isinstance(args.show_fid_values, bool) and args.show_fid_values != CMain.classic_settings("Show FormID Values"):
        CMain.yaml_settings(CMain.YAML.Settings, "CLASSIC_Settings.IMI Mode", args.imi_mode)

    if isinstance(args.move_unsolved, bool) and args.move_unsolved != CMain.classic_settings("Move Unsolved Logs"):
        CMain.yaml_settings(CMain.YAML.Settings, "CLASSIC_Settings.Move Unsolved", args.args.move_unsolved)

    if isinstance(ini_path, Path) and ini_path.resolve().is_dir() and str(ini_path) != CMain.classic_settings("INI Folder Path"):
        CMain.yaml_settings(CMain.YAML.Settings, "CLASSIC_Settings.INI Folder Path", str(Path(ini_path).resolve()))

    if isinstance(scan_path, Path) and scan_path.resolve().is_dir() and str(scan_path) != CMain.classic_settings("SCAN Custom Path"):
        CMain.yaml_settings(CMain.YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(Path(scan_path).resolve()))

    if isinstance(mods_folder_path, Path) and mods_folder_path.resolve().is_dir() and str(mods_folder_path) != CMain.classic_settings("MODS Folder Path"):
        CMain.yaml_settings(CMain.YAML.Settings, "CLASSIC_Settings.MODS Folder Path", str(Path(mods_folder_path).resolve()))

    if isinstance(args.simplify_logs, bool) and args.simplify_logs != CMain.classic_settings("Simplify Logs"):
        CMain.yaml_settings(CMain.YAML.Settings, "CLASSIC_Settings.Simplify Logs", args.simplify_logs)

    crashlogs_scan()
    os.system("pause")

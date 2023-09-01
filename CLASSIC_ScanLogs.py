# import timeit | RESERVED For timing functions.
import os
import re
import time
import shutil
import random
import logging
from pathlib import Path
from collections import Counter
import CLASSIC_Main as CMain

# Logging levels: debug | info | warning | error | critical | Level in basicConfig is minimum and must be UPPERCASE
logging.basicConfig(level=logging.DEBUG, filename="CLASSIC Journal.log", filemode="a", format="%(asctime)s | %(levelname)s | %(message)s")


# ================================================
# INITIAL TRUNCATING FOR CRASH LOG FILES
# ================================================
def crashlogs_get_files():  # Get paths of all available crash logs.
    logging.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION")
    CLASSIC_folder = os.getcwd()
    CUSTOM_folder = CMain.classic_settings("SCAN Custom Path")
    XSE_folder = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Game_Info", "Docs_Folder_F4SE")
    if CMain.classic_settings("VR Mode"):
        XSE_folder = CMain.yaml_get("CLASSIC Config/CLASSIC FO4VR.yaml", "GameVR_Info", "Docs_Folder_F4SE")

    if Path(XSE_folder).exists():
        xse_crash_files = list(Path(XSE_folder).glob("crash-*.log"))
        if xse_crash_files:
            for crash_file in xse_crash_files:
                destination_file = fr"{CLASSIC_folder}/{crash_file.name}"
                shutil.move(crash_file, destination_file)

    crash_files = list(Path(CLASSIC_folder).glob("crash-*.log"))
    if CUSTOM_folder:
        if Path(CUSTOM_folder).exists():
            crash_files.extend(Path(CUSTOM_folder).glob("crash-*.log"))

    return crash_files


def crashlogs_truncate():  # Remove *useless* lines from all available crash logs.
    logging.info("- - - SIMPLIFY LOGS IS ENABLED -> TRUNCATING ALL AVAILABLE CRASH LOGS")
    crash_files = crashlogs_get_files()
    remove_list = CMain.yaml_get("CLASSIC Config/CLASSIC Main.yaml", "exclude_log_records")
    for file in crash_files:
        with file.open("r", encoding="utf-8", errors="ignore") as crash_log:
            crash_data = crash_log.readlines()
            truncated_lines = [line for line in crash_data if not any(string in line for string in remove_list)]
        with file.open("w", encoding="utf-8", errors="ignore") as crash_log:
            crash_log.writelines(truncated_lines)


def crashlogs_reformat():  # Reformat plugin lists in crash logs, so that old and new CRASHGEN formats match.
    logging.debug("- - - INITIATED CRASH LOG FILE REFORMAT")
    xse_acronym = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Game_Info", "XSE_Acronym")
    if CMain.classic_settings("VR Mode"):
        xse_acronym = CMain.yaml_get("CLASSIC Config/CLASSIC FO4VR.yaml", "GameVR_Info", "XSE_Acronym")

    crash_files = crashlogs_get_files()
    for file in crash_files:
        with file.open("r", encoding="utf-8", errors="ignore") as crash_log:
            crash_data = crash_log.readlines()
            index_plugins = 1
            for index, line in enumerate(crash_data):
                if xse_acronym not in line and "PLUGINS:" in line:
                    index_plugins = index
                    break
            for index, line in enumerate(crash_data):
                if index > index_plugins:  # Replace all white space chars inside [ ] brackets with the 0 char.
                    formatted_line = re.sub(r'\[(.*?)]', lambda x: "[" + re.sub(r'\s', '0', x.group(1)) + "]", line)
                    crash_data[index] = formatted_line
        with file.open("w", encoding="utf-8", errors="ignore") as crash_log:
            crash_log.writelines(crash_data)


# ================================================
# CRASH LOG SCAN START
# ================================================
def crashlogs_scan():
    crashlogs_reformat()
    if CMain.classic_settings("Simplify Logs"):
        crashlogs_truncate()

    # ================================================
    # Grabbing YAML values are time expensive, so keep these out of the main file loop.
    classic_game_hints = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Game_Hints")
    classic_records_list = CMain.yaml_get("CLASSIC Config/CLASSIC Main.yaml", "catch_log_records")
    classic_version = CMain.yaml_get("CLASSIC Config/CLASSIC Main.yaml", "CLASSIC_Info", "version")
    classic_version_date = CMain.yaml_get("CLASSIC Config/CLASSIC Main.yaml", "CLASSIC_Info", "version_date")

    crashgen_latestver = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Game_Info", "CRASHGEN_LatestVer")
    crashgen_logname = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Game_Info", "CRASHGEN_LogName")
    crashgen_vrlatestver = CMain.yaml_get("CLASSIC Config/CLASSIC FO4VR.yaml", "GameVR_Info", "CRASHGEN_LatestVer")

    warn_noplugins = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Warnings_CRASHGEN", "Warn_NOPlugins")
    warn_outdated = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Warnings_CRASHGEN", "Warn_Outdated")
    xse_acronym = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Game_Info", "XSE_Acronym")

    custom_ignore_plugins = CMain.yaml_get("CLASSIC Ignore.yaml", "CLASSIC_Ignore_Fallout4")
    game_ignore_plugins = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Crashlog_Plugins_Exclude")
    game_ignore_records = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Crashlog_Records_Exclude")
    suspects_error_list = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Crashlog_Error_Check")
    suspects_stack_list = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Crashlog_Stack_Check")
    game_mods_conf = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Mods_CONF")
    game_mods_core = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Mods_CORE")
    game_mods_freq = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Mods_FREQ")
    game_mods_opc2 = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Mods_OPC2")
    game_mods_solu = CMain.yaml_get("CLASSIC Config/CLASSIC FO4.yaml", "Mods_SOLU")

    # ================================================
    if CMain.classic_settings("FCX Mode"):
        main_files_check = CMain.func_combined_output()
    else:
        main_files_check = "❌ FCX Mode is not enabled, skipping game files check... \n-----\n"
    
    # DETECT ONE WHOLE KEY (1 MOD) PER LOOP IN YAML DICT
    def detect_mods_single(yaml_dict):
        trigger_mod_found = False
        for mod_name in yaml_dict:
            mod_warn = yaml_dict.get(mod_name)
            for plugin_name in crashlog_plugins:
                plugin_fid = crashlog_plugins.get(plugin_name)
                if mod_name.lower() in plugin_name.lower():
                    autoscan_report.extend([f"[!] FOUND : [{plugin_fid}] ", mod_warn])
                    trigger_mod_found = True
                    break
        return trigger_mod_found

    # DETECT ONE SPLIT KEY (2 MODS) PER LOOP IN YAML DICT
    def detect_mods_double(yaml_dict):
        trigger_mod_found = False
        for mod_name in yaml_dict:
            mod_warn = yaml_dict.get(mod_name)
            mod_split = mod_name.split(' | ', 1)
            mod1_found = mod2_found = False
            for plugin_name in crashlog_plugins:
                if mod_split[0].lower() in plugin_name.lower():
                    mod1_found = True
                    continue
                if mod_split[1].lower() in plugin_name.lower():
                    mod2_found = True
                    continue
            if mod1_found and mod2_found:
                autoscan_report.extend(["[!] CAUTION : ", mod_warn])
                trigger_mod_found = True
        return trigger_mod_found

    # DETECT ONE IMPORTANT CORE AND GPU SPECIFIC MOD PER LOOP IN YAML DICT
    def detect_mods_important(yaml_dict):
        gpu_rival = "nvidia" if (crashlog_GPUAMD or crashlog_GPUI) else "amd" if crashlog_GPUNV else None
        for mod_name in yaml_dict:
            mod_warn = yaml_dict.get(mod_name)
            mod_split = mod_name.split(' | ', 1)
            mod_found = False
            for plugin_name in crashlog_plugins:
                if mod_split[0].lower() in plugin_name.lower():
                    mod_found = True
                    continue
            if mod_found:
                if gpu_rival in mod_warn.lower():
                    autoscan_report.extend([f"❓ {mod_split[1]} is installed, BUT YOU DON'T HAVE AN {gpu_rival.upper()} GPU!\n",
                                            "THIS MOD IS NOT INTENDED FOR YOUR GPU, PLEASE REMOVE IT TO AVOID PROBLEMS!"])
                else:
                    autoscan_report.extend([f"✔️ {mod_split[1]} is installed!\n\n"])
            else:
                if gpu_rival not in mod_warn.lower():
                    autoscan_report.extend([f"❌ {mod_split[1]} is not installed!\n", mod_warn, "\n"])

    print("\nSCANNING LOGS, PLEASE WAIT...\n")
    scan_start_time = time.perf_counter()
    crashlog_list = crashlogs_get_files()
    stats_crashlog_scanned = stats_crashlog_incomplete = stats_crashlog_failed = 0
    logging.info(f"- - - INITIATED CRASH LOG FILE SCAN >>> CURRENTLY SCANNING {len(crashlog_list)} FILES")
    for crashlog_file in crashlog_list:
        autoscan_report = []
        trigger_plugin_limit = False
        trigger_plugins_loaded = False
        with crashlog_file.open("r", encoding="utf-8", errors="ignore") as crash_log:
            crash_data_intact = crash_log.read()
            crash_log.seek(0)  # DON'T FORGET
            crash_data = crash_log.readlines()

        autoscan_report.extend([f"{crashlog_file.name} -> AUTOSCAN REPORT GENERATED BY {classic_version} \n",
                                "# FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR # \n",
                                "# PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES # \n",
                                "====================================================\n"])

        # ================================================
        # 1) CHECK EXISTENCE AND INDEXES OF EACH SEGMENT
        # ================================================

        # Set default initial index values in case specific index is not found.
        index_crashgenver = 1
        index_mainerror = 3
        index_lastline: int = len(crash_data) - 1
        for index, line in enumerate(crash_data):
            if crashgen_logname.lower() in line.lower():
                index_crashgenver = index
            elif "unhandled exception" in line.lower():
                index_mainerror = index

        def crashlog_generate_segment(segment_start, segment_end):
            index_start = index_end = 0
            if segment_start.lower() in crash_data_intact.lower():
                for s_index, s_line in enumerate(crash_data):
                    if segment_start.lower() in s_line.lower():
                        index_start = s_index + 1
                if segment_end.lower() in crash_data_intact.lower():
                    for s_index, s_line in enumerate(crash_data):
                        if segment_end.lower() in s_line.lower():
                            index_end = s_index - 1
                    segment_output = [s_line.strip() for s_line in crash_data[index_start:index_end]]
                else:
                    segment_output = [s_line.strip() for s_line in crash_data[index_start:index_lastline]]
            else:
                segment_output = []
            return segment_output

        # ================================================
        # 2) GENERATE REQUIRED SEGMENTS FROM THE CRASH LOG
        # ================================================
        segment_allmodules = crashlog_generate_segment("modules:", f"{xse_acronym.lower()} plugins:")
        segment_xsemodules = crashlog_generate_segment(f"{xse_acronym.lower()} plugins:", "plugins:")
        segment_callstack = crashlog_generate_segment("probable call stack:", "modules:")
        segment_crashgen = crashlog_generate_segment("[compatibility]", "system specs:")
        segment_system = crashlog_generate_segment("system specs:", "probable call stack:")
        segment_plugins = crashlog_generate_segment("plugins:", "???????")  # Second value doesn't matter.
        segment_callstack_intact = "".join(segment_callstack)

        # ================== MAIN ERROR ==================
        crashlog_mainerror = crash_data[index_mainerror]
        if "," in crashlog_mainerror:
            crashlog_errorsplit = crashlog_mainerror.split(",", 1)
            autoscan_report.append(f"\nMain Error: {crashlog_errorsplit[0]}\n{crashlog_errorsplit[1]}\n")
        else:
            autoscan_report.append(f"\nMain Error: {crashlog_mainerror}\n")

        # =============== CRASHGEN VERSION ===============
        crashlog_crashgen = crash_data[index_crashgenver].strip()
        autoscan_report.append(f"Detected {crashgen_logname} Version: {crashlog_crashgen} \n")
        if crashgen_latestver == crashlog_crashgen or crashgen_vrlatestver == crashlog_crashgen:
            autoscan_report.append(f"* You have the latest version of {crashgen_logname}! *\n\n")
        else:
            autoscan_report.append(f"{warn_outdated} \n")

        # ======= REQUIRED LISTS, DICTS AND CHECKS =======
        if custom_ignore_plugins:
            ignore_plugins_list = [item.lower() for item in custom_ignore_plugins]
        else:
            ignore_plugins_list = False

        crashlog_GPUAMD = crashlog_GPUNV = False
        crashlog_plugins = {}
        if len(segment_plugins) > 1:
            trigger_plugins_loaded = True

        # ================================================
        # 3) CHECK EACH SEGMENT AND CREATE REQUIRED VALUES
        # ================================================

        # CHECK GPU TYPE FOR CRASH LOG
        for elem in segment_system:
            if "GPU" in elem and "AMD" in elem:
                crashlog_GPUAMD = True
            elif "GPU" in elem and "Nvidia" in elem:
                crashlog_GPUNV = True
        if not crashlog_GPUAMD and not crashlog_GPUNV:
            crashlog_GPUI = True
        else:
            crashlog_GPUI = False

        # IF CRASH LOG DOESN'T LIST PLUGINS, CHECK LOADORDER FILE
        if not trigger_plugins_loaded:
            if os.path.exists("loadorder.txt"):
                autoscan_report.extend(["* ✔️ LOADORDER.TXT FILE FOUND IN THE CLASSIC FOLDER! *\n",
                                        "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
                                        "[ To disable this functionality, simply remove loadrder.txt from your CLASSIC folder. ]\n"])
                with open("loadorder.txt", "r", encoding="utf-8", errors="ignore") as loadorder_file:
                    loadorder_data = loadorder_file.readlines()
                for elem in loadorder_data[1:]:
                    if elem not in crashlog_plugins:
                        crashlog_plugins[elem] = "LO"

        else:  # IF CRASH LOG LISTS PLUGINS, USE THOSE INSTEAD
            for elem in segment_plugins:
                if "[FF]" in elem:
                    trigger_plugin_limit = True
                if " " in elem:
                    elem = elem.replace("[", "").replace(":", "").replace("]", "").replace("     ", " ").strip()
                    elem_parts = elem.split(' ', 1)
                    crashlog_plugins[elem_parts[1]] = elem_parts[0]

        for elem in segment_xsemodules:
            # SOME IMPORTANT DLLs HAVE A VERSION, REMOVE IT
            elem = elem.strip()
            if " v" in elem:
                elem_parts = elem.split(' v', 1)
                elem = elem_parts[0]
            if elem not in crashlog_plugins:
                crashlog_plugins[elem] = "DLL"

        for elem in segment_allmodules:
            # SOME IMPORTANT DLLs ONLY APPEAR UNDER MODULES
            if "vulkan" in elem.lower():
                elem = elem.strip()
                elem_parts = elem.split(' ', 1)
                elem_parts[1] = "DLL"
                if elem not in crashlog_plugins:
                    crashlog_plugins[elem_parts[0]] = elem_parts[1]

        # CHECK IF THERE ARE ANY PLUGINS IN THE IGNORE TOML
        if ignore_plugins_list:
            for item in ignore_plugins_list:
                for plugin in crashlog_plugins:
                    if item.lower() == plugin.lower():
                        del crashlog_plugins[plugin]
                        break

        autoscan_report.extend(["====================================================\n",
                                "CHECKING IF LOG MATCHES ANY KNOWN CRASH SUSPECTS...\n",
                                "====================================================\n"])

        if ".dll" in crashlog_mainerror.lower() and "tbbmalloc" not in crashlog_mainerror.lower():
            autoscan_report.extend(["* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! *",
                                    "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n-----\n"])
        max_warn_length = 30
        trigger_suspect_found = False
        for error in suspects_error_list:
            error_split = error.split(" | ", 1)
            if error_split[1] in crashlog_mainerror:
                error_split[1] = error_split[1].ljust(max_warn_length, ".")
                autoscan_report.append(f"# Checking for {error_split[1]} SUSPECT FOUND! > Severity : {error_split[0]} # \n-----\n")
                trigger_suspect_found = True

        for key in suspects_stack_list:
            key_split = key.split(" | ", 1)
            error_req_found = error_opt_found = stack_found = False
            item_list = suspects_stack_list.get(key)
            for item in item_list:
                if "|" in item:
                    item_split = item.split("|", 1)
                    if item_split[0] == "ME-REQ":
                        if item_split[1] in crashlog_mainerror:
                            error_req_found = True
                    elif item_split[0] == "ME-OPT":
                        if item_split[1] in crashlog_mainerror:
                            error_opt_found = True
                    elif item_split[0].isdecimal():
                        if segment_callstack_intact.count(item_split[1]) >= int(item_split[0]):
                            stack_found = True
                    elif item_split[0] == "NOT":
                        if item_split[1] in segment_callstack_intact:
                            break
                else:
                    if item in segment_callstack_intact:
                        stack_found = True

            # print(f"TEST: {error_req_found} | {error_opt_found} | {stack_found}")
            if (error_req_found and stack_found) or (error_opt_found or stack_found):
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

        if not CMain.classic_settings("FCX Mode"):
            autoscan_report.extend(["* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n",
                                    "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n"])
            
            crashgen_ignore = ["F4EE", "WaitForDebugger", "Achievements", "InputSwitch", "MemoryManager", "MemoryManagerDebug"]
            for line in segment_crashgen:
                if "false" in line.lower() and all(elem.lower() not in line.lower() for elem in crashgen_ignore):
                    line_split = line.split(":", 1)
                    autoscan_report.append(f"* NOTICE : {line_split[0].strip()} is disabled in your {crashgen_logname} settings, is this intentional? * \n-----\n")

                if "achievements:" in line.lower():
                    if "true" in line.lower() and any(("achievements.dll" or "unlimitedsurvivalmode.dll") in elem.lower() for elem in segment_xsemodules):
                        autoscan_report.extend(["# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE #",
                                                f" FIX: Open {crashgen_logname}'s TOML file and change Achievements to FALSE, this prevents conflicts with Buffout 4.\n-----\n"])
                    else:
                        autoscan_report.append(f"✔️ Achievements parameter is correctly configured in your {crashgen_logname} settings! \n-----\n")

                if "memorymanager:" in line.lower():
                    if "true" in line.lower() and any("bakascrapheap.dll" in elem.lower() for elem in segment_xsemodules):
                        autoscan_report.extend(["# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but MemoryManager parameter is set to TRUE #",
                                                f" FIX: Open {crashgen_logname}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with Buffout 4.\n-----\n"])
                    else:
                        autoscan_report.append(f"✔️ Memory Manager parameter is correctly configured in your {crashgen_logname} settings! \n-----\n")

                if "f4ee:" in line.lower():
                    if "false" in line.lower() and any("f4ee.dll" in elem.lower() for elem in segment_xsemodules):
                        autoscan_report.extend(["# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under [Compatibility] is set to FALSE #",
                                                f" FIX: Open {crashgen_logname}'s TOML file and change F4EE to TRUE, this prevents bugs and crashes from Looks Menu.\n-----\n"])
                    else:
                        autoscan_report.append(f"✔️ F4EE (Looks Menu) parameter is correctly configured in your {crashgen_logname} settings! \n-----\n")
        else:
            autoscan_report.extend(["* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n",
                                    "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n"])
            
            autoscan_report.append(main_files_check)

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
                                        "[Due to limitations, CLAS will show warnings for some mods even if fixes or patches are already installed.] \n",
                                        "[To hide these warnings, you can add their plugin names to the CLASSIC Ignore.yaml file. ONE PLUGIN PER LINE.] \n\n"])
            else:
                autoscan_report.append(f"# FOUND NO PROBLEMATIC MODS WITH AVAILABLE SOLUTIONS AND COMMUNITY PATCHES # \n\n")
        else:
            autoscan_report.append(warn_noplugins)

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
            detect_mods_important(game_mods_core)
        else:
            autoscan_report.append(warn_noplugins)

        autoscan_report.extend(["====================================================\n",
                                "SCANNING THE LOG FOR SPECIFIC (POSSIBLE) SUSPECTS...\n",
                                "====================================================\n"])

        if trigger_plugin_limit:
            autoscan_report.extend(["# [!] CAUTION : ONE OF YOUR PLUGINS HAS THE [FF] PLUGIN INDEX VALUE #",
                                    "* THIS MEANS YOU ALMOST CERTAINLY WENT OVER THE GAME PLUGIN LIMIT! *",
                                    "Disable some of your esm/esp plugins and re-run the Crash Log Scan.\n-----\n"])

        # ================================================

        autoscan_report.append("# LIST OF (POSSIBLE) PLUGIN SUSPECTS #\n")
        plugins_matches = []
        for line in segment_callstack:
            for plugin in crashlog_plugins:
                if plugin.lower() in line.lower() and "modified by:" not in line.lower():
                    if all(ignore.lower() not in plugin.lower() for ignore in game_ignore_plugins):
                        plugins_matches.append(plugin)

        if plugins_matches:
            plugins_found = dict(Counter(plugins_matches))
            for key, value in plugins_found.items():
                autoscan_report.append(f"- {key} | {value}\n")

            autoscan_report.extend(["\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n",
                                    "These Plugins were caught by Buffout 4 and some of them might be responsible for this crash.\n",
                                    "You can try disabling these plugins and recheck your game, though this method can be unreliable.\n\n"])
        else:
            autoscan_report.append("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n")

        # ================================================

        autoscan_report.append("# LIST OF (POSSIBLE) FORM ID SUSPECTS #\n")
        formids_matches = [line.replace('0x', '').strip() for line in segment_callstack if "formid:" in line.lower() and "0xFF" not in line]
        if formids_matches:
            formids_found = dict(Counter(formids_matches))
            for form_id, count in formids_found.items():
                formid_split = form_id.split(": ", 1)
                for plugin, plugin_id in crashlog_plugins.items():
                    if str(plugin_id) == str(formid_split[1][:2]):
                        autoscan_report.append(f"- {form_id} | [{plugin}] | {count}\n")

            autoscan_report.extend(["\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
                                    f"These Form IDs were caught by {crashgen_logname} and some of them might be related to this crash.\n",
                                    "You can try searching any listed Form IDs in FO4Edit and see if they lead to relevant records.\n\n"])
        else:
            autoscan_report.append("* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n")

        # ================================================

        autoscan_report.append("# LIST OF DETECTED (NAMED) RECORDS #\n")
        records_matches = []
        for line in segment_callstack:
            if any(item.lower() in line.lower() for item in classic_records_list):
                if all(record.lower() not in line.lower() for record in game_ignore_records):
                    records_matches.append(line.strip())
        if records_matches:
            records_found = dict(Counter(records_matches))
            for record, count in records_found.items():
                autoscan_report.append(f"- {record} | {count}\n")

            autoscan_report.extend(["\n[Last number counts how many times each Named Record shows up in the crash log.]\n",
                                    f"These records were caught by {crashgen_logname} and some of them might be related to this crash.\n",
                                    "Named records should give extra info on involved game objects, record types or mod files.\n\n"])
        else:
            autoscan_report.append("* COULDN'T FIND ANY NAMED RECORDS *\n\n")

        # ============== AUTOSCAN REPORT END ==============
        autoscan_report.extend(["FOR FULL LIST OF MODS THAT CAUSE PROBLEMS, THEIR ALTERNATIVES AND DETAILED SOLUTIONS,\n",
                                "VISIT THE BUFFOUT 4 CRASH ARTICLE: https://www.nexusmods.com/fallout4/articles/3115\n",
                                "===============================================================================\n",
                                f"END OF AUTOSCAN | Author / Made By: Poet#9800 (DISCORD) | {classic_version_date}\n",
                                "CONTRIBUTORS | evildarkarchon | kittivelae | AtomicFallout757\n",
                                "CLASSIC | https://www.nexusmods.com/fallout4/mods/56255"])

        autoscan_name = crashlog_file.name.replace(".log", "")
        with open(f"{autoscan_name}-AUTOSCAN.md", "w", encoding="utf-8", errors="ignore") as autoscan_file:
            logging.info(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
            autoscan_output = "".join(autoscan_report)
            autoscan_file.write(autoscan_output)

    # ================================================
    # CRASH LOG SCAN COMPLETE / TERMINAL OUTPUT
    # ================================================
    logging.info("- - - COMPLETED CRASH LOG FILE SCAN >>> ALL LOGS SCANNED SUCCESSFULLY")
    print("SCAN COMPLETE! (IT MIGHT TAKE SEVERAL SECONDS FOR SCAN RESULTS TO APPEAR)")
    print("SCAN RESULTS ARE AVAILABLE IN FILES NAMED crash-date-and-time-AUTOSCAN.md \n")
    print(f"{random.choice(classic_game_hints)}\n-----")
    print(f"Scanned all available logs in {str(time.perf_counter() - 0.5 - scan_start_time)[:5]} seconds.")
    print(f"Number of Scanned Logs (No Autoscan Errors): {stats_crashlog_scanned}")
    print(f"Number of Incomplete Logs (No Plugins List): {stats_crashlog_incomplete}")
    print(f"Number of Failed Logs (Autoscan Can't Scan): {stats_crashlog_failed}\n-----")
    print("FOR FULL LIST OF MODS THAT CAUSE PROBLEMS, THEIR ALTERNATIVES AND DETAILED SOLUTIONS,")
    print("VISIT THE BUFFOUT 4 CRASH ARTICLE: https://www.nexusmods.com/fallout4/articles/3115 \n")
    print("================================ CONTACT INFO =================================")
    print("DISCORD | Poet#9800 (guidance.of.grace) | https://discord.gg/DfFYJtt8p4")
    print("CLASSIC ON NEXUS | https://www.nexusmods.com/fallout4/mods/56255")
    print("NEXUS PROFILE | https://www.nexusmods.com/users/64682231 \n")
    # Trying to generate Stat Logging for 0 valid logs can crash the script.
    if stats_crashlog_scanned == 0 and stats_crashlog_incomplete == 0:
        print(" ❌ CLAS found no crash logs to scan or the scan failed.")
        print("    There are no statistics to show (at this time).\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="Crash Log Auto Scanner & Setup Integrity Checker (CLASSIC)", description="All terminal options are saved to the YAML file.")
    # Argument values will simply change INI values since that requires the least refactoring
    # I will figure out a better way in a future iteration, this iteration simply mimics the GUI. - evildarkarchon
    parser.add_argument("--fcx-mode", action=argparse.BooleanOptionalAction, help="Enable (or disable) FCX mode")
    parser.add_argument("--imi-mode", action=argparse.BooleanOptionalAction, help="Enable (or disable) IMI mode")
    parser.add_argument("--stat-logging", action=argparse.BooleanOptionalAction, help="Enable (or disable) Stat Logging")
    parser.add_argument("--move-unsolved", action=argparse.BooleanOptionalAction, help="Enable (or disable) moving unsolved logs to a separate directory")
    parser.add_argument("--ini-path", type=Path, help="Set the directory that stores the game's INI files.")
    parser.add_argument("--scan-path", type=Path, help="Set which custom directory to scan crash logs from.")
    args = parser.parse_args()

    scan_path: Path = args.scan_path  # VSCode gives me type errors because args.* is set at runtime (doesn't know what types it's dealing with).
    ini_path: Path = args.ini_path  # Using intermediate variables with type annotations to satisfy it.

    # Default output value for an argparse.BooleanOptionalAction is None, and so fails the isinstance check.
    # So it will respect current INI values if not specified on the command line.
    if isinstance(args.fcx_mode, bool) and not args.fcx_mode == CMain.classic_settings("FCX Mode"):
        CMain.yaml_update("CLASSIC Settings.yaml", "CLASSIC_Settings.FCX Mode", args.fcx_mode)

    if isinstance(args.imi_mode, bool) and not args.imi_mode == CMain.classic_settings("IMI Mode"):
        CMain.yaml_update("CLASSIC Settings.yaml", "CLASSIC_Settings.IMI Mode", args.imi_mode)

    if isinstance(args.move_unsolved, bool) and not args.move_unsolved == CMain.classic_settings("Move Unsolved"):
        CMain.yaml_update("CLASSIC Settings.yaml", "CLASSIC_Settings.Move Unsolved", args.args.move_unsolved)

    if isinstance(ini_path, Path) and ini_path.resolve().is_dir() and not str(ini_path) == CMain.classic_settings("INI Folder Path"):
        CMain.yaml_update("CLASSIC Settings.yaml", "CLASSIC_Settings.INI Folder Path", str(Path(ini_path).resolve()))

    if isinstance(scan_path, Path) and scan_path.resolve().is_dir() and not str(scan_path) == CMain.classic_settings("SCAN Custom Path"):
        CMain.yaml_update("CLASSIC Settings.yaml", "CLASSIC_Settings.SCAN Custom Path", str(Path(scan_path).resolve()))

    crashlogs_scan()
    # execution_time = timeit.timeit(crashlogs_scan, number=1)
    # print(f"Execution time: {execution_time} seconds")
    # os.system("pause")
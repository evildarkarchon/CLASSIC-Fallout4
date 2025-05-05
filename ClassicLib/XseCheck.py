# =========== CHECK GAME XSE SCRIPTS -> GET PATH AND HASHES ===========
import hashlib
from pathlib import Path
from typing import cast

from ClassicLib import Constants
from ClassicLib.Logger import logger
from ClassicLib.Util import open_file_with_encoding
from ClassicLib.YamlSettingsCache import yaml_settings


# noinspection DuplicatedCode
def xse_check_integrity() -> str:  # RESERVED | NEED VR HASH/FILE CHECK
    """
    Checks the integrity of the XSE (Script Extender) installation, files, and logs.

    This function performs an integrity check for the Script Extender (XSE) by verifying the existence of
    required files, ensuring compatibility with the latest version, and analyzing log files for potential
    errors. It also generates informative messages or warnings based on the state of the XSE components
    and captures any issues identified in the log file.

    Raises:
        TypeError: If expected settings or file paths are not of the correct type or are invalid.

    Returns:
        str: A concatenated string of messages and warnings indicating the results of the integrity check.
    """
    failed_list: list[str] = []
    message_list: list[str] = []
    logger.debug("- - - INITIATED XSE INTEGRITY CHECK")

    catch_errors = yaml_settings(list[str], Constants.YAML.Main, "catch_log_errors")
    xse_acronym = yaml_settings(str, Constants.YAML.Game, f"Game{Constants.gamevars["vr"]}_Info.XSE_Acronym")
    xse_log_file = yaml_settings(str, Constants.YAML.Game_Local, f"Game{Constants.gamevars["vr"]}_Info.Docs_File_XSE")
    xse_full_name = yaml_settings(str, Constants.YAML.Game, f"Game{Constants.gamevars["vr"]}_Info.XSE_FullName")
    xse_ver_latest = yaml_settings(str, Constants.YAML.Game, f"Game{Constants.gamevars["vr"]}_Info.XSE_Ver_Latest")
    adlib_file_str = yaml_settings(str, Constants.YAML.Game_Local,
                                   f"Game{Constants.gamevars["vr"]}_Info.Game_File_AddressLib")
    if not isinstance(catch_errors, list):
        raise TypeError
    if not (isinstance(xse_acronym, str) and isinstance(xse_full_name, str) and isinstance(xse_ver_latest, str)):
        raise TypeError
    if not (isinstance(xse_log_file, str) or xse_log_file is None):
        raise TypeError
    if not (isinstance(adlib_file_str, str) or adlib_file_str is None):
        raise TypeError
    adlib_file = Path(adlib_file_str) if adlib_file_str else None

    match adlib_file:
        case str() | Path():
            if Path(adlib_file).exists():
                message_list.append("✔️ REQUIRED: *Address Library* for Script Extender is installed! \n-----\n")
            else:
                warn_adlib = yaml_settings(str, Constants.YAML.Game, "Warnings_MODS.Warn_ADLIB_Missing")
                if not isinstance(warn_adlib, str):
                    raise TypeError
                message_list.append(warn_adlib)
        case _:
            message_list.append(
                f"❌ Value for Address Library is invalid or missing from CLASSIC {Constants.gamevars["game"]} Local.yaml!\n-----\n")

    match xse_log_file:
        case str() | Path():
            if Path(cast("str", xse_log_file)).exists():
                message_list.append(f"✔️ REQUIRED: *{xse_full_name}* is installed! \n-----\n")
                with open_file_with_encoding(cast("str", xse_log_file)) as xse_log:
                    xse_data = xse_log.readlines()
                if str(xse_ver_latest) in xse_data[0]:
                    message_list.append(f"✔️ You have the latest version of *{xse_full_name}*! \n-----\n")
                else:
                    warn_outdated = yaml_settings(str, Constants.YAML.Game, "Warnings_XSE.Warn_Outdated")
                    if not isinstance(warn_outdated, str):
                        raise TypeError
                    message_list.append(warn_outdated)
                failed_list.extend([
                    line for line in xse_data if any(item.lower() in line.lower() for item in catch_errors)
                ])

                if failed_list:
                    message_list.append(f"#❌ CAUTION : {xse_acronym}.log REPORTS THE FOLLOWING ERRORS #\n")
                    message_list.extend([f"ERROR > {elem.strip()} \n-----\n" for elem in failed_list])
            else:
                message_list.extend(
                    [f"❌ CAUTION : *{xse_acronym.lower()}.log* FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
                     f"   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n",
                     "    After that, try running CLASSIC again! \n-----\n"])
        case _:
            message_list.append(
                f"❌ Value for {xse_acronym.lower()}.log is invalid or missing from CLASSIC {Constants.gamevars["game"]} Local.yaml!\n-----\n")

    return "".join(message_list)


def xse_check_hashes() -> str:
    """
    Performs integrity checks for Script Extender (XSE) files by validating their hashes against the expected ones
    stored in the game YAML configuration. Reports missing or mismatched files and generates appropriate warning
    messages based on the configuration. Ensures that the scripts are intact and not overridden by external modifications.

    Raises:
        TypeError: If configuration data types retrieved from YAML settings do not match the expected types.

    Returns:
        str: Consolidated message summarizing the results of the integrity check, including warnings about missing or
        mismatched files, or confirmation that all scripts are correctly validated.
    """
    message_list: list[str] = []
    logger.debug("- - - INITIATED XSE FILE HASH CHECK")

    xse_script_missing = xse_script_mismatch = False
    xse_hashedscripts = yaml_settings(dict[str, str], Constants.YAML.Game,
                                      f"Game{Constants.gamevars["vr"]}_Info.XSE_HashedScripts")
    game_folder_scripts = yaml_settings(str, Constants.YAML.Game_Local,
                                        f"Game{Constants.gamevars["vr"]}_Info.Game_Folder_Scripts")
    if not isinstance(xse_hashedscripts, dict):
        raise TypeError
    if not (isinstance(game_folder_scripts, str) or game_folder_scripts is None):
        raise TypeError

    xse_hashedscripts_local = dict.fromkeys(xse_hashedscripts)
    for key in xse_hashedscripts_local:
        script_path = Path(rf"{game_folder_scripts}\{key!s}")
        if script_path.is_file():
            with script_path.open("rb") as f:
                file_contents = f.read()
                # Algo should match the one used for Database YAML!
                file_hash = hashlib.sha256(file_contents).hexdigest()
                xse_hashedscripts_local[key] = str(file_hash)

    for key in xse_hashedscripts:
        if key in xse_hashedscripts_local:
            hash1 = xse_hashedscripts[key]
            hash2 = xse_hashedscripts_local[key]
            if hash1 == hash2:
                pass
            elif hash2 is None:  # Can only be None if not hashed in the first place, meaning it is missing.
                message_list.append(
                    f"❌ CAUTION : {key} Script Extender file is missing from your game Scripts folder! \n-----\n")
                xse_script_missing = True
            else:
                message_list.append(
                    f"[!] CAUTION : {key} Script Extender file is outdated or overriden by another mod! \n-----\n")
                xse_script_mismatch = True

    if xse_script_missing:
        warn_missing = yaml_settings(str, Constants.YAML.Game, "Warnings_XSE.Warn_Missing")
        if not isinstance(warn_missing, str):
            raise TypeError
        message_list.append(warn_missing)
    if xse_script_mismatch:
        warn_mismatch = yaml_settings(str, Constants.YAML.Game, "Warnings_XSE.Warn_Mismatch")
        if not isinstance(warn_mismatch, str):
            raise TypeError
        message_list.append(warn_mismatch)
    if not xse_script_missing and not xse_script_mismatch:
        message_list.append("✔️ All Script Extender files have been found and accounted for! \n-----\n")

    return "".join(message_list)

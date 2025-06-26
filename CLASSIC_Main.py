import contextlib
import shutil
import sys
from pathlib import Path
from typing import Any

from ClassicLib import GlobalRegistry, MessageTarget, init_message_handler, msg_info, msg_success, msg_warning
from ClassicLib.Constants import YAML
from ClassicLib.DocsPath import docs_check_ini, docs_generate_paths, docs_path_find
from ClassicLib.GamePath import game_generate_paths, game_path_find
from ClassicLib.Logger import logger
from ClassicLib.Util import calculate_file_hash, configure_logging, normalize_list, open_file_with_encoding
from ClassicLib.XseCheck import xse_check_hashes, xse_check_integrity
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

with contextlib.suppress(ImportError):
    pass  # type: ignore[import]

""" AUTHOR NOTES (POET): ❓ ❌ ✔️
    ❓ REMINDER: 'shadows x from outer scope' means the variable name repeats both in the func and outside all other func.
    ❓ Comments marked as RESERVED in all scripts are intended for future updates or tests, do not edit / move / remove.
    ❓ (..., encoding="utf-8", errors="ignore") needs to go with every opened file because of unicode & charmap errors.
    ❓ import shelve if you want to store persistent data that you do not want regular users to access or modify.
    ❓ Globals are generally used to standardize game paths and INI files naming conventions.
"""


def classic_generate_files() -> None:
    """Generate necessary CLASSIC YAML files.

    This function generates the following files if they do not already exist:
    - `CLASSIC Ignore.yaml`: Uses a default ignore file string specified in
      the YAML settings. Ensures the file content is written in UTF-8 encoding.
    - `CLASSIC Data/CLASSIC <GAME> Local.yaml`: Uses a default local YAML
      string specified in the YAML settings, where `<GAME>` is dynamically
      determined from `gamevars["game"]`. Ensures the file content is written
      in UTF-8 encoding.

    Raises:
        TypeError: If the default content retrieved for either the ignore file
            or the local YAML file is not of type `str`.
    """
    """Generate `CLASSIC Ignore.yaml` and `CLASSIC Data/CLASSIC <GAME> Local.yaml`."""
    ignore_path = Path("CLASSIC Ignore.yaml")
    if not ignore_path.exists():
        default_ignorefile = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_ignorefile")
        if not isinstance(default_ignorefile, str):
            raise TypeError
        ignore_path.write_text(default_ignorefile, encoding="utf-8")

    local_path = Path(f"CLASSIC Data/CLASSIC {GlobalRegistry.get_game()} Local.yaml")
    if not local_path.exists():
        default_yaml = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_localyaml")
        if not isinstance(default_yaml, str):
            raise TypeError
        local_path.write_text(default_yaml, encoding="utf-8")


# =========== CHECK GAME EXE FILE -> GET PATH AND HASHES ===========
# noinspection DuplicatedCode
def game_check_integrity() -> str:
    """
    Checks the integrity of the game files, including executable file version and Steam
    INI file existence, and generates a summary message on the validity and installation
    status of the game. It ensures that the local game files match the hashes stored in
    the database and assesses proper installation directories.

    Returns:
        str: A detailed message indicating the integrity status of game files.

    Raises:
        TypeError: If any of the settings loaded from the configuration files is not of the
            expected type.
    """
    logger.debug("- - - INITIATED GAME INTEGRITY CHECK")

    # Load configuration settings
    config: dict = _load_game_config()

    # Validate paths
    exe_path: Path | None = Path(config["game_exe_path"]) if config["game_exe_path"] else None
    steam_ini_path = Path(config["steam_ini_path"]) if config["steam_ini_path"] else None

    messages: list[str] = []

    # Check game executable if it exists
    if exe_path and exe_path.is_file():
        # Calculate local executable hash
        local_hash: str = calculate_file_hash(exe_path)

        # Check if hash matches known versions
        is_valid_version: bool = local_hash in (config["exe_hash_old"], config["exe_hash_new"])
        steam_ini_exists: Path | bool | None = steam_ini_path and steam_ini_path.exists()

        # Add version status message
        if is_valid_version and not steam_ini_exists:
            messages.append(f"✔️ You have the latest version of {config['root_name']}! \n-----\n")
        else:
            icon = "\U0001f480" if steam_ini_exists else "❌"
            messages.append(f"{icon} CAUTION : YOUR {config['root_name']} GAME / EXE VERSION IS OUT OF DATE \n-----\n")

        # Add installation location message
        if "Program Files" not in str(exe_path):
            messages.append(f"✔️ Your {config['root_name']} game files are installed outside of the Program Files folder! \n-----\n")
        else:
            messages.append(config["root_warn"])

    return "".join(messages)


def _load_game_config() -> dict:
    """Load and validate all needed game configuration settings."""
    vr_suffix: str = GlobalRegistry.get_vr()

    # Load settings from YAML
    config: dict[str, str | None] = {
        "steam_ini_path": yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_SteamINI"),
        "exe_hash_old": yaml_settings(str, YAML.Game, "Game_Info.EXE_HashedOLD"),
        "exe_hash_new": yaml_settings(str, YAML.Game, "Game_Info.EXE_HashedNEW"),
        "game_exe_path": yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_EXE"),
        "root_name": yaml_settings(str, YAML.Game, f"Game{vr_suffix}_Info.Main_Root_Name"),
        "root_warn": yaml_settings(str, YAML.Main, "Warnings_GAME.warn_root_path"),
    }

    # Validate settings types
    for key, value in config.items():
        if value is not None and not isinstance(value, str):
            raise TypeError(f"Expected string for {key}, got {type(value)}")

    return config


# ================================================
# CHECK DOCUMENTS GAME INI FILES & INI SETTINGS
# ================================================
def docs_check_folder() -> str:
    """
    Checks the folder configuration for game documentation and returns any warnings if applicable.

    This function verifies the documentation path and checks for specific keywords like "onedrive"
    in the documentation path name. If the specific condition is met, it appends a warning
    message to a list and returns the concatenated string of warnings.

    Returns:
        str: A concatenated string of all warnings, if applicable; otherwise, an empty string.

    Raises:
        TypeError: If the `docs_name` or `docs_warn` obtained from YAML settings is not of type str.
    """
    message_list: list[str] = []
    docs_name: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Docs_Name")
    if not isinstance(docs_name, str):
        raise TypeError
    if "onedrive" in docs_name.lower():
        docs_warn: str | None = yaml_settings(str, YAML.Main, "Warnings_GAME.warn_docs_path")
        if not isinstance(docs_warn, str):
            raise TypeError
        message_list.append(docs_warn)
    return "".join(message_list)


# =========== GENERATE FILE BACKUPS ===========
# noinspection DuplicatedCode
def main_files_backup() -> None:
    """
    Backs up game files specified in the YAML configuration to a versioned directory.

    The function reads a list of files to back up from the YAML configuration, the game
    path, and the current game-specific log file. It determines the current game
    version, creates a backup directory for that version if it does not exist, and
    copies files from the game directory to the backup directory, provided the files
    are listed in the backup configuration and do not already exist in the backup.

    Raises:
        TypeError: If the YAML settings do not provide the required data types.
        FileNotFoundError: If the game log file specified in the YAML settings is not found
          during attempt to read it.
    """
    # Load configuration settings
    config: dict = _load_backup_configuration()

    # Get XSE version from log file
    xse_version: str | None = _extract_xse_version(config["xse_log_file"], config["xse_ver_latest"])
    if not xse_version:
        return  # No version found, nothing to back up

    # Create backup directory and perform backup
    _perform_backup(xse_version, config["game_path"], config["backup_list"])


def _load_backup_configuration() -> dict:
    """
    Load and validate the backup configuration settings from YAML.

    Returns:
        A dictionary containing validated configuration settings.

    Raises:
        TypeError: If any of the settings have invalid types.
    """
    game_vr: str = GlobalRegistry.get_vr()
    backup_list: list[str] | None = yaml_settings(list[str], YAML.Main, "CLASSIC_AutoBackup")
    game_path: str | None = yaml_settings(str, YAML.Game_Local, f"Game{game_vr}_Info.Root_Folder_Game")
    xse_log_file: str | None = yaml_settings(str, YAML.Game_Local, f"Game{game_vr}_Info.Docs_File_XSE")
    xse_ver_latest: str | None = yaml_settings(str, YAML.Game, f"Game{game_vr}_Info.XSE_Ver_Latest")

    # Validate types
    if not isinstance(backup_list, list):
        raise TypeError("Backup list must be a list of strings")
    if not isinstance(xse_log_file, str):
        raise TypeError("XSE log file path must be a string")
    if not isinstance(xse_ver_latest, str):
        raise TypeError("Latest XSE version must be a string")

    return {"backup_list": backup_list, "game_path": game_path, "xse_log_file": xse_log_file, "xse_ver_latest": xse_ver_latest}


def _extract_xse_version(xse_log_file: str, default_version: str) -> str | None:
    """
    Extract the XSE version from the log file.

    Args:
        xse_log_file: Path to the XSE log file
        default_version: Default version to use if version cannot be extracted

    Returns:
        The extracted XSE version or None if no log data is available
    """
    xse_data_lower: list[str] = []
    try:
        with open_file_with_encoding(xse_log_file) as xse_log:
            xse_data: list[str] = xse_log.readlines()
            xse_data_lower = normalize_list(xse_data)
    except FileNotFoundError:
        pass

    if not xse_data_lower:
        return None

    version: str = default_version
    try:
        line_with_version: str = next(line for line in xse_data_lower if "version = " in line)
        split_line: list[str] = line_with_version.split(" ")

        for index, item in enumerate(split_line):
            if "version" in item:
                version = split_line[index + 2]
                break
    except (StopIteration, IndexError):
        # If we can't extract version from log, use the default
        pass

    return version


def _perform_backup(version: str, game_path: str | None, backup_list: list[str]) -> None:
    """
    Create backup directory and copy files from game directory to backup.

    Args:
        version: XSE version to use for backup directory
        game_path: Path to the game directory
        backup_list: List of file patterns to back up
    """
    backup_path: Path = Path(f"CLASSIC Backup/Game Files/{version}")
    backup_path.mkdir(parents=True, exist_ok=True)

    if not game_path:
        return

    # Validate game path before attempting backup
    from ClassicLib.Util import validate_path

    is_valid, error_msg = validate_path(game_path, check_write=False, check_read=True)
    if not is_valid:
        logger.warning(f"Cannot backup files - {error_msg}")
        return

    # Back up the file if backup of file does not already exist
    game_files: list[Path] = list(Path(game_path).glob("*.*"))
    backup_files: list[str] = [file.name for file in backup_path.glob("*.*")]

    for file in game_files:
        if file.name not in backup_files and any(file.name in item for item in backup_list):
            destination_file: Path = backup_path / file.name
            shutil.copy2(file, destination_file)


# =========== GENERATE MAIN RESULTS ===========
def main_combined_result() -> str:
    """
    Combines and executes multiple integrity and configuration checks.

    This function executes a series of integrity checks that include game
    integrity validation, hash verification, and validation of specific
    configuration files. The results from all the checks are aggregated
    and returned as a single concatenated string representing the combined
    outcome of all checks.

    Returns:
        str: A concatenated string containing the results of all executed
        checks.
    """
    game_name: str = GlobalRegistry.get_game()
    combined_return: list[str] = [
        game_check_integrity(),
        xse_check_integrity(),
        xse_check_hashes(),
        docs_check_folder(),
        docs_check_ini(f"{game_name}.ini"),
        docs_check_ini(f"{game_name}Custom.ini"),
        docs_check_ini(f"{game_name}Prefs.ini"),
    ]
    return "".join(combined_return)


def main_generate_required() -> None:
    """
    Executes the main logic for generating required settings and verifying the game setup integrity.

    This function configures logging, generates files, and validates game and classic version
    info. It provides an initial check and feedback for compatibility of crash logs and game
    settings. Depending on whether the game path is found within the settings, the function
    either runs path generation procedures or backs up main files. Displays relevant messages
    to the user regarding progress and outcomes.

    Raises:
        TypeError: If the classic version or game name settings are not of type `str`.

    """
    configure_logging(logger)
    classic_generate_files()
    classic_ver: str | None = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
    game_name: str | None = yaml_settings(str, YAML.Game, "Game_Info.Main_Root_Name")
    if not (isinstance(classic_ver, str) and isinstance(game_name, str)):
        raise TypeError
    msg_info(
        f"Hello World! | Crash Log Auto Scanner & Setup Integrity Checker | {classic_ver} | {game_name}", target=MessageTarget.CLI_ONLY
    )
    msg_info("REMINDER: COMPATIBLE CRASH LOGS MUST START WITH 'crash-' AND MUST HAVE .log EXTENSION", target=MessageTarget.CLI_ONLY)
    msg_info("❓ PLEASE WAIT WHILE CLASSIC CHECKS YOUR SETTINGS AND GAME SETUP...", target=MessageTarget.CLI_ONLY)
    logger.debug(f"> > > STARTED {classic_ver}")

    game_path: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")

    if not game_path:
        docs_path_find(GlobalRegistry.is_gui_mode())
        docs_generate_paths()
        game_path_find()
        game_generate_paths()
    else:
        main_files_backup()

    msg_success("ALL CLASSIC AND GAME SETTINGS CHECKS HAVE BEEN PERFORMED!", target=MessageTarget.CLI_ONLY)
    msg_info("YOU CAN NOW SCAN YOUR CRASH LOGS, GAME AND/OR MOD FILES", target=MessageTarget.CLI_ONLY)


def is_gui_mode() -> bool:
    """Check if application is running in GUI mode."""
    return GlobalRegistry.is_gui_mode()


def validate_settings_paths() -> None:
    """
    Validates and cleans up invalid paths in settings.

    This function checks for paths stored in settings and removes any that:
    - Don't exist on the filesystem
    - Are empty strings
    - Are None values
    - Are restricted (hard-coded) directories

    Currently validates:
    - SCAN Custom Path: Used for custom crash log scanning directories
    """
    from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

    # Validate custom scan path
    custom_scan_path: str | None = classic_settings(str, "SCAN Custom Path")
    if custom_scan_path:
        # Check if the path exists
        path_obj = Path(custom_scan_path)
        if not path_obj.exists() or not path_obj.is_dir():
            logger.debug(f"Invalid custom scan path found in settings: {custom_scan_path}")
            # Clear the invalid path from settings
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            msg_warning(f"Removed invalid custom scan path: {custom_scan_path}")
        elif not is_valid_custom_scan_path(custom_scan_path):
            logger.debug(f"Restricted custom scan path found in settings: {custom_scan_path}")
            # Clear the restricted path from settings
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            msg_warning(f"Removed restricted custom scan path: {custom_scan_path}")


def initialize(is_gui: bool = False) -> None:
    """
    Initializes the application state, sets up the YAML settings cache, and optionally enables GUI mode.

    This function initializes the necessary elements required for the application's operation, such
    as loading static YAML files into a settings cache. It also determines whether the application
    should operate in GUI mode and sets up related resources accordingly.

    Args:
        is_gui (bool): Indicates whether the application should operate in GUI mode. If True,
            GUI-related resources are initialized.
    """
    # Initialize message handler first
    init_message_handler(parent=None, is_gui_mode=is_gui)

    yaml_cache: Any = GlobalRegistry.get_yaml_cache()
    GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, is_gui_mode)
    # Preload static YAML files
    for store in yaml_cache.STATIC_YAML_STORES:
        path = yaml_cache.get_path_for_store(store)
        yaml_cache.load_yaml(path)

    # noinspection PyTypedDict
    GlobalRegistry.register(GlobalRegistry.Keys.VR, "" if not classic_settings(bool, "VR Mode") else "VR")
    managed_game_setting: str | None = classic_settings(str, "Managed Game")
    game_value: str = managed_game_setting.replace(" ", "") if isinstance(managed_game_setting, str) else ""
    GlobalRegistry.register(GlobalRegistry.Keys.GAME, game_value)
    GlobalRegistry.register(GlobalRegistry.Keys.IS_PRERELEASE, yaml_settings(bool, YAML.Main, "CLASSIC_Info.is_prerelease"))

    if getattr(sys, "frozen", False):
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(sys.executable).parent)
    else:
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(__file__).parent)

    # Validate settings after initialization
    validate_settings_paths()


if __name__ == "__main__":  # AKA only autorun / do the following when NOT imported.
    raise RuntimeError("""This module is not meant to be run directly. 
Please use it as part of the CLASSIC application.""")

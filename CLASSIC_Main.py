import contextlib
import hashlib
import shutil
import sys
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML, gamevars
from ClassicLib.DocsPath import docs_check_ini, docs_generate_paths, docs_path_find
from ClassicLib.GamePath import game_generate_paths, game_path_find
from ClassicLib.GuiComponents import GamePathEntry, ManualDocsPath
from ClassicLib.Logger import logger
from ClassicLib.Util import configure_logging, open_file_with_encoding
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

    local_path = Path(f"CLASSIC Data/CLASSIC {gamevars["game"]} Local.yaml")
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
    message_list = []
    logger.debug("- - - INITIATED GAME INTEGRITY CHECK")

    steam_ini_local = yaml_settings(str, YAML.Game_Local,
                                    f"Game{gamevars["vr"]}_Info.Game_File_SteamINI")
    exe_hash_old = yaml_settings(str, YAML.Game,
                                 "Game_Info.EXE_HashedOLD")  # The VR check is not needed here.
    exe_hash_new = yaml_settings(str, YAML.Game,
                                 "Game_Info.EXE_HashedNEW")  # ...or here. VR hashes are not available at this time.
    game_exe_local = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_EXE")
    root_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Root_Name")
    if not (isinstance(exe_hash_old, str) and isinstance(root_name, str)):
        raise TypeError
    if not (isinstance(steam_ini_local, str) or steam_ini_local is None):
        raise TypeError
    if not (isinstance(game_exe_local, str) or game_exe_local is None):
        raise TypeError

    game_exe_path = Path(game_exe_local) if game_exe_local else None
    steam_ini_path = Path(steam_ini_local) if steam_ini_local else None
    if game_exe_path and game_exe_path.is_file():
        with game_exe_path.open("rb") as f:
            file_contents = f.read()
            # Algo should match the one used for Database YAML!
            exe_hash_local = hashlib.sha256(file_contents).hexdigest()
        # print(f"LOCAL: {exe_hash_local}\nDATABASE: {exe_hash_old}")
        if (exe_hash_local in (exe_hash_old, exe_hash_new)) and not (steam_ini_path and steam_ini_path.exists()):
            message_list.append(f"✔️ You have the latest version of {root_name}! \n-----\n")
        elif steam_ini_path and steam_ini_path.exists():
            message_list.append(f"\U0001F480 CAUTION : YOUR {root_name} GAME / EXE VERSION IS OUT OF DATE \n-----\n")
        else:
            message_list.append(f"❌ CAUTION : YOUR {root_name} GAME / EXE VERSION IS OUT OF DATE \n-----\n")

        if "Program Files" not in str(game_exe_path):
            message_list.append(
                f"✔️ Your {root_name} game files are installed outside of the Program Files folder! \n-----\n")
        else:
            root_warn = yaml_settings(str, YAML.Main, "Warnings_GAME.warn_root_path")
            if not isinstance(root_warn, str):
                raise TypeError
            message_list.append(root_warn)

    return "".join(message_list)


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
    message_list = []
    docs_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Docs_Name")
    if not isinstance(docs_name, str):
        raise TypeError
    if "onedrive" in docs_name.lower():
        docs_warn = yaml_settings(str, YAML.Main, "Warnings_GAME.warn_docs_path")
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
    # Got an expired certificate warning after a few tries, maybe there's a better way?
    backup_list = yaml_settings(list[str], YAML.Main, "CLASSIC_AutoBackup")
    game_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game")
    xse_log_file = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_XSE")
    xse_ver_latest = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Ver_Latest")

    if not (isinstance(backup_list, list) and isinstance(xse_ver_latest, str)):
        raise TypeError
    if not (isinstance(game_path, str) or game_path is None):
        raise TypeError
    if not isinstance(xse_log_file, str):
        raise TypeError

    try:
        with open_file_with_encoding(xse_log_file) as xse_log:
            xse_data = xse_log.readlines()
            xse_data_lower = [line.lower() for line in xse_data]
    except FileNotFoundError:
        xse_data_lower = []

    # Grab current xse version to create a folder with that name.
    if len(xse_data_lower) > 0:
        line_xse = next(line for _, line in enumerate(xse_data_lower) if "version = " in line)
        split_xse = line_xse.split(" ")
        version_xse = xse_ver_latest

        for index, item in enumerate(split_xse):
            if "version" in item:
                index_xse = int(index + 2)
                version_xse = split_xse[index_xse]
                break

        # If there is no folder for current xse version, create it.
        backup_path = Path(f"CLASSIC Backup/Game Files/{version_xse}") if version_xse else None
        if backup_path:
            backup_path.mkdir(parents=True, exist_ok=True)

            # Back up the file if backup of file does not already exist.
            game_files = list(Path(game_path).glob("*.*")) if game_path else []
            backup_files = [file.name for file in backup_path.glob("*.*")]

            for file in game_files:
                if file.name not in backup_files and any(file.name in item for item in backup_list):
                    destination_file = backup_path / file.name
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
    combined_return = [game_check_integrity(), xse_check_integrity(), xse_check_hashes(), docs_check_folder(),
                       docs_check_ini(f"{gamevars["game"]}.ini"),
                       docs_check_ini(f"{gamevars["game"]}Custom.ini"),
                       docs_check_ini(f"{gamevars["game"]}Prefs.ini")]
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
    classic_ver = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
    game_name = yaml_settings(str, YAML.Game, "Game_Info.Main_Root_Name")
    if not (isinstance(classic_ver, str) and isinstance(game_name, str)):
        raise TypeError
    print(f"Hello World! | Crash Log Auto Scanner & Setup Integrity Checker | {classic_ver} | {game_name}")
    print("REMINDER: COMPATIBLE CRASH LOGS MUST START WITH 'crash-' AND MUST HAVE .log EXTENSION \n")
    print("❓ PLEASE WAIT WHILE CLASSIC CHECKS YOUR SETTINGS AND GAME SETUP...")
    logger.debug(f"> > > STARTED {classic_ver}")

    game_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game")

    if not game_path:
        docs_path_find(is_gui_mode())
        docs_generate_paths()
        game_path_find()
        game_generate_paths()
    else:
        main_files_backup()

    print("✔️ ALL CLASSIC AND GAME SETTINGS CHECKS HAVE BEEN PERFORMED!")
    print("    YOU CAN NOW SCAN YOUR CRASH LOGS, GAME AND/OR MOD FILES \n")


def get_manual_docs_gui() -> ManualDocsPath:
    """Get the manual docs GUI component from the registry."""
    return GlobalRegistry.get_manual_docs_gui()


def get_game_path_gui() -> GamePathEntry:
    """Get the game path GUI component from the registry."""
    return GlobalRegistry.get_game_path_gui()


def is_gui_mode() -> bool:
    """Check if application is running in GUI mode."""
    return GlobalRegistry.is_gui_mode()


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
    yaml_cache = GlobalRegistry.get_yaml_cache()
    GlobalRegistry.register(GlobalRegistry.Keys.GUI_MODE, is_gui)
    # Preload static YAML files
    for store in yaml_cache.STATIC_YAML_STORES:
        path = yaml_cache.get_path_for_store(store)
        yaml_cache.load_yaml(path)

    # noinspection PyTypedDict
    gamevars["vr"] = "" if not classic_settings(bool, "VR Mode") else "VR"
    managed_game = classic_settings(str, "Managed Game") or ""
    gamevars["game"] = managed_game.replace(" ", "")
    GlobalRegistry.register(GlobalRegistry.Keys.VR, gamevars["vr"])
    GlobalRegistry.register(GlobalRegistry.Keys.GAME, gamevars["game"])

    if is_gui:
        GlobalRegistry.register(GlobalRegistry.Keys.MANUAL_DOCS_GUI, ManualDocsPath())
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH_GUI, GamePathEntry())

    if getattr(sys, "frozen", False):
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(sys.executable).parent)
    else:
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(__file__).parent)


if __name__ == "__main__":  # AKA only autorun / do the following when NOT imported.
    raise RuntimeError("""This module is not meant to be run directly. 
Please use it as part of the CLASSIC application.""")

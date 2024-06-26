import os
import re
import shutil
import logging
import hashlib
import zipfile
import datetime
import requests
import platform
import ruamel.yaml
import configparser
import sqlite3
import chardet
from pathlib import Path
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

""" AUTHOR NOTES (POET): ❓ ❌ ✔️
    ❓ REMINDER: 'shadows x from outer scope' means the variable name repeats both in the func and outside all other func.
    ❓ Comments marked as RESERVED in all scripts are intended for future updates or tests, do not edit / move / remove.
    ❓ (..., encoding="utf-8", errors="ignore") needs to go with every opened file because of unicode & charmap errors.
    ❓ import shelve if you want to store persistent data that you do not want regular users to access or modify.
    ❓ Globals are generally used to standardize game paths and INI files naming conventions.
    -----
    CO-AUTHOR NOTES (EvilDarkArchon):
    ❓ We're going to have to special-case (or disable) Starfield Script Extender update checks because it's on Nexus, not silverlock.org.
"""
# GLOBALS ========================================
vr = ""  # Used for checking VR Mode yaml setting.
# ================================================
game = "Fallout4"  # Set game managed by CLASSIC.
# ================================================

def open_file_with_encoding(file_path):  # Read only file open with encoding detection. Only for text files.
    with open(file_path, "rb") as f:
        raw_data = f.read()
        encoding = chardet.detect(raw_data)["encoding"]
        return open(file_path, "r", encoding=encoding, errors="ignore")

def vrmode_check():
    global vr
    if classic_settings("VR Mode"):
        vr = "VR"


# Logging levels: debug | info | warning | error | critical
# Level in basicConfig is minimum and must be UPPERCASE
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        filename="CLASSIC Journal.log",
        filemode="a",
        format="%(asctime)s | %(levelname)s | %(message)s")


# ================================================
# DEFINE FILE / YAML FUNCTIONS
# ================================================
def remove_readonly(file_path):
    try:
        # Get current file permissions.
        if platform.system() == "Windows":
            permissions = os.stat(file_path).st_mode
        else:
            permissions = os.stat(file_path).st_mode & 0o777
        # Remove file permissions if needed.
        if permissions & (os.O_RDONLY | os.O_WRONLY):
            if platform.system() == "Windows":
                os.chmod(file_path, permissions & ~0o400)
            else:
                os.chmod(file_path, permissions | 0o200)

            logging.debug(f"- - - '{file_path}' is no longer Read-Only.")
        else:
            logging.debug(f"- - - '{file_path}' is not set to Read-Only.")

    except FileNotFoundError:
        logging.error(f"> > > ERROR (remove_readonly) : '{file_path}' not found.")
    except (ValueError, OSError) as err:
        logging.error(f"> > > ERROR (remove_readonly) : {err}")

yaml_cache = {} # Cache for YAML files to prevent multiple reads.

def yaml_settings(yaml_path, key_path, new_value=None):
    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    yaml.width = 300
    
    if yaml_path not in yaml_cache:
        with open(yaml_path, 'r', encoding='utf-8') as yaml_file:
            yaml_cache[yaml_path] = yaml.load(yaml_file)

    data = yaml_cache[yaml_path]

    keys = key_path.split('.') if isinstance(key_path, str) else key_path
    value = data
    # If new_value is provided, update the value.
    if new_value is not None:
        for key in keys[:-1]:
            value = value[key]

        value[keys[-1]] = new_value
        with open(yaml_path, 'w', encoding='utf-8') as yaml_file:
            yaml.dump(data, yaml_file)
    # Otherwise, traverse YAML structure to get value.
    else:
        for key in keys:
            if key in value:
                value = value[key]
            else:
                return None  # Key not found.
        if value is None and "Path" not in key_path:  # Error me if I mistype or screw up the value grab.
            print(f"❌ ERROR (yaml_settings) : Trying to grab a None value for : '{key_path}'")

    yaml_cache[yaml_path] = data  # Update the cache with the modified data
    return value


# ================================================
# CREATE REQUIRED FILES, SETTINGS & UPDATE CHECK
# ================================================
def classic_generate_files():  # Other paths will be auto generated by the code.
    if not os.path.exists("CLASSIC Ignore.yaml"):
        default_ignorefile = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Info.default_ignorefile")
        with open('CLASSIC Ignore.yaml', 'w', encoding='utf-8') as file:
            file.write(default_ignorefile)

    if not os.path.exists(f"CLASSIC Data/CLASSIC {game} Local.yaml"):
        default_yaml = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Info.default_localyaml")
        with open(f"CLASSIC Data/CLASSIC {game} Local.yaml", "w", encoding="utf-8", errors="ignore") as file:
            file.write(default_yaml)

    if not os.path.exists(f"CLASSIC Data/databases/{game} FID Mods.txt"):
        default_fidfile = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Default_FIDMods")
        with open(f"CLASSIC Data/databases/{game} FID Mods.txt", "w", encoding="utf-8") as file:
            file.write(default_fidfile)


def classic_logging():
    logging.debug("- - - INITIATED LOGGING CHECK")
    if os.path.exists("CLASSIC Journal.log"):
        log_time = datetime.datetime.fromtimestamp(os.path.getmtime("CLASSIC Journal.log"))
        current_time = datetime.datetime.now()
        log_age = current_time - log_time
        if log_age.days > 7:
            try:
                classic_update_check()
                os.remove("CLASSIC Journal.log")  # We do this to trigger an auto update check every X days.
                print("CLASSIC Journal.log has been deleted and regenerated due to being older than 7 days.")
                logging.basicConfig(level=logging.INFO, filename="CLASSIC Journal.log", filemode="a", format="%(asctime)s | %(levelname)s | %(message)s")
            except (ValueError, OSError) as err:
                print(f"An error occurred while deleting CLASSIC Journal.log: {err}")
                classic_update_check()

def create_formid_db():
    with sqlite3.connect(f"CLASSIC Data/databases/{game} FormIDs.db") as conn, open(f"CLASSIC Data/databases/{game} FID Main.txt", encoding="utf-8", errors="ignore") as f:
        conn.execute(f'''CREATE TABLE IF NOT EXISTS {game} 
            (id INTEGER PRIMARY KEY AUTOINCREMENT,  
            plugin TEXT, formid TEXT, entry TEXT)''')
        conn.execute(f"CREATE INDEX IF NOT EXISTS Fallout4_index ON {game}(formid, plugin COLLATE nocase);")
        if conn.in_transaction:
            conn.commit()
        lines = f.readlines()
        if len(lines) > 0:
            print("⏳ Generating FormID cache...", end="")
            for line in lines:
                line = line.strip()
                if "|" in line and len(line.split(" | ")) >= 3:
                    plugin, formid, entry, *extra = line.split(" | ")  # the *extra is for any extraneous data that might be in the line (Python thinks there are more than 3 items in the list for some reason)
                    conn.execute(f'''INSERT INTO {game} (plugin, formid, entry) VALUES (?, ?, ?)''', (plugin, formid, entry))
            if conn.in_transaction:
                conn.commit()
            print(" Done!")

def classic_data_extract():
    def open_zip():
        if os.path.exists("CLASSIC Data/CLASSIC Data.zip"):
            return zipfile.ZipFile("CLASSIC Data/CLASSIC Data.zip", "r")
        elif os.path.exists("CLASSIC Data.zip"):
            return zipfile.ZipFile("CLASSIC Data.zip", "r")
        else:
            raise FileNotFoundError
    try:
        if not os.path.exists("CLASSIC Data/databases/CLASSIC Main.yaml"):
            with open_zip() as zip_data:
                zip_data.extractall("CLASSIC Data")
    except FileNotFoundError:
        print("❌ ERROR : UNABLE TO FIND CLASSIC Data.zip! This archive is required for CLASSIC to function.")
        print("Please ensure that you have extracted all CLASSIC files into the same folder after downloading.")
        raise
        
    try:
        if not os.path.exists(f"CLASSIC Data/databases/{game} FID Main.txt"):
            with open_zip() as zip_data:
                zip_data.extract(f"databases/{game} FID Main.txt", "CLASSIC Data")
    except FileNotFoundError:
        print(f"❌ ERROR : UNABLE TO FIND {game} FID Main.txt! CLASSIC will not be able to show FormID values.")
        print("Please ensure that you have extracted all CLASSIC files into the same folder after downloading.")
        raise
    
    if os.path.exists(f"CLASSIC Data/databases/{game} FID Main.txt") and not os.path.exists(f"CLASSIC Data/databases/{game} FormIDs.db"):
        create_formid_db()

def classic_settings(setting=None):
    if not os.path.exists("CLASSIC Settings.yaml"):
        default_settings = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Info.default_settings")
        with open('CLASSIC Settings.yaml', 'w', encoding='utf-8') as file:
            file.write(default_settings)
    if setting:
        get_setting = yaml_settings("CLASSIC Settings.yaml", f"CLASSIC_Settings.{setting}")
        if get_setting is None and "Path" not in setting:  # Error me if I make a stupid mistype.
            print(f"❌ ERROR (classic_settings) : Trying to grab a None value for : '{setting}'")
        return get_setting


def classic_update_check():
    logging.debug("- - - INITIATED UPDATE CHECK")
    if classic_settings("Update Check"):
        classic_local = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Info.version")
        print("❓ (Needs internet connection) CHECKING FOR NEW CLASSIC VERSIONS...")
        print("   (You can disable this check in the EXE or CLASSIC Settings.yaml) \n")
        try:
            response = requests.get("https://api.github.com/repos/evildarkarchon/CLASSIC-Fallout4/releases/latest", timeout=10)
            if not response.status_code == requests.codes.ok:
                response.raise_for_status()
            classic_ver_received = response.json()["name"]
            print(f"Your CLASSIC Version: {classic_local}\nNewest CLASSIC Version: {classic_ver_received}\n")
            if classic_ver_received == classic_local:
                print("✔️ You have the latest version of CLASSIC! \n")
                return True
            else:
                print(yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", f"CLASSIC_Interface.update_warning_{game}"))
        except (ValueError, OSError, requests.exceptions.RequestException) as err:
            print(err)
            print(yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", f"CLASSIC_Interface.update_unable_{game}"))
    else:
        print("\n❌ NOTICE: UPDATE CHECK IS DISABLED IN CLASSIC Settings.yaml \n")
        print("===============================================================================")
    return False


# ================================================
# CHECK DEFAULT DOCUMENTS & GAME FOLDERS / FILES
# ================================================
# =========== CHECK DOCUMENTS FOLDER PATH -> GET GAME DOCUMENTS FOLDER ===========
def docs_path_find():
    logging.debug("- - - INITIATED DOCS PATH CHECK")
    game_sid = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.Main_SteamID")
    docs_name = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.Main_Docs_Name")

    def get_windows_docs_path():
        import ctypes.wintypes
        CSIDL_PERSONAL = 5
        SHGFP_TYPE_CURRENT = 0
        win_buffer = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, win_buffer)
        win_docs = os.path.join(win_buffer.value, fr"My Games\{docs_name}")
        yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Docs", f"{win_docs}")

    def get_linux_docs_path():
        libraryfolders_path = Path.home().joinpath(".local", "share", "Steam", "steamapps", "common", "libraryfolders.vdf")
        if libraryfolders_path.is_file():
            library_path = Path()
            with libraryfolders_path.open(encoding="utf-8", errors="ignore") as steam_library_raw:
                steam_library = steam_library_raw.readlines()
            for library_line in steam_library:
                if "path" in library_line:
                    library_path = Path(library_line.split('"')[3])
                if str(game_sid) in library_line:
                    library_path = library_path.joinpath("steamapps")
                    linux_docs = library_path.joinpath("compatdata", str(game_sid), "pfx", "drive_c", "users", "steamuser", "My Documents", "My Games", docs_name)
                    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Docs", f"{linux_docs}")

    def get_manual_docs_path():
        print(f"> > > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {docs_name}.ini IS LOCATED < < <")
        while True:
            path_input = input(f"(EXAMPLE: C:/Users/Zen/Documents/My Games/{docs_name} | Press ENTER to confirm.)\n> ")
            if os.path.exists(path_input) and os.path.isdir(path_input):
                print(f"You entered: '{path_input}' | This path will be automatically added to CLASSIC Settings.yaml")
                manual_docs = Path(path_input.strip())
                yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Docs", manual_docs)
                break
            else:
                print(f"'{path_input}' is not a valid or existing directory path. Please try again.")

    # =========== CHECK IF GAME DOCUMENTS FOLDER PATH WAS GENERATED AND FOUND ===========
    docs_path = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Docs")
    if docs_path is None:
        if platform.system() == "Windows":
            get_windows_docs_path()
        else:
            get_linux_docs_path()

    docs_path = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Docs")
    try:  # In case .exists() complains about checking a None value.
        if not Path(docs_path).exists():
            get_manual_docs_path()
    except (ValueError, OSError):
        get_manual_docs_path()


def docs_generate_paths():
    logging.debug("- - - INITIATED DOCS PATH GENERATION")
    xse_acronym = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game_Info.XSE_Acronym")
    docs_path = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Docs")

    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Docs_Folder_XSE", fr"{docs_path}\{xse_acronym_base}")
    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Docs_File_PapyrusLog", fr"{docs_path}\Logs\Script\Papyrus.0.log")
    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Docs_File_WryeBashPC", fr"{docs_path}\ModChecker.html")
    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Docs_File_XSE", fr"{docs_path}\{xse_acronym_base}\{xse_acronym.lower()}.log")


# =========== CHECK DOCUMENTS XSE FILE -> GET GAME ROOT FOLDER PATH ===========
def game_path_find():
    logging.debug("- - - INITIATED GAME PATH CHECK")
    xse_file = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Docs_File_XSE")
    xse_acronym = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Game_Info.XSE_Acronym")
    game_name = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.Main_Root_Name")

    if Path(xse_file).is_file():
        with open_file_with_encoding(xse_file) as LOG_Check:
            Path_Check = LOG_Check.readlines()
            for logline in Path_Check:
                if "plugin directory" in logline:
                    logline = logline[19:].replace(f"\\Data\\{xse_acronym_base}\\Plugins", "")
                    game_path = logline.replace("\n", "")
                    if not game_path or not Path(game_path).exists():
                        print(f"> > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {game_name} IS LOCATED < <")
                        path_input = input(fr"(EXAMPLE: C:\Steam\steamapps\common\{game_name} | Press ENTER to confirm.)\n> ")
                        print(f"You entered: {path_input} | This path will be automatically added to CLASSIC Settings.yaml")
                        game_path = Path(path_input.strip())

                    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Game", str(game_path))
    else:
        print(f"❌ CAUTION : THE {xse_acronym.lower()}.log FILE IS MISSING FROM YOUR GAME DOCUMENTS FOLDER! \n")
        print(f"   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n")
        print("    After that, try running CLASSIC again! \n-----\n")


def game_generate_paths():
    logging.debug("- - - INITIATED GAME PATH GENERATION")

    game_path = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Game")
    xse_acronym = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game_Info.XSE_Acronym")

    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_Folder_Data", fr"{game_path}Data")
    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_Folder_Scripts", fr"{game_path}Data\Scripts")
    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_Folder_Plugins", fr"{game_path}Data\{xse_acronym_base}\Plugins")
    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_File_SteamINI", fr"{game_path}steam_api.ini")
    yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_File_EXE", fr"{game_path}{game}{vr}.exe")
    match game:
        case "Fallout4" if not vr:
            yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", "Game_Info.Game_File_AddressLib", fr"{game_path}Data\{xse_acronym_base}\plugins\version-1-10-163-0.bin")
        case "Fallout4" if vr:
            yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", "GameVR_Info.Game_File_AddressLib", fr"{game_path}Data\{xse_acronym_base}\plugins\version-1-2-72-0.csv")


# =========== CHECK GAME EXE FILE -> GET PATH AND HASHES ===========
def game_check_integrity() -> str:
    message_list = []
    logging.debug("- - - INITIATED GAME INTEGRITY CHECK")

    steam_ini_local = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_File_SteamINI")
    exe_hash_old = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.EXE_HashedOLD")
    # exe_hash_new = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.EXE_HashedNEW") | RESERVED FOR 2023 UPDATE
    game_exe_local = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_File_EXE")
    root_name = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.Main_Root_Name")

    game_exe_path = Path(game_exe_local)
    steam_ini_path = Path(steam_ini_local)
    if game_exe_path.is_file():
        with open(game_exe_path, "rb") as f:
            file_contents = f.read()
            # Algo should match the one used for Database YAML!
            exe_hash_local = hashlib.sha256(file_contents).hexdigest()
        # print(f"LOCAL: {exe_hash_local}\nDATABASE: {exe_hash_old}")
        if exe_hash_local == exe_hash_old and not steam_ini_path.exists():
            message_list.append(f"✔️ You have the latest version of {root_name}! \n-----\n")
        elif steam_ini_path.exists():
            message_list.append(f"\U0001F480 CAUTION : YOUR {root_name} GAME / EXE VERSION IS OUT OF DATE \n-----\n")
        else:
            message_list.append(f"❌ CAUTION : YOUR {root_name} GAME / EXE VERSION IS OUT OF DATE \n-----\n")

        if "Program Files" not in str(game_exe_path):
            message_list.append(f"✔️ Your {root_name} game files are installed outside of the Program Files folder! \n-----\n")
        else:
            root_warn = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "Warnings_GAME.warn_root_path")
            message_list.append(root_warn)

    message_output = "".join(message_list)
    return message_output


# =========== CHECK GAME XSE SCRIPTS -> GET PATH AND HASHES ===========
def xse_check_integrity() -> str:  # RESERVED | NEED VR HASH/FILE CHECK
    failed_list = []
    message_list = []
    logging.debug("- - - INITIATED XSE INTEGRITY CHECK")

    catch_errors = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "catch_log_errors")
    xse_acronym = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_Acronym")
    xse_log_file = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Docs_File_XSE")
    xse_full_name = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_FullName")
    xse_ver_latest = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_Ver_Latest")
    adlib_file = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_File_AddressLib")
    
    match adlib_file:
        case str() | Path():
            if Path(adlib_file).exists():
                message_list.append(f"✔️ REQUIRED: *Address Library* for Script Extender is installed! \n-----\n")
            else:
                message_list.append(yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Warnings_MODS.Warn_ADLIB_Missing"))
        case _:
            message_list.append(f"❌ Value for Address Library is invalid or missing from CLASSIC {game} Local.yaml!\n-----\n")

    match xse_log_file:
        case str() | Path():
            if Path(xse_log_file).exists():
                message_list.append(f"✔️ REQUIRED: *{xse_full_name}* is installed! \n-----\n")
                with open_file_with_encoding(xse_log_file) as xse_log:
                    xse_data = xse_log.readlines()
                if str(xse_ver_latest) in xse_data[0]:
                    message_list.append(f"✔️ You have the latest version of *{xse_full_name}*! \n-----\n")
                else:
                    message_list.append(yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Warnings_XSE.Warn_Outdated"))
                for line in xse_data:
                    if any(item.lower() in line.lower() for item in catch_errors):
                        failed_list.append(line)

                if failed_list:
                    message_list.append(f"#❌ CAUTION : {xse_acronym}.log REPORTS THE FOLLOWING ERRORS #\n")
                    for elem in failed_list:
                        message_list.append(f"ERROR > {elem.strip()} \n-----\n")
            else:
                message_list.extend([f"❌ CAUTION : *{xse_acronym.lower()}.log* FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
                                    f"   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n",
                                    "    After that, try running CLASSIC again! \n-----\n"])
        case _:
            message_list.append(f"❌ Value for {xse_acronym.lower()}.log is invalid or missing from CLASSIC {game} Local.yaml!\n-----\n")

    message_output = "".join(message_list)
    return message_output


def xse_check_hashes() -> str:
    message_list = []
    logging.debug("- - - INITIATED XSE FILE HASH CHECK")

    xse_script_missing = xse_script_mismatch = False
    xse_hashedscripts = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_HashedScripts")
    game_folder_scripts = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Game_Folder_Scripts")

    xse_hashedscripts_local = {key: None for key in xse_hashedscripts.keys()}
    for key in xse_hashedscripts_local:
        script_path = Path(fr"{game_folder_scripts}\{str(key)}")
        if script_path.is_file():
            with open(script_path, "rb") as f:
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
                message_list.append(f"❌ CAUTION : {key} Script Extender file is missing from your game Scripts folder! \n-----\n")
                xse_script_missing = True
            else:
                message_list.append(f"[!] CAUTION : {key} Script Extender file is outdated or overriden by another mod! \n-----\n")
                xse_script_mismatch = True

    if xse_script_missing:
        message_list.append(yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Warnings_XSE.Warn_Missing"))
    if xse_script_mismatch:
        message_list.append(yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Warnings_XSE.Warn_Mismatch"))
    if not xse_script_missing and not xse_script_mismatch:
        message_list.append("✔️ All Script Extender files have been found and accounted for! \n-----\n")

    message_output = "".join(message_list)
    return message_output


# ================================================
# CHECK DOCUMENTS GAME INI FILES & INI SETTINGS
# ================================================
def docs_check_folder():
    message_list = []
    docs_name = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.Main_Docs_Name")
    if "onedrive" in docs_name.lower():
        docs_warn = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "Warnings_GAME.warn_docs_path")
        message_list.append(docs_warn)
    message_output = "".join(message_list)
    return message_output


# =========== CHECK DOCS MAIN INI -> CHECK EXISTENCE & CORRUPTION ===========
def docs_check_ini(ini_name) -> str:
    message_list = []
    logging.info(f"- - - INITIATED {ini_name} CHECK")
    folder_docs = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Docs")
    docs_name = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.Main_Docs_Name")

    ini_file_list = list(Path(folder_docs).glob("*.ini"))
    ini_path = Path(folder_docs).joinpath(ini_name)
    if any(ini_name.lower() in file.name.lower() for file in ini_file_list):
        try:
            remove_readonly(ini_path)

            INI_config = configparser.ConfigParser()
            INI_config.optionxform = str
            INI_config.read(ini_path)
            message_list.append(f"✔️ No obvious corruption detected in {ini_name}, file seems OK! \n-----\n")

            if ini_name.lower() == f"{docs_name.lower()}custom.ini":
                if "Archive" not in INI_config.sections():
                    message_list.extend(["❌ WARNING : Archive Invalidation / Loose Files setting is not enabled. \n",
                                         "  CLASSIC will now enable this setting automatically in the game INI files. \n-----\n"])
                    try:
                        INI_config.add_section("Archive")
                    except configparser.DuplicateSectionError:
                        pass
                else:
                    message_list.append("✔️ Archive Invalidation / Loose Files setting is already enabled! \n-----\n")

                INI_config.set("Archive", "bInvalidateOlderFiles", "1")
                INI_config.set("Archive", "sResourceDataDirsFinal", "")

                with open(ini_path, "w+", encoding="utf-8", errors="ignore") as ini_file:
                    INI_config.write(ini_file, space_around_delimiters=False)

        except PermissionError:
            message_list.extend([f"[!] CAUTION : YOUR {ini_name} FILE IS SET TO READ ONLY. \n",
                                 "     PLEASE REMOVE THE READ ONLY PROPERTY FROM THIS FILE, \n",
                                 "     SO CLASSIC CAN MAKE THE REQUIRED CHANGES TO IT. \n-----\n"])

        except (configparser.MissingSectionHeaderError, configparser.ParsingError, ValueError, OSError):
            message_list.extend([f"[!] CAUTION : YOUR {ini_name} FILE IS VERY LIKELY BROKEN, PLEASE CREATE A NEW ONE \n",
                                 f"    Delete this file from your Documents/My Games/{docs_name} folder, then press \n",
                                 f"    *Scan Game Files* in CLASSIC to generate a new {ini_name} file. \n-----\n"])
        except configparser.DuplicateOptionError as e:
            message_list.extend([f"[!] ERROR : Your {ini_name} file has duplicate options! \n",
                                 f"    {e} \n-----\n"])
    else:
        if ini_name.lower() == f"{docs_name.lower()}.ini":
            message_list.extend([f"❌ CAUTION : {ini_name} FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
                                 f"   You need to run the game at least once with {docs_name}Launcher.exe \n",
                                 "    This will create files and INI settings required for the game to run. \n-----\n"])

        if ini_name.lower() == f"{docs_name.lower()}custom.ini":
            with open(ini_path, "a", encoding="utf-8", errors="ignore") as ini_file:
                message_list.extend(["❌ WARNING : Archive Invalidation / Loose Files setting is not enabled. \n",
                                     "  CLASSIC will now enable this setting automatically in the game INI files. \n-----\n"])
                customini_config = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Default_CustomINI")
                ini_file.write(customini_config)

    message_output = "".join(message_list)
    return message_output


# =========== GENERATE FILE BACKUPS ===========
def main_files_backup():
    # Got an expired certificate warning after a few tries, maybe there's a better way?
    # noinspection PyUnresolvedReferences
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    backup_list = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_AutoBackup")
    game_path = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Game")
    xse_acronym = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Game_Info.XSE_Acronym")
    xse_log_file = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Docs_File_XSE")
    xse_ver_latest = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", f"Game{vr}_Info.XSE_Ver_Latest")
    with open_file_with_encoding(xse_log_file) as xse_log:
        xse_data = xse_log.readlines()
    # Grab current xse version to create a folder with that name.
    line_xse = next(line for index, line in enumerate(xse_data) if "version = " in line.lower())
    split_xse = line_xse.split(" ")
    version_xse = xse_ver_latest
    for index, item in enumerate(split_xse):
        if "version" in item.lower():
            index_xse = int(index + 2)
            version_xse = split_xse[index_xse]
            break

    # If there is no folder for current xse version, create it.
    backup_path = f"CLASSIC Backup/Game Files/{version_xse}"
    Path(backup_path).mkdir(parents=True, exist_ok=True)
    # Backup the file if backup of file does not already exist.
    game_files = list(Path(game_path).glob("*.*"))
    backup_files = list(Path(backup_path).glob("*.*"))
    for file in game_files:
        if any(file.name in item for item in backup_list):
            if all(file.name not in str(item) for item in backup_files):
                destination_file = f"{backup_path}/{file.name}"
                shutil.copy2(file, destination_file)

    # Check for Script Extender updates since we also need local version for it.
    xse_links = []
    try:
        response = requests.get(f"https://{xse_acronym_base.lower()}.silverlock.org", verify=False, timeout=10)
        if response.status_code == 200:  # Check if request went through.
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')  # Find all anchor tags (links) in HTML.
            for link in links:
                href = link.get('href')  # We only care about links for archives.
                if href and (re.search(r'\.7z$', href) or re.search(r'\.zip$', href)):
                    xse_links.append(str(href))
        else:
            print(f"❌ ERROR : Unable to check for {xse_acronym} updates. \n Status Code: {response.status_code} \n")

    except (ValueError, OSError, requests.exceptions.RequestException) as err:
        print(f"❌ ERROR : Unable to check for {xse_acronym} updates. \n {err} \n")

    if xse_links:
        version_format = str(version_xse.replace(".", "_").replace("0_", ""))
        if not any(version_format in link for link in xse_links):
            print(yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Warnings_XSE.Warn_Outdated"))


# =========== GENERATE MAIN RESULTS ===========
def main_combined_result():
    vrmode_check()
    combined_return = [game_check_integrity(), xse_check_integrity(), xse_check_hashes(), docs_check_folder(),
                       docs_check_ini(f"{game}.ini"), docs_check_ini(f"{game}Custom.ini"), docs_check_ini(f"{game}Prefs.ini")]
    combined_result = "".join(combined_return)
    return combined_result


def main_generate_required():
    configure_logging()
    classic_logging()
    classic_data_extract()
    classic_generate_files()
    classic_ver = yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Info.version")
    game_name = yaml_settings(f"CLASSIC Data/databases/CLASSIC {game}.yaml", "Game_Info.Main_Root_Name")
    print(f"Hello World! | Crash Log Auto Scanner & Setup Integrity Checker | {classic_ver} | {game_name}")
    print("REMINDER: COMPATIBLE CRASH LOGS MUST START WITH 'crash-' AND MUST HAVE .log EXTENSION \n")
    print("❓ PLEASE WAIT WHILE CLASSIC CHECKS YOUR SETTINGS AND GAME SETUP...")
    logging.debug(f"> > > STARTED {classic_ver}")

    vrmode_check()
    game_path = yaml_settings(f"CLASSIC Data/CLASSIC {game} Local.yaml", f"Game{vr}_Info.Root_Folder_Game")

    if not game_path:
        docs_path_find()
        docs_generate_paths()
        game_path_find()
        game_generate_paths()
    else:
        main_files_backup()

    print("✔️ ALL CLASSIC AND GAME SETTINGS CHECKS HAVE BEEN PERFORMED!")
    print("    YOU CAN NOW SCAN YOUR CRASH LOGS, GAME AND/OR MOD FILES \n")


if __name__ == "__main__":  # AKA only autorun / do the following when NOT imported.
    main_generate_required()
    os.system("pause")
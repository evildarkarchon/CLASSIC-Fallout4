import winreg
from pathlib import Path
from typing import cast

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import FO4_VERSIONS, NG_VERSION, NULL_VERSION, OG_VERSION, YAML
from ClassicLib.Logger import logger
from ClassicLib.Util import get_game_version, open_file_with_encoding
from ClassicLib.YamlSettingsCache import yaml_settings


def game_path_find() -> None:
    """
    Performs game path verification and ensures that the game executable is
    correctly located. It checks for the installation path in the Windows
    Registry and verifies the game directory using log files or user input.
    The method also updates the YAML settings for future reference.

    Raises:
        TypeError: If the XSE loader log file or game-related YAML settings are
            not of the expected type.
    """
    logger.debug("- - - INITIATED GAME PATH CHECK")

    path: str | None
    game_path: Path | None

    try:
        # Open the registry key
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 rf"SOFTWARE\WOW6432Node\Bethesda Softworks\{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}")  # pyright: ignore[reportPossiblyUnboundVariable]
        # Query the 'installed path' value
        path, _ = winreg.QueryValueEx(reg_key, "installed path")  # pyright: ignore[reportPossiblyUnboundVariable]
        winreg.CloseKey(reg_key)  # pyright: ignore[reportPossiblyUnboundVariable]
    except FileNotFoundError:
        try:
            reg_key_gog = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         r"SOFTWARE\WOW6432Node\GOG.com\Games\1998527297")  # pyright: ignore[reportPossiblyUnboundVariable]
            path, _ = winreg.QueryValueEx(reg_key_gog, "path")  # pyright: ignore[reportPossiblyUnboundVariable]
            winreg.CloseKey(reg_key_gog)  # pyright: ignore[reportPossiblyUnboundVariable]
        except (FileNotFoundError, UnboundLocalError, OSError):
            game_path = None
        else:
            game_path = Path(path) if path else None
    except (UnboundLocalError, OSError):
        game_path = None
    else:
        game_path = Path(path) if path else None

    exe_name = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"

    if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
        yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game",
                      str(game_path))
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)
        return

    xse_file = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_XSE")
    xse_acronym = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    game_name = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Root_Name")
    if not (isinstance(xse_file, str) or xse_file is None):
        raise TypeError
    if not (isinstance(xse_acronym, str) and isinstance(xse_acronym_base, str) and isinstance(game_name, str)):
        raise TypeError

    if not xse_file or not Path(cast("str", xse_file)).is_file():
        print(f"❌ CAUTION : THE {xse_acronym.lower()}.log FILE IS MISSING FROM YOUR GAME DOCUMENTS FOLDER! \n")
        print(f"   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n")
        print("    After that, try running CLASSIC again! \n-----\n")
        return

    with open_file_with_encoding(cast("str", xse_file)) as LOG_Check:
        path_check = LOG_Check.readlines()
    for logline in path_check:
        if logline.startswith("plugin directory"):
            logline = logline.split("=", maxsplit=1)[1].strip().replace(f"\\Data\\{xse_acronym_base}\\Plugins",
                                                                        "").replace("\n", "")
            game_path = Path(logline)
            break
    if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
        yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game",
                      str(game_path))
        return

    if GlobalRegistry.is_gui_mode():
        game_path_gui = GlobalRegistry.get_game_path_gui()
        if game_path_gui is None:
            raise TypeError("CMain not initialized")
        game_path_gui.game_path_signal.emit()
        return

    while True:
        print(f"> > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {game_name} IS LOCATED < <")
        path_input = input(fr"(EXAMPLE: C:\Steam\steamapps\common\{game_name} | Press ENTER to confirm.)\n> ")
        print(f"You entered: {path_input} | This path will be automatically added to CLASSIC Settings.yaml")
        game_path = Path(path_input.strip())
        if game_path and game_path.joinpath(exe_name).is_file():
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game",
                          str(game_path))
            return
        print(
            f"❌ ERROR : NO {GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe FILE FOUND IN '{game_path}'! Please try again.")


def game_generate_paths() -> None:
    """
    Generates and updates file paths for game configurations based on game variant and version.

    This function reads game-specific configurations and dynamically constructs essential
    file paths required for game execution. The paths are stored in a configuration YAML
    file for local game settings. Additionally, it handles version-specific file naming
    in certain cases such as "AddressLib" files for different versions of Fallout 4. The
    function also ensures appropriate types for necessary variables, raising errors
    if validations fail.

    Raises:
        TypeError: If `game_path` or `xse_acronym_base` are not strings.
        ValueError: If an unsupported or invalid `game_version` is detected for Fallout 4.

    Returns:
        None
    """
    logger.debug("- - - INITIATED GAME PATH GENERATION")

    game_path = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
    yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    if not (isinstance(game_path, str) and isinstance(xse_acronym_base, str)):
        raise TypeError

    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Data",
                  rf"{game_path}\Data")
    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Scripts",
                  rf"{game_path}\Data\Scripts")
    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Plugins",
                  fr"{game_path}\Data\{xse_acronym_base}\Plugins")
    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_SteamINI",
                  rf"{game_path}\steam_api.ini")
    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_EXE",
                  fr"{game_path}\{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe")
    game_version = get_game_version(
        Path(cast("str",
                  yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_EXE"))))
    match GlobalRegistry.get_game():
        case "Fallout4" if not GlobalRegistry.get_vr():
            if (
                    not game_version or game_version not in FO4_VERSIONS) and game_version != NULL_VERSION:
                raise ValueError("Unsupported or invalid game version")
            if game_version in (OG_VERSION, NULL_VERSION):
                yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib",
                              fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-163-0.bin")
            elif game_version == NG_VERSION:
                yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib",
                              fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-984-0.bin")
        case "Fallout4" if GlobalRegistry.get_vr():
            yaml_settings(str, YAML.Game_Local, "GameVR_Info.Game_File_AddressLib",
                          fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-2-72-0.csv")

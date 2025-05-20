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
    Attempts to locate and validate the installation directory of a game by retrieving the path through
    several methods, including the system registry, log file inspection, and user input. Registers the
    located path or updates configuration settings as needed.

    Raises:
        TypeError: If invalid types are encountered, such as improperly formatted settings or unexpected
        results during path validation.

    Notes:
        - The function uses several fallback mechanisms to determine the correct game path.
        - If the registry lookup fails, the function attempts to find the path via a log file or
          prompts the user for manual input.
        - Registry keys from both Bethesda Softworks and GOG.com installations are queried initially.
        - Global configuration and settings files are updated upon successfully finding the valid path.
    """
    logger.debug("- - - INITIATED GAME PATH CHECK")

    path: str | None
    game_path: Path | None

    try:
        # Open the registry key
        reg_key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Bethesda Softworks\{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}"
        )  # pyright: ignore[reportPossiblyUnboundVariable]
        # Query the 'installed path' value
        path, _ = winreg.QueryValueEx(reg_key, "installed path")  # pyright: ignore[reportPossiblyUnboundVariable]
        winreg.CloseKey(reg_key)  # pyright: ignore[reportPossiblyUnboundVariable]
    except FileNotFoundError:
        try:
            reg_key_gog = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\Games\1998527297")  # pyright: ignore[reportPossiblyUnboundVariable]
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

    exe_name: str = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"

    if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
        yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)
        return

    xse_file: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_XSE")
    xse_acronym: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_acronym_base: str | None = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    game_name: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Root_Name")
    if not (isinstance(xse_acronym, str) and isinstance(xse_acronym_base, str) and isinstance(game_name, str)):
        raise TypeError

    if not xse_file or not Path(cast("str", xse_file)).is_file():
        print(f"❌ CAUTION : THE {xse_acronym.lower()}.log FILE IS MISSING FROM YOUR GAME DOCUMENTS FOLDER! \n")
        print(f"   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n")
        print("    After that, try running CLASSIC again! \n-----\n")
        return

    with open_file_with_encoding(cast("str", xse_file)) as LOG_Check:
        path_check: list[str] = LOG_Check.readlines()
    for logline in path_check:
        if logline.startswith("plugin directory"):
            logline = logline.split("=", maxsplit=1)[1].strip().replace(f"\\Data\\{xse_acronym_base}\\Plugins", "").replace("\n", "")
            game_path = Path(logline)
            break
    if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
        yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
        return

    if GlobalRegistry.is_gui_mode():
        # Show dialog until valid path is selected or user cancels
        from CLASSIC_Interface import show_game_path_dialog_static

        # This will return a valid path or exit the application if cancelled
        game_path = show_game_path_dialog_static()

        # If we get here, we have a valid path (function exits if user cancels)
        yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)
        return

    while True:
        print(f"> > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {game_name} IS LOCATED < <")
        path_input: str = input(rf"(EXAMPLE: C:\Steam\steamapps\common\{game_name} | Press ENTER to confirm.)\n> ")
        print(f"You entered: {path_input} | This path will be automatically added to CLASSIC Settings.yaml")
        game_path = Path(path_input.strip())
        if game_path and game_path.joinpath(exe_name).is_file():
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
            return
        print(f"❌ ERROR : NO {GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe FILE FOUND IN '{game_path}'! Please try again.")


def game_generate_paths() -> None:
    """
    Generates and configures the necessary paths and files for the current game version. This function interacts
    with a YAML settings manager to set up paths and validates game versions. It ensures the local game environment
    is correctly configured based on the registry's active game and version setting.

    Raises:
        TypeError: If the game path or XSE acronym base is not a string type as expected.
        ValueError: If the game version is unsupported, invalid, or does not match the known valid versions for Fallout4.
    """
    logger.debug("- - - INITIATED GAME PATH GENERATION")

    game_path = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
    yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    if not (isinstance(game_path, str) and isinstance(xse_acronym_base, str)):
        raise TypeError

    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Data", rf"{game_path}\Data")
    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Scripts", rf"{game_path}\Data\Scripts")
    yaml_settings(
        str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Plugins", rf"{game_path}\Data\{xse_acronym_base}\Plugins"
    )
    yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_SteamINI", rf"{game_path}\steam_api.ini")
    yaml_settings(
        str,
        YAML.Game_Local,
        f"Game{GlobalRegistry.get_vr()}_Info.Game_File_EXE",
        rf"{game_path}\{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe",
    )
    game_version = get_game_version(
        Path(cast("str", yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_EXE")))
    )
    match GlobalRegistry.get_game():
        case "Fallout4" if not GlobalRegistry.get_vr():
            if (not game_version or game_version not in FO4_VERSIONS) and game_version != NULL_VERSION:
                raise ValueError("Unsupported or invalid game version")
            if game_version in (OG_VERSION, NULL_VERSION):
                yaml_settings(
                    str,
                    YAML.Game_Local,
                    "Game_Info.Game_File_AddressLib",
                    rf"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-163-0.bin",
                )
            elif game_version == NG_VERSION:
                yaml_settings(
                    str,
                    YAML.Game_Local,
                    "Game_Info.Game_File_AddressLib",
                    rf"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-984-0.bin",
                )
        case "Fallout4" if GlobalRegistry.get_vr():
            yaml_settings(
                str,
                YAML.Game_Local,
                "GameVR_Info.Game_File_AddressLib",
                rf"{game_path}\Data\{xse_acronym_base}\plugins\version-1-2-72-0.csv",
            )

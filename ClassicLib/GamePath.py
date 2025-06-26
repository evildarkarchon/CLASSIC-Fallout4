import platform
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ClassicLib import GlobalRegistry, msg_error, msg_info
from ClassicLib.Constants import FO4_VERSIONS, NG_VERSION, NULL_VERSION, OG_VERSION, YAML
from ClassicLib.Logger import logger
from ClassicLib.Util import get_game_version, open_file_with_encoding
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from packaging.version import Version


def _game_path_find_registry(exe_name: str) -> Path | None:
    """
    Finds the installation path of a game via system registry and validates the path.

    The method attempts to retrieve the installation path of a specific game by querying the Windows
    registry for registry keys associated with the game's installation. It first checks the key for
    Bethesda Softworks and then attempts to retrieve the path for GOG's registry key if the first
    attempt fails. The retrieved path is validated to ensure it exists and includes the game's
    executable. If successful, the validated path is registered globally.

    Args:
        exe_name: The name of the game's executable file to validate its presence in the resolved path.

    Returns:
        A Path object representing the game's valid installation directory if found and validated,
        otherwise None.
    """
    import winreg

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

    if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
        yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)
        return game_path
    return None


def game_path_find() -> None:
    """
    Finds and verifies the game installation path by checking specific requirements and interacting with the user
    through different interfaces depending on context (e.g., GUI mode or console). Updates the game's settings once
    a valid path is confirmed.

    Raises
    ------
    TypeError
        If essential configuration data retrieved from YAML settings is not of the expected type.
    """
    logger.debug("- - - INITIATED GAME PATH CHECK")

    exe_name: str = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"

    game_path = _game_path_find_registry(exe_name) if platform.system() == "Windows" else None

    xse_file: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_XSE")
    xse_acronym: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_acronym_base: str | None = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    game_name: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Root_Name")
    if not (isinstance(xse_acronym, str) and isinstance(xse_acronym_base, str) and isinstance(game_name, str)):
        raise TypeError

    # Validate XSE file path before attempting to access it
    from ClassicLib.Util import validate_path

    if not xse_file:
        msg_error(
            f"❌ CAUTION : THE {xse_acronym.lower()}.log FILE PATH IS NOT CONFIGURED! \n   Please configure the game documents folder first! \n-----\n"
        )
        return

    is_valid, error_msg = validate_path(cast("str", xse_file), check_write=False, check_read=True)
    if not is_valid:
        if "does not exist" in error_msg:
            msg_error(
                f"❌ CAUTION : THE {xse_acronym.lower()}.log FILE IS MISSING FROM YOUR GAME DOCUMENTS FOLDER! \n   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n    After that, try running CLASSIC again! \n   Error: {error_msg} \n-----\n"
            )
        else:
            msg_error(
                f"❌ CAUTION : CANNOT ACCESS {xse_acronym.lower()}.log FILE! \n   Error: {error_msg} \n   Please check your game documents folder and try again! \n-----\n"
            )
        return

    with open_file_with_encoding(cast("str", xse_file)) as LOG_Check:
        path_check: list[str] = LOG_Check.readlines()
    for logline in path_check:
        if logline.startswith("plugin directory"):
            logline: str = logline.split("=", maxsplit=1)[1].strip().replace(f"\\Data\\{xse_acronym_base}\\Plugins", "").replace("\n", "")
            game_path = Path(logline)
            break
    if game_path:
        # Validate the game path extracted from XSE log
        is_valid, error_msg = validate_path(game_path, check_write=False, check_read=True)
        if is_valid and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
            return
        if not is_valid:
            logger.warning(f"Game path from XSE log is not accessible: {error_msg}")
        else:
            logger.warning(f"Game executable not found in path from XSE log: {game_path}")

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
        msg_info(f"> > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {game_name} IS LOCATED < <")
        path_input: str = input(rf"(EXAMPLE: C:\Steam\steamapps\common\{game_name} | Press ENTER to confirm.)\n> ")
        msg_info(f"You entered: {path_input} | This path will be automatically added to CLASSIC Settings.yaml")
        game_path = Path(path_input.strip())

        # Validate path before checking for executable
        is_valid, error_msg = validate_path(game_path, check_write=False, check_read=True)
        if not is_valid:
            msg_error(f"ERROR : {error_msg}")
            continue

        if game_path and game_path.joinpath(exe_name).is_file():
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
            return
        msg_error(f"ERROR : NO {GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe FILE FOUND IN '{game_path}'! Please try again.")


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

    game_path: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
    yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_acronym_base: str | None = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
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
    game_version: Version = get_game_version(
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

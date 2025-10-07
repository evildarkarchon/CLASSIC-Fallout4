"""
Handles operations related to resolving and validating game installation paths, including system
registry checks, user interactions, and configuration updates.

The module ensures the correct game path is determined based on platform-specific logic, registry
lookups, and user-provided input. Once validated, the paths are registered and stored in YAML
settings.

Functions:
    _game_path_find_registry: Retrieves the game's installation path from the Windows registry
    if available.
    game_path_find: Coordinates the process of finding, validating, and configuring the game's
    installation path using multiple strategies.
    game_generate_paths: Configures game paths and files necessary for the current game version.
"""

import platform
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ClassicLib import GlobalRegistry, msg_error, msg_info
from ClassicLib.Constants import FO4_VERSIONS, NG_VERSION, NULL_VERSION, OG_VERSION, YAML
from ClassicLib.Interface.PathDialogMixin import show_game_path_dialog_static
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
    # noinspection PyCompatibility
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
        from ClassicLib.ResourceLoader import ResourceLoader

        # Save to all cache locations for uvx compatibility
        ResourceLoader.save_path_to_cache(game_path, "GamePath")
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)
        return game_path
    return None


class GamePathFinder:
    """Helper class to encapsulate game path finding logic."""

    def __init__(self):
        self.exe_name = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
        self.xse_file = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_XSE")
        self.xse_acronym = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
        self.xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
        self.game_name = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Root_Name")

        if not all(isinstance(val, str) for val in [self.xse_acronym, self.xse_acronym_base, self.game_name]):
            raise TypeError("Required YAML settings are not strings")

    def _validate_xse_file(self) -> bool:
        """Validate XSE file existence and accessibility."""
        from ClassicLib.Util import validate_path

        if not self.xse_file:
            xse_acronym_lower = self.xse_acronym.lower() if self.xse_acronym else "xse"
            msg_error(
                f"❌ CAUTION : THE {xse_acronym_lower}.log FILE PATH IS NOT CONFIGURED! \n"
                "   Please configure the game documents folder first! \n-----\n"
            )
            return False

        is_valid, error_msg = validate_path(cast("str", self.xse_file), check_write=False, check_read=True)
        if not is_valid:
            self._report_xse_error(error_msg)
            return False

        return True

    def _report_xse_error(self, error_msg: str) -> None:
        """Report XSE file access errors with appropriate messages."""
        xse_acronym_lower = self.xse_acronym.lower() if self.xse_acronym else "xse"
        if "does not exist" in error_msg:
            msg_error(
                f"❌ CAUTION : THE {xse_acronym_lower}.log FILE IS MISSING FROM YOUR GAME DOCUMENTS FOLDER! \n"
                f"   You need to run the game at least once with {xse_acronym_lower}_loader.exe \n"
                f"    After that, try running CLASSIC again! \n   Error: {error_msg} \n-----\n"
            )
        else:
            msg_error(
                f"❌ CAUTION : CANNOT ACCESS {xse_acronym_lower}.log FILE! \n"
                f"   Error: {error_msg} \n"
                "   Please check your game documents folder and try again! \n-----\n"
            )

    def _parse_xse_log_for_path(self) -> Path | None:
        """Parse XSE log file to extract game path."""
        with open_file_with_encoding(cast("str", self.xse_file)) as log_file:
            for line in log_file:
                if line.startswith("plugin directory"):
                    path_str = (
                        line.split("=", maxsplit=1)[1]
                        .strip()
                        .replace(f"\\Data\\{self.xse_acronym_base}\\Plugins", "")
                        .replace("\n", "")
                    )
                    return Path(path_str)
        return None

    def _validate_game_path(self, game_path: Path) -> bool:
        """Validate that the game path is valid and contains the game executable."""
        from ClassicLib.Util import validate_path

        is_valid, error_msg = validate_path(game_path, check_write=False, check_read=True)

        if not is_valid:
            logger.warning(f"Game path from XSE log is not accessible: {error_msg}")
            return False

        if not game_path.is_dir():
            logger.warning(f"Game path is not a directory: {game_path}")
            return False

        if not game_path.joinpath(self.exe_name).is_file():
            logger.warning(f"Game executable not found in path: {game_path}")
            return False

        return True

    def _save_game_path(self, game_path: Path) -> None:
        """Save the validated game path to settings and cache."""
        from ClassicLib.ResourceLoader import ResourceLoader

        # Save to all cache locations (cache.yaml, Local.yaml, and suggest env var)
        ResourceLoader.save_path_to_cache(game_path, "GamePath")
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)

    def _get_path_from_user_gui(self) -> Path:
        """Get game path from user via GUI dialog."""
        # This will return a valid path or exit the application if cancelled
        result = show_game_path_dialog_static()
        if result is None:
            # Should not reach here as the dialog exits on cancel, but handle it safely
            raise RuntimeError("Game path selection was cancelled")
        return result

    def _get_path_from_user_console(self) -> Path:
        """Get game path from user via console input."""
        from ClassicLib.Util import validate_path

        while True:
            msg_info(f"> > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {self.game_name} IS LOCATED < <")
            path_input = input(rf"(EXAMPLE: C:\Steam\steamapps\common\{self.game_name} | Press ENTER to confirm.)\n> ")
            msg_info(f"You entered: {path_input} | This path will be automatically added to CLASSIC Settings.yaml")

            game_path = Path(path_input.strip())

            # Validate path
            is_valid, error_msg = validate_path(game_path, check_write=False, check_read=True)
            if not is_valid:
                msg_error(f"ERROR : {error_msg}")
                continue

            # Check for executable
            if game_path.joinpath(self.exe_name).is_file():
                return game_path

            msg_error(f"ERROR : NO {self.exe_name} FILE FOUND IN '{game_path}'! Please try again.")

    def find_game_path(self) -> None:
        """Main method to find and configure the game path."""
        # First, check if we have a cached path (for uvx compatibility)
        from ClassicLib.ResourceLoader import ResourceLoader

        cached_path = ResourceLoader.get_cached_game_path()
        if cached_path and cached_path.joinpath(self.exe_name).is_file():
            logger.debug(f"Using cached game path: {cached_path}")
            GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, cached_path)
            # Still save to Local.yaml for consistency
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(cached_path))
            return

        # Try registry first on Windows
        if platform.system() == "Windows":
            game_path = _game_path_find_registry(self.exe_name)
            if game_path:
                return

        # Validate XSE file
        if not self._validate_xse_file():
            return

        # Try to extract path from XSE log
        game_path = self._parse_xse_log_for_path()
        if game_path and self._validate_game_path(game_path):
            self._save_game_path(game_path)
            return

        # Fall back to user input
        if GlobalRegistry.is_gui_mode():
            game_path = self._get_path_from_user_gui()
        else:
            game_path = self._get_path_from_user_console()

        self._save_game_path(game_path)


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

    finder = GamePathFinder()
    finder.find_game_path()


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
            if game_version in {OG_VERSION, NULL_VERSION}:
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

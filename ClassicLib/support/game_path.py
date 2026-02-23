"""Handle operations related to resolving and validating game installation paths.

The module ensures the correct game path is determined using Rust GamePathFinder.
Once validated, the paths are registered and stored in YAML settings.

**Implementation**: All path-finding operations use Rust GamePathFinder exclusively.
There is no Python fallback - if the Rust module is unavailable, ImportError propagates.

Functions:
    _game_path_find_registry: Retrieves the game's installation path via Rust registry lookup.
    game_path_find: Coordinates the process of finding, validating, and configuring the game's
        installation path using multiple strategies.
    game_generate_paths: Configures game paths and files necessary for the current game version.
"""

import asyncio
import functools
from pathlib import Path
from typing import TYPE_CHECKING, cast

# Direct Rust import - ImportError propagates if unavailable (Rust-only, hard fail)
from classic_path import GamePathFinder as RustGamePathFinder
from classic_path import PathValidator

from ClassicLib.core.constants import NULL_VERSION, YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.Interface.controllers.path_dialog import show_game_path_dialog_static
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.messaging import msg_error, msg_info
from ClassicLib.support.versions import get_version_registry

if TYPE_CHECKING:
    from packaging.version import Version


@functools.lru_cache(maxsize=1)
def _log_version_warning(game_version: "Version", match_message: str = "") -> bool:
    """Log a warning about unsupported or unknown game versions.

    Uses the VersionRegistry to get the list of supported versions dynamically.
    This function is decorated with lru_cache so it only runs once per unique
    (game_version, match_message) combination.

    Args:
        game_version: The detected game version.
        match_message: Optional message from VersionRegistry matching.

    Returns:
        True (cached -- function runs only once per unique arguments).

    """
    registry = get_version_registry()
    supported = [str(v.version) for v in registry.get_all_for_game("Fallout4")]
    logger.warning(f"Unknown game version detected: {game_version}. Supported versions: {', '.join(supported)}. {match_message}")
    return True


def _game_path_find_registry(exe_name: str) -> Path | None:
    """Find the installation path of a game via Rust registry lookup.

    Uses Rust GamePathFinder for registry queries. On success, saves the path
    to cache and registers it globally.

    Args:
        exe_name: The name of the game's executable file.

    Returns:
        A Path object representing the game's valid installation directory if found,
        otherwise None.

    """
    try:
        finder = RustGamePathFinder(
            exe_name,
            None,  # xse_loader not needed for registry lookup
            GlobalRegistry.get_game(),
            bool(GlobalRegistry.get_vr()),
        )
        # Try to find via registry (cached_path=None, xse_log_path=None)
        path_str = finder.find_game_path(cached_path=None, xse_log_path=None)
    except FileNotFoundError:
        logger.debug("Registry lookup failed: game not found")
        return None
    except (ValueError, OSError, RuntimeError) as e:
        logger.debug(f"Registry lookup error: {e}")
        return None

    game_path = Path(path_str)
    from ClassicLib.support.resources import ResourceLoader

    ResourceLoader.save_path_to_cache(game_path, "GamePath")
    GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)
    return game_path


class GamePathFinder:
    """Handle the discovery and configuration of the game path.

    This class locates the installation directory of a game using Rust GamePathFinder.
    It utilizes cached paths, system registry (on Windows), XSE log parsing, and user
    input as fallback strategies.

    Attributes:
        exe_name: Name of the game executable file.
        xse_file: Path to the XSE log file.
        xse_acronym: Acronym used in the XSE file configuration.
        xse_acronym_base: Base acronym for XSE.
        game_name: Root name of the game.

    """

    def __init__(self) -> None:
        """Initialize GamePathFinder with YAML settings.

        Note: This constructor uses synchronous yaml_settings(). For async contexts,
        use the async factory method create_async() instead.

        Raises:
            TypeError: If any of the YAML settings are not strings.
            RuntimeError: If called from within an async context.

        """
        self.exe_name = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
        self.xse_file = yaml_settings(str, YAML.Game_Local, "Game_Info.Docs_File_XSE")

        # Get XSE acronyms from Version Registry (static metadata).
        # XSE acronym is identical across FO4_OG / FO4_NG / FO4_AE ("F4SE");
        # FO4_OG is used as the canonical non-VR source for these static fields.
        registry = get_version_registry()
        is_vr = GlobalRegistry.get_vr() == "VR"
        version_info = registry.get_by_id("FO4_VR" if is_vr else "FO4_OG")
        base_version_info = registry.get_by_id("FO4_OG")
        self.xse_acronym = version_info.xse.acronym if version_info and version_info.xse else None
        self.xse_acronym_base = base_version_info.xse.acronym if base_version_info and base_version_info.xse else None

        self.game_name = yaml_settings(str, YAML.Game, "Game_Info.Main_Root_Name")

        if not all(isinstance(val, str) for val in [self.xse_acronym, self.xse_acronym_base, self.game_name]):
            raise TypeError("Required YAML settings are not strings")

        # Create Rust finder instance
        self._rust_finder = RustGamePathFinder(
            self.exe_name,
            f"{self.xse_acronym_base.lower()}_loader.exe" if self.xse_acronym_base else None,
            GlobalRegistry.get_game(),
            GlobalRegistry.is_vr_version(),
        )

    @classmethod
    async def create_async(cls) -> "GamePathFinder":
        """Async factory method to create a GamePathFinder instance.

        This method should be used in async contexts instead of the synchronous __init__.
        It uses yaml_settings_async() to load configuration without blocking.

        Returns:
            GamePathFinder: A fully initialized instance with YAML settings loaded.

        Raises:
            TypeError: If any of the YAML settings are not strings.

        """
        from ClassicLib.io.yaml import yaml_settings_async

        # Create instance without calling __init__
        instance = cls.__new__(cls)

        # Initialize attributes using async yaml operations
        instance.exe_name = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
        instance.xse_file = await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Docs_File_XSE")

        # Get XSE acronyms from Version Registry (static metadata).
        # XSE acronym is identical across FO4_OG / FO4_NG / FO4_AE ("F4SE");
        # FO4_OG is used as the canonical non-VR source for these static fields.
        registry = get_version_registry()
        is_vr = GlobalRegistry.get_vr() == "VR"
        version_info = registry.get_by_id("FO4_VR" if is_vr else "FO4_OG")
        base_version_info = registry.get_by_id("FO4_OG")
        instance.xse_acronym = version_info.xse.acronym if version_info and version_info.xse else None
        instance.xse_acronym_base = base_version_info.xse.acronym if base_version_info and base_version_info.xse else None

        instance.game_name = await yaml_settings_async(str, YAML.Game, "Game_Info.Main_Root_Name")

        if not all(isinstance(val, str) for val in [instance.xse_acronym, instance.xse_acronym_base, instance.game_name]):
            raise TypeError("Required YAML settings are not strings")

        # Create Rust finder instance
        instance._rust_finder = RustGamePathFinder(
            instance.exe_name,
            f"{instance.xse_acronym_base.lower()}_loader.exe" if instance.xse_acronym_base else None,
            GlobalRegistry.get_game(),
            GlobalRegistry.is_vr_version(),
        )

        return instance

    @staticmethod
    def _get_path_from_user_gui() -> Path:
        """Retrieve a file path from the user via a graphical user interface (GUI).

        Raises:
            RuntimeError: If the user cancels the file path selection dialog.

        Returns:
            Path: The file path selected by the user.

        """
        result = show_game_path_dialog_static()
        if result is None:
            raise RuntimeError("Game path selection was cancelled")
        return result

    def _get_path_from_user_console(self) -> Path:
        """Retrieve and validate a directory path from the user via console input.

        Returns:
            Path: The validated directory path provided by the user.

        """
        while True:
            msg_info(f"> > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {self.game_name} IS LOCATED < <")
            path_input = input(rf"(EXAMPLE: C:\Steam\steamapps\common\{self.game_name} | Press ENTER to confirm.)" + "\n> ")
            msg_info(f"You entered: {path_input} | This path will be automatically added to CLASSIC Settings.yaml")

            game_path = Path(path_input.strip())

            # Validate using Rust PathValidator
            if not PathValidator.is_valid_path(str(game_path)):
                msg_error(f"ERROR : Path does not exist: {game_path}")
                continue

            # Check for executable using Rust validation
            try:
                self._rust_finder.validate_game_path(str(game_path))
            except ValueError as e:
                msg_error(f"ERROR : {e}")
            else:
                return game_path

    @staticmethod
    def _save_game_path(game_path: Path) -> None:
        """Save the provided game path to cache and register it globally.

        Args:
            game_path: The path to the game directory to be saved.

        """
        from ClassicLib.support.resources import ResourceLoader

        ResourceLoader.save_path_to_cache(game_path, "GamePath")
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)

    @staticmethod
    async def _save_game_path_async(game_path: Path) -> None:
        """Asynchronously save the game path to cache and register it globally.

        Args:
            game_path: The path to the game directory to be saved.

        """
        from ClassicLib.support.resources import ResourceLoader

        await ResourceLoader.save_path_to_cache_async(game_path, "GamePath")
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)

    def find_game_path(self) -> None:
        """Find and set the game installation path (sync version).

        This method determines the path to the game installation by using various
        approaches: cached paths, registry lookup, XSE log parsing, and user input.

        Note: For async contexts, use find_game_path_async() instead.
        """
        from ClassicLib.support.resources import ResourceLoader

        # Check cached path first
        cached_path = ResourceLoader.get_cached_game_path()
        if cached_path and PathValidator.is_valid_path(str(cached_path)):
            # Validate with Rust
            try:
                self._rust_finder.validate_game_path(str(cached_path))
            except (ValueError, FileNotFoundError):
                logger.debug("Cached path invalid, trying other methods")
            else:
                logger.debug(f"Using cached game path: {cached_path}")
                GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, cached_path)
                yaml_settings(str, YAML.Game_Local, "Game_Info.Root_Folder_Game", str(cached_path))
                return

        # Try Rust finder with all strategies
        xse_log_path = str(self.xse_file) if self.xse_file else None
        try:
            path_str = self._rust_finder.find_game_path(cached_path=str(cached_path) if cached_path else None, xse_log_path=xse_log_path)
        except FileNotFoundError:
            logger.debug("Rust finder could not find game path, prompting user")
        else:
            game_path = Path(path_str)
            self._save_game_path(game_path)
            return

        # Fall back to user input
        game_path = self._get_path_from_user_gui() if GlobalRegistry.is_gui_mode() else self._get_path_from_user_console()
        self._save_game_path(game_path)

    async def find_game_path_async(self) -> None:
        """Asynchronously find and set the game installation path.

        This is the async version that should be used from async contexts.
        Uses run_in_executor() for Rust calls to prevent blocking the event loop.
        """
        from ClassicLib.io.yaml import yaml_settings_async
        from ClassicLib.support.resources import ResourceLoader

        loop = asyncio.get_running_loop()

        # Check cached path first
        cached_path = await ResourceLoader.get_cached_game_path_async()
        if cached_path:
            is_valid = await loop.run_in_executor(None, PathValidator.is_valid_path, str(cached_path))
            if is_valid:
                try:
                    await loop.run_in_executor(None, self._rust_finder.validate_game_path, str(cached_path))
                except (ValueError, FileNotFoundError):
                    logger.debug("Cached path invalid, trying other methods")
                else:
                    logger.debug(f"Using cached game path: {cached_path}")
                    GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, cached_path)
                    await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Root_Folder_Game", str(cached_path))
                    return

        # Try Rust finder with all strategies
        xse_log_path = str(self.xse_file) if self.xse_file else None

        def find_path() -> str:
            return self._rust_finder.find_game_path(cached_path=str(cached_path) if cached_path else None, xse_log_path=xse_log_path)

        try:
            path_str = await loop.run_in_executor(None, find_path)
        except FileNotFoundError:
            logger.debug("Rust finder could not find game path, prompting user")
        else:
            game_path = Path(path_str)
            await self._save_game_path_async(game_path)
            return

        # Fall back to user input
        game_path = self._get_path_from_user_gui() if GlobalRegistry.is_gui_mode() else self._get_path_from_user_console()
        await self._save_game_path_async(game_path)


def game_path_find() -> None:
    """Find and verify the game path.

    Logs the initiation of the game path check for debugging purposes.

    Raises:
        Any exceptions raised by the `GamePathFinder` methods will propagate.

    """
    logger.debug("- - - INITIATED GAME PATH CHECK")
    finder = GamePathFinder()
    finder.find_game_path()


async def game_path_find_async() -> None:
    """Asynchronously verify and determine the game path.

    This async function should be used in async contexts instead of game_path_find().
    """
    logger.debug("- - - INITIATED GAME PATH CHECK (ASYNC)")
    finder = await GamePathFinder.create_async()
    await finder.find_game_path_async()


def game_generate_paths() -> None:
    """Generate game-specific paths and configurations using YAML settings.

    Raises:
        TypeError: If the game path or XSE acronym base is not of type `str`.
        ValueError: If the game version is unsupported or invalid.

    """
    from ClassicLib.Utils.version_utils import read_game_exe_version

    logger.debug("- - - INITIATED GAME PATH GENERATION")

    game_path: str | None = yaml_settings(str, YAML.Game_Local, "Game_Info.Root_Folder_Game")
    # Get base XSE acronym from Version Registry (always non-VR, used for folder paths).
    # XSE acronym is identical across FO4_OG / FO4_NG / FO4_AE ("F4SE");
    # FO4_OG is used as the canonical non-VR source so the plugins folder path is consistent.
    registry = get_version_registry()
    base_version_info = registry.get_by_id("FO4_OG")
    xse_acronym_base: str | None = base_version_info.xse.acronym if base_version_info and base_version_info.xse else None
    if not (isinstance(game_path, str) and game_path.strip() and isinstance(xse_acronym_base, str)):
        raise TypeError

    yaml_settings(str, YAML.Game_Local, "Game_Info.Game_Folder_Data", rf"{game_path}\Data")
    yaml_settings(str, YAML.Game_Local, "Game_Info.Game_Folder_Scripts", rf"{game_path}\Data\Scripts")
    yaml_settings(str, YAML.Game_Local, "Game_Info.Game_Folder_Plugins", rf"{game_path}\Data\{xse_acronym_base}\Plugins")
    yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_SteamINI", rf"{game_path}\steam_api.ini")
    yaml_settings(
        str,
        YAML.Game_Local,
        "Game_Info.Game_File_EXE",
        rf"{game_path}\{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe",
    )
    game_version: Version = read_game_exe_version(Path(cast("str", yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_EXE"))))
    match GlobalRegistry.get_game():
        case "Fallout4":
            is_vr = GlobalRegistry.is_vr_version()
            registry = get_version_registry()

            if game_version == NULL_VERSION:
                default_id = "FO4_VR" if is_vr else "FO4_OG"
                default_info = registry.get_by_id(default_id)
                if default_info and default_info.address_library:
                    yaml_settings(
                        str,
                        YAML.Game_Local,
                        "Game_Info.Game_File_AddressLib",
                        rf"{game_path}\Data\{xse_acronym_base}\plugins\{default_info.address_library.filename}",
                    )
                return

            match_result = registry.match_version(game_version, "Fallout4", is_vr=is_vr)

            if match_result.should_warn:
                _log_version_warning(game_version, match_result.message)

            if match_result.version_info and match_result.version_info.address_library:
                yaml_settings(
                    str,
                    YAML.Game_Local,
                    "Game_Info.Game_File_AddressLib",
                    rf"{game_path}\Data\{xse_acronym_base}\plugins\{match_result.version_info.address_library.filename}",
                )
        case _:
            raise ValueError(f"Unsupported game: {GlobalRegistry.get_game()!r}. Only Fallout4 is supported.")


async def game_generate_paths_async() -> None:
    """Asynchronously generate game-specific paths and configurations.

    This async version should be used in async contexts instead of game_generate_paths().

    Raises:
        TypeError: If the game path or XSE acronym base is not of type `str`.
        ValueError: If the game version is unsupported or invalid.

    """
    from ClassicLib.io.yaml import yaml_settings_async
    from ClassicLib.Utils.version_utils import read_game_exe_version

    logger.debug("- - - INITIATED GAME PATH GENERATION (ASYNC)")

    game_path: str | None = await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Root_Folder_Game")
    # Get base XSE acronym from Version Registry (always non-VR, used for folder paths).
    # XSE acronym is identical across FO4_OG / FO4_NG / FO4_AE ("F4SE");
    # FO4_OG is used as the canonical non-VR source so the plugins folder path is consistent.
    registry = get_version_registry()
    base_version_info = registry.get_by_id("FO4_OG")
    xse_acronym_base: str | None = base_version_info.xse.acronym if base_version_info and base_version_info.xse else None
    if not (isinstance(game_path, str) and game_path.strip() and isinstance(xse_acronym_base, str)):
        raise TypeError

    await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_Folder_Data", rf"{game_path}\Data")
    await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_Folder_Scripts", rf"{game_path}\Data\Scripts")
    await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_Folder_Plugins", rf"{game_path}\Data\{xse_acronym_base}\Plugins")
    await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_File_SteamINI", rf"{game_path}\steam_api.ini")
    await yaml_settings_async(
        str,
        YAML.Game_Local,
        "Game_Info.Game_File_EXE",
        rf"{game_path}\{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe",
    )
    game_version: Version = read_game_exe_version(
        Path(cast("str", await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_File_EXE")))
    )
    match GlobalRegistry.get_game():
        case "Fallout4":
            is_vr = GlobalRegistry.is_vr_version()
            registry = get_version_registry()

            if game_version == NULL_VERSION:
                default_id = "FO4_VR" if is_vr else "FO4_OG"
                default_info = registry.get_by_id(default_id)
                if default_info and default_info.address_library:
                    await yaml_settings_async(
                        str,
                        YAML.Game_Local,
                        "Game_Info.Game_File_AddressLib",
                        rf"{game_path}\Data\{xse_acronym_base}\plugins\{default_info.address_library.filename}",
                    )
                return

            match_result = registry.match_version(game_version, "Fallout4", is_vr=is_vr)

            if match_result.should_warn:
                _log_version_warning(game_version, match_result.message)

            if match_result.version_info and match_result.version_info.address_library:
                await yaml_settings_async(
                    str,
                    YAML.Game_Local,
                    "Game_Info.Game_File_AddressLib",
                    rf"{game_path}\Data\{xse_acronym_base}\plugins\{match_result.version_info.address_library.filename}",
                )
        case _:
            raise ValueError(f"Unsupported game: {GlobalRegistry.get_game()!r}. Only Fallout4 is supported.")

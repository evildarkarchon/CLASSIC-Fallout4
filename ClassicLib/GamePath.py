"""
Handles operations related to resolving and validating game installation paths, including system
registry checks, user interactions, and configuration updates.

The module ensures the correct game path is determined based on platform-specific logic, registry
lookups, and user-provided input. Once validated, the paths are registered and stored in YAML
settings.

**Performance**: Core path-finding operations (registry queries, XSE log parsing) automatically use
Rust acceleration when available, providing 10-50x performance improvements.

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

# Import factory for Rust acceleration
from ClassicLib.integration.factory import get_path_operations

# Get Rust module if available, None otherwise
classic_path = get_path_operations()
_HAS_RUST_PATH = classic_path is not None

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

    **Performance**: Uses Rust acceleration when available for 10-50x faster registry queries on Windows.

    Args:
        exe_name: The name of the game's executable file to validate its presence in the resolved path.

    Returns:
        A Path object representing the game's valid installation directory if found and validated,
        otherwise None.
    """
    # Try Rust acceleration first if available
    if _HAS_RUST_PATH and platform.system() == "Windows":
        try:
            finder = classic_path.GamePathFinder(  # pyright: ignore[reportPossiblyUnboundVariable]
                exe_name,
                None,  # xse_loader not needed for registry lookup
                GlobalRegistry.get_game(),
                bool(GlobalRegistry.get_vr())
            )
            # Try to find via registry (cached_path=None, xse_log_path=None)
            path_str = finder.find_game_path(cached_path=None, xse_log_path=None)
        except FileNotFoundError:
            logger.debug("Rust registry lookup failed, falling back to Python implementation")
        except (ValueError, OSError, RuntimeError) as e:
            logger.debug(f"Rust registry lookup error: {e}, falling back to Python implementation")
        else:
            game_path = Path(path_str)
            from ClassicLib.ResourceLoader import ResourceLoader
            ResourceLoader.save_path_to_cache(game_path, "GamePath")
            GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)
            return game_path

    # Python fallback implementation
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
    """
    Handles the discovery and configuration of the game path.

    This class is responsible for locating the installation directory of
    a game. It utilizes various methods, including cached paths, system
    registry (on Windows), configuration files, and user inputs. The
    class ensures that the determined game path is valid before saving it
    to settings.

    Attributes:
        exe_name (str): Name of the game executable file, usually determined
            dynamically based on the game and virtual reality configuration.
        xse_file (str): Path to the XSE (game log or configuration) file, loaded
            from YAML settings.
        xse_acronym (str): Acronym used in the XSE file configuration, loaded
            from YAML settings.
        xse_acronym_base (str): Base acronym for XSE, loaded from a global YAML
            settings key.
        game_name (str): Root name of the game, loaded from YAML settings.
    """

    def __init__(self) -> None:
        """
        Represents a configuration class that initializes and manages key YAML settings and game-related identifiers.

        Note: This constructor uses synchronous yaml_settings(). For async contexts,
        use the async factory method create_async() instead.

        Raises:
            TypeError: If any of the YAML settings such as `xse_acronym`, `xse_acronym_base`, or
                `game_name` are not strings.
            RuntimeError: If called from within an async context.
        """
        self.exe_name = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
        self.xse_file = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_XSE")
        self.xse_acronym = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
        self.xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
        self.game_name = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Root_Name")

        if not all(isinstance(val, str) for val in [self.xse_acronym, self.xse_acronym_base, self.game_name]):
            raise TypeError("Required YAML settings are not strings")

    @classmethod
    async def create_async(cls) -> "GamePathFinder":
        """
        Async factory method to create a GamePathFinder instance.

        This method should be used in async contexts instead of the synchronous __init__.
        It uses yaml_settings_async() to load configuration without blocking.

        Returns:
            GamePathFinder: A fully initialized instance with YAML settings loaded.

        Raises:
            TypeError: If any of the YAML settings are not strings.

        Example:
            >>> finder = await GamePathFinder.create_async()
            >>> finder.find_game_path()
        """
        from ClassicLib.YamlSettingsCache import yaml_settings_async

        # Create instance without calling __init__
        instance = cls.__new__(cls)

        # Initialize attributes using async yaml operations
        instance.exe_name = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
        instance.xse_file = await yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_XSE")
        instance.xse_acronym = await yaml_settings_async(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
        instance.xse_acronym_base = await yaml_settings_async(str, YAML.Game, "Game_Info.XSE_Acronym")
        instance.game_name = await yaml_settings_async(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Root_Name")

        if not all(isinstance(val, str) for val in [instance.xse_acronym, instance.xse_acronym_base, instance.game_name]):
            raise TypeError("Required YAML settings are not strings")

        return instance

    def _validate_xse_file(self) -> bool:
        """Validate XSE file existence and accessibility.

        Returns:
            bool: True if XSE file exists and is accessible, False otherwise.
        """
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
        """
        Reports an error related to the XSE log file based on the provided error message. The error is logged
        with details, guiding the user toward resolving the issue depending on the type of error.

        Args:
            error_msg (str): The error message indicating the reason for the encountered issue.
        """
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
        """
        Parses a log file to extract a directory path.

        This method processes a log file associated with the `xse_file` attribute, searches
        for a line starting with the string "plugin directory", and extracts a directory
        path based on specific formatting rules. If no such line is found, the method returns `None`.

        **Performance**: Uses Rust acceleration when available for 10-50x faster parsing.

        Returns:
            Path | None: Extracted directory path if found; otherwise, None.
        """
        # Use Rust acceleration if available
        if _HAS_RUST_PATH:
            try:
                path_str = classic_path.GamePathFinder.parse_xse_log(str(self.xse_file))  # pyright: ignore[reportPossiblyUnboundVariable]
                return Path(path_str)
            except (FileNotFoundError, ValueError) as e:
                logger.debug(f"Rust XSE log parsing failed: {e}")
                return None

        # Python fallback
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
        """
        Validates the provided game path to ensure it meets the necessary criteria.

        This function checks if the path is accessible, whether it is an existing directory,
        and if the expected executable file is present within the directory.

        Args:
            game_path (Path): The path to the game directory that needs to be validated.

        Returns:
            bool: True if the game path is valid and meets all required conditions, False otherwise.
        """
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

    async def _save_game_path_async(self, game_path: Path) -> None:  # noqa: PLR6301
        """
        Asynchronously saves the game path to cache locations and registers it.

        Args:
            game_path (Path): The path to the game directory to be saved.
        """
        from ClassicLib.ResourceLoader import ResourceLoader

        # Save to all cache locations (cache.yaml, Local.yaml)
        await ResourceLoader.save_path_to_cache_async(game_path, "GamePath")
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)

    def _save_game_path(self, game_path: Path) -> None:  # noqa: PLR6301
        """
        Saves the provided game path to multiple cache locations and registers
        it within the global registry.

        Note: This is the sync version. For async contexts, use _save_game_path_async().

        Args:
            game_path (Path): The path to the game directory to be saved.
        """
        from ClassicLib.ResourceLoader import ResourceLoader

        # Save to all cache locations (cache.yaml, Local.yaml, and suggest env var)
        ResourceLoader.save_path_to_cache(game_path, "GamePath")
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)

    def _get_path_from_user_gui(self) -> Path:  # noqa: PLR6301
        """
        Retrieves a file path from the user via a graphical user interface (GUI).

        This method prompts the user with a dialog to select a file path. If the user
        cancels the selection, the application will safely handle it by raising a
        RuntimeError. The retrieved file path is returned.

        Raises:
            RuntimeError: If the user cancels the file path selection dialog.

        Returns:
            Path: The file path selected by the user.
        """
        # This will return a valid path or exit the application if cancelled
        result = show_game_path_dialog_static()
        if result is None:
            # Should not reach here as the dialog exits on cancel, but handle it safely
            raise RuntimeError("Game path selection was cancelled")
        return result

    def _get_path_from_user_console(self) -> Path:
        """
        Retrieves and validates a directory path for a game installation from the user via console input.

        This method prompts the user to provide the full directory path where the game is located.
        The entered path is validated for readability, and the existence of the game's executable file
        is confirmed. If the validation fails or the executable file is not found, the user is prompted
        to re-enter the path until a valid path is provided.

        Returns:
            Path: The validated directory path provided by the user.
        """
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

    async def find_game_path_async(self) -> None:
        """
        Asynchronously finds and sets the game installation path.

        This is the async version that should be used from async contexts (CLI, async workers).
        It uses yaml_settings_async() and _save_game_path_async() to properly handle async operations.

        Raises:
            ValueError: If the user-provided path or XSE-derived path is invalid.
        """
        # First, check if we have a cached path (for uvx compatibility)
        from ClassicLib.ResourceLoader import ResourceLoader
        from ClassicLib.YamlSettingsCache import yaml_settings_async

        cached_path = await ResourceLoader.get_cached_game_path_async()
        if cached_path and cached_path.joinpath(self.exe_name).is_file():
            logger.debug(f"Using cached game path: {cached_path}")
            GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, cached_path)
            # Still save to Local.yaml for consistency
            await yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(cached_path))
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
            await self._save_game_path_async(game_path)
            return

        # Fall back to user input
        game_path = self._get_path_from_user_gui() if GlobalRegistry.is_gui_mode() else self._get_path_from_user_console()

        await self._save_game_path_async(game_path)

    def find_game_path(self) -> None:
        """
        Finds and sets the game installation path (sync version).

        This method determines the path to the game installation by using various approaches in a
        hierarchical manner. It first checks if a cached path is available. If not, on Windows systems,
        it attempts to retrieve the path from the registry. If these methods fail, it validates the XSE
        file and tries to extract the path from the XSE log. As a last resort, it prompts the user
        for the path either via a GUI or the console, depending on the mode the application runs in.

        Note: For async contexts (CLI, async workers), use find_game_path_async() instead.

        Raises:
            ValueError: If the user-provided path or XSE-derived path is invalid.

        """
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
        game_path = self._get_path_from_user_gui() if GlobalRegistry.is_gui_mode() else self._get_path_from_user_console()

        self._save_game_path(game_path)


def game_path_find() -> None:
    """
    Find and verify the game path by initializing and utilizing the GamePathFinder
    class. This function is responsible for initiating the game path check process
    and ensuring that the proper game path is found.

    Logs the initiation of the game path check for debugging purposes.

    Raises:
        Any exceptions raised by the `GamePathFinder` methods will propagate and need
        to be handled by the caller. Refer to the `GamePathFinder` class documentation
        for details on the exceptions.
    """
    logger.debug("- - - INITIATED GAME PATH CHECK")

    finder = GamePathFinder()
    finder.find_game_path()


async def game_path_find_async() -> None:
    """
    Asynchronously verifies and determines the game path.

    This async function creates a GamePathFinder instance using async initialization
    and initiates the process of finding the game path. It should be used in async
    contexts (like CLI async code or async workers) instead of the synchronous
    game_path_find().

    Example:
        >>> await game_path_find_async()
    """
    logger.debug("- - - INITIATED GAME PATH CHECK (ASYNC)")

    finder = await GamePathFinder.create_async()
    await finder.find_game_path_async()


def game_generate_paths() -> None:
    """
    Generates game-specific paths and configurations using YAML settings and global registry data.

    This function reads and verifies necessary game paths and settings and configures them based on
    the game version and type (e.g., VR or non-VR). It ensures that certain properties like file paths
    and game configurations are correctly set based on predefined constants and the game's version
    compatibility. If any invalid or unsupported values are encountered, appropriate exceptions are
    raised.

    Raises:
        TypeError: If the game path or XSE acronym base is not of type `str`.
        ValueError: If the game version is unsupported or invalid.
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


async def game_generate_paths_async() -> None:
    """
    Asynchronously generates game-specific paths and configurations using YAML settings.

    This async version should be used in async contexts (like CLI async code or async workers)
    instead of the synchronous game_generate_paths(). It uses yaml_settings_async() to avoid
    blocking the event loop.

    Raises:
        TypeError: If the game path or XSE acronym base is not of type `str`.
        ValueError: If the game version is unsupported or invalid.

    Example:
        >>> await game_generate_paths_async()
    """
    from ClassicLib.YamlSettingsCache import yaml_settings_async

    logger.debug("- - - INITIATED GAME PATH GENERATION (ASYNC)")

    game_path: str | None = await yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
    await yaml_settings_async(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_acronym_base: str | None = await yaml_settings_async(str, YAML.Game, "Game_Info.XSE_Acronym")
    if not (isinstance(game_path, str) and isinstance(xse_acronym_base, str)):
        raise TypeError

    await yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Data", rf"{game_path}\Data")
    await yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Scripts", rf"{game_path}\Data\Scripts")
    await yaml_settings_async(
        str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Plugins", rf"{game_path}\Data\{xse_acronym_base}\Plugins"
    )
    await yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_SteamINI", rf"{game_path}\steam_api.ini")
    await yaml_settings_async(
        str,
        YAML.Game_Local,
        f"Game{GlobalRegistry.get_vr()}_Info.Game_File_EXE",
        rf"{game_path}\{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe",
    )
    game_version: Version = get_game_version(
        Path(cast("str", await yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_EXE")))
    )
    match GlobalRegistry.get_game():
        case "Fallout4" if not GlobalRegistry.get_vr():
            if (not game_version or game_version not in FO4_VERSIONS) and game_version != NULL_VERSION:
                raise ValueError("Unsupported or invalid game version")
            if game_version in {OG_VERSION, NULL_VERSION}:
                await yaml_settings_async(
                    str,
                    YAML.Game_Local,
                    "Game_Info.Game_File_AddressLib",
                    rf"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-163-0.bin",
                )
            elif game_version == NG_VERSION:
                await yaml_settings_async(
                    str,
                    YAML.Game_Local,
                    "Game_Info.Game_File_AddressLib",
                    rf"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-984-0.bin",
                )
        case "Fallout4" if GlobalRegistry.get_vr():
            await yaml_settings_async(
                str,
                YAML.Game_Local,
                "GameVR_Info.Game_File_AddressLib",
                rf"{game_path}\Data\{xse_acronym_base}\plugins\version-1-2-72-0.csv",
            )

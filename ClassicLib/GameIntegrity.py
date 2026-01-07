"""GameIntegrityChecker module provides tools to validate the integrity and proper installation
of a game. This includes ensuring that the executable files are up to date and verifying
that the installation complies with recommended practices.
"""

from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.Utils.file_utils import calculate_file_hash


class GameIntegrityChecker:
    """GameIntegrityChecker is a utility class for validating the integrity and installation
    configuration of a game.

    It ensures the game executable and its version are up-to-date and checks that the game
    is installed in a recommended location. This class provides detailed messages about the
    results of its checks to aid users in resolving potential issues.

    Attributes:
        _config (dict[str, str | None]): Stores configuration details such as paths to the
            game executable, expected hash values, and location information.

    """

    def __init__(self) -> None:
        """Represent the initialization method for the class.

        Initializes the class attributes to their default values. This method sets up
        internal configuration storage.
        """
        self._config: dict[str, str | None] = {}

    def load_configuration(self) -> None:
        """Load game configuration from YAML settings and VersionRegistry.

        Loads settings including:
        - Steam INI path
        - Valid executable hashes from VersionRegistry
        - Game executable path
        - Root name and warning messages

        Raises:
            TypeError: If any of the settings loaded from the configuration
                files is not of the expected type.

        """
        from ClassicLib.VersionRegistry import get_version_registry
        from ClassicLib.YamlSettings import yaml_settings

        vr_suffix: str = GlobalRegistry.get_vr()
        is_vr: bool = vr_suffix == "VR"

        # Get valid exe hashes from VersionRegistry
        registry = get_version_registry()
        valid_exe_hashes: set[str] = registry.get_all_exe_hashes("Fallout4", is_vr)

        # Load settings from YAML
        self._config = {
            "steam_ini_path": yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_SteamINI"),
            "valid_exe_hashes": valid_exe_hashes,
            "game_exe_path": yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_EXE"),
            "root_name": yaml_settings(str, YAML.Game, f"Game{vr_suffix}_Info.Main_Root_Name"),
            "root_warn": yaml_settings(str, YAML.Main, "Warnings_GAME.warn_root_path"),
        }

        # Validate string settings types (valid_exe_hashes is a set, not a string)
        for key, value in self._config.items():
            if key == "valid_exe_hashes":
                continue  # Skip set validation
            if value is not None and not isinstance(value, str):
                raise TypeError(f"Expected string for {key}, got {type(value)}")

        logger.debug("Loaded game integrity configuration")

    async def load_configuration_async(self) -> None:
        """Asynchronously loads game-specific configuration settings from YAML files.

        This is the async version that should be used from async contexts.
        It loads various settings needed for integrity checks asynchronously.

        Raises:
            TypeError: If any of the loaded settings are not strings.

        """
        from ClassicLib.VersionRegistry import get_version_registry
        from ClassicLib.YamlSettings import yaml_settings_async

        vr_suffix: str = GlobalRegistry.get_vr()
        is_vr: bool = vr_suffix == "VR"

        # Get valid exe hashes from VersionRegistry
        registry = get_version_registry()
        valid_exe_hashes: set[str] = registry.get_all_exe_hashes("Fallout4", is_vr)

        # Load settings from YAML asynchronously
        self._config = {
            "steam_ini_path": await yaml_settings_async(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_SteamINI"),
            "valid_exe_hashes": valid_exe_hashes,
            "game_exe_path": await yaml_settings_async(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_EXE"),
            "root_name": await yaml_settings_async(str, YAML.Game, f"Game{vr_suffix}_Info.Main_Root_Name"),
            "root_warn": await yaml_settings_async(str, YAML.Main, "Warnings_GAME.warn_root_path"),
        }

        # Validate string settings types (valid_exe_hashes is a set, not a string)
        for key, value in self._config.items():
            if key == "valid_exe_hashes":
                continue  # Skip set validation
            if value is not None and not isinstance(value, str):
                raise TypeError(f"Expected string for {key}, got {type(value)}")

        logger.debug("Loaded game integrity configuration (async)")

    def check_executable_version(self) -> tuple[bool, str]:
        """Check if game executable is up to date.

        Returns:
            Tuple of (is_valid, message) where is_valid indicates if the
            executable version is current and message provides details.

        """
        exe_path = Path(self._config["game_exe_path"]) if self._config["game_exe_path"] else None

        if not exe_path or not exe_path.is_file():
            return False, "Game executable not found"

        # Calculate local executable hash
        local_hash: str = calculate_file_hash(exe_path)

        # Check if hash matches known versions from VersionRegistry
        valid_hashes: set[str] = self._config["valid_exe_hashes"]
        is_valid_version: bool = local_hash in valid_hashes

        # Check for Steam INI (indicates outdated installation)
        steam_ini_path = Path(self._config["steam_ini_path"]) if self._config["steam_ini_path"] else None
        steam_ini_exists = steam_ini_path and steam_ini_path.exists()

        if is_valid_version and not steam_ini_exists:
            message = f"✔️ You have the latest version of {self._config['root_name']}! \n-----\n"
            return True, message
        icon = "\U0001f480" if steam_ini_exists else "❌"
        message = f"{icon} CAUTION : YOUR {self._config['root_name']} GAME / EXE VERSION IS OUT OF DATE \n-----\n"
        return False, message

    def check_installation_location(self) -> tuple[bool, str]:
        """Verify game is installed in recommended location.

        Checks if the game is installed outside of Program Files,
        which is recommended to avoid permission issues.

        Returns:
            Tuple of (is_valid, message) where is_valid indicates if the
            installation location is recommended and message provides details.

        """
        exe_path = Path(self._config["game_exe_path"]) if self._config["game_exe_path"] else None

        if not exe_path or not exe_path.is_file():
            return False, ""

        if "Program Files" not in str(exe_path):
            message = f"✔️ Your {self._config['root_name']} game files are installed outside of the Program Files folder! \n-----\n"
            return True, message
        message = self._config["root_warn"] or ""
        return False, message

    async def run_full_check_async(self) -> str:
        """Asynchronously run all integrity checks and return combined results.

        This is the async version that should be used from async contexts.
        Performs the following checks:
        1. Game executable version validation
        2. Installation location verification

        Returns:
            A detailed message string indicating the integrity status
            of all game files and installation.

        """
        logger.debug("- - - INITIATED GAME INTEGRITY CHECK (ASYNC)")

        # Ensure configuration is loaded
        if not self._config:
            await self.load_configuration_async()

        messages: list[str] = []

        # Check game executable version
        _, version_message = self.check_executable_version()
        if version_message:
            messages.append(version_message)

        # Check installation location
        _, location_message = self.check_installation_location()
        if location_message:
            messages.append(location_message)

        return "".join(messages)

    def run_full_check(self) -> str:
        """Run all integrity checks and return combined results (sync version).

        Performs the following checks:
        1. Game executable version validation
        2. Installation location verification

        Note: For async contexts, use run_full_check_async() instead.

        Returns:
            A detailed message string indicating the integrity status
            of all game files and installation.

        """
        logger.debug("- - - INITIATED GAME INTEGRITY CHECK")

        # Ensure configuration is loaded
        if not self._config:
            self.load_configuration()

        messages: list[str] = []

        # Check game executable version
        _, version_message = self.check_executable_version()
        if version_message:
            messages.append(version_message)

        # Check installation location
        _, location_message = self.check_installation_location()
        if location_message:
            messages.append(location_message)

        return "".join(messages)

"""Game integrity checking module for validating game installation and files."""

from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.Util import calculate_file_hash


class GameIntegrityChecker:
    """Validates game installation and file integrity."""

    def __init__(self) -> None:
        """Initialize the GameIntegrityChecker."""
        self._config: dict[str, str | None] = {}

    def load_configuration(self) -> None:
        """
        Load game configuration from YAML settings.

        Loads settings including:
        - Steam INI path
        - Executable hash values (old and new versions)
        - Game executable path
        - Root name and warning messages

        Raises:
            TypeError: If any of the settings loaded from the configuration
                files is not of the expected type.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        vr_suffix: str = GlobalRegistry.get_vr()

        # Load settings from YAML
        self._config = {
            "steam_ini_path": yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_SteamINI"),
            "exe_hash_old": yaml_settings(str, YAML.Game, "Game_Info.EXE_HashedOLD"),
            "exe_hash_new": yaml_settings(str, YAML.Game, "Game_Info.EXE_HashedNEW"),
            "game_exe_path": yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Game_File_EXE"),
            "root_name": yaml_settings(str, YAML.Game, f"Game{vr_suffix}_Info.Main_Root_Name"),
            "root_warn": yaml_settings(str, YAML.Main, "Warnings_GAME.warn_root_path"),
        }

        # Validate settings types
        for key, value in self._config.items():
            if value is not None and not isinstance(value, str):
                raise TypeError(f"Expected string for {key}, got {type(value)}")

        logger.debug("Loaded game integrity configuration")

    def check_executable_version(self) -> tuple[bool, str]:
        """
        Check if game executable is up to date.

        Returns:
            Tuple of (is_valid, message) where is_valid indicates if the
            executable version is current and message provides details.
        """
        exe_path = Path(self._config["game_exe_path"]) if self._config["game_exe_path"] else None

        if not exe_path or not exe_path.is_file():
            return False, "Game executable not found"

        # Calculate local executable hash
        local_hash: str = calculate_file_hash(exe_path)

        # Check if hash matches known versions
        is_valid_version: bool = local_hash in (self._config["exe_hash_old"], self._config["exe_hash_new"])

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
        """
        Verify game is installed in recommended location.

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
        message = self._config["root_warn"] if self._config["root_warn"] else ""
        return False, message

    def run_full_check(self) -> str:
        """
        Run all integrity checks and return combined results.

        Performs the following checks:
        1. Game executable version validation
        2. Installation location verification

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

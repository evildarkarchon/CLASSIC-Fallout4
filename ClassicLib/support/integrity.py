"""GameIntegrityChecker module provides tools to validate the integrity and proper installation
of a game. This includes ensuring that the executable files are up to date and verifying
that the installation complies with recommended practices.

Delegates to Rust classic_scangame.GameIntegrityChecker for SHA-256 hashing and
location validation (20-40x faster). Python layer handles YAML config loading and
VersionRegistry integration.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry

if TYPE_CHECKING:
    import classic_scangame


class GameIntegrityChecker:
    """GameIntegrityChecker is a utility class for validating the integrity and installation
    configuration of a game.

    It ensures the game executable and its version are up-to-date and checks that the game
    is installed in a recommended location. This class provides detailed messages about the
    results of its checks to aid users in resolving potential issues.

    The actual checking logic (SHA-256 hashing, Program Files detection) is delegated to
    the Rust classic_scangame.GameIntegrityChecker for performance.

    Attributes:
        _config (dict[str, str | None]): Stores configuration details such as paths to the
            game executable and location information.
        _valid_exe_hashes (set[str]): Set of valid executable hash strings from VersionRegistry.

    """

    def __init__(self) -> None:
        """Represent the initialization method for the class.

        Initializes the class attributes to their default values. This method sets up
        internal configuration storage.
        """
        self._config: dict[str, str | None] = {}
        self._valid_exe_hashes: set[str] = set()

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
        from ClassicLib.io.yaml import yaml_settings
        from ClassicLib.support.versions import get_version_registry

        is_vr: bool = GlobalRegistry.is_vr_version()

        # Get valid exe hashes from VersionRegistry
        registry = get_version_registry()
        self._valid_exe_hashes = registry.get_all_exe_hashes("Fallout4", is_vr)

        # Load settings from YAML
        self._config = {
            "steam_ini_path": yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_SteamINI"),
            "game_exe_path": yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_EXE"),
            "root_name": yaml_settings(str, YAML.Game, "Game_Info.Main_Root_Name"),
            "root_warn": yaml_settings(str, YAML.Main, "Warnings_GAME.warn_root_path"),
        }

        # Validate string settings types
        for key, value in self._config.items():
            if value is not None and not isinstance(value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise TypeError(f"Expected string for {key}, got {type(value)}")

        logger.debug("Loaded game integrity configuration")

    async def load_configuration_async(self) -> None:
        """Asynchronously loads game-specific configuration settings from YAML files.

        This is the async version that should be used from async contexts.
        It loads various settings needed for integrity checks asynchronously.

        Raises:
            TypeError: If any of the loaded settings are not strings.

        """
        from ClassicLib.io.yaml import yaml_settings_async
        from ClassicLib.support.versions import get_version_registry

        is_vr: bool = GlobalRegistry.is_vr_version()

        # Get valid exe hashes from VersionRegistry
        registry = get_version_registry()
        self._valid_exe_hashes = registry.get_all_exe_hashes("Fallout4", is_vr)

        # Load settings from YAML asynchronously
        self._config = {
            "steam_ini_path": await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_File_SteamINI"),
            "game_exe_path": await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_File_EXE"),
            "root_name": await yaml_settings_async(str, YAML.Game, "Game_Info.Main_Root_Name"),
            "root_warn": await yaml_settings_async(str, YAML.Main, "Warnings_GAME.warn_root_path"),
        }

        # Validate string settings types
        for key, value in self._config.items():
            if value is not None and not isinstance(value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise TypeError(f"Expected string for {key}, got {type(value)}")

        logger.debug("Loaded game integrity configuration (async)")

    def _build_rust_checker(self) -> classic_scangame.GameIntegrityChecker:
        """Build a Rust GameIntegrityChecker from loaded config.

        Returns:
            A configured classic_scangame.GameIntegrityChecker instance.

        Raises:
            RuntimeError: If configuration has not been loaded.

        """
        import classic_scangame

        exe_path_str = self._config.get("game_exe_path")
        if not exe_path_str:
            raise RuntimeError("Game executable path not configured")

        root_name = self._config.get("root_name") or "Fallout 4"

        config = classic_scangame.IntegrityConfig(
            Path(exe_path_str),
            list(self._valid_exe_hashes),
            root_name,
        )

        # Set optional fields (builder pattern, mutates config in-place)
        steam_ini_str = self._config.get("steam_ini_path")
        if steam_ini_str:
            config.with_steam_ini(Path(steam_ini_str))

        root_warn = self._config.get("root_warn")
        if root_warn:
            config.with_root_warn(root_warn)

        return classic_scangame.GameIntegrityChecker(config)

    def check_executable_version(self) -> tuple[bool, str]:
        """Check if game executable is up to date.

        Delegates SHA-256 hashing and comparison to Rust for 20-40x speedup.

        Returns:
            Tuple of (is_valid, message) where is_valid indicates if the
            executable version is current and message provides details.

        """
        try:
            checker = self._build_rust_checker()
            result = checker.check_executable_version()
        except (FileNotFoundError, OSError, RuntimeError):
            return False, "Game executable not found"
        else:
            return result.is_valid, result.message

    def check_installation_location(self) -> tuple[bool, str]:
        """Verify game is installed in recommended location.

        Checks if the game is installed outside of Program Files,
        which is recommended to avoid permission issues.

        Returns:
            Tuple of (is_valid, message) where is_valid indicates if the
            installation location is recommended and message provides details.

        """
        exe_path = Path(self._config["game_exe_path"]) if self._config.get("game_exe_path") else None

        if not exe_path or not exe_path.is_file():
            return False, ""

        if "Program Files" not in str(exe_path):
            message = (
                f"\u2714\ufe0f Your {self._config['root_name']} game files are installed outside of the Program Files folder! \n-----\n"
            )
            return True, message
        message = self._config.get("root_warn") or ""
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

        try:
            checker = self._build_rust_checker()
            return checker.run_full_check()
        except (FileNotFoundError, OSError, RuntimeError) as e:
            logger.warning(f"Rust integrity check failed: {e}")
            return ""

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

        try:
            checker = self._build_rust_checker()
            return checker.run_full_check()
        except (FileNotFoundError, OSError, RuntimeError) as e:
            logger.warning(f"Rust integrity check failed: {e}")
            return ""

"""Setup coordination module that orchestrates application initialization and setup tasks."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ClassicLib import GlobalRegistry, MessageTarget, init_message_handler, msg_info, msg_success
from ClassicLib.BackupManager import BackupManager
from ClassicLib.Constants import YAML
from ClassicLib.DocsPath import docs_generate_paths, docs_path_find
from ClassicLib.DocumentsChecker import DocumentsChecker
from ClassicLib.FileGeneration import FileGenerator
from ClassicLib.GameIntegrity import GameIntegrityChecker
from ClassicLib.GamePath import game_generate_paths, game_path_find
from ClassicLib.Logger import logger
from ClassicLib.PathValidator import PathValidator
from ClassicLib.Util import configure_logging
from ClassicLib.XseCheck import xse_check_hashes, xse_check_integrity

if TYPE_CHECKING:
    from ClassicLib.YamlSettingsCache import YamlSettingsCache  # noqa: F401


class SetupCoordinator:
    """Coordinates application setup and initialization."""

    def __init__(self) -> None:
        """Initialize the SetupCoordinator with all required components."""
        self.file_generator = FileGenerator()
        self.integrity_checker = GameIntegrityChecker()
        self.backup_manager = BackupManager()
        self.docs_checker = DocumentsChecker()
        self.path_validator = PathValidator()

    def run_initial_setup(self) -> None:
        """
        Run complete initial setup sequence.

        This method:
        1. Configures logging
        2. Generates required configuration files
        3. Displays welcome messages
        4. Checks for game path and generates paths if needed
        5. Backs up game files if paths are already configured

        Raises:
            TypeError: If the classic version or game name settings are not of type str.
        """
        from ClassicLib.PerformanceMonitor import TimedBlock
        from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings  # noqa: F401

        # Configure logging
        configure_logging(logger)

        # Generate required files
        with TimedBlock("File Generation", log_level="debug"):
            self.file_generator.generate_all_files()

        # Batch load version, game information, and game path
        with TimedBlock("Initial Settings Load", log_level="debug"):
            requests = [
                (str, YAML.Main, "CLASSIC_Info.version"),
                (str, YAML.Game, "Game_Info.Main_Root_Name"),
                (str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
            ]

            classic_ver, game_name, game_path = yaml_cache.batch_get_settings(requests)

        if not (isinstance(classic_ver, str) and isinstance(game_name, str)):
            raise TypeError("Classic version and game name must be strings")

        # Display welcome messages
        msg_info(
            f"Hello World! | Crash Log Auto Scanner & Setup Integrity Checker | {classic_ver} | {game_name}", target=MessageTarget.CLI_ONLY
        )
        msg_info("REMINDER: COMPATIBLE CRASH LOGS MUST START WITH 'crash-' AND MUST HAVE .log EXTENSION", target=MessageTarget.CLI_ONLY)
        msg_info("❓ PLEASE WAIT WHILE CLASSIC CHECKS YOUR SETTINGS AND GAME SETUP...", target=MessageTarget.CLI_ONLY)
        logger.debug(f"> > > STARTED {classic_ver}")

        if not game_path:
            # Generate paths if not configured
            docs_path_find(GlobalRegistry.is_gui_mode())
            docs_generate_paths()
            game_path_find()
            game_generate_paths()
        else:
            # Backup files if paths are configured
            self.backup_manager.run_backup()

        msg_success("ALL CLASSIC AND GAME SETTINGS CHECKS HAVE BEEN PERFORMED!", target=MessageTarget.CLI_ONLY)
        msg_info("YOU CAN NOW SCAN YOUR CRASH LOGS, GAME AND/OR MOD FILES", target=MessageTarget.CLI_ONLY)

    def generate_combined_results(self) -> str:
        """
        Generate combined results from all checks.

        This method executes a series of integrity checks including:
        - Game integrity validation
        - XSE integrity and hash verification
        - Document folder configuration checks
        - INI file validation

        Returns:
            A concatenated string containing the results of all executed checks.
        """
        game_name: str = GlobalRegistry.get_game()  # noqa: F841

        # Run all checks and collect results
        combined_return: list[str] = [self.integrity_checker.run_full_check(), xse_check_integrity(), xse_check_hashes()]

        # Document checks
        combined_return.extend(self.docs_checker.run_all_checks())

        return "".join(combined_return)

    def initialize_application(self, is_gui: bool = False, parent: Any = None) -> None:
        """
        Initialize application with all required components.

        This method sets up the application state, loads YAML settings cache,
        configures the message handler, and validates paths.

        Args:
            is_gui: Indicates whether the application should operate in GUI mode.
                If True, GUI-related resources are initialized.
            parent: Optional parent widget for GUI mode. This is passed to the
                message handler to ensure proper dialog parenting in GUI applications.
        """
        from ClassicLib.YamlSettingsCache import yaml_cache

        # Initialize message handler first
        # Note: init_message_handler will replace any existing handler
        # In GUI mode, the MainWindow should initialize its own handler with itself as parent
        init_message_handler(parent=parent, is_gui_mode=is_gui)

        # Get and configure YAML cache (already registered as singleton)
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, is_gui)

        # Prefetch all common settings at startup for better performance
        # This loads Main, Settings, and Game YAML files concurrently
        yaml_cache.prefetch_all_settings()

        # Batch load all application settings
        requests = [
            (bool, YAML.Settings, "CLASSIC_Settings.VR Mode"),
            (str, YAML.Settings, "CLASSIC_Settings.Managed Game"),
            (bool, YAML.Main, "CLASSIC_Info.is_prerelease")
        ]

        vr_mode, managed_game_setting, is_prerelease = yaml_cache.batch_get_settings(requests)

        # Register application settings
        # noinspection PyTypedDict
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "" if not vr_mode else "VR")

        game_value: str = managed_game_setting.replace(" ", "") if isinstance(managed_game_setting, str) else ""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, game_value)

        GlobalRegistry.register(GlobalRegistry.Keys.IS_PRERELEASE, is_prerelease)

        # Set local directory
        if getattr(sys, "frozen", False):
            GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(sys.executable).parent)
        else:
            GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(__file__).parent.parent)

        # Validate settings paths after initialization
        self.path_validator.validate_all_settings_paths()

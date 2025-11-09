"""
Initializes and coordinates various setup operations and integrity checks for the application.

This module provides a setup coordinator which encapsulates the logic for configuring logging,
generating configuration files, validating paths, performing game integrity checks, and running
application-level initiation sequences. It also manages YAML settings and ensures a consistent
application state across components of the system.
"""

import asyncio
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
from ClassicLib.ResourceLoader import ResourceLoader
from ClassicLib.Util import configure_logging
from ClassicLib.XseCheck import xse_check_hashes, xse_check_integrity

if TYPE_CHECKING:
    from ClassicLib.YamlSettingsCache import YamlSettingsCache  # noqa: F401


class SetupCoordinator:
    """Coordinates application setup and initialization."""

    def __init__(self) -> None:
        """
        Initializes the primary components required for the system's functionality.

        The constructor sets up instances of the necessary helper classes for
        file generation, integrity checking, backup management, document validation,
        and path validation.
        """
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
        # Use asyncio.run() during initialization (before Qt event loop)
        # AsyncBridge is ONLY for Qt worker threads, NOT for initialization
        with TimedBlock("Initial Settings Load", log_level="debug"):
            requests = [
                (str, YAML.Main, "CLASSIC_Info.version"),
                (str, YAML.Game, "Game_Info.Main_Root_Name"),
                (str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game"),
            ]

            classic_ver, game_name, game_path = asyncio.run(yaml_cache.batch_get_settings_async(requests))

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

        # Configure logging first - required for both CLI and GUI modes
        configure_logging(logger)

        # Initialize message handler
        # Note: init_message_handler will replace any existing handler
        # In GUI mode, the MainWindow should initialize its own handler with itself as parent
        init_message_handler(parent=parent, is_gui_mode=is_gui)

        # Get and configure YAML cache (already registered as singleton)
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, is_gui)

        # Ensure data files exist (extracts bundled resources if needed)
        ResourceLoader.ensure_data_files_exist()

        # NOTE: Prefetching removed from initialization
        # AsyncBridge should NOT be used during initialization (before Qt event loop starts)
        # Settings will load lazily on first access, which is fine for startup performance
        # If prefetching is needed, it should be done async with asyncio.run() or after Qt starts

        # Batch load all application settings
        # Use asyncio.run() during initialization (before Qt event loop)
        # AsyncBridge is ONLY for Qt worker threads, NOT for initialization
        requests = [
            (bool, YAML.Settings, "CLASSIC_Settings.VR Mode"),
            (str, YAML.Settings, "CLASSIC_Settings.Managed Game"),
            (bool, YAML.Main, "CLASSIC_Info.is_prerelease"),
        ]

        vr_mode, managed_game_setting, is_prerelease = asyncio.run(yaml_cache.batch_get_settings_async(requests))

        # Register application settings
        # noinspection PyTypedDict
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "" if not vr_mode else "VR")

        game_value: str = managed_game_setting.replace(" ", "") if isinstance(managed_game_setting, str) else ""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, game_value)

        GlobalRegistry.register(GlobalRegistry.Keys.IS_PRERELEASE, is_prerelease)

        # Set local directory only if not already set by entry point
        if not GlobalRegistry.is_registered(GlobalRegistry.Keys.LOCAL_DIR):
            if getattr(sys, "frozen", False):
                GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(sys.executable).parent)
            else:
                GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(__file__).parent.parent)

        # Validate settings paths after initialization
        self.path_validator.validate_all_settings_paths()

        # Log Rust acceleration status
        self._log_rust_acceleration_status()

    def _log_rust_acceleration_status(self) -> None:
        """
        Log the Rust acceleration status at application startup.

        This method checks which components are using Rust acceleration and logs
        a summary to help with debugging and performance monitoring.

        Logger calls always execute for diagnostics.
        MessageHandler calls only execute when Debug Messages setting is enabled.
        """
        from ClassicLib.YamlSettingsCache import classic_settings
        debug_enabled = bool(classic_settings(bool, "Debug Messages"))
        is_gui = GlobalRegistry.is_gui_mode()

        try:
            from ClassicLib.integration.status import get_rust_component_status
            status = get_rust_component_status()

            # Handle different acceleration states
            if status["disabled"]:
                self._log_disabled_status(debug_enabled, is_gui)
            elif status["active_count"] > 0:
                self._log_active_acceleration(status, debug_enabled, is_gui)
            else:
                self._log_no_acceleration(debug_enabled, is_gui)

            # Log version info if available
            if status.get("version"):
                logger.debug(f"   Rust Extension Version: {status['version']}")

        except ImportError:
            self._log_import_error(debug_enabled, is_gui)
        except Exception as e:  # noqa: BLE001 - Rust status check is optional, should not crash app
            self._log_status_check_error(e, debug_enabled, is_gui)

    @staticmethod
    def _log_disabled_status(debug_enabled: bool, is_gui: bool) -> None:
        """Log status when Rust acceleration is explicitly disabled."""
        status_msg = "⚠️  Rust acceleration disabled (CLASSIC_DISABLE_RUST is set)"
        if debug_enabled:
            SetupCoordinator._display_status_message(status_msg, "WARNING", is_gui)
        logger.warning("   To enable: unset CLASSIC_DISABLE_RUST environment variable")

    @staticmethod
    def _log_active_acceleration(status: dict[str, Any], debug_enabled: bool, is_gui: bool) -> None:
        """Log status when Rust acceleration is active."""
        status_msg = f"🚀 Rust Acceleration: {status['active_count']}/{status['total_count']} components active ({status['percentage']:.0f}%)"
        if debug_enabled:
            SetupCoordinator._display_status_message(status_msg, "INFO", is_gui)

        logger.info(f"Rust Acceleration Status: {status['acceleration_level']}")
        logger.info(f"   Active Components: {status['active_count']}/{status['total_count']} ({status['percentage']:.1f}%)")

        # Log detailed component info at debug level
        if status["performance_gains"]:
            logger.debug("   Active Rust Components:")
            for component, speedup in status["performance_gains"].items():
                logger.debug(f"      ✅ {component}: {speedup}")

    @staticmethod
    def _log_no_acceleration(debug_enabled: bool, is_gui: bool) -> None:
        """Log status when no Rust acceleration is available."""
        status_msg = "⚠️  No Rust acceleration - using Python fallback (slower performance)"
        if debug_enabled:
            SetupCoordinator._display_status_message(status_msg, "WARNING", is_gui)

        logger.warning("   To enable: Build and install the Rust extension:")
        logger.warning("      cd classic-rust")
        logger.warning("      maturin build --release --out dist")
        logger.warning("      uv pip install dist/classic-*.whl --force-reinstall")

    @staticmethod
    def _log_import_error(debug_enabled: bool, is_gui: bool) -> None:
        """Log status when Rust integration module is not available."""
        status_msg = "Using Python implementation (Rust extension not installed)"
        if debug_enabled:
            SetupCoordinator._display_status_message(status_msg, "INFO", is_gui)
        logger.debug("Rust integration module not available - using pure Python implementation")

    @staticmethod
    def _log_status_check_error(error: Exception, debug_enabled: bool, is_gui: bool) -> None:
        """Log error when Rust status check fails unexpectedly."""
        logger.debug(f"Error checking Rust acceleration status: {error}")
        if debug_enabled and not is_gui:
            print(f"Note: Could not determine Rust acceleration status ({error})")

    @staticmethod
    def _display_status_message(message: str, level: str, is_gui: bool) -> None:
        """
        Displays a status message to the user, either via the command-line interface (CLI)
        or a graphical user interface (GUI). The display method and formatting vary
        based on the specified level and interface type.

        Args:
            message: The message string to be displayed to the user.
            level: The severity level of the message ("INFO", "WARNING", or "ERROR").
            is_gui: A flag indicating whether the message is to be displayed in a
                graphical user interface (True) or the command-line interface (False).
        """
        # Always print for CLI visibility
        if not is_gui:
            print(message)

        # Use MessageHandler for both modes (GUI will show toast, CLI will print)
        if level == "INFO":
            msg_info(message)
        elif level == "WARNING":
            from ClassicLib import msg_warning
            msg_warning(message)
        elif level == "ERROR":
            from ClassicLib import msg_error
            msg_error(message)

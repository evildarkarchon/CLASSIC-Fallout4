"""Initialize and coordinates various setup operations and integrity checks for the application.

This module provides a setup coordinator which encapsulates the logic for configuring logging,
generating configuration files, validating paths, performing game integrity checks, and running
application-level initiation sequences. It also manages YAML settings and ensures a consistent
application state across components of the system.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.performance import TimedBlock
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.integration.factory_internal.logging_contract import (
    EVENT_STARTUP_ACCELERATION_STATUS,
    EVENT_STARTUP_BINDING_CONTRACT_FAILED,
    format_contract_event,
)
from ClassicLib.io.yaml import ensure_classic_settings_file_exists, yaml_cache, yaml_settings
from ClassicLib.messaging import MessageTarget, init_message_handler, msg_info, msg_success
from ClassicLib.support.backup import BackupManager
from ClassicLib.support.docs_path import docs_generate_paths, docs_path_find
from ClassicLib.support.documents import DocumentsChecker
from ClassicLib.support.file_gen import FileGenerator
from ClassicLib.support.game_path import game_generate_paths, game_path_find
from ClassicLib.support.integrity import GameIntegrityChecker
from ClassicLib.support.path_validator import PathValidator
from ClassicLib.support.resources import ResourceLoader
from ClassicLib.support.xse import xse_check_hashes, xse_check_integrity
from ClassicLib.Utils.logging_utils import configure_logging, enable_debug_logging


class SetupCoordinator:
    """Coordinates application setup and initialization.

    Manages the complete initialization workflow including file generation,
    game path detection, integrity checking, and settings loading.

    Attributes:
        file_generator: FileGenerator instance for creating config files.
        integrity_checker: GameIntegrityChecker for verifying game files.
        backup_manager: BackupManager for XSE/ENB backup operations.
        docs_checker: DocumentsChecker for validating documents folder.
        path_validator: PathValidator for validating configured paths.

    """

    def __init__(self) -> None:
        """Initialize all helper components for the setup workflow."""
        self.file_generator = FileGenerator()
        self.integrity_checker = GameIntegrityChecker()
        self.backup_manager = BackupManager()
        self.docs_checker = DocumentsChecker()
        self.path_validator = PathValidator()

    def run_initial_setup(self) -> None:
        """Run complete initial setup sequence.

        This method:
        1. Configures logging
        2. Generates required configuration files
        3. Displays welcome messages
        4. Checks for game path and generates paths if needed
        5. Backs up game files if paths are already configured

        Raises:
            TypeError: If the classic version or game name settings are not of type str.

        """
        # Configure logging
        configure_logging(logger)

        # Generate required files
        with TimedBlock("File Generation", log_level="debug"):
            self.file_generator.generate_all_files()

        # Batch load version, game information, game path, and debug setting
        # Use asyncio.run() during initialization (before Qt event loop)
        # AsyncBridge is ONLY for Qt worker threads, NOT for initialization
        with TimedBlock("Initial Settings Load", log_level="debug"):
            requests = [
                (str, YAML.Main, "CLASSIC_Info.version"),
                (str, YAML.Game, "Game_Info.Main_Root_Name"),
                (str, YAML.Game_Local, "Game_Info.Root_Folder_Game"),
                (bool, YAML.Settings, "CLASSIC_Settings.Debug Messages"),
            ]

            classic_ver, game_name, game_path, debug_messages = asyncio.run(yaml_cache.batch_get_settings_async(requests))

            # Enable debug logging if setting is enabled
            if debug_messages:
                enable_debug_logging(logger)

        if not (isinstance(classic_ver, str) and isinstance(game_name, str)):
            raise TypeError("Classic version and game name must be strings")

        # Display welcome messages
        msg_info(
            f"Hello World! | Crash Log Auto Scanner & Setup Integrity Checker | {classic_ver} | {game_name}", target=MessageTarget.CONSOLE
        )
        msg_info("REMINDER: COMPATIBLE CRASH LOGS MUST START WITH 'crash-' AND MUST HAVE .log EXTENSION", target=MessageTarget.CONSOLE)
        msg_info("❓ PLEASE WAIT WHILE CLASSIC CHECKS YOUR SETTINGS AND GAME SETUP...", target=MessageTarget.CONSOLE)
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

        msg_success("ALL CLASSIC AND GAME SETTINGS CHECKS HAVE BEEN PERFORMED!", target=MessageTarget.CONSOLE)
        msg_info("YOU CAN NOW SCAN YOUR CRASH LOGS, GAME AND/OR MOD FILES", target=MessageTarget.CONSOLE)

    @staticmethod
    def _get_config_suffix() -> str:
        """Get the config key suffix based on game version.

        .. deprecated::
            Use :func:`GlobalRegistry.get_config_suffix()` instead.
            This method is kept for backward compatibility.

        This method provides the configuration suffix ("" or "VR") based on the
        current GAME_VERSION setting. Note: Runtime path cache keys now always
        use "Game_Info" regardless of VR status.

        Returns:
            str: "VR" if game version is VR, otherwise empty string "".

        """
        # Delegate to the VersionRegistry-based function in GlobalRegistry
        return GlobalRegistry.get_config_suffix()

    def generate_combined_results(self) -> str:
        """Generate combined results from all checks.

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
        """Initialize application with all required components.

        This method sets up the application state, loads YAML settings cache,
        configures the message handler, and validates paths.

        Args:
            is_gui: Indicates whether the application should operate in GUI mode.
                If True, GUI-related resources are initialized.
            parent: Optional parent widget for GUI mode. This is passed to the
                message handler to ensure proper dialog parenting in GUI applications.

        """
        # Configure logging first - required for both CLI and GUI modes
        configure_logging(logger)

        # Initialize message handler
        # Note: init_message_handler will replace any existing handler
        # In GUI mode, the MainWindow should initialize its own handler with itself as parent
        init_message_handler(parent=parent, is_gui_mode=is_gui)

        # Validate mandatory Rust bindings before touching core workflows.
        from ClassicLib.integration.factory import validate_rust_modules

        validate_rust_modules("startup_all")

        # Get and configure YAML cache (already registered as singleton)
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, is_gui)

        # Ensure data files exist (extracts bundled resources if needed)
        ResourceLoader.ensure_data_files_exist()

        # NOTE: Prefetching removed from initialization
        # AsyncBridge should NOT be used during initialization (before Qt event loop starts)
        # Settings will load lazily on first access, which is fine for startup performance
        # If prefetching is needed, it should be done async with asyncio.run() or after Qt starts

        # Ensure CLASSIC Settings.yaml exists before batch loading.
        # Use non-strict mode here to preserve initialization behavior even if
        # defaults are temporarily invalid.
        ensure_classic_settings_file_exists(strict=False)

        # Batch load all application settings
        # Use asyncio.run() during initialization (before Qt event loop)
        # AsyncBridge is ONLY for Qt worker threads, NOT for initialization
        # Load both legacy VR Mode (for migration) and new Game Version setting
        requests = [
            (str, YAML.Settings, "CLASSIC_Settings.Game Version"),  # New setting (v8.0+)
            (bool, YAML.Settings, "CLASSIC_Settings.VR Mode"),  # Legacy setting (deprecated)
            (str, YAML.Settings, "CLASSIC_Settings.Managed Game"),
            (bool, YAML.Main, "CLASSIC_Info.is_prerelease"),
            (bool, YAML.Settings, "CLASSIC_Settings.Debug Messages"),
        ]

        game_version, legacy_vr_mode, managed_game_setting, is_prerelease, debug_messages = asyncio.run(
            yaml_cache.batch_get_settings_async(requests)
        )

        # Enable debug logging if setting is enabled
        if debug_messages:
            enable_debug_logging(logger)

        # Handle migration from legacy VR Mode to Game Version
        if (not game_version or game_version == "auto") and legacy_vr_mode:
            # Migrate legacy VR Mode = true to Game Version = "VR"
            game_version = "VR"
            logger.info("Migrated legacy VR Mode setting to Game Version: VR")

        # Register the game version (new system)
        # Defaults to "auto" if not set
        effective_game_version = game_version if game_version in {"Original", "NextGen", "VR"} else "auto"
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_VERSION, effective_game_version)

        # Also update legacy VR key for backward compatibility with components not yet migrated
        # This allows get_vr() to work correctly during the transition period
        if effective_game_version == "VR":
            GlobalRegistry.register(GlobalRegistry.Keys.VR, "VR")
        else:
            GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        game_value: str = managed_game_setting.replace(" ", "") if isinstance(managed_game_setting, str) else ""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, game_value)

        GlobalRegistry.register(GlobalRegistry.Keys.IS_PRERELEASE, is_prerelease)

        # Set local directory only if not already set by entry point
        if not GlobalRegistry.is_registered(GlobalRegistry.Keys.LOCAL_DIR):
            if getattr(sys, "frozen", False):
                GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(sys.executable).parent)
            else:
                GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path(__file__).parent.parent.parent)

        # Validate settings paths after initialization
        self.path_validator.validate_all_settings_paths()

        # Detect game and docs paths if not configured
        self._ensure_paths_configured(is_gui)

        # Log Rust acceleration status
        self._log_rust_acceleration_status()

    @staticmethod
    def _ensure_paths_configured(is_gui: bool) -> None:
        """Ensure game and docs paths are configured, detecting them if needed.

        This method checks if game and docs paths exist in settings. If not,
        it triggers automatic path detection.

        Args:
            is_gui: Whether running in GUI mode (affects path detection UI).

        """
        # Check if paths are configured
        game_path = yaml_settings(str, YAML.Game_Local, "Game_Info.Root_Folder_Game")
        docs_path = yaml_settings(str, YAML.Game_Local, "Game_Info.Root_Folder_Docs")

        # Detect docs path if missing
        if not docs_path:
            logger.debug("Docs path not configured, running docs path detection")
            docs_path_find(is_gui)
            docs_generate_paths()

        # Detect game path if missing
        if not game_path:
            logger.debug("Game path not configured, running game path detection")
            game_path_find()
            game_generate_paths()

    def _log_rust_acceleration_status(self) -> None:
        """Log the Rust acceleration status at application startup.

        This method checks which components are using Rust acceleration and logs
        a summary to help with debugging and performance monitoring.

        Logger calls always execute for diagnostics.
        MessageHandler calls only execute when Debug Messages setting is enabled.
        """
        debug_enabled = bool(yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Debug Messages"))
        is_gui = GlobalRegistry.is_gui_mode()

        from ClassicLib.integration.exceptions import RustBindingError
        from ClassicLib.integration.factory import detect_component, validate_rust_modules

        try:
            validate_rust_modules("startup_all")
            known = ["classic_yaml", "classic_scanlog", "classic_file_io", "classic_database", "classic_path"]
            available = [m for m in known if detect_component(m)[0]]
            status = {
                "active_count": len(available),
                "total_count": len(known),
                "percentage": len(available) / len(known) * 100,
                "acceleration_level": "MANDATORY",
                "performance_gains": dict.fromkeys(available, "active"),
            }
            self._log_active_acceleration(status, debug_enabled, is_gui)
        except RustBindingError as error:
            self._log_binding_failure(error, debug_enabled, is_gui)
            raise

    @staticmethod
    def _log_active_acceleration(status: dict[str, Any], debug_enabled: bool, is_gui: bool) -> None:
        """Log status when Rust acceleration is active."""
        status_msg = (
            f"🚀 Rust Acceleration: {status['active_count']}/{status['total_count']} components active ({status['percentage']:.0f}%)"
        )
        if debug_enabled:
            SetupCoordinator._display_status_message(status_msg, "INFO", is_gui)

        logger.info(f"Rust Acceleration Status: {status['acceleration_level']}")
        logger.info(f"   Active Components: {status['active_count']}/{status['total_count']} ({status['percentage']:.1f}%)")

        # Log detailed component info at debug level
        if status["performance_gains"]:
            logger.debug("   Active Rust Components:")
            for component, speedup in status["performance_gains"].items():
                logger.debug(f"      ✅ {component}: {speedup}")

        logger.info(
            format_contract_event(
                component="integration.startup",
                event=EVENT_STARTUP_ACCELERATION_STATUS,
                severity="info",
                outcome="success",
                context={
                    "active_components": status["active_count"],
                    "total_components": status["total_count"],
                    "acceleration_level": status["acceleration_level"],
                },
            )
        )

    @staticmethod
    def _log_binding_failure(error: Exception, debug_enabled: bool, is_gui: bool) -> None:
        """Log status when mandatory Rust bindings fail startup validation."""
        from ClassicLib.integration.exceptions import get_rust_rebuild_remediation

        status_msg = f"❌ Required Rust bindings failed validation: {error}"
        if debug_enabled:
            SetupCoordinator._display_status_message(status_msg, "ERROR", is_gui)
        logger.error(
            format_contract_event(
                component="integration.startup",
                event=EVENT_STARTUP_BINDING_CONTRACT_FAILED,
                severity="error",
                outcome="failure",
                context={
                    "failure_hint": get_rust_rebuild_remediation(),
                    "error": str(error),
                },
            )
        )

    @staticmethod
    def _log_status_check_error(error: Exception, debug_enabled: bool, is_gui: bool) -> None:
        """Log error when Rust status check fails unexpectedly."""
        logger.debug(f"Error checking Rust acceleration status: {error}")
        if debug_enabled and not is_gui:
            print(f"Note: Could not determine Rust acceleration status ({error})")

    @staticmethod
    def _display_status_message(message: str, level: str, is_gui: bool) -> None:
        """Display a status message to the user, either via the command-line interface (CLI)
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

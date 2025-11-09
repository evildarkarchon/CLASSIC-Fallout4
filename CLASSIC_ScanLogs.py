"""
CLASSIC ScanLogs CLI interface.

This module provides a command-line interface for CLASSIC crash log scanning.
It has been refactored to use the new modular architecture while maintaining
backward compatibility.

Phase 4: Async-First CLI Entry Point
-------------------------------------
This CLI uses native async patterns (like TUI) instead of AsyncBridge.
The main() function is async and uses asyncio.run() only at the entry point.
"""

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ClassicLib.Constants import YAML
from ClassicLib.ScanLog.models import ScanConfig, ScanResult
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
from ClassicLib.SetupCoordinator import SetupCoordinator
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

if TYPE_CHECKING:
    import argparse
    from argparse import Namespace


def parse_arguments() -> "argparse.Namespace":
    """Parse command line arguments.

    Returns:
        Parsed command line arguments containing configuration options for CLASSIC.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Command-line arguments for CLASSIC's Command Line Interface")

    parser.add_argument("--fcx-mode", action=argparse.BooleanOptionalAction, help="Enable FCX mode")
    parser.add_argument("--show-fid-values", action=argparse.BooleanOptionalAction, help="Show FormID values")
    parser.add_argument("--stat-logging", action=argparse.BooleanOptionalAction, help="Enable statistical logging")
    parser.add_argument("--move-unsolved", action=argparse.BooleanOptionalAction, help="Move unsolved logs")
    parser.add_argument("--ini-path", type=Path, help="Path to the INI file")
    parser.add_argument("--scan-path", type=Path, help="Path to the scan directory")
    parser.add_argument("--mods-folder-path", type=Path, help="Path to the mods folder")
    parser.add_argument(
        "--simplify-logs", action=argparse.BooleanOptionalAction, help="Simplify the logs (Warning: May remove important information)"
    )

    return parser.parse_args()


def create_config_from_args(args: "argparse.Namespace") -> ScanConfig:
    """Create scan configuration from CLI arguments.

    Args:
        args: Parsed command line arguments containing configuration options.

    Returns:
        ScanConfig: A configured ScanConfig instance with settings applied from
            command line arguments. Settings are also persisted to YAML files.
    """
    from ClassicLib import msg_error

    config = ScanConfig()

    # Handle command line arguments by updating settings
    if isinstance(args.fcx_mode, bool) and args.fcx_mode != classic_settings(bool, "FCX Mode"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", args.fcx_mode)
        config.fcx_mode = args.fcx_mode

    if isinstance(args.show_fid_values, bool) and args.show_fid_values != classic_settings(bool, "Show FormID Values"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Show FormID Values", args.show_fid_values)
        config.show_formid_values = args.show_fid_values

    if isinstance(args.move_unsolved, bool) and args.move_unsolved != classic_settings(bool, "Move Unsolved Logs"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved Logs", args.move_unsolved)
        config.move_unsolved_logs = args.move_unsolved

    if (
        isinstance(args.ini_path, Path)
        and args.ini_path.resolve().is_dir()
        and str(args.ini_path) != classic_settings(str, "INI Folder Path")
    ):
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", str(args.ini_path.resolve()))
        config.custom_paths["ini_path"] = args.ini_path.resolve()

    if (
        isinstance(args.scan_path, Path)
        and args.scan_path.resolve().is_dir()
        and str(args.scan_path) != classic_settings(str, "SCAN Custom Path")
    ):
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        if is_valid_custom_scan_path(args.scan_path):
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(args.scan_path.resolve()))
            config.custom_paths["scan_path"] = args.scan_path.resolve()
        else:
            msg_error(
                "WARNING: The specified scan path cannot be used as a custom scan directory.\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC and cannot be set as custom scan directories.\n"
                "Resetting custom scan path."
            )
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")

    if (
        isinstance(args.mods_folder_path, Path)
        and args.mods_folder_path.resolve().is_dir()
        and str(args.mods_folder_path) != classic_settings(str, "MODS Folder Path")
    ):
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", str(args.mods_folder_path.resolve()))
        config.custom_paths["mods_folder_path"] = args.mods_folder_path.resolve()

    if isinstance(args.simplify_logs, bool) and args.simplify_logs != classic_settings(bool, "Simplify Logs"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Simplify Logs", args.simplify_logs)
        config.simplify_logs = args.simplify_logs

    return config


async def main() -> None:
    """
    Main CLI entry point - Async-First (Phase 4).

    This function is async and uses native await instead of AsyncBridge,
    matching the TUI pattern. asyncio.run() is only used at the entry point.
    """
    # Ensure UTF-8 encoding for Windows console
    from ClassicLib.MessageHandler import msg_info

    if sys.platform == "win32":  # type: ignore
        import io

        # noinspection PyTypeChecker
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        # noinspection PyTypeChecker
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

    # Initialize application using SetupCoordinator
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)

    # Parse command line arguments and create configuration
    args: Namespace = parse_arguments()
    config: ScanConfig = create_config_from_args(args)

    # Create executor and run scan using native async
    executor = ScanLogsExecutor(config)
    result: ScanResult = await executor.execute_scan()  # ✅ Direct async, no AsyncBridge

    # Display results summary
    msg_info(executor.generate_summary(result))

    # Ensure all output is flushed before pause
    sys.stdout.flush()
    sys.stderr.flush()


if __name__ == "__main__":
    # Single asyncio.run() at entry point only
    asyncio.run(main())

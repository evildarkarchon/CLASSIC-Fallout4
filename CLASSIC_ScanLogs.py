"""CLASSIC ScanLogs CLI interface.

This module provides a command-line interface for CLASSIC crash log scanning.
It has been refactored to use the new modular architecture while maintaining
backward compatibility.

Phase 4: Async-First CLI Entry Point
-------------------------------------
This CLI uses native async patterns (like TUI) instead of AsyncBridge.
The main() function is async and uses asyncio.run() only at the entry point.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ClassicLib.Constants import YAML
from ClassicLib.ScanLog.models import ScanConfig, ScanResult
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
from ClassicLib.SetupCoordinator import SetupCoordinator
from ClassicLib.YamlSettings import classic_settings_async, yaml_settings_async

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

    # Add max-concurrent argument with CPU-based help text
    cpu_count = os.cpu_count() or 4
    recommended = max(cpu_count - 2, 2)
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=None,
        metavar="N",
        help=f"Maximum parallel crash log scans. 0 = Automatic (recommended). "
        f"Suggested value for your system: {recommended} (based on {cpu_count} CPU cores)",
    )

    return parser.parse_args()


async def create_config_from_args_async(args: "argparse.Namespace") -> ScanConfig:
    """Create scan configuration from CLI arguments asynchronously.

    This function uses async settings functions for efficient CLI operation,
    avoiding AsyncBridge overhead that is only needed in GUI contexts.

    Args:
        args: Parsed command line arguments containing configuration options.

    Returns:
        ScanConfig: A configured ScanConfig instance with settings applied from
            command line arguments. Settings are also persisted to YAML files.

    """
    from ClassicLib import msg_error

    config = ScanConfig()

    # Handle command line arguments by updating settings
    if isinstance(args.fcx_mode, bool) and args.fcx_mode != await classic_settings_async(bool, "FCX Mode"):
        await yaml_settings_async(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", args.fcx_mode)
        config.fcx_mode = args.fcx_mode

    if isinstance(args.show_fid_values, bool) and args.show_fid_values != await classic_settings_async(bool, "Show FormID Values"):
        await yaml_settings_async(bool, YAML.Settings, "CLASSIC_Settings.Show FormID Values", args.show_fid_values)
        config.show_formid_values = args.show_fid_values

    if isinstance(args.move_unsolved, bool) and args.move_unsolved != await classic_settings_async(bool, "Move Unsolved Logs"):
        await yaml_settings_async(bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved Logs", args.move_unsolved)
        config.move_unsolved_logs = args.move_unsolved

    if (
        isinstance(args.ini_path, Path)
        and args.ini_path.resolve().is_dir()
        and str(args.ini_path) != await classic_settings_async(str, "INI Folder Path")
    ):
        await yaml_settings_async(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", str(args.ini_path.resolve()))
        config.custom_paths["ini_path"] = args.ini_path.resolve()

    if (
        isinstance(args.scan_path, Path)
        and args.scan_path.resolve().is_dir()
        and str(args.scan_path) != await classic_settings_async(str, "SCAN Custom Path")
    ):
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        if is_valid_custom_scan_path(args.scan_path):
            await yaml_settings_async(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(args.scan_path.resolve()))
            config.custom_paths["scan_path"] = args.scan_path.resolve()
        else:
            msg_error(
                "WARNING: The specified scan path cannot be used as a custom scan directory.\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC and cannot be set as custom scan directories.\n"
                "Resetting custom scan path."
            )
            await yaml_settings_async(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")

    if (
        isinstance(args.mods_folder_path, Path)
        and args.mods_folder_path.resolve().is_dir()
        and str(args.mods_folder_path) != await classic_settings_async(str, "MODS Folder Path")
    ):
        await yaml_settings_async(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", str(args.mods_folder_path.resolve()))
        config.custom_paths["mods_folder_path"] = args.mods_folder_path.resolve()

    if isinstance(args.simplify_logs, bool) and args.simplify_logs != await classic_settings_async(bool, "Simplify Logs"):
        await yaml_settings_async(bool, YAML.Settings, "CLASSIC_Settings.Simplify Logs", args.simplify_logs)
        config.simplify_logs = args.simplify_logs

    # Handle --max-concurrent argument
    if args.max_concurrent is not None:
        # Validate CLI argument to match ScanConfig.__post_init__ constraints (0-32)
        # This is necessary because we assign to config.max_concurrent after construction,
        # bypassing __post_init__ validation
        validated_value = max(0, min(args.max_concurrent, 32))

        # CLI argument provided - save to YAML if different and use it
        current_setting = await classic_settings_async(int, "Max Concurrent Scans") or 0
        if validated_value != current_setting:
            await yaml_settings_async(int, YAML.Settings, "CLASSIC_Settings.Max Concurrent Scans", validated_value)
        config.max_concurrent = validated_value
    else:
        # No CLI argument - load from saved YAML setting
        # Validate to match ScanConfig constraints (0-32) in case YAML was manually edited
        yaml_value = await classic_settings_async(int, "Max Concurrent Scans") or 0
        config.max_concurrent = max(0, min(yaml_value, 32))

    return config


async def run_scan(args: "Namespace") -> None:
    """Run the scan operation asynchronously.

    This function contains the async portion of the CLI entry point.
    It creates the config using async settings functions and executes the scan.

    Args:
        args: Parsed command line arguments.

    """
    from ClassicLib.MessageHandler import msg_info

    # Create configuration from arguments using async settings (inside event loop)
    config = await create_config_from_args_async(args)

    try:
        # Create executor and run scan using native async
        executor = ScanLogsExecutor(config)
        result: ScanResult = await executor.execute_scan()  # ✅ Direct async, no AsyncBridge

        # Display results summary
        msg_info(executor.generate_summary(result))
    finally:
        # Close database connections to ensure WAL files are properly checkpointed
        # This prevents .db-wal and .db-shm files from persisting after exit
        from ClassicLib.Database import cleanup_database_pools_async

        await cleanup_database_pools_async()

    # Ensure all output is flushed before pause
    sys.stdout.flush()
    sys.stderr.flush()


def main() -> None:
    """Serve as main CLI entry point - Async-First (Phase 4).

    This function handles synchronous initialization (SetupCoordinator uses asyncio.run()
    internally), then delegates to async run_scan() for the actual scan operation.
    This structure prevents nested asyncio.run() calls.
    """
    # Ensure UTF-8 encoding for Windows console
    if sys.platform == "win32":  # type: ignore[comparison-overlap]  # Platform type narrowing
        import io

        # noinspection PyTypeChecker
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        # noinspection PyTypeChecker
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

    # Parse command line arguments first (may exit for --help)
    args: Namespace = parse_arguments()

    # Initialize application using SetupCoordinator
    # NOTE: This must happen BEFORE asyncio.run() because SetupCoordinator
    # uses asyncio.run() internally for async operations
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)

    # Run the async scan operation (config creation happens inside async context)
    asyncio.run(run_scan(args))


if __name__ == "__main__":
    main()

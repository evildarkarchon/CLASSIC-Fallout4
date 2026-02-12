"""Factory for ScanGame components using mandatory Rust acceleration.

This module provides factory functions that return Rust implementations
from the classic_scangame binding crate.

Usage:
    from ClassicLib.integration.scangame_factory import get_ba2_scanner

    scanner = get_ba2_scanner()
    issues = scanner.scan_archive(path)
"""

from pathlib import Path
from typing import Any

import classic_scangame


def is_rust_available() -> bool:
    """Check if Rust acceleration is available.

    Returns:
        Always True since classic_scangame is mandatory.

    """
    return True


def get_ba2_scanner() -> Any:
    """Get BA2Scanner implementation.

    Returns:
        BA2Scanner instance from Rust.

    """
    return classic_scangame.BA2Scanner()


def get_config_duplicate_detector() -> Any:
    """Get ConfigDuplicateDetector implementation.

    Returns:
        ConfigDuplicateDetector instance from Rust.

    """
    return classic_scangame.ConfigDuplicateDetector()


def get_unpacked_scanner() -> Any:
    """Get UnpackedScanner implementation.

    Returns:
        UnpackedScanner instance from Rust.

    """
    return classic_scangame.UnpackedScanner()


def get_log_processor(catch_errors: list[str], ignore_files: list[str], ignore_errors: list[str]) -> Any:
    """Get LogProcessor implementation.

    Args:
        catch_errors: List of error patterns to catch.
        ignore_files: List of file patterns to ignore.
        ignore_errors: List of error patterns to ignore.

    Returns:
        LogProcessor instance from Rust.

    """
    return classic_scangame.LogProcessor(catch_errors, ignore_files, ignore_errors)


def get_ini_validator(game_name: str) -> Any:
    """Get IniValidator implementation.

    Args:
        game_name: Name of the game (e.g., "Fallout4").

    Returns:
        IniValidator instance from Rust.

    """
    return classic_scangame.IniValidator(game_name)


def get_crashgen_checker(plugins_path: Path, crashgen_name: str) -> Any:
    """Get CrashgenChecker implementation.

    Args:
        plugins_path: Path to plugins directory.
        crashgen_name: Name of crash generator (e.g., "Buffout4").

    Returns:
        CrashgenChecker instance from Rust.

    """
    return classic_scangame.CrashgenChecker(plugins_path, crashgen_name)


def get_xse_checker(plugins_path: Path, is_vr_mode: bool = False, game_version: Any = None) -> Any:
    """Get XseChecker implementation.

    Args:
        plugins_path: Path to plugins directory.
        is_vr_mode: Whether game is in VR mode.
        game_version: Game version enum (uses Original if None).

    Returns:
        XseChecker instance from Rust.

    """
    if game_version is None:
        game_version = classic_scangame.GameVersion.Original
    return classic_scangame.XseChecker(plugins_path, is_vr_mode, game_version)


def get_rust_status() -> dict[str, Any]:
    """Get detailed Rust acceleration status.

    Returns:
        Dictionary with Rust availability information.

    """
    components = [
        "BA2Scanner",
        "ConfigDuplicateDetector",
        "UnpackedScanner",
        "LogProcessor",
        "IniValidator",
        "CrashgenChecker",
        "XseChecker",
    ]

    return {"available": True, "version": getattr(classic_scangame, "__version__", "unknown"), "components": components}

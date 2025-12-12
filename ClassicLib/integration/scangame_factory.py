"""Factory for ScanGame components with transparent Rust acceleration.

This module provides factory functions that return Rust implementations when available,
automatically falling back to Python implementations if Rust modules are not installed.

Usage:
    from ClassicLib.integration.scangame_factory import get_ba2_scanner

    scanner = get_ba2_scanner()  # Returns Rust or Python implementation
    issues = scanner.scan_archive(path)
"""

from pathlib import Path
from types import ModuleType
from typing import Any

# Track Rust availability
_RUST_AVAILABLE = False
_classic_scangame: ModuleType | None = None

try:
    import classic_scangame

    _classic_scangame = classic_scangame
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False


def is_rust_available() -> bool:
    """Check if Rust acceleration is available.

    Returns:
        True if classic_scangame Rust module is installed, False otherwise.

    """
    return _RUST_AVAILABLE


def get_ba2_scanner() -> Any:
    """Get BA2Scanner implementation (Rust or Python fallback).

    Returns:
        BA2Scanner instance (Rust if available, otherwise Python).

    """
    if _RUST_AVAILABLE:
        assert _classic_scangame is not None
        return _classic_scangame.BA2Scanner()
    from ClassicLib.ScanGame.core.ba2_fallback import BA2Scanner

    return BA2Scanner()


def get_config_duplicate_detector() -> Any:
    """Get ConfigDuplicateDetector implementation (Rust or Python fallback).

    Returns:
        ConfigDuplicateDetector instance (Rust if available, otherwise Python).

    """
    if _RUST_AVAILABLE:
        assert _classic_scangame is not None
        return _classic_scangame.ConfigDuplicateDetector()
    from ClassicLib.ScanGame.core.config_duplicate_fallback import ConfigDuplicateDetector

    return ConfigDuplicateDetector()


def get_unpacked_scanner() -> Any:
    """Get UnpackedScanner implementation (Rust or Python fallback).

    Returns:
        UnpackedScanner instance (Rust if available, otherwise Python).

    """
    if _RUST_AVAILABLE:
        assert _classic_scangame is not None
        return _classic_scangame.UnpackedScanner()
    from ClassicLib.ScanGame.core.unpacked_fallback import UnpackedScanner

    return UnpackedScanner()


def get_log_processor(catch_errors: list[str], ignore_files: list[str], ignore_errors: list[str]) -> Any:
    """Get LogProcessor implementation (Rust or Python fallback).

    Args:
        catch_errors: List of error patterns to catch.
        ignore_files: List of file patterns to ignore.
        ignore_errors: List of error patterns to ignore.

    Returns:
        LogProcessor instance (Rust if available, otherwise Python).

    """
    if _RUST_AVAILABLE:
        assert _classic_scangame is not None
        return _classic_scangame.LogProcessor(catch_errors, ignore_files, ignore_errors)
    from ClassicLib.ScanGame.core.log_fallback import LogProcessor

    return LogProcessor(catch_errors, ignore_files, ignore_errors)


def get_ini_validator(game_name: str) -> Any:
    """Get IniValidator implementation (Rust or Python fallback).

    Args:
        game_name: Name of the game (e.g., "Fallout4").

    Returns:
        IniValidator instance (Rust if available, otherwise Python).

    """
    if _RUST_AVAILABLE:
        assert _classic_scangame is not None
        return _classic_scangame.IniValidator(game_name)
    from ClassicLib.ScanGame.core.ini_fallback import IniValidator

    return IniValidator(game_name)


def get_crashgen_checker(plugins_path: Path, crashgen_name: str) -> Any:
    """Get CrashgenChecker implementation (Rust or Python fallback).

    Args:
        plugins_path: Path to plugins directory.
        crashgen_name: Name of crash generator (e.g., "Buffout4").

    Returns:
        CrashgenChecker instance (Rust if available, otherwise Python).

    Note:
        The Python fallback retrieves plugins_path and crashgen_name from
        settings internally, so these arguments are only used for Rust.

    """
    if _RUST_AVAILABLE:
        assert _classic_scangame is not None
        return _classic_scangame.CrashgenChecker(plugins_path, crashgen_name)
    from ClassicLib.ScanGame.CheckCrashgen import CrashgenChecker

    # Python implementation gets these from settings, ignores arguments
    return CrashgenChecker()


def get_xse_checker(plugins_path: Path, is_vr_mode: bool = False, game_version: Any = None) -> Any:
    """Get XseChecker implementation (Rust or Python fallback).

    Args:
        plugins_path: Path to plugins directory.
        is_vr_mode: Whether game is in VR mode.
        game_version: Game version enum (uses Original if None).

    Returns:
        XseChecker instance (Rust if available, otherwise Python).

    """
    if _RUST_AVAILABLE:
        assert _classic_scangame is not None
        if game_version is None:
            game_version = _classic_scangame.GameVersion.Original
        return _classic_scangame.XseChecker(plugins_path, is_vr_mode, game_version)
    from ClassicLib.ScanGame.core.xse_fallback import GameVersion, XseChecker

    if game_version is None:
        game_version = GameVersion.Original
    return XseChecker(plugins_path, is_vr_mode, game_version)


def get_rust_status() -> dict[str, Any]:
    """Get detailed Rust acceleration status.

    Returns:
        Dictionary with Rust availability information:
        - available: bool - Whether Rust is available
        - version: str or None - classic_scangame version
        - components: list[str] - Available Rust components

    """
    if not _RUST_AVAILABLE:
        return {"available": False, "version": None, "components": []}

    components = [
        "BA2Scanner",
        "ConfigDuplicateDetector",
        "UnpackedScanner",
        "LogProcessor",
        "IniValidator",
        "CrashgenChecker",
        "XseChecker",
    ]

    return {"available": True, "version": getattr(_classic_scangame, "__version__", "unknown"), "components": components}

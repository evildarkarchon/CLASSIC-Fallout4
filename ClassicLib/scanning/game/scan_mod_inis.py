"""Mod INI scanning - thin wrapper delegating to Rust ModIniScanner (G-04).

Replaces ~350 lines of Python with delegation to Rust for console command
detection, VSync settings, mod-specific issue detection, and duplicate scanning.
"""

from pathlib import Path
from typing import Any

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import get_game, get_vr
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue, ConfigIssueSeverity


def _get_game_root() -> Path | None:
    """Resolve the game root path from YAML settings."""
    return yaml_settings(Path, YAML.Game_Local, f"Game{get_vr()}_Info.Root_Folder_Game")


def _run_rust_scan() -> Any:
    """Run the Rust ModIniScanner and return the raw result."""
    from classic_scangame import RustModIniScanner

    game_root = _get_game_root()
    if not game_root:
        return None

    return RustModIniScanner.scan(game_root, get_game())


async def scan_mod_inis_async() -> str:  # noqa: RUF029
    """Scan mod INI files for issues using Rust ModIniScanner.

    Must remain async for callers using ``await scan_mod_inis_async()``.

    Returns:
        str: Formatted report of console command notices, VSync settings,
        mod-specific issues, and duplicate files detected.

    """
    result = _run_rust_scan()
    return result.message if result else ""


def scan_mod_inis() -> str:
    """Sync wrapper for scan_mod_inis_async. GUI workers only.

    WARNING: This function uses AsyncBridge internally and creates
    additional event loop overhead. Not for CLI use.

    Returns:
        str: Formatted report of detected INI issues.

    """
    result = _run_rust_scan()
    return result.message if result else ""


async def detect_all_ini_issues_async(config_files: Any = None) -> list[ConfigIssue]:  # noqa: RUF029, ARG001
    """Detect all INI configuration issues using Rust scanner.

    Must remain async for callers using ``await``.

    Args:
        config_files: Ignored (kept for backward compatibility). Rust creates
            its own ConfigFileCache internally.

    Returns:
        list[ConfigIssue]: Structured configuration issues detected by Rust.

    """
    result = _run_rust_scan()
    if not result:
        return []

    return [
        ConfigIssue(
            file_path=Path(issue.file_path),
            section=issue.section,
            setting=issue.setting,
            current_value=issue.current_value,
            recommended_value=issue.recommended_value,
            description=issue.description,
            severity=_convert_severity(issue.severity),
        )
        for issue in result.issues
    ]


def _convert_severity(rust_severity: object) -> ConfigIssueSeverity:
    """Convert Rust IssueSeverity enum to Python ConfigIssueSeverity string."""
    name = getattr(rust_severity, "name", str(rust_severity)).lower()
    if name in {"error", "warning", "info"}:
        return name  # type: ignore[return-value]
    return "warning"

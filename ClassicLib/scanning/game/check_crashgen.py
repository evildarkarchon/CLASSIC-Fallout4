"""Check and validate settings for Crash Generator (Buffout4) configuration.

Delegates path resolution, plugin detection, TOML parsing, and settings
validation to the Rust CrashgenCheckOrchestrator (classic_scangame).
Python handles YAML settings resolution and backward-compatible type conversion.
"""

from pathlib import Path

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import get_vr
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue


def check_crashgen_settings() -> tuple[str, list[ConfigIssue]]:
    """Check crash generator settings using the Rust CrashgenCheckOrchestrator.

    Resolves paths and names from YAML, delegates to Rust for the full
    check (path resolution, plugin detection, TOML validation), then
    converts the result to backward-compatible Python types.

    Returns:
        tuple[str, list[ConfigIssue]]: A tuple containing:
            - Formatted message string with detected issues and recommendations
            - List of ConfigIssue objects for structured reporting

    """
    from classic_scangame import CrashgenCheckOrchestrator

    # Resolve settings from YAML
    plugins_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{get_vr()}_Info.Game_Folder_Plugins")
    crashgen_name_setting: str | None = yaml_settings(str, YAML.Game, f"Game{get_vr()}_Info.CRASHGEN_LogName")
    crashgen_name: str = crashgen_name_setting if isinstance(crashgen_name_setting, str) else "Buffout4"

    if not plugins_path:
        msg = (
            f"# [!] NOTICE : Unable to find the {crashgen_name} config file, settings check will be skipped. #\n"
            f"  To ensure this check doesn't get skipped, {crashgen_name} has to be installed manually.\n"
            "  [ If you are using Mod Organizer 2, you need to run CLASSIC through a shortcut in MO2. ]\n-----\n"
        )
        return msg, []

    # Delegate to Rust orchestrator
    report = CrashgenCheckOrchestrator.check(plugins_path, crashgen_name)

    # Convert Rust TomlConfigIssue objects to Python ConfigIssue for backward compat
    issues: list[ConfigIssue] = [
        ConfigIssue(
            file_path=Path(issue.file_path) if issue.file_path else plugins_path,
            section=issue.section,
            setting=issue.setting,
            current_value=issue.current_value,
            recommended_value=issue.recommended_value,
            description=issue.description,
            severity=_convert_severity(issue.severity),
        )
        for issue in report.issues
    ]

    return report.message, issues


def _convert_severity(rust_severity: object) -> str:
    """Convert a Rust TomlIssueSeverity enum to a Python severity string."""
    name = getattr(rust_severity, "name", str(rust_severity)).lower()
    if name in {"error", "warning", "info"}:
        return name
    return "warning"

"""Check and validate settings for Crash Generator (Buffout4) configuration.

Delegates path resolution, plugin detection, TOML parsing, and settings
validation to the Rust CrashgenCheckOrchestrator (classic_scangame).
Python handles YAML settings resolution and backward-compatible type conversion.
"""

from pathlib import Path

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import get_vr
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue, ConfigIssueSeverity


def check_crashgen_settings() -> tuple[str, list[ConfigIssue]]:
    """Check crash generator settings using the Rust CrashgenCheckOrchestrator.

    Resolves paths and names from YAML, delegates to Rust for the full
    check (path resolution, plugin detection, TOML validation), then
    converts the result to backward-compatible Python types.

    Note: The Buffout-4-only name gate has been removed. The Rust orchestrator
    now handles per-crashgen routing via the CrashgenRegistry.

    Returns:
        tuple[str, list[ConfigIssue]]: A tuple containing:
            - Formatted message string with detected issues and recommendations
            - List of ConfigIssue objects for structured reporting

    """
    from classic_scangame import CrashgenCheckOrchestrator
    from ClassicLib.support.versions import get_version_registry
    from ClassicLib.support.versions.core import get_detected_version_info

    # Resolve runtime path from YAML cache
    plugins_path: Path | None = yaml_settings(Path, YAML.Game_Local, "Game_Info.Game_Folder_Plugins")

    # Get crashgen display name from Version Registry (static metadata).
    # Use the detected version so NG/AE users get their edition's crashgen name
    # (e.g. "Buffout 4 NG") rather than always falling back to OG's first entry.
    # Fall back to FO4_OG if detection is unavailable (e.g. EXE not yet found).
    registry = get_version_registry()
    is_vr = get_vr() == "VR"
    version_info = get_detected_version_info() or registry.get_by_id("FO4_VR" if is_vr else "FO4_OG")
    crashgen_name: str = "Buffout4"
    if version_info and version_info.crashgen_versions:
        crashgen_name = version_info.crashgen_versions[0].name

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


def _convert_severity(rust_severity: object) -> ConfigIssueSeverity:
    """Convert a Rust TomlIssueSeverity enum to a Python severity string."""
    name = getattr(rust_severity, "name", str(rust_severity)).lower()
    if name == "error":
        return "error"
    if name == "info":
        return "info"
    return "warning"

"""Parse and identify potential issues in Wrye Bash plugin checker reports.

Delegates HTML parsing and report formatting to the Rust WryeBashParser
(classic_scangame.WryeBashParser). Python handles YAML settings resolution,
file reading, and surrounding message construction.
"""

from pathlib import Path

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import get_game, get_vr
from ClassicLib.integration.factory import get_file_io
from ClassicLib.io.yaml import yaml_settings


def _read_file(path: Path) -> str:
    """Read a file synchronously via AsyncBridge (GUI-only helper)."""
    io_core = get_file_io()
    return AsyncBridge.get_instance().run_async(io_core.read_file(path))


def scan_wryecheck() -> str:
    """Scan the Wrye Bash plugin checker report for detected problems.

    Reads settings from YAML configuration, reads the HTML report,
    and delegates parsing to the Rust WryeBashParser.

    Returns:
        Analysis message detailing the report contents, or a warning
        if the report is missing.

    Raises:
        ValueError: If required warnings setting is missing from YAML config.

    """
    from classic_scangame import WryeBashParser

    # Load settings from YAML
    missing_html_setting: str | None = yaml_settings(str, YAML.Game, "Warnings_MODS.Warn_WRYE_MissingHTML")
    plugin_check_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{get_vr()}_Info.Docs_File_WryeBashPC")
    warnings_dict: dict[str, str] | None = yaml_settings(dict[str, str], YAML.Main, "Warnings_WRYE")

    missing_html_message: str | None = missing_html_setting if isinstance(missing_html_setting, str) else None
    wrye_warnings: dict[str, str] = warnings_dict if isinstance(warnings_dict, dict) else {}

    # Return early if report not found
    if not plugin_check_path or not plugin_check_path.is_file():
        if missing_html_message is not None:
            return missing_html_message
        raise ValueError("ERROR: Warnings_WRYE missing from the database!")

    # Read HTML and delegate parsing to Rust
    html_content = _read_file(plugin_check_path)
    parser = WryeBashParser(wrye_warnings)
    issues = parser.parse(html_content)
    report_body = WryeBashParser.format_report(issues)

    # Build the full message with header and resource links
    message_parts: list[str] = [
        "\n\u2714\ufe0f WRYE BASH PLUGIN CHECKER REPORT WAS FOUND! ANALYZING CONTENTS...\n",
        f"  [This report is located in your Documents/My Games/{get_game()} folder.]\n",
        "  [To hide this report, remove *ModChecker.html* from the same folder.]\n",
        report_body,
        "\n\u2754 For more info about the above detected problems, see the WB Advanced Readme\n",
        "  For more details about solutions, read the Advanced Troubleshooting Article\n",
        "  Advanced Troubleshooting: https://www.nexusmods.com/fallout4/articles/4141\n",
        "  Wrye Bash Advanced Readme Documentation: https://wrye-bash.github.io/docs/\n",
        "  [ After resolving any problems, run Plugin Checker in Wrye Bash again! ]\n\n",
    ]

    return "".join(message_parts)

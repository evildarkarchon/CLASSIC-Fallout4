from pathlib import Path

from bs4 import BeautifulSoup, PageElement

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Util import open_file_with_encoding
from ClassicLib.YamlSettingsCache import yaml_settings


def scan_wryecheck() -> str:
    """
    Analyzes Wrye Bash plugin checker report and generates a detailed message containing plugin-related warnings,
    recommendations, and additional resources based on the report content and predefined settings.

    Returns:
        str: A formatted multi-line string containing analysis and recommendations based on the Wrye Bash plugin
        checker report.
    """
    # Constants for formatting and links
    # noinspection PyPep8Naming
    RESOURCE_LINKS: dict[str, str] = {
        "troubleshooting": "https://www.nexusmods.com/fallout4/articles/4141",
        "documentation": "https://wrye-bash.github.io/docs/",
        "simple_eslify": "https://www.nexusmods.com/skyrimspecialedition/mods/27568",
    }

    # Load settings from YAML
    missing_html_setting: str | None = yaml_settings(str, YAML.Game, "Warnings_MODS.Warn_WRYE_MissingHTML")
    plugin_check_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_WryeBashPC")
    warnings_dict: dict[str, str] | None = yaml_settings(dict[str, str], YAML.Main, "Warnings_WRYE")

    # Validate settings
    missing_html_message: str | None = missing_html_setting if isinstance(missing_html_setting, str) else None
    wrye_warnings: dict[str, str] = warnings_dict if isinstance(warnings_dict, dict) else {}

    # Return early if report not found
    if not plugin_check_path or not plugin_check_path.is_file():
        if missing_html_message is not None:
            return missing_html_message
        raise ValueError("ERROR: Warnings_WRYE missing from the database!")

    # Build the message
    message_parts: list[str] = [
        "\n✔️ WRYE BASH PLUGIN CHECKER REPORT WAS FOUND! ANALYZING CONTENTS...\n",
        f"  [This report is located in your Documents/My Games/{GlobalRegistry.get_game()} folder.]\n",
        "  [To hide this report, remove *ModChecker.html* from the same folder.]\n",
    ]

    # Parse the HTML report
    report_contents: list[str] = parse_wrye_report(plugin_check_path, wrye_warnings)
    message_parts.extend(report_contents)

    # Add resource links
    message_parts.extend([
        "\n❔ For more info about the above detected problems, see the WB Advanced Readme\n",
        "  For more details about solutions, read the Advanced Troubleshooting Article\n",
        f"  Advanced Troubleshooting: {RESOURCE_LINKS['troubleshooting']}\n",
        f"  Wrye Bash Advanced Readme Documentation: {RESOURCE_LINKS['documentation']}\n",
        "  [ After resolving any problems, run Plugin Checker in Wrye Bash again! ]\n\n",
    ])

    return "".join(message_parts)


def parse_wrye_report(report_path: Path, wrye_warnings: dict[str, str]) -> list[str]:
    """
    Parses the Wrye Bash HTML report and formats the content into readable messages.

    Args:
        report_path: Path to the Wrye Bash plugin checker HTML report
        wrye_warnings: Dictionary containing warning messages for specific section titles

    Returns:
        List of formatted message strings
    """
    message_parts: list[str] = []

    # Read and parse HTML file
    with open_file_with_encoding(report_path) as wb_file:
        soup: BeautifulSoup = BeautifulSoup(wb_file.read(), "html.parser")

    # Process each section (h3 element)
    for section in soup.find_all("h3"):
        title: str = section.get_text()
        plugins: list[str] = extract_plugins_from_section(section)

        # Format section header
        if title != "Active Plugins:":
            message_parts.append(format_section_header(title))

        # Handle special ESL Capable section
        if title == "ESL Capable":
            message_parts.extend([
                f"❓ There are {len(plugins)} plugins that can be given the ESL flag. This can be done with\n",
                "  the SimpleESLify script to avoid reaching the plugin limit (254 esm/esp).\n",
                "  SimpleESLify: https://www.nexusmods.com/skyrimspecialedition/mods/27568\n  -----\n",
            ])

        # Add any matching warnings from settings
        message_parts.extend([warning_text for warning_name, warning_text in wrye_warnings.items() if warning_name in title])

        # List plugins (except for special sections)
        if title not in {"ESL Capable", "Active Plugins:"}:
            message_parts.extend([f"    > {plugin}\n" for plugin in plugins])

    return message_parts


def extract_plugins_from_section(section: PageElement) -> list[str]:
    """
    Extracts plugin entries from a section in the Wrye Bash report.

    Args:
        section: BeautifulSoup PageElement (h3) containing the section

    Returns:
        List of plugin entries
    """
    plugins: list[str] = []
    for paragraph in section.find_next_siblings("p"):
        # Stop if we've moved to a different section
        if paragraph.find_previous_sibling("h3") != section:
            break

        # Process the plugin entry
        text: str = paragraph.get_text().strip().replace("•\xa0 ", "")
        if any(ext in text for ext in (".esp", ".esl", ".esm")):
            plugins.append(text)

    return plugins


def format_section_header(title: str) -> str:
    """
    Formats a section title with decorative equals signs.

    Args:
        title: The section title to format

    Returns:
        Formatted section header string
    """
    if len(title) < 32:
        diff: int = 32 - len(title)
        left: int = diff // 2
        right: int = diff - left
        return f"\n   {'=' * left} {title} {'=' * right}\n"
    return title

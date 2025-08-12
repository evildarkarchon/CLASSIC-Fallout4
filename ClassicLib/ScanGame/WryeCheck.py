from pathlib import Path

# noinspection PyProtectedMember
from bs4 import BeautifulSoup, PageElement

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.FileIOCore import read_file_sync
from ClassicLib.YamlSettingsCache import yaml_settings


def scan_wryecheck() -> str:
    """
    Scans the Wrye Bash plugin checker report for detected problems and generates
    a detailed analysis message. The function reads specific settings for the check
    from a YAML configuration file and validates the presence of a plugin check
    HTML report. If the report exists, it is parsed and a summary message is
    constructed with detailed resources and guidance links. If the report is
    missing, an optional warning message is returned instead.

    Parameters: None

    Returns:
        str: The generated analysis message detailing the contents of the plugin
             checker report or an optional warning message if the report is
             missing.

    Raises:
        ValueError: If the required warnings setting related to the Wrye Bash report
                    is not found in the YAML configuration file.
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
    Parses a Wrye Bash report in HTML format and extracts relevant messages and plugin details.

    This function reads a Wrye Bash plugin analysis report in the form of an HTML file,
    extracts and processes relevant data concerning plugins and warnings. The data is formatted
    into a list of strings, which may include sections, warnings, and lists of plugins,
    based on the content of the file and a provided dictionary of warning messages.

    Arguments:
        report_path (Path): The path to the Wrye Bash report file in HTML format.
        wrye_warnings (dict[str, str]): A dictionary mapping warning names to their respective warning messages.

    Returns:
        list[str]: A list of formatted message strings containing details from the report and warnings.
    """
    message_parts: list[str] = []

    # Read and parse HTML file
    html_content = read_file_sync(report_path)
    soup: BeautifulSoup = BeautifulSoup(html_content, "html.parser")

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
    Extracts plugin file names from a specified section of a web page.

    Traverses paragraphs following a given section header to collect
    plugin file names based on their respective extensions. Stops processing
    if a paragraph belongs to a different section.

    Parameters:
    section (PageElement): The header element representing the section from
    which plugins are to be extracted.

    Returns:
    list[str]: A list of plugin file names found within the given section, where
    each file name must contain one of the following extensions: .esp, .esl, or .esm.
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
    Formats a section header with adjustable padding to center-align the title.
    If the title is shorter than 32 characters, it adds equal padding on both
    sides to ensure consistent alignment. For titles longer than 32 characters,
    it directly returns the title without any modification.

    Parameters:
        title (str): The title string to be formatted as a section header.

    Returns:
        str: The formatted section header with or without applied padding.
    """
    if len(title) < 32:
        diff: int = 32 - len(title)
        left: int = diff // 2
        right: int = diff - left
        return f"\n   {'=' * left} {title} {'=' * right}\n"
    return title

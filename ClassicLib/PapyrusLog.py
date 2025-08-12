# ================================================
# PAPYRUS MONITORING / LOGGING
# ================================================
from pathlib import Path

import chardet

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import yaml_settings


def papyrus_logging() -> tuple[str, int]:
    """
    Analyzes Papyrus log files, extracting various statistics and compiling a summary.

    This function reads a Papyrus log file, if available, and computes key data such
    as the total number of dumps, stacks, warnings, and errors present in the log.
    It also calculates the ratio of dumps to stacks. If the log file is not found,
    the function provides user guidance on enabling and locating Papyrus logging.

    Returns:
        tuple[str, int]: A tuple containing a formatted string with log analysis
        details and the total count of dumps extracted from the log.

    Raises:
        ValueError: If encoding detection fails or returns a None value from the
        chardet library when reading the log file's bytes.
    """
    message_list: list[str] = []
    papyrus_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_PapyrusLog")

    count_dumps = count_stacks = count_warnings = count_errors = 0
    if papyrus_path and papyrus_path.exists():
        papyrus_encoding: str | None = chardet.detect(papyrus_path.read_bytes())["encoding"]
        with papyrus_path.open(encoding=papyrus_encoding, errors="ignore") as papyrus_log:
            papyrus_data: list[str] = papyrus_log.readlines()
        for line in papyrus_data:
            if "Dumping Stacks" in line:
                count_dumps += 1
            elif "Dumping Stack" in line:
                count_stacks += 1
            elif " warning: " in line:
                count_warnings += 1
            elif " error: " in line:
                count_errors += 1

        ratio: float = 0.0 if count_dumps == 0 else count_dumps / count_stacks

        message_list.extend((
            f"NUMBER OF DUMPS    : {count_dumps}\n",
            f"NUMBER OF STACKS   : {count_stacks}\n",
            f"DUMPS/STACKS RATIO : {round(ratio, 3)}\n",  # pyrefly: ignore
            f"NUMBER OF WARNINGS : {count_warnings}\n",
            f"NUMBER OF ERRORS   : {count_errors}\n",
        ))
    else:
        message_list.extend((
            "[!] ERROR : UNABLE TO FIND *Papyrus.0.log* (LOGGING IS DISABLED OR YOU DIDN'T RUN THE GAME)\n",
            "ENABLE PAPYRUS LOGGING MANUALLY OR WITH BETHINI AND START THE GAME TO GENERATE THE LOG FILE\n",
            "BethINI Link | Use Manual Download : https://www.nexusmods.com/site/mods/631?tab=files\n",
        ))

    message_output: str = "".join(message_list)  # Debug print
    return message_output, count_dumps

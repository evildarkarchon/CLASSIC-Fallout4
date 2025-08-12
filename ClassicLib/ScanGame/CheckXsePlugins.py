from pathlib import Path
from typing import TypedDict

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import NG_VERSION, NULL_VERSION, OG_VERSION, VR_VERSION, YAML, Version
from ClassicLib.Util import get_game_version
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class AddressLibVersionInfo(TypedDict):
    version_const: Version
    filename: str
    description: str
    url: str


ALL_ADDRESS_LIB_INFO: dict[str, AddressLibVersionInfo] = {
    "VR": {
        "version_const": VR_VERSION,
        "filename": "version-1-2-72-0.csv",
        "description": "Virtual Reality (VR) version",
        "url": "https://www.nexusmods.com/fallout4/mods/64879?tab=files",
    },
    "OG": {
        "version_const": OG_VERSION,
        "filename": "version-1-10-163-0.bin",
        "description": "Non-VR (Regular) version",
        "url": "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
    },
    "NG": {
        "version_const": NG_VERSION,
        "filename": "version-1-10-984-0.bin",
        "description": "Non-VR (New Game) version",
        "url": "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
    },
}


def _determine_relevant_versions(is_vr_mode: bool) -> tuple[list[AddressLibVersionInfo], list[AddressLibVersionInfo]]:
    """Determines correct and wrong Address Library versions based on VR mode."""
    if is_vr_mode:
        correct_versions: list = [ALL_ADDRESS_LIB_INFO["VR"]]
        wrong_versions: list = [ALL_ADDRESS_LIB_INFO["OG"], ALL_ADDRESS_LIB_INFO["NG"]]
    else:
        correct_versions = [ALL_ADDRESS_LIB_INFO["OG"], ALL_ADDRESS_LIB_INFO["NG"]]
        wrong_versions = [ALL_ADDRESS_LIB_INFO["VR"]]
    return correct_versions, wrong_versions


def _format_game_version_not_detected_message() -> list[str]:
    """Formats message for when game version cannot be detected."""
    return [
        "❓ NOTICE : Unable to locate Address Library\n",
        "  If you have Address Library installed, please check the path in your settings.\n",
        "  If you don't have it installed, you can find it on the Nexus.\n",
        f"  Link: Regular: {ALL_ADDRESS_LIB_INFO['OG']['url']} or VR: {ALL_ADDRESS_LIB_INFO['VR']['url']}\n-----\n",
    ]


def _format_plugins_path_not_found_message() -> list[str]:
    """Formats message for when plugins path is not found in settings."""
    return ["❌ ERROR: Could not locate plugins folder path in settings\n-----\n"]


def _format_correct_address_lib_message() -> list[str]:
    """Formats message for when the correct Address Library version is found."""
    return ["✔️ You have the correct version of the Address Library file!\n-----\n"]


def _format_wrong_address_lib_message(correct_version_info: AddressLibVersionInfo) -> list[str]:
    """Formats message for when a wrong Address Library version is found."""
    return [
        "❌ CAUTION: You have installed the wrong version of the Address Library file!\n",
        f"  Remove the current Address Library file and install the {correct_version_info['description']}.\n",
        f"  Link: {correct_version_info['url']}\n-----\n",
    ]


def _format_address_lib_not_found_message(correct_version_info: AddressLibVersionInfo) -> list[str]:
    """Formats message for when Address Library file is not found."""
    return [
        "❓ NOTICE: Address Library file not found\n",
        f"  Please install the {correct_version_info['description']} for proper functionality.\n",
        f"  Link: {correct_version_info['url']}\n-----\n",
    ]


def check_xse_plugins() -> str:
    """
    Checks the XSE plugins for compatibility and addresses potential issues.

    This function verifies the existence and compatibility of specific plugin
    versions in the designated plugins folder for the game. It determines
    compatibility, handles cases where the game executable or plugins path is not
    found, and provides appropriate messages based on the analysis.

    Returns:
        str: A message detailing the result of the compatibility check. The message
        conveys information about the presence of correct plugin versions, incorrect
        plugin versions, or the absence of plugins.

    Raises:
        None
    """
    message_list: list[str]

    plugins_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Plugins")

    game_exe_path_str: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_File_EXE")
    if not game_exe_path_str:
        # Handle case where game exe path string is not found, though original code implies it's casted
        # This case wasn't explicitly handled for NULL_VERSION trigger in original, but good practice
        message_list = _format_game_version_not_detected_message()  # Or a more specific error
        return "".join(message_list)

    game_version: Version = get_game_version(Path(game_exe_path_str))

    if game_version == NULL_VERSION:
        message_list = _format_game_version_not_detected_message()
        return "".join(message_list)

    if not plugins_path:
        message_list = _format_plugins_path_not_found_message()
        return "".join(message_list)

    is_vr_mode: bool | None = classic_settings(bool, "VR Mode")
    # Ensure is_vr_mode is not None, provide a default if necessary or handle error
    if is_vr_mode is None:
        # Fallback or error handling if VR mode setting is missing
        # For this example, let's assume a default or raise an error if critical
        # This case was not explicitly in the original, but good for robustness
        is_vr_mode = False  # Defaulting to non-VR if setting is missing

    correct_versions, wrong_versions = _determine_relevant_versions(is_vr_mode)

    correct_version_exists: bool = any(plugins_path.joinpath(version["filename"]).exists() for version in correct_versions)
    wrong_version_exists: bool = any(plugins_path.joinpath(version["filename"]).exists() for version in wrong_versions)

    if correct_version_exists:
        message_list = _format_correct_address_lib_message()
    elif wrong_version_exists:
        message_list = _format_wrong_address_lib_message(correct_versions[0])
    else:
        message_list = _format_address_lib_not_found_message(correct_versions[0])

    return "".join(message_list)

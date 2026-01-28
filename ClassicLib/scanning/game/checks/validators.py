"""Validation and configuration methods for handling game mod scanning.

This module provides functionality to fetch and cache scanning settings, as well
as to generate standardized issue messages for mod scan reports. The purpose is
to assist in identifying and resolving issues in game mods, ensuring compatibility
and stability during usage.
"""

from pathlib import Path

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import get_vr
from ClassicLib.io.yaml import classic_settings_async, yaml_settings_async


class ScanValidators:
    """Manage and provide scan validation utilities for modding.

    This class provides validation mechanisms such as retrieving scan settings
    and standardized issue messages for mod scanning reports. The results of
    these operations are cached to optimize performance during the lifetime
    of the process.
    """

    def __init__(self) -> None:
        """Initialize an instance of the class."""
        self._scan_settings_cache: tuple[str, dict[str, set[str]], Path | None] | None = None
        self._issue_messages_cache: dict[tuple[str, str], dict[str, list[str]]] = {}

    async def get_scan_settings(self) -> tuple[str, dict[str, set[str]], Path | None]:
        """Retrieve and caches scanning settings required for the application.

        This method gathers scanning settings information, caching it for further use
        to enhance performance. The settings include an acronym, details of hashed
        script files, and the path to the mods folder. If cached settings already
        exist, they are immediately returned to avoid redundant operations. Otherwise,
        the method facilitates fetching and caching of new settings data.

        Returns:
            tuple[str, dict[str, set[str]], Path | None]: A tuple containing the acronym as
                a string, hashed script files as a dictionary (script filename -> set of valid
                hashes), and the mods folder path as a `Path` object or `None`.

        """
        # Use cached value if available
        if self._scan_settings_cache is not None:
            return self._scan_settings_cache

        # Get XSE acronym from YAML (still needed for display purposes)
        xse_acronym_setting: str | None = await yaml_settings_async(str, YAML.Game, f"Game{get_vr()}_Info.XSE_Acronym")
        xse_acronym: str = xse_acronym_setting if isinstance(xse_acronym_setting, str) else "XSE"

        # Get script hashes from VersionRegistry
        from ClassicLib.support.versions import get_version_registry

        registry = get_version_registry()
        is_vr = get_vr() == "VR"
        xse_scriptfiles: dict[str, set[str]] = registry.get_all_script_hashes("Fallout4", is_vr)

        # Get mods path
        mod_path: Path | None = await classic_settings_async(Path, "MODS Folder Path")

        # Cache the result
        self._scan_settings_cache = (xse_acronym, xse_scriptfiles, mod_path)
        return self._scan_settings_cache

    def get_issue_messages(self, xse_acronym: str, mode: str) -> dict[str, list[str]]:
        """Retrieve issue messages based on a combination of script engine acronym and mode, with details
        of identified problems and recommendations. The issue messages provide detailed explanations
        for common mod issues and are categorized based on texture, sound formats, and other
        potential conflicts.

        The function prioritizes cached data for performance optimization and caches new results after
        processing. Depending on the mode ('unpacked' or 'archived'), it includes specific messages
        pertinent to the corresponding mode while retaining a base set of messages.

        Args:
            xse_acronym (str): Acronym representing the script extender engine.
            mode (str): Mode in which the issues are being checked, such as 'unpacked' or 'archived'.

        Returns:
            dict[str, list[str]]: A dictionary where keys are issue categories, and values are lists of
            associated warning or error messages.

        """
        # Check cache first
        cache_key = (xse_acronym, mode)
        if cache_key in self._issue_messages_cache:
            return self._issue_messages_cache[cache_key]
        base_messages = {
            "tex_dims": [
                "\n**⚠️ DDS DIMENSIONS ARE NOT DIVISIBLE BY 2 ⚠️**\n",
                "▶️ Any mods that have texture files with incorrect dimensions\n",
                "  are very likely to cause a *Texture (DDS) Crash*. For further details,\n",
                "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
            ],
            "tex_frmt": [
                "\n**❓ TEXTURE FILES HAVE INCORRECT FORMAT, SHOULD BE DDS ❓**\n",
                "▶️ Any files with an incorrect file format will not work.\n",
                "  Mod authors should convert these files to their proper game format.\n",
                "  If possible, notify the original mod authors about these problems.\n\n",
            ],
            "snd_frmt": [
                "\n**❓ SOUND FILES HAVE INCORRECT FORMAT, SHOULD BE XWM OR WAV ❓**\n",
                "▶️ Any files with an incorrect file format will not work.\n",
                "  Mod authors should convert these files to their proper game format.\n",
                "  If possible, notify the original mod authors about these problems.\n\n",
            ],
        }

        # Add mode-specific messages
        if mode == "unpacked":
            base_messages.update({
                "xse_file": [
                    f"\n**⚠️ FOLDERS CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️**\n",
                    "▶️ Any mods with copies of original Script Extender files\n",
                    "  may cause script related problems or crashes.\n\n",
                ],
                "previs": [
                    "\n**⚠️ FOLDERS CONTAIN LOOSE PRECOMBINE / PREVIS FILES ⚠️**\n",
                    "▶️ Any mods that contain custom precombine/previs files\n",
                    "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n",
                    "  Otherwise, see if there is a PRP patch available for these mods.\n\n",
                ],
                "animdata": [
                    "\n**❓ FOLDERS CONTAIN CUSTOM ANIMATION FILE DATA ❓**\n",
                    "▶️ Any mods that have their own custom Animation File Data\n",
                    "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
                    "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
                ],
                "cleanup": ["\n**📄 DOCUMENTATION FILES MOVED TO 'CLASSIC Backup\\Cleaned Files' 📄**\n"],
            })
        else:  # archived
            base_messages.update({
                "xse_file": [
                    f"\n**⚠️ BA2 ARCHIVES CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️**\n",
                    "▶️ Any mods with copies of original Script Extender files\n",
                    "  may cause script related problems or crashes.\n\n",
                ],
                "ba2_frmt": [
                    "\n**❓ BA2 ARCHIVES HAVE INCORRECT FORMAT, SHOULD BE BTDX-GNRL OR BTDX-DX10 ❓**\n",
                    "▶️ Any files with an incorrect file format will not work.\n",
                    "  Mod authors should convert these files to their proper game format.\n",
                    "  If possible, notify the original mod authors about these problems.\n\n",
                ],
            })

        # Cache and return
        self._issue_messages_cache[cache_key] = base_messages
        return base_messages

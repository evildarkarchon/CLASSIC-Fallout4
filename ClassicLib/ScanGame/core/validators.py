"""Validation and configuration methods for ScanGame operations."""

from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class ScanValidators:
    """Validation and configuration methods for game scanning."""

    def __init__(self) -> None:
        """Initialize validators with caching."""
        self._scan_settings_cache: tuple[str, dict[str, str], Path | None] | None = None
        self._issue_messages_cache: dict[tuple[str, str], dict[str, list[str]]] = {}

    def get_scan_settings(self) -> tuple[str, dict[str, str], Path | None]:
        """
        Gets common settings used by mod scanning functions.
        Results are cached for the lifetime of the process.

        Returns:
            tuple: (xse_acronym, xse_scriptfiles, mod_path)
        """
        # Use cached value if available
        if self._scan_settings_cache is not None:
            return self._scan_settings_cache

        # Get XSE settings - YamlSettingsCache already caches these
        xse_acronym_setting: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
        xse_scriptfiles_setting: dict[str, str] | None = yaml_settings(
            dict[str, str], YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_HashedScripts"
        )
        xse_acronym: str = xse_acronym_setting if isinstance(xse_acronym_setting, str) else "XSE"
        xse_scriptfiles: dict[str, str] = xse_scriptfiles_setting if isinstance(xse_scriptfiles_setting, dict) else {}

        # Get mods path
        mod_path: Path | None = classic_settings(Path, "MODS Folder Path")

        # Cache the result
        self._scan_settings_cache = (xse_acronym, xse_scriptfiles, mod_path)
        return self._scan_settings_cache

    def get_issue_messages(self, xse_acronym: str, mode: str) -> dict[str, list[str]]:
        """
        Returns standardized issue messages for mod scan reports.
        Results are cached for the lifetime of the process.

        Args:
            xse_acronym: Script extender acronym from settings
            mode: Either "unpacked" or "archived"

        Returns:
            dict: Dictionary of issue types and their message templates
        """
        # Check cache first
        cache_key = (xse_acronym, mode)
        if cache_key in self._issue_messages_cache:
            return self._issue_messages_cache[cache_key]
        base_messages = {
            "tex_dims": [
                "\n# ⚠️ DDS DIMENSIONS ARE NOT DIVISIBLE BY 2 ⚠️\n",
                "▶️ Any mods that have texture files with incorrect dimensions\n",
                "  are very likely to cause a *Texture (DDS) Crash*. For further details,\n",
                "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
            ],
            "tex_frmt": [
                "\n# ❓ TEXTURE FILES HAVE INCORRECT FORMAT, SHOULD BE DDS ❓\n",
                "▶️ Any files with an incorrect file format will not work.\n",
                "  Mod authors should convert these files to their proper game format.\n",
                "  If possible, notify the original mod authors about these problems.\n\n",
            ],
            "snd_frmt": [
                "\n# ❓ SOUND FILES HAVE INCORRECT FORMAT, SHOULD BE XWM OR WAV ❓\n",
                "▶️ Any files with an incorrect file format will not work.\n",
                "  Mod authors should convert these files to their proper game format.\n",
                "  If possible, notify the original mod authors about these problems.\n\n",
            ],
        }

        # Add mode-specific messages
        if mode == "unpacked":
            base_messages.update({
                "xse_file": [
                    f"\n# ⚠️ FOLDERS CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️\n",
                    "▶️ Any mods with copies of original Script Extender files\n",
                    "  may cause script related problems or crashes.\n\n",
                ],
                "previs": [
                    "\n# ⚠️ FOLDERS CONTAIN LOOSE PRECOMBINE / PREVIS FILES ⚠️\n",
                    "▶️ Any mods that contain custom precombine/previs files\n",
                    "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n",
                    "  Otherwise, see if there is a PRP patch available for these mods.\n\n",
                ],
                "animdata": [
                    "\n# ❓ FOLDERS CONTAIN CUSTOM ANIMATION FILE DATA ❓\n",
                    "▶️ Any mods that have their own custom Animation File Data\n",
                    "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
                    "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
                ],
                "cleanup": ["\n# 📄 DOCUMENTATION FILES MOVED TO 'CLASSIC Backup\\Cleaned Files' 📄\n"],
            })
        else:  # archived
            base_messages.update({
                "xse_file": [
                    f"\n# ⚠️ BA2 ARCHIVES CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️\n",
                    "▶️ Any mods with copies of original Script Extender files\n",
                    "  may cause script related problems or crashes.\n\n",
                ],
                "previs": [
                    "\n# ⚠️ BA2 ARCHIVES CONTAIN CUSTOM PRECOMBINE / PREVIS FILES ⚠️\n",
                    "▶️ Any mods that contain custom precombine/previs files\n",
                    "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n",
                    "  Otherwise, see if there is a PRP patch available for these mods.\n\n",
                ],
                "animdata": [
                    "\n# ❓ BA2 ARCHIVES CONTAIN CUSTOM ANIMATION FILE DATA ❓\n",
                    "▶️ Any mods that have their own custom Animation File Data\n",
                    "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
                    "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
                ],
                "ba2_frmt": [
                    "\n# ❓ BA2 ARCHIVES HAVE INCORRECT FORMAT, SHOULD BE BTDX-GNRL OR BTDX-DX10 ❓\n",
                    "▶️ Any files with an incorrect file format will not work.\n",
                    "  Mod authors should convert these files to their proper game format.\n",
                    "  If possible, notify the original mod authors about these problems.\n\n",
                ],
            })

        # Cache and return
        self._issue_messages_cache[cache_key] = base_messages
        return base_messages

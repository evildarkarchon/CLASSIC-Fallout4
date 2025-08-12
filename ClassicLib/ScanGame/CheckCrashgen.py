# ================================================
# CHECK BUFFOUT CONFIG SETTINGS
# ================================================
from pathlib import Path
from typing import Any, cast

from ClassicLib import GlobalRegistry, msg_error
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanGame.Config import mod_toml_config
from ClassicLib.YamlSettingsCache import yaml_settings


class CrashgenChecker:
    """Checks and validates settings for Crash Generator (Buffout4) configuration."""

    def __init__(self) -> None:
        self.message_list: list[str] = []
        self.plugins_path = self._get_plugins_path()
        self.crashgen_name = self._get_crashgen_name()
        self.config_file = self._find_config_file()
        self.installed_plugins = self._detect_installed_plugins()

    @staticmethod
    def _get_plugins_path() -> Path | None:
        """Get plugins path from settings and ensure it's a Path object."""
        plugins_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Plugins")
        return plugins_path

    @staticmethod
    def _get_crashgen_name() -> str:
        """Get crash generator name from settings."""
        crashgen_name_setting: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.CRASHGEN_LogName")
        return crashgen_name_setting if isinstance(crashgen_name_setting, str) else "Buffout4"

    def _find_config_file(self) -> Path | None:
        """Find and determine which config file to use."""
        if not self.plugins_path:
            return None

        crashgen_toml_og: Path = self.plugins_path / "Buffout4/config.toml"
        crashgen_toml_vr: Path = self.plugins_path / "Buffout4.toml"

        # Check for missing config files
        if (crashgen_toml_og and not crashgen_toml_og.exists()) or (crashgen_toml_vr and not crashgen_toml_vr.exists()):
            self.message_list.extend([
                f"# ❌ CAUTION : {self.crashgen_name.upper()} TOML SETTINGS FILE NOT FOUND! #\n",
                f"Please recheck your {self.crashgen_name} installation and delete any obsolete files.\n-----\n",
            ])

        # Check for duplicate config files
        if crashgen_toml_og.is_file() and crashgen_toml_vr.is_file():
            self.message_list.extend([
                f"# ❌ CAUTION : BOTH VERSIONS OF {self.crashgen_name.upper()} TOML SETTINGS FILES WERE FOUND! #\n",
                f"When editing {self.crashgen_name} toml settings, make sure you are editing the correct file.\n",
                f"Please recheck your {self.crashgen_name} installation and delete any obsolete files.\n-----\n",
            ])

        # Determine which config file to use
        if crashgen_toml_og.is_file():
            return crashgen_toml_og
        if crashgen_toml_vr.is_file():
            return crashgen_toml_vr
        return None

    def _detect_installed_plugins(self) -> set[str]:
        """Check for installed mods by examining DLL files in the plugins directory."""
        xse_files: set[str] = set()
        if self.plugins_path and self.plugins_path.exists():
            try:
                xse_files = {file.name.lower() for file in self.plugins_path.iterdir()}
            except (PermissionError, OSError) as e:
                logger.debug(f"Error accessing plugins directory: {e}")
                msg_error(f"Cannot access plugins directory: {e}")
        return xse_files

    def has_plugin(self, plugin_names: list[str]) -> bool:
        """
        Determines if any of the specified plugins are present in the installed plugins list.

        The method checks if at least one plugin from the given list of plugin names exists
        in the installed plugins list.

        Args:
            plugin_names (list[str]): A list of plugin names to check against the
                installed plugins.

        Returns:
            bool: True if any of the provided plugin names is found in the installed
                plugins, otherwise False.
        """
        return any(plugin in self.installed_plugins for plugin in plugin_names)

    def _get_settings_to_check(self) -> list[dict[str, Any]]:
        """Define configuration settings to check with their requirements and desired states."""
        if GlobalRegistry.get_game() != "Fallout4":
            return []

        has_xcell = self.has_plugin(["x-cell-fo4.dll", "x-cell-og.dll", "x-cell-ng2.dll"])
        has_achievements = self.has_plugin(["achievements.dll", "achievementsmodsenablerloader.dll"])
        has_looksmenu = any("f4ee" in file for file in self.installed_plugins)

        return [
            # Patches section settings
            {
                "section": "Patches",
                "key": "Achievements",
                "name": "Achievements",
                "condition": has_achievements,
                "desired_value": False,
                "description": "The Achievements Mod and/or Unlimited Survival Mode is installed",
                "reason": f"to prevent conflicts with {self.crashgen_name}",
            },
            {
                "section": "Patches",
                "key": "MemoryManager",
                "name": "Memory Manager",
                "condition": has_xcell,
                "desired_value": False,
                "description": "The X-Cell Mod is installed",
                "reason": "to prevent conflicts with X-Cell",
                "special_case": "bakascrapheap",
            },
            {
                "section": "Patches",
                "key": "HavokMemorySystem",
                "name": "Havok Memory System",
                "condition": has_xcell,
                "desired_value": False,
                "description": "The X-Cell Mod is installed",
                "reason": "to prevent conflicts with X-Cell",
            },
            {
                "section": "Patches",
                "key": "BSTextureStreamerLocalHeap",
                "name": "BS Texture Streamer Local Heap",
                "condition": has_xcell,
                "desired_value": False,
                "description": "The X-Cell Mod is installed",
                "reason": "to prevent conflicts with X-Cell",
            },
            {
                "section": "Patches",
                "key": "ScaleformAllocator",
                "name": "Scaleform Allocator",
                "condition": has_xcell,
                "desired_value": False,
                "description": "The X-Cell Mod is installed",
                "reason": "to prevent conflicts with X-Cell",
            },
            {
                "section": "Patches",
                "key": "SmallBlockAllocator",
                "name": "Small Block Allocator",
                "condition": has_xcell,
                "desired_value": False,
                "description": "The X-Cell Mod is installed",
                "reason": "to prevent conflicts with X-Cell",
            },
            {
                "section": "Patches",
                "key": "ArchiveLimit",
                "name": "Archive Limit",
                "condition": self.config_file and "buffout4/config.toml" in str(self.config_file).lower(),
                "desired_value": False,
                "description": "Archive Limit is enabled",
                "reason": "to prevent crashes",
            },
            {
                "section": "Patches",
                "name": "MaxStdIO",
                "key": "MaxStdIO",
                "condition": False,  # This is a placeholder
                "desired_value": 2048,
                "description": "MaxStdIO is set to a low value",
                "reason": "to improve performance",
            },
            # Compatibility section settings
            {
                "section": "Compatibility",
                "key": "F4EE",
                "name": "F4EE (Looks Menu)",
                "condition": has_looksmenu,
                "desired_value": True,
                "description": "Looks Menu is installed, but F4EE parameter is set to FALSE",
                "reason": "to prevent bugs and crashes from Looks Menu",
            },
        ]

    def _process_settings(self) -> None:
        """Process each setting and make necessary adjustments."""
        assert self.config_file is not None, "Config file must be checked by the caller before processing settings."
        has_bakascrapheap: bool = "bakascrapheap.dll" in self.installed_plugins

        for setting in self._get_settings_to_check():
            # Get current setting value
            current_value: Any | None = mod_toml_config(self.config_file, cast("str", setting["section"]), cast("str", setting["key"]))

            # Special case for BakaScrapHeap with MemoryManager
            if setting.get("special_case") == "bakascrapheap" and has_bakascrapheap and current_value:
                self.message_list.extend([
                    f"# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but is redundant with {self.crashgen_name} #\n",
                    f" FIX: Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {self.crashgen_name}.\n-----\n",
                ])
                continue

            # Check if condition is met and setting needs changing
            if setting["condition"] and current_value != setting["desired_value"]:
                self.message_list.extend([
                    f"# ❌ CAUTION : {setting['description']}, but {setting['name']} parameter is set to {current_value} #\n",
                    f"    Auto Scanner will change this parameter to {setting['desired_value']} {setting['reason']}.\n-----\n",
                ])
                # Apply the change
                mod_toml_config(
                    cast("Path", self.config_file),
                    cast("str", setting["section"]),
                    cast("str", setting["key"]),
                    cast("str | bool | int | None", setting["desired_value"]),
                )
                logger.info(f"Changed {setting['name']} from {current_value} to {setting['desired_value']}")
            else:
                # Setting is already correctly configured
                self.message_list.append(
                    f"✔️ {setting['name']} parameter is correctly configured in your {self.crashgen_name} settings!\n-----\n"
                )

    def check(self) -> str:
        """
        Checks the settings for the given configuration file and generates an appropriate
        message based on the existence of the config file.

        This method inspects the application's state to verify if a configuration file
        specific to a crash generator exists. If the config file is not found, it appends
        a series of pre-defined messages to the message list, informing the user of the
        issue without raising an exception. If the config file exists, it logs an
        information message indicating the start of the settings check and invokes the
        internal processing for settings. At the end, the cumulative message list is
        returned as a concatenated string.

        Returns:
            str: The concatenated message list containing either the notice regarding a
            missing configuration file or any messages resulting from the settings check.
        """
        # If no config file found, return message without raising exception
        if not self.config_file:
            self.message_list.extend([
                f"# [!] NOTICE : Unable to find the {self.crashgen_name} config file, settings check will be skipped. #\n",
                f"  To ensure this check doesn't get skipped, {self.crashgen_name} has to be installed manually.\n",
                "  [ If you are using Mod Organizer 2, you need to run CLASSIC through a shortcut in MO2. ]\n-----\n",
            ])
            return "".join(self.message_list)

        logger.info(f"Checking {self.crashgen_name} settings in {self.config_file}")
        self._process_settings()
        return "".join(self.message_list)


def check_crashgen_settings() -> str:
    """
    Checks the crash generation settings using a CrashgenChecker instance.

    This function creates an instance of the CrashgenChecker class and
    uses it to check the current crash generation settings. The result
    of the check is returned as a string.

    Returns:
        str: The result of the crash generation settings check.
    """
    checker: CrashgenChecker = CrashgenChecker()
    return checker.check()

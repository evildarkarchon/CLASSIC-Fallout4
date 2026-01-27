"""A module to check and validate settings for Crash Generator (Buffout4) configuration.

This module contains the CrashgenChecker class, which is used to locate and verify
the configuration files for Buffout4 and ensure that the settings are appropriate
based on the installed plugins and given requirements. The class also handles the
detection of installed plugins and evaluates the correctness of the configuration.
"""

from pathlib import Path
from typing import Any, cast

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import get_game, get_vr
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.messaging import msg_error
from ClassicLib.scanning.game.config import mod_toml_config
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue


class CrashgenChecker:
    """Handle checking and validating the installation of crash generation mods, their configurations,
    and compatibility with installed plugins.

    This class is designed to manage the setup and requirements for crash generation tools, ensuring
    correct configuration files are used, detecting installed plugins, and checking for potential
    conflicts. It provides functionality to validate mod settings and compatibility for proper behavior.

    Attributes:
        message_list (list[str]): List of messages for logging issues, warnings, or errors during the
            validation process.
        plugins_path (Path | None): Path to the plugins directory extracted from the settings.
        crashgen_name (str): Name of the crash generator mod based on the settings or default value.
        config_file (Path | None): Path to the configuration file being used by the crash generator mod.
        installed_plugins (set[str]): Set of installed plugins (DLL files) detected in the plugins directory.

    """

    def __init__(self) -> None:
        """Initialize the class and sets up initial attributes for managing message list and
        plugin configurations.

        Raises:
            FileNotFoundError: If the configuration file is not found during initialization.

        """
        self.message_list: list[str] = []
        self.plugins_path = self._get_plugins_path()
        self.crashgen_name = self._get_crashgen_name()
        self.config_file = self._find_config_file()
        self.installed_plugins = self._detect_installed_plugins()

    @staticmethod
    def _get_plugins_path() -> Path | None:
        """Get the path to the plugins directory if available.

        This method retrieves the path to the plugins folder for a specific game configuration
        based on the provided YAML settings and the VR version fetched from the global registry.
        It returns the resolved path as a `Path` object or `None` if the path is unavailable.

        Returns:
            Path | None: The path to the plugins directory or `None` if unavailable.

        """
        plugins_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{get_vr()}_Info.Game_Folder_Plugins")
        return plugins_path

    @staticmethod
    def _get_crashgen_name() -> str:
        """Return the crash generator name based on the game's YAML settings.

        If a valid string value for `CRASHGEN_LogName` is provided in the game's YAML
        settings, it will be returned. Otherwise, a default value of "Buffout4" is
        returned.

        Returns:
            str: The crash generator name derived from the YAML settings or the
            default "Buffout4" string.

        """
        crashgen_name_setting: str | None = yaml_settings(str, YAML.Game, f"Game{get_vr()}_Info.CRASHGEN_LogName")
        return crashgen_name_setting if isinstance(crashgen_name_setting, str) else "Buffout4"

    def _find_config_file(self) -> Path | None:
        """Find the configuration file for the plugin based on the available file paths and
        resolves potential conflicts, such as missing or duplicate configuration files.

        If both configuration file versions are found, an error message is added to the
        message list. If only one valid configuration file is found, returns that file's path.
        If no configuration files are found, returns None.

        Returns:
            Path | None: The path to the configuration file, or None if no
            valid configuration file is found.

        """
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
        """Detect installed plugins by scanning the specified plugins directory.

        This method identifies the installed plugins by iterating through files in the plugins
        directory specified by the `plugins_path` attribute. It collects the names of the files
        in lowercase and returns them as a set of strings. If the directory does not exist or
        cannot be accessed due to permissions or other errors, it handles these scenarios
        gracefully by logging the error and showing an error message.

        Returns:
            set[str]: A set containing the lowercase names of the files in the plugins
            directory.

        Raises:
            PermissionError: If the plugins directory cannot be accessed due to permissions.
            OSError: If an operating system-related error occurs while accessing the
            plugins directory.

        """
        xse_files: set[str] = set()
        if self.plugins_path and self.plugins_path.exists():
            try:
                xse_files = {file.name.lower() for file in self.plugins_path.iterdir()}
            except (PermissionError, OSError) as e:
                logger.debug(f"Error accessing plugins directory: {e}")
                msg_error(f"Cannot access plugins directory: {e}")
        return xse_files

    def has_plugin(self, plugin_names: list[str]) -> bool:
        """Determine if any of the specified plugins are present in the installed plugins list.

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
        """Retrieve a list of configuration settings to check for compatibility and stability
        based on the installed game, plugins, and specific mod configurations for Fallout 4.
        The method conditionally evaluates the presence of various mods or plugins and returns
        appropriate settings designed to prevent conflicts and ensure proper functionality.

        Returns:
            list[dict[str, Any]]: A list of dictionaries, each representing a setting to check.
            Includes information about configuration sections, keys, conditions, desired values,
            descriptions, and reasons for the suggested changes.

        """
        if get_game() != "Fallout4":
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

    @staticmethod
    def _detect_toml_issue(
        config_file: Path,
        setting: dict[str, Any],
        current_value: Any,
    ) -> ConfigIssue | None:
        """Detect a TOML configuration issue without modifying the file.

        Args:
            config_file: Path to the TOML configuration file.
            setting: Dictionary containing setting information (name, section, key,
                desired_value, description, reason).
            current_value: Current value in the TOML file.

        Returns:
            ConfigIssue if setting doesn't match desired value, None if correct.

        """
        if current_value != setting["desired_value"]:
            description = f"{setting['description']}. {setting['reason']}"
            return ConfigIssue(
                file_path=config_file,
                section=setting["section"],
                setting=setting["key"],
                current_value=str(current_value),
                recommended_value=str(setting["desired_value"]),
                description=description,
                severity="warning",
            )
        return None

    def _detect_settings_issues(self) -> list[ConfigIssue]:
        """Detect configuration issues in TOML settings without modifying files (FCX read-only mode).

        This method follows the FCX read-only pattern established in ScanModInis.py.
        It detects configuration issues and returns them as ConfigIssue objects for
        reporting to the user, but never modifies the configuration files.

        Returns:
            list[ConfigIssue]: List of detected configuration issues.

        Note:
            This replaces the deprecated auto-fix behavior. See CLAUDE.md for FCX mode
            documentation (completed 2025-10-29).

        """
        issues: list[ConfigIssue] = []

        # Type narrowing: config_file is validated by caller before this method is called
        config_file = cast("Path", self.config_file)
        has_bakascrapheap: bool = "bakascrapheap.dll" in self.installed_plugins

        for setting in self._get_settings_to_check():
            # Get current setting value (read-only operation)
            current_value: Any | None = mod_toml_config(config_file, cast("str", setting["section"]), cast("str", setting["key"]))

            # Special case for BakaScrapHeap with MemoryManager
            if setting.get("special_case") == "bakascrapheap" and has_bakascrapheap and current_value:
                issue = ConfigIssue(
                    file_path=config_file,
                    section=setting["section"],
                    setting=setting["key"],
                    current_value=str(current_value),
                    recommended_value=str(setting["desired_value"]),
                    description=f"The Baka ScrapHeap Mod is installed, but is redundant with {self.crashgen_name}. "
                    f"Uninstall the Baka ScrapHeap Mod to prevent conflicts with {self.crashgen_name}.",
                    severity="error",
                )
                issues.append(issue)
                self.message_list.extend([
                    f"# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but is redundant with {self.crashgen_name} #\n",
                    f" FIX: Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {self.crashgen_name}.\n-----\n",
                ])
                continue

            # Check if condition is met and setting needs attention
            if setting["condition"] and current_value != setting["desired_value"]:
                # Detect issue without modifying
                issue = self._detect_toml_issue(config_file, setting, current_value)
                if issue:
                    issues.append(issue)
                    # Build message for backward compatibility
                    self.message_list.extend([
                        f"**❌ CAUTION : {setting['description']}, but {setting['name']} parameter is set to {current_value}**\n",
                        f" FIX: Open {self.crashgen_name}'s TOML file and change {setting['name']} to {setting['desired_value']} {setting['reason']}.\n-----\n",
                    ])
                    logger.info(f"Detected issue: {setting['name']} is {current_value}, recommended: {setting['desired_value']}")
            else:
                # Setting is already correctly configured
                self.message_list.append(
                    f"✔️ {setting['name']} parameter is correctly configured in your {self.crashgen_name} settings!\n-----\n"
                )

        return issues

    def check(self) -> tuple[str, list[ConfigIssue]]:
        """Check the settings for the given configuration file and detects configuration issues.

        This method follows the FCX read-only pattern, detecting configuration issues
        without modifying files. It returns both a formatted message string (for backward
        compatibility) and a list of ConfigIssue objects (for structured reporting).

        Returns:
            tuple[str, list[ConfigIssue]]: A tuple containing:
                - Formatted message string with detected issues and recommendations
                - List of ConfigIssue objects for structured reporting

        Note:
            This method no longer auto-fixes configuration issues. It only detects and
            reports them. See CLAUDE.md for FCX read-only mode documentation.

        """
        # If no config file found, return message without raising exception
        if not self.config_file:
            self.message_list.extend([
                f"# [!] NOTICE : Unable to find the {self.crashgen_name} config file, settings check will be skipped. #\n",
                f"  To ensure this check doesn't get skipped, {self.crashgen_name} has to be installed manually.\n",
                "  [ If you are using Mod Organizer 2, you need to run CLASSIC through a shortcut in MO2. ]\n-----\n",
            ])
            return "".join(self.message_list), []

        logger.info(f"Checking {self.crashgen_name} settings in {self.config_file}")
        issues = self._detect_settings_issues()
        return "".join(self.message_list), issues


def check_crashgen_settings() -> tuple[str, list[ConfigIssue]]:
    """Check the crash generation settings using a CrashgenChecker instance (FCX read-only mode).

    This function creates an instance of the CrashgenChecker class and
    uses it to check the current crash generation settings. It returns both
    a formatted message string and a list of detected configuration issues.

    Returns:
        tuple[str, list[ConfigIssue]]: A tuple containing:
            - Formatted message string with detected issues and recommendations
            - List of ConfigIssue objects for structured reporting

    Note:
        This function no longer auto-fixes issues. It follows the FCX read-only
        pattern established in CLAUDE.md (2025-10-29).

    """
    checker: CrashgenChecker = CrashgenChecker()
    return checker.check()

"""
Settings scanner module for CLASSIC.

This module validates crash generator and mod settings including:
- Buffout 4 configuration settings validation
- Compatibility settings for installed mods
- Memory management parameters checking
- F4EE/Looks Menu configuration verification
"""

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.Util import append_or_extend

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class SettingsScanner:
    """Handles validation of crash generator and mod settings."""

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initialize the settings scanner.

        Args:
            yamldata: Configuration data
        """
        self.yamldata: ClassicScanLogsInfo = yamldata

    def scan_buffout_achievements_setting(
        self, autoscan_report: list[str], xsemodules: set[str], crashgen: dict[str, bool | int | str]
    ) -> None:
        """
        Scans the achievements setting in the configuration for potential conflicts
        and generates a report based on the findings. Checks whether the Achievements
        mod or Unlimited Survival Mode are installed and whether the `Achievements`
        parameter in the configuration is correctly set to avoid conflicts. Updates
        the autoscan report accordingly.

        Args:
            autoscan_report (list[str]): The list used to store the autoscan report,
                updated with messages about the achievements settings.
            xsemodules (set[str]): A set of currently loaded XSE plugin modules.
            crashgen (dict[str, bool | int | str]): A dictionary containing the
                configuration settings for the crash generator. Used to validate
                the "Achievements" key.
        """
        crashgen_achievements: bool | int | str | None = crashgen.get("Achievements")
        if crashgen_achievements and ("achievements.dll" in xsemodules or "unlimitedsurvivalmode.dll" in xsemodules):
            append_or_extend(
                (
                    "# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change Achievements to FALSE, this prevents conflicts with {self.yamldata.crashgen_name}.\n-----\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend(
                f"✔️ Achievements parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                autoscan_report,
            )

    def scan_buffout_memorymanagement_settings(
        self, autoscan_report: list[str], crashgen: dict[str, bool | int | str], has_xcell: bool, has_baka_scrapheap: bool
    ) -> None:
        """
        Analyzes and adjusts memory management settings based on compatibility requirements and installed
        components, updating the report with appropriate success or warning messages. This function checks
        the configuration of the MemoryManager and additional memory-related parameters for compatibility
        with specific mod components such as X-Cell and Baka ScrapHeap.

        Arguments:
            autoscan_report (list[str]): A list containing the current autoscan report to which success or
                warning messages will be appended.
            crashgen (dict[str, bool | int | str]): A dictionary containing the current memory management
                configuration settings from the crashgen's config.
            has_xcell (bool): A flag indicating whether the X-Cell mod is installed.
            has_baka_scrapheap (bool): A flag indicating whether the Baka ScrapHeap mod is installed.

        Returns:
            None
        """
        # Constants for messages and settings
        separator = "\n-----\n"
        success_prefix = "✔️ "
        warning_prefix = "# ❌ CAUTION : "
        fix_prefix = " FIX: "
        crashgen_name: str = self.yamldata.crashgen_name

        def add_success_message(message: str) -> None:
            """Add a success message to the report."""
            append_or_extend(f"{success_prefix}{message}{separator}", autoscan_report)

        def add_warning_message(warning: str, fix: str) -> None:
            """Add a warning message with fix instructions to the report."""
            append_or_extend((f"{warning_prefix}{warning} # \n", f"{fix_prefix}{fix}{separator}"), autoscan_report)

        # Check main MemoryManager setting
        mem_manager_enabled: bool | int | str = crashgen.get("MemoryManager", False)

        # Handle main memory manager configuration
        if mem_manager_enabled:
            if has_xcell:
                add_warning_message(
                    "X-Cell is installed, but MemoryManager parameter is set to TRUE",
                    f"Open {crashgen_name}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with X-Cell.",
                )
            elif has_baka_scrapheap:
                add_warning_message(
                    f"The Baka ScrapHeap Mod is installed, but is redundant with {crashgen_name}",
                    f"Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {crashgen_name}.",
                )
            else:
                add_success_message(f"Memory Manager parameter is correctly configured in your {crashgen_name} settings!")
        elif has_xcell:
            if has_baka_scrapheap:
                add_warning_message(
                    "The Baka ScrapHeap Mod is installed, but is redundant with X-Cell",
                    "Uninstall the Baka ScrapHeap Mod, this prevents conflicts with X-Cell.",
                )
            else:
                add_success_message(
                    f"Memory Manager parameter is correctly configured for use with X-Cell in your {crashgen_name} settings!"
                )
        elif has_baka_scrapheap:
            add_warning_message(
                f"The Baka ScrapHeap Mod is installed, but is redundant with {crashgen_name}",
                f"Uninstall the Baka ScrapHeap Mod and open {crashgen_name}'s TOML file and change MemoryManager to TRUE, this improves performance.",
            )

        # Check additional memory settings for X-Cell compatibility
        if has_xcell:
            memory_settings: dict[str, str] = {
                "HavokMemorySystem": "Havok Memory System",
                "BSTextureStreamerLocalHeap": "BSTextureStreamerLocalHeap",
                "ScaleformAllocator": "Scaleform Allocator",
                "SmallBlockAllocator": "Small Block Allocator",
            }

            for setting_key, display_name in memory_settings.items():
                if crashgen.get(setting_key):
                    add_warning_message(
                        f"X-Cell is installed, but {setting_key} parameter is set to TRUE",
                        f"Open {crashgen_name}'s TOML file and change {setting_key} to FALSE, this prevents conflicts with X-Cell.",
                    )
                else:
                    add_success_message(
                        f"{display_name} parameter is correctly configured for use with X-Cell in your {crashgen_name} settings!"
                    )

    def scan_archivelimit_setting(self, autoscan_report: list[str], crashgen: dict[str, bool | int | str]) -> None:
        """
        Scans and validates the "ArchiveLimit" setting in the provided crash generation configuration.

        This function checks if the "ArchiveLimit" parameter in the `crashgen` dictionary is set and takes appropriate action based
        on its value. Warnings or positive confirmations are appended or extended to the `autoscan_report` list to notify users
        about the configuration status of the "ArchiveLimit" setting.

        Attributes:
            autoscan_report (list[str]): List to store warnings or confirmations regarding the "ArchiveLimit" parameter.
            crashgen (dict[str, bool | int | str]): Dictionary containing crash generation settings, including "ArchiveLimit".

        Args:
            autoscan_report: A list storing messages generated as a result of scanning the "ArchiveLimit" setting.
            crashgen: A dictionary that contains various settings for crash generation configurations.

        Returns:
            None
        """
        crashgen_archivelimit: bool | int | str | None = crashgen.get("ArchiveLimit")
        if crashgen_archivelimit:
            append_or_extend(
                (
                    "# ❌ CAUTION : ArchiveLimit is set to TRUE, this setting is known to cause instability. # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change ArchiveLimit to FALSE.\n-----\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend(
                f"✔️ ArchiveLimit parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                autoscan_report,
            )

    def scan_buffout_looksmenu_setting(
        self, crashgen: dict[str, bool | int | str], autoscan_report: list[str], xsemodules: set[str]
    ) -> None:
        """
        Analyzes the Looksmenu setting in the provided crash generation configuration, ensuring proper compatibility settings.

        Parameters:
            crashgen (dict[str, bool | int | str]): A mapping containing the crash generation settings,
                with keys representing configuration parameters and associated values.
            autoscan_report (list[str]): A list used for appending messages generated by the scan process,
                which can be error notifications, warnings, or confirmations.
            xsemodules (set[str]): A set of module names that indicates the external script extender modules
                available in the current configuration.

        Returns:
            None

        """
        crashgen_f4ee: bool | int | str | None = crashgen.get("F4EE")
        if crashgen_f4ee is not None:
            if not crashgen_f4ee and "f4ee.dll" in xsemodules:
                append_or_extend(
                    (
                        "# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under [Compatibility] is set to FALSE # \n",
                        f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change F4EE to TRUE, this prevents bugs and crashes from Looks Menu.\n-----\n",
                    ),
                    autoscan_report,
                )
            else:
                append_or_extend(
                    f"✔️ F4EE (Looks Menu) parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                    autoscan_report,
                )

    def check_disabled_settings(self, crashgen: dict[str, bool | int | str], autoscan_report: list[str], crashgen_ignore: set[str]) -> None:
        """
        Check disabled settings in crash generation configuration and log notices.

        Examines the provided crash generation settings (`crashgen`) to identify any
        disabled settings that are not present in the `crashgen_ignore` set. If such
        settings are found, it appends or extends the `autoscan_report` list with
        appropriately formatted notice messages.

        Parameters:
            crashgen: dict[str, bool | int | str]
                A dictionary containing crash generation settings, where the key is
                the setting name and the value represents its state or value.
            autoscan_report: list[str]
                A list to which any generated notice messages will be appended.
            crashgen_ignore: set[str]
                A set of setting names that, even if found disabled in `crashgen`,
                should be ignored and no notice should be logged for them.

        Returns:
            None
        """
        if crashgen:
            for setting_name, setting_value in crashgen.items():
                if setting_value is False and setting_name not in crashgen_ignore:
                    append_or_extend(
                        f"* NOTICE : {setting_name} is disabled in your {self.yamldata.crashgen_name} settings, is this intentional? * \n-----\n",
                        autoscan_report,
                    )

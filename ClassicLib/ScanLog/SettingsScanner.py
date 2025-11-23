"""
Fragment-based settings scanner for CLASSIC.

This module provides fragment-returning versions of all settings scanning functions,
replacing the mutable list pattern with immutable fragment composition.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from ClassicLib.ScanLog.fragments import ReportFragment
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

if TYPE_CHECKING:
    from packaging.version import Version

    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo


class SettingsScannerFragments:
    """Fragment-based settings scanner for crash log analysis."""

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initialize the settings scanner.

        Args:
            yamldata: Configuration data
        """
        self.yamldata: ClassicScanLogsInfo = yamldata

    def scan_buffout_achievements_setting(self, xsemodules: set[str], crashgen: dict[str, bool | int | str]) -> ReportFragment:
        """
        Scan the achievements setting for potential conflicts.

        Args:
            xsemodules: A set of currently loaded XSE plugin modules.
            crashgen: Configuration settings for the crash generator.

        Returns:
            ReportFragment containing the scan results.
        """
        lines = []
        crashgen_achievements = crashgen.get("Achievements")

        if crashgen_achievements and ("achievements.dll" in xsemodules or "unlimitedsurvivalmode.dll" in xsemodules):
            lines.extend([
                "# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE # \n",
                f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change Achievements to FALSE, this prevents conflicts with {self.yamldata.crashgen_name}.\n\n-----\n",
            ])
        else:
            lines.append(f"✔️ Achievements parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n\n-----\n")

        return ReportFragment.from_lines(lines)

    def scan_buffout_memorymanagement_settings(
        self,
        crashgen: dict[str, bool | int | str],
        has_xcell: bool,
        has_old_xcell: bool,
        has_baka_scrapheap: bool,
    ) -> ReportFragment:
        """
        Analyze and validate memory management settings.

        Args:
            crashgen: Configuration settings from CrashGen.
            has_xcell: Whether X-Cell mod is installed.
            has_old_xcell: Whether an outdated X-Cell is installed.
            has_baka_scrapheap: Whether Baka ScrapHeap mod is installed.

        Returns:
            ReportFragment containing the scan results.
        """
        lines = []
        separator = "\n\n-----\n"

        def add_success(message: str) -> None:
            """Add a success message."""
            lines.append(f"✔️ {message}{separator}")

        def add_warning(warning: str, fix: str) -> None:
            """Add a warning with fix instructions."""
            lines.extend([f"# ❌ CAUTION : {warning} # \n", f" FIX: {fix}{separator}"])

        # Check for old X-Cell version first
        if has_old_xcell:
            add_warning(
                "You have an old version of X-Cell installed, please update it to the latest version.",
                "Download the latest version from here: https://www.nexusmods.com/fallout4/mods/84214?tab=files",
            )

        # Validate main memory manager configuration
        mem_manager_enabled = bool(crashgen.get("MemoryManager"))
        self._validate_memory_config(
            mem_manager_enabled, has_xcell, has_baka_scrapheap, self.yamldata.crashgen_name, add_success, add_warning
        )

        # Check X-Cell specific settings
        if has_xcell:
            self._validate_xcell_settings(crashgen, self.yamldata.crashgen_name, add_success, add_warning)

        return ReportFragment.from_lines(lines)

    @staticmethod
    def _validate_memory_config(
        mem_enabled: bool,
        has_xcell: bool,
        has_baka: bool,
        crashgen_name: str,
        add_success: Callable[[str], None],
        add_warning: Callable[[str, str], None],
    ) -> None:
        """Validate memory manager configuration based on installed mods."""
        # Create configuration tuple for cleaner logic
        config = (mem_enabled, has_xcell, has_baka)

        # Map configurations to their handlers
        config_handlers = {
            (True, True, False): lambda: add_warning(
                "X-Cell is installed, but MemoryManager parameter is set to TRUE",
                f"Open {crashgen_name}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with X-Cell.",
            ),
            (True, False, True): lambda: add_warning(
                f"The Baka ScrapHeap Mod is installed, but is redundant with {crashgen_name}",
                f"Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {crashgen_name}.",
            ),
            (True, False, False): lambda: add_success(
                f"Memory Manager parameter is correctly configured in your {crashgen_name} settings!"
            ),
            (False, True, True): lambda: add_warning(
                "The Baka ScrapHeap Mod is installed, but is redundant with X-Cell",
                "Uninstall the Baka ScrapHeap Mod, this prevents conflicts with X-Cell.",
            ),
            (False, True, False): lambda: add_success(
                f"Memory Manager parameter is correctly configured for use with X-Cell in your {crashgen_name} settings!"
            ),
            (False, False, True): lambda: add_warning(
                f"The Baka ScrapHeap Mod is installed, but is redundant with {crashgen_name}",
                f"Uninstall the Baka ScrapHeap Mod and open {crashgen_name}'s TOML file and change MemoryManager to TRUE, this improves performance.",
            ),
        }

        # Execute the appropriate handler
        handler = config_handlers.get(config)
        if handler:
            handler()

    @staticmethod
    def _validate_xcell_settings(
        crashgen: dict, crashgen_name: str, add_success: Callable[[str], None], add_warning: Callable[[str, str], None]
    ) -> None:
        """Validate X-Cell specific memory settings."""
        memory_settings = {
            "HavokMemorySystem": "Havok Memory System",
            "BSTextureStreamerLocalHeap": "BSTextureStreamerLocalHeap",
            "ScaleformAllocator": "Scaleform Allocator",
            "SmallBlockAllocator": "Small Block Allocator",
        }

        for setting_key, display_name in memory_settings.items():
            if crashgen.get(setting_key):
                add_warning(
                    f"X-Cell is installed, but {setting_key} parameter is set to TRUE",
                    f"Open {crashgen_name}'s TOML file and change {setting_key} to FALSE, this prevents conflicts with X-Cell.",
                )
            else:
                add_success(f"{display_name} parameter is correctly configured for use with X-Cell in your {crashgen_name} settings!")

    def scan_archivelimit_setting(self, crashgen: dict[str, bool | int | str], crashgen_version: "Version | None" = None) -> ReportFragment:
        """
        Scan and validate the "ArchiveLimit" setting.

        Args:
            crashgen: Configuration settings from CrashGen.
            crashgen_version: The version of the crash generator.

        Returns:
            ReportFragment containing the scan results.
        """
        # Import here to avoid circular dependency
        from packaging.version import Version

        # Skip check for versions >= 1.29.0
        if crashgen_version and crashgen_version >= Version("1.29.0"):
            return ReportFragment.empty()

        lines = []
        crashgen_archivelimit = crashgen.get("ArchiveLimit")

        if crashgen_archivelimit:
            lines.extend([
                "# ❌ CAUTION : ArchiveLimit is set to TRUE, this setting is known to cause instability. # \n",
                f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change ArchiveLimit to FALSE.\n\n-----\n",
            ])
        else:
            lines.append(f"✔️ ArchiveLimit parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n\n-----\n")

        return ReportFragment.from_lines(lines)

    def scan_buffout_looksmenu_setting(self, crashgen: dict[str, bool | int | str], xsemodules: set[str]) -> ReportFragment:
        """
        Analyze the Looksmenu setting for proper compatibility.

        Args:
            crashgen: Configuration settings from CrashGen.
            xsemodules: A set of currently loaded XSE plugin modules.

        Returns:
            ReportFragment containing the scan results.
        """
        lines = []
        crashgen_f4ee = crashgen.get("F4EE")

        if crashgen_f4ee is not None:
            if not crashgen_f4ee and "f4ee.dll" in xsemodules:
                lines.extend([
                    "# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under [Compatibility] is set to FALSE # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change F4EE to TRUE, this prevents bugs and crashes from Looks Menu.\n\n-----\n",
                ])
            else:
                lines.append(
                    f"✔️ F4EE (Looks Menu) parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n\n-----\n"
                )

        return ReportFragment.from_lines(lines)

    def check_disabled_settings(self, crashgen: dict[str, bool | int | str], crashgen_ignore: set[str]) -> ReportFragment:
        """
        Check disabled settings in crash generation configuration.

        Args:
            crashgen: Configuration settings from CrashGen.
            crashgen_ignore: Settings to ignore even if disabled.

        Returns:
            ReportFragment containing any notices about disabled settings.
        """
        lines = []

        if crashgen:
            for setting_name, setting_value in crashgen.items():
                if setting_value is False and setting_name not in crashgen_ignore:
                    lines.append(
                        f"* NOTICE : {setting_name} is disabled in your {self.yamldata.crashgen_name} settings, is this intentional? * \n\n-----\n"
                    )

        return ReportFragment.from_lines(lines)

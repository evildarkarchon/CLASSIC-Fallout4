"""
Rust-accelerated SettingsValidator wrapper.

This module provides a transparent wrapper around the Rust SettingsValidator implementation,
maintaining full API compatibility with the Python reference (SettingsScannerFragments) while
delivering performance improvements.

Key API Translations:
- Constructor: Extract crashgen_name and crashgen_ignore from yamldata
- Return types: Convert Rust list[str] to Python ReportFragment
- Method names: All methods match Python reference exactly
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.ReportFragment import ReportFragment

if TYPE_CHECKING:
    from packaging.version import Version

    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

try:
    import classic_core

    RustSettingsValidator = classic_core.scanlog.SettingsValidator
    RUST_AVAILABLE = True
except (ImportError, AttributeError):
    RustSettingsValidator = None
    RUST_AVAILABLE = False


class RustAcceleratedSettingsValidator:
    """
    Rust-accelerated settings validator with Python API compatibility.

    This wrapper bridges the API differences between Rust and Python implementations:
    - Rust constructor takes crashgen_name and crashgen_ignore directly
    - Python constructor takes yamldata object
    - Rust returns list[str], Python returns ReportFragment
    """

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initialize the settings validator.

        Args:
            yamldata: Configuration data containing crashgen settings
        """
        self.yamldata = yamldata
        self._use_rust = RUST_AVAILABLE

        if self._use_rust:
            # Extract required parameters for Rust constructor
            crashgen_name = getattr(yamldata, "crashgen_name", "Buffout 4")
            crashgen_ignore = getattr(yamldata, "crashgen_ignore", [])
            self._validator = RustSettingsValidator(crashgen_name, crashgen_ignore)
        else:
            # Fallback to Python implementation
            from ClassicLib.ScanLog.SettingsScanner import SettingsScannerFragments

            self._validator = SettingsScannerFragments(yamldata)

    def scan_buffout_achievements_setting(self, xsemodules: set[str], crashgen: dict[str, bool | int | str]) -> ReportFragment:
        """
        Scan the achievements setting for potential conflicts.

        Args:
            xsemodules: A set of currently loaded XSE plugin modules.
            crashgen: Configuration settings for the crash generator.

        Returns:
            ReportFragment containing the scan results.
        """
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_buffout_achievements_setting(xsemodules, crashgen_str)
            return ReportFragment.from_lines(lines)
        else:
            # Python already returns ReportFragment
            return self._validator.scan_buffout_achievements_setting(xsemodules, crashgen)

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
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_buffout_memorymanagement_settings(
                crashgen_str, has_xcell, has_old_xcell, has_baka_scrapheap
            )
            return ReportFragment.from_lines(lines)
        else:
            # Python already returns ReportFragment
            return self._validator.scan_buffout_memorymanagement_settings(
                crashgen, has_xcell, has_old_xcell, has_baka_scrapheap
            )

    def scan_archivelimit_setting(self, crashgen: dict[str, bool | int | str], crashgen_version: "Version | None" = None) -> ReportFragment:
        """
        Scan and validate the "ArchiveLimit" setting.

        Args:
            crashgen: Configuration settings from CrashGen.
            crashgen_version: The version of the crash generator.

        Returns:
            ReportFragment containing the scan results.
        """
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_archivelimit_setting(crashgen_str, crashgen_version)
            return ReportFragment.from_lines(lines)
        else:
            # Python already returns ReportFragment
            return self._validator.scan_archivelimit_setting(crashgen, crashgen_version)

    def scan_buffout_looksmenu_setting(self, crashgen: dict[str, bool | int | str], xsemodules: set[str]) -> ReportFragment:
        """
        Analyze the Looksmenu setting for proper compatibility.

        Args:
            crashgen: Configuration settings from CrashGen.
            xsemodules: A set of currently loaded XSE plugin modules.

        Returns:
            ReportFragment containing the scan results.
        """
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_buffout_looksmenu_setting(crashgen_str, xsemodules)
            return ReportFragment.from_lines(lines)
        else:
            # Python already returns ReportFragment
            return self._validator.scan_buffout_looksmenu_setting(crashgen, xsemodules)


# Export both the wrapper and components for compatibility
SettingsValidator = RustAcceleratedSettingsValidator
SettingsScannerFragments = RustAcceleratedSettingsValidator  # Alternative naming (Python class name)
__all__ = ["SettingsValidator", "SettingsScannerFragments", "RustAcceleratedSettingsValidator", "RUST_AVAILABLE"]

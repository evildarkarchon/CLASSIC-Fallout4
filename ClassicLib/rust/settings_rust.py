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

from ClassicLib.ScanLog.fragments import ReportFragment

if TYPE_CHECKING:
    from packaging.version import Version

    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

try:
    import classic_scanlog

    RustSettingsValidator = classic_scanlog.SettingsValidator
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

    def __init__(self, yamldata: ClassicScanLogsInfo) -> None:
        """
        Initializes the validator instance for handling ClassicScanLogsInfo based on the
        availability of a Rust implementation. If Rust is available, utilizes the Rust-
        based validation mechanism; otherwise, falls back to the Python implementation.

        Args:
            yamldata (ClassicScanLogsInfo): Data containing the YAML configuration
                necessary for initializing the validator.
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
        Scans the provided `xsemodules` and `crashgen` to extract or validate Buffout achievements
        settings, returning the corresponding `ReportFragment`.

        Depending on whether the Rust validator is used, the `crashgen` dictionary is adjusted so that
        all values are converted to strings, as required by the Rust implementation. The Python
        implementation processes the input directly without conversions.

        Args:
            xsemodules (set[str]): A set of module identifiers to be scanned.
            crashgen (dict[str, bool | int | str]): A dictionary containing key-value pairs of crash
                generation settings, where values can be of types boolean, integer, or string.

        Returns:
            ReportFragment: A fragment object containing details of the scanned results.
        """
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_buffout_achievements_setting(xsemodules, crashgen_str)
            return ReportFragment.from_lines(lines)
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
        Scans memory management settings from Buffout and generates a report
        fragment based on the provided configurations.

        This method determines which version of the validator to use (Rust or
        Python) based on the internal state, converts data as necessary for Rust
        requirements, and returns a processed report fragment.

        Args:
            crashgen (dict[str, bool | int | str]): Configuration data from Buffout,
                where keys correspond to setting names and values to their respective
                configurations. Rust requires all values as strings.
            has_xcell (bool): Flag indicating whether xCell is present in the settings.
            has_old_xcell (bool): Flag indicating whether an older version of xCell is
                used in the settings.
            has_baka_scrapheap (bool): Flag indicating whether Baka ScrapHeap is present
                in the settings.

        Returns:
            ReportFragment: A processed fragment containing the scan results based on
            the provided Buffout memory management settings.
        """
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_buffout_memorymanagement_settings(
                crashgen_str, has_xcell, has_old_xcell, has_baka_scrapheap
            )
            return ReportFragment.from_lines(lines)
        # Python already returns ReportFragment
        return self._validator.scan_buffout_memorymanagement_settings(
            crashgen, has_xcell, has_old_xcell, has_baka_scrapheap
        )

    def scan_archivelimit_setting(self, crashgen: dict[str, bool | int | str], crashgen_version: Version | None = None) -> ReportFragment:
        """
        Validates and processes the "archivelimit" setting based on the provided configuration
        and version. This function supports two implementations: one leveraging Rust for improved
        performance, and the other using native Python. When using Rust, the function converts
        the values of the input dictionary to strings to meet the expected format. Both
        implementations rely on methods provided by the `_validator` object.

        Args:
            crashgen (dict[str, bool | int | str]): A dictionary containing the configuration
                settings for crash generation. The keys are configuration options, and the values
                represent their respective settings.
            crashgen_version (Version | None): An optional version object identifying the version
                of crash generation settings to validate or process. Defaults to None.

        Returns:
            ReportFragment: An object encapsulating the scanned and validated results of the
                "archivelimit" setting, formatted based on the selected implementation (Rust or Python).
        """
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_archivelimit_setting(crashgen_str, crashgen_version)
            return ReportFragment.from_lines(lines)
        # Python already returns ReportFragment
        return self._validator.scan_archivelimit_setting(crashgen, crashgen_version)

    def scan_buffout_looksmenu_setting(self, crashgen: dict[str, bool | int | str], xsemodules: set[str]) -> ReportFragment:
        """
        Analyzes the 'Buffout' and 'LooksMenu' settings from the provided crash generation data and XSE modules.

        This method validates the compatibility of 'Buffout' crashes and 'LooksMenu'
        settings based on the provided crash generation dictionary and XSE modules.
        Depending on the implementation context (Rust or Python), it processes the inputs
        accordingly and generates a `ReportFragment`, which contains the results
        of the analysis.

        Args:
            crashgen (dict[str, bool | int | str]): Dictionary representing the crash
                generation settings. Keys represent setting names, and values can be
                of type bool, int, or str depending on the setting.
            xsemodules (set[str]): Set containing XSE module identifiers.

        Returns:
            ReportFragment: A structured object that encapsulates the results of the
            validation and analysis.

        """
        if self._use_rust:
            # Rust requires dict[str, str], convert all values to strings
            crashgen_str = {k: str(v) for k, v in crashgen.items()}
            lines = self._validator.scan_buffout_looksmenu_setting(crashgen_str, xsemodules)
            return ReportFragment.from_lines(lines)
        # Python already returns ReportFragment
        return self._validator.scan_buffout_looksmenu_setting(crashgen, xsemodules)


# Export both the wrapper and components for compatibility
SettingsValidator = RustAcceleratedSettingsValidator
SettingsScannerFragments = RustAcceleratedSettingsValidator  # Alternative naming (Python class name)
__all__ = ["SettingsValidator", "SettingsScannerFragments", "RustAcceleratedSettingsValidator", "RUST_AVAILABLE"]

"""Rust-accelerated ReportGenerator wrapper.

This module provides the RustAcceleratedReportGenerator class for
efficient string building and pooling with automatic fallback to Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ClassicLib.integration.detector import detect_component
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyReportFragment
from ClassicLib.ScanLog.fragments.report_generator_functional import ReportGeneratorFunctional as PyReportGenerator

if TYPE_CHECKING:
    from classic_scanlog import ReportGenerator as RustReportGenerator

    RUST_AVAILABLE: bool = True
else:
    _has_generator, RustReportGenerator = detect_component("classic_scanlog", "ReportGenerator")
    RUST_AVAILABLE = _has_generator

    if not RUST_AVAILABLE:
        RustReportGenerator = None  # type: ignore[assignment, misc]

# Import fragment wrapper - using lazy import to avoid circular imports


def _get_fragment_class() -> type:
    """Get RustAcceleratedReportFragment class lazily to avoid circular imports.

    Returns:
        The RustAcceleratedReportFragment class.

    """
    from ClassicLib.rust.report.fragment import RustAcceleratedReportFragment

    return RustAcceleratedReportFragment


class RustAcceleratedReportGenerator:
    """Wrapper for Rust-accelerated ReportGenerator with Python fallback.

    Provides efficient string building and pooling when using Rust implementation.
    """

    def __init__(self, yamldata: Any = None) -> None:
        """Initialize the object and sets up the report generator based on the availability
        of the Rust implementation. If Rust is not available, a Python-based report
        generator is used.

        Args:
            yamldata: Optional initial data in YAML format that will be associated
                with the report generator.

        """
        self._use_rust = RUST_AVAILABLE
        self.yamldata = yamldata

        if self._use_rust:
            self._generator = RustReportGenerator()  # type: ignore[misc]
        else:
            self._generator = PyReportGenerator()
            self._generator.yamldata = yamldata  # type: ignore[attr-defined]

    def generate_header(self, crashlog_filename: str, version: str = "") -> Any:
        """Generate a header fragment for a Rust-accelerated report. The method determines
        the use of Rust acceleration and delegates the generation of the header accordingly.

        Args:
            crashlog_filename: The filename of the crash log to be processed.
            version: The version string to be included in the header. Defaults to an
                empty string.

        Returns:
            RustAcceleratedReportFragment: An instance containing the generated
            header fragment.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        if self._use_rust:
            result._fragment = self._generator.generate_header(crashlog_filename, version)
        else:
            result._fragment = self._generator.generate_header(crashlog_filename, version)

        return result

    def generate_error_section(
        self,
        main_error: str,
        crashgen_version: str,
        version_current: Any,
        version_latest: Any,
        version_latest_vr: Any,
    ) -> Any:
        """Generate an error section in the report.

        This method determines the appropriate error section for a report based on the
        provided parameters and handles logic for generating the fragment either using
        Python or Rust implementation. It includes checks for whether the version is up
        to date and provides warning messages accordingly.

        Args:
            main_error: The main error message to be included in the report.
            crashgen_version: The version of the crash generator used.
            version_current: The current version of the software (comparable type).
            version_latest: The latest supported version of the software (comparable type).
            version_latest_vr: The latest VR-compatible version of the software (comparable type).

        Returns:
            RustAcceleratedReportFragment: A fragment object containing the error section.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        if self._use_rust:
            assert RustReportGenerator is not None, "Rust should be available when _use_rust is True"
            # Rust implementation expects different signature - convert parameters
            from ClassicLib import GlobalRegistry

            crashgen_name = self.yamldata.crashgen_name if self.yamldata else "Crashgen"
            game_is_vr = GlobalRegistry.get_vr() == "VR"

            # Check if version is latest
            is_latest = not (
                (version_current < version_latest_vr and version_current != version_latest)
                or (not game_is_vr and version_current < version_latest)
            )

            warn_outdated = f"***\u274c WARNING: YOUR {crashgen_name} IS OUTDATED! PLEASE UPDATE TO THE LATEST VERSION!***"

            result._fragment = self._generator.generate_error_section(main_error, crashgen_version, crashgen_name, is_latest, warn_outdated)
        else:
            # Python implementation uses the original signature
            result._fragment = self._generator.generate_error_section(
                main_error, crashgen_version, version_current, version_latest, version_latest_vr
            )

        return result

    def generate_suspect_section(self, found_suspects: list[str]) -> Any:
        """Generate a suspect section fragment using either the Rust or Python generator,
        depending on the specified configuration setting.

        Args:
            found_suspects (list[str]): A list of suspect identifiers as strings.

        Returns:
            RustAcceleratedReportFragment: A generated report fragment containing the
            suspect section.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        if self._use_rust:
            result._fragment = self._generator.generate_suspect_section(found_suspects)
        else:
            result._fragment = self._generator.generate_suspect_section(found_suspects)

        return result

    @staticmethod
    def generate_suspect_section_header() -> Any:
        """Generate a section header for reporting known crash messages, errors, and suspects.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the section header.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Known Crash Messages, Errors and Suspects\n\n",
        ])

        return result

    @staticmethod
    def generate_suspect_found_footer(found_suspect: bool) -> Any:
        """Generate a footer message indicating whether suspects were detected.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Args:
            found_suspect: Whether one or more suspects were detected.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the footer message.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static footer
        if found_suspect:
            result._fragment = PyReportFragment.from_lines([
                "* **ONE OR MORE SUSPECTS DETECTED! CHECK LOG ABOVE FOR MORE INFORMATION!** *\n\n",
                "---\n\n",
            ])
        else:
            result._fragment = PyReportFragment.from_lines([
                "* **NO SUSPECTS DETECTED** *\n\n",
                "---\n\n",
            ])

        return result

    @staticmethod
    def generate_settings_section_header() -> Any:
        """Generate a section header for reporting settings-related issues.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the settings-related issues header.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Settings-related Issues\n\n",
        ])

        return result

    @staticmethod
    def generate_mod_check_header(check_type: str) -> Any:
        """Generate a report fragment header for mod checks based on the provided check type.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Args:
            check_type: The type of mod check to include in the header.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the formatted header lines.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            f"### Checking For Mods That {check_type}\n\n",
        ])

        return result

    @staticmethod
    def generate_plugin_suspect_header() -> Any:
        """Generate a header fragment for reports related to plugin-related errors.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A fragment containing formatted header information.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Plugin-related Errors\n\n",
        ])

        return result

    @staticmethod
    def generate_formid_section_header() -> Any:
        """Generate a section header for FormID checks.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A segment of the report containing the FormID check header.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking FormIDs\n\n",
        ])

        return result

    @staticmethod
    def generate_record_section_header() -> Any:
        """Generate a section header for checking named records.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: An instance containing the predefined header lines.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Named Records\n\n",
        ])

        return result


__all__ = [
    "RUST_AVAILABLE",
    "RustAcceleratedReportGenerator",
]

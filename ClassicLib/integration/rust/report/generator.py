"""Rust-accelerated ReportGenerator wrapper.

This module provides the RustAcceleratedReportGenerator class that delegates
all report section generation to the Rust implementation. No Python fallback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ClassicLib.integration.factory import get_component

if TYPE_CHECKING:
    from classic_scanlog import ReportGenerator as RustReportGenerator

    from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment
else:
    RustReportGenerator = get_component("classic_scanlog", "ReportGenerator")


def _get_fragment_class() -> type[RustAcceleratedReportFragment]:
    """Get RustAcceleratedReportFragment class lazily to avoid circular imports.

    Returns:
        The RustAcceleratedReportFragment class.

    """
    from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

    return RustAcceleratedReportFragment


class RustAcceleratedReportGenerator:
    """Rust-only ReportGenerator wrapper.

    Delegates all report section generation to required Rust implementation.
    """

    def __init__(self, yamldata: Any = None) -> None:
        """Initialize the report generator with Rust backend.

        Args:
            yamldata: Optional configuration data (kept for API compatibility).

        """
        self._generator = RustReportGenerator()  # type: ignore[misc]
        self.yamldata = yamldata

    def generate_header(self, crashlog_filename: str, version: str = "") -> Any:  # noqa: ARG002 - protocol compatibility
        """Generate a header fragment for the crash log report.

        Args:
            crashlog_filename: The filename of the crash log to be processed.
            version: Compatibility-only argument to match ReportGeneratorProtocol.
                The Rust backend does not require this value.

        Returns:
            RustAcceleratedReportFragment: An instance containing the generated
            header fragment.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_header(crashlog_filename)
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_error_section(
        self,
        main_error: str,
        crashgen_version: str,
        version_current: Any,
        version_latest: Any,
        _version_latest_vr: Any,
        *,
        game_version_id: str | None = None,
    ) -> Any:
        """Generate an error section in the report.

        Computes version outdated status in Python, passes boolean to Rust.

        Args:
            main_error: The main error message to be included in the report.
            crashgen_version: The version of the crash generator used.
            version_current: The current version of the software (comparable type).
            version_latest: The latest supported version of the software (comparable type).
            version_latest_vr: The latest VR-compatible version (deprecated, kept for signature compatibility).
            game_version_id: The game version ID for list-based version checking (e.g., "FO4_OG").
                When provided, uses the new VersionRegistry-based checking.

        Returns:
            RustAcceleratedReportFragment: A fragment object containing the error section.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        # Determine if version is outdated
        if game_version_id is not None:
            # New list-based version checking via VersionRegistry
            from ClassicLib.support.versions.crashgen_checker import (
                CrashgenVersionStatus,
                check_crashgen_version,
            )

            crashgen_name = self.yamldata.crashgen_name if self.yamldata else "Crashgen"
            result = check_crashgen_version(version_current, game_version_id, crashgen_name)
            is_outdated = result.status == CrashgenVersionStatus.OUTDATED
        else:
            # Legacy single-version comparison (simple: current < latest)
            is_outdated = version_current < version_latest

        fragment = self._generator.generate_error_section(main_error, crashgen_version, is_outdated)
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_suspect_section(self, found_suspects: list[str]) -> Any:
        """Generate a suspect section fragment.

        Args:
            found_suspects (list[str]): A list of suspect identifiers as strings.

        Returns:
            RustAcceleratedReportFragment: A generated report fragment containing the
            suspect section.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_suspect_section(found_suspects)
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_suspect_section_header(self) -> Any:
        """Generate a section header for reporting known crash messages, errors, and suspects.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the section header.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_suspect_section_header()
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_suspect_found_footer(self, found_suspect: bool) -> Any:
        """Generate a footer message indicating whether suspects were detected.

        Args:
            found_suspect: Whether one or more suspects were detected.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the footer message.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_suspect_found_footer(found_suspect)
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_settings_section_header(self) -> Any:
        """Generate a section header for reporting settings-related issues.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the settings-related issues header.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_settings_section_header()
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_mod_check_header(self, check_type: str) -> Any:
        """Generate a report fragment header for mod checks based on the provided check type.

        Args:
            check_type: The type of mod check to include in the header.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the formatted header lines.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_mod_check_header(check_type)
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_plugin_suspect_header(self) -> Any:
        """Generate a header fragment for reports related to plugin-related errors.

        Returns:
            RustAcceleratedReportFragment: A fragment containing formatted header information.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_plugin_suspect_header()
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_formid_section_header(self) -> Any:
        """Generate a section header for FormID checks.

        Returns:
            RustAcceleratedReportFragment: A segment of the report containing the FormID check header.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_formid_section_header()
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_record_section_header(self) -> Any:
        """Generate a section header for checking named records.

        Returns:
            RustAcceleratedReportFragment: An instance containing the predefined header lines.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_record_section_header()
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def generate_footer(self) -> Any:
        """Generate a footer section for the report.

        Returns:
            RustAcceleratedReportFragment: The report fragment representing the footer section.

        """
        RustAcceleratedReportFragment = _get_fragment_class()
        fragment = self._generator.generate_footer()
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)


__all__ = [
    "RustAcceleratedReportGenerator",
]

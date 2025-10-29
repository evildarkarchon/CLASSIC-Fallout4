"""
Rust-accelerated SuspectScanner wrapper.

This module provides a transparent wrapper around the Rust SuspectScanner implementation,
maintaining full API compatibility with the Python reference while delivering significant
performance improvements.

Key API Translations:
- Constructor: Extract suspects lists from yamldata object
- Return types: Convert Rust list[str] to Python ReportFragment
- Method signatures: Maintain Python API while calling Rust internals
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.ReportFragment import ReportFragment

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

try:
    import classic_core

    RustSuspectScanner = classic_core.scanlog.SuspectScanner
    RUST_AVAILABLE = True
except (ImportError, AttributeError):
    RustSuspectScanner = None
    RUST_AVAILABLE = False


class RustAcceleratedSuspectScanner:
    """
    Rust-accelerated suspect scanner with Python API compatibility.

    This wrapper bridges the API differences between Rust and Python implementations:
    - Rust constructor takes suspects lists directly
    - Python constructor takes yamldata object
    - Rust returns list[str], Python returns ReportFragment
    """

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initialize the suspect scanner.

        Args:
            yamldata: Configuration data containing suspect patterns
        """
        self.yamldata = yamldata
        self._use_rust = RUST_AVAILABLE

        if self._use_rust:
            # Extract suspects lists from yamldata for Rust constructor
            suspects_error_list = getattr(yamldata, "suspects_error_list", {})
            suspects_stack_list = getattr(yamldata, "suspects_stack_list", {})
            self._scanner = RustSuspectScanner(suspects_error_list, suspects_stack_list)
        else:
            # Fallback to Python implementation
            from ClassicLib.ScanLog.SuspectScanner import SuspectScanner as PySuspectScanner

            self._scanner = PySuspectScanner(yamldata)

    def suspect_scan_mainerror(self, crashlog_mainerror: str, max_warn_length: int) -> tuple[ReportFragment, bool]:
        """
        Scans the crash log for errors listed in a predefined suspect error list.

        Args:
            crashlog_mainerror: The main error output from a crash log to scan for suspect errors.
            max_warn_length: The maximum length for formatting the error name in the report.

        Returns:
            Tuple of (ReportFragment containing findings, bool indicating if suspects found).
        """
        if self._use_rust:
            # Rust returns (list[str], bool), need to convert to (ReportFragment, bool)
            lines, found_suspect = self._scanner.suspect_scan_mainerror(crashlog_mainerror, max_warn_length)
            return ReportFragment.from_lines(lines), found_suspect
        else:
            # Python already returns correct types
            return self._scanner.suspect_scan_mainerror(crashlog_mainerror, max_warn_length)

    def suspect_scan_stack(
        self, crashlog_mainerror: str, segment_callstack_intact: str, max_warn_length: int
    ) -> tuple[ReportFragment, bool]:
        """
        Analyzes a crash report and call stack information to identify potential suspect errors.

        Args:
            crashlog_mainerror: The main error extracted from the crash log.
            segment_callstack_intact: The intact segment of the call stack relevant to the analysis.
            max_warn_length: Maximum allowed length for warnings included in the report.

        Returns:
            Tuple of (ReportFragment containing findings, bool indicating if suspects found).
        """
        if self._use_rust:
            # Rust returns (list[str], bool), need to convert to (ReportFragment, bool)
            lines, any_suspect_found = self._scanner.suspect_scan_stack(
                crashlog_mainerror, segment_callstack_intact, max_warn_length
            )
            return ReportFragment.from_lines(lines), any_suspect_found
        else:
            # Python already returns correct types
            return self._scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, max_warn_length)

    @staticmethod
    def check_dll_crash(crashlog_mainerror: str) -> ReportFragment:
        """
        Analyze a crash log to identify if a DLL file is implicated in the crash.

        Args:
            crashlog_mainerror: The main error message extracted from the crash log.

        Returns:
            ReportFragment containing DLL crash notification, or empty fragment.
        """
        if RUST_AVAILABLE:
            # Rust returns list[str], need to convert to ReportFragment
            lines = RustSuspectScanner.check_dll_crash(crashlog_mainerror)
            return ReportFragment.from_lines(lines)
        else:
            # Fallback to Python implementation
            from ClassicLib.ScanLog.SuspectScanner import SuspectScanner as PySuspectScanner

            return PySuspectScanner.check_dll_crash(crashlog_mainerror)


# Export both the wrapper and components for compatibility
SuspectScanner = RustAcceleratedSuspectScanner
__all__ = ["SuspectScanner", "RustAcceleratedSuspectScanner", "RUST_AVAILABLE"]

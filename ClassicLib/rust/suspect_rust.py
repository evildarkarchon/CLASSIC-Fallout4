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

from ClassicLib.ScanLog.fragments import ReportFragment

if TYPE_CHECKING:
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

try:
    import classic_scanlog

    RustSuspectScanner = classic_scanlog.SuspectScanner
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

    def __init__(self, yamldata: ClassicScanLogsInfo) -> None:
        """
        Initializes an instance of the class with the provided ClassicScanLogsInfo object
        and determines whether to use the Rust or Python implementation for the scanner,
        based on the availability of Rust.

        Args:
            yamldata: An instance of ClassicScanLogsInfo that contains information
                necessary for initializing the scanner.
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
        Analyzes the main error extracted from a crashlog and determines potential suspects by scanning
        the input string and evaluating against a defined warning length threshold. This function either
        uses a Rust-based scanner or a Python-based scanner depending on the runtime configuration.

        Args:
            crashlog_mainerror (str): The main error extracted from the crashlog to be analyzed.
            max_warn_length (int): The maximum warning length considered during the scan process.

        Returns:
            tuple[ReportFragment, bool]: A tuple containing a `ReportFragment` object based on the scan
            results and a boolean indicating whether a suspect was found.
        """
        if self._use_rust:
            # Rust returns (list[str], bool), need to convert to (ReportFragment, bool)
            lines, found_suspect = self._scanner.suspect_scan_mainerror(crashlog_mainerror, max_warn_length)
            return ReportFragment.from_lines(lines), found_suspect
        # Python already returns correct types
        return self._scanner.suspect_scan_mainerror(crashlog_mainerror, max_warn_length)

    def suspect_scan_stack(
        self, crashlog_mainerror: str, segment_callstack_intact: str, max_warn_length: int
    ) -> tuple[ReportFragment, bool]:
        """
        Perform a scan of the stack to identify potential suspects based on the crash log
        and call stack segment provided. This function determines whether any suspects
        can be identified and returns the processed report fragment alongside a boolean
        indicating detection status.

        Args:
            crashlog_mainerror (str): Main error message or signature extracted from the crash log.
            segment_callstack_intact (str): Call stack information in a simplified or processed form.
            max_warn_length (int): Maximum permissible length for warnings in the report.

        Returns:
            tuple[ReportFragment, bool]: A tuple containing the processed report fragment
            and a boolean flag indicating whether any suspect was found.
        """
        if self._use_rust:
            # Rust returns (list[str], bool), need to convert to (ReportFragment, bool)
            lines, any_suspect_found = self._scanner.suspect_scan_stack(
                crashlog_mainerror, segment_callstack_intact, max_warn_length
            )
            return ReportFragment.from_lines(lines), any_suspect_found
        # Python already returns correct types
        return self._scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, max_warn_length)

    @staticmethod
    def check_dll_crash(crashlog_mainerror: str) -> ReportFragment:
        """
        Checks for DLL-related crashes in the given crash log and returns a
        processed report.

        This method attempts to analyze crash logs using Rust-based logic if
        available, providing efficient processing. If Rust is unavailable, it
        falls back to a Python-based implementation to ensure the operation
        can still be performed.

        Args:
            crashlog_mainerror (str): The main error log string to be analyzed.

        Returns:
            ReportFragment: A detailed analysis report generated from the given
            crash log.

        """
        if RUST_AVAILABLE:
            # Rust returns list[str], need to convert to ReportFragment
            lines = RustSuspectScanner.check_dll_crash(crashlog_mainerror)
            return ReportFragment.from_lines(lines)
        # Fallback to Python implementation
        from ClassicLib.ScanLog.SuspectScanner import SuspectScanner as PySuspectScanner

        return PySuspectScanner.check_dll_crash(crashlog_mainerror)


# Export both the wrapper and components for compatibility
SuspectScanner = RustAcceleratedSuspectScanner
__all__ = ["SuspectScanner", "RustAcceleratedSuspectScanner", "RUST_AVAILABLE"]

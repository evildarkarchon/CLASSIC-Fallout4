"""
Suspect scanner module for CLASSIC.

This module scans for known crash patterns and suspects including:
- Checking main errors against known patterns
- Scanning call stacks for problematic signatures
- Identifying DLL-related crashes
- Matching against YAML-defined suspect patterns
"""

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.ReportFragment import ReportFragment
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class SuspectScanner:
    """Handles scanning for known crash patterns and suspects."""

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initialize the suspect scanner.

        Args:
            yamldata: Configuration data containing suspect patterns
        """
        self.yamldata: ClassicScanLogsInfo = yamldata

    def suspect_scan_mainerror(self, crashlog_mainerror: str, max_warn_length: int) -> tuple[ReportFragment, bool]:
        """
        Scans the crash log for errors listed in a predefined suspect error list.

        Args:
            crashlog_mainerror: The main error output from a crash log to scan for suspect errors.
            max_warn_length: The maximum length for formatting the error name in the report.

        Returns:
            Tuple of (ReportFragment containing findings, bool indicating if suspects found).
        """
        lines = []
        found_suspect = False

        for error_key, signal in self.yamldata.suspects_error_list.items():
            # Skip checking if signal not in crash log
            if signal not in crashlog_mainerror:
                continue

            # Parse error information
            error_severity, error_name = error_key.split(" | ", 1)

            # Format the error name for report
            formatted_error_name = error_name.ljust(max_warn_length, ".")

            # Add the error to the report
            lines.append(f"- **Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity}** \n\n")
            lines.append("-----\n")

            # Update suspect found status
            found_suspect = True

        return ReportFragment.from_lines(lines), found_suspect

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
        lines = []
        any_suspect_found = False

        for error_key, signal_list in self.yamldata.suspects_stack_list.items():
            # Parse error information
            error_severity, error_name = error_key.split(" | ", 1)

            # Initialize match status tracking dictionary
            match_status = {
                "has_required_item": False,
                "error_req_found": False,
                "error_opt_found": False,
                "stack_found": False,
            }

            # Process each signal in the list
            should_skip_error = False
            for signal in signal_list:
                # Process the signal and update match_status accordingly
                if self._process_signal(signal, crashlog_mainerror, segment_callstack_intact, match_status):
                    should_skip_error = True
                    break

            # Skip this error if a condition indicates we should
            if should_skip_error:
                continue

            # Determine if we have a match based on the processed signals
            if self._is_suspect_match(match_status):
                # Add the suspect to the report and update the found status
                formatted_error_name = error_name.ljust(max_warn_length, ".")
                lines.append(f"- **Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity}** \n\n")
                lines.append("-----\n")
                any_suspect_found = True

        return ReportFragment.from_lines(lines), any_suspect_found

    @staticmethod
    def _process_signal(signal: str, crashlog_mainerror: str, segment_callstack_intact: str, match_status: dict[str, bool]) -> bool:
        """
        Process an individual signal and update match status.

        Returns:
            True if processing should stop (NOT condition met)
        """
        # Constants for signal modifiers
        main_error_required = "ME-REQ"
        main_error_optional = "ME-OPT"
        callstack_negative = "NOT"

        if "|" not in signal:
            # Simple case: direct string match in callstack
            if signal in segment_callstack_intact:
                match_status["stack_found"] = True
            return False

        signal_modifier, signal_string = signal.split("|", 1)

        # Process based on signal modifier
        if signal_modifier == main_error_required:
            match_status["has_required_item"] = True
            if signal_string in crashlog_mainerror:
                match_status["error_req_found"] = True
        elif signal_modifier == main_error_optional:
            if signal_string in crashlog_mainerror:
                match_status["error_opt_found"] = True
        elif signal_modifier == callstack_negative:
            # Return True to break out of the loop if NOT condition is met
            return signal_string in segment_callstack_intact
        elif signal_modifier.isdecimal():
            # Check for minimum occurrences
            min_occurrences = int(signal_modifier)
            if segment_callstack_intact.count(signal_string) >= min_occurrences:
                match_status["stack_found"] = True

        return False

    @staticmethod
    def _is_suspect_match(match_status: dict[str, bool]) -> bool:
        """Determine if current error conditions constitute a suspect match."""
        if match_status["has_required_item"]:
            return match_status["error_req_found"]
        return match_status["error_opt_found"] or match_status["stack_found"]

    @staticmethod
    def _format_suspect_message(error_name: str, error_severity: str, max_warn_length: int) -> str:
        """Format a suspect message for the report."""
        formatted_error_name = error_name.ljust(max_warn_length, ".")
        return f"- **Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity}** \n\n-----\n"

    @staticmethod
    def check_dll_crash(crashlog_mainerror: str) -> ReportFragment:
        """
        Analyze a crash log to identify if a DLL file is implicated in the crash.

        Args:
            crashlog_mainerror: The main error message extracted from the crash log.

        Returns:
            ReportFragment containing DLL crash notification, or empty fragment.
        """
        crashlog_mainerror_lower = crashlog_mainerror.lower()
        if ".dll" in crashlog_mainerror_lower and "tbbmalloc" not in crashlog_mainerror_lower:
            return ReportFragment.from_lines([
                "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \n",
                "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n\n",
                "-----\n",
            ])
        return ReportFragment.empty()

"""
Suspect scanner module for CLASSIC.

This module scans for known crash patterns and suspects including:
- Checking main errors against known patterns
- Scanning call stacks for problematic signatures
- Identifying DLL-related crashes
- Matching against YAML-defined suspect patterns
"""

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.Util import append_or_extend

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

    def suspect_scan_mainerror(self, autoscan_report: list[str], crashlog_mainerror: str, max_warn_length: int) -> bool:
        """
        Scans the crash log for errors listed in a predefined suspect error list, updates the
        autoscan report upon detection, and determines if any suspects are found.

        Parameters:
        autoscan_report (list[str]): A list to store formatted strings of identified suspect
            errors and their associated details.
        crashlog_mainerror (str): The main error output from a crash log to scan for
            suspect errors.
        max_warn_length (int): The maximum length for formatting the error name in the autoscan
            report.

        Returns:
        bool: A boolean indicating whether any suspect errors were found in the crash log.
        """
        found_suspect = False

        for error_key, signal in self.yamldata.suspects_error_list.items():
            # Skip checking if signal not in crash log
            if signal not in crashlog_mainerror:
                continue

            # Parse error information
            error_severity, error_name = error_key.split(" | ", 1)

            # Format the error name for report
            formatted_error_name: str = error_name.ljust(max_warn_length, ".")

            # Add the error to the report
            report_entry: str = f"# Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n"
            append_or_extend(report_entry, autoscan_report)

            # Update suspect found status
            found_suspect = True

        return found_suspect

    def suspect_scan_stack(
        self, crashlog_mainerror: str, segment_callstack_intact: str, autoscan_report: list[str], max_warn_length: int
    ) -> bool:
        """
        Analyzes a crash report and call stack information to identify potential suspect errors
        and integrates findings into an autoscan report. The function evaluates signal
        criteria from a YAML configuration to detect mismatches, potential issues, and specific
        patterns in the provided crash log and call stack details.

        Parameters:
            crashlog_mainerror (str): The main error extracted from the crash log.
            segment_callstack_intact (str): The intact segment of the call stack relevant to the analysis.
            autoscan_report (list[str]): A mutable report list where detected suspects are appended.
            max_warn_length (int): Maximum allowed length for warnings included in the report.

        Returns:
            bool: Indicates whether any suspect has been identified and added to the autoscan report.
        """
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
                self._add_suspect_to_report(error_name, error_severity, max_warn_length, autoscan_report)
                any_suspect_found = True

        return any_suspect_found

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
    def _add_suspect_to_report(error_name: str, error_severity: str, max_warn_length: int, autoscan_report: list[str]) -> None:
        """Add a found suspect to the report with proper formatting."""
        formatted_error_name: str = error_name.ljust(max_warn_length, ".")
        message: str = f"# Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n"
        append_or_extend(message, autoscan_report)

    @staticmethod
    def check_dll_crash(crashlog_mainerror: str, autoscan_report: list[str]) -> None:
        """
        A static method designed to analyze a crash log and identify if a DLL file is implicated in the crash.
        The method evaluates the primary error message from the crash log to determine if it references a DLL
        file, excluding specific cases such as "tbbmalloc". If a potentially problematic DLL is detected, the
        method appends a formatted notification to the autoscan report.

        Arguments:
            crashlog_mainerror: str
                The main error message extracted from the crash log, which is inspected for DLL-related
                mentions.
            autoscan_report: list[str]
                A reference to a list where any relevant findings or alerts about the crash will be appended.

        Returns:
            None
        """
        crashlog_mainerror_lower: str = crashlog_mainerror.lower()
        if ".dll" in crashlog_mainerror_lower and "tbbmalloc" not in crashlog_mainerror_lower:
            append_or_extend(
                (
                    "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \n",
                    "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n-----\n",
                ),
                autoscan_report,
            )

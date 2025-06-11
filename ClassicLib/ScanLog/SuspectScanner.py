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
        
    def suspect_scan_mainerror(
        self, autoscan_report: list[str], crashlog_mainerror: str, max_warn_length: int
    ) -> bool:
        """
        Scan for main errors based on suspect error list.
        
        Args:
            autoscan_report: List to append detected errors
            crashlog_mainerror: Main error string from crash log
            max_warn_length: Maximum length for warning labels
            
        Returns:
            True if any suspect error was found
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
        Scan call stack for suspect patterns.
        
        Args:
            crashlog_mainerror: Main error string
            segment_callstack_intact: Complete call stack as string
            autoscan_report: List to append findings
            max_warn_length: Maximum length for formatting
            
        Returns:
            True if at least one suspect is found
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
    def _process_signal(
        signal: str, crashlog_mainerror: str, segment_callstack_intact: str, match_status: dict[str, bool]
    ) -> bool:
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
    def _add_suspect_to_report(
        error_name: str, error_severity: str, max_warn_length: int, autoscan_report: list[str]
    ) -> None:
        """Add a found suspect to the report with proper formatting."""
        formatted_error_name: str = error_name.ljust(max_warn_length, ".")
        message: str = f"# Checking for {formatted_error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n"
        append_or_extend(message, autoscan_report)
        
    @staticmethod
    def check_dll_crash(crashlog_mainerror: str, autoscan_report: list[str]) -> None:
        """
        Check if a DLL file was involved in the crash.
        
        Args:
            crashlog_mainerror: Main error string
            autoscan_report: List to append findings
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
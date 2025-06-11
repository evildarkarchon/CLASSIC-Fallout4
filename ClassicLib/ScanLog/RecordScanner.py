"""
Record scanner module for CLASSIC.

This module handles named record detection including:
- Finding named records in crash logs
- Matching against known record types
- Filtering ignored records
- Formatting record reports
"""

from collections import Counter
from typing import TYPE_CHECKING

from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.Util import append_or_extend

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class RecordScanner:
    """Handles scanning for named records in crash logs."""
    
    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initialize the record scanner.
        
        Args:
            yamldata: Configuration data containing record patterns
        """
        self.yamldata: ClassicScanLogsInfo = yamldata
        self.lower_records: set[str] = {record.lower() for record in yamldata.classic_records_list} or set()
        self.lower_ignore: set[str] = {record.lower() for record in yamldata.game_ignore_records} or set()
        
    def scan_named_records(
        self, segment_callstack: list[str], records_matches: list[str], autoscan_report: list[str]
    ) -> None:
        """
        Scan call stack segment for named records.
        
        Args:
            segment_callstack: List of call stack lines
            records_matches: List to store matched records
            autoscan_report: List to append analysis summary
        """
        # Constants
        rsp_marker = "[RSP+"
        rsp_offset = 30
        
        # Find matching records
        self._find_matching_records(segment_callstack, records_matches, rsp_marker, rsp_offset)
        
        # Report results
        if records_matches:
            self._report_found_records(records_matches, autoscan_report)
        else:
            append_or_extend("* COULDN'T FIND ANY NAMED RECORDS *\n\n", autoscan_report)
            
    def _find_matching_records(
        self, segment_callstack: list[str], records_matches: list[str], rsp_marker: str, rsp_offset: int
    ) -> None:
        """
        Extract matching records from the call stack.
        
        Args:
            segment_callstack: Call stack lines
            records_matches: List to append found records
            rsp_marker: Marker to identify RSP lines
            rsp_offset: Offset for extracting record data
        """
        for line in segment_callstack:
            lower_line: str = line.lower()
            
            # Check if line contains any target record and doesn't contain any ignored terms
            if any(item in lower_line for item in self.lower_records) and all(
                record not in lower_line for record in self.lower_ignore
            ):
                # Extract the relevant part of the line based on format
                if rsp_marker in line:
                    records_matches.append(line[rsp_offset:].strip())
                else:
                    records_matches.append(line.strip())
                    
    def _report_found_records(self, records_matches: list[str], autoscan_report: list[str]) -> None:
        """
        Format and add report entries for found records.
        
        Args:
            records_matches: List of found records
            autoscan_report: List to append formatted report
        """
        # Count and sort the records
        records_found: dict[str, int] = dict(Counter(sorted(records_matches)))
        
        # Add each record with its count
        for record, count in records_found.items():
            append_or_extend(f"- {record} | {count}\n", autoscan_report)
            
        # Add explanatory notes
        explanatory_notes: tuple[str, str, str] = (
            "\n[Last number counts how many times each Named Record shows up in the crash log.]\n",
            f"These records were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
            "Named records should give extra info on involved game objects, record types or mod files.\n\n",
        )
        append_or_extend(explanatory_notes, autoscan_report)
        
    def extract_records(self, segment_callstack: list[str]) -> list[str]:
        """
        Extract all matching records from call stack.
        
        Args:
            segment_callstack: List of call stack lines
            
        Returns:
            List of extracted record strings
        """
        records_matches = []
        
        # Constants
        rsp_marker = "[RSP+"
        rsp_offset = 30
        
        self._find_matching_records(segment_callstack, records_matches, rsp_marker, rsp_offset)
        
        return records_matches
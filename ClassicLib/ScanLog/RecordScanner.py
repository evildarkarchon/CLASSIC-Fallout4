"""
Record scanner module for CLASSIC.

This module handles named record detection including:
- Finding named records in crash logs
- Matching against known record types
- Filtering ignored records
- Formatting record reports
"""

from collections import Counter
from typing import TYPE_CHECKING, Any

from ClassicLib.ScanLog.ReportFragment import ReportFragment
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

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

    def scan_named_records(self, segment_callstack: list[str]) -> tuple[ReportFragment, list[str]]:
        """
        Scans named records in the provided segment callstack and identifies matches.

        Args:
            segment_callstack: The callstack to scan for named records.

        Returns:
            Tuple of (ReportFragment containing results, list of found records).
        """
        # Constants
        rsp_marker = "[RSP+"
        rsp_offset = 30

        records_matches: list[str] = []

        # Find matching records
        self._find_matching_records(segment_callstack, records_matches, rsp_marker, rsp_offset)

        # Generate report fragment
        if records_matches:
            fragment = self._generate_found_records_fragment(records_matches)
        else:
            fragment = ReportFragment.from_lines(["* COULDN'T FIND ANY NAMED RECORDS *\n\n"])

        return fragment, records_matches

    def _find_matching_records(self, segment_callstack: list[str], records_matches: list[str], rsp_marker: str, rsp_offset: int) -> None:
        """
        Finds and collects matching records from a given segment of a call stack based on specified criteria.

        This function processes each line in a provided segment of the call stack, checks whether the line contains any target
        records defined in the class's attributes, and excludes lines containing terms that should be ignored. If the line meets
        the criteria, the relevant part of the line is extracted and appended to a list of matching records.

        Parameters:
        segment_callstack: list of str
            A list of strings representing segment of the call stack to be analyzed.
        records_matches: list of str
            A list where matching record lines will be appended.
        rsp_marker: str
            A marker string to identify the relevant portion of the call stack lines.
        rsp_offset: int
            An integer representing the character offset from rsp_marker used to determine where to begin extracting record
            content.

        Returns:
        None
        """
        for line in segment_callstack:
            lower_line: str = line.lower()

            # Check if line contains any target record and doesn't contain any ignored terms
            if any(item in lower_line for item in self.lower_records) and all(record not in lower_line for record in self.lower_ignore):
                # Extract the relevant part of the line based on format
                if rsp_marker in line:
                    records_matches.append(line[rsp_offset:].strip())
                else:
                    records_matches.append(line.strip())

    def _generate_found_records_fragment(self, records_matches: list[str]) -> ReportFragment:
        """
        Generate report fragment for found records.

        Args:
            records_matches: List of found records

        Returns:
            ReportFragment containing formatted record report.
        """
        lines = []

        # Count and sort the records
        records_found: dict[str, int] = dict(Counter(sorted(records_matches)))

        # Add each record with its count
        for record, count in records_found.items():
            lines.append(f"- {record} | {count}\n")

        # Add explanatory notes
        lines.append("\n[Last number counts how many times each Named Record shows up in the crash log.]\n")
        lines.append(f"These records were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n")
        lines.append("Named records should give extra info on involved game objects, record types or mod files.\n\n")

        return ReportFragment.from_lines(lines)

    def extract_records(self, segment_callstack: list[str]) -> list[str]:
        """
        Extract records from a segment callstack based on specific matching criteria.

        This method processes a given segment callstack and identifies matching records
        based on predefined constants for marker and offset. Matching records are then
        collected and returned as a list.

        Args:
            segment_callstack (list[str]): The list of strings representing the segment
            callstack to be processed.

        Returns:
            list[str]: A list of strings containing the matching records identified from
            the segment callstack.
        """
        records_matches: list[Any] = []

        # Constants
        rsp_marker = "[RSP+"
        rsp_offset = 30

        self._find_matching_records(segment_callstack, records_matches, rsp_marker, rsp_offset)

        return records_matches

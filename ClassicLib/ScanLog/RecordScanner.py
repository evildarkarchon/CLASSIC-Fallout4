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

    def scan_named_records(self, segment_callstack: list[str], records_matches: list[str], autoscan_report: list[str]) -> None:
        """
        Scans named records in the provided segment callstack, identifies matches,
        and updates the autoscan report accordingly.

        This function processes the provided callstack to locate specific named
        records, utilizing defined markers and offsets. Any matches found are
        added to the records_matches list and subsequently reported in the
        autoscan report. If no matches are identified, a corresponding message
        is appended to the report.

        Arguments:
            segment_callstack (list[str]): The callstack to scan for named records.
            records_matches (list[str]): A list to hold records that match the scan criteria.
            autoscan_report (list[str]): The report to be updated based on scanning results.

        Returns:
            None
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

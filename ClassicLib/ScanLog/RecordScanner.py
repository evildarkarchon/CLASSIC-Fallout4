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
    """
    Manages operations for scanning, extracting, and generating reports of named records
    from provided callstack segments.

    The `RecordScanner` class is designed to process callstack segments, identify specific
    named records, optionally ignore specific ones, and generate formatted reports. It uses
    predefined configurations to match or ignore records and offers methods to extract or
    report findings efficiently.

    Attributes:
        yamldata (ClassicScanLogsInfo): Configuration data containing record patterns such
        as classic records list and ignore records.
        lower_records (set[str]): A set of lowercase named records to be searched for in
        the callstack.
        lower_ignore (set[str]): A set of lowercase named records to be ignored during the
        scanning process.
    """

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initializes the object with the provided YAML data and processes it.

        This constructor takes a `ClassicScanLogsInfo` instance as input, processes
        its records by converting them to lowercase, and stores these results into
        appropriate attributes. The processed attributes include `lower_records`
        which contains the lowercased versions of `classic_records_list`, and
        `lower_ignore` capturing the lowercased versions of `game_ignore_records`.

        Args:
            yamldata: An instance of ClassicScanLogsInfo containing classic scan logs
                data including lists of records and ignored records.
        """
        self.yamldata: ClassicScanLogsInfo = yamldata
        self.lower_records: set[str] = {record.lower() for record in yamldata.classic_records_list} or set()
        self.lower_ignore: set[str] = {record.lower() for record in yamldata.game_ignore_records} or set()

    def scan_named_records(self, segment_callstack: list[str]) -> tuple[ReportFragment, list[str]]:
        """
        Scans the provided callstack for named records and returns a report fragment
        along with the list of matching records.

        This function analyzes a given callstack to identify specific records
        matching the criteria defined within the method. It produces a report
        fragment summarizing the findings and a list of the matching records.

        Args:
            segment_callstack (list[str]): The callstack information, represented
                as a list of strings.

        Returns:
            tuple[ReportFragment, list[str]]: A tuple containing:
                - A ReportFragment describing the results of the scan.
                - A list of matching records found during the scan.
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
        Generates a ReportFragment containing a summary of found records, including their count and
        related explanatory notes. This function organizes the records, counts their occurrences, and
        provides a formatted output that aids in diagnosing crash logs.

        Args:
            records_matches (list[str]): List of Named Records matched during crash
                log analysis.

        Returns:
            ReportFragment: A ReportFragment object containing formatted lines with
                counted records and supplementary explanatory notes.
        """
        lines = []

        # Count and sort the records
        records_found: dict[str, int] = dict(Counter(sorted(records_matches)))

        # Add each record with its count
        for record, count in records_found.items():
            lines.append(f"- {record} | {count}\n")

        # Add explanatory notes
        lines.extend((
            "\n[Last number counts how many times each Named Record shows up in the crash log.]\n",
            f"These records were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
            "Named records should give extra info on involved game objects, record types or mod files.\n\n",
        ))

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

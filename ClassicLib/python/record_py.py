"""
Pure Python implementation of record scanning.

This module provides the fallback Python implementation for named record detection
and analysis when Rust acceleration is not available. It handles finding named
records in crash logs, matching against known types, and filtering operations.
"""

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ReportFragment import ReportFragment
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class PythonRecordScanner:
    """
    Pure Python implementation for scanning and analyzing named records from crash logs.

    This class provides the fallback implementation for processing callstack segments,
    identifying specific named records, optionally ignoring specific ones, and
    generating formatted reports.

    Attributes:
        yamldata: Configuration data containing record patterns.
        lower_records: Set of lowercase named records to search for.
        lower_ignore: Set of lowercase named records to ignore.
    """

    def __init__(self, yamldata: "ClassicScanLogsInfo") -> None:
        """
        Initializes the record scanner with provided YAML configuration.

        This constructor processes the configuration data by converting records
        to lowercase for case-insensitive matching.

        Args:
            yamldata: An instance of ClassicScanLogsInfo containing scan logs data
                     including lists of records and ignored records.
        """
        self.yamldata = yamldata
        self.lower_records = {record.lower() for record in yamldata.classic_records_list} or set()
        self.lower_ignore = {record.lower() for record in yamldata.game_ignore_records} or set()

    def scan_named_records(self, segment_callstack: list[str]) -> tuple["ReportFragment", list[str]]:
        """
        Scans the provided callstack for named records and returns a report.

        This function analyzes a given callstack to identify specific records
        matching the criteria. It produces a report fragment summarizing the
        findings and a list of the matching records.

        Args:
            segment_callstack: The callstack information as a list of strings.

        Returns:
            tuple containing:
                - A ReportFragment describing the results of the scan.
                - A list of matching records found during the scan.
        """
        from ClassicLib.ScanLog.ReportFragment import ReportFragment

        # Constants for record extraction
        rsp_marker = "[RSP+"
        rsp_offset = 30

        records_matches = []

        # Find matching records
        self._find_matching_records(segment_callstack, records_matches, rsp_marker, rsp_offset)

        # Generate report fragment
        if records_matches:
            fragment = self._generate_found_records_fragment(records_matches)
        else:
            fragment = ReportFragment.from_lines(["* COULDN'T FIND ANY NAMED RECORDS *\n\n"])

        return fragment, records_matches

    def _find_matching_records(
        self, segment_callstack: list[str], records_matches: list[str], rsp_marker: str, rsp_offset: int
    ) -> None:
        """
        Finds and collects matching records from a call stack segment.

        This function processes each line in the call stack, checks whether the line
        contains any target records, and excludes lines containing ignored terms.
        If the line meets criteria, the relevant part is extracted and appended.

        Args:
            segment_callstack: List of strings representing the call stack segment.
            records_matches: List where matching record lines will be appended.
            rsp_marker: Marker string to identify relevant portions of lines.
            rsp_offset: Character offset from rsp_marker for extraction.
        """
        for line in segment_callstack:
            lower_line = line.lower()

            # Check if line contains any target record and doesn't contain any ignored terms
            if any(item in lower_line for item in self.lower_records) and all(
                record not in lower_line for record in self.lower_ignore
            ):
                # Extract the relevant part of the line based on format
                if rsp_marker in line:
                    records_matches.append(line[rsp_offset:].strip())
                else:
                    records_matches.append(line.strip())

    def _generate_found_records_fragment(self, records_matches: list[str]) -> "ReportFragment":
        """
        Generates a ReportFragment containing a summary of found records.

        This function organizes the records, counts their occurrences, and provides
        a formatted output that aids in diagnosing crash logs.

        Args:
            records_matches: List of Named Records matched during analysis.

        Returns:
            ReportFragment: Object containing formatted lines with counted records.
        """
        from ClassicLib.ScanLog.ReportFragment import ReportFragment

        lines = []

        # Count and sort the records
        records_found = dict(Counter(sorted(records_matches)))

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
        based on predefined constants for marker and offset.

        Args:
            segment_callstack: List of strings representing the segment callstack.

        Returns:
            list[str]: List containing the matching records identified.
        """
        records_matches = []

        # Constants for record extraction
        rsp_marker = "[RSP+"
        rsp_offset = 30

        self._find_matching_records(segment_callstack, records_matches, rsp_marker, rsp_offset)

        return records_matches

# Alias for compatibility
RecordScanner = PythonRecordScanner

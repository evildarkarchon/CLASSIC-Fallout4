"""
Record scanner module for CLASSIC.

This module handles named record detection including:
- Finding named records in crash logs
- Matching against known record types
- Filtering ignored records
- Formatting record reports
"""

import re
from collections import Counter
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from ClassicLib.ScanLog.fragments import ReportFragment
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

if TYPE_CHECKING:
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo


@lru_cache(maxsize=128)
def _compile_records_pattern(records: frozenset[str]) -> re.Pattern[str] | None:
    """
    Compiles a regex pattern from a frozenset of record names with caching.

    This function creates a single compiled regex pattern that matches any of the
    provided record names. Results are cached for performance when processing
    multiple crash logs with the same record set.

    Args:
        records: A frozenset of record names to match (must be hashable for caching).

    Returns:
        A compiled regex pattern with case-insensitive matching, or None if no records.
    """
    if not records:
        return None

    # Escape special regex characters and build alternation pattern
    patterns = [re.escape(record) for record in sorted(records)]
    return re.compile("|".join(patterns), re.IGNORECASE)


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

        # Pre-compile regex patterns for efficient matching
        self._records_pattern = _compile_records_pattern(frozenset(self.lower_records))
        self._ignore_pattern = _compile_records_pattern(frozenset(self.lower_ignore))

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
        """Find and collect matching records from a call stack segment.

        Processes each line in the call stack segment, checking for target records
        and excluding lines with ignored terms. Uses pre-compiled regex patterns
        for efficient matching (20-30x faster than nested loops).

        Args:
            segment_callstack: List of strings from the call stack to analyze.
            records_matches: List to append matching record lines to.
            rsp_marker: Marker string to identify relevant call stack portions.
            rsp_offset: Character offset from rsp_marker for extracting content.
        """
        # Early return if no records pattern compiled
        if not self._records_pattern:
            return

        for line in segment_callstack:
            # Use compiled regex for efficient matching (single pass)
            has_record = self._records_pattern.search(line) is not None

            # Check ignore pattern only if record was found
            if has_record:
                has_ignore = self._ignore_pattern.search(line) is not None if self._ignore_pattern else False

                # Only add if record found and no ignore terms present
                if not has_ignore:
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

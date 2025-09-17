"""
Backwards compatibility wrapper for fragment-based report generation.

This module provides FragmentCollector which maintains a list-like interface
while internally using the fragment-based approach for gradual migration.
"""

from __future__ import annotations

from ClassicLib.ScanLog.fragments.report_composer import ReportComposer
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment


class FragmentCollector:
    """
    Provides a backwards-compatible interface that looks like a list
    but internally uses fragments.

    This allows gradual migration from the mutable list approach.
    """

    def __init__(self) -> None:
        """
        Initializes an instance of the class.

        This constructor initializes the attributes required for managing report
        fragments and pending lines.

        Attributes:
            _fragments (list[ReportFragment]): Internal storage for report fragments.
            _pending_lines (list[str]): Internal storage for pending lines to be handled.
        """
        self._fragments: list[ReportFragment] = []
        self._pending_lines: list[str] = []

    def append(self, line: str) -> None:
        """
        Appends a line to the pending lines list.

        This method adds the provided line to the internal list of pending lines. It does not
        return any value but modifies the internal state by appending the input line.

        Args:
            line (str): The line to be added to the pending lines list.
        """
        self._pending_lines.append(line)

    def extend(self, lines: list[str] | tuple[str, ...]) -> None:
        """
        Extends the existing list of pending lines with the given lines.

        Args:
            lines (list[str] | tuple[str, ...]): A list or tuple of strings to be added to
                the pending lines.
        """
        self._pending_lines.extend(lines)

    def insert(self, index: int, line: str) -> None:
        """
        Inserts a line into the internal pending lines at the given index.

        This method is used to handle fragment-based insertion by adding a
        new line into the pending lines list at a specific index. It ensures
        that all pending operations are flushed before performing the insertion.

        Args:
            index (int): The position at which the line will be inserted.
            line (str): The line to be inserted.

        """
        # Convert to fragment-based insertion
        self._flush_pending()
        # This is complex to handle properly, but for migration we can track it
        self._pending_lines.insert(index, line)

    def _flush_pending(self) -> None:
        """
        Flushes all pending lines into fragments.

        This method checks if there are any pending lines to be processed. If found,
        it converts these lines into a ReportFragment and appends it to the fragments
        list. After processing, it clears the pending lines.
        """
        if self._pending_lines:
            self._fragments.append(ReportFragment.from_lines(self._pending_lines))
            self._pending_lines = []

    def to_fragment(self) -> ReportFragment:
        """
        Converts the current state of the report into a ReportFragment.

        This method finalizes any pending operations and consolidates all
        available fragments into a single ReportFragment. The consolidated
        ReportFragment can then be utilized for further processing or output.

        Returns:
            ReportFragment: The finalized report fragment containing all
            processed information.
        """
        self._flush_pending()
        return ReportComposer.compose(*self._fragments)

    def to_list(self) -> list[str]:
        """
        Converts the object into a list of strings using its fragment representation.

        This method utilizes the `to_fragment` method of the current object to
        retrieve a fragment representation, which is then converted into a list
        of strings.

        Returns:
            list[str]: A list of strings obtained from the fragment representation.
        """
        return self.to_fragment().to_list()

    def __len__(self) -> int:
        """
        Calculates the total length of the content held within the object.

        The method computes the sum of the lengths of all fragments and any
        pending lines. It ensures that pending operations are processed before
        calculating the total length.

        Returns:
            int: The total length of content.
        """
        self._flush_pending()
        total_len = sum(len(f.content) for f in self._fragments)
        return total_len + len(self._pending_lines)

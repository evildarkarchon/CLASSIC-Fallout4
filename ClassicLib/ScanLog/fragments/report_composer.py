"""Report composer for functional fragment composition.

This module provides the ReportComposer class that handles
composing multiple report fragments in a functional way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment

if TYPE_CHECKING:
    from collections.abc import Callable


class ReportComposer:
    """A utility class for composing and managing report fragments.

    This class provides methods for composing multiple fragments into a single
    report fragment and creating conditional sections with dynamic headers.

    Methods in this class are static and designed to work with the `ReportFragment`
    type. They are intended to provide seamless operations for managing report
    generation workflows.
    """

    @staticmethod
    def compose(*fragments: ReportFragment) -> ReportFragment:
        """Composes multiple ReportFragment objects into a single ReportFragment.
        The method takes a variable number of ReportFragment arguments
        and combines them using the addition operation.

        Args:
            *fragments (ReportFragment): Variable number of ReportFragment
                objects to be composed.

        Returns:
            ReportFragment: A single ReportFragment that represents
                the combination of all input fragments.

        """
        result = ReportFragment.empty()
        for fragment in fragments:
            result += fragment
        return result

    @staticmethod
    def conditional_section(
        generator_func: Callable[[], ReportFragment],
        header_func: Callable[[], list[str] | tuple[str, ...]],
    ) -> ReportFragment:
        """Generate a conditional report fragment with an optional header.

        This method executes a generator function to produce a report fragment. If the
        generated fragment contains content, it appends a header to the fragment using
        the provided header function. If the fragment does not contain any content, it
        is returned as is without a header.

        Args:
            generator_func (Callable[[], ReportFragment]): A callable that generates
                a `ReportFragment` instance.
            header_func (Callable[[], list[str] | tuple[str, ...]]): A callable that
                generates the header for the report fragment.

        Returns:
            ReportFragment: The resulting report fragment, potentially including a
            header if the fragment has content.

        """
        fragment = generator_func()
        if fragment.has_content:
            return fragment.with_header(header_func())
        return fragment

"""
Report composer for combining multiple fragments.

This module provides the ReportComposer class for composing
multiple report fragments into a complete report.
"""

from collections.abc import Callable

from ClassicLib.ScanLog.ReportFragment import ReportFragment
from .conditional_section import ConditionalSection


class ReportComposer:
    """Composes multiple report fragments into a complete report."""

    def __init__(self) -> None:
        """Initialize the report composer."""
        self.fragments: list[ReportFragment] = []

    def add(self, fragment: ReportFragment) -> "ReportComposer":
        """
        Add a fragment to the report.

        Args:
            fragment: The fragment to add

        Returns:
            Self for method chaining
        """
        self.fragments.append(fragment)
        return self

    def add_conditional(
        self,
        content_generator: Callable[[], ReportFragment],
        header_text: str,
    ) -> "ReportComposer":
        """
        Add a conditional section with header.

        Args:
            content_generator: Function that generates the content
            header_text: Header text to use if content exists

        Returns:
            Self for method chaining
        """
        fragment = ConditionalSection.with_header(content_generator, header_text)
        self.fragments.append(fragment)
        return self

    def add_conditional_custom(
        self,
        content_generator: Callable[[], ReportFragment],
        header_generator: Callable[[], ReportFragment],
    ) -> "ReportComposer":
        """
        Add a conditional section with custom header.

        Args:
            content_generator: Function that generates the content
            header_generator: Function that generates the header

        Returns:
            Self for method chaining
        """
        fragment = ConditionalSection.with_custom_header(content_generator, header_generator)
        self.fragments.append(fragment)
        return self

    def compose(self) -> ReportFragment:
        """
        Compose all fragments into a single fragment.

        Returns:
            Combined fragment containing all added fragments
        """
        if not self.fragments:
            return ReportFragment.empty()

        result = self.fragments[0]
        for fragment in self.fragments[1:]:
            result = result + fragment

        return result

    def build(self) -> ReportFragment:
        """
        Build the final composed fragment.

        Returns:
            Combined fragment containing all added fragments
        """
        return self.compose()

    def to_list(self) -> list[str]:
        """
        Compose fragments and convert to list.

        Returns:
            List of strings representing the complete report
        """
        return self.compose().to_list()

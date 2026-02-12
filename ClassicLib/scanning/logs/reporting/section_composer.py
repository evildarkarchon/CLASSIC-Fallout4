"""Report composer for combining multiple fragments.

This module provides the ReportComposer class for composing
multiple report fragments into a complete report. Delegates to
Rust-accelerated ReportComposer for high-performance composition.
"""

from collections.abc import Callable

from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
from ClassicLib.integration.rust.report_rust import ReportFragment
from ClassicLib.scanning.logs.reporting.conditional_section import ConditionalSection


class ReportComposer:
    """Compose report fragments into a cohesive structure.

    Delegates to Rust-accelerated ReportComposer for parallel fragment
    processing with string interning. Supports method chaining and
    conditional section additions.
    """

    def __init__(self) -> None:
        self._inner = RustAcceleratedReportComposer()

    def add(self, fragment: ReportFragment) -> "ReportComposer":
        """Add a report fragment to the composer.

        Args:
            fragment: The report fragment to add.

        Returns:
            ReportComposer: Self for method chaining.

        """
        self._inner.add(fragment)
        return self

    def add_conditional(
        self,
        content_generator: Callable[[], ReportFragment],
        header_text: str,
    ) -> "ReportComposer":
        """Add a conditional section that includes a header only if content exists.

        Args:
            content_generator: Callable that generates the content fragment.
            header_text: Header text for the conditional section.

        Returns:
            ReportComposer: Self for method chaining.

        """
        fragment = ConditionalSection.with_header(content_generator, header_text)
        self._inner.add(fragment)
        return self

    def add_conditional_custom(
        self,
        content_generator: Callable[[], ReportFragment],
        header_generator: Callable[[], ReportFragment],
    ) -> "ReportComposer":
        """Add a conditional section with a custom header fragment.

        Args:
            content_generator: Callable that generates the content fragment.
            header_generator: Callable that generates the header fragment.

        Returns:
            ReportComposer: Self for method chaining.

        """
        fragment = ConditionalSection.with_custom_header(content_generator, header_generator)
        self._inner.add(fragment)
        return self

    def compose(self) -> ReportFragment:
        """Compose all fragments into a single ReportFragment.

        Returns:
            ReportFragment: The combined result of all added fragments.

        """
        return self._inner.compose()

    def build(self) -> ReportFragment:
        """Alias for compose().

        Returns:
            ReportFragment: The combined result of all added fragments.

        """
        return self._inner.build()

    def to_list(self) -> list[str]:
        """Compose and convert to a list of strings.

        Returns:
            list[str]: All report lines as strings.

        """
        return self._inner.to_list()

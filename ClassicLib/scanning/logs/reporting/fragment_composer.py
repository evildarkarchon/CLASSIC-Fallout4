"""Report composer for functional fragment composition.

Delegates to the Rust-accelerated ReportFragment from the integration layer
when available. Provides compose() and conditional_section() static methods
for combining report fragments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.integration.rust.report_rust import ReportFragment

if TYPE_CHECKING:
    from collections.abc import Callable


class ReportComposer:
    """A utility class for composing and managing report fragments.

    Uses Rust-accelerated ReportFragment operations when available.
    """

    @staticmethod
    def compose(*fragments: ReportFragment) -> ReportFragment:
        """Compose multiple ReportFragment objects into a single ReportFragment.

        Args:
            *fragments (ReportFragment): Variable number of ReportFragment
                objects to be composed.

        Returns:
            ReportFragment: A single ReportFragment combining all input fragments.

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

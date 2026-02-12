"""Conditional section utilities for report composition.

This module provides utilities for creating report sections with
headers that only appear when content exists. Uses Rust-accelerated
ReportGenerator for header generation and ReportFragment.with_header()
for efficient fragment composition.
"""

from collections.abc import Callable

from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator
from ClassicLib.integration.rust.report_rust import ReportFragment

# Shared generator instance for header generation
_report_generator = RustAcceleratedReportGenerator()


class ConditionalSection:
    """Conditional report section builder.

    Generates sections with headers that only appear when content exists,
    using Rust-accelerated ReportFragment.with_header() for composition.
    """

    @staticmethod
    def with_header(
        content_generator: Callable[[], ReportFragment],
        header_text: str | None,
        header_generator: Callable[[], ReportFragment] | None = None,
    ) -> ReportFragment:
        """Generate a section with header only if content exists.

        Args:
            content_generator: Function that generates the content fragment.
            header_text: The header text to prepend if content exists.
            header_generator: Optional custom header generator function.

        Returns:
            Combined fragment with header if content exists, or the content fragment.

        """
        content = content_generator()

        if content.has_content:
            if header_generator:
                header = header_generator()
            elif header_text:
                header = _report_generator.generate_mod_check_header(header_text)
            else:
                return content
            return header + content

        return content

    @staticmethod
    def with_custom_header(
        content_generator: Callable[[], ReportFragment],
        header_generator: Callable[[], ReportFragment],
    ) -> ReportFragment:
        """Generate a section with a custom header only if content exists.

        Args:
            content_generator: Function that generates the content fragment.
            header_generator: Function that generates the header fragment.

        Returns:
            Combined fragment if content exists, otherwise the empty content fragment.

        """
        content = content_generator()

        if content.has_content:
            header = header_generator()
            return header + content

        return content


def conditional_mod_section(
    detector_func: Callable[[], ReportFragment],
    check_type: str,
) -> ReportFragment:
    """Create a mod detection section with conditional header.

    Args:
        detector_func: Function that detects mods and returns a fragment.
        check_type: The type of check (e.g., "CONFLICT (TOGETHER)", "FREQUENTLY CRASH").

    Returns:
        Fragment with header if mods detected, or empty fragment.

    """
    return ConditionalSection.with_header(detector_func, check_type)

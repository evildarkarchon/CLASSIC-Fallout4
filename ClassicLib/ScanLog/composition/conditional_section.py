"""
Conditional section utilities for report composition.

This module provides utilities for creating report sections with
headers that only appear when content exists.
"""

from collections.abc import Callable

from ClassicLib.ScanLog.ReportFragment import ReportFragment
from ClassicLib.ScanLog.ReportGenerator import ReportGeneratorFragments


class ConditionalSection:
    """Helper for creating sections with conditional headers."""

    @staticmethod
    def with_header(
        content_generator: Callable[[], ReportFragment],
        header_text: str | None,
        header_generator: Callable[[], ReportFragment] | None = None,
    ) -> ReportFragment:
        """
        Generate a section with header only if content exists.

        This replaces the pattern of:
        1. Save list length
        2. Call function that might add content
        3. Check if content was added
        4. Retroactively insert header

        Args:
            content_generator: Function that generates the content fragment
            header_text: The header text to prepend if content exists (or None to use header_generator)
            header_generator: Optional custom header generator function

        Returns:
            Combined fragment with header if content exists, or empty fragment
        """
        content = content_generator()

        if content.has_content:
            if header_generator:
                header = header_generator()
            elif header_text:
                header = ReportGeneratorFragments.generate_mod_check_header(header_text)
            else:
                return content
            return header + content

        return content

    @staticmethod
    def with_custom_header(
        content_generator: Callable[[], ReportFragment],
        header_generator: Callable[[], ReportFragment],
    ) -> ReportFragment:
        """
        Generate a section with custom header fragment only if content exists.

        Args:
            content_generator: Function that generates the content fragment
            header_generator: Function that generates the header fragment

        Returns:
            Combined fragment with header if content exists, or empty fragment
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
    """
    Create a mod detection section with conditional header.

    This is a convenience function for the common pattern of:
    - Running a mod detector
    - Adding a header only if mods were detected

    Args:
        detector_func: Function that detects mods and returns a fragment
        check_type: The type of check (e.g., "CONFLICT (TOGETHER)", "FREQUENTLY CRASH")

    Returns:
        Fragment with header if mods detected, or empty fragment
    """
    return ConditionalSection.with_header(detector_func, check_type)

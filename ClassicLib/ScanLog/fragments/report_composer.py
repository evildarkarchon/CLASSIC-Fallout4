"""
Report composer for functional fragment composition.

This module provides the ReportComposer class that handles
composing multiple report fragments in a functional way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .report_fragment import ReportFragment

if TYPE_CHECKING:
    from collections.abc import Callable


class ReportComposer:
    """
    Composes report fragments in a functional way.

    This replaces passing a mutable list to every method.
    """

    @staticmethod
    def compose(*fragments: ReportFragment) -> ReportFragment:
        """Compose multiple fragments into one."""
        result = ReportFragment.empty()
        for fragment in fragments:
            result = result + fragment
        return result

    @staticmethod
    def conditional_section(
        generator_func: Callable[[], ReportFragment],
        header_func: Callable[[], list[str] | tuple[str, ...]],
    ) -> ReportFragment:
        """
        Generate a section with conditional header.

        This replaces the pattern of:
        1. Save list length
        2. Call function that might add content
        3. Check if content was added
        4. Retroactively insert header
        """
        fragment = generator_func()
        if fragment.has_content:
            return fragment.with_header(header_func())
        return fragment

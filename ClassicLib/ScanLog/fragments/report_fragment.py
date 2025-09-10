"""
Immutable report fragment for functional report generation.

This module provides the core ReportFragment dataclass that represents
an immutable piece of a report that can be composed with others.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportFragment:
    """
    Immutable report fragment that can be composed with others.

    This replaces the mutable list approach with functional composition.
    """

    content: tuple[str, ...]  # Immutable tuple instead of mutable list
    has_content: bool  # Explicitly track if meaningful content exists

    @classmethod
    def empty(cls) -> ReportFragment:
        """Create an empty fragment."""
        return cls(content=(), has_content=False)

    @classmethod
    def from_lines(cls, lines: list[str] | tuple[str, ...], check_content: bool = True) -> ReportFragment:
        """
        Create a fragment from lines.

        Args:
            lines: The content lines
            check_content: If True, sets has_content based on whether lines exist
        """
        content = tuple(lines) if isinstance(lines, list) else lines
        has_content = bool(content) if check_content else True
        return cls(content=content, has_content=has_content)

    def with_header(self, header_lines: list[str] | tuple[str, ...]) -> ReportFragment:
        """
        Add a header to this fragment (only if it has content).

        This replaces the retroactive header insertion pattern.
        """
        if not self.has_content:
            return self

        header_tuple = tuple(header_lines) if isinstance(header_lines, list) else header_lines
        return ReportFragment(content=header_tuple + self.content, has_content=True)

    def __add__(self, other: ReportFragment) -> ReportFragment:
        """Combine two fragments."""
        if not self.has_content and not other.has_content:
            return ReportFragment.empty()

        return ReportFragment(content=self.content + other.content, has_content=self.has_content or other.has_content)

    def to_list(self) -> list[str]:
        """Convert to mutable list for backwards compatibility."""
        return list(self.content)

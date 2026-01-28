"""Immutable report fragment for functional report generation.

This module provides the core ReportFragment dataclass that represents
an immutable piece of a report that can be composed with others.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportFragment:
    """Represent an immutable fragment of a report.

    This class is designed to handle sections of a report in a structured way, ensuring immutability
    and easy combinability. It allows for creating fragments from a series of strings, adding headers
    to existing fragments, and combining multiple fragments. Additionally, it provides a mechanism
    to convert the immutable fragments back to a mutable list, maintaining compatibility with legacy
    code where necessary.

    Attributes:
        content (tuple[str, ...]): The immutable sequence of strings constituting the fragment's content.
        has_content (bool): Indicates whether the fragment contains meaningful content.

    """

    content: tuple[str, ...]  # Immutable tuple instead of mutable list
    has_content: bool  # Explicitly track if meaningful content exists

    @classmethod
    def empty(cls) -> ReportFragment:
        """Create an empty instance of the `ReportFragment` class with predefined
        default values.

        Args:
            cls (Type[ReportFragment]): The class itself, automatically passed by
                Python when invoking a class method.

        Returns:
            ReportFragment: A new `ReportFragment` instance with `content` as an
            empty tuple and `has_content` set to `False`.

        """
        return cls(content=(), has_content=False)

    @classmethod
    def from_lines(cls, lines: list[str] | tuple[str, ...], check_content: bool = True) -> ReportFragment:
        """Create a new instance of ReportFragment based on the given lines of content.

        Lines can be provided as either a list or tuple of strings. This method also allows
        an option to validate the existence of content within the lines. If `check_content`
        is True, the method evaluates the content for presence before instantiating the class.

        Args:
            lines (list[str] | tuple[str, ...]): The lines of text to be used as content for
                the ReportFragment instance. Can be provided as a list or tuple of strings.
            check_content (bool, optional): A flag indicating whether to check if the content
                is present. If False, the content presence check is skipped. Defaults to True.

        Returns:
            ReportFragment: An instance of ReportFragment initialized with the provided content.

        """
        content = tuple(lines) if isinstance(lines, list) else lines
        has_content = bool(content) if check_content else True
        return cls(content=content, has_content=has_content)

    def with_header(self, header_lines: list[str] | tuple[str, ...]) -> ReportFragment:
        """Append header lines to the content of the ReportFragment if it already contains content.

        If the `ReportFragment` instance has content, this method prepends the provided header
        lines to the current content and returns a new `ReportFragment` instance with the updated
        content. Otherwise, it returns the current instance without any modifications.

        Args:
            header_lines (list[str] | tuple[str, ...]): A list or tuple of strings to prepend
                as header lines to the current content.

        Returns:
            ReportFragment: A new `ReportFragment` instance with the header lines added to
            the content if `has_content` is True. If `has_content` is False, the existing
            instance is returned unmodified.

        """
        if not self.has_content:
            return self

        header_tuple = tuple(header_lines) if isinstance(header_lines, list) else header_lines
        return ReportFragment(content=header_tuple + self.content, has_content=True)

    def __add__(self, other: ReportFragment) -> ReportFragment:
        """Add two ReportFragment objects and returns a new ReportFragment object.

        If both fragments being added have no content, an empty ReportFragment
        object is returned. Otherwise, combines the content of both fragments and
        determines if the resulting fragment contains content.

        Args:
            other (ReportFragment): Another ReportFragment object to add.

        Returns:
            ReportFragment: A new ReportFragment object resulting from the addition
            of the two fragments.

        """
        if not self.has_content and not other.has_content:
            return ReportFragment.empty()

        return ReportFragment(content=self.content + other.content, has_content=self.has_content or other.has_content)

    def __len__(self) -> int:
        """Return the number of lines in this fragment.

        Returns:
            int: The number of content lines.

        """
        return len(self.content)

    def __bool__(self) -> bool:
        """Return whether this fragment has meaningful content.

        Returns:
            bool: True if the fragment has content.

        """
        return self.has_content

    def to_list(self) -> list[str]:
        """Convert the content of the object into a list of strings.

        This method takes the content attribute and converts it into a list of
        individual strings. It is particularly useful for breaking down the content
        into manageable parts if it is stored as a sequence.

        Returns:
            list[str]: A list containing each element of the content as a string.

        """
        return list(self.content)

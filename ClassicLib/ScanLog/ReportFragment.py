"""
Report fragment system for functional report generation.

This module provides a functional approach to report generation where each
component returns its contribution as a fragment, eliminating the need for
shared mutable state while maintaining identical output format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


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


# Adapter functions for backwards compatibility
def detect_mods_single_fragment(
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
) -> ReportFragment:
    """
    Functional version of detect_mods_single that returns a fragment.

    This is what the refactored version would look like.
    """
    lines = []
    found_count = 0

    for mod_name, mod_description in yaml_dict.items():
        # Check if all required plugins are present
        if "|" in mod_name:
            required_plugins = [p.strip() for p in mod_name.split("|")]
            if not all(any(p.lower() in plugin.lower() for plugin in crashlog_plugins) for p in required_plugins):
                continue
        # Single plugin check
        elif not any(mod_name.lower() in plugin.lower() for plugin in crashlog_plugins):
            continue

        # Add the warning for this mod
        lines.append(f"* ⚠️ {mod_description}\n")
        found_count += 1

    if found_count > 0:
        lines.append("\n")

    return ReportFragment.from_lines(lines)


def generate_mod_check_header_fragment(check_type: str) -> tuple[str, ...]:
    """Generate header lines for mod check sections."""
    return (f"### Checking For Mods That {check_type}\n\n",)


# Backwards compatibility wrapper
class FragmentCollector:
    """
    Provides a backwards-compatible interface that looks like a list
    but internally uses fragments.

    This allows gradual migration from the mutable list approach.
    """

    def __init__(self) -> None:
        self._fragments: list[ReportFragment] = []
        self._pending_lines: list[str] = []

    def append(self, line: str) -> None:
        """Append a line (for compatibility)."""
        self._pending_lines.append(line)

    def extend(self, lines: list[str] | tuple[str, ...]) -> None:
        """Extend with multiple lines (for compatibility)."""
        self._pending_lines.extend(lines)

    def insert(self, index: int, line: str) -> None:
        """Insert at index (for compatibility)."""
        # Convert to fragment-based insertion
        self._flush_pending()
        # This is complex to handle properly, but for migration we can track it
        self._pending_lines.insert(index, line)

    def _flush_pending(self) -> None:
        """Flush pending lines to a fragment."""
        if self._pending_lines:
            self._fragments.append(ReportFragment.from_lines(self._pending_lines))
            self._pending_lines = []

    def to_fragment(self) -> ReportFragment:
        """Convert to a single fragment."""
        self._flush_pending()
        return ReportComposer.compose(*self._fragments)

    def to_list(self) -> list[str]:
        """Get as list for final output."""
        return self.to_fragment().to_list()

    def __len__(self) -> int:
        """Get total length (for compatibility)."""
        self._flush_pending()
        total_len = sum(len(f.content) for f in self._fragments)
        return total_len + len(self._pending_lines)


# Example of how to refactor a method to use fragments
class ReportGeneratorFunctional:
    """Functional version of ReportGenerator that returns fragments."""

    @staticmethod
    def generate_header(crashlog_filename: str, version: str) -> ReportFragment:
        """Generate header as a fragment."""
        return ReportFragment.from_lines([
            f"# {crashlog_filename}\n",
            f"**AUTOSCAN REPORT GENERATED BY {version}**\n\n",
            "> **FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR**\n\n",
            "> **PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES**\n\n",
            "---\n\n",
        ])

    @staticmethod
    def generate_error_section(
        main_error: str,
        crashgen_version: str,
        crashgen_name: str,
        is_latest: bool,
        warn_outdated: str,
    ) -> ReportFragment:
        """Generate error section as a fragment."""
        lines = [
            "### Error Information\n\n",
            f"**Main Error:** {main_error}\n\n",
            f"**Detected {crashgen_name} Version:** {crashgen_version}\n\n",
        ]

        if is_latest:
            lines.append(f"✅ *You have the latest version of {crashgen_name}!*\n\n")
        else:
            lines.append(f"⚠️ {warn_outdated}\n\n")

        return ReportFragment.from_lines(lines)

    @staticmethod
    def generate_suspect_section(found_suspects: list[str]) -> ReportFragment:
        """Generate suspect section with conditional header."""
        if not found_suspects:
            return ReportFragment.from_lines([
                "### Checking If Log Matches Any Known Crash Suspects\n\n",
                "# FOUND NO CRASH ERRORS / SUSPECTS THAT MATCH THE CURRENT DATABASE #\n",
                "Check below for mods that can cause frequent crashes and other problems.\n\n",
            ])

        lines = ["### Checking If Log Matches Any Known Crash Suspects\n\n"]
        lines.extend(found_suspects)
        lines.extend([
            "* FOR DETAILED DESCRIPTIONS AND POSSIBLE SOLUTIONS TO ANY ABOVE DETECTED CRASH SUSPECTS *\n",
            "* SEE: https://docs.google.com/document/d/17FzeIMJ256xE85XdjoPvv_Zi3C5uHeSTQh6wOZugs4c *\n\n",
        ])

        return ReportFragment.from_lines(lines)

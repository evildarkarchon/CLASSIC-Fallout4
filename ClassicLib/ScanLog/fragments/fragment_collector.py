"""
Backwards compatibility wrapper for fragment-based report generation.

This module provides FragmentCollector which maintains a list-like interface
while internally using the fragment-based approach for gradual migration.
"""

from __future__ import annotations

from .report_composer import ReportComposer
from .report_fragment import ReportFragment


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

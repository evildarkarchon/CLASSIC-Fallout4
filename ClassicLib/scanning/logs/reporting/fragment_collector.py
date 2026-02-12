"""Backwards compatibility wrapper for fragment-based report generation.

Provides FragmentCollector which maintains a list-like interface while
internally using Rust-accelerated ReportFragment from the integration layer.
"""

from __future__ import annotations

from ClassicLib.integration.rust.report_rust import ReportFragment
from ClassicLib.scanning.logs.reporting.fragment_composer import ReportComposer


class FragmentCollector:
    """Provide a backwards-compatible interface that looks like a list
    but internally uses Rust-accelerated fragments.
    """

    def __init__(self) -> None:
        """Initialize fragment collector with empty state."""
        self._fragments: list[ReportFragment] = []
        self._pending_lines: list[str] = []

    def append(self, line: str) -> None:
        """Append a line to the internal pending lines buffer."""
        self._pending_lines.append(line)

    def extend(self, lines: list[str] | tuple[str, ...]) -> None:
        """Extend the pending lines with the provided lines."""
        self._pending_lines.extend(lines)

    def insert(self, index: int, line: str) -> None:
        """Insert a line at the given index."""
        self._flush_pending()
        self._pending_lines.insert(index, line)

    def _flush_pending(self) -> None:
        """Flush pending lines into a ReportFragment."""
        if self._pending_lines:
            self._fragments.append(ReportFragment.from_lines(self._pending_lines))
            self._pending_lines = []

    def to_fragment(self) -> ReportFragment:
        """Compose all fragments into a single ReportFragment."""
        self._flush_pending()
        return ReportComposer.compose(*self._fragments)

    def to_list(self) -> list[str]:
        """Convert to a list of strings."""
        return self.to_fragment().to_list()

    def __len__(self) -> int:
        """Return the total number of lines across all fragments."""
        self._flush_pending()
        return sum(len(f) for f in self._fragments) + len(self._pending_lines)

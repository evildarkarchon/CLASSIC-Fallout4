"""Parallel report processing capabilities.

This module provides the ParallelReportProcessor class for
parallel fragment processing (Rust-only feature with Python fallback).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ClassicLib.integration.detector import detect_component
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyReportFragment

if TYPE_CHECKING:
    from classic_scanlog import ParallelReportProcessor as RustParallelProcessor

    RUST_AVAILABLE: bool = True
else:
    _has_parallel, RustParallelProcessor = detect_component("classic_scanlog", "ParallelReportProcessor")
    RUST_AVAILABLE = _has_parallel

    if not RUST_AVAILABLE:
        RustParallelProcessor = None  # type: ignore[assignment, misc]

# Import fragment wrapper - using lazy import to avoid circular imports
if TYPE_CHECKING:
    from ClassicLib.rust.report.fragment import RustAcceleratedReportFragment


def _get_fragment_class() -> type:
    """Get RustAcceleratedReportFragment class lazily to avoid circular imports.

    Returns:
        The RustAcceleratedReportFragment class.

    """
    from ClassicLib.rust.report.fragment import RustAcceleratedReportFragment
    return RustAcceleratedReportFragment


class ParallelReportProcessor:
    """Parallel report processing capabilities (Rust-only feature).

    Falls back to sequential processing in Python.
    """

    def __init__(self) -> None:
        """Initialize an instance of the class, setting up a processor based on the availability
        of Rust support.
        """
        self._use_rust = RUST_AVAILABLE

        if self._use_rust:
            assert RustParallelProcessor is not None, "Rust should be available when _use_rust is True"
            self._processor = RustParallelProcessor()
        else:
            self._processor = None

    def process_reports(self, reports: list[list[str]]) -> list[list[str]]:
        """Process a list of report fragments by either utilizing a Rust-based processor
        (if available) or falling back to Python implementation for sequential processing.

        This method takes a two-dimensional list of strings, processes each
        list of lines into a report fragment, and returns a list of processed report fragments.
        When a Rust-based processor is available, it optimizes the handling of the reports,
        otherwise the processing is completed in Python.

        Args:
            reports (list[list[str]]): A list of report fragments, where each fragment
                is a list of strings containing lines of a particular report.

        Returns:
            list[list[str]]: A list of processed report fragments (each fragment is a list of strings).

        """
        if self._use_rust and self._processor is not None:
            from classic_scanlog import ParallelReportProcessor

            return ParallelReportProcessor.process_batch(reports, None)

        # Python fallback - sequential processing
        results = []
        for lines in reports:
            fragment = PyReportFragment.from_lines(lines)
            results.append(fragment.to_list())

        return results

    def combine_fragments_parallel(self, fragments: list[Any]) -> Any:
        """Combine multiple RustAcceleratedReportFragment instances into a single fragment
        utilizing parallel processing when applicable or falling back to sequential processing in Python.

        Args:
            fragments: A list of RustAcceleratedReportFragment instances to be combined.
                All fragments should support Rust-based processing if using Rust.

        Returns:
            RustAcceleratedReportFragment: A new RustAcceleratedReportFragment instance that
            represents the combined result of the input fragments.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        if self._use_rust and self._processor is not None and all(f._use_rust for f in fragments):
            from classic_scanlog import ParallelReportProcessor

            # Extract the Rust ReportFragment instances from the wrappers
            # Type ignore needed because _fragment is a union type, but we've checked _use_rust
            rust_fragments = [f._fragment for f in fragments]  # type: ignore[misc]
            result_fragment = ParallelReportProcessor.combine_fragments(rust_fragments)  # type: ignore[arg-type]

            result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
            result._use_rust = True
            result._fragment = result_fragment
            return result

        # Python fallback - sequential combination
        if not fragments:
            return RustAcceleratedReportFragment.empty()

        result = fragments[0]
        for fragment in fragments[1:]:
            result += fragment

        return result


__all__ = [
    "RUST_AVAILABLE",
    "ParallelReportProcessor",
]

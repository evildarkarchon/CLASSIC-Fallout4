"""Rust-accelerated report generation components.

This module provides backward-compatible wrappers for the Rust report generation
components, implementing Phase 5 of the Rust migration plan. It offers:
- 10-15x performance improvement in report generation
- Memory-efficient string interning
- Parallel fragment processing
- Drop-in replacement for existing Python components

All classes are re-exported from their individual modules for backward compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment
from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator
from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

if TYPE_CHECKING:
    from classic_scanlog import StringPool as RustStringPool
else:
    from ClassicLib.integration.factory import get_component

    RustStringPool = get_component("classic_scanlog", "StringPool")


# Convenience aliases for backward compatibility
ReportFragment = RustAcceleratedReportFragment
ReportComposer = RustAcceleratedReportComposer
ReportGenerator = RustAcceleratedReportGenerator


StringPool = RustStringPool  # type: ignore[assignment,misc]


__all__ = [
    "ParallelReportProcessor",
    "ReportComposer",
    "ReportFragment",
    "ReportGenerator",
    "RustAcceleratedReportComposer",
    "RustAcceleratedReportFragment",
    "RustAcceleratedReportGenerator",
    "StringPool",
]

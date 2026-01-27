"""Rust-accelerated report generation wrapper.

This module provides backward-compatible wrappers for the Rust report generation
components, implementing Phase 5 of the Rust migration plan. It offers:
- 10-15x performance improvement in report generation
- Memory-efficient string interning
- Parallel fragment processing
- Drop-in replacement for existing Python components

Note:
    This module is a compatibility shim. The actual implementations have been
    refactored into the `ClassicLib.rust.report` package. Import from there
    for new code, or continue importing from here for backward compatibility.

"""

from __future__ import annotations

# Re-export everything from the new package structure
from ClassicLib.integration.rust.report import (
    RUST_AVAILABLE,
    ParallelReportProcessor,
    ReportComposer,
    ReportFragment,
    ReportGenerator,
    RustAcceleratedReportComposer,
    RustAcceleratedReportFragment,
    RustAcceleratedReportGenerator,
    StringPool,
)

__all__ = [
    "RUST_AVAILABLE",
    "ParallelReportProcessor",
    "ReportComposer",
    "ReportFragment",
    "ReportGenerator",
    "RustAcceleratedReportComposer",
    "RustAcceleratedReportFragment",
    "RustAcceleratedReportGenerator",
    "StringPool",
]

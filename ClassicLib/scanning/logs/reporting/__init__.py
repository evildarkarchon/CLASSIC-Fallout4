"""Report generation and composition for crash log analysis.

This package consolidates report generation functionality:
- Fragment collection and composition
- Report composers and generators
- Async pipeline for report generation

All report modules now delegate to Rust-accelerated implementations via
``ClassicLib.integration.rust.report_rust`` when available.  The
``ReportFragment`` exported here is the Rust-accelerated wrapper.
"""

from ClassicLib.integration.rust.report_rust import ReportFragment
from ClassicLib.scanning.logs.reporting.async_crash_log_pipeline import AsyncCrashLogPipeline
from ClassicLib.scanning.logs.reporting.async_performance_monitor import AsyncPerformanceMonitor
from ClassicLib.scanning.logs.reporting.conditional_section import ConditionalSection
from ClassicLib.scanning.logs.reporting.fragment_collector import FragmentCollector
from ClassicLib.scanning.logs.reporting.fragment_composer import ReportComposer as FragmentReportComposer
from ClassicLib.scanning.logs.reporting.mod_detection import (
    detect_mods_single_fragment,
    generate_mod_check_header_fragment,
)
from ClassicLib.scanning.logs.reporting.report_generator_functional import ReportGeneratorFunctional
from ClassicLib.scanning.logs.reporting.section_composer import ReportComposer

__all__ = [
    # Fragment system
    "FragmentCollector",
    "FragmentReportComposer",
    "ReportFragment",
    "ReportGeneratorFunctional",
    "detect_mods_single_fragment",
    "generate_mod_check_header_fragment",
    # Section composition
    "ConditionalSection",
    "ReportComposer",
    # Pipeline
    "AsyncCrashLogPipeline",
    "AsyncPerformanceMonitor",
]

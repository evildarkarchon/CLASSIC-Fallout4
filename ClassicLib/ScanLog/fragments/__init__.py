"""Report fragment system for functional report generation.

This module provides a functional approach to report generation where each
component returns its contribution as a fragment, eliminating the need for
shared mutable state while maintaining identical output format.

**IMPORTANT**: This module exports Python-only implementations.
For Rust-accelerated versions (recommended), import from ClassicLib.rust.report_rust:
    from ClassicLib.rust.report_rust import ReportFragment, ReportComposer, ReportGenerator
"""

from ClassicLib.ScanLog.fragments.fragment_collector import FragmentCollector
from ClassicLib.ScanLog.fragments.mod_detection import detect_mods_single_fragment, generate_mod_check_header_fragment
from ClassicLib.ScanLog.fragments.report_composer import ReportComposer
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment
from ClassicLib.ScanLog.fragments.report_generator_functional import ReportGeneratorFunctional

__all__ = [
    "FragmentCollector",
    "ReportComposer",
    "ReportFragment",
    "ReportGeneratorFunctional",
    "detect_mods_single_fragment",
    "generate_mod_check_header_fragment",
]

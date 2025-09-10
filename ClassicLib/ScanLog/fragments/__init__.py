"""
Report fragment system for functional report generation.

This module provides a functional approach to report generation where each
component returns its contribution as a fragment, eliminating the need for
shared mutable state while maintaining identical output format.
"""

from .fragment_collector import FragmentCollector
from .mod_detection import detect_mods_single_fragment, generate_mod_check_header_fragment
from .report_composer import ReportComposer
from .report_fragment import ReportFragment
from .report_generator_functional import ReportGeneratorFunctional

__all__ = [
    "ReportFragment",
    "ReportComposer",
    "FragmentCollector",
    "ReportGeneratorFunctional",
    "detect_mods_single_fragment",
    "generate_mod_check_header_fragment",
]

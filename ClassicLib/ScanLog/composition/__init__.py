"""
Report composition utilities for combining fragments with conditional headers.

This module provides utilities for the common pattern of adding headers
only when content exists, replacing the retroactive header insertion pattern.
"""

from ClassicLib.ScanLog.composition.conditional_section import ConditionalSection, conditional_mod_section
from ClassicLib.ScanLog.composition.report_composer import ReportComposer

__all__ = [
    "ConditionalSection",
    "ReportComposer",
    "conditional_mod_section",
]

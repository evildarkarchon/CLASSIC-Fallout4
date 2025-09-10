"""
Report composition utilities for combining fragments with conditional headers.

This module provides utilities for the common pattern of adding headers
only when content exists, replacing the retroactive header insertion pattern.
"""

from .conditional_section import ConditionalSection, conditional_mod_section
from .report_composer import ReportComposer

__all__ = [
    "ConditionalSection",
    "ReportComposer",
    "conditional_mod_section",
]

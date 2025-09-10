"""
Data models for scan log operations.

This module contains data classes that define the configuration and results
for crash log scanning operations, providing a clean interface between
the CLI and business logic components.
"""

from .scan_config import ScanConfig, ScanConfigDict
from .scan_result import ScanResult, ScanResultDict
from .scan_statistics import ScanStatistics

__all__ = [
    "ScanConfig",
    "ScanStatistics",
    "ScanResult",
    "ScanConfigDict",
    "ScanResultDict",
]

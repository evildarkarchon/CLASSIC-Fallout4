"""
Scan log information and caching components.

This module provides configuration management for scan log operations.
"""
# ruff: noqa: TID252 - Relative imports intentional for __init__.py re-exports

from .classic_scan_logs_info import ClassicScanLogsInfo

__all__ = [
    "ClassicScanLogsInfo",
]

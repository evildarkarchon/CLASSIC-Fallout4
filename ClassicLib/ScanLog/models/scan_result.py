"""
Result data model for scan operations.

This module contains the ScanResult dataclass that holds
the outcomes of scanning crash logs.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .scan_statistics import ScanStatistics


@dataclass
class ScanResult:
    """
    Results from a crash log scan operation.

    Contains the outcomes of scanning crash logs, including statistics,
    failed logs, and timing information.
    """

    stats: ScanStatistics = field(default_factory=ScanStatistics)
    failed_logs: list[str] = field(default_factory=list)
    scan_time: float = 0.0

    # Additional result data
    processed_files: list[Path] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize computed fields after dataclass creation."""
        # Calculate scan time if not provided
        if self.scan_time == 0.0:
            self.scan_time = self.stats.get_scan_duration()

    def add_failed_log(self, log_name: str) -> None:
        """Add a failed log to the results."""
        if log_name not in self.failed_logs:
            self.failed_logs.append(log_name)
        self.stats.increment_failed()

    def add_processed_file(self, file_path: Path) -> None:
        """Add a successfully processed file to the results."""
        if file_path not in self.processed_files:
            self.processed_files.append(file_path)

    def add_error_message(self, message: str) -> None:
        """Add an error message to the results."""
        if message not in self.error_messages:
            self.error_messages.append(message)

    def is_successful(self) -> bool:
        """Check if the scan was generally successful."""
        return (
            self.stats.scanned > 0 and self.stats.failed < self.stats.total_files * 0.5  # Less than 50% failure rate
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the scan results."""
        return {
            "total_files": self.stats.total_files,
            "scanned": self.stats.scanned,
            "incomplete": self.stats.incomplete,
            "failed": self.stats.failed,
            "success_rate": self.stats.get_success_rate(),
            "scan_duration": self.scan_time,
            "failed_logs_count": len(self.failed_logs),
            "error_messages_count": len(self.error_messages),
        }


# Type alias for better code readability
ScanResultDict = dict[str, Any]

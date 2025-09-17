"""
Result data model for scan operations.

This module contains the ScanResult dataclass that holds
the outcomes of scanning crash logs.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ClassicLib.ScanLog.models.scan_statistics import ScanStatistics


@dataclass
class ScanResult:
    """
    Represents the results of a scanning operation.

    Provides methods for managing scan result data such as failed logs, processed
    files, error messages, and statistical summaries.

    Attributes:
        stats (ScanStatistics): Statistical details of the scanning operation.
        failed_logs (list[str]): List of logs that failed during the scan.
        scan_time (float): Duration of the scan in seconds.
        processed_files (list[Path]): List of successfully processed files.
        error_messages (list[str]): List of error messages encountered during the scan.
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
        """
        Determines if the operation is considered successful based on the scanning and failure statistics.

        The method evaluates whether the scanning operation qualifies as successful by checking if
        the number of scanned items is greater than zero and the failure rate is less than 50%.

        Returns:
            bool: True if the operation is successful per the defined criteria, False otherwise.
        """
        return (
            self.stats.scanned > 0 and self.stats.failed < self.stats.total_files * 0.5  # Less than 50% failure rate
        )

    def get_summary(self) -> dict[str, Any]:
        """
        Retrieves a summary of the current scan statistics and results.

        This method compiles various metrics about the scan, such as the total number of files
        processed, the number of successful and failed scans, the scan duration, and additional
        details about errors encountered. The result is returned as a dictionary.

        Returns:
            dict[str, Any]: A dictionary containing the following keys:
                - total_files: Total number of files targeted by the scan.
                - scanned: Successfully scanned files count.
                - incomplete: Count of files that were not fully scanned.
                - failed: Number of files with scan failure.
                - success_rate: The percentage of successfully scanned files.
                - scan_duration: Time taken to complete the scan process.
                - failed_logs_count: Number of failure logs recorded.
                - error_messages_count: Number of error messages registered during the scan.
        """
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

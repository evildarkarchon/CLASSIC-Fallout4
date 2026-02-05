"""Result data model for scan operations.

This module contains the ScanResult dataclass that holds
the outcomes of scanning crash logs.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ClassicLib.scanning.logs.models.scan_statistics import ScanStatistics


@dataclass
class ScanResult:
    """Represent the results of a scanning operation.

    Provides methods for managing scan result data such as failed logs, processed
    files, error messages, and statistical summaries.

    Attributes:
        stats (ScanStatistics): Statistical details of the scanning operation.
        failed_logs (list[str]): List of logs that failed during the scan.
        scan_time (float): Duration of the scan in seconds.
        processed_files (list[Path]): List of successfully processed files.
        error_messages (list[str]): List of error messages encountered during the scan.

    Note:
        Phase 16 Optimization: Uses internal sets for O(1) membership checks while
        maintaining list interfaces for backward compatibility.

    """

    stats: ScanStatistics = field(default_factory=ScanStatistics)
    failed_logs: list[str] = field(default_factory=list)
    scan_time: float = 0.0

    # Additional result data
    processed_files: list[Path] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)

    # Phase 16 Optimization: Internal sets for O(1) membership checks
    # These are used internally to avoid O(n) list membership checks
    _processed_files_set: set[Path] = field(default_factory=set, repr=False)
    _failed_logs_set: set[str] = field(default_factory=set, repr=False)
    _error_messages_set: set[str] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        """Calculate and assigns a default scan time if not explicitly provided during initialization.

        This method is automatically invoked after the object is initialized. It checks whether a
        scan time has been set. If the scan time is zero, it determines a default value by retrieving
        the scan duration from the associated statistics.

        Raises:
            AttributeError: If `self.stats` does not have a `get_scan_duration` method, resulting
            in the inability to calculate the scan time.

        """
        # Calculate scan time if not provided
        if self.scan_time == 0.0:
            self.scan_time = self.stats.get_scan_duration()

    def add_failed_log(self, log_name: str) -> None:
        """Add a log entry to the list of failed logs if it is not already present and
        updates the count of failed logs.

        Phase 16 Optimization: Uses set for O(1) membership check instead of O(n) list check.

        Args:
            log_name (str): The name of the log to be added to the failed logs list.

        """
        if log_name not in self._failed_logs_set:
            self._failed_logs_set.add(log_name)
            self.failed_logs.append(log_name)
        self.stats.increment_failed()

    def add_processed_file(self, file_path: Path) -> None:
        """Add a file to the list of processed files if it has not already been processed.

        Phase 16 Optimization: Uses set for O(1) membership check instead of O(n) list check.

        Args:
            file_path (Path): The path of the file to be added to the processed files list.

        """
        if file_path not in self._processed_files_set:
            self._processed_files_set.add(file_path)
            self.processed_files.append(file_path)

    def add_error_message(self, message: str) -> None:
        """Add an error message to the list of error messages if it does not already exist.

        Phase 16 Optimization: Uses set for O(1) membership check instead of O(n) list check.

        Args:
            message (str): The error message to add.

        """
        if message not in self._error_messages_set:
            self._error_messages_set.add(message)
            self.error_messages.append(message)

    def is_successful(self) -> bool:
        """Determine whether the given operation was successful based on statistical thresholds.

        The method evaluates success based on the number of scanned and failed files in
        relation to the total number of files. The operation is considered successful
        if at least one file has been scanned, and the failure rate is less than 50%.

        Returns:
            bool: True if the operation meets the success criteria, False otherwise.

        """
        return (
            self.stats.scanned > 0 and self.stats.failed < self.stats.total_files * 0.5  # Less than 50% failure rate
        )

    def get_summary(self) -> dict[str, Any]:
        """Retrieve a summary of the current scan statistics and results.

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

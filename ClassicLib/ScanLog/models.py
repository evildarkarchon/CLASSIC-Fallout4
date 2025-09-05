"""
Data models for scan log operations.

This module contains data classes that define the configuration and results
for crash log scanning operations, providing a clean interface between
the CLI and business logic components.
"""

import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScanConfig:
    """
    Configuration data class for scan operations.

    This class encapsulates all configuration options that affect
    how crash logs are scanned and processed.
    """

    # Core scanning options
    fcx_mode: bool | None = None
    show_formid_values: bool | None = None
    move_unsolved_logs: bool | None = None
    simplify_logs: bool | None = None

    # Path configuration
    custom_paths: dict[str, Path] = field(default_factory=dict)

    # Performance settings
    max_concurrent: int = 10

    # Internal settings (typically set by system, not user)
    formid_db_exists: bool = True
    remove_list: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Initialize computed fields after dataclass creation."""
        # Ensure custom_paths is always a dict
        if self.custom_paths is None:
            self.custom_paths = {}

        # Validate max_concurrent
        if self.max_concurrent < 1:
            self.max_concurrent = 1
        elif self.max_concurrent > 50:  # Reasonable upper limit
            self.max_concurrent = 50


@dataclass
class ScanStatistics:
    """
    Statistics tracking for scan operations.

    Tracks various metrics about the scanning process for reporting
    and performance monitoring purposes.
    """

    scanned: int = 0
    incomplete: int = 0
    failed: int = 0
    total_files: int = 0
    scan_start_time: float = field(default_factory=time.perf_counter)

    def increment_scanned(self) -> None:
        """Increment the count of successfully scanned logs."""
        self.scanned += 1

    def increment_incomplete(self) -> None:
        """Increment the count of incomplete logs."""
        self.incomplete += 1

    def increment_failed(self) -> None:
        """Increment the count of failed logs."""
        self.failed += 1

    def get_scan_duration(self) -> float:
        """Get the duration of the scan in seconds."""
        return time.perf_counter() - self.scan_start_time

    def get_success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.scanned / self.total_files) * 100.0

    def to_counter(self) -> Counter[str]:
        """Convert to Counter format for backward compatibility."""
        return Counter(scanned=self.scanned, incomplete=self.incomplete, failed=self.failed)

    def update_from_counter(self, counter: Counter[str]) -> None:
        """Update statistics from a Counter object."""
        self.scanned += counter.get("scanned", 0)
        self.incomplete += counter.get("incomplete", 0)
        self.failed += counter.get("failed", 0)


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


# Type aliases for better code readability
ScanConfigDict = dict[str, Any]
ScanResultDict = dict[str, Any]

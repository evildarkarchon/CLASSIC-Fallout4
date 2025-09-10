"""
Statistics tracking model for scan operations.

This module contains the ScanStatistics dataclass that tracks
various metrics about the scanning process.
"""

import time
from collections import Counter
from dataclasses import dataclass, field


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

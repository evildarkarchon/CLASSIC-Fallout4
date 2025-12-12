"""Statistics tracking model for scan operations.

This module contains the ScanStatistics dataclass that tracks
various metrics about the scanning process.
"""

import time
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class ScanStatistics:
    """Represent the statistics of a scanning operation.

    This class provides a way to track and update statistics related to a scanning
    operation. Attributes such as the number of successfully scanned logs, incomplete
    logs, and failed logs are tracked. Additional functionalities include calculating
    scan duration, determining success rates, and converting the statistics into
    different formats for compatibility.

    Attributes:
        scanned (int): The number of successfully scanned logs.
        incomplete (int): The number of incomplete logs.
        failed (int): The number of failed logs.
        total_files (int): The total number of files to scan.
        scan_start_time (float): The start time of the scan, as a performance counter.

    """

    scanned: int = 0
    incomplete: int = 0
    failed: int = 0
    total_files: int = 0
    scan_start_time: float = field(default_factory=time.perf_counter)

    def increment_scanned(self) -> None:
        """Increments the scanned count by 1.

        This method updates an internal counter that tracks the total number
        of scanned items. It is primarily used to maintain a record of the
        scanned operations.
        """
        self.scanned += 1

    def increment_incomplete(self) -> None:
        """Increments the count of incomplete items by one.

        This method increases the value of the `incomplete` attribute by one
        every time it is invoked. It is typically used to track or manage the
        number of incomplete tasks or items in a system.
        """
        self.incomplete += 1

    def increment_failed(self) -> None:
        """Increments the internal counter tracking the number of failed attempts.

        The method updates the `failed` attribute by incrementing its value by 1.
        This allows for keeping a record of failure occurrences.
        """
        self.failed += 1

    def get_scan_duration(self) -> float:
        """Calculate the duration of the scan.

        This method computes the time elapsed since the scan started by subtracting
        the stored start time from the current time using a high-resolution
        performance counter.

        Returns:
            float: The duration of the scan in seconds.

        """
        return time.perf_counter() - self.scan_start_time

    def get_success_rate(self) -> float:
        """Calculate the success rate as a percentage.

        This method computes the success rate of scanned files relative to the total
        number of files. If no files exist (i.e., total_files is zero), it returns 0.0
        to avoid division by zero.

        Returns:
            float: The success rate as a percentage.

        """
        if self.total_files == 0:
            return 0.0
        return (self.scanned / self.total_files) * 100.0

    def to_counter(self) -> Counter[str]:
        """Convert the object's state to a Counter representation.

        This method creates a Counter object representing the instance's
        attributes, allowing for an aggregated and easily readable summary
        of specific state counts.

        Returns:
            Counter[str]: A Counter object with keys corresponding to the
            attribute names and values representing their counts.

        """
        return Counter(scanned=self.scanned, incomplete=self.incomplete, failed=self.failed)

    def update_from_counter(self, counter: Counter[str]) -> None:
        """Update the object's attributes with corresponding counts from the provided `Counter`.

        This method increments the object's attributes based on the keys and values found
        in the given `Counter` object. If a key is not present in the `Counter`, a
        default value of 0 is used.

        Args:
            counter (Counter[str]): A `Counter` object containing counts for keys
                "scanned", "incomplete", and "failed" to update the corresponding
                attributes.

        """
        self.scanned += counter.get("scanned", 0)
        self.incomplete += counter.get("incomplete", 0)
        self.failed += counter.get("failed", 0)

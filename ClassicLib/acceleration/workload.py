"""Workload characteristics for optimization decisions.

This module provides the WorkloadCharacteristics dataclass for capturing
workload metrics and determining optimal optimization levels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OptimizationLevel(Enum):
    """Represent different levels of optimization that can be applied.

    This enumeration defines a range of optimization strategies that vary
    from being completely disabled to dynamically adjusting based on workloads.
    It is designed to provide flexible options for balancing performance,
    compatibility, and resource usage.

    Attributes:
        DISABLED (int): Component disabled, no optimizations applied.
        MINIMAL (int): Minimal optimization level, prioritizing maximum
            compatibility, and stability.
        BALANCED (int): Balances performance and resource usage, serving
            as the default option for general scenarios.
        AGGRESSIVE (int): Focuses on maximum performance, potentially
            utilizing higher amounts of resources.
        ADAPTIVE (int): Dynamically adjusts optimization level based on the
            workload to maintain optimal performance and resource efficiency.

    """

    DISABLED = 0  # Component disabled
    MINIMAL = 1  # Minimal optimization, maximum compatibility
    BALANCED = 2  # Balanced performance and resource usage (default)
    AGGRESSIVE = 3  # Maximum performance, higher resource usage
    ADAPTIVE = 4  # Dynamically adjust based on workload


@dataclass
class WorkloadCharacteristics:
    """Represent characteristics of a computational workload and provides methods to
    evaluate its optimization level and performance.

    The WorkloadCharacteristics class is used to encapsulate various metrics and
    attributes of a workload, including file count, file sizes, batch operation
    flags, memory constraints, and extended metrics such as rust acceleration,
    component errors, and performance timings. It supports determining the optimal
    optimization level and calculating a performance score based on the given inputs.

    Attributes:
        file_count (int): Number of files involved in the workload.
        total_file_size (int): Aggregate file size (in bytes) across all files.
        formid_count (int): Count of FormID elements in the workload.
        plugin_count (int): Number of plugins included in the workload.
        database_queries (int): Number of database queries in the workload.
        report_fragments (int): Count of report fragments being processed.
        is_batch_operation (bool): Indicates whether the workload is part of a batch operation.
        is_memory_constrained (bool): Specifies if memory availability is limited.
        extended_metrics (dict[str, Any]): Additional workload metrics, such as
            acceleration percentage, performance timings, or cache metrics.

    """

    file_count: int = 0
    total_file_size: int = 0
    formid_count: int = 0
    plugin_count: int = 0
    database_queries: int = 0
    report_fragments: int = 0
    is_batch_operation: bool = False
    is_memory_constrained: bool = False
    extended_metrics: dict[str, Any] = field(default_factory=dict)  # Phase 6 addition

    def determine_optimization_level(self) -> OptimizationLevel:
        """Determine the optimal level of optimization based on various dynamic system metrics
        and configuration parameters. This method analyzes conditions such as system stability,
        Rust acceleration percentage, cache utilization, memory constraints, and workload
        characteristics to return the appropriate optimization level for the current operation.

        Returns:
            OptimizationLevel: The determined optimization level based on the analyzed metrics.

        Raises:
            KeyError: If any required key in `extended_metrics` is missing.

        """
        # Check for component instability first
        component_errors = self.extended_metrics.get("component_errors", 0)
        if component_errors > 3:
            # Many component errors suggest instability - use minimal optimization
            return OptimizationLevel.MINIMAL

        # Check acceleration percentage for Rust availability
        acceleration_pct = self.extended_metrics.get("acceleration_percentage", 100)

        # Large batch operations with good Rust acceleration
        if self.is_batch_operation and self.file_count > 10 and acceleration_pct > 70:
            return OptimizationLevel.AGGRESSIVE

        # High-performance single operations with excellent acceleration
        if not self.is_batch_operation and acceleration_pct > 90:
            cache_util = self.extended_metrics.get("cache_utilization", 0)
            if cache_util > 80:  # Good cache performance
                return OptimizationLevel.AGGRESSIVE

        # Memory constrained environments or low acceleration
        if self.is_memory_constrained or acceleration_pct < 30:
            return OptimizationLevel.BALANCED

        # Heavy database operations benefit from aggressive caching
        if self.database_queries > 100 and acceleration_pct > 50:
            return OptimizationLevel.AGGRESSIVE

        # Large plugin counts with good acceleration
        if self.plugin_count > 200 and acceleration_pct > 60:
            return OptimizationLevel.AGGRESSIVE

        # High FormID counts need optimization
        if self.formid_count > 500 and acceleration_pct > 50:
            return OptimizationLevel.AGGRESSIVE

        # Consider performance timings
        parse_time = self.extended_metrics.get("parse_time", 0)
        if parse_time > 2.0 and acceleration_pct < 50:  # Slow parsing without Rust
            return OptimizationLevel.BALANCED  # Don't stress the system further

        # Default to balanced for most workloads
        return OptimizationLevel.BALANCED

    def get_performance_score(self) -> float:
        """Calculate the performance score based on various metrics such as acceleration
        percentage, cache utilization, component errors, and parse time. The score is
        adjusted to provide bonuses or penalties based on these criteria, ensuring it
        falls within the range of 0 to 100.

        Returns:
            float: The calculated performance score, constrained between 0.0 and 100.0.

        Raises:
            None

        """
        score = 50.0  # Base score

        # Rust acceleration bonus
        acceleration_pct = self.extended_metrics.get("acceleration_percentage", 0)
        score += (acceleration_pct / 100) * 30  # Up to 30 points for full acceleration

        # Cache utilization bonus
        cache_util = self.extended_metrics.get("cache_utilization", 0)
        score += (cache_util / 100) * 15  # Up to 15 points for excellent caching

        # Error penalty
        component_errors = self.extended_metrics.get("component_errors", 0)
        score -= min(component_errors * 5, 20)  # Up to 20 points penalty for errors

        # Performance timing bonus/penalty
        parse_time = self.extended_metrics.get("parse_time", 1.0)
        if parse_time < 0.1:  # Very fast parsing
            score += 5
        elif parse_time > 5.0:  # Slow parsing
            score -= 10

        return max(0.0, min(100.0, score))


__all__ = ["OptimizationLevel", "WorkloadCharacteristics"]

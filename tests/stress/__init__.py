"""
Stress testing package for CLASSIC-Fallout4 Phase 6 Rust migration validation.

This package provides comprehensive stress testing capabilities including:
- Memory stress tests with leak detection
- Concurrency stress tests for thread safety
- Performance stress tests for sustained load
- Error recovery stress tests for failure scenarios
- Data volume stress tests for massive datasets
- Comprehensive reporting for production readiness assessment

Usage:
    pytest tests/stress/ -v --tb=short

For specific test categories:
    pytest tests/stress/ -m "memory" -v
    pytest tests/stress/ -m "concurrency" -v
    pytest tests/stress/ -m "performance" -v
    pytest tests/stress/ -m "error_recovery" -v
    pytest tests/stress/ -m "data_volume" -v

With slow tests:
    pytest tests/stress/ --run-slow -v

The stress tests are designed to validate that the Rust migration components
can handle production-level workloads and extreme conditions without failures.
"""

from .stress_report_generator import StressTestReporter, SystemSpecs, TestMetric, TestSectionResult
from .stress_test_fixtures import ConcurrencyTestHelper, MemoryTracker, PerformanceProfiler, StressDataGenerator

__all__ = [
    "MemoryTracker",
    "ConcurrencyTestHelper",
    "StressDataGenerator",
    "PerformanceProfiler",
    "StressTestReporter",
    "TestMetric",
    "TestSectionResult",
    "SystemSpecs",
]

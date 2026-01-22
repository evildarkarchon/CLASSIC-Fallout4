"""Unit tests for the PerformanceMonitor module.

This module tests the performance monitoring utilities:
- timed_operation decorator for sync functions
- async_timed_operation decorator for async functions
- batch_operation_monitor decorator
- TimedBlock context manager
- Metrics storage and reporting functions
"""

import asyncio
import time

import pytest

pytestmark = [pytest.mark.unit]

from ClassicLib.PerformanceMonitor import (
    TimedBlock,
    _performance_metrics,
    _store_metric,
    async_timed_operation,
    batch_operation_monitor,
    get_performance_summary,
    log_performance_summary,
    reset_metrics,
    timed_operation,
)


@pytest.fixture(autouse=True)
def reset_metrics_before_test() -> None:
    """Reset performance metrics before each test."""
    reset_metrics()


class TestTimedOperationDecorator:
    """Test suite for timed_operation decorator."""

    def test_decorator_times_successful_function(self) -> None:
        """Test that decorator times a successful function execution."""

        @timed_operation("test_op")
        def sample_function() -> str:
            time.sleep(0.01)
            return "result"

        result = sample_function()

        assert result == "result"
        # Check metric was stored
        assert "test_op" in _performance_metrics
        assert len(_performance_metrics["test_op"]) == 1
        assert _performance_metrics["test_op"][0] >= 0.01

    def test_decorator_uses_function_name_when_no_name_provided(self) -> None:
        """Test that decorator uses function name if no name specified."""

        @timed_operation()
        def my_custom_function() -> int:
            return 42

        my_custom_function()

        assert "my_custom_function" in _performance_metrics

    def test_decorator_raises_exception_from_function(self) -> None:
        """Test that decorator re-raises exceptions from decorated function."""

        @timed_operation("failing_op")
        def failing_function() -> None:
            raise ValueError("Expected error")

        with pytest.raises(ValueError, match="Expected error"):
            failing_function()

    def test_decorator_with_debug_log_level(self) -> None:
        """Test decorator with debug log level."""

        @timed_operation("debug_op", log_level="debug")
        def debug_function() -> str:
            return "debug"

        result = debug_function()

        assert result == "debug"
        assert "debug_op" in _performance_metrics

    def test_decorator_with_warning_log_level(self) -> None:
        """Test decorator with warning log level."""

        @timed_operation("warning_op", log_level="warning")
        def warning_function() -> str:
            return "warning"

        result = warning_function()

        assert result == "warning"
        assert "warning_op" in _performance_metrics

    def test_decorator_with_args_and_kwargs(self) -> None:
        """Test decorator passes args and kwargs correctly."""

        @timed_operation("args_test")
        def function_with_args(a: int, b: int, multiplier: int = 1) -> int:
            return (a + b) * multiplier

        result = function_with_args(5, 3, multiplier=2)

        assert result == 16


class TestAsyncTimedOperationDecorator:
    """Test suite for async_timed_operation decorator."""

    @pytest.mark.asyncio
    async def test_async_decorator_times_coroutine(self) -> None:
        """Test that async decorator times coroutine execution."""

        @async_timed_operation("async_test")
        async def async_sample() -> str:
            await asyncio.sleep(0.01)
            return "async_result"

        result = await async_sample()

        assert result == "async_result"
        assert "async_test" in _performance_metrics
        assert _performance_metrics["async_test"][0] >= 0.01

    @pytest.mark.asyncio
    async def test_async_decorator_uses_function_name(self) -> None:
        """Test async decorator uses function name if no name specified."""

        @async_timed_operation()
        async def async_named_function() -> int:
            return 100

        await async_named_function()

        assert "async_named_function" in _performance_metrics

    @pytest.mark.asyncio
    async def test_async_decorator_raises_exception(self) -> None:
        """Test async decorator re-raises exceptions."""

        @async_timed_operation("async_fail")
        async def async_failing() -> None:
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError, match="Async error"):
            await async_failing()

    @pytest.mark.asyncio
    async def test_async_decorator_with_log_levels(self) -> None:
        """Test async decorator with different log levels."""

        @async_timed_operation("async_debug", log_level="debug")
        async def debug_async() -> str:
            return "debug"

        @async_timed_operation("async_warning", log_level="warning")
        async def warning_async() -> str:
            return "warning"

        await debug_async()
        await warning_async()

        assert "async_debug" in _performance_metrics
        assert "async_warning" in _performance_metrics


class TestBatchOperationMonitor:
    """Test suite for batch_operation_monitor decorator."""

    def test_batch_monitor_with_list_result(self) -> None:
        """Test batch monitor calculates per-item time for list results."""

        @batch_operation_monitor("batch_list")
        def list_operation() -> list[int]:
            return [1, 2, 3, 4, 5]

        result = list_operation()

        assert result == [1, 2, 3, 4, 5]
        assert "batch_list" in _performance_metrics
        assert "batch_list_per_item" in _performance_metrics

    def test_batch_monitor_with_tuple_result(self) -> None:
        """Test batch monitor calculates per-item time for tuple results."""

        @batch_operation_monitor("batch_tuple")
        def tuple_operation() -> tuple[str, ...]:
            return ("a", "b", "c")

        result = tuple_operation()

        assert result == ("a", "b", "c")
        assert "batch_tuple" in _performance_metrics
        assert "batch_tuple_per_item" in _performance_metrics

    def test_batch_monitor_with_non_sequence_result(self) -> None:
        """Test batch monitor handles non-sequence results (batch_size=1)."""

        @batch_operation_monitor("batch_single")
        def single_operation() -> int:
            return 42

        result = single_operation()

        assert result == 42
        assert "batch_single" in _performance_metrics

    def test_batch_monitor_with_empty_list(self) -> None:
        """Test batch monitor handles empty list (avoids division by zero)."""

        @batch_operation_monitor("batch_empty")
        def empty_operation() -> list[int]:
            return []

        result = empty_operation()

        assert result == []
        assert "batch_empty" in _performance_metrics


class TestTimedBlockContextManager:
    """Test suite for TimedBlock context manager."""

    def test_timed_block_measures_duration(self) -> None:
        """Test that TimedBlock measures block duration."""
        with TimedBlock("context_test"):
            time.sleep(0.01)

        assert "context_test" in _performance_metrics
        assert _performance_metrics["context_test"][0] >= 0.01

    def test_timed_block_returns_itself(self) -> None:
        """Test that TimedBlock returns itself as context variable."""
        with TimedBlock("self_test") as block:
            assert isinstance(block, TimedBlock)
            assert block.name == "self_test"

    def test_timed_block_with_debug_level(self) -> None:
        """Test TimedBlock with debug log level."""
        with TimedBlock("debug_block", log_level="debug"):
            pass

        assert "debug_block" in _performance_metrics

    def test_timed_block_with_warning_level(self) -> None:
        """Test TimedBlock with warning log level."""
        with TimedBlock("warning_block", log_level="warning"):
            pass

        assert "warning_block" in _performance_metrics

    def test_timed_block_handles_exception(self) -> None:
        """Test that TimedBlock handles exceptions in block."""
        with pytest.raises(ValueError):
            with TimedBlock("exception_block"):
                raise ValueError("Block error")

        # Metric should NOT be stored for failed blocks
        # (based on the implementation checking exc_type is None)
        assert "exception_block" not in _performance_metrics


class TestMetricsStorage:
    """Test suite for metrics storage functions."""

    def test_store_metric_creates_new_key(self) -> None:
        """Test that _store_metric creates new metric key."""
        _store_metric("new_metric", 0.5)

        assert "new_metric" in _performance_metrics
        assert _performance_metrics["new_metric"] == [0.5]

    def test_store_metric_appends_to_existing(self) -> None:
        """Test that _store_metric appends to existing metric."""
        _store_metric("multi_metric", 0.1)
        _store_metric("multi_metric", 0.2)
        _store_metric("multi_metric", 0.3)

        assert _performance_metrics["multi_metric"] == [0.1, 0.2, 0.3]

    def test_reset_metrics_clears_all(self) -> None:
        """Test that reset_metrics clears all stored metrics."""
        _store_metric("metric1", 1.0)
        _store_metric("metric2", 2.0)

        reset_metrics()

        assert _performance_metrics == {}


class TestPerformanceSummary:
    """Test suite for get_performance_summary function."""

    def test_summary_returns_empty_for_no_metrics(self) -> None:
        """Test summary returns empty dict when no metrics."""
        summary = get_performance_summary()

        assert summary == {}

    def test_summary_calculates_statistics(self) -> None:
        """Test summary calculates count, total, avg, min, max."""
        _store_metric("stats_test", 1.0)
        _store_metric("stats_test", 2.0)
        _store_metric("stats_test", 3.0)

        summary = get_performance_summary()

        assert "stats_test" in summary
        stats = summary["stats_test"]
        assert stats["count"] == 3
        assert stats["total"] == 6.0
        assert stats["average"] == 2.0
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0

    def test_summary_handles_multiple_operations(self) -> None:
        """Test summary handles multiple operations."""
        _store_metric("op_a", 1.0)
        _store_metric("op_b", 2.0)

        summary = get_performance_summary()

        assert len(summary) == 2
        assert "op_a" in summary
        assert "op_b" in summary


class TestLogPerformanceSummary:
    """Test suite for log_performance_summary function."""

    def test_log_summary_with_no_metrics(self) -> None:
        """Test logging when no metrics collected (should not raise)."""
        # Should log "No performance metrics collected" but not raise
        log_performance_summary()

    def test_log_summary_with_metrics(self) -> None:
        """Test logging with collected metrics."""
        _store_metric("logged_op", 0.5)

        # Should log summary without raising
        log_performance_summary()

        # Verify metric still exists
        assert "logged_op" in _performance_metrics

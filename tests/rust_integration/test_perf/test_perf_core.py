"""
Integration tests for classic-perf Rust core functionality.

These tests verify that the Rust-accelerated performance monitoring
core functions work correctly. Decorator and wrapper tests are in
the ClassicLib test suite.
"""

import time

# Import the Rust module
import classic_perf
import pytest


class TestPerfImport:
    """Test that the perf module can be imported."""

    def test_import_module(self):
        """Test that the module imports successfully."""
        assert classic_perf is not None
        assert hasattr(classic_perf, "record_timing")
        assert hasattr(classic_perf, "get_summary")
        assert hasattr(classic_perf, "clear_metrics")
        assert hasattr(classic_perf, "reset_metrics")


class TestCoreOperations:
    """Test core metrics recording and retrieval."""

    def setup_method(self):
        """Clear metrics before each test."""
        classic_perf.clear_metrics()

    def test_record_and_get_summary(self):
        """Test recording timing and getting summary."""
        classic_perf.record_timing("test_op", 0.123)

        summary = classic_perf.get_summary()
        assert "test_op" in summary
        assert summary["test_op"].count == 1
        assert abs(summary["test_op"].total - 0.123) < 0.001

    def test_multiple_timings(self):
        """Test recording multiple timings for the same operation."""
        classic_perf.record_timing("batch_op", 0.1)
        classic_perf.record_timing("batch_op", 0.2)
        classic_perf.record_timing("batch_op", 0.3)

        summary = classic_perf.get_summary()
        stats = summary["batch_op"]
        assert stats.count == 3
        assert abs(stats.total - 0.6) < 0.001
        assert abs(stats.average - 0.2) < 0.001
        assert abs(stats.min - 0.1) < 0.001
        assert abs(stats.max - 0.3) < 0.001

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        classic_perf.record_timing("op1", 0.1)
        classic_perf.record_timing("op2", 0.2)
        assert len(classic_perf.get_summary()) == 2

        classic_perf.clear_metrics()
        assert len(classic_perf.get_summary()) == 0

    def test_reset_metrics_alias(self):
        """Test reset_metrics() as alias for clear_metrics()."""
        classic_perf.record_timing("op1", 0.1)
        assert len(classic_perf.get_summary()) == 1

        classic_perf.reset_metrics()
        assert len(classic_perf.get_summary()) == 0

    def test_empty_summary(self):
        """Test getting summary when no metrics exist."""
        summary = classic_perf.get_summary()
        assert isinstance(summary, dict)
        assert len(summary) == 0

    def test_metrics_summary_properties(self):
        """Test MetricsSummary object properties."""
        classic_perf.record_timing("prop_test", 1.0)
        classic_perf.record_timing("prop_test", 2.0)
        classic_perf.record_timing("prop_test", 3.0)

        summary = classic_perf.get_summary()
        stats = summary["prop_test"]

        # Test all properties are accessible
        assert stats.count == 3
        assert stats.total == 6.0
        assert stats.average == 2.0
        assert stats.min == 1.0
        assert stats.max == 3.0

    def test_metrics_summary_repr(self):
        """Test MetricsSummary repr."""
        classic_perf.record_timing("repr_test", 0.5)

        summary = classic_perf.get_summary()
        stats = summary["repr_test"]

        repr_str = repr(stats)
        assert "MetricsSummary" in repr_str
        assert "count=1" in repr_str


class TestTimer:
    """Test the Timer RAII class."""

    def setup_method(self):
        """Clear metrics before each test."""
        classic_perf.clear_metrics()

    def test_timer_finish(self):
        """Test explicitly finishing a timer."""
        timer = classic_perf.start_timer("finish_test")
        time.sleep(0.01)
        timer.finish()

        summary = classic_perf.get_summary()
        assert "finish_test" in summary
        assert summary["finish_test"].count == 1
        assert summary["finish_test"].total >= 0.01

    def test_timer_elapsed(self):
        """Test getting elapsed time from timer."""
        timer = classic_perf.start_timer("elapsed_test")
        time.sleep(0.05)
        elapsed = timer.elapsed()

        assert elapsed >= 0.05
        timer.finish()

    def test_timer_repr(self):
        """Test Timer repr."""
        timer = classic_perf.start_timer("repr_test")
        repr_str = repr(timer)
        assert "Timer" in repr_str
        assert "elapsed=" in repr_str
        timer.finish()


class TestThreadSafety:
    """Test thread safety of metrics collection."""

    def setup_method(self):
        """Clear metrics before each test."""
        classic_perf.clear_metrics()

    def test_concurrent_recording(self):
        """Test concurrent recording from multiple threads."""
        import threading

        def record_metrics(thread_id):
            for i in range(10):
                classic_perf.record_timing(f"thread_{thread_id}", 0.001 * (i + 1))

        threads = [threading.Thread(target=record_metrics, args=(i,)) for i in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        summary = classic_perf.get_summary()
        # Should have 10 different operations (one per thread)
        assert len(summary) == 10

        # Each should have 10 samples
        for i in range(10):
            key = f"thread_{i}"
            assert key in summary
            assert summary[key].count == 10


@pytest.mark.rust
class TestRustAcceleration:
    """Test that Rust acceleration is working."""

    def test_rust_available(self):
        """Test that Rust implementation is being used."""
        # Check that we can import the Rust module
        import classic_perf as rust_perf

        assert hasattr(rust_perf, "record_timing")
        assert hasattr(rust_perf, "get_summary")
        assert hasattr(rust_perf, "Timer")
        assert hasattr(rust_perf, "MetricsSummary")

    def test_performance_comparison(self):
        """Test that Rust implementation is faster (basic sanity check)."""
        # This is a basic sanity check, not a comprehensive benchmark
        classic_perf.clear_metrics()

        iterations = 1000

        # Time the Rust implementation
        start = time.perf_counter()
        for i in range(iterations):
            classic_perf.record_timing("rust_test", 0.001 * i)
        rust_time = time.perf_counter() - start

        # Get summary (also uses Rust)
        summary = classic_perf.get_summary()
        assert "rust_test" in summary
        assert summary["rust_test"].count == iterations

        # Rust implementation should complete in reasonable time (< 100ms for 1000 operations)
        assert rust_time < 0.1, f"Rust implementation took {rust_time}s, expected < 0.1s"

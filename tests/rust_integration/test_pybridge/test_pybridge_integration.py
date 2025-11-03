"""Integration tests for classic_pybridge Rust module.

Tests the AsyncBridge utilities including:
- BridgeOperationType enum
- BridgeMetrics tracking
- RuntimeInfo queries
- Metrics recording and retrieval
- Thread safety
"""

from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.mark.rust
@pytest.mark.integration
class TestPybridgeImport:
    """Test that classic_pybridge can be imported and has expected API."""

    def test_import_module(self):
        """Test that classic_pybridge module imports successfully."""
        import classic_pybridge

        assert classic_pybridge is not None

    def test_module_exports(self):
        """Test that all expected exports are available."""
        import classic_pybridge

        expected_exports = {
            "BridgeOperationType",
            "BridgeMetrics",
            "RuntimeInfo",
            "record_operation",
            "get_metrics",
            "clear_metrics",
            "is_runtime_available",
            "get_runtime_info",
        }

        actual_exports = {
            name for name in dir(classic_pybridge) if not name.startswith("_")
        }

        # Remove submodule if present
        actual_exports.discard("classic_pybridge")

        assert expected_exports.issubset(
            actual_exports
        ), f"Missing exports: {expected_exports - actual_exports}"


@pytest.mark.rust
@pytest.mark.integration
class TestBridgeOperationType:
    """Test BridgeOperationType enum."""

    def test_operation_type_variants(self):
        """Test that all operation type variants exist."""
        from classic_pybridge import BridgeOperationType

        # All expected variants
        assert hasattr(BridgeOperationType, "RunAsync")
        assert hasattr(BridgeOperationType, "RunAsyncWithTimeout")
        assert hasattr(BridgeOperationType, "LoopCreation")
        assert hasattr(BridgeOperationType, "LoopCleanup")

    def test_operation_type_values(self):
        """Test that operation types can be created."""
        from classic_pybridge import BridgeOperationType

        run_async = BridgeOperationType.RunAsync
        timeout = BridgeOperationType.RunAsyncWithTimeout
        creation = BridgeOperationType.LoopCreation
        cleanup = BridgeOperationType.LoopCleanup

        assert run_async is not None
        assert timeout is not None
        assert creation is not None
        assert cleanup is not None


@pytest.mark.rust
@pytest.mark.integration
class TestMetricsRecording:
    """Test metrics recording functionality."""

    def setup_method(self):
        """Clear metrics before each test."""
        from classic_pybridge import clear_metrics

        clear_metrics()

    def test_record_operation_basic(self):
        """Test basic operation recording."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        record_operation(BridgeOperationType.RunAsync, 0.123, True)

        metrics = get_metrics()
        assert metrics.run_async_count == 1
        assert metrics.run_async_success == 1
        assert metrics.run_async_failure == 0
        assert metrics.run_async_total_time > 0

    def test_record_operation_failure(self):
        """Test recording failed operations."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        record_operation(BridgeOperationType.RunAsync, 0.050, False)

        metrics = get_metrics()
        assert metrics.run_async_count == 1
        assert metrics.run_async_success == 0
        assert metrics.run_async_failure == 1

    def test_record_timeout_operations(self):
        """Test recording timeout operations."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        record_operation(BridgeOperationType.RunAsyncWithTimeout, 1.5, True)
        record_operation(BridgeOperationType.RunAsyncWithTimeout, 2.0, False)

        metrics = get_metrics()
        assert metrics.timeout_count == 2
        assert metrics.timeout_success == 1
        assert metrics.timeout_failure == 1
        assert metrics.timeout_total_time > 0

    def test_record_loop_operations(self):
        """Test recording loop creation and cleanup operations."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        record_operation(BridgeOperationType.LoopCreation, 0.001, True)
        record_operation(BridgeOperationType.LoopCleanup, 0.002, True)

        metrics = get_metrics()
        assert metrics.loops_created == 1
        assert metrics.loops_cleaned == 1

    def test_multiple_operations(self):
        """Test recording multiple operations of different types."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        # Record various operations
        record_operation(BridgeOperationType.RunAsync, 0.100, True)
        record_operation(BridgeOperationType.RunAsync, 0.150, True)
        record_operation(BridgeOperationType.RunAsync, 0.075, False)
        record_operation(BridgeOperationType.RunAsyncWithTimeout, 1.0, True)
        record_operation(BridgeOperationType.LoopCreation, 0.001, True)
        record_operation(BridgeOperationType.LoopCleanup, 0.002, True)

        metrics = get_metrics()

        # Verify counts
        assert metrics.run_async_count == 3
        assert metrics.run_async_success == 2
        assert metrics.run_async_failure == 1
        assert metrics.timeout_count == 1
        assert metrics.timeout_success == 1
        assert metrics.loops_created == 1
        assert metrics.loops_cleaned == 1

        # Verify timing
        assert metrics.run_async_total_time > 0
        assert metrics.timeout_total_time > 0


@pytest.mark.rust
@pytest.mark.integration
class TestBridgeMetrics:
    """Test BridgeMetrics class."""

    def setup_method(self):
        """Clear metrics before each test."""
        from classic_pybridge import clear_metrics

        clear_metrics()

    def test_metrics_attributes(self):
        """Test that BridgeMetrics has all expected attributes."""
        from classic_pybridge import get_metrics

        metrics = get_metrics()

        # All expected attributes
        assert hasattr(metrics, "run_async_count")
        assert hasattr(metrics, "run_async_success")
        assert hasattr(metrics, "run_async_failure")
        assert hasattr(metrics, "run_async_total_time")
        assert hasattr(metrics, "timeout_count")
        assert hasattr(metrics, "timeout_success")
        assert hasattr(metrics, "timeout_failure")
        assert hasattr(metrics, "timeout_total_time")
        assert hasattr(metrics, "loops_created")
        assert hasattr(metrics, "loops_cleaned")

    def test_metrics_initial_values(self):
        """Test that metrics start at zero after clearing."""
        from classic_pybridge import get_metrics

        metrics = get_metrics()

        assert metrics.run_async_count == 0
        assert metrics.run_async_success == 0
        assert metrics.run_async_failure == 0
        assert metrics.run_async_total_time == 0.0
        assert metrics.timeout_count == 0
        assert metrics.timeout_success == 0
        assert metrics.timeout_failure == 0
        assert metrics.timeout_total_time == 0.0
        assert metrics.loops_created == 0
        assert metrics.loops_cleaned == 0

    def test_metrics_repr(self):
        """Test BridgeMetrics __repr__ method."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        record_operation(BridgeOperationType.RunAsync, 0.1, True)
        record_operation(BridgeOperationType.LoopCreation, 0.001, True)

        metrics = get_metrics()
        repr_str = repr(metrics)

        assert "BridgeMetrics" in repr_str
        assert "run_async=" in repr_str
        assert "timeout=" in repr_str
        assert "loops=" in repr_str


@pytest.mark.rust
@pytest.mark.integration
class TestRuntimeInfo:
    """Test RuntimeInfo functionality."""

    def test_is_runtime_available(self):
        """Test runtime availability check."""
        from classic_pybridge import is_runtime_available

        # Runtime should always be available
        assert is_runtime_available() is True

    def test_get_runtime_info(self):
        """Test getting runtime information."""
        from classic_pybridge import get_runtime_info

        info = get_runtime_info()

        assert info is not None
        assert hasattr(info, "available")
        assert hasattr(info, "worker_threads")

    def test_runtime_info_values(self):
        """Test that runtime info has sensible values."""
        from classic_pybridge import get_runtime_info

        info = get_runtime_info()

        # Runtime should be available
        assert info.available is True

        # Worker threads should be positive
        assert info.worker_threads > 0

        # Should have reasonable number of threads
        assert info.worker_threads <= 128  # Sanity check

    def test_runtime_info_repr(self):
        """Test RuntimeInfo __repr__ method."""
        from classic_pybridge import get_runtime_info

        info = get_runtime_info()
        repr_str = repr(info)

        assert "RuntimeInfo" in repr_str
        assert "available=" in repr_str
        assert "worker_threads=" in repr_str


@pytest.mark.rust
@pytest.mark.integration
class TestMetricsClear:
    """Test metrics clearing functionality."""

    def test_clear_metrics(self):
        """Test that clear_metrics resets all counters."""
        from classic_pybridge import (
            BridgeOperationType,
            clear_metrics,
            get_metrics,
            record_operation,
        )

        # Record some operations
        record_operation(BridgeOperationType.RunAsync, 0.1, True)
        record_operation(BridgeOperationType.RunAsyncWithTimeout, 1.0, False)
        record_operation(BridgeOperationType.LoopCreation, 0.001, True)

        # Verify metrics are recorded
        metrics_before = get_metrics()
        assert metrics_before.run_async_count > 0
        assert metrics_before.timeout_count > 0
        assert metrics_before.loops_created > 0

        # Clear metrics
        clear_metrics()

        # Verify all metrics are reset
        metrics_after = get_metrics()
        assert metrics_after.run_async_count == 0
        assert metrics_after.run_async_success == 0
        assert metrics_after.run_async_failure == 0
        assert metrics_after.run_async_total_time == 0.0
        assert metrics_after.timeout_count == 0
        assert metrics_after.timeout_success == 0
        assert metrics_after.timeout_failure == 0
        assert metrics_after.timeout_total_time == 0.0
        assert metrics_after.loops_created == 0
        assert metrics_after.loops_cleaned == 0


@pytest.mark.rust
@pytest.mark.integration
class TestThreadSafety:
    """Test thread safety of metrics recording."""

    def setup_method(self):
        """Clear metrics before each test."""
        from classic_pybridge import clear_metrics

        clear_metrics()

    def test_concurrent_recording(self):
        """Test that concurrent recordings are thread-safe."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        def record_operations(thread_id: int):
            """Record operations from a thread."""
            for i in range(100):
                success = (thread_id + i) % 3 != 0  # Mix of success/failure
                record_operation(BridgeOperationType.RunAsync, 0.001, success)

        # Run concurrent recordings
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(record_operations, i) for i in range(4)]
            for future in futures:
                future.result()

        # Verify total count
        metrics = get_metrics()
        assert metrics.run_async_count == 400  # 4 threads * 100 operations
        assert (
            metrics.run_async_success + metrics.run_async_failure
            == metrics.run_async_count
        )

    def test_concurrent_types(self):
        """Test concurrent recording of different operation types."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        def record_run_async():
            for _ in range(50):
                record_operation(BridgeOperationType.RunAsync, 0.001, True)

        def record_timeout():
            for _ in range(50):
                record_operation(BridgeOperationType.RunAsyncWithTimeout, 0.002, True)

        def record_loop_ops():
            for _ in range(50):
                record_operation(BridgeOperationType.LoopCreation, 0.0001, True)
                record_operation(BridgeOperationType.LoopCleanup, 0.0001, True)

        with ThreadPoolExecutor(max_workers=3) as executor:
            f1 = executor.submit(record_run_async)
            f2 = executor.submit(record_timeout)
            f3 = executor.submit(record_loop_ops)

            f1.result()
            f2.result()
            f3.result()

        metrics = get_metrics()
        assert metrics.run_async_count == 50
        assert metrics.timeout_count == 50
        assert metrics.loops_created == 50
        assert metrics.loops_cleaned == 50


@pytest.mark.rust
@pytest.mark.integration
class TestAccuracy:
    """Test accuracy of timing measurements."""

    def setup_method(self):
        """Clear metrics before each test."""
        from classic_pybridge import clear_metrics

        clear_metrics()

    def test_timing_accuracy(self):
        """Test that recorded times are accurate."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        durations = [0.100, 0.200, 0.300]
        for duration in durations:
            record_operation(BridgeOperationType.RunAsync, duration, True)

        metrics = get_metrics()
        expected_total = sum(durations)

        # Allow for small floating point errors
        assert abs(metrics.run_async_total_time - expected_total) < 0.001

    def test_zero_duration(self):
        """Test that zero duration operations are recorded correctly."""
        from classic_pybridge import (
            BridgeOperationType,
            get_metrics,
            record_operation,
        )

        record_operation(BridgeOperationType.RunAsync, 0.0, True)

        metrics = get_metrics()
        assert metrics.run_async_count == 1
        assert metrics.run_async_total_time == 0.0


@pytest.mark.rust
@pytest.mark.integration
class TestRustAcceleration:
    """Test that Rust acceleration is being used."""

    def test_rust_module_used(self):
        """Test that we're using the Rust-accelerated module."""
        from pathlib import Path

        import classic_pybridge

        # Check if the Rust extension module exists
        # The module structure is: classic_pybridge (package) -> classic_pybridge.pyd (extension)
        if hasattr(classic_pybridge, "classic_pybridge"):
            # Accessing the inner extension module
            rust_module = classic_pybridge.classic_pybridge
            module_file = rust_module.__file__
        else:
            # For packages, check the directory for .pyd/.so/.dylib files
            package_file = classic_pybridge.__file__
            package_dir = Path(package_file).parent
            rust_files = list(package_dir.glob("*.pyd")) + \
                        list(package_dir.glob("*.so")) + \
                        list(package_dir.glob("*.dylib"))
            assert len(rust_files) > 0, f"No Rust extension found in {package_dir}"
            module_file = str(rust_files[0])

        assert module_file is not None
        # Windows: .pyd, Linux: .so, Mac: .dylib
        assert any(
            ext in module_file.lower()
            for ext in [".pyd", ".so", ".dylib"]
        ), f"Module file {module_file} is not a Rust extension"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

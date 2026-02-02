"""Performance regression tests for memory and baselines.

This module tests memory efficiency and establishes performance baselines,
ensuring no regressions in memory usage or overall performance targets.
"""

import gc
import random
import statistics
import time
from typing import Any
from unittest.mock import MagicMock

import psutil
import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.integration, pytest.mark.performance]


class PerformanceMetrics:
    """Track and analyze performance metrics.

    Thread-safe implementation for parallel test execution.
    """

    def __init__(self):
        import threading

        self.measurements: dict[str, list[float]] = {}
        self.baselines: dict[str, float] = {}
        self.rust_status: dict[str, bool] = {}
        self._lock = threading.Lock()

    def measure(self, name: str, func, *args, **kwargs) -> tuple[Any, float]:
        """Measure execution time of a function."""
        gc.collect()  # Clean state
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        with self._lock:
            if name not in self.measurements:
                self.measurements[name] = []
            self.measurements[name].append(elapsed)

        return result, elapsed

    async def measure_async(self, name: str, coro) -> tuple[Any, float]:
        """Measure execution time of an async coroutine."""
        gc.collect()  # Clean state
        start = time.perf_counter()
        result = await coro
        elapsed = time.perf_counter() - start

        with self._lock:
            if name not in self.measurements:
                self.measurements[name] = []
            self.measurements[name].append(elapsed)

        return result, elapsed

    def get_statistics(self, name: str) -> dict[str, float]:
        """Get statistics for a measurement."""
        with self._lock:
            if name not in self.measurements or not self.measurements[name]:
                return {}

            values = self.measurements[name].copy()  # Copy to release lock quickly

        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "count": len(values),
        }

    def check_regression(self, name: str, threshold: float = 1.5) -> bool:
        """Check if performance has regressed beyond threshold."""
        with self._lock:
            if name not in self.baselines:
                return False
            baseline = self.baselines[name]

        stats = self.get_statistics(name)
        if not stats:
            return False

        # Check if median time is worse than baseline * threshold
        return stats["median"] > baseline * threshold


class SyntheticDataGenerator:
    """Generate synthetic data for performance testing."""

    @staticmethod
    def generate_crash_log(size_mb: float, complexity: str = "medium") -> str:
        """Generate synthetic crash log of specified size and complexity."""
        lines = []

        # Header
        lines.append("Fallout 4 v1.10.163")
        lines.append("Buffout 4 v1.28.6")
        lines.append("")
        lines.append('Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512')
        lines.append("")

        if complexity in ["medium", "high"]:
            # Add plugin list
            lines.append("PLUGINS:")
            num_plugins = 50 if complexity == "medium" else 200
            for i in range(num_plugins):
                if i < 10:
                    lines.append(f"\t[{i:02X}] Master_{i}.esm")
                elif i < 50:
                    lines.append(f"\t[{i:02X}] Regular_{i}.esp")
                else:
                    lines.append(f"\t[FE:{i - 50:03X}] Light_{i}.esl")
            lines.append("")

        if complexity == "high":
            # Add stack trace
            lines.append("STACK TRACE:")
            for i in range(100):
                addr = random.randint(0x7FF600000000, 0x7FF6FFFFFFFF)
                offset = random.randint(0x1000, 0xFFFFFF)
                lines.append(f"\t[{i}] 0x{addr:016X} module.dll+{offset:07X}")
            lines.append("")

            # Add memory dump
            lines.append("MEMORY DUMP:")
            for i in range(200):
                addr = random.randint(0x100000000, 0xFFFFFFFFFF)
                value = random.randint(0, 0xFFFFFFFF)
                lines.append(f"\t0x{addr:016X}: {value:08X}")
            lines.append("")

        # Add FormIDs
        num_formids = 100 if complexity == "high" else 20
        for i in range(num_formids):
            plugin_index = random.randint(0x00, 0xFE)
            local_id = random.randint(0x000001, 0xFFFFFF)
            lines.append(f"FormID: {plugin_index:02X}{local_id:06X}")

        # Pad to target size
        current_size = len("\n".join(lines))
        target_bytes = int(size_mb * 1024 * 1024)

        while current_size < target_bytes:
            padding_line = "x" * min(80, target_bytes - current_size)
            lines.append(padding_line)
            current_size += len(padding_line) + 1

        return "\n".join(lines)

    @staticmethod
    def generate_formid_list(count: int) -> list[str]:
        """Generate list of synthetic FormIDs."""
        formids = []
        for _i in range(count):
            plugin_index = random.randint(0x00, 0xFE)
            local_id = random.randint(0x000001, 0xFFFFFF)
            formids.append(f"{plugin_index:02X}{local_id:06X}")
        return formids

    @staticmethod
    def generate_plugin_data(num_plugins: int, formids_per_plugin: int) -> dict:
        """Generate synthetic plugin data."""
        plugins = {}
        for i in range(num_plugins):
            plugin_name = f"Plugin_{i}.esp" if i < 50 else f"Light_{i}.esl"
            plugin_index = i if i < 50 else 0xFE

            formids = []
            for _j in range(formids_per_plugin):
                local_id = random.randint(0x000001, 0xFFFFFF)
                formids.append(f"{plugin_index:02X}{local_id:06X}")

            plugins[plugin_name] = {
                "formids": formids,
                "index": f"{plugin_index:02X}" if plugin_index < 0xFE else f"FE:{i - 50:03X}",
                "masters": ["Fallout4.esm"] if i > 0 else [],
            }
        return plugins


class TestMemoryPerformance:
    """Test memory usage and efficiency."""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    @pytest.fixture
    def generator(self):
        return SyntheticDataGenerator()

    def test_memory_efficiency_large_logs(self, generator):
        """Test memory efficiency when processing large logs."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        process = psutil.Process()

        # Initial memory
        gc.collect()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

        # Process multiple large logs
        for i in range(5):
            log = generator.generate_crash_log(2.0, "high")
            lines = log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

            # Explicitly clean up
            del log
            del segments

            if i % 2 == 0:
                gc.collect()

        # Final memory
        gc.collect()
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory

        print(f"\nMemory usage: Initial={initial_memory:.1f}MB, Final={final_memory:.1f}MB")
        print(f"Memory increase: {memory_increase:.1f}MB")

        # Should not leak excessive memory
        assert memory_increase < 50, f"Memory leak detected: {memory_increase:.1f}MB increase"

    @pytest.mark.skip(reason="Lists cannot be weak referenced")
    def test_memory_cleanup_after_processing(self, generator):
        """Test that memory is properly cleaned up after processing."""
        import weakref

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Track objects with weak references
        tracked_objects = []

        for _i in range(10):
            log = generator.generate_crash_log(0.5, "simple")
            lines = log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

            # Try to track the result
            try:
                ref = weakref.ref(segments)
                tracked_objects.append(ref)
            except TypeError:
                # Some objects don't support weak references
                pass

            del log
            del segments

        # Force cleanup
        gc.collect()

        # Check how many objects are still alive
        alive = sum(1 for ref in tracked_objects if ref() is not None)

        print(f"\nObjects still alive after cleanup: {alive}/{len(tracked_objects)}")

        # Most objects should be freed
        assert alive < len(tracked_objects) // 2, f"Too many objects still alive: {alive}"


class TestRegressionBaselines:
    """Establish and test against performance baselines."""

    @pytest.fixture
    def metrics(self):
        """Create metrics tracker with baselines."""
        m = PerformanceMetrics()

        # Establish baselines (with Rust acceleration expected)
        m.baselines = {
            "parse_1mb": 0.2,  # 200ms for 1MB log with Rust
            "parse_2mb": 0.5,  # 500ms for 2MB log with Rust
            "formid_1000": 0.01,  # 10ms for 1000 FormIDs with Rust
            "file_read_100kb": 0.005,  # 5ms per 100KB file with Rust
            "conflict_check_100": 1.0,  # 1s for 100 plugins
        }

        return m

    @pytest.fixture
    def generator(self):
        return SyntheticDataGenerator()

    def test_no_regression_in_parsing(self, metrics, generator):
        """Test that parsing performance hasn't regressed."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Test 1MB parsing
        log_1mb = generator.generate_crash_log(1.0, "medium")

        def parse_1mb():
            lines = log_1mb.splitlines()
            return parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

        _, elapsed = metrics.measure("parse_1mb", parse_1mb)

        # Check for regression
        if not metrics.check_regression("parse_1mb", threshold=2.0):
            print(f"\n✓ No regression in 1MB parsing: {elapsed:.3f}s")
        else:
            stats = metrics.get_statistics("parse_1mb")
            baseline = metrics.baselines["parse_1mb"]
            pytest.fail(f"Performance regression: 1MB parsing took {stats['median']:.3f}s (baseline: {baseline:.3f}s)")

    def test_no_regression_in_formid_analysis(self, metrics, generator):
        """Test that FormID analysis performance hasn't regressed."""
        from ClassicLib.integration.factory import get_formid_analyzer

        mock_yamldata = MagicMock()
        analyzer = get_formid_analyzer(mock_yamldata, True, False)

        # Test 1000 FormIDs using extract_formids
        formids = generator.generate_formid_list(1000)

        start = time.perf_counter()
        analyzer.extract_formids(formids)
        elapsed = time.perf_counter() - start

        metrics.measurements["formid_1000"] = [elapsed]

        # Check for regression
        if not metrics.check_regression("formid_1000", threshold=2.0):
            print(f"\n✓ No regression in FormID analysis: {elapsed:.3f}s for 1000 IDs")
        else:
            baseline = metrics.baselines["formid_1000"]
            pytest.fail(f"Performance regression: FormID analysis took {elapsed:.3f}s (baseline: {baseline:.3f}s)")

    def test_performance_summary(self, metrics, generator):
        """Generate performance summary report."""
        from ClassicLib.integration.factory import get_rust_component_status

        rust_status = get_rust_component_status()

        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)

        print("\nRust Acceleration Status:")
        print(f"  Active: {rust_status['acceleration_active']}")
        print(f"  Components: {rust_status['active_count']}/{rust_status['total_count']}")

        if rust_status["acceleration_active"]:
            print("\n✓ Rust acceleration is ACTIVE - expecting high performance")
            print("\nExpected speedups over Python:")
            print("  • Log Parsing: 10x faster")
            print("  • FormID Analysis: 25x faster")
            print("  • Pattern Matching: 20x faster")
            print("  • File I/O: 10x faster")
        else:
            print("\n⚠ Running in Python fallback mode")
            print("  For best performance, ensure Rust module is built")

        print("\n" + "=" * 60)

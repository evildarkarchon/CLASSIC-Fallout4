"""Performance regression tests for parsing operations.

This module tests log parsing and FormID analysis performance, comparing
Rust-accelerated components against Python fallbacks and ensuring performance
targets are met.
"""

import gc
import random
import statistics
import time
from typing import Any
from unittest.mock import MagicMock

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


class TestLogParsingPerformance:
    """Test log parsing performance with Rust vs Python."""

    @pytest.fixture
    def metrics(self):
        """Performance metrics tracker."""
        return PerformanceMetrics()

    @pytest.fixture
    def generator(self):
        """Data generator."""
        return SyntheticDataGenerator()

    def test_parser_performance_small_logs(self, metrics, generator):
        """Test parser performance on small logs (0.5MB)."""
        from ClassicLib.integration.factory import get_parser, is_rust_accelerated

        parser = get_parser()
        using_rust = is_rust_accelerated("parser")

        # Generate test logs
        logs = [generator.generate_crash_log(0.5, "simple") for _ in range(5)]

        # Warm up
        warm_lines = logs[0][:100].splitlines()
        parser.find_segments(warm_lines, "Buffout 4", "F4SE", "Fallout4.exe")

        # Measure performance
        for i, log in enumerate(logs):

            def parse_log():
                lines = log.splitlines()
                return parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

            _, elapsed = metrics.measure(f"parse_small_{i}", parse_log)

        stats = metrics.get_statistics("parse_small_0")

        # Performance expectations
        if using_rust:
            # With Rust: 0.5MB should parse in <100ms
            assert stats["median"] < 0.1, f"Small log parsing slow with Rust: {stats['median']:.3f}s"
            print(f"\n[RUST] Small log (0.5MB) parse time: {stats['median'] * 1000:.1f}ms")
        else:
            # Python fallback: 0.5MB in <1s
            assert stats["median"] < 1.0, f"Small log parsing slow with Python: {stats['median']:.3f}s"
            print(f"\n[Python] Small log (0.5MB) parse time: {stats['median'] * 1000:.1f}ms")

    def test_parser_performance_medium_logs(self, metrics, generator):
        """Test parser performance on medium logs (1.5MB)."""
        from ClassicLib.integration.factory import get_parser, is_rust_accelerated

        parser = get_parser()
        using_rust = is_rust_accelerated("parser")

        # Generate test logs
        logs = [generator.generate_crash_log(1.5, "medium") for _ in range(3)]

        # Measure performance
        for i, log in enumerate(logs):

            def parse_log():
                lines = log.splitlines()
                return parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

            _, elapsed = metrics.measure(f"parse_medium_{i}", parse_log)

        # Calculate statistics
        all_measurements = []
        for i in range(3):
            all_measurements.extend(metrics.measurements.get(f"parse_medium_{i}", []))

        median_time = statistics.median(all_measurements)

        # Performance expectations
        if using_rust:
            # With Rust: 1.5MB should parse in <300ms (10x faster than Python)
            assert median_time < 0.3, f"Medium log parsing slow with Rust: {median_time:.3f}s"
            print(f"\n[RUST] Medium log (1.5MB) parse time: {median_time * 1000:.1f}ms")
        else:
            # Python fallback: 1.5MB in <3s
            assert median_time < 3.0, f"Medium log parsing slow with Python: {median_time:.3f}s"
            print(f"\n[Python] Medium log (1.5MB) parse time: {median_time * 1000:.1f}ms")

    def test_parser_performance_complex_logs(self, metrics, generator):
        """Test parser performance on complex logs with many sections."""
        from ClassicLib.integration.factory import get_parser, is_rust_accelerated

        parser = get_parser()
        using_rust = is_rust_accelerated("parser")

        # Generate complex log
        complex_log = generator.generate_crash_log(2.0, "high")

        # Measure parsing
        def parse_complex():
            lines = complex_log.splitlines()
            return parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

        _, elapsed = metrics.measure("parse_complex", parse_complex)

        # Performance expectations
        if using_rust:
            # With Rust: 2MB complex should parse in <500ms
            assert elapsed < 0.5, f"Complex log parsing slow with Rust: {elapsed:.3f}s"
            print(f"\n[RUST] Complex log (2MB) parse time: {elapsed * 1000:.1f}ms")
        else:
            # Python fallback: 2MB complex in <5s
            assert elapsed < 5.0, f"Complex log parsing slow with Python: {elapsed:.3f}s"
            print(f"\n[Python] Complex log (2MB) parse time: {elapsed * 1000:.1f}ms")

    def test_parser_scaling_performance(self, metrics, generator):
        """Test parser performance scaling with log size."""
        from ClassicLib.integration.factory import get_parser, is_rust_accelerated

        parser = get_parser()
        using_rust = is_rust_accelerated("parser")

        sizes = [0.5, 1.0, 1.5, 2.0]
        times = []

        for size in sizes:
            log = generator.generate_crash_log(size, "medium")

            def parse_log():
                lines = log.splitlines()
                return parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

            _, elapsed = metrics.measure(f"scale_{size}MB", parse_log)
            times.append(elapsed)

        # Check scaling behavior
        # Time should scale roughly linearly with size
        scaling_factor = times[-1] / times[0]  # 2MB time / 0.5MB time
        expected_factor = 4.0  # 2MB is 4x larger than 0.5MB

        print(f"\nScaling factor: {scaling_factor:.2f}x (expected ~{expected_factor}x)")

        if using_rust:
            # Rust should have near-linear scaling
            assert scaling_factor < 6.0, f"Poor scaling with Rust: {scaling_factor:.2f}x"
        else:
            # Python may have worse scaling
            assert scaling_factor < 8.0, f"Poor scaling with Python: {scaling_factor:.2f}x"


class TestFormIDAnalysisPerformance:
    """Test FormID analysis performance."""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    @pytest.fixture
    def generator(self):
        return SyntheticDataGenerator()

    def test_formid_analysis_speed(self, metrics, generator, mock_yamldata):
        """Test FormID analysis performance (target: 25x speedup with Rust)."""
        from ClassicLib.integration.factory import get_formid_analyzer, is_rust_accelerated

        # Add formid-specific attributes to the fixture
        mock_yamldata.formid_keywords = ["crash", "error"]

        analyzer = get_formid_analyzer(mock_yamldata, show_values=True, db_exists=False)
        using_rust = is_rust_accelerated("formid_analyzer")

        # Generate 1000 FormIDs
        formids = generator.generate_formid_list(1000)

        # Measure batch analysis using extract_formids
        start = time.perf_counter()
        analyzer.extract_formids(formids)
        elapsed = time.perf_counter() - start

        # Calculate per-FormID time
        per_formid_ms = (elapsed / 1000) * 1000

        print(f"\nFormID analysis (1000 IDs): {elapsed:.3f}s ({per_formid_ms:.3f}ms per ID)")

        if using_rust:
            # With Rust: Should analyze 1000 FormIDs in <10ms total (25x speedup)
            assert elapsed < 0.01, f"FormID analysis slow with Rust: {elapsed:.3f}s for 1000 IDs"
            print(f"[RUST] Performance: {1000 / elapsed:.0f} FormIDs/second")
        else:
            # Python fallback: 1000 FormIDs in <250ms
            assert elapsed < 0.25, f"FormID analysis slow with Python: {elapsed:.3f}s for 1000 IDs"
            print(f"[Python] Performance: {1000 / elapsed:.0f} FormIDs/second")

    def test_formid_pattern_matching(self, metrics, generator, mock_yamldata):
        """Test FormID pattern matching performance."""
        from ClassicLib.integration.factory import get_formid_analyzer

        # Add formid-specific attributes to the fixture
        mock_yamldata.formid_keywords = ["crash", "error", "ctd", "exception"]

        analyzer = get_formid_analyzer(mock_yamldata, show_values=True, db_exists=False)

        # Generate FormIDs with patterns
        formids = []
        # Known problematic ranges
        for i in range(100):
            formids.append(f"00{i:06X}")  # Base game
            formids.append(f"FE000{i:03X}")  # Light plugins
            formids.append(f"{random.randint(0x01, 0x7F)}{i:06X}")  # Regular plugins

        # Measure pattern matching using extract_formids
        _, elapsed = metrics.measure("pattern_match", lambda: analyzer.extract_formids(formids))

        print(f"\nPattern matching {len(formids)} FormIDs: {elapsed:.3f}s")

        # Should be fast even with patterns
        assert elapsed < 0.5, f"Pattern matching too slow: {elapsed:.3f}s"

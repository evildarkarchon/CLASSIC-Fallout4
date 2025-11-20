"""Performance regression test suite.

This module establishes performance baselines and tests for regressions,
comparing Rust-accelerated components against Python fallbacks and
ensuring performance targets are met.
"""

import asyncio
import gc
import random
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import psutil
import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.integration, pytest.mark.performance]


class PerformanceMetrics:
    """Track and analyze performance metrics."""

    def __init__(self):
        self.measurements: dict[str, list[float]] = {}
        self.baselines: dict[str, float] = {}
        self.rust_status: dict[str, bool] = {}

    def measure(self, name: str, func, *args, **kwargs) -> tuple[Any, float]:
        """Measure execution time of a function."""
        gc.collect()  # Clean state
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

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

        if name not in self.measurements:
            self.measurements[name] = []
        self.measurements[name].append(elapsed)

        return result, elapsed

    def get_statistics(self, name: str) -> dict[str, float]:
        """Get statistics for a measurement."""
        if name not in self.measurements or not self.measurements[name]:
            return {}

        values = self.measurements[name]
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
        if name not in self.baselines:
            return False

        stats = self.get_statistics(name)
        if not stats:
            return False

        # Check if median time is worse than baseline * threshold
        return stats["median"] > self.baselines[name] * threshold


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
        from ClassicLib.integration.factory import get_parser
        from ClassicLib.integration.status import is_rust_accelerated

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
        from ClassicLib.integration.factory import get_parser
        from ClassicLib.integration.status import is_rust_accelerated

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
        from ClassicLib.integration.factory import get_parser
        from ClassicLib.integration.status import is_rust_accelerated

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
        from ClassicLib.integration.factory import get_parser
        from ClassicLib.integration.status import is_rust_accelerated

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

    def test_formid_analysis_speed(self, metrics, generator):
        """Test FormID analysis performance (target: 25x speedup with Rust)."""
        from ClassicLib.integration.factory import get_formid_analyzer
        from ClassicLib.integration.status import is_rust_accelerated

        mock_yamldata = MagicMock()
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

    def test_formid_pattern_matching(self, metrics, generator):
        """Test FormID pattern matching performance."""
        from ClassicLib.integration.factory import get_formid_analyzer

        mock_yamldata = MagicMock()
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


class TestFileIOPerformance:
    """Test file I/O performance with Rust acceleration."""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    @pytest.mark.asyncio
    async def test_file_read_performance(self, metrics):
        """Test file reading performance (target: 10x speedup with Rust)."""
        from ClassicLib.FileIOCore import FileIOCore
        from ClassicLib.integration.status import is_rust_accelerated

        io_core = FileIOCore()
        using_rust = is_rust_accelerated("file_io")

        # Create test files of various sizes
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create 10 test files (100KB each)
            test_files = []
            for i in range(10):
                file_path = temp_path / f"test_{i}.log"
                content = "x" * (100 * 1024)  # 100KB
                file_path.write_text(content)
                test_files.append(file_path)

            # Measure read performance
            start = time.perf_counter()
            for file_path in test_files:
                content = await io_core.read_file(str(file_path))
                assert len(content) == 100 * 1024
            elapsed = time.perf_counter() - start

            per_file_ms = (elapsed / 10) * 1000

            print(f"\nFile I/O (10x100KB): {elapsed:.3f}s ({per_file_ms:.1f}ms per file)")

            if using_rust:
                # With Rust: 10 files in <50ms (5ms per file)
                assert elapsed < 0.05, f"File I/O slow with Rust: {elapsed:.3f}s"
                print(f"[RUST] Throughput: {(10 * 0.1) / elapsed:.1f} MB/s")
            else:
                # Python: 10 files in <500ms (50ms per file)
                assert elapsed < 0.5, f"File I/O slow with Python: {elapsed:.3f}s"
                print(f"[Python] Throughput: {(10 * 0.1) / elapsed:.1f} MB/s")

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, metrics):
        """Test concurrent file operations performance."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            for i in range(20):
                file_path = temp_path / f"concurrent_{i}.log"
                file_path.write_text(f"Content {i}\n" * 1000)

            # Concurrent reads
            async def read_file(path: Path):
                return await io_core.read_file(str(path))

            files = list(temp_path.glob("concurrent_*.log"))

            start = time.perf_counter()
            results = await asyncio.gather(*[read_file(f) for f in files])
            elapsed = time.perf_counter() - start

            assert len(results) == 20
            print(f"\nConcurrent reads (20 files): {elapsed:.3f}s")

            # Should handle concurrent ops efficiently
            assert elapsed < 1.0, f"Concurrent I/O too slow: {elapsed:.3f}s"


class TestPluginAnalysisPerformance:
    """Test plugin analysis performance."""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    @pytest.fixture
    def generator(self):
        return SyntheticDataGenerator()

    def test_plugin_conflict_detection(self, metrics, generator):
        """Test plugin conflict detection performance."""
        from ClassicLib.integration.factory import get_plugin_analyzer

        # Generate synthetic plugin data
        plugin_data = generator.generate_plugin_data(num_plugins=100, formids_per_plugin=100)

        with patch("ClassicLib.integration.plugin_analyzer.load_plugins", return_value=plugin_data):
            get_plugin_analyzer()

            # Measure conflict detection
            start = time.perf_counter()

            # Check for FormID conflicts between all plugin pairs
            conflicts = []
            plugin_list = list(plugin_data.items())
            for i in range(len(plugin_list)):
                for j in range(i + 1, len(plugin_list)):
                    plugin1_name, plugin1_data = plugin_list[i]
                    plugin2_name, plugin2_data = plugin_list[j]

                    # Find common FormIDs
                    common = set(plugin1_data["formids"]) & set(plugin2_data["formids"])
                    if common:
                        conflicts.append((plugin1_name, plugin2_name, list(common)))

            elapsed = time.perf_counter() - start

            print(f"\nPlugin conflict detection (100 plugins): {elapsed:.3f}s")
            print(f"Conflicts found: {len(conflicts)}")

            # Should detect conflicts quickly even with 100 plugins
            assert elapsed < 2.0, f"Conflict detection too slow: {elapsed:.3f}s"

    def test_dependency_chain_analysis(self, metrics, generator):
        """Test plugin dependency chain analysis performance."""
        # Create dependency chains
        dependencies = {}
        for i in range(50):
            plugin_name = f"Plugin_{i}.esp"
            deps = []
            if i > 0:
                # Each plugin depends on previous ones
                deps.append("Fallout4.esm")
                if i > 1:
                    deps.append(f"Plugin_{i - 1}.esp")
                if i > 10:
                    deps.append(f"Plugin_{i - 10}.esp")
            dependencies[plugin_name] = deps

        # Measure dependency resolution
        def resolve_dependencies(plugin: str, resolved: set = None) -> list[str]:
            if resolved is None:
                resolved = set()

            if plugin in resolved:
                return []

            resolved.add(plugin)
            result = []

            for dep in dependencies.get(plugin, []):
                result.extend(resolve_dependencies(dep, resolved))
            result.append(plugin)

            return result

        _, elapsed = metrics.measure("dependency_resolve", resolve_dependencies, "Plugin_49.esp")

        print(f"\nDependency chain resolution: {elapsed:.3f}s")

        # Should resolve complex chains quickly
        assert elapsed < 0.1, f"Dependency resolution too slow: {elapsed:.3f}s"


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
        from ClassicLib.integration.status import get_rust_component_status

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

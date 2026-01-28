"""Performance regression tests for I/O and plugin operations.

This module tests file I/O and plugin analysis performance, comparing
Rust-accelerated components against Python fallbacks and ensuring performance
targets are met.
"""

import asyncio
import gc
import random
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

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


class TestFileIOPerformance:
    """Test file I/O performance with Rust acceleration."""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    @pytest.mark.asyncio
    async def test_file_read_performance(self, metrics):
        """Test file reading performance using the best available backend.

        Uses the factory to get the correct FileIOCore (Rust or Python),
        ensuring Rust acceleration is actually exercised when available.
        Rust acceleration provides true async Tokio I/O; the biggest speedups
        are in batch/parallel reads and DDS parsing rather than sequential reads.
        """
        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()
        using_rust = getattr(io_core, "is_rust_accelerated", False)

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
                # Rust uses true async Tokio I/O with encoding detection.
                # Sequential single-file reads see moderate speedup; the major
                # gains come from batch/parallel operations and DDS parsing.
                assert elapsed < 0.3, f"File I/O slow with Rust: {elapsed:.3f}s"
                print(f"[RUST] Throughput: {(10 * 0.1) / elapsed:.1f} MB/s")
            else:
                # Python: chardet + aiofiles encoding detection path
                assert elapsed < 0.5, f"File I/O slow with Python: {elapsed:.3f}s"
                print(f"[Python] Throughput: {(10 * 0.1) / elapsed:.1f} MB/s")

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, metrics):
        """Test concurrent file operations performance."""
        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()

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

        # Generate synthetic plugin data
        plugin_data = generator.generate_plugin_data(num_plugins=100, formids_per_plugin=100)

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
        def resolve_dependencies(plugin: str, resolved: set = None) -> list[str]:  # pyright: ignore[reportArgumentType]
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

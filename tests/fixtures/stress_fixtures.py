"""Stress test fixtures and utilities.

This module provides comprehensive fixtures and utilities for stress testing
the Rust migration components under extreme production conditions.

Includes:
- Memory tracking utilities
- Concurrency testing helpers
- Data generators for large test datasets
- Performance profiling tools
"""

import threading
import time
import traceback
import tracemalloc
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import psutil
import pytest


# ============================================================================
# Memory Tracking
# ============================================================================


class MemoryTracker:
    """Tracks memory usage patterns during test execution.

    Provides detailed memory profiling including peak usage, growth patterns,
    and leak detection for comprehensive memory stress testing.
    """

    def __init__(self) -> None:
        """Initialize memory tracking."""
        self._initial_memory: float | None = None
        self._peak_memory: float = 0
        self._measurements: list[dict[str, Any]] = []
        self._tracking_enabled: bool = False

    def start_tracking(self) -> None:
        """Start memory tracking with tracemalloc."""
        tracemalloc.start()
        self._initial_memory = self._get_current_memory()
        self._peak_memory = self._initial_memory
        self._measurements = []
        self._tracking_enabled = True

    def stop_tracking(self) -> dict[str, Any]:
        """Stop tracking and return comprehensive memory statistics.

        Returns:
            Dict containing memory statistics including peak usage,
            growth patterns, and potential leak indicators.
        """
        if not self._tracking_enabled:
            return {}

        assert self._initial_memory is not None, "start_tracking() must be called before stop_tracking()"

        final_memory = self._get_current_memory()
        tracemalloc.stop()

        return {
            "initial_mb": self._initial_memory,
            "final_mb": final_memory,
            "peak_mb": self._peak_memory,
            "growth_mb": final_memory - self._initial_memory,
            "measurements": self._measurements,
            "potential_leak": final_memory > self._initial_memory * 1.5,
            "memory_efficiency": (final_memory / max(self._peak_memory, 1)) * 100,
        }

    def take_measurement(self, label: str = "") -> float:
        """Take a memory measurement and update peak tracking.

        Args:
            label: Optional label for the measurement

        Returns:
            Current memory usage in MB
        """
        if not self._tracking_enabled:
            return 0.0

        current = self._get_current_memory()
        self._peak_memory = max(self._peak_memory, current)

        self._measurements.append({"timestamp": time.time(), "memory_mb": current, "label": label})

        return current

    def _get_current_memory(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024


# ============================================================================
# Concurrency Testing
# ============================================================================


class ConcurrencyTestHelper:
    """Helper for testing concurrent operations and race conditions.

    Provides utilities for creating high-contention scenarios,
    detecting race conditions, and validating thread safety.
    """

    def __init__(self) -> None:
        """Initialize concurrency test helper."""
        self._shared_state: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._error_collector: list[dict[str, Any]] = []

    def create_contention_scenario(
        self,
        target_func: Callable[..., Any],
        num_threads: int = 20,
        iterations_per_thread: int = 100,
        shared_data: Any = None,
    ) -> dict[str, Any]:
        """Create a high-contention scenario to test thread safety.

        Args:
            target_func: Function to execute concurrently
            num_threads: Number of concurrent threads
            iterations_per_thread: Operations per thread
            shared_data: Data shared between threads

        Returns:
            Dict containing results and error information
        """
        self._error_collector = []
        results: list[Any] = []

        def worker(thread_id: int) -> list[Any]:
            """Worker function for concurrent execution."""
            thread_results = []
            try:
                for i in range(iterations_per_thread):
                    result = target_func(thread_id, i, shared_data)
                    thread_results.append(result)
            except Exception as e:
                self._error_collector.append({"thread_id": thread_id, "error": str(e), "traceback": traceback.format_exc()})
            return thread_results

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]

            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    self._error_collector.append({"error": str(e), "traceback": traceback.format_exc()})

        duration = time.time() - start_time

        return {
            "results": results,
            "errors": self._error_collector,
            "total_operations": num_threads * iterations_per_thread,
            "duration_seconds": duration,
            "operations_per_second": (num_threads * iterations_per_thread) / duration,
            "error_rate": len(self._error_collector) / max(len(results), 1),
        }

    def detect_race_conditions(self, operations: list[Callable[..., Any]], num_iterations: int = 1000) -> dict[str, Any]:
        """Detect potential race conditions by running operations many times.

        Args:
            operations: List of operations to run concurrently
            num_iterations: Number of test iterations

        Returns:
            Dict containing race condition analysis
        """
        inconsistencies = []

        for iteration in range(num_iterations):
            # Reset shared state for each iteration
            self._shared_state = {"counter": 0, "data": []}

            # Run all operations concurrently
            with ThreadPoolExecutor(max_workers=len(operations)) as executor:
                futures = [executor.submit(op, self._shared_state) for op in operations]
                results = [f.result() for f in as_completed(futures)]

            # Check for inconsistent state
            if self._is_state_inconsistent():
                inconsistencies.append({"iteration": iteration, "state": dict(self._shared_state), "results": results})

        return {
            "total_iterations": num_iterations,
            "inconsistencies_found": len(inconsistencies),
            "race_condition_rate": len(inconsistencies) / num_iterations,
            "sample_inconsistencies": inconsistencies[:5],
        }

    def _is_state_inconsistent(self) -> bool:
        """Check if current shared state shows inconsistencies."""
        return self._shared_state.get("counter", 0) != len(self._shared_state.get("data", []))


# ============================================================================
# Data Generation
# ============================================================================


class StressDataGenerator:
    """Generates large datasets for stress testing.

    Creates realistic test data that simulates production workloads
    with configurable complexity and size characteristics.
    """

    @staticmethod
    def generate_large_crash_log(size_mb: int = 100, plugin_count: int = 500, formid_count: int = 10000) -> str:
        """Generate a very large crash log for memory stress testing.

        Args:
            size_mb: Target size in MB (approximate)
            plugin_count: Number of plugins to include
            formid_count: Number of FormIDs to generate

        Returns:
            Large crash log content as string
        """
        lines = []

        # Header section
        lines.extend([
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512',
            "",
            "SYSTEM SPECS:",
            "\tOS: Microsoft Windows 11 Pro v10.0.22621",
            "\tCPU: AMD Ryzen 9 7950X3D 16-Core Processor",
            "\tGPU #1: Nvidia RTX 4090",
            "\tRAM: 64GB DDR5-6000",
            "",
        ])

        # Massive plugin list
        lines.append("PLUGINS:")
        for i in range(plugin_count):
            plugin_type = "esm" if i < 20 else "esp" if i < plugin_count - 50 else "esl"
            lines.append(f"\t[{i:03d}] StressTestPlugin_{i:04d}.{plugin_type}")
        lines.append("")

        # Large stack trace with many FormIDs
        lines.append("STACK TRACE:")
        for i in range(formid_count // 10):
            formid = f"0x{(0x14000000 + i):08X}"
            lines.extend([
                f"\t{i:04d} Fallout4.exe+{0x500000 + i * 16:07X}",
                f"\t     FormID: {formid} PluginIndex: {i % plugin_count:03d}",
                f"\t     Function: stress_test_function_{i % 100}()",
            ])

        # Add filler content to reach target size
        current_content = "\n".join(lines)
        current_size_mb = len(current_content.encode("utf-8")) / 1024 / 1024

        if current_size_mb < size_mb:
            filler_lines = []
            for section in range(int((size_mb - current_size_mb) * 100)):
                filler_lines.extend([
                    f"MEMORY SECTION {section:06d}:",
                    f"\tAddress: 0x{0x7FF000000000 + section * 0x1000:012X}",
                    f"\tSize: {4096 + section % 8192} bytes",
                    f"\tStatus: {'COMMITTED' if section % 3 == 0 else 'RESERVED'}",
                    f"\tProtection: {'PAGE_READWRITE' if section % 2 == 0 else 'PAGE_READONLY'}",
                    "",
                ])
            lines.extend(filler_lines)

        return "\n".join(lines)

    @staticmethod
    def generate_plugin_load_order(count: int = 500) -> list[str]:
        """Generate a large plugin load order for testing.

        Args:
            count: Number of plugins to generate

        Returns:
            List of plugin names
        """
        plugins = []

        # Essential master files
        essential = [
            "Fallout4.esm",
            "DLCRobot.esm",
            "DLCworkshop01.esm",
            "DLCworkshop02.esm",
            "DLCworkshop03.esm",
            "DLCCoast.esm",
            "DLCNukaWorld.esm",
        ]
        plugins.extend(essential)

        # Generate stress test plugins
        for i in range(count - len(essential)):
            if i < 50:
                plugins.append(f"StressMaster_{i:03d}.esm")
            elif i < count - 100:
                plugins.append(f"StressPlugin_{i:04d}.esp")
            else:
                plugins.append(f"StressLight_{i:03d}.esl")

        return plugins

    @staticmethod
    def generate_formid_dataset(count: int = 10000) -> list[str]:
        """Generate a large set of FormIDs for testing.

        Args:
            count: Number of FormIDs to generate

        Returns:
            List of FormID strings in various formats
        """
        formids = []

        for i in range(count):
            if i % 10 == 0:
                formids.append(f"0x{i % 0xFFFFFF:08X}")
            elif i % 10 == 1:
                formids.append(f"0x{0x01000000 + (i % 0xFFFFFF):08X}")
            elif i % 10 == 2:
                formids.append(f"0x{0x02000000 + (i % 0xFFFFFF):08X}")
            else:
                formids.append(f"0x{0x14000000 + i:08X}")

        return formids


# ============================================================================
# Performance Profiling
# ============================================================================


class PerformanceProfiler:
    """Profiles performance characteristics during stress tests.

    Monitors CPU usage, I/O patterns, and response times to detect
    performance degradation under sustained load.
    """

    def __init__(self) -> None:
        """Initialize performance profiler."""
        self._start_time: float | None = None
        self._measurements: list[dict[str, Any]] = []
        self._cpu_measurements: list[dict[str, Any]] = []
        self._io_measurements: list[dict[str, Any]] = []
        self._monitoring: bool = False
        self._monitor_thread: threading.Thread | None = None

    def start_profiling(self) -> None:
        """Start performance profiling."""
        self._start_time = time.time()
        self._measurements = []
        self._cpu_measurements = []
        self._io_measurements = []

        # Start background monitoring
        self._monitor_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self._monitoring = True
        self._monitor_thread.start()

    def stop_profiling(self) -> dict[str, Any]:
        """Stop profiling and return comprehensive performance statistics.

        Returns:
            Dict containing detailed performance metrics
        """
        self._monitoring = False
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=1)

        duration = time.time() - self._start_time if self._start_time else 0

        cpu_stats = self._calculate_cpu_stats()
        io_stats = self._calculate_io_stats()

        return {
            "duration_seconds": duration,
            "cpu_stats": cpu_stats,
            "io_stats": io_stats,
            "measurements": self._measurements,
            "performance_degradation": self._detect_degradation(),
        }

    def record_operation(self, operation_name: str, duration: float, memory_used: float = 0) -> None:
        """Record a single operation's performance metrics."""
        self._measurements.append({
            "timestamp": time.time(),
            "operation": operation_name,
            "duration_ms": duration * 1000,
            "memory_mb": memory_used,
        })

    def _background_monitor(self) -> None:
        """Background monitoring of system resources."""
        while self._monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self._cpu_measurements.append({"timestamp": time.time(), "cpu_percent": cpu_percent})

                process = psutil.Process()
                io_counters = process.io_counters()
                self._io_measurements.append({
                    "timestamp": time.time(),
                    "read_bytes": io_counters.read_bytes,
                    "write_bytes": io_counters.write_bytes,
                })

                time.sleep(0.1)
            except Exception:
                pass

    def _calculate_cpu_stats(self) -> dict[str, float]:
        """Calculate CPU usage statistics."""
        if not self._cpu_measurements:
            return {}

        cpu_values = [m["cpu_percent"] for m in self._cpu_measurements]
        return {"average_percent": sum(cpu_values) / len(cpu_values), "peak_percent": max(cpu_values), "min_percent": min(cpu_values)}

    def _calculate_io_stats(self) -> dict[str, Any]:
        """Calculate I/O statistics."""
        if len(self._io_measurements) < 2:
            return {}

        first = self._io_measurements[0]
        last = self._io_measurements[-1]
        duration = last["timestamp"] - first["timestamp"]

        read_rate = (last["read_bytes"] - first["read_bytes"]) / duration if duration > 0 else 0
        write_rate = (last["write_bytes"] - first["write_bytes"]) / duration if duration > 0 else 0

        return {
            "read_rate_bytes_per_sec": read_rate,
            "write_rate_bytes_per_sec": write_rate,
            "total_read_bytes": last["read_bytes"] - first["read_bytes"],
            "total_write_bytes": last["write_bytes"] - first["write_bytes"],
        }

    def _detect_degradation(self) -> dict[str, Any]:
        """Detect performance degradation patterns."""
        if len(self._measurements) < 10:
            return {"degradation_detected": False}

        early_ops = self._measurements[: len(self._measurements) // 3]
        late_ops = self._measurements[-len(self._measurements) // 3 :]

        early_avg = sum(op["duration_ms"] for op in early_ops) / len(early_ops)
        late_avg = sum(op["duration_ms"] for op in late_ops) / len(late_ops)

        degradation_factor = late_avg / early_avg if early_avg > 0 else 1.0

        return {
            "degradation_detected": degradation_factor > 1.5,
            "degradation_factor": degradation_factor,
            "early_avg_ms": early_avg,
            "late_avg_ms": late_avg,
        }


# ============================================================================
# Resource Simulation
# ============================================================================


class ResourceExhaustionSimulator:
    """Simulator for resource exhaustion scenarios."""

    def __init__(self) -> None:
        self.file_handles: int = 0
        self.memory_allocated: int = 0
        self.max_handles: int = 100
        self.max_memory: int = 1024 * 1024 * 1024  # 1GB

    def allocate_file_handle(self) -> Mock:
        """Allocate a simulated file handle."""
        if self.file_handles >= self.max_handles:
            raise OSError("Too many open files")
        self.file_handles += 1
        return Mock()

    def allocate_memory(self, size_bytes: int) -> bytearray:
        """Allocate simulated memory."""
        if self.memory_allocated + size_bytes > self.max_memory:
            raise MemoryError("Cannot allocate memory")
        self.memory_allocated += size_bytes
        return bytearray(size_bytes)

    def release_handle(self) -> None:
        """Release a file handle."""
        if self.file_handles > 0:
            self.file_handles -= 1

    def release_memory(self, size_bytes: int) -> None:
        """Release memory."""
        self.memory_allocated = max(0, self.memory_allocated - size_bytes)


class FailingDatabasePool:
    """Mock database pool that fails after some operations."""

    def __init__(self, fail_after: int = 100) -> None:
        self.operations: int = 0
        self.fail_after: int = fail_after

    def execute_query(self, query: str) -> Mock:
        """Execute a query, failing after threshold."""
        self.operations += 1
        if self.operations > self.fail_after:
            raise Exception(f"Database connection failed after {self.operations} operations")
        return Mock()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def memory_tracker() -> MemoryTracker:
    """Session-wide memory tracker for leak detection across tests."""
    return MemoryTracker()


@pytest.fixture
def fresh_memory_tracker() -> MemoryTracker:
    """Fresh memory tracker for individual test isolation."""
    return MemoryTracker()


@pytest.fixture
def concurrency_helper() -> ConcurrencyTestHelper:
    """Helper for concurrency and race condition testing."""
    return ConcurrencyTestHelper()


@pytest.fixture(scope="session")
def stress_data_generator() -> StressDataGenerator:
    """Generator for large test datasets."""
    return StressDataGenerator()


@pytest.fixture
def performance_profiler() -> PerformanceProfiler:
    """Performance profiler for monitoring test execution."""
    return PerformanceProfiler()


@pytest.fixture
def large_crash_log(tmp_path: Path, stress_data_generator: StressDataGenerator) -> Path:
    """Generate a large crash log file for memory stress testing.

    Args:
        tmp_path: Pytest temporary directory.
        stress_data_generator: Data generator fixture.

    Returns:
        Path to the large crash log file.
    """
    log_content = stress_data_generator.generate_large_crash_log(size_mb=50)
    log_file = tmp_path / "large_crash.log"
    log_file.write_text(log_content, encoding="utf-8")
    return log_file


@pytest.fixture
def massive_plugin_list(stress_data_generator: StressDataGenerator) -> list[str]:
    """Generate a massive plugin load order for testing."""
    return stress_data_generator.generate_plugin_load_order(count=500)


@pytest.fixture
def formid_dataset(stress_data_generator: StressDataGenerator) -> list[str]:
    """Generate a large FormID dataset for testing."""
    return stress_data_generator.generate_formid_dataset(count=5000)


@pytest.fixture
def temp_crash_logs_dir(tmp_path: Path, stress_data_generator: StressDataGenerator) -> Path:
    """Create directory with multiple large crash logs.

    Args:
        tmp_path: Pytest temporary directory.
        stress_data_generator: Data generator fixture.

    Returns:
        Path to directory containing crash logs.
    """
    logs_dir = tmp_path / "stress_crash_logs"
    logs_dir.mkdir()

    for i in range(10):
        log_content = stress_data_generator.generate_large_crash_log(
            size_mb=10,
            plugin_count=100,
            formid_count=1000,
        )
        log_file = logs_dir / f"stress_crash_{i:03d}.log"
        log_file.write_text(log_content, encoding="utf-8")

    return logs_dir


@pytest.fixture
def failing_database_pool() -> FailingDatabasePool:
    """Mock database pool that fails after some operations."""
    return FailingDatabasePool()


@pytest.fixture
def resource_exhaustion_simulator() -> ResourceExhaustionSimulator:
    """Simulator for resource exhaustion scenarios."""
    return ResourceExhaustionSimulator()

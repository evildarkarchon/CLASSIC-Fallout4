"""FFI Overhead Profiler for CLASSIC Rust Integration.

This module provides comprehensive profiling tools for analyzing Python↔Rust FFI overhead
and identifying optimization opportunities in the Phase 6 Rust migration.

Key Features:
- Call frequency and timing analysis for Python↔Rust boundaries
- Data marshaling overhead measurement for different data types
- Memory allocation tracking at FFI boundaries
- GIL acquisition/release overhead measurement
- High-frequency FFI crossing pattern identification

Performance Impact Analysis:
- Measures actual vs theoretical speedups from Rust migration
- Identifies bottlenecks where FFI overhead reduces Rust benefits
- Provides actionable optimization recommendations
- Tracks memory efficiency of data transfers

Usage:
    from tools.ffi_profiler import FFIProfiler

    profiler = FFIProfiler()
    with profiler.profile_ffi_calls():
        # Your Rust-accelerated code here
        result = rust_function(data)

    analysis = profiler.analyze_performance()
    profiler.print_report()
"""

from __future__ import annotations

import contextlib
import gc
import logging
import sys
import threading
import time
import traceback
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

# Try to import memory profiler for advanced memory tracking
try:
    import memory_profiler  # noqa: F401  # pyright: ignore[reportMissingTypeStubs]

    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class FFICall:
    """Represent a single FFI call with comprehensive profiling data."""

    # Basic call information
    function_name: str
    module_name: str
    call_timestamp: float
    thread_id: int

    # Performance measurements
    wall_time: float = 0.0  # Total wall clock time
    cpu_time: float = 0.0  # CPU time spent
    gil_wait_time: float = 0.0  # Time waiting for GIL

    # Data transfer measurements
    input_size: int = 0  # Size of input data in bytes
    output_size: int = 0  # Size of output data in bytes
    input_type: str = ""  # Type of input data (str, list, dict, etc.)
    output_type: str = ""  # Type of output data

    # Memory measurements
    memory_before: float = 0.0  # Memory usage before call (MB)
    memory_after: float = 0.0  # Memory usage after call (MB)
    memory_peak: float = 0.0  # Peak memory during call (MB)

    # Context information
    call_stack_depth: int = 0  # Python call stack depth
    is_batch_operation: bool = False  # Whether this is a batch call
    batch_size: int = 0  # Size of batch if applicable

    # Error tracking
    error: str | None = None  # Error message if call failed
    success: bool = True  # Whether call completed successfully


@dataclass
class FFIProfileStats:
    """Aggregated statistics for FFI performance analysis."""

    # Call frequency statistics
    total_calls: int = 0
    calls_per_second: float = 0.0
    unique_functions: int = 0

    # Performance statistics
    total_wall_time: float = 0.0
    total_cpu_time: float = 0.0
    total_gil_wait_time: float = 0.0
    average_call_time: float = 0.0
    median_call_time: float = 0.0
    p95_call_time: float = 0.0
    p99_call_time: float = 0.0

    # Data transfer statistics
    total_data_transferred: int = 0  # Total bytes transferred
    average_transfer_size: float = 0.0
    largest_transfer: int = 0
    transfer_efficiency: float = 0.0  # Data transferred per second

    # Memory statistics
    peak_memory_usage: float = 0.0
    average_memory_delta: float = 0.0
    memory_leaks_detected: int = 0

    # Optimization opportunities
    high_frequency_calls: list[str] = field(default_factory=list)
    expensive_calls: list[str] = field(default_factory=list)
    batch_opportunities: list[str] = field(default_factory=list)
    inefficient_transfers: list[str] = field(default_factory=list)


class FFIProfiler:
    """Comprehensive FFI profiler for analyzing Python↔Rust boundary performance.

    This profiler uses multiple techniques to capture detailed performance data:
    1. Function call tracing with sys.settrace
    2. Memory monitoring with psutil and memory_profiler
    3. GIL monitoring through threading analysis
    4. Data marshaling cost analysis
    """

    def __init__(
        self,
        rust_module_patterns: list[str] | None = None,
        memory_sampling_interval: float = 0.01,
        enable_gil_monitoring: bool = True,
        max_call_history: int = 10000,
    ) -> None:
        """Initialize the FFI profiler.

        Args:
            rust_module_patterns: List of module name patterns to identify Rust calls
            memory_sampling_interval: Interval for memory sampling (seconds)
            enable_gil_monitoring: Whether to monitor GIL contention
            max_call_history: Maximum number of calls to store in history

        """
        # Configuration
        self.rust_module_patterns = rust_module_patterns or [
            "classic_scanlog",
            "classic_database",
            "classic_file_io",
            "classic_yaml",
            "classic_path",
            "classic_config",
            "classic_perf",
            "classic_registry",
            "classic_resource",
            "classic_settings",
            "classic_update",
            "classic_version",
            "classic_web",
            "classic_xse",
            "_rust",
            "rust_",
            "pyo3_",
            "maturin_",
        ]
        self.memory_sampling_interval = memory_sampling_interval
        self.enable_gil_monitoring = enable_gil_monitoring
        self.max_call_history = max_call_history

        # Profiling state
        self.is_profiling = False
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._original_trace_func = None

        # Data collection
        self.ffi_calls: deque[FFICall] = deque(maxlen=max_call_history)
        self.call_counts: defaultdict[str, int] = defaultdict(int)
        self.call_times: defaultdict[str, list[float]] = defaultdict(list)
        self.memory_timeline: list[tuple[float, float]] = []  # (timestamp, memory_mb)

        # Threading support
        self._profile_lock = threading.RLock()
        self._memory_monitor_thread: threading.Thread | None = None
        self._stop_monitoring = threading.Event()

        # GIL monitoring
        self._gil_monitor_thread: threading.Thread | None = None
        self.gil_contention_events: list[tuple[float, float]] = []  # (timestamp, wait_time)

        # Performance baseline
        self._baseline_memory: float | None = None
        self._process = psutil.Process()

    def _is_rust_call(self, frame: Any) -> bool:
        """Determine if a frame represents a call to Rust code.

        This uses heuristics to identify Rust calls:
        1. Module name patterns (classic_scanlog, _rust, etc.)
        2. File path analysis
        3. Function name patterns
        """
        try:
            # Check module name
            module_name = frame.f_globals.get("__name__", "")
            for pattern in self.rust_module_patterns:
                if pattern in module_name:
                    return True

            # Check file path for compiled extensions
            filename = frame.f_code.co_filename
            if filename.endswith((".pyd", ".so", ".dylib")):
                return True

            # Check for PyO3/maturin indicators in function names
            func_name = frame.f_code.co_name
            return any(indicator in func_name.lower() for indicator in ["rust_", "pyo3_", "_rust"])
        except (AttributeError, KeyError):
            return False

    def _get_data_size(self, obj: Any) -> int:
        """Estimate the size of data being transferred across FFI boundary.

        This provides a rough estimate of marshaling cost by analyzing
        the size and complexity of Python objects.
        """
        try:
            # Use sys.getsizeof for basic size
            size = sys.getsizeof(obj)

            # Add recursive size for collections
            if isinstance(obj, (list, tuple)):
                size += sum(self._get_data_size(item) for item in obj[:100])  # Limit to avoid deep recursion # pyright: ignore[reportUnknownArgumentType, reportUnknownReturnType, reportUnknownVariableType]
            elif isinstance(obj, dict):
                for k, v in list(obj.items())[:100]:  # Limit items # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
                    size += self._get_data_size(k) + self._get_data_size(v)
            elif isinstance(obj, str):
                # String marshaling has specific overhead
                size += len(obj.encode("utf-8", errors="ignore"))  # pyright: ignore[reportUnknownArgumentType]

            return size  # noqa: TRY300
        except (RecursionError, MemoryError):
            # Fallback for complex objects
            return sys.getsizeof(obj)  # pyright: ignore[reportUnknownArgumentType]

    @staticmethod
    def _get_data_type(obj: Any) -> str:
        """Get a descriptive type string for data transfer analysis."""
        obj_type = type(obj).__name__

        # Add size information for collections
        if isinstance(obj, (list, tuple)):
            obj_type += f"[{len(obj)}]"  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(obj, dict):
            obj_type += f"{{{len(obj)}}}"  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(obj, str):
            obj_type += f"({len(obj)}chars)"  # pyright: ignore[reportUnknownArgumentType]
        elif hasattr(obj, "__len__"):
            with contextlib.suppress(Exception):
                obj_type += f"[{len(obj)}]"  # pyright: ignore[reportUnknownArgumentType]

        return obj_type

    def _memory_monitor(self) -> None:
        """Background thread to monitor memory usage during profiling."""
        try:
            while not self._stop_monitoring.wait(self.memory_sampling_interval):
                try:
                    # Get current memory usage in MB
                    memory_mb = self._process.memory_info().rss / 1024 / 1024  # pyright: ignore[reportUnknownReturnType]
                    timestamp = time.perf_counter()

                    with self._profile_lock:
                        self.memory_timeline.append((timestamp, memory_mb))

                        # Keep timeline manageable
                        if len(self.memory_timeline) > 10000:
                            self.memory_timeline = self.memory_timeline[-5000:]

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"Memory monitoring error: {e}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Memory monitor thread failed: {e}")

    def _gil_monitor(self) -> None:
        """Background thread to monitor GIL contention."""
        if not self.enable_gil_monitoring:
            return

        try:  # noqa: PLR1702
            while not self._stop_monitoring.wait(0.001):  # High frequency sampling
                try:
                    # Measure time to acquire a lock (proxy for GIL contention)
                    start_time = time.perf_counter()
                    test_lock = threading.Lock()
                    with test_lock:
                        pass
                    end_time = time.perf_counter()

                    wait_time = end_time - start_time
                    if wait_time > 0.0001:  # Only record significant waits (>0.1ms)
                        with self._profile_lock:
                            self.gil_contention_events.append((start_time, wait_time))

                            # Keep events manageable
                            if len(self.gil_contention_events) > 1000:
                                self.gil_contention_events = self.gil_contention_events[-500:]

                except Exception as e:  # noqa: BLE001
                    logger.debug(f"GIL monitoring error: {e}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"GIL monitor thread failed: {e}")

    def _trace_calls(self, frame: Any, event: str, arg: Any) -> Any:  # noqa: PLR0912
        """Trace function calls to identify and profile FFI calls.

        This is the core tracing function that captures detailed information
        about every function call, focusing on Rust FFI boundaries.
        """
        if not self.is_profiling:
            return None

        try:  # noqa: PLR1702
            if event == "call" and self._is_rust_call(frame):
                # Start of a Rust call
                call_start = time.perf_counter()
                call_start_cpu = time.process_time()

                # Get memory usage before call
                memory_before = self._process.memory_info().rss / 1024 / 1024  # pyright: ignore[reportUnknownReturnType]

                # Extract call information
                func_name = frame.f_code.co_name
                module_name = frame.f_globals.get("__name__", "unknown")
                thread_id = threading.get_ident()
                call_stack_depth = len(traceback.extract_stack())

                # Try to estimate input data size (from frame locals)
                input_size = 0
                input_types = []

                try:
                    # Look at function arguments in frame locals
                    for name, value in frame.f_locals.items():
                        if not name.startswith("_"):  # Skip private variables
                            input_size += self._get_data_size(value)
                            input_types.append(self._get_data_type(value))
                except Exception:  # noqa: BLE001
                    pass

                # Store call start info in frame for retrieval on return
                frame.ffi_profile_data = {
                    "start_time": call_start,
                    "start_cpu": call_start_cpu,
                    "memory_before": memory_before,
                    "func_name": func_name,
                    "module_name": module_name,
                    "thread_id": thread_id,
                    "input_size": input_size,
                    "input_types": input_types,
                    "call_stack_depth": call_stack_depth,
                }

            elif event == "return" and hasattr(frame, "ffi_profile_data"):
                # End of a Rust call
                call_end = time.perf_counter()
                call_end_cpu = time.process_time()
                memory_after = self._process.memory_info().rss / 1024 / 1024  # pyright: ignore[reportUnknownReturnType]

                # Retrieve call start info
                profile_data = frame.ffi_profile_data

                # Calculate timings
                wall_time = call_end - profile_data["start_time"]
                cpu_time = call_end_cpu - profile_data["start_cpu"]

                # Estimate output data size
                output_size = 0
                output_type = ""
                if arg is not None:  # Return value
                    output_size = self._get_data_size(arg)
                    output_type = self._get_data_type(arg)

                # Check for batch operations (heuristic: large input or multiple items)
                is_batch = profile_data["input_size"] > 10000 or any(
                    "[" in t and int(t.split("[")[1].split("]")[0]) > 10 for t in profile_data["input_types"] if "[" in t
                )

                batch_size = 0
                if is_batch:
                    # Try to estimate batch size from input types
                    for input_type in profile_data["input_types"]:
                        if "[" in input_type:
                            try:
                                size_str = input_type.split("[")[1].split("]")[0]
                                batch_size = max(batch_size, int(size_str))
                            except (ValueError, IndexError):
                                pass

                # Create FFI call record
                ffi_call = FFICall(
                    function_name=profile_data["func_name"],
                    module_name=profile_data["module_name"],
                    call_timestamp=profile_data["start_time"],
                    thread_id=profile_data["thread_id"],
                    wall_time=wall_time,
                    cpu_time=cpu_time,
                    input_size=profile_data["input_size"],
                    output_size=output_size,
                    input_type=", ".join(profile_data["input_types"]) if profile_data["input_types"] else "unknown",
                    output_type=output_type,
                    memory_before=profile_data["memory_before"],
                    memory_after=memory_after,
                    call_stack_depth=profile_data["call_stack_depth"],
                    is_batch_operation=is_batch,
                    batch_size=batch_size,
                    success=True,
                )

                # Record the call
                with self._profile_lock:
                    self.ffi_calls.append(ffi_call)
                    func_key = f"{profile_data['module_name']}.{profile_data['func_name']}"
                    self.call_counts[func_key] += 1
                    self.call_times[func_key].append(wall_time)

                # Clean up frame data
                delattr(frame, "ffi_profile_data")

        except Exception as e:  # noqa: BLE001
            # Don't let profiling errors break the application
            logger.debug(f"FFI profiling error: {e}")

        # Continue with original trace function if any
        if self._original_trace_func:
            return self._original_trace_func(frame, event, arg)

        return None

    def start_profiling(self) -> None:
        """Start FFI profiling with comprehensive monitoring."""
        if self.is_profiling:
            logger.warning("FFI profiling already active")
            return

        logger.info("Starting FFI profiling with comprehensive monitoring")

        # Reset state
        self.ffi_calls.clear()
        self.call_counts.clear()
        self.call_times.clear()
        self.memory_timeline.clear()
        self.gil_contention_events.clear()

        # Set up timing
        self._start_time = time.perf_counter()
        self.is_profiling = True

        # Get baseline memory
        self._baseline_memory = self._process.memory_info().rss / 1024 / 1024  # pyright: ignore[reportUnknownReturnType]

        # Set up tracing
        self._original_trace_func = sys.gettrace()
        sys.settrace(self._trace_calls)

        # Start monitoring threads
        self._stop_monitoring.clear()

        self._memory_monitor_thread = threading.Thread(target=self._memory_monitor, daemon=True)
        self._memory_monitor_thread.start()

        if self.enable_gil_monitoring:
            self._gil_monitor_thread = threading.Thread(target=self._gil_monitor, daemon=True)
            self._gil_monitor_thread.start()

        logger.info("FFI profiling started successfully")

    def stop_profiling(self) -> None:
        """Stop FFI profiling and finalize data collection."""
        if not self.is_profiling:
            logger.warning("FFI profiling not active")
            return

        logger.info("Stopping FFI profiling")

        # Stop profiling
        self.is_profiling = False
        self._end_time = time.perf_counter()

        # Restore original trace function
        sys.settrace(self._original_trace_func)

        # Stop monitoring threads
        self._stop_monitoring.set()

        if self._memory_monitor_thread and self._memory_monitor_thread.is_alive():
            self._memory_monitor_thread.join(timeout=1.0)

        if self._gil_monitor_thread and self._gil_monitor_thread.is_alive():
            self._gil_monitor_thread.join(timeout=1.0)

        # Force garbage collection to get accurate final memory
        gc.collect()

        logger.info(f"FFI profiling stopped. Collected {len(self.ffi_calls)} FFI calls")

    @contextlib.contextmanager
    def profile_ffi_calls(self) -> Any:
        """Context manager for FFI profiling."""
        self.start_profiling()
        try:
            yield self
        finally:
            self.stop_profiling()

    def get_profile_duration(self) -> float:
        """Get the total profiling duration in seconds."""
        if self._start_time is None:
            return 0.0
        end_time = self._end_time or time.perf_counter()
        return end_time - self._start_time

    def analyze_performance(self) -> FFIProfileStats:
        """Analyze collected profiling data and return comprehensive statistics.

        This performs detailed analysis of:
        - Call frequency and patterns
        - Performance bottlenecks
        - Memory usage patterns
        - Optimization opportunities
        """
        if not self.ffi_calls:
            return FFIProfileStats()

        # Calculate timing statistics
        all_wall_times = [call.wall_time for call in self.ffi_calls]
        all_wall_times.sort()

        total_calls = len(self.ffi_calls)
        duration = self.get_profile_duration()
        calls_per_second = total_calls / duration if duration > 0 else 0

        # Performance statistics
        total_wall_time = sum(all_wall_times)
        total_cpu_time = sum(call.cpu_time for call in self.ffi_calls)
        total_gil_wait_time = sum(event[1] for event in self.gil_contention_events)

        average_call_time = total_wall_time / total_calls if total_calls > 0 else 0
        median_call_time = all_wall_times[total_calls // 2] if total_calls > 0 else 0
        p95_call_time = all_wall_times[int(total_calls * 0.95)] if total_calls > 0 else 0
        p99_call_time = all_wall_times[int(total_calls * 0.99)] if total_calls > 0 else 0

        # Data transfer statistics
        total_data_transferred = sum(call.input_size + call.output_size for call in self.ffi_calls)
        average_transfer_size = total_data_transferred / total_calls if total_calls > 0 else 0
        largest_transfer = max((call.input_size + call.output_size) for call in self.ffi_calls) if self.ffi_calls else 0
        transfer_efficiency = total_data_transferred / total_wall_time if total_wall_time > 0 else 0

        # Memory statistics
        memory_deltas = [call.memory_after - call.memory_before for call in self.ffi_calls]
        peak_memory_usage = max(call.memory_after for call in self.ffi_calls) if self.ffi_calls else 0
        average_memory_delta = sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0
        memory_leaks_detected = sum(1 for delta in memory_deltas if delta > 10)  # >10MB increase

        # Identify optimization opportunities
        # High frequency calls (called more than 100 times or >10% of total calls)
        high_frequency_threshold = max(100, total_calls * 0.1)
        high_frequency_calls = [func for func, count in self.call_counts.items() if count >= high_frequency_threshold]

        # Expensive calls (>95th percentile in time)
        expensive_calls = []
        if p95_call_time > 0:
            expensive_funcs: set[str] = set()
            for call in self.ffi_calls:
                if call.wall_time >= p95_call_time:
                    expensive_funcs.add(f"{call.module_name}.{call.function_name}")
            expensive_calls = list(expensive_funcs)

        # Batch opportunities (functions called frequently with small data)
        batch_opportunities = []
        func_call_patterns: defaultdict[str, list[FFICall]] = defaultdict(list)
        for call in self.ffi_calls:
            func_key = f"{call.module_name}.{call.function_name}"
            func_call_patterns[func_key].append(call)

        for func, calls in func_call_patterns.items():
            if len(calls) > 50:  # Called frequently
                avg_input_size = sum(call.input_size for call in calls) / len(calls)
                if avg_input_size < 1000:  # Small individual calls
                    batch_opportunities.append(func)

        # Inefficient transfers (high data volume, low transfer efficiency)
        inefficient_transfers = []
        for func, calls in func_call_patterns.items():
            total_transfer = sum(call.input_size + call.output_size for call in calls)
            total_time = sum(call.wall_time for call in calls)
            if total_transfer > 100000 and total_time > 0:  # >100KB total
                efficiency = total_transfer / total_time
                if efficiency < 1000000:  # <1MB/s (inefficient)
                    inefficient_transfers.append(func)

        # Get unique functions
        unique_functions = len({f"{call.module_name}.{call.function_name}" for call in self.ffi_calls})

        return FFIProfileStats(
            total_calls=total_calls,
            calls_per_second=calls_per_second,
            unique_functions=unique_functions,
            total_wall_time=total_wall_time,
            total_cpu_time=total_cpu_time,
            total_gil_wait_time=total_gil_wait_time,
            average_call_time=average_call_time,
            median_call_time=median_call_time,
            p95_call_time=p95_call_time,
            p99_call_time=p99_call_time,
            total_data_transferred=total_data_transferred,
            average_transfer_size=average_transfer_size,
            largest_transfer=largest_transfer,
            transfer_efficiency=transfer_efficiency,
            peak_memory_usage=peak_memory_usage,
            average_memory_delta=average_memory_delta,
            memory_leaks_detected=memory_leaks_detected,
            high_frequency_calls=high_frequency_calls,
            expensive_calls=expensive_calls,
            batch_opportunities=batch_opportunities,  # pyright: ignore[reportUnknownArgumentType]
            inefficient_transfers=inefficient_transfers,  # pyright: ignore[reportUnknownArgumentType]
        )

    def print_report(self, detailed: bool = True) -> None:  # noqa: PLR0912
        """Print a comprehensive FFI profiling report.

        Args:
            detailed: Whether to include detailed call-by-call analysis

        """
        stats = self.analyze_performance()
        duration = self.get_profile_duration()

        print("\n" + "=" * 80)
        print("🔍 FFI OVERHEAD PROFILING REPORT")
        print("=" * 80)

        # Basic statistics
        print("\n📊 PROFILING SUMMARY:")
        print(f"  Duration           : {duration:.2f}s")
        print(f"  Total FFI Calls    : {stats.total_calls:,}")
        print(f"  Unique Functions   : {stats.unique_functions}")
        print(f"  Calls per Second   : {stats.calls_per_second:.1f}")

        # Performance analysis
        print("\n⏱️ PERFORMANCE ANALYSIS:")
        print(f"  Total Wall Time    : {stats.total_wall_time:.3f}s")
        print(f"  Total CPU Time     : {stats.total_cpu_time:.3f}s")
        print(f"  Total GIL Wait     : {stats.total_gil_wait_time:.3f}s")
        print(f"  Average Call Time  : {stats.average_call_time * 1000:.2f}ms")
        print(f"  Median Call Time   : {stats.median_call_time * 1000:.2f}ms")
        print(f"  95th Percentile    : {stats.p95_call_time * 1000:.2f}ms")
        print(f"  99th Percentile    : {stats.p99_call_time * 1000:.2f}ms")

        # Data transfer analysis
        print("\n💾 DATA TRANSFER ANALYSIS:")
        print(f"  Total Data Transfer: {stats.total_data_transferred:,} bytes ({stats.total_data_transferred / 1024 / 1024:.2f}MB)")
        print(f"  Average Transfer   : {stats.average_transfer_size:.0f} bytes")
        print(f"  Largest Transfer   : {stats.largest_transfer:,} bytes")
        print(f"  Transfer Efficiency: {stats.transfer_efficiency / 1024 / 1024:.2f} MB/s")

        # Memory analysis
        print("\n🧠 MEMORY ANALYSIS:")
        print(f"  Peak Memory Usage  : {stats.peak_memory_usage:.2f}MB")
        print(f"  Average Memory Δ   : {stats.average_memory_delta:+.2f}MB")
        print(f"  Potential Leaks    : {stats.memory_leaks_detected}")

        # Optimization opportunities
        print("\n🚀 OPTIMIZATION OPPORTUNITIES:")

        if stats.high_frequency_calls:
            print(f"  High-Frequency Calls ({len(stats.high_frequency_calls)}):")
            for func in stats.high_frequency_calls[:5]:  # Show top 5
                count = self.call_counts[func]
                avg_time = sum(self.call_times[func]) / len(self.call_times[func])
                print(f"    • {func}: {count:,} calls, {avg_time * 1000:.2f}ms avg")

        if stats.expensive_calls:
            print(f"  Expensive Calls ({len(stats.expensive_calls)}):")
            for func in stats.expensive_calls[:5]:
                if func in self.call_times:
                    max_time = max(self.call_times[func])
                    print(f"    • {func}: max {max_time * 1000:.2f}ms")

        if stats.batch_opportunities:
            print(f"  Batching Opportunities ({len(stats.batch_opportunities)}):")
            for func in stats.batch_opportunities[:5]:
                count = self.call_counts[func]
                print(f"    • {func}: {count:,} small calls")

        if stats.inefficient_transfers:
            print(f"  Inefficient Transfers ({len(stats.inefficient_transfers)}):")
            for func in stats.inefficient_transfers[:3]:
                print(f"    • {func}: Low transfer efficiency")

        # Detailed call analysis
        if detailed and len(self.ffi_calls) > 0:
            print("\n🔎 TOP EXPENSIVE CALLS:")
            sorted_calls = sorted(self.ffi_calls, key=lambda c: c.wall_time, reverse=True)
            for i, call in enumerate(sorted_calls[:10], 1):
                print(f"  {i:2d}. {call.module_name}.{call.function_name}")
                print(
                    f"      Time: {call.wall_time * 1000:.2f}ms | "
                    f"Data: {call.input_size + call.output_size:,}B | "
                    f"Memory Δ: {call.memory_after - call.memory_before:+.2f}MB"
                )

        # FFI efficiency analysis
        print("\n📈 FFI EFFICIENCY ANALYSIS:")
        if stats.total_wall_time > 0:
            ffi_overhead_pct = (stats.total_wall_time / duration) * 100
            print(f"  FFI Time Overhead  : {ffi_overhead_pct:.1f}% of total time")

            if ffi_overhead_pct > 20:
                print("  ⚠️ WARNING: High FFI overhead detected!")
                print("     Consider batching operations or reducing call frequency")
            elif ffi_overhead_pct < 5:
                print("  ✅ Good: FFI overhead is minimal")
            else:
                print("  ℹ️ Moderate FFI overhead - optimization may help")  # noqa: RUF001

        if stats.total_gil_wait_time > 0 and stats.total_wall_time > 0:
            gil_overhead_pct = (stats.total_gil_wait_time / stats.total_wall_time) * 100
            print(f"  GIL Wait Overhead  : {gil_overhead_pct:.1f}% of FFI time")

            if gil_overhead_pct > 10:
                print("  ⚠️ High GIL contention detected!")

        print("=" * 80)

    def export_data(self, filepath: str | Path) -> None:
        """Export profiling data to JSON for further analysis."""
        import json
        from pathlib import Path

        filepath = Path(filepath)

        # Convert data to serializable format
        export_data = {
            "metadata": {
                "start_time": self._start_time,
                "end_time": self._end_time,
                "duration": self.get_profile_duration(),
                "rust_module_patterns": self.rust_module_patterns,
                "memory_profiler_available": MEMORY_PROFILER_AVAILABLE,
                "baseline_memory": self._baseline_memory,
            },
            "calls": [
                {
                    "function_name": call.function_name,
                    "module_name": call.module_name,
                    "call_timestamp": call.call_timestamp,
                    "thread_id": call.thread_id,
                    "wall_time": call.wall_time,
                    "cpu_time": call.cpu_time,
                    "input_size": call.input_size,
                    "output_size": call.output_size,
                    "input_type": call.input_type,
                    "output_type": call.output_type,
                    "memory_before": call.memory_before,
                    "memory_after": call.memory_after,
                    "is_batch_operation": call.is_batch_operation,
                    "batch_size": call.batch_size,
                    "success": call.success,
                    "error": call.error,
                }
                for call in self.ffi_calls
            ],
            "memory_timeline": self.memory_timeline,
            "gil_contention": self.gil_contention_events,
            "statistics": {"call_counts": dict(self.call_counts), "call_times": {k: list(v) for k, v in self.call_times.items()}},
        }

        with Path(filepath).open("w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"FFI profiling data exported to {filepath}")


# Convenience functions for quick profiling
def profile_ffi_function(func: Callable[..., Any]) -> Callable[..., Any]:  # pyright: ignore[reportUnknownReturnType]
    """Decorate to profile a single function's FFI usage.

    Usage:
        @profile_ffi_function
        def my_rust_calling_function():
            return rust_module.expensive_operation()
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        profiler = FFIProfiler()
        with profiler.profile_ffi_calls():
            result = func(*args, **kwargs)

        print(f"\nFFI Profile for {func.__name__}:")
        profiler.print_report(detailed=False)
        return result

    return wrapper


def quick_profile_context() -> Any:
    """Quick context manager for FFI profiling.

    Usage:
        with quick_profile_context() as profiler:
            # Your Rust-calling code here
            pass
        # Report is automatically printed
    """
    profiler = FFIProfiler()

    @contextlib.contextmanager
    def profile_context() -> Any:
        with profiler.profile_ffi_calls():
            yield profiler
        profiler.print_report(detailed=False)

    return profile_context()


if __name__ == "__main__":
    # Example usage and testing
    print("FFI Profiler - Test Mode")
    print("This would typically be used to profile Rust FFI calls.")

    # Create a test profiler
    profiler = FFIProfiler()

    # Simulate some test data
    import random

    with profiler.profile_ffi_calls():
        # Simulate some "FFI calls" with sleeps
        for _i in range(10):
            time.sleep(random.uniform(0.001, 0.01))

    profiler.print_report()

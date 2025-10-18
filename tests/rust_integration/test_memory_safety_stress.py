"""Memory safety stress tests for Rust-Python FFI boundary.

This module stress tests memory safety at the FFI boundary, ensuring
no memory leaks, proper cleanup, and graceful handling of extreme
memory conditions using only synthetic data.
"""

import pytest
import gc
import psutil
import threading
import time
import weakref
import sys
from pathlib import Path

# resource module is Unix-only
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False
from typing import List, Any, Optional
from unittest.mock import MagicMock, patch
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import random
import string

# Mark all tests in this module
pytestmark = [pytest.mark.stress, pytest.mark.rust, pytest.mark.slow]


class MemoryMonitor:
    """Monitor memory usage during tests."""

    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = None
        self.peak_memory = 0
        self.samples = []

    def start(self):
        """Start monitoring memory."""
        gc.collect()
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory
        self.samples = [self.initial_memory]

    def sample(self):
        """Take a memory sample."""
        current = self.process.memory_info().rss
        self.samples.append(current)
        self.peak_memory = max(self.peak_memory, current)
        return current

    def get_leak_estimate(self) -> int:
        """Estimate memory leak in bytes."""
        gc.collect()
        final = self.process.memory_info().rss
        # Allow for some variance (10MB)
        variance = 10 * 1024 * 1024
        leak = final - self.initial_memory
        return max(0, leak - variance)


class SyntheticDataGenerator:
    """Generate synthetic data for memory tests."""

    @staticmethod
    def generate_large_log(size_mb: float) -> str:
        """Generate a synthetic crash log of specified size."""
        size_bytes = int(size_mb * 1024 * 1024)
        lines = []
        current_size = 0

        # Synthetic log patterns
        patterns = [
            "ERROR: Synthetic memory allocation failed at 0x{:08X}",
            "STACK: [{:08X}] synthetic_module.dll+{:04X}",
            "FormID: {:08X} from SyntheticPlugin.esp",
            "WARNING: Synthetic buffer overflow detected",
            "DEBUG: Memory usage: {} bytes allocated",
        ]

        line_num = 0
        while current_size < size_bytes:
            pattern = random.choice(patterns)
            line = pattern.format(random.randint(0, 0xFFFFFFFF))
            lines.append(f"{line_num:06d}: {line}")
            current_size += len(lines[-1]) + 1  # +1 for newline
            line_num += 1

        return "\n".join(lines)

    @staticmethod
    def generate_formid_batch(count: int) -> List[str]:
        """Generate a batch of synthetic FormIDs."""
        formids = []
        for i in range(count):
            plugin_index = random.randint(0x00, 0xFF)
            local_id = random.randint(0x000001, 0xFFFFFF)
            formid = f"{plugin_index:02X}{local_id:06X}"
            formids.append(formid)
        return formids

    @staticmethod
    def generate_plugin_data(size_kb: int) -> dict:
        """Generate synthetic plugin data structure."""
        num_records = size_kb * 10  # Approximate
        return {
            "header": "SYNTH_PLUGIN_V1",
            "formids": SyntheticDataGenerator.generate_formid_batch(num_records),
            "records": [
                {
                    "type": random.choice(["NPC_", "WEAP", "ARMO", "CELL"]),
                    "formid": f"{i:08X}",
                    "data": "x" * random.randint(10, 100)
                }
                for i in range(min(num_records, 1000))
            ],
            "size": size_kb * 1024
        }


class TestMemorySafetyStress:
    """Test memory safety under stress conditions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.rust_available = False
        try:
            import classic_core
            self.rust_available = True
        except ImportError:
            pass

        # Force garbage collection before each test
        gc.collect()

    def test_large_allocation_deallocation_cycles(self):
        """Test rapid allocation and deallocation of large objects."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        monitor = MemoryMonitor()
        monitor.start()

        parser = get_parser()
        generator = SyntheticDataGenerator()

        # Perform 100 allocation/deallocation cycles
        for cycle in range(100):
            # Allocate large synthetic log (5-10MB)
            size_mb = random.uniform(5, 10)
            large_log = generator.generate_large_log(size_mb)

            # Parse it (causes Rust allocation) using find_segments
            lines = large_log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(
                lines, "Buffout 4", "F4SE", "Fallout4.exe"
            )

            # Explicitly delete to trigger deallocation
            del large_log
            del segments

            # Force Python GC every 10 cycles
            if cycle % 10 == 0:
                gc.collect()
                monitor.sample()

        # Final cleanup
        gc.collect()
        time.sleep(0.1)  # Allow Rust cleanup

        # Check for memory leaks
        leak = monitor.get_leak_estimate()
        leak_mb = leak / (1024 * 1024)

        # Should not leak more than 50MB after 100 cycles
        assert leak_mb < 50, f"Memory leak detected: {leak_mb:.2f}MB"

    def test_concurrent_memory_operations(self):
        """Test memory safety with concurrent operations from multiple threads."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser, get_formid_analyzer

        monitor = MemoryMonitor()
        monitor.start()

        generator = SyntheticDataGenerator()
        errors = []

        def worker(worker_id: int, num_ops: int):
            """Worker thread that performs memory operations."""
            try:
                parser = get_parser()
                mock_yamldata = MagicMock()
                analyzer = get_formid_analyzer(mock_yamldata, True, False)

                for op in range(num_ops):
                    # Generate and parse synthetic data
                    if op % 2 == 0:
                        # Parse log using find_segments
                        log = generator.generate_large_log(random.uniform(0.5, 2))
                        lines = log.splitlines()
                        game_ver, crashgen_ver, error, segments = parser.find_segments(
                            lines, "Buffout 4", "F4SE", "Fallout4.exe"
                        )
                        del segments
                    else:
                        # Analyze FormIDs using extract_formids
                        formids = generator.generate_formid_batch(random.randint(100, 1000))
                        results = analyzer.extract_formids(formids)
                        del results

                    # Periodic cleanup
                    if op % 10 == 0:
                        gc.collect()

            except Exception as e:
                errors.append((worker_id, e))

        # Launch concurrent workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(worker, i, 50)
                for i in range(10)
            ]

            # Wait for completion
            for future in as_completed(futures):
                future.result()

        # Check for errors
        assert len(errors) == 0, f"Errors in workers: {errors}"

        # Check memory
        gc.collect()
        leak = monitor.get_leak_estimate()
        leak_mb = leak / (1024 * 1024)

        # Should not leak more than 100MB with 10 concurrent threads
        assert leak_mb < 100, f"Memory leak with concurrency: {leak_mb:.2f}MB"

    def test_reference_counting_across_ffi(self):
        """Test that reference counting works correctly across FFI boundary."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        generator = SyntheticDataGenerator()

        # Create objects and track with weak references
        weak_refs = []

        for i in range(100):
            # Create synthetic data
            data = generator.generate_large_log(1)
            lines = data.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(
                lines, "Buffout 4", "F4SE", "Fallout4.exe"
            )

            # Create weak reference to result
            try:
                weak_refs.append(weakref.ref(segments))
            except TypeError:
                # Some types don't support weak references
                pass

            # Delete strong reference
            del segments
            del data

        # Force garbage collection
        gc.collect()
        time.sleep(0.1)

        # Check that objects were actually freed
        alive_count = sum(1 for ref in weak_refs if ref() is not None)

        # Most objects should be freed (allow a few to survive due to caching)
        assert alive_count < 10, f"Too many objects still alive: {alive_count}/100"

    def test_memory_fragmentation_handling(self):
        """Test handling of memory fragmentation with many small allocations."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        monitor = MemoryMonitor()
        monitor.start()

        parser = get_parser()
        generator = SyntheticDataGenerator()

        # Create many small allocations
        small_results = []
        for i in range(10000):
            # Very small synthetic data (< 1KB)
            tiny_log = f"Line {i}: FormID: {i:08X}"
            lines = tiny_log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(
                lines, "Buffout 4", "F4SE", "Fallout4.exe"
            )
            small_results.append(segments)

            # Delete some to create fragmentation
            if i % 3 == 0 and small_results:
                small_results.pop(random.randint(0, len(small_results) - 1))

        # Now try large allocation
        large_log = generator.generate_large_log(10)
        lines = large_log.splitlines()
        game_ver, crashgen_ver, error, large_result = parser.find_segments(
            lines, "Buffout 4", "F4SE", "Fallout4.exe"
        )

        # Should succeed without excessive memory use
        current_memory = monitor.sample()
        memory_mb = (current_memory - monitor.initial_memory) / (1024 * 1024)

        # Should use less than 200MB for this test
        assert memory_mb < 200, f"Excessive memory use with fragmentation: {memory_mb:.2f}MB"

    def test_out_of_memory_recovery(self):
        """Test recovery from near out-of-memory conditions."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        generator = SyntheticDataGenerator()

        # Try to allocate very large amount (but not enough to crash)
        try:
            # Create 100MB synthetic log
            huge_log = generator.generate_large_log(100)
            lines = huge_log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(
                lines, "Buffout 4", "F4SE", "Fallout4.exe"
            )
            del segments
            del huge_log
        except MemoryError:
            # Expected - should handle gracefully
            pass
        except Exception as e:
            # Should only get memory-related errors
            assert "memory" in str(e).lower()

        # Force cleanup
        gc.collect()
        time.sleep(0.1)

        # Should still be able to work after near-OOM
        small_log = "Test after OOM"
        lines = small_log.splitlines()
        game_ver, crashgen_ver, error, segments = parser.find_segments(
            lines, "Buffout 4", "F4SE", "Fallout4.exe"
        )
        assert segments is not None

    def test_cyclic_reference_detection(self):
        """Test that cyclic references don't cause memory leaks."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_plugin_analyzer

        monitor = MemoryMonitor()
        monitor.start()

        analyzer = get_plugin_analyzer()
        generator = SyntheticDataGenerator()

        # Create structures with potential circular references
        for i in range(100):
            # Create plugin data that references itself
            plugin_data = generator.generate_plugin_data(10)

            # Add circular reference in Python side
            plugin_data["self_ref"] = plugin_data
            plugin_data["children"] = [plugin_data] * 10

            # Process through Rust
            try:
                result = analyzer.process_plugin_data(plugin_data)
            except (AttributeError, TypeError):
                # Method might not exist or handle this data
                pass

            # Delete everything
            del plugin_data

        # Force cycle detection and cleanup
        gc.collect()

        # Check for leaks
        leak = monitor.get_leak_estimate()
        leak_mb = leak / (1024 * 1024)

        # Should handle cycles without leaking
        assert leak_mb < 20, f"Memory leak with cyclic references: {leak_mb:.2f}MB"

    def test_string_interning_efficiency(self):
        """Test that string interning works efficiently across FFI."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        monitor = MemoryMonitor()
        monitor.start()

        parser = get_parser()

        # Create many logs with repeated strings
        repeated_formid = "FE000800"
        repeated_plugin = "SyntheticPlugin.esp"

        for i in range(1000):
            # Log with many repeated strings
            log = f"""
            FormID: {repeated_formid} from {repeated_plugin}
            FormID: {repeated_formid} from {repeated_plugin}
            FormID: {repeated_formid} from {repeated_plugin}
            Error in {repeated_plugin} at FormID {repeated_formid}
            """ * 10

            lines = log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(
                lines, "Buffout 4", "F4SE", "Fallout4.exe"
            )
            del segments

        # Memory usage should be reasonable due to string interning
        current_memory = monitor.sample()
        memory_mb = (current_memory - monitor.initial_memory) / (1024 * 1024)

        # Should use less than 50MB even with many repeated strings
        assert memory_mb < 50, f"Inefficient string handling: {memory_mb:.2f}MB"

    def test_memory_cleanup_on_panic(self):
        """Test that memory is cleaned up even if Rust panics."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        monitor = MemoryMonitor()
        monitor.start()

        parser = get_parser()

        # Try to cause a panic with malformed data
        malformed_inputs = [
            "\x00" * 1000000,  # Null bytes
            "💥" * 1000000,  # Emoji spam
            "\xFF\xFE" * 500000,  # Invalid UTF-8
            "A" * 100000000,  # Extremely long single line
        ]

        for malformed in malformed_inputs:
            try:
                lines = malformed.splitlines() if isinstance(malformed, str) else [malformed]
                game_ver, crashgen_ver, error, segments = parser.find_segments(
                    lines, "Buffout 4", "F4SE", "Fallout4.exe"
                )
                del segments
            except Exception:
                # Expected - Rust might panic or return error
                pass

            # Cleanup after each attempt
            gc.collect()

        # Should recover and not leak memory
        leak = monitor.get_leak_estimate()
        leak_mb = leak / (1024 * 1024)

        # Even with panics, should not leak excessively
        assert leak_mb < 100, f"Memory leak after panics: {leak_mb:.2f}MB"

    @pytest.mark.skipif(sys.platform == "win32", reason="Process pools behave differently on Windows")
    def test_memory_isolation_across_processes(self):
        """Test that memory is properly isolated across process boundaries."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        def worker_process(size_mb):
            """Worker process that allocates memory."""
            from ClassicLib.integration.factory import get_parser
            generator = SyntheticDataGenerator()

            parser = get_parser()
            log = generator.generate_large_log(size_mb)
            lines = log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(
                lines, "Buffout 4", "F4SE", "Fallout4.exe"
            )

            # Return size of result
            return len(str(segments)) if segments else 0

        # Monitor main process memory
        monitor = MemoryMonitor()
        monitor.start()

        # Launch workers in separate processes
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(worker_process, 10)
                for _ in range(20)
            ]

            results = [f.result() for f in as_completed(futures)]

        # Main process memory should not be affected
        leak = monitor.get_leak_estimate()
        leak_mb = leak / (1024 * 1024)

        # Should have minimal impact on main process
        assert leak_mb < 10, f"Memory leak in main process: {leak_mb:.2f}MB"

    def test_memory_pressure_monitoring(self):
        """Test behavior under memory pressure with monitoring."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        generator = SyntheticDataGenerator()

        # Track memory trajectory
        tracemalloc.start()

        allocations = []
        for i in range(50):
            # Gradually increase memory pressure
            size_mb = i * 0.5
            log = generator.generate_large_log(size_mb)
            lines = log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(
                lines, "Buffout 4", "F4SE", "Fallout4.exe"
            )
            allocations.append(segments)

            # Get current memory usage
            current, peak = tracemalloc.get_traced_memory()
            current_mb = current / (1024 * 1024)

            # If using too much memory, start releasing
            if current_mb > 500:
                # Release half of allocations
                for _ in range(len(allocations) // 2):
                    if allocations:
                        allocations.pop(0)
                gc.collect()

        tracemalloc.stop()

        # Should have managed memory pressure
        assert len(allocations) > 0, "Should have kept some allocations"
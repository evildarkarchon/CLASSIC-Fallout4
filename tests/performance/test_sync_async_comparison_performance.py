"""
Real-world sync vs async comparison performance tests.

This module contains performance tests that directly compare synchronous and
asynchronous processing patterns using real crash log data.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import time
from itertools import starmap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ClassicLib.scanning.logs.async_util import load_crash_logs_async

pytestmark = pytest.mark.performance


@pytest.mark.slow
@pytest.mark.asyncio
class TestRealWorldSyncAsyncComparison:
    """Real-world sync vs async performance comparison tests."""

    async def test_sync_vs_async_real_world_comparison(self, mock_yamldata: MagicMock, small_performance_test_logs: list[Path]) -> None:
        """Direct comparison of sync vs async processing with test crash logs.

        This test uses sample crash logs from test_data directory to ensure
        test isolation and reproducibility.
        """
        # Use fixture-provided crash log files (20 files)
        crash_log_files: list[Path] = small_performance_test_logs

        if len(crash_log_files) < 5:
            pytest.skip("Not enough crash log files for comparison - need at least 5 crash logs")

        print("\n=== SYNC VS ASYNC REAL-WORLD COMPARISON ===")
        print(f"Testing with {len(crash_log_files)} crash logs")

        # Test 1: File Loading Performance
        print("\n1. FILE LOADING COMPARISON:")

        # Sync loading
        sync_load_start = time.perf_counter()
        sync_data = {}
        for log_file in crash_log_files:
            sync_data[log_file.name] = log_file.read_text(errors="ignore").splitlines()
        sync_load_time = time.perf_counter() - sync_load_start

        # Async loading
        async_load_start = time.perf_counter()
        async_data = await load_crash_logs_async(crash_log_files)
        async_load_time = time.perf_counter() - async_load_start

        print(f"  Sync:  {sync_load_time:.4f}s")
        print(f"  Async: {async_load_time:.4f}s")
        print(f"  Speedup: {sync_load_time / async_load_time:.2f}x" if async_load_time > 0 else "N/A")

        # Test 2: Concurrent Processing
        print("\n2. CONCURRENT PROCESSING COMPARISON:")

        # Sequential processing
        seq_start = time.perf_counter()
        seq_results = []
        for _name, lines in sync_data.items():
            # Simulate processing
            result = len([l for l in lines if "Form ID:" in l or "EXCEPTION_" in l])
            seq_results.append(result)
            await asyncio.sleep(0.001)  # Simulate processing delay
        seq_time = time.perf_counter() - seq_start

        # Concurrent processing
        async def process_log(name: str, lines: list[str]) -> int:
            await asyncio.sleep(0.001)  # Simulate processing delay
            return len([l for l in lines if "Form ID:" in l or "EXCEPTION_" in l])

        conc_start = time.perf_counter()
        tasks = list(starmap(process_log, async_data.items()))
        conc_results = await asyncio.gather(*tasks)
        conc_time = time.perf_counter() - conc_start

        print(f"  Sequential: {seq_time:.4f}s")
        print(f"  Concurrent: {conc_time:.4f}s")
        print(f"  Speedup: {seq_time / conc_time:.2f}x" if conc_time > 0 else "N/A")

        # Test 3: Memory Efficiency
        print("\n3. MEMORY EFFICIENCY:")

        total_size = sum(len("".join(lines)) for lines in sync_data.values())
        print(f"  Total data processed: {total_size:,} bytes")
        print(f"  Files processed: {len(crash_log_files)}")
        print(f"  Avg file size: {total_size / len(crash_log_files):,.0f} bytes")

        # Assertions
        assert len(sync_data) == len(async_data)
        assert len(seq_results) == len(conc_results)
        assert async_load_time > 0
        assert conc_time > 0

        # Performance expectations
        # Async should generally be faster for I/O bound operations
        if len(crash_log_files) >= 10:
            # With enough files, async should show benefits
            assert conc_time <= seq_time * 1.1  # Allow 10% variance


if __name__ == "__main__":
    pytest.main([__file__])

"""
Memory usage performance baseline tests for async operations.

This module establishes baseline performance metrics specifically for memory consumption,
including sync vs async memory patterns and resource usage monitoring.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import gc
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.AsyncBridge import AsyncBridge

from ClassicLib.ScanLog.AsyncFileIO import load_crash_logs_async_optimized

pytestmark = pytest.mark.performance


def create_large_crash_log_set(tmp_path: Path, log_count: int) -> list[Path]:
    """Create a larger set of crash logs for performance testing."""
    crash_logs_dir: Path = tmp_path / "Performance_Test_Logs"
    crash_logs_dir.mkdir(parents=True, exist_ok=True)

    # Realistic crash log content with various sizes
    base_content: str = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]

PROBABLE CALL STACK:
"""

    files: list[Path] = []
    for i in range(log_count):
        log_file: Path = crash_logs_dir / f"crash-perf-test-{i:03d}.log"

        # Vary content size to simulate real-world scenarios
        callstack_lines: int = min(50 + (i % 20), 100)  # 50-100 lines of callstack
        content_parts: list[str] = [base_content]

        for j in range(callstack_lines):
            content_parts.append(f"\t[{j:2d}] 0x7FF6EF{j:06X} Fallout4.exe+{j:07X} -> {j * 1000 + 555}+0x{j:02X}\n")
            if j % 5 == 0:  # Add FormIDs periodically
                content_parts.append(f"\tForm ID: 0x{j:08X}\n")

        # Add modules and plugins
        content_parts.extend([
            "\nMODULES:\n",
            f"\tperformance_module_{i}.dll\n",
            f"\ttest_module_{i % 10}.dll\n",
            "\nF4SE PLUGINS:\n",
            f"\tf4se_perf_plugin_{i}.dll\n",
            "\nPLUGINS:\n",
            "\t[00] Fallout4.esm\n",
            "\t[01] DLCRobot.esm\n",
            f"\t[{i:02d}] PerfTestPlugin_{i}.esp\n",
        ])

        log_file.write_text("".join(content_parts))
        files.append(log_file)

    return files


class TestAsyncPerformanceMemory:
    """Performance baseline tests for memory usage patterns."""

    @pytest.mark.slow
    def test_memory_usage_baseline(self, tmp_path: Path, message_handler, async_bridge) -> None:
        """Baseline: Memory usage patterns for async operations."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process()
        test_files = create_large_crash_log_set(tmp_path, 30)

        # Measure sync memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        sync_data = {}
        for f in test_files:
            sync_data[f.name] = f.read_text()

        sync_peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        sync_memory_increase = sync_peak_memory - initial_memory

        # Clear sync data
        sync_data.clear()
        gc.collect()

        # Measure async memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        async def async_load():
            return await load_crash_logs_async_optimized(test_files)

        bridge = AsyncBridge.get_instance()
        async_data = bridge.run_async(async_load())

        async_peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        async_memory_increase = async_peak_memory - initial_memory

        print("\n=== MEMORY USAGE BASELINE (30 files) ===")
        print(f"Sync memory increase:  {sync_memory_increase:.1f} MB")
        print(f"Async memory increase: {async_memory_increase:.1f} MB")
        if sync_memory_increase > 0:
            efficiency = (1 - async_memory_increase / sync_memory_increase) * 100
            print(f"Memory efficiency:     {efficiency:+.1f}%")

        # Both should use reasonable memory
        assert sync_memory_increase < 100  # Less than 100MB for 30 files
        assert async_memory_increase < 100


if __name__ == "__main__":
    pytest.main([__file__])

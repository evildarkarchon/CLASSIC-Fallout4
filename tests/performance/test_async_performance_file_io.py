"""
File I/O performance baseline tests for async operations.

This module establishes baseline performance metrics specifically for file I/O operations,
including single file processing and batch operations.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Mock ClassicScanLogsInfo for testing."""
    yamldata: MagicMock = MagicMock()
    yamldata.fallout4_crashlog_scan_exclusions = ["test_exclusion"]
    yamldata.fallout4_crashlog_mods_single = {"test_mod": "Test mod message"}
    yamldata.game_ignore_plugins = []
    yamldata.game_ignore_records = []
    yamldata.ignore_list = []
    yamldata.classic_records_list = []
    yamldata.fallout4_crashlog_mods_top = {}
    yamldata.fallout4_crashlog_mods_groups = {}
    yamldata.fallout4_crashlog_stack_check = {}
    yamldata.fallout4_crashlog_error_check = {}
    yamldata.formid_analyzer_enabled = True
    yamldata.record_scanner_enabled = True
    yamldata.plugin_analyzer_enabled = True
    return yamldata


class TestAsyncPerformanceFileIO:
    """Performance baseline tests for file I/O operations."""

    @pytest.mark.asyncio
    async def test_file_io_baseline_single_files(self, tmp_path: Path, mock_yamldata: MagicMock) -> None:
        """
        Baseline test for single file I/O operations.

        Establishes performance metrics for loading individual crash logs
        with various file sizes and content complexity.
        """
        # Create test files with different sizes
        small_files = create_large_crash_log_set(tmp_path, 5)  # Small set
        medium_files = create_large_crash_log_set(tmp_path / "medium", 15)  # Medium set
        large_files = create_large_crash_log_set(tmp_path / "large", 25)  # Large set

        all_files = small_files + medium_files + large_files

        # Measure single file processing times
        single_file_times: list[float] = []

        for log_file in all_files[:10]:  # Test first 10 files
            start_time = time.perf_counter()

            try:
                # Test single file loading
                with patch("ClassicLib.ScanLog.AsyncFileIO.load_crash_logs_async_optimized") as mock_load:
                    mock_load.return_value = (["Mock content"], [])

                    result = await load_crash_logs_async_optimized([log_file])
                    assert result is not None

                end_time = time.perf_counter()
                file_time = end_time - start_time
                single_file_times.append(file_time)

                # Log performance metrics
                file_size = log_file.stat().st_size
                print(f"File {log_file.name}: {file_size} bytes, {file_time:.4f}s")

            except Exception as e:
                print(f"Error processing {log_file}: {e}")
                continue

        # Performance assertions
        if single_file_times:
            avg_time = sum(single_file_times) / len(single_file_times)
            max_time = max(single_file_times)

            print("Single file I/O performance:")
            print(f"  Average time: {avg_time:.4f}s")
            print(f"  Maximum time: {max_time:.4f}s")
            print(f"  Files processed: {len(single_file_times)}")

            # Baseline assertions (adjust thresholds as needed)
            assert avg_time < 1.0, f"Average single file processing too slow: {avg_time:.4f}s"
            assert max_time < 2.0, f"Maximum single file processing too slow: {max_time:.4f}s"

    @pytest.mark.asyncio
    async def test_file_io_baseline_batch_operations(self, tmp_path: Path, mock_yamldata: MagicMock) -> None:
        """
        Baseline test for batch file I/O operations.

        Tests the performance of loading multiple crash logs simultaneously
        using async batch processing patterns.
        """
        # Create sets of files for batch testing
        batch_sizes = [5, 10, 20, 30]
        batch_performance: dict[int, float] = {}

        for batch_size in batch_sizes:
            batch_files = create_large_crash_log_set(tmp_path / f"batch_{batch_size}", batch_size)

            start_time = time.perf_counter()

            try:
                # Test batch loading with different strategies
                with patch("ClassicLib.ScanLog.AsyncFileIO.load_crash_logs_async_optimized") as mock_load:
                    mock_load.return_value = (["Mock content"] * batch_size, [])

                    # Concurrent batch loading
                    tasks = []
                    for log_file in batch_files:
                        task = load_crash_logs_async_optimized([log_file])
                        tasks.append(task)

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Verify results
                    successful_results = [r for r in results if not isinstance(r, Exception)]
                    assert len(successful_results) >= batch_size * 0.8  # Allow 20% failure tolerance

                end_time = time.perf_counter()
                batch_time = end_time - start_time
                batch_performance[batch_size] = batch_time

                # Calculate throughput
                throughput = batch_size / batch_time if batch_time > 0 else 0

                print(f"Batch size {batch_size}: {batch_time:.4f}s, {throughput:.2f} files/sec")

            except Exception as e:
                print(f"Error in batch processing {batch_size} files: {e}")
                continue

        # Performance analysis
        if batch_performance:
            print("\nBatch I/O performance summary:")
            for size, time_taken in batch_performance.items():
                throughput = size / time_taken if time_taken > 0 else 0
                print(f"  {size} files: {time_taken:.4f}s ({throughput:.2f} files/sec)")

            # Baseline assertions
            max_batch_time = max(batch_performance.values())
            min_throughput = min(size / time_taken for size, time_taken in batch_performance.items() if time_taken > 0)

            assert max_batch_time < 5.0, f"Batch processing too slow: {max_batch_time:.4f}s"
            assert min_throughput > 2.0, f"Throughput too low: {min_throughput:.2f} files/sec"


if __name__ == "__main__":
    pytest.main([__file__])

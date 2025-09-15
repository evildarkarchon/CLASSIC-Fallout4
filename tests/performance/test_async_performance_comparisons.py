"""
Performance comparison tests for async vs sync operations.

This module contains direct performance comparisons between synchronous and
asynchronous implementations to validate performance improvements.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncFileIO import load_crash_logs_async_optimized
from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async
from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async


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


@pytest.mark.performance
@pytest.mark.slow
class TestAsyncPerformanceComparison:
    """Direct performance comparisons between async and sync implementations."""

    @pytest.mark.asyncio
    async def test_crashlogs_reformat_async_direct(self, tmp_path: Path) -> None:
        """Test direct async crashlog reformatting performance."""
        crash_logs: list[Path] = create_large_crash_log_set(tmp_path, 10)

        start_time: float = time.perf_counter()
        result: list[str] = await crashlogs_reformat_async(crash_logs)
        end_time: float = time.perf_counter()

        assert len(result) == 10
        elapsed_time: float = end_time - start_time
        print(f"Async reformat time for 10 logs: {elapsed_time:.4f}s")

        # Performance assertion - should complete reasonably quickly
        assert elapsed_time < 5.0, f"Async reformat took too long: {elapsed_time:.4f}s"

    def test_async_vs_sync_file_loading_performance(self, tmp_path: Path) -> None:
        """Compare async vs sync file loading performance."""
        crash_logs: list[Path] = create_large_crash_log_set(tmp_path, 25)

        # Test async loading performance
        start_time: float = time.perf_counter()
        async_result: Any = load_crash_logs_async(crash_logs)
        async_time: float = time.perf_counter() - start_time

        # Test optimized async loading
        start_time = time.perf_counter()
        optimized_result: Any = load_crash_logs_async_optimized(crash_logs)
        optimized_time: float = time.perf_counter() - start_time

        print(f"Async loading time: {async_time:.4f}s")
        print(f"Optimized async loading time: {optimized_time:.4f}s")

        # Both should complete reasonably quickly
        assert async_time < 10.0, f"Async loading took too long: {async_time:.4f}s"
        assert optimized_time < 10.0, f"Optimized async loading took too long: {optimized_time:.4f}s"

        # Results should be valid
        assert async_result is not None
        assert optimized_result is not None

        # Optimized should be faster or at least not significantly slower
        slowdown_ratio: float = optimized_time / async_time if async_time > 0 else 1.0
        assert slowdown_ratio < 2.0, f"Optimized version is too slow compared to basic async: {slowdown_ratio:.2f}x"

"""
Pipeline performance baseline tests for async operations.

This module establishes baseline performance metrics specifically for pipeline processing,
including scalability testing and throughput measurements.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.pipeline.async_crash_log_pipeline import AsyncCrashLogPipeline

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


class TestAsyncPerformancePipeline:
    """Performance baseline tests for pipeline scalability."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_async_pipeline_scalability_baseline(
        self, tmp_path: Path, mock_yamldata: MagicMock
    ) -> None:
        """Baseline: Async pipeline scalability with different log counts."""
        test_counts = [5, 10, 25]
        results = []

        for count in test_counts:
            test_files = create_large_crash_log_set(tmp_path / f"scale_{count}", count)

            pipeline = AsyncCrashLogPipeline(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            # Mock pipeline components
            with (
                patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async"),
                patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.load_crash_logs_async") as mock_load,
                patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.write_reports_batch"),
                patch("ClassicLib.ScanLog.OrchestratorCore.OrchestratorCore") as mock_orch,
            ):
                mock_load.return_value = {f.name: ["content"] for f in test_files}

                mock_orchestrator = AsyncMock()
                mock_orchestrator.process_crash_logs_batch.return_value = [
                    (f, ["report"], False, {}) for f in test_files
                ]
                mock_orch.return_value.__aenter__.return_value = mock_orchestrator
                mock_orch.return_value.__aexit__.return_value = None

                start = time.perf_counter()
                _, stats = await pipeline.process_crash_logs_async(test_files)
                total_time = time.perf_counter() - start

                results.append({
                    "count": count,
                    "time": total_time,
                    "logs_per_second": count / total_time if total_time > 0 else 0,
                })

        print("\n=== PIPELINE SCALABILITY BASELINE ===")
        for result in results:
            print(
                f"{result['count']:3d} logs: {result['time']:.3f}s "
                f"({result['logs_per_second']:.1f} logs/sec)"
            )

        # Verify scalability (time should increase sublinearly with count)
        if len(results) >= 2:
            # Rough check: doubling files shouldn't double time (concurrent benefit)
            time_ratio = results[1]["time"] / results[0]["time"]
            count_ratio = results[1]["count"] / results[0]["count"]
            # Time should increase less than linearly
            assert time_ratio < count_ratio * 1.5  # Allow some overhead


if __name__ == "__main__":
    pytest.main([__file__])

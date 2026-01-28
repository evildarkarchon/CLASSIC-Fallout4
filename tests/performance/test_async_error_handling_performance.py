"""
Error handling performance baseline tests for async operations.

This module establishes baseline performance metrics specifically for error handling patterns,
including the performance impact of various error scenarios and recovery mechanisms.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import time
from pathlib import Path

import pytest

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.scanning.logs.async_util import load_crash_logs_async

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


class TestAsyncPerformanceErrorHandling:
    """Performance baseline tests for error handling patterns."""

    @pytest.mark.slow
    def test_error_handling_performance_baseline(self, tmp_path: Path, message_handler, async_bridge) -> None:
        """Baseline: Performance impact of error handling.

        Tests that adding problematic files (empty, malformed) to a batch of valid
        crash logs doesn't cause excessive slowdown compared to processing only valid files.
        """
        # Mix of valid and problematic files
        valid_files = create_large_crash_log_set(tmp_path / "valid", 10)

        # Create some problematic files (similar size to valid files, not massive)
        problem_dir = tmp_path / "problems"
        problem_dir.mkdir()

        # Empty file - tests empty input handling
        empty_file = problem_dir / "empty.log"
        empty_file.write_text("")

        # Malformed file - tests parsing error handling (similar size to valid files)
        malformed_file = problem_dir / "malformed.log"
        malformed_content = "Not a valid crash log format\n" * 100  # ~3KB
        malformed_file.write_text(malformed_content)

        # Note: We don't include massive files here because that tests I/O throughput,
        # not error handling overhead. The goal is to test error handling paths.
        all_files = valid_files + [empty_file, malformed_file]

        # Time with error handling
        async def with_error_handling():
            start = time.perf_counter()
            try:
                result = await load_crash_logs_async(all_files)
            except Exception:
                result = {}
            return time.perf_counter() - start, result

        bridge = AsyncBridge.get_instance()
        time_with_errors, result = bridge.run_async(with_error_handling())

        # Time without problematic files
        async def without_errors():
            start = time.perf_counter()
            result = await load_crash_logs_async(valid_files)
            return time.perf_counter() - start, result

        time_without_errors, _ = bridge.run_async(without_errors())

        print("\n=== ERROR HANDLING PERFORMANCE ===")
        print(f"With problematic files:    {time_with_errors:.4f}s")
        print(f"Without problematic files: {time_without_errors:.4f}s")
        overhead = ((time_with_errors - time_without_errors) / time_without_errors) * 100
        print(f"Error handling overhead:   {overhead:.1f}%")

        # Error handling shouldn't cause massive slowdown
        # Allow up to 8x slowdown since:
        # - We're processing 12 files vs 10 files (1.2x baseline)
        # - Error paths may involve additional validation/recovery logic
        # - File I/O timing can vary significantly on different systems
        # - Empty/malformed file handling has additional overhead
        assert time_with_errors < time_without_errors * 8, (
            f"Error handling overhead too high: {time_with_errors:.4f}s vs {time_without_errors:.4f}s (expected < 8x)"
        )


if __name__ == "__main__":
    pytest.main([__file__])

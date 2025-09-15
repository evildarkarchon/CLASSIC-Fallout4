"""
Real-world performance baseline management utilities.

This module contains utilities for saving and managing performance baseline
data for future regression testing and performance tracking.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import json
import time
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.performance


class TestRealWorldBaselineManagement:
    """Utilities for managing performance baselines."""

    def save_performance_baseline(
        self,
        crash_log_files: list[Path],
        total_size: int,
        sync_stats: dict[str, float],
        async_stats: dict[str, float],
        full_test_time: float,
        comparison: dict[str, Any],
    ) -> None:
        """Save performance baseline data for future comparisons."""
        baseline_data: dict[str, Any] = {
            "test_type": "real_world_crash_logs",
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "log_count": len(crash_log_files),
            "total_size_bytes": total_size,
            "avg_file_size": total_size / len(crash_log_files),
            "sync_performance": sync_stats,
            "async_performance": {
                **async_stats,
                "total_time": full_test_time,
                "throughput_logs_per_sec": len(crash_log_files) / full_test_time,
            },
            "comparison": comparison,
        }

        # Save to project root
        project_root: Path = Path(__file__).parent.parent.parent
        baseline_dir: Path = project_root / "performance_baselines"
        baseline_dir.mkdir(exist_ok=True)

        timestamp: str = time.strftime("%Y%m%d_%H%M%S")
        baseline_file: Path = baseline_dir / f"real_world_baseline_{timestamp}.json"
        latest_file: Path = baseline_dir / "real_world_baseline_latest.json"

        baseline_file.write_text(json.dumps(baseline_data, indent=2))
        latest_file.write_text(json.dumps(baseline_data, indent=2))

        print(f"\nPerformance baseline saved to: {baseline_file}")

    def test_baseline_file_structure(self, tmp_path: Path) -> None:
        """Test the baseline file saving functionality."""
        # Create mock data
        mock_files = [tmp_path / f"test_{i}.log" for i in range(3)]
        for f in mock_files:
            f.write_text(f"Mock crash log content {f.name}")

        mock_sync_stats = {"total_time": 1.5, "logs_per_second": 2.0}
        mock_async_stats = {"total_time": 1.0, "logs_per_second": 3.0}
        mock_comparison = {"speedup_factor": 1.5, "improvement_percent": 33.3}

        # Test saving baseline
        self.save_performance_baseline(
            crash_log_files=mock_files,
            total_size=sum(f.stat().st_size for f in mock_files),
            sync_stats=mock_sync_stats,
            async_stats=mock_async_stats,
            full_test_time=1.0,
            comparison=mock_comparison,
        )

        # Verify baseline directory exists
        project_root = Path(__file__).parent.parent.parent
        baseline_dir = project_root / "performance_baselines"
        assert baseline_dir.exists()

        # Verify latest file exists and has correct structure
        latest_file = baseline_dir / "real_world_baseline_latest.json"
        assert latest_file.exists()

        baseline_data = json.loads(latest_file.read_text())
        assert baseline_data["test_type"] == "real_world_crash_logs"
        assert baseline_data["log_count"] == 3
        assert "test_date" in baseline_data
        assert "sync_performance" in baseline_data
        assert "async_performance" in baseline_data
        assert "comparison" in baseline_data


if __name__ == "__main__":
    pytest.main([__file__])

"""
Stress test configuration and domain-specific fixtures.

This file provides the autouse cleanup fixture for stress tests and shared
helper classes for comprehensive stress testing.

Common stress fixtures (MemoryTracker, ConcurrencyTestHelper, StressDataGenerator,
PerformanceProfiler, etc.) are imported from tests/fixtures/stress_fixtures.py
via the root conftest.py.

Available fixtures from root conftest.py:
- memory_tracker, fresh_memory_tracker (from stress_fixtures)
- concurrency_helper (from stress_fixtures)
- stress_data_generator (from stress_fixtures)
- performance_profiler (from stress_fixtures)
- large_crash_log, massive_plugin_list, formid_dataset (from stress_fixtures)
- temp_crash_logs_dir (from stress_fixtures)
- failing_database_pool, resource_exhaustion_simulator (from stress_fixtures)
"""

import gc
import random
import threading
import time
from typing import Any

import psutil
import pytest


class StressTestMetrics:
    """Track metrics during stress tests."""

    def __init__(self):
        self.start_time = time.time()
        self.operations_completed = 0
        self.errors_encountered = []
        self.peak_memory_mb = 0
        self.thread_counts = []
        self.response_times = []
        self.process = psutil.Process()

    def record_operation(self, duration: float):
        """Record a completed operation."""
        self.operations_completed += 1
        self.response_times.append(duration)

    def record_error(self, error: Exception):
        """Record an error."""
        self.errors_encountered.append(str(error))

    def update_memory(self):
        """Update peak memory usage."""
        current_mb = self.process.memory_info().rss / (1024 * 1024)
        self.peak_memory_mb = max(self.peak_memory_mb, current_mb)

    def update_threads(self):
        """Update thread count."""
        self.thread_counts.append(threading.active_count())

    def get_summary(self) -> dict[str, Any]:
        """Get test summary."""
        elapsed = time.time() - self.start_time
        return {
            "duration": elapsed,
            "operations": self.operations_completed,
            "ops_per_second": self.operations_completed / elapsed if elapsed > 0 else 0,
            "errors": len(self.errors_encountered),
            "error_rate": len(self.errors_encountered) / self.operations_completed if self.operations_completed > 0 else 0,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "max_threads": max(self.thread_counts) if self.thread_counts else 0,
        }


class SyntheticWorkloadGenerator:
    """Generate synthetic workloads for stress testing."""

    @staticmethod
    def generate_typical_crash_log() -> str:
        """Generate a typical 1-2MB crash log."""
        lines = []
        lines.append("Fallout 4 v1.10.163")
        lines.append("Buffout 4 v1.28.6")
        lines.append("")
        lines.append('Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512')
        lines.append("")

        # Add plugins (typical mod setup has 50-150 plugins)
        lines.append("PLUGINS:")
        for i in range(100):
            if i < 10:
                lines.append(f"\t[{i:02X}] Master_{i}.esm")
            elif i < 50:
                lines.append(f"\t[{i:02X}] Mod_{i}.esp")
            else:
                lines.append(f"\t[FE:{i - 50:03X}] Light_{i}.esl")

        # Add stack trace
        lines.append("\nSTACK TRACE:")
        for i in range(50):
            addr = 0x7FF600000000 + random.randint(0, 0xFFFFFFFF)
            lines.append(f"\t[{i}] 0x{addr:016X} module.dll+{random.randint(0x1000, 0xFFFFFF):07X}")

        # Add FormIDs
        lines.append("\nFORMIDS:")
        for i in range(200):
            plugin_index = random.randint(0x00, 0xFE)
            local_id = random.randint(0x000001, 0xFFFFFF)
            lines.append(f"FormID: {plugin_index:02X}{local_id:06X}")

        # Pad to ~1.5MB (typical size)
        content = "\n".join(lines)
        target_size = 1.5 * 1024 * 1024
        padding_needed = int(target_size - len(content))
        if padding_needed > 0:
            padding = "x" * (padding_needed // 80) + "\n"
            content += padding

        return content

    @staticmethod
    def generate_user_action_sequence() -> list[str]:
        """Generate a sequence of typical user actions."""
        actions = []
        action_types = [
            "scan_log",
            "analyze_formids",
            "check_plugins",
            "generate_report",
            "save_settings",
            "load_settings",
            "refresh_ui",
            "search_mods",
            "validate_game",
        ]

        # Typical user session has 10-50 actions
        for _ in range(random.randint(10, 50)):
            actions.append(random.choice(action_types))

        return actions


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test to prevent pollution."""
    yield

    # Force garbage collection
    gc.collect()

    # Clear config/yaml caches if available
    try:
        import classic_config

        if hasattr(classic_config, "clear_yaml_cache"):
            classic_config.clear_yaml_cache()
    except ImportError:
        pass

    # Clear registry caches if available
    try:
        import classic_registry

        if hasattr(classic_registry, "clear_all"):
            classic_registry.clear_all()
    except ImportError:
        pass

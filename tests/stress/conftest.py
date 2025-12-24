"""
Stress test configuration and domain-specific fixtures.

This file provides the autouse cleanup fixture for stress tests.
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

import pytest


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

"""
Shared fixtures and utilities for stress/performance tests.

This module provides common utilities for memory monitoring and performance
measurement across stress test files.
"""

import gc
import os
from contextlib import contextmanager

import psutil
import pytest


@contextmanager
def memory_monitor():
    """
    Context manager to monitor memory usage during test execution.

    Yields memory statistics before and after the test block,
    allowing detection of memory leaks and excessive usage.
    """
    process = psutil.Process(os.getpid())

    # Force garbage collection before measurement
    gc.collect()
    initial_memory = process.memory_info()
    initial_rss = initial_memory.rss
    initial_vms = initial_memory.vms

    memory_stats = {
        "initial_rss": initial_rss,
        "initial_vms": initial_vms,
        "peak_rss": initial_rss,
        "peak_vms": initial_vms,
        "samples": [],
    }

    try:
        yield memory_stats
    finally:
        # Final measurement
        gc.collect()
        final_memory = process.memory_info()
        final_rss = final_memory.rss
        final_vms = final_memory.vms

        memory_stats.update({
            "final_rss": final_rss,
            "final_vms": final_vms,
            "rss_growth": final_rss - initial_rss,
            "vms_growth": final_vms - initial_vms,
            "rss_growth_mb": (final_rss - initial_rss) / 1024 / 1024,
            "vms_growth_mb": (final_vms - initial_vms) / 1024 / 1024,
        })


@pytest.fixture
def memory_monitor_fixture():
    """Fixture wrapper for memory_monitor context manager."""
    return memory_monitor

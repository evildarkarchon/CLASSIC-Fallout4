"""GIL release verification test fixtures.

This module provides fixtures for testing that Rust FFI operations properly
release the Python GIL, allowing concurrent Python threads to make progress.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Iterator

import pytest


@pytest.fixture
def thread_pool() -> Iterator[ThreadPoolExecutor]:
    """Provide a thread pool for concurrent tests.

    Uses 4 workers by default to test concurrency without overwhelming
    the system.

    Yields:
        ThreadPoolExecutor: A thread pool for submitting concurrent tasks.
    """
    with ThreadPoolExecutor(max_workers=4) as pool:
        yield pool


@pytest.fixture
def large_test_data() -> list[str]:
    """Generate test data large enough to take >1ms to process.

    Returns:
        list[str]: 10,000 lines of simulated crash log content.
    """
    return [f"Test log line {i} with some content for processing" for i in range(10000)]


@pytest.fixture
def yaml_test_content() -> str:
    """Generate YAML content large enough to take >1ms to parse.

    Returns:
        str: YAML content with 5,000 key-value pairs.
    """
    return "\n".join(f"key_{i}: value_{i}" for i in range(5000))


@pytest.fixture
def plugin_test_data() -> dict[str, str]:
    """Generate plugin dictionary for testing.

    Returns:
        dict[str, str]: Dictionary mapping plugin names to load order IDs.
    """
    return {f"Plugin{i}.esp": f"{i:02X}" for i in range(200)}

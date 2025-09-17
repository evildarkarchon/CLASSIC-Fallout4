"""
Test fixtures for version string cache isolation.

These fixtures ensure proper cleanup of LRU caches in version utilities
to prevent test pollution from cached results.
"""

import pytest

from ClassicLib.Utils.version_utils import crashgen_version_gen


@pytest.fixture(autouse=True)
def clean_version_caches():
    """
    Automatically clear version string caches between tests.

    This fixture ensures that cached version parsing results don't leak
    between tests, which could cause false positives or negatives in tests
    that depend on version parsing behavior.
    """
    # Clear the LRU cache before test
    crashgen_version_gen.cache_clear()

    yield

    # Clear the cache after test
    crashgen_version_gen.cache_clear()


@pytest.fixture
def verify_version_cache_empty():
    """
    Fixture to verify that version caches are empty.

    Use this in tests that need to ensure they're starting with no cached values.
    """
    cache_info = crashgen_version_gen.cache_info()
    assert cache_info.hits == 0, f"Version cache not empty: {cache_info.hits} hits"
    assert cache_info.misses == 0, f"Version cache not empty: {cache_info.misses} misses"
    assert cache_info.currsize == 0, f"Version cache not empty: size {cache_info.currsize}"

    yield


@pytest.fixture
def mock_version_parsing():
    """
    Mock version parsing to control version behavior in tests.

    This fixture replaces the actual version parsing with a controlled mock,
    useful for testing components that depend on version parsing without
    actually parsing version strings.
    """
    from unittest.mock import patch
    from packaging.version import Version

    def mock_crashgen_version(input_string: str) -> Version:
        """Mock version parser that returns predictable versions."""
        if "1.10.163" in input_string:
            return Version("1.10.163.0")
        elif "1.28.6" in input_string:
            return Version("1.28.6")
        elif "1.2.72" in input_string:
            return Version("1.2.72")
        else:
            return Version("0.0.0")

    with patch('ClassicLib.Utils.version_utils.crashgen_version_gen', side_effect=mock_crashgen_version):
        yield mock_crashgen_version


@pytest.fixture
def track_version_cache_usage():
    """
    Fixture to track version cache usage during a test.

    Returns a function that can be called to get current cache statistics.
    """

    def get_cache_stats():
        """Get current cache statistics."""
        info = crashgen_version_gen.cache_info()
        return {
            'hits': info.hits,
            'misses': info.misses,
            'size': info.currsize,
            'maxsize': info.maxsize,
            'hit_rate': info.hits / (info.hits + info.misses) if (info.hits + info.misses) > 0 else 0
        }

    # Clear cache to start fresh
    crashgen_version_gen.cache_clear()

    yield get_cache_stats


@pytest.fixture
def populated_version_cache():
    """
    Provide a pre-populated version cache for testing cache behavior.

    This fixture pre-populates the cache with common version strings
    to test behavior when the cache already contains entries.
    """
    # Clear cache first
    crashgen_version_gen.cache_clear()

    # Pre-populate with common versions
    common_versions = [
        "1.10.163.0",
        "1.28.6",
        "1.2.72",
        "v1.28.6",
        "1.10.163",
    ]

    for version_str in common_versions:
        crashgen_version_gen(version_str)

    yield common_versions

    # Clear cache after test
    crashgen_version_gen.cache_clear()

"""
Memory performance and leak detection tests for Rust components.

This module provides comprehensive memory testing to validate that Rust components
use memory efficiently and don't introduce memory leaks during processing. Tests
monitor memory usage patterns, detect leaks, and ensure memory efficiency in both
sequential and concurrent processing scenarios.

Key Testing Areas:
- Memory stability during repeated processing
- Memory leak detection
- Memory efficiency comparisons
- Concurrent processing memory usage
- Peak memory usage validation
"""
# ruff: noqa: ANN201, ANN001, ARG001, PLR6301

import gc
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import Mock

import psutil
import pytest

# Skip entire module if Rust extensions not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

# Import core components
from ClassicLib.integration.factory import (
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
)
from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer as RustFormIDAnalyzer
from ClassicLib.integration.rust.plugin_rust import RustPluginAnalyzer
from ClassicLib.integration.status import (
    is_rust_accelerated,
)
from tests.fixtures.stress_fixtures import memory_monitor

logger = logging.getLogger(__name__)


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.performance
class TestMemoryPerformance:
    """
    Memory performance and leak detection tests.

    These tests validate that Rust components use memory efficiently
    and don't introduce memory leaks during processing.
    """

    @pytest.fixture
    def large_test_data(self) -> list[str]:
        """Generate large test data for memory testing."""
        data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            "PROBABLE CALL STACK:",
        ]

        # Generate many FormID entries
        data.extend(f"\t[{i}] 0x7FF66DF{i:06X} -> FormID: 0x{i:08X}" for i in range(2000))

        data.extend(("", "PLUGINS:"))

        # Generate many plugins
        data.extend(f"\t[{i:02X}] LargePlugin{i:04d}.esp" for i in range(300))

        return data

    def test_memory_usage_stability(self, large_test_data, mock_yamldata):
        """
        Test that memory usage remains stable during repeated processing.

        This test validates that Rust components don't leak memory
        when processing large amounts of data repeatedly.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"] if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for memory testing")

        with memory_monitor() as memory_stats:
            # Perform many operations to detect leaks
            iterations = 20

            for i in range(iterations):
                segments = None
                if "parser" in available_components:
                    parser = get_parser()
                    result = parser.find_segments(
                        crash_data=large_test_data,
                        crashgen_name=mock_yamldata.crashgen_name,
                        xse_acronym=mock_yamldata.xse_acronym,
                        game_root_name=mock_yamldata.game_root_name,
                    )
                    segments = result[3]

                if "formid_analyzer" in available_components:
                    formid_analyzer = RustFormIDAnalyzer(mock_yamldata, True, True)
                    callstack = segments[2] if segments and len(segments) > 2 else large_test_data
                    _ = formid_analyzer.extract_formids(callstack)

                if "plugin_analyzer" in available_components:
                    plugin_analyzer = RustPluginAnalyzer(mock_yamldata)
                    plugin_data = segments[-1] if segments else large_test_data
                    _, _, _ = plugin_analyzer.loadorder_scan_log(plugin_data)

                # Sample memory periodically
                if i % 5 == 0:
                    process = psutil.Process(os.getpid())
                    current_memory = process.memory_info()
                    memory_stats["samples"].append({"iteration": i, "rss": current_memory.rss, "vms": current_memory.vms})

                    # Update peak memory
                    memory_stats["peak_rss"] = max(memory_stats["peak_rss"], current_memory.rss)
                    memory_stats["peak_vms"] = max(memory_stats["peak_vms"], current_memory.vms)

        # Analyze memory usage
        initial_rss_mb = memory_stats["initial_rss"] / 1024 / 1024
        final_rss_mb = memory_stats["final_rss"] / 1024 / 1024
        peak_rss_mb = memory_stats["peak_rss"] / 1024 / 1024
        growth_mb = memory_stats["rss_growth_mb"]

        logger.info("Memory usage analysis:")
        logger.info(f"  Initial RSS: {initial_rss_mb:.1f} MB")
        logger.info(f"  Final RSS: {final_rss_mb:.1f} MB")
        logger.info(f"  Peak RSS: {peak_rss_mb:.1f} MB")
        logger.info(f"  Growth: {growth_mb:.1f} MB")

        # Memory growth should be minimal (< 50MB for this test)
        max_acceptable_growth = 50.0  # MB
        assert growth_mb < max_acceptable_growth, f"Excessive memory growth: {growth_mb:.1f}MB > {max_acceptable_growth}MB"

        # Peak memory should be reasonable
        max_acceptable_peak = initial_rss_mb + 100.0  # MB
        assert peak_rss_mb < max_acceptable_peak, f"Excessive peak memory: {peak_rss_mb:.1f}MB > {max_acceptable_peak:.1f}MB"

    def test_memory_efficiency_comparison(self, large_test_data, mock_yamldata):
        """
        Test memory efficiency compared to baseline.

        This test measures memory usage of Rust components and ensures
        they use memory efficiently compared to expected baselines.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available for memory efficiency testing")

        # Test FormID analyzer memory efficiency
        with memory_monitor() as memory_stats:
            formid_analyzer = RustFormIDAnalyzer(mock_yamldata, True, True)

            # Process data multiple times to check for accumulation
            for _ in range(10):
                formid_analyzer.extract_formids(large_test_data)

        growth_mb = memory_stats["rss_growth_mb"]
        formid_count = len(large_test_data)  # Approximate

        # Memory per item should be very small
        memory_per_item = (growth_mb * 1024 * 1024) / formid_count if formid_count > 0 else 0

        logger.info("Memory efficiency - FormID analyzer:")
        logger.info(f"  Growth: {growth_mb:.1f} MB for {formid_count} items")
        logger.info(f"  Per item: {memory_per_item:.2f} bytes")

        # Should use very little memory per item
        max_bytes_per_item = 100  # Very generous limit
        assert memory_per_item < max_bytes_per_item, f"Memory usage per item too high: {memory_per_item:.2f} bytes"

    def test_concurrent_memory_usage(self, large_test_data, mock_yamldata):
        """
        Test memory usage during concurrent processing.

        This test validates that concurrent processing doesn't lead to
        excessive memory usage or memory leaks.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"] if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for concurrent memory testing")

        def process_data(thread_id: int) -> dict[str, Any]:
            """Process data in a thread and return results."""
            thread_results = {}

            if "parser" in available_components:
                parser = get_parser()
                result = parser.find_segments(
                    crash_data=large_test_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name,
                )
                thread_results["segments"] = len(result[3])

            if "formid_analyzer" in available_components:
                formid_analyzer = RustFormIDAnalyzer(mock_yamldata, True, True)
                formids = formid_analyzer.extract_formids(large_test_data)
                thread_results["formids"] = len(formids)

            return thread_results

        with memory_monitor() as memory_stats:
            # Run concurrent processing
            num_threads = 4
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(process_data, i) for i in range(num_threads)]
                results = [future.result() for future in as_completed(futures)]

        growth_mb = memory_stats["rss_growth_mb"]
        peak_mb = memory_stats["peak_rss"] / 1024 / 1024
        initial_mb = memory_stats["initial_rss"] / 1024 / 1024

        logger.info(f"Concurrent memory usage ({num_threads} threads):")
        logger.info(f"  Initial: {initial_mb:.1f} MB")
        logger.info(f"  Peak: {peak_mb:.1f} MB")
        logger.info(f"  Growth: {growth_mb:.1f} MB")
        logger.info(f"  Results: {results}")

        # Peak memory shouldn't be excessive for concurrent processing
        max_acceptable_peak = initial_mb + (num_threads * 20)  # 20MB per thread max
        assert peak_mb < max_acceptable_peak, f"Concurrent peak memory too high: {peak_mb:.1f}MB > {max_acceptable_peak:.1f}MB"

        # Final growth should be minimal
        assert growth_mb < 100, f"Concurrent memory growth too high: {growth_mb:.1f}MB"


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

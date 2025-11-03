"""
Performance integration tests for Phase 6 Rust migration validation.

This module provides comprehensive performance testing and benchmarking of
Rust components in integrated scenarios. Tests measure actual performance
improvements, validate memory usage, and ensure performance targets are met
in real-world usage patterns.

Key Performance Areas:
- Actual performance improvements with real data
- Memory usage optimization and leak detection
- Concurrent processing performance
- Performance regression detection
- Scalability validation with large datasets
"""

import gc
import logging
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any
from unittest.mock import Mock

import psutil
import pytest

# Skip entire module if Rust extensions not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

# Import test infrastructure
# Import core components
from ClassicLib.integration.factory import (
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
    get_record_scanner,
)
from ClassicLib.integration.status import (
    is_rust_accelerated,
)
from tests.test_infra.performance_utils import PerformanceTimer


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
        "samples": []
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
            "vms_growth_mb": (final_vms - initial_vms) / 1024 / 1024
        })


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """
    Performance benchmarking tests for Rust components.

    These tests establish performance baselines and validate that
    Rust acceleration provides the expected performance improvements
    in various scenarios.
    """

    @pytest.fixture(scope="class")
    def performance_test_data(self) -> dict[str, list[str]]:
        """
        Generate test data of various sizes for performance testing.

        Returns a dictionary with different sized datasets to test
        performance characteristics across different data volumes.
        """
        datasets = {}

        # Small dataset (typical small crash log)
        small_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            "PROBABLE CALL STACK:",
        ]

        # Add moderate call stack
        for i in range(50):
            small_data.append(f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}")

        small_data.extend([
            "",
            "PLUGINS:",
        ])

        # Add moderate plugin list
        for i in range(50):
            small_data.append(f"\t[{i:02X}] Plugin{i:03d}.esp")

        datasets["small"] = small_data

        # Medium dataset (typical crash log)
        medium_data = small_data.copy()

        # Expand call stack
        for i in range(50, 200):
            medium_data.insert(-52, f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}")

        # Expand plugin list
        for i in range(50, 150):
            medium_data.append(f"\t[{i:02X}] Plugin{i:03d}.esp")

        datasets["medium"] = medium_data

        # Large dataset (large crash log with many mods)
        large_data = medium_data.copy()

        # Massive call stack
        for i in range(200, 1000):
            large_data.insert(-152, f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}")

        # Large plugin list
        for i in range(150, 250):
            large_data.append(f"\t[{i:02X}] Plugin{i:03d}.esp")

        # Add ESL plugins
        for i in range(50):
            large_data.append(f"\t[FE:{i:03X}] ESLPlugin{i:03d}.esl")

        datasets["large"] = large_data

        # Extra large dataset (stress test)
        xlarge_data = large_data.copy()

        # Enormous call stack
        for i in range(1000, 5000):
            xlarge_data.insert(-302, f"\t[{i}] 0x7FF66DF{i:06X} -> FormID: 0x{i:08X}")

        datasets["xlarge"] = xlarge_data

        return datasets

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Mock YAML data optimized for performance testing."""
        mock_yaml = Mock()
        mock_yaml.game_type = "fallout4"
        mock_yaml.crashgen_name = "Buffout 4"
        mock_yaml.xse_acronym = "F4SE"
        mock_yaml.game_root_name = "Fallout 4"
        mock_yaml.problematic_plugins = {}  # Keep empty for performance focus
        mock_yaml.formid_database_enabled = True
        mock_yaml.show_formid_values = True
        mock_yaml.record_patterns = ["TESForm", "BGSKeyword"]  # Minimal for performance
        return mock_yaml

    def test_parser_performance_scaling(self, performance_test_data, mock_yamldata):
        """
        Test parser performance scaling across different data sizes.

        This test validates that the Rust parser scales well with
        increasing data size and meets performance targets.
        """
        if not is_rust_accelerated("parser"):
            pytest.skip("Rust parser not available for performance testing")

        parser = get_parser()
        performance_results = {}

        # Test each data size
        for size_category, crash_data in performance_test_data.items():
            data_size_lines = len(crash_data)

            # Run multiple iterations for statistical accuracy
            times = []
            for iteration in range(5):
                with PerformanceTimer() as timer:
                    result = parser.find_segments(
                        crash_data=crash_data,
                        crashgen_name=mock_yamldata.crashgen_name,
                        xse_acronym=mock_yamldata.xse_acronym,
                        game_root_name=mock_yamldata.game_root_name
                    )
                times.append(timer.elapsed)

            # Calculate statistics
            avg_time = statistics.mean(times)
            std_time = statistics.stdev(times) if len(times) > 1 else 0
            min_time = min(times)
            max_time = max(times)

            performance_results[size_category] = {
                "data_size": data_size_lines,
                "avg_time": avg_time,
                "std_time": std_time,
                "min_time": min_time,
                "max_time": max_time,
                "lines_per_second": data_size_lines / avg_time
            }

            logging.info(f"Parser performance - {size_category} ({data_size_lines} lines): "
                        f"avg={avg_time:.3f}s, std={std_time:.3f}s, "
                        f"rate={data_size_lines/avg_time:.0f} lines/sec")

        # Validate performance targets
        targets = {
            "small": 0.01,    # 10ms for small logs
            "medium": 0.05,   # 50ms for medium logs
            "large": 0.15,    # 150ms for large logs
            "xlarge": 0.5     # 500ms for extra large logs
        }

        for size_category, target_time in targets.items():
            if size_category in performance_results:
                avg_time = performance_results[size_category]["avg_time"]
                assert avg_time < target_time, \
                    f"Parser too slow for {size_category}: {avg_time:.3f}s > {target_time}s"

        # Validate scaling characteristics (should be roughly linear)
        sizes = [(k, v["data_size"], v["avg_time"]) for k, v in performance_results.items()]
        sizes.sort(key=lambda x: x[1])  # Sort by data size

        if len(sizes) >= 2:
            # Check that performance scales reasonably
            small_rate = sizes[0][1] / sizes[0][2]  # lines per second
            large_rate = sizes[-1][1] / sizes[-1][2]  # lines per second

            # Rate should not degrade more than 50% with larger datasets
            rate_ratio = large_rate / small_rate
            assert rate_ratio > 0.5, \
                f"Performance degrades too much with size: {rate_ratio:.2f}"

    def test_formid_analyzer_performance(self, performance_test_data, mock_yamldata):
        """
        Test FormID analyzer performance across different data sizes.

        Validates that FormID extraction maintains high performance
        even with large numbers of FormIDs to process.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available for performance testing")

        analyzer = get_formid_analyzer(mock_yamldata, True, True)
        performance_results = {}

        for size_category, crash_data in performance_test_data.items():
            # Extract just the call stack portion (where FormIDs typically are)
            callstack_data = [line for line in crash_data if "FormID:" in line or "0x7FF" in line]

            if not callstack_data:
                continue

            expected_formids = len([line for line in callstack_data if "FormID:" in line])

            # Performance test
            times = []
            formid_counts = []

            for iteration in range(5):
                with PerformanceTimer() as timer:
                    formids = analyzer.extract_formids(callstack_data)
                times.append(timer.elapsed)
                formid_counts.append(len(formids))

            avg_time = statistics.mean(times)
            avg_formid_count = statistics.mean(formid_counts)
            formids_per_second = avg_formid_count / avg_time if avg_time > 0 else 0

            performance_results[size_category] = {
                "callstack_lines": len(callstack_data),
                "expected_formids": expected_formids,
                "extracted_formids": avg_formid_count,
                "avg_time": avg_time,
                "formids_per_second": formids_per_second
            }

            logging.info(f"FormID analyzer - {size_category}: "
                        f"extracted {avg_formid_count:.1f} FormIDs in {avg_time:.3f}s "
                        f"({formids_per_second:.0f} FormIDs/sec)")

        # Validate performance targets
        for size_category, results in performance_results.items():
            # Should extract FormIDs very quickly
            if results["extracted_formids"] > 10:  # Only test substantial extractions
                formids_per_second = results["formids_per_second"]
                assert formids_per_second > 1000, \
                    f"FormID extraction too slow for {size_category}: {formids_per_second:.0f} FormIDs/sec"

    def test_plugin_analyzer_performance(self, performance_test_data, mock_yamldata):
        """
        Test plugin analyzer performance with varying load order sizes.

        Validates that plugin analysis scales well with large load orders
        and maintains high throughput.
        """
        if not is_rust_accelerated("plugin_analyzer"):
            pytest.skip("Rust plugin analyzer not available for performance testing")

        analyzer = get_plugin_analyzer(mock_yamldata)
        performance_results = {}

        for size_category, crash_data in performance_test_data.items():
            # Extract plugin lines
            plugin_data = [line for line in crash_data if line.strip().startswith("[") and ".es" in line]

            if not plugin_data:
                continue

            expected_plugins = len(plugin_data)

            # Performance test
            times = []
            plugin_counts = []

            for iteration in range(5):
                with PerformanceTimer() as timer:
                    plugins_dict, limit_triggered, limit_disabled = analyzer.loadorder_scan_log(plugin_data)
                times.append(timer.elapsed)
                plugin_counts.append(len(plugins_dict))

            avg_time = statistics.mean(times)
            avg_plugin_count = statistics.mean(plugin_counts)
            plugins_per_second = avg_plugin_count / avg_time if avg_time > 0 else 0

            performance_results[size_category] = {
                "plugin_lines": len(plugin_data),
                "expected_plugins": expected_plugins,
                "parsed_plugins": avg_plugin_count,
                "avg_time": avg_time,
                "plugins_per_second": plugins_per_second
            }

            logging.info(f"Plugin analyzer - {size_category}: "
                        f"parsed {avg_plugin_count:.1f} plugins in {avg_time:.3f}s "
                        f"({plugins_per_second:.0f} plugins/sec)")

        # Validate performance targets
        for size_category, results in performance_results.items():
            if results["parsed_plugins"] > 10:  # Only test substantial load orders
                plugins_per_second = results["plugins_per_second"]
                assert plugins_per_second > 5000, \
                    f"Plugin analysis too slow for {size_category}: {plugins_per_second:.0f} plugins/sec"

    def test_integrated_pipeline_performance(self, performance_test_data, mock_yamldata):
        """
        Test performance of the complete integrated pipeline.

        This test measures the performance when all components work
        together in the complete processing pipeline.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"]
                               if is_rust_accelerated(comp)]

        if len(available_components) < 2:
            pytest.skip("Need at least 2 Rust components for integrated performance testing")

        performance_results = {}

        for size_category, crash_data in performance_test_data.items():
            # Run complete pipeline
            times = []
            results_data = []

            for iteration in range(3):  # Fewer iterations due to complexity
                with PerformanceTimer() as timer:
                    # Initialize components
                    if "parser" in available_components:
                        parser = get_parser()
                        game_version, crashgen_version, main_error, segments = parser.find_segments(
                            crash_data=crash_data,
                            crashgen_name=mock_yamldata.crashgen_name,
                            xse_acronym=mock_yamldata.xse_acronym,
                            game_root_name=mock_yamldata.game_root_name
                        )
                    else:
                        segments = [[], [], crash_data, [], [], crash_data]  # Mock segments

                    pipeline_results = {}

                    # FormID analysis
                    if "formid_analyzer" in available_components and len(segments) > 2:
                        formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)
                        formids = formid_analyzer.extract_formids(segments[2])
                        pipeline_results["formids"] = len(formids)

                    # Plugin analysis
                    if "plugin_analyzer" in available_components:
                        plugin_analyzer = get_plugin_analyzer(mock_yamldata)
                        plugins_dict, _, _ = plugin_analyzer.loadorder_scan_log(segments[-1] if segments else crash_data)
                        pipeline_results["plugins"] = len(plugins_dict)

                    # Record scanning
                    if "record_scanner" in available_components and len(segments) > 2:
                        record_scanner = get_record_scanner(mock_yamldata)
                        fragment, matches = record_scanner.scan_named_records(segments[2])
                        pipeline_results["records"] = len(matches)

                times.append(timer.elapsed)
                results_data.append(pipeline_results)

            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)

            performance_results[size_category] = {
                "data_size": len(crash_data),
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "components": len(available_components),
                "results": results_data[0] if results_data else {}
            }

            logging.info(f"Integrated pipeline - {size_category}: "
                        f"{avg_time:.3f}s avg, {len(available_components)} components, "
                        f"results: {results_data[0] if results_data else 'none'}")

        # Validate integrated performance targets
        targets = {
            "small": 0.05,    # 50ms for small logs
            "medium": 0.15,   # 150ms for medium logs
            "large": 0.5,     # 500ms for large logs
            "xlarge": 2.0     # 2s for extra large logs
        }

        for size_category, target_time in targets.items():
            if size_category in performance_results:
                avg_time = performance_results[size_category]["avg_time"]
                assert avg_time < target_time, \
                    f"Integrated pipeline too slow for {size_category}: {avg_time:.3f}s > {target_time}s"


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
        for i in range(2000):
            data.append(f"\t[{i}] 0x7FF66DF{i:06X} -> FormID: 0x{i:08X}")

        data.append("")
        data.append("PLUGINS:")

        # Generate many plugins
        for i in range(300):
            data.append(f"\t[{i:02X}] LargePlugin{i:04d}.esp")

        return data

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Mock YAML data for memory testing."""
        mock_yaml = Mock()
        mock_yaml.game_type = "fallout4"
        mock_yaml.crashgen_name = "Buffout 4"
        mock_yaml.xse_acronym = "F4SE"
        mock_yaml.game_root_name = "Fallout 4"
        mock_yaml.problematic_plugins = {}
        mock_yaml.formid_database_enabled = True
        mock_yaml.show_formid_values = True
        mock_yaml.record_patterns = ["TESForm"]
        return mock_yaml

    def test_memory_usage_stability(self, large_test_data, mock_yamldata):
        """
        Test that memory usage remains stable during repeated processing.

        This test validates that Rust components don't leak memory
        when processing large amounts of data repeatedly.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"]
                               if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for memory testing")

        with memory_monitor() as memory_stats:
            # Perform many operations to detect leaks
            iterations = 20

            for i in range(iterations):
                if "parser" in available_components:
                    parser = get_parser()
                    result = parser.find_segments(
                        crash_data=large_test_data,
                        crashgen_name=mock_yamldata.crashgen_name,
                        xse_acronym=mock_yamldata.xse_acronym,
                        game_root_name=mock_yamldata.game_root_name
                    )
                    segments = result[3]

                if "formid_analyzer" in available_components:
                    formid_analyzer = RustFormIDAnalyzer(mock_yamldata, True, True)
                    callstack = segments[2] if 'segments' in locals() and len(segments) > 2 else large_test_data
                    formids = formid_analyzer.extract_formids(callstack)

                if "plugin_analyzer" in available_components:
                    plugin_analyzer = RustPluginAnalyzer(mock_yamldata)
                    plugin_data = segments[-1] if 'segments' in locals() and segments else large_test_data
                    plugins, _, _ = plugin_analyzer.loadorder_scan_log(plugin_data)

                # Sample memory periodically
                if i % 5 == 0:
                    process = psutil.Process(os.getpid())
                    current_memory = process.memory_info()
                    memory_stats["samples"].append({
                        "iteration": i,
                        "rss": current_memory.rss,
                        "vms": current_memory.vms
                    })

                    # Update peak memory
                    memory_stats["peak_rss"] = max(memory_stats["peak_rss"], current_memory.rss)
                    memory_stats["peak_vms"] = max(memory_stats["peak_vms"], current_memory.vms)

        # Analyze memory usage
        initial_rss_mb = memory_stats["initial_rss"] / 1024 / 1024
        final_rss_mb = memory_stats["final_rss"] / 1024 / 1024
        peak_rss_mb = memory_stats["peak_rss"] / 1024 / 1024
        growth_mb = memory_stats["rss_growth_mb"]

        logging.info("Memory usage analysis:")
        logging.info(f"  Initial RSS: {initial_rss_mb:.1f} MB")
        logging.info(f"  Final RSS: {final_rss_mb:.1f} MB")
        logging.info(f"  Peak RSS: {peak_rss_mb:.1f} MB")
        logging.info(f"  Growth: {growth_mb:.1f} MB")

        # Memory growth should be minimal (< 50MB for this test)
        max_acceptable_growth = 50.0  # MB
        assert growth_mb < max_acceptable_growth, \
            f"Excessive memory growth: {growth_mb:.1f}MB > {max_acceptable_growth}MB"

        # Peak memory should be reasonable
        max_acceptable_peak = initial_rss_mb + 100.0  # MB
        assert peak_rss_mb < max_acceptable_peak, \
            f"Excessive peak memory: {peak_rss_mb:.1f}MB > {max_acceptable_peak:.1f}MB"

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
                formids = formid_analyzer.extract_formids(large_test_data)

        growth_mb = memory_stats["rss_growth_mb"]
        formid_count = len(large_test_data)  # Approximate

        # Memory per item should be very small
        memory_per_item = (growth_mb * 1024 * 1024) / formid_count if formid_count > 0 else 0

        logging.info("Memory efficiency - FormID analyzer:")
        logging.info(f"  Growth: {growth_mb:.1f} MB for {formid_count} items")
        logging.info(f"  Per item: {memory_per_item:.2f} bytes")

        # Should use very little memory per item
        max_bytes_per_item = 100  # Very generous limit
        assert memory_per_item < max_bytes_per_item, \
            f"Memory usage per item too high: {memory_per_item:.2f} bytes"

    def test_concurrent_memory_usage(self, large_test_data, mock_yamldata):
        """
        Test memory usage during concurrent processing.

        This test validates that concurrent processing doesn't lead to
        excessive memory usage or memory leaks.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"]
                               if is_rust_accelerated(comp)]

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
                    game_root_name=mock_yamldata.game_root_name
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

        logging.info(f"Concurrent memory usage ({num_threads} threads):")
        logging.info(f"  Initial: {initial_mb:.1f} MB")
        logging.info(f"  Peak: {peak_mb:.1f} MB")
        logging.info(f"  Growth: {growth_mb:.1f} MB")
        logging.info(f"  Results: {results}")

        # Peak memory shouldn't be excessive for concurrent processing
        max_acceptable_peak = initial_mb + (num_threads * 20)  # 20MB per thread max
        assert peak_mb < max_acceptable_peak, \
            f"Concurrent peak memory too high: {peak_mb:.1f}MB > {max_acceptable_peak:.1f}MB"

        # Final growth should be minimal
        assert growth_mb < 100, f"Concurrent memory growth too high: {growth_mb:.1f}MB"


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.performance
class TestConcurrentPerformance:
    """
    Concurrent processing performance tests.

    These tests validate that Rust components can handle concurrent
    processing efficiently and scale well with multiple threads.
    """

    @pytest.fixture
    def concurrent_test_data(self) -> list[list[str]]:
        """Generate multiple datasets for concurrent testing."""
        datasets = []

        for dataset_id in range(8):  # 8 different datasets
            data = [
                f"Fallout 4 v1.10.163 - Dataset {dataset_id}",
                "Buffout 4 v1.28.6",
                "",
                "PROBABLE CALL STACK:",
            ]

            # Each dataset has different FormIDs/plugins
            for i in range(100):
                formid_base = (dataset_id * 100) + i
                data.append(f"\t[{i}] 0x7FF66DF{formid_base:06X} -> FormID: 0x{formid_base:08X}")

            data.append("")
            data.append("PLUGINS:")

            for i in range(50):
                plugin_id = (dataset_id * 50) + i
                data.append(f"\t[{i:02X}] Dataset{dataset_id}Plugin{plugin_id:03d}.esp")

            datasets.append(data)

        return datasets

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Mock YAML data for concurrent testing."""
        mock_yaml = Mock()
        mock_yaml.game_type = "fallout4"
        mock_yaml.crashgen_name = "Buffout 4"
        mock_yaml.xse_acronym = "F4SE"
        mock_yaml.game_root_name = "Fallout 4"
        mock_yaml.problematic_plugins = {}
        mock_yaml.formid_database_enabled = True
        mock_yaml.show_formid_values = True
        mock_yaml.record_patterns = ["TESForm"]
        return mock_yaml

    def test_concurrent_parser_performance(self, concurrent_test_data, mock_yamldata):
        """
        Test parser performance under concurrent load.

        This test validates that multiple parsers can run concurrently
        without significant performance degradation.
        """
        if not is_rust_accelerated("parser"):
            pytest.skip("Rust parser not available for concurrent performance testing")

        def parse_single(data_index: int) -> dict[str, Any]:
            """Parse a single dataset and return timing info."""
            crash_data = concurrent_test_data[data_index]
            parser = get_parser()

            start_time = time.perf_counter()
            result = parser.find_segments(
                crash_data=crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name
            )
            end_time = time.perf_counter()

            return {
                "data_index": data_index,
                "duration": end_time - start_time,
                "segments_count": len(result[3]),
                "data_size": len(crash_data)
            }

        # Test sequential performance first
        sequential_start = time.perf_counter()
        sequential_results = [parse_single(i) for i in range(4)]
        sequential_time = time.perf_counter() - sequential_start

        # Test concurrent performance
        concurrent_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(parse_single, i) for i in range(4)]
            concurrent_results = [future.result() for future in as_completed(futures)]
        concurrent_time = time.perf_counter() - concurrent_start

        # Analyze results
        sequential_avg = statistics.mean([r["duration"] for r in sequential_results])
        concurrent_avg = statistics.mean([r["duration"] for r in concurrent_results])

        speedup = sequential_time / concurrent_time
        efficiency = speedup / 4  # 4 threads

        logging.info("Parser concurrent performance:")
        logging.info(f"  Sequential total: {sequential_time:.3f}s (avg: {sequential_avg:.3f}s per task)")
        logging.info(f"  Concurrent total: {concurrent_time:.3f}s (avg: {concurrent_avg:.3f}s per task)")
        logging.info(f"  Speedup: {speedup:.2f}x")
        logging.info(f"  Efficiency: {efficiency:.2f} ({efficiency*100:.1f}%)")

        # Should achieve reasonable speedup (at least 2x with 4 threads)
        assert speedup >= 2.0, f"Poor concurrent speedup: {speedup:.2f}x"

        # Efficiency should be reasonable (at least 50%)
        assert efficiency >= 0.5, f"Poor concurrent efficiency: {efficiency:.2f}"

    def test_concurrent_formid_analysis_performance(self, concurrent_test_data, mock_yamldata):
        """
        Test FormID analyzer performance under concurrent load.

        Validates that FormID extraction scales well with concurrent processing.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available for concurrent testing")

        def analyze_formids(data_index: int) -> dict[str, Any]:
            """Analyze FormIDs in a single dataset."""
            crash_data = concurrent_test_data[data_index]
            analyzer = get_formid_analyzer(mock_yamldata, True, True)

            start_time = time.perf_counter()
            formids = analyzer.extract_formids(crash_data)
            end_time = time.perf_counter()

            return {
                "data_index": data_index,
                "duration": end_time - start_time,
                "formid_count": len(formids),
                "data_size": len(crash_data)
            }

        # Test with varying numbers of concurrent threads
        thread_counts = [1, 2, 4]
        results = {}

        for num_threads in thread_counts:
            start_time = time.perf_counter()

            if num_threads == 1:
                # Sequential
                thread_results = [analyze_formids(i) for i in range(4)]
            else:
                # Concurrent
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [executor.submit(analyze_formids, i) for i in range(4)]
                    thread_results = [future.result() for future in as_completed(futures)]

            total_time = time.perf_counter() - start_time
            avg_task_time = statistics.mean([r["duration"] for r in thread_results])
            total_formids = sum(r["formid_count"] for r in thread_results)

            results[num_threads] = {
                "total_time": total_time,
                "avg_task_time": avg_task_time,
                "total_formids": total_formids,
                "formids_per_second": total_formids / total_time
            }

            logging.info(f"FormID analysis with {num_threads} threads: "
                        f"total={total_time:.3f}s, avg_task={avg_task_time:.3f}s, "
                        f"rate={total_formids/total_time:.0f} FormIDs/sec")

        # Validate scaling
        sequential_rate = results[1]["formids_per_second"]
        concurrent_rate = results[4]["formids_per_second"]
        rate_improvement = concurrent_rate / sequential_rate

        # Should see some improvement with concurrency
        assert rate_improvement >= 1.5, \
            f"Poor concurrent scaling for FormID analysis: {rate_improvement:.2f}x"

    def test_mixed_concurrent_operations(self, concurrent_test_data, mock_yamldata):
        """
        Test performance when different components run concurrently.

        This test validates that different types of Rust components can
        run concurrently without interfering with each other's performance.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"]
                               if is_rust_accelerated(comp)]

        if len(available_components) < 2:
            pytest.skip("Need at least 2 different Rust components for mixed concurrent testing")

        def run_mixed_operations(data_index: int) -> dict[str, Any]:
            """Run mixed operations on a dataset."""
            crash_data = concurrent_test_data[data_index]
            results = {"data_index": data_index}

            start_time = time.perf_counter()

            if "parser" in available_components:
                parser = get_parser()
                parse_result = parser.find_segments(
                    crash_data=crash_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name
                )
                results["segments"] = len(parse_result[3])
                segments = parse_result[3]
            else:
                segments = [crash_data]  # Fallback

            if "formid_analyzer" in available_components:
                formid_analyzer = RustFormIDAnalyzer(mock_yamldata, True, True)
                formids = formid_analyzer.extract_formids(segments[0] if segments else crash_data)
                results["formids"] = len(formids)

            if "plugin_analyzer" in available_components:
                plugin_analyzer = RustPluginAnalyzer(mock_yamldata)
                plugins, _, _ = plugin_analyzer.loadorder_scan_log(crash_data)
                results["plugins"] = len(plugins)

            results["duration"] = time.perf_counter() - start_time
            return results

        # Test sequential vs concurrent mixed operations
        sequential_start = time.perf_counter()
        sequential_results = [run_mixed_operations(i) for i in range(4)]
        sequential_time = time.perf_counter() - sequential_start

        concurrent_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_mixed_operations, i) for i in range(4)]
            concurrent_results = [future.result() for future in as_completed(futures)]
        concurrent_time = time.perf_counter() - concurrent_start

        speedup = sequential_time / concurrent_time

        logging.info("Mixed concurrent operations:")
        logging.info(f"  Components: {available_components}")
        logging.info(f"  Sequential: {sequential_time:.3f}s")
        logging.info(f"  Concurrent: {concurrent_time:.3f}s")
        logging.info(f"  Speedup: {speedup:.2f}x")

        # Should achieve some speedup with mixed operations
        assert speedup >= 1.5, f"Poor mixed concurrent speedup: {speedup:.2f}x"

        # Results should be consistent
        for seq_result, conc_result in zip(sequential_results, concurrent_results):
            for key in ["segments", "formids", "plugins"]:
                if key in seq_result and key in conc_result:
                    assert seq_result[key] == conc_result[key], \
                        f"Inconsistent results for {key}: seq={seq_result[key]}, conc={conc_result[key]}"


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

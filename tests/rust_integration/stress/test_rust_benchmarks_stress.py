"""
Performance benchmarking tests for Rust components.

This module provides comprehensive performance benchmarking tests that establish
performance baselines and validate that Rust acceleration provides expected
performance improvements across various scenarios and data sizes.

Key Testing Areas:
- Parser performance scaling with different data sizes
- FormID analyzer performance characteristics
- Plugin analyzer throughput testing
- Integrated pipeline performance validation
- Performance regression detection
"""
# ruff: noqa: ANN201, ANN001, ARG001, PLR6301

import logging
import operator
import statistics
import tracemalloc
from unittest.mock import Mock

import pytest

# Skip entire module if Rust extensions not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

if tracemalloc.is_tracing():
    pytest.skip("Tracemalloc is running, results would be skewed.", allow_module_level=True)

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

logger = logging.getLogger(__name__)


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
        small_data.extend(f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}" for i in range(50))

        small_data.extend((
            "",
            "PLUGINS:",
        ))

        # Add moderate plugin list
        small_data.extend(f"\t[{i:02X}] Plugin{i:03d}.esp" for i in range(50))

        datasets["small"] = small_data

        # Medium dataset (typical crash log)
        medium_data = small_data.copy()

        # Expand call stack
        for i in range(50, 200):
            medium_data.insert(-52, f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}")

        # Expand plugin list
        medium_data.extend(f"\t[{i:02X}] Plugin{i:03d}.esp" for i in range(50, 150))

        datasets["medium"] = medium_data

        # Large dataset (large crash log with many mods)
        large_data = medium_data.copy()

        # Massive call stack
        for i in range(200, 1000):
            large_data.insert(-152, f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}")

        # Large plugin list
        large_data.extend(f"\t[{i:02X}] Plugin{i:03d}.esp" for i in range(150, 250))

        # Add ESL plugins
        large_data.extend(f"\t[FE:{i:03X}] ESLPlugin{i:03d}.esl" for i in range(50))

        datasets["large"] = large_data

        # Extra large dataset (stress test)
        xlarge_data = large_data.copy()

        # Enormous call stack
        for i in range(1000, 5000):
            xlarge_data.insert(-302, f"\t[{i}] 0x7FF66DF{i:06X} -> FormID: 0x{i:08X}")

        datasets["xlarge"] = xlarge_data

        return datasets

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
            for _iteration in range(5):
                with PerformanceTimer() as timer:
                    parser.find_segments(
                        crash_data=crash_data,
                        crashgen_name=mock_yamldata.crashgen_name,
                        xse_acronym=mock_yamldata.xse_acronym,
                        game_root_name=mock_yamldata.game_root_name,
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
                "lines_per_second": data_size_lines / avg_time,
            }

            logger.info(
                f"Parser performance - {size_category} ({data_size_lines} lines): "
                f"avg={avg_time:.3f}s, std={std_time:.3f}s, "
                f"rate={data_size_lines / avg_time:.0f} lines/sec"
            )

        # Validate performance targets
        targets = {
            "small": 0.01,  # 10ms for small logs
            "medium": 0.05,  # 50ms for medium logs
            "large": 0.15,  # 150ms for large logs
            "xlarge": 0.5,  # 500ms for extra large logs
        }

        for size_category, target_time in targets.items():
            if size_category in performance_results:
                avg_time = performance_results[size_category]["avg_time"]
                assert avg_time < target_time, f"Parser too slow for {size_category}: {avg_time:.3f}s > {target_time}s"

        # Validate scaling characteristics (should be roughly linear)
        sizes = [(k, v["data_size"], v["avg_time"]) for k, v in performance_results.items()]
        sizes.sort(key=operator.itemgetter(1))  # Sort by data size

        if len(sizes) >= 2:
            # Check that performance scales reasonably
            small_rate = sizes[0][1] / sizes[0][2]  # lines per second
            large_rate = sizes[-1][1] / sizes[-1][2]  # lines per second

            # Rate should not degrade more than 50% with larger datasets
            rate_ratio = large_rate / small_rate
            assert rate_ratio > 0.5, f"Performance degrades too much with size: {rate_ratio:.2f}"

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

            for _iteration in range(5):
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
                "formids_per_second": formids_per_second,
            }

            logger.info(
                f"FormID analyzer - {size_category}: "
                f"extracted {avg_formid_count:.1f} FormIDs in {avg_time:.3f}s "
                f"({formids_per_second:.0f} FormIDs/sec)"
            )

        # Validate performance targets
        for size_category, results in performance_results.items():
            # Should extract FormIDs very quickly
            if results["extracted_formids"] > 10:  # Only test substantial extractions
                formids_per_second = results["formids_per_second"]
                assert formids_per_second > 1000, f"FormID extraction too slow for {size_category}: {formids_per_second:.0f} FormIDs/sec"

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

            for _iteration in range(5):
                with PerformanceTimer() as timer:
                    plugins_dict, _, _ = analyzer.loadorder_scan_log(plugin_data)
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
                "plugins_per_second": plugins_per_second,
            }

            logger.info(
                f"Plugin analyzer - {size_category}: "
                f"parsed {avg_plugin_count:.1f} plugins in {avg_time:.3f}s "
                f"({plugins_per_second:.0f} plugins/sec)"
            )

        # Validate performance targets
        for size_category, results in performance_results.items():
            if results["parsed_plugins"] > 10:  # Only test substantial load orders
                plugins_per_second = results["plugins_per_second"]
                assert plugins_per_second > 5000, f"Plugin analysis too slow for {size_category}: {plugins_per_second:.0f} plugins/sec"

    def test_integrated_pipeline_performance(self, performance_test_data, mock_yamldata):
        """
        Test performance of the complete integrated pipeline.

        This test measures the performance when all components work
        together in the complete processing pipeline.
        """
        available_components = [
            comp for comp in ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"] if is_rust_accelerated(comp)
        ]

        if len(available_components) < 2:
            pytest.skip("Need at least 2 Rust components for integrated performance testing")

        performance_results = {}

        for size_category, crash_data in performance_test_data.items():
            # Run complete pipeline
            times = []
            results_data = []

            for _iteration in range(3):  # Fewer iterations due to complexity
                with PerformanceTimer() as timer:
                    # Initialize components
                    segments = []
                    if "parser" in available_components:
                        parser = get_parser()
                        _, _, _, segments = parser.find_segments(
                            crash_data=crash_data,
                            crashgen_name=mock_yamldata.crashgen_name,
                            xse_acronym=mock_yamldata.xse_acronym,
                            game_root_name=mock_yamldata.game_root_name,
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
                        _, matches = record_scanner.scan_named_records(segments[2])
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
                "results": results_data[0] if results_data else {},
            }

            logger.info(
                f"Integrated pipeline - {size_category}: "
                f"{avg_time:.3f}s avg, {len(available_components)} components, "
                f"results: {results_data[0] if results_data else 'none'}"
            )

        # Validate integrated performance targets
        targets = {
            "small": 0.05,  # 50ms for small logs
            "medium": 0.15,  # 150ms for medium logs
            "large": 0.5,  # 500ms for large logs
            "xlarge": 2.0,  # 2s for extra large logs
        }

        for size_category, target_time in targets.items():
            if size_category in performance_results:
                avg_time = performance_results[size_category]["avg_time"]
                assert avg_time < target_time, f"Integrated pipeline too slow for {size_category}: {avg_time:.3f}s > {target_time}s"


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

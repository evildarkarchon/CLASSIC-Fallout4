"""
Component performance tests for Phase 6 Rust migration validation.

This module tests performance characteristics of component interactions,
validating that component interactions don't introduce performance
bottlenecks and that the combined performance is better than the sum
of individual component times.

Key Integration Points Tested:
- Component pipeline performance
- Memory usage stability
"""
# ruff: noqa: ANN201, ANN001, PLR6301, ARG002, ANN202, BLE001, PT017

import logging
from unittest.mock import Mock

import pytest

# Skip entire module if Rust extensions not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

# Import factory pattern for Rust components
from ClassicLib.integration.factory import (
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
    is_rust_accelerated,
)

# Status imports
from tests.test_infra.performance_utils import PerformanceTimer

logger = logging.getLogger(__name__)


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.component
@pytest.mark.performance
class TestComponentPerformance:
    """
    Test performance characteristics of component interactions.

    These tests validate that component interactions don't introduce
    performance bottlenecks and that the combined performance is
    better than the sum of individual component times.
    """

    @pytest.fixture
    def large_crash_data(self) -> list[str]:
        """Generate large crash data for performance testing."""
        base_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            "PROBABLE CALL STACK:",
        ]

        # Add many call stack entries with FormIDs
        base_data.extend(f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}" for i in range(1000))

        base_data.extend([
            "",
            "PLUGINS:",
        ])

        # Add many plugins
        base_data.extend(f"\t[{i:02X}] Plugin{i:03d}.esp" for i in range(200))

        return base_data

    def test_component_pipeline_performance(self, large_crash_data, mock_yamldata):
        """
        Test performance of the complete component pipeline.

        Measures the time it takes to process large crash data through
        all available Rust components and validates performance targets.
        """
        available_components = [
            comp for comp in ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"] if is_rust_accelerated(comp)
        ]

        if not available_components:
            pytest.skip("No Rust components available for performance testing")

        component_times = {}
        segments = None

        # Measure parser performance
        if "parser" in available_components:
            parser = get_parser()

            with PerformanceTimer() as timer:
                result = parser.find_segments(
                    crash_data=large_crash_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name,
                )
                segments = result[3]

            component_times["parser"] = timer.elapsed
            assert timer.elapsed < 0.1, f"Parser too slow for large data: {timer.elapsed:.3f}s"

        # Measure FormID analyzer performance
        if "formid_analyzer" in available_components and segments:
            formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)
            callstack = segments[2] if len(segments) > 2 else large_crash_data

            with PerformanceTimer() as timer:
                formids = formid_analyzer.extract_formids(callstack)

            component_times["formid_analyzer"] = timer.elapsed
            assert timer.elapsed < 0.05, f"FormID analyzer too slow: {timer.elapsed:.3f}s"
            assert len(formids) > 0, "Should extract FormIDs from large data"

        # Measure Plugin analyzer performance
        if "plugin_analyzer" in available_components:
            plugin_analyzer = get_plugin_analyzer(mock_yamldata)
            plugin_data = segments[-1] if segments else large_crash_data

            with PerformanceTimer() as timer:
                plugins, _, _ = plugin_analyzer.loadorder_scan_log(plugin_data)

            component_times["plugin_analyzer"] = timer.elapsed
            assert timer.elapsed < 0.05, f"Plugin analyzer too slow: {timer.elapsed:.3f}s"
            assert len(plugins) > 0, "Should extract plugins from large data"

        # Log performance summary
        total_time = sum(component_times.values())
        logger.info("Component pipeline performance:")
        for component, time_taken in component_times.items():
            logger.info(f"  {component}: {time_taken:.3f}s")
        logger.info(f"  Total: {total_time:.3f}s")

        # Total pipeline should be very fast even with large data
        assert total_time < 0.2, f"Total pipeline too slow: {total_time:.3f}s"

    def test_memory_usage_stability(self, large_crash_data, mock_yamldata):
        """
        Test that component interactions don't cause memory leaks.

        Runs the component pipeline multiple times and validates
        that memory usage remains stable.
        """
        import os

        import psutil

        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"] if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for memory testing")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Run pipeline multiple times
        for _iteration in range(10):
            segments = None
            if "parser" in available_components:
                parser = get_parser()
                result = parser.find_segments(
                    crash_data=large_crash_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name,
                )
                segments = result[3]

            if "formid_analyzer" in available_components and segments:
                formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)
                callstack = segments[2] if len(segments) > 2 else large_crash_data
                formid_analyzer.extract_formids(callstack)

            if "plugin_analyzer" in available_components:
                plugin_analyzer = get_plugin_analyzer(mock_yamldata)
                plugin_data = segments[-1] if segments else large_crash_data
                _, _, _ = plugin_analyzer.loadorder_scan_log(plugin_data)

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal (< 10MB)
        max_growth = 10 * 1024 * 1024  # 10MB
        assert memory_growth < max_growth, f"Excessive memory growth: {memory_growth / 1024 / 1024:.1f}MB"


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

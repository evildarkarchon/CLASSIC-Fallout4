"""
Component concurrency tests for Phase 6 Rust migration validation.

This module tests thread safety and concurrent access patterns for Rust
components, validating that they can be safely used concurrently without
race conditions or data corruption.

Key Integration Points Tested:
- Concurrent parser usage
- Concurrent FormID analysis
- Mixed concurrent component usage
"""
# ruff: noqa: ANN201, ANN001, PLR6301, ARG002, ANN202, BLE001, PT017

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
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

logger = logging.getLogger(__name__)


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.component
class TestComponentConcurrency:
    """
    Test thread safety and concurrent access patterns.

    These tests validate that Rust components can be safely used
    concurrently without race conditions or data corruption.
    """

    @pytest.fixture
    def sample_crash_data(self) -> list[str]:
        """Sample crash data for concurrency testing."""
        return [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            "PROBABLE CALL STACK:",
            "\t[0] 0x7FF66DF19300 -> FormID: 0x12345678",
            "\t[1] 0x7FF66DF19400 -> FormID: 0xABCDEF01",
            "",
            "PLUGINS:",
            "\t[00] Fallout4.esm",
            "\t[01] TestPlugin.esp",
        ]

    def test_concurrent_parser_usage(self, sample_crash_data, mock_yamldata):
        """
        Test that multiple parsers can run concurrently.

        Validates that parser instances don't interfere with each other
        when processing different crash logs simultaneously.
        """
        if not is_rust_accelerated("parser"):
            pytest.skip("Rust parser not available for concurrency testing")

        def parse_log(thread_id: int) -> dict[str, Any]:
            """Parse log in a thread and return results."""
            parser = get_parser()
            start_time = time.time()

            result = parser.find_segments(
                crash_data=sample_crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name,
            )

            end_time = time.time()
            return {"thread_id": thread_id, "result": result, "duration": end_time - start_time, "segments_count": len(result[3])}

        # Run multiple parsers concurrently
        num_threads = 5
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(parse_log, i) for i in range(num_threads)]
            results = [future.result() for future in futures]

        # Validate all results are consistent
        baseline_segments_count = results[0]["segments_count"]
        for result in results:
            assert result["segments_count"] == baseline_segments_count, (
                f"Thread {result['thread_id']} got different segment count: {result['segments_count']} vs {baseline_segments_count}"
            )
            assert result["duration"] < 1.0, f"Thread {result['thread_id']} took too long: {result['duration']}s"

    def test_concurrent_formid_analysis(self, mock_yamldata):
        """
        Test concurrent FormID analysis operations.

        Validates that FormID analyzer can safely process different
        data sets concurrently without interference.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available for concurrency testing")

        # Different test data for each thread
        test_datasets = [
            ["\t[0] 0x7FF66DF19300 -> FormID: 0x11111111"],
            ["\t[0] 0x7FF66DF19400 -> FormID: 0x22222222"],
            ["\t[0] 0x7FF66DF19500 -> FormID: 0x33333333"],
            ["\t[0] 0x7FF66DF19600 -> FormID: 0x44444444"],
            ["\t[0] 0x7FF66DF19700 -> FormID: 0x55555555"],
        ]

        def analyze_formids(thread_id: int, data: list[str]) -> dict[str, Any]:
            """Analyze FormIDs in a thread."""
            analyzer = get_formid_analyzer(mock_yamldata, True, True)
            start_time = time.time()

            formids = analyzer.extract_formids(data)

            end_time = time.time()
            return {
                "thread_id": thread_id,
                "formids": formids,
                "duration": end_time - start_time,
                "expected_formid": f"{(thread_id + 1) * 11111111}",  # Match input format which is 0x11111111 but output strips 0x
            }

        # Run concurrent FormID analysis
        with ThreadPoolExecutor(max_workers=len(test_datasets)) as executor:
            futures = [executor.submit(analyze_formids, i, data) for i, data in enumerate(test_datasets)]
            results = [future.result() for future in futures]

        # Validate each thread got the correct FormID
        for result in results:
            expected = result["expected_formid"]
            found_formids = result["formids"]

            assert any(expected in formid for formid in found_formids), (
                f"Thread {result['thread_id']} didn't find expected FormID {expected} in {found_formids}"
            )

    def test_concurrent_component_mix(self, sample_crash_data, mock_yamldata):
        """
        Test concurrent usage of different component types.

        Validates that different types of components (parser, analyzer, etc.)
        can run concurrently without interfering with each other.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"] if is_rust_accelerated(comp)]

        if len(available_components) < 2:
            pytest.skip("Need at least 2 different Rust components for mixed concurrency testing")

        results = {}

        def run_parser():
            if "parser" not in available_components:
                return None
            parser = get_parser()
            return parser.find_segments(
                crash_data=sample_crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name,
            )

        def run_formid_analyzer():
            if "formid_analyzer" not in available_components:
                return None
            analyzer = get_formid_analyzer(mock_yamldata, True, True)
            return analyzer.extract_formids(sample_crash_data)

        def run_plugin_analyzer():
            if "plugin_analyzer" not in available_components:
                return None
            analyzer = get_plugin_analyzer(mock_yamldata)
            return analyzer.loadorder_scan_log(sample_crash_data)

        # Run different components concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            if "parser" in available_components:
                futures["parser"] = executor.submit(run_parser)
            if "formid_analyzer" in available_components:
                futures["formid_analyzer"] = executor.submit(run_formid_analyzer)
            if "plugin_analyzer" in available_components:
                futures["plugin_analyzer"] = executor.submit(run_plugin_analyzer)

            # Collect results
            for component, future in futures.items():
                try:
                    results[component] = future.result()
                except Exception as e:
                    results[component] = f"Error: {e}"

        # Validate that all components completed successfully
        for component, result in results.items():
            assert not str(result).startswith("Error:"), f"Component {component} failed in concurrent execution: {result}"
            assert result is not None, f"Component {component} returned None"


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

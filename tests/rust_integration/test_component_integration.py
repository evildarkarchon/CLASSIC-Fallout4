"""
Component integration tests for Phase 6 Rust migration validation.

This module tests how all Rust components work together, validating data flow
between components, error handling, and ensuring no performance regressions.
Tests focus on the interactions between components rather than individual
component functionality.

Key Integration Points Tested:
- Data flow between LogParser -> FormIDAnalyzer -> PluginAnalyzer -> RecordScanner
- Shared state and caching between components
- Error propagation and recovery mechanisms
- Memory management across component boundaries
- Thread safety and concurrent access patterns
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Skip entire module if Rust extensions not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

# Import test infrastructure
from tests.test_infra.async_test_utils import AsyncTestCase
from tests.test_infra.performance_utils import PerformanceTimer

# Import core components
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib import GlobalRegistry
from ClassicLib.MessageHandler import MessageHandler
# Import factory pattern for Rust components
from ClassicLib.integration.factory import (
    get_parser,
    get_formid_analyzer,
    get_plugin_analyzer,
    get_record_scanner,
    get_database_pool,
    get_file_io,
)
from ClassicLib.integration.status import (
    get_rust_component_status,
    is_rust_accelerated,
)
# Status imports
from ClassicLib.integration.status import (
    RUST_AVAILABLE,
    get_performance_multiplier,
    print_rust_status,
)
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.component
class TestComponentDataFlow:
    """
    Test data flow between Rust components.

    These tests validate that data passes correctly between components
    and that the output of one component is properly formatted for
    consumption by the next component in the pipeline.
    """

    @pytest.fixture
    def sample_crash_data(self) -> List[str]:
        """
        Provide sample crash log data for component testing.

        Returns a comprehensive crash log with all sections needed
        for testing component interactions.
        """
        return [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF66DF19300 Fallout4.exe+0DB9300",
            "",
            "\t[Compatibility]",
            "\t\tF4EE: false",
            "",
            "SYSTEM SPECS:",
            "\tOS: Microsoft Windows 11 Home v10.0.22621",
            "\tCPU: AMD Ryzen 5 5600X 6-Core Processor",
            "\tGPU #1: Nvidia GeForce RTX 3060 Ti",
            "\tPHYSICAL MEMORY: 16.00 GB/32.00 GB",
            "",
            "PROBABLE CALL STACK:",
            "\t[0] 0x7FF66DF19300 Fallout4.exe+0DB9300 -> FormID: 0x12345678 (TestMod.esp)",
            "\t[1] 0x7FF66DF19400 Fallout4.exe+0DB9400 -> FormID: 0xABCDEF01 (AnotherMod.esp)",
            "\t[2] 0x7FF66E123456 Fallout4.exe+1523456 -> BGSKeyword at 0x7FF66E123456",
            "\t[3] 0x7FF66E789ABC Fallout4.exe+1789ABC -> TESForm at 0x7FF66E789ABC",
            "",
            "MODULES:",
            "\tFallout4.exe",
            "\tf4se_1_6_353.dll",
            "\tbuffout4.dll",
            "\tTestMod.dll",
            "",
            "F4SE PLUGINS:",
            "\tBuffout4 v1.28.6",
            "\tTestPlugin v1.0.0",
            "",
            "PLUGINS:",
            "\t[00] Fallout4.esm",
            "\t[01] DLCRobot.esm",
            "\t[02] DLCworkshop01.esm",
            "\t[03] DLCCoast.esm",
            "\t[04] DLCNukaWorld.esm",
            "\t[FE:000] TestMod.esl",
            "\t[05] TestPlugin.esp",
            "\t[06] AnotherMod.esp",
            "\t[07] ProblematicPlugin.esp"
        ]

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Create comprehensive mock YAML data for component integration testing."""
        mock_yaml = Mock()

        # Game configuration
        mock_yaml.game_type = "fallout4"
        mock_yaml.crashgen_name = "Buffout 4"
        mock_yaml.xse_acronym = "F4SE"
        mock_yaml.game_root_name = "Fallout 4"

        # Problematic plugins for testing plugin matching
        mock_yaml.problematic_plugins = {
            "ProblematicPlugin.esp": "Known to cause crashes",
            "OldMod.esp": "Outdated mod that conflicts",
            "BrokenMesh.esp": "Contains broken meshes"
        }

        # FormID database configuration
        mock_yaml.formid_database_enabled = True
        mock_yaml.show_formid_values = True

        # Record patterns for named record scanning
        mock_yaml.record_patterns = [
            "TESForm",
            "BGSKeyword",
            "TESObjectSTAT",
            "TESObjectREFR",
            "BGSConstructibleObject"
        ]

        # Plugin limit configuration
        mock_yaml.plugin_limits = {
            "esp_limit": 255,
            "esl_limit": 2048
        }

        return mock_yaml

    def test_parser_to_formid_analyzer_flow(self, sample_crash_data, mock_yamldata):
        """
        Test data flow from LogParser to FormIDAnalyzer.

        Validates that the segments produced by the parser are properly
        formatted and contain the data needed by the FormID analyzer.
        """
        if not (is_rust_accelerated("parser") and is_rust_accelerated("formid_analyzer")):
            pytest.skip("Both parser and FormID analyzer needed for flow testing")

        # Parse the crash log
        parser = get_parser()
        game_version, crashgen_version, main_error, segments = parser.find_segments(
            crash_data=sample_crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name
        )

        # Validate parser output structure
        assert isinstance(segments, list), "Segments should be a list"
        assert len(segments) >= 3, "Should have at least 3 segments (compatibility, system, callstack)"

        # Extract call stack segment (typically index 2)
        callstack_segment = segments[2] if len(segments) > 2 else []

        # Pass to FormID analyzer
        formid_analyzer = get_formid_analyzer(
            yamldata=mock_yamldata,
            show_values=True,
            db_exists=True
        )

        formids = formid_analyzer.extract_formids(callstack_segment)

        # Validate FormID extraction results
        assert isinstance(formids, list), "FormIDs should be returned as list"

        # Should find the FormIDs in our test data
        expected_formids = ["0x12345678", "0xABCDEF01"]
        for expected_formid in expected_formids:
            assert any(expected_formid in formid for formid in formids), \
                f"Expected FormID {expected_formid} not found in {formids}"

    def test_parser_to_plugin_analyzer_flow(self, sample_crash_data, mock_yamldata):
        """
        Test data flow from LogParser to PluginAnalyzer.

        Validates that plugin segments are properly extracted and
        formatted for plugin analysis.
        """
        if not (is_rust_accelerated("parser") and is_rust_accelerated("plugin_analyzer")):
            pytest.skip("Both parser and plugin analyzer needed for flow testing")

        # Parse the crash log
        parser = get_parser()
        _, _, _, segments = parser.find_segments(
            crash_data=sample_crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name
        )

        # Extract plugins segment (typically the last segment)
        plugins_segment = segments[-1] if segments else []

        # Pass to Plugin analyzer
        plugin_analyzer = get_plugin_analyzer(mock_yamldata)

        plugins_dict, limit_triggered, limit_disabled = plugin_analyzer.loadorder_scan_log(
            segment_plugins=plugins_segment
        )

        # Validate plugin analysis results
        assert isinstance(plugins_dict, dict), "Plugins should be returned as dict"

        # Should find expected plugins from test data
        expected_plugins = ["Fallout4.esm", "TestPlugin.esp", "AnotherMod.esp"]
        found_plugins = list(plugins_dict.values())

        for expected_plugin in expected_plugins:
            assert any(expected_plugin in plugin for plugin in found_plugins), \
                f"Expected plugin {expected_plugin} not found in {found_plugins}"

    def test_parser_to_record_scanner_flow(self, sample_crash_data, mock_yamldata):
        """
        Test data flow from LogParser to RecordScanner.

        Validates that call stack segments contain the data needed
        for named record scanning.
        """
        if not (is_rust_accelerated("parser") and is_rust_accelerated("record_scanner")):
            pytest.skip("Both parser and record scanner needed for flow testing")

        # Parse the crash log
        parser = get_parser()
        _, _, _, segments = parser.find_segments(
            crash_data=sample_crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name
        )

        # Extract call stack segment
        callstack_segment = segments[2] if len(segments) > 2 else []

        # Pass to Record scanner
        record_scanner = get_record_scanner(mock_yamldata)

        fragment, matches = record_scanner.scan_named_records(callstack_segment)

        # Validate record scanning results
        assert isinstance(matches, list), "Matches should be returned as list"

        # Should find the record types in our test data
        expected_records = ["BGSKeyword", "TESForm"]
        for expected_record in expected_records:
            assert any(expected_record in match for match in matches), \
                f"Expected record {expected_record} not found in {matches}"

    def test_integrated_component_chain(self, sample_crash_data, mock_yamldata):
        """
        Test the complete chain of component interactions.

        This test runs data through the entire chain: Parser -> FormIDAnalyzer,
        Parser -> PluginAnalyzer, Parser -> RecordScanner, and validates
        that all components can work together seamlessly.
        """
        required_components = ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"]
        missing = [comp for comp in required_components if not is_rust_accelerated(comp)]
        if missing:
            pytest.skip(f"Missing Rust components for chain test: {missing}")

        # Initialize all components
        parser = get_parser()
        formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)
        plugin_analyzer = get_plugin_analyzer(mock_yamldata)
        record_scanner = get_record_scanner(mock_yamldata)

        # Parse crash log
        with PerformanceTimer("Complete component chain") as timer:
            game_version, crashgen_version, main_error, segments = parser.find_segments(
                crash_data=sample_crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name
            )

            # Process through all analyzers
            results = {}

            if len(segments) > 2:
                callstack_segment = segments[2]

                # FormID analysis
                results["formids"] = formid_analyzer.extract_formids(callstack_segment)

                # Record scanning
                results["records_fragment"], results["record_matches"] = record_scanner.scan_named_records(callstack_segment)

            # Plugin analysis (last segment)
            if segments:
                plugins_segment = segments[-1]
                results["plugins"], results["limit_triggered"], results["limit_disabled"] = plugin_analyzer.loadorder_scan_log(plugins_segment)

        # Validate complete chain results
        assert "formids" in results, "FormID analysis should complete"
        assert "plugins" in results, "Plugin analysis should complete"
        assert "record_matches" in results, "Record scanning should complete"

        # Validate data consistency across components
        formids = results["formids"]
        plugins = results["plugins"]

        # FormIDs should reference plugins that exist in the load order
        if formids and plugins:
            plugin_names = list(plugins.values())
            # Check that FormIDs reference known plugins (this is a simplified check)
            for formid in formids:
                if "(" in formid and ")" in formid:
                    # Extract plugin name from FormID string like "0x12345678 (TestMod.esp)"
                    plugin_ref = formid.split("(")[1].split(")")[0]
                    assert any(plugin_ref in plugin for plugin in plugin_names), \
                        f"FormID references unknown plugin: {plugin_ref}"

        logging.info(f"Complete component chain processing time: {timer.elapsed:.3f}s")


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.component
class TestComponentErrorHandling:
    """
    Test error handling and recovery mechanisms between components.

    These tests validate that errors in one component don't cascade
    and break other components, and that proper fallback mechanisms
    are in place.
    """

    @pytest.fixture
    def corrupted_crash_data(self) -> List[str]:
        """Provide corrupted crash data to test error handling."""
        return [
            "CORRUPTED_HEADER",
            "INVALID_DATA_123",
            "",
            "PROBABLE CALL STACK:",
            "INVALID_STACK_ENTRY",
            "\t[MALFORMED] 0xINVALID -> FormID: NOTAHEX",
            "",
            "PLUGINS:",
            "INVALID_PLUGIN_ENTRY",
            "\t[XX] InvalidPlugin.esp",
        ]

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Mock YAML data for error testing."""
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

    def test_parser_error_isolation(self, corrupted_crash_data, mock_yamldata):
        """
        Test that parser errors don't crash other components.

        Validates that when the parser encounters malformed data,
        it still produces usable output for downstream components.
        """
        if not is_rust_accelerated("parser"):
            pytest.skip("Rust parser not available for error testing")

        parser = get_parser()

        # Parser should handle corrupted data gracefully
        try:
            game_version, crashgen_version, main_error, segments = parser.find_segments(
                crash_data=corrupted_crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name
            )

            # Should still return structured data even with corruption
            assert isinstance(segments, list), "Should return list even with corrupted data"
            assert game_version is not None, "Should return some game version"
            assert crashgen_version is not None, "Should return some crashgen version"
            assert main_error is not None, "Should return some error info"

        except Exception as e:
            # If parser does fail, it should be a controlled failure, not a crash
            assert "corrupted" in str(e).lower() or "invalid" in str(e).lower(), \
                f"Parser error should indicate data corruption: {e}"

    def test_formid_analyzer_error_recovery(self, corrupted_crash_data, mock_yamldata):
        """
        Test that FormIDAnalyzer handles malformed data gracefully.

        Validates that invalid FormIDs don't crash the analyzer and
        that it can extract what valid data exists.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available for error testing")

        formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)

        # Create segment with mixed valid/invalid FormIDs
        mixed_data = [
            "\t[0] 0x7FF66DF19300 Fallout4.exe+0DB9300 -> FormID: 0x12345678",  # Valid
            "\t[1] 0xINVALID -> FormID: NOTAHEX",  # Invalid
            "\t[2] 0x7FF66DF19400 -> FormID: 0xABCDEF01",  # Valid
            "CORRUPTED LINE WITH NO FORMID",  # No FormID
        ]

        try:
            formids = formid_analyzer.extract_formids(mixed_data)

            # Should return a list even with mixed data
            assert isinstance(formids, list), "Should return list with mixed data"

            # Should extract valid FormIDs and skip invalid ones
            valid_formids = [fid for fid in formids if fid and "0x" in fid]
            assert len(valid_formids) > 0, "Should extract at least some valid FormIDs"

        except Exception as e:
            # If it does fail, should be a controlled failure
            assert "invalid" in str(e).lower() or "malformed" in str(e).lower(), \
                f"FormID analyzer error should indicate data issues: {e}"

    def test_plugin_analyzer_error_resilience(self, corrupted_crash_data, mock_yamldata):
        """
        Test that PluginAnalyzer handles malformed plugin data.

        Validates that invalid plugin entries don't prevent processing
        of valid entries and that the analyzer recovers gracefully.
        """
        if not is_rust_accelerated("plugin_analyzer"):
            pytest.skip("Rust plugin analyzer not available for error testing")

        plugin_analyzer = get_plugin_analyzer(mock_yamldata)

        # Create segment with mixed valid/invalid plugins
        mixed_plugins = [
            "\t[00] Fallout4.esm",  # Valid
            "\t[INVALID] BrokenEntry",  # Invalid format
            "\t[01] ValidPlugin.esp",  # Valid
            "CORRUPTED_PLUGIN_LINE",  # Completely malformed
            "\t[02] AnotherValid.esp",  # Valid
        ]

        try:
            plugins_dict, limit_triggered, limit_disabled = plugin_analyzer.loadorder_scan_log(mixed_plugins)

            # Should return structured data even with mixed input
            assert isinstance(plugins_dict, dict), "Should return dict with mixed data"
            assert isinstance(limit_triggered, bool), "Should return boolean for limit trigger"
            assert isinstance(limit_disabled, bool), "Should return boolean for limit disabled"

            # Should extract valid plugins and skip invalid ones
            valid_plugins = [p for p in plugins_dict.values() if p and ".es" in p]
            assert len(valid_plugins) > 0, "Should extract at least some valid plugins"

        except Exception as e:
            # If it does fail, should be controlled
            assert "invalid" in str(e).lower() or "malformed" in str(e).lower(), \
                f"Plugin analyzer error should indicate data issues: {e}"

    def test_component_chain_error_propagation(self, corrupted_crash_data, mock_yamldata):
        """
        Test error propagation through the component chain.

        Validates that an error in one component doesn't prevent
        other components from processing what data they can.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"]
                               if is_rust_accelerated(comp)]

        if len(available_components) < 2:
            pytest.skip("Need at least 2 Rust components for error propagation testing")

        results = {}
        errors = {}

        # Try each component and collect results/errors
        if "parser" in available_components:
            try:
                parser = get_parser()
                results["parser"] = parser.find_segments(
                    crash_data=corrupted_crash_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name
                )
            except Exception as e:
                errors["parser"] = str(e)

        # Get segments for downstream components
        segments = results.get("parser", (None, None, None, []))[3]

        if "formid_analyzer" in available_components and segments:
            try:
                formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)
                callstack = segments[0] if segments else corrupted_crash_data
                results["formid_analyzer"] = formid_analyzer.extract_formids(callstack)
            except Exception as e:
                errors["formid_analyzer"] = str(e)

        if "plugin_analyzer" in available_components:
            try:
                plugin_analyzer = get_plugin_analyzer(mock_yamldata)
                plugin_data = segments[-1] if segments else corrupted_crash_data
                results["plugin_analyzer"] = plugin_analyzer.loadorder_scan_log(plugin_data)
            except Exception as e:
                errors["plugin_analyzer"] = str(e)

        # At least some components should either succeed or fail gracefully
        total_attempts = len(available_components)
        successful_results = len(results)
        controlled_errors = len([e for e in errors.values() if "invalid" in e.lower() or "malformed" in e.lower()])

        assert (successful_results + controlled_errors) == total_attempts, \
            f"Components should either succeed or fail gracefully. Results: {results}, Errors: {errors}"


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
    def sample_crash_data(self) -> List[str]:
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

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Mock YAML data for concurrency testing."""
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

    def test_concurrent_parser_usage(self, sample_crash_data, mock_yamldata):
        """
        Test that multiple parsers can run concurrently.

        Validates that parser instances don't interfere with each other
        when processing different crash logs simultaneously.
        """
        if not is_rust_accelerated("parser"):
            pytest.skip("Rust parser not available for concurrency testing")

        def parse_log(thread_id: int) -> Dict[str, Any]:
            """Parse log in a thread and return results."""
            parser = get_parser()
            start_time = time.time()

            result = parser.find_segments(
                crash_data=sample_crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name
            )

            end_time = time.time()
            return {
                "thread_id": thread_id,
                "result": result,
                "duration": end_time - start_time,
                "segments_count": len(result[3])
            }

        # Run multiple parsers concurrently
        num_threads = 5
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(parse_log, i) for i in range(num_threads)]
            results = [future.result() for future in futures]

        # Validate all results are consistent
        baseline_segments_count = results[0]["segments_count"]
        for result in results:
            assert result["segments_count"] == baseline_segments_count, \
                f"Thread {result['thread_id']} got different segment count: {result['segments_count']} vs {baseline_segments_count}"
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

        def analyze_formids(thread_id: int, data: List[str]) -> Dict[str, Any]:
            """Analyze FormIDs in a thread."""
            analyzer = get_formid_analyzer(mock_yamldata, True, True)
            start_time = time.time()

            formids = analyzer.extract_formids(data)

            end_time = time.time()
            return {
                "thread_id": thread_id,
                "formids": formids,
                "duration": end_time - start_time,
                "expected_formid": f"0x{(thread_id + 1) * 11111111:08X}".upper()
            }

        # Run concurrent FormID analysis
        with ThreadPoolExecutor(max_workers=len(test_datasets)) as executor:
            futures = [executor.submit(analyze_formids, i, data)
                      for i, data in enumerate(test_datasets)]
            results = [future.result() for future in futures]

        # Validate each thread got the correct FormID
        for result in results:
            expected = result["expected_formid"]
            found_formids = result["formids"]

            assert any(expected in formid for formid in found_formids), \
                f"Thread {result['thread_id']} didn't find expected FormID {expected} in {found_formids}"

    def test_concurrent_component_mix(self, sample_crash_data, mock_yamldata):
        """
        Test concurrent usage of different component types.

        Validates that different types of components (parser, analyzer, etc.)
        can run concurrently without interfering with each other.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"]
                               if is_rust_accelerated(comp)]

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
                game_root_name=mock_yamldata.game_root_name
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
            assert not str(result).startswith("Error:"), \
                f"Component {component} failed in concurrent execution: {result}"
            assert result is not None, f"Component {component} returned None"


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
    def large_crash_data(self) -> List[str]:
        """Generate large crash data for performance testing."""
        base_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            "PROBABLE CALL STACK:",
        ]

        # Add many call stack entries with FormIDs
        for i in range(1000):
            base_data.append(f"\t[{i}] 0x7FF66DF{i:05X} -> FormID: 0x{i:08X}")

        base_data.extend([
            "",
            "PLUGINS:",
        ])

        # Add many plugins
        for i in range(200):
            base_data.append(f"\t[{i:02X}] Plugin{i:03d}.esp")

        return base_data

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Mock YAML data for performance testing."""
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

    def test_component_pipeline_performance(self, large_crash_data, mock_yamldata):
        """
        Test performance of the complete component pipeline.

        Measures the time it takes to process large crash data through
        all available Rust components and validates performance targets.
        """
        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"]
                               if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for performance testing")

        component_times = {}

        # Measure parser performance
        if "parser" in available_components:
            parser = get_parser()

            with PerformanceTimer() as timer:
                result = parser.find_segments(
                    crash_data=large_crash_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name
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
        logging.info(f"Component pipeline performance:")
        for component, time_taken in component_times.items():
            logging.info(f"  {component}: {time_taken:.3f}s")
        logging.info(f"  Total: {total_time:.3f}s")

        # Total pipeline should be very fast even with large data
        assert total_time < 0.2, f"Total pipeline too slow: {total_time:.3f}s"

    def test_memory_usage_stability(self, large_crash_data, mock_yamldata):
        """
        Test that component interactions don't cause memory leaks.

        Runs the component pipeline multiple times and validates
        that memory usage remains stable.
        """
        import psutil
        import os

        available_components = [comp for comp in ["parser", "formid_analyzer", "plugin_analyzer"]
                               if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for memory testing")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Run pipeline multiple times
        for iteration in range(10):
            if "parser" in available_components:
                parser = get_parser()
                result = parser.find_segments(
                    crash_data=large_crash_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name
                )
                segments = result[3]

            if "formid_analyzer" in available_components and segments:
                formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)
                callstack = segments[2] if len(segments) > 2 else large_crash_data
                formids = formid_analyzer.extract_formids(callstack)

            if "plugin_analyzer" in available_components:
                plugin_analyzer = get_plugin_analyzer(mock_yamldata)
                plugin_data = segments[-1] if segments else large_crash_data
                plugins, _, _ = plugin_analyzer.loadorder_scan_log(plugin_data)

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal (< 10MB)
        max_growth = 10 * 1024 * 1024  # 10MB
        assert memory_growth < max_growth, \
            f"Excessive memory growth: {memory_growth / 1024 / 1024:.1f}MB"


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

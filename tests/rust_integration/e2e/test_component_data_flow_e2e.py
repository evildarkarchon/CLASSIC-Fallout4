"""
Component data flow tests for Phase 6 Rust migration validation.

This module tests how data flows between Rust components, validating that
the output of one component is properly formatted for consumption by the
next component in the pipeline.

Key Integration Points Tested:
- Data flow between LogParser -> FormIDAnalyzer
- Data flow between LogParser -> PluginAnalyzer
- Data flow between LogParser -> RecordScanner
- Complete integrated component chain
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
    get_record_scanner,
)
from ClassicLib.integration.status import (
    is_rust_accelerated,
)

# Status imports
from tests.test_infra.performance_utils import PerformanceTimer

logger = logging.getLogger(__name__)


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
    def sample_crash_data(self) -> list[str]:
        """
        Provide sample crash log data for component testing.

        Returns a comprehensive crash log with all sections needed
        for testing component interactions.
        """
        return [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF66DF19300 Fallout4.exe+0DB9300',
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
            "\t[07] ProblematicPlugin.esp",
        ]

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
        _, _, _, segments = parser.find_segments(
            crash_data=sample_crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name,
        )

        # Validate parser output structure
        assert isinstance(segments, list), "Segments should be a list"
        assert len(segments) >= 3, "Should have at least 3 segments (compatibility, system, callstack)"

        # Extract call stack segment (typically index 2)
        callstack_segment = segments[2] if len(segments) > 2 else []

        # Pass to FormID analyzer
        formid_analyzer = get_formid_analyzer(yamldata=mock_yamldata, show_values=True, db_exists=True)

        formids = formid_analyzer.extract_formids(callstack_segment)

        # Validate FormID extraction results
        assert isinstance(formids, list), "FormIDs should be returned as list"

        # Should find the FormIDs in our test data
        expected_formids = ["12345678", "ABCDEF01"]
        for expected_formid in expected_formids:
            assert any(expected_formid in formid for formid in formids), f"Expected FormID {expected_formid} not found in {formids}"

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
            game_root_name=mock_yamldata.game_root_name,
        )

        # Extract plugins segment (typically the last segment)
        plugins_segment = segments[-1] if segments else []

        # Pass to Plugin analyzer
        plugin_analyzer = get_plugin_analyzer(mock_yamldata)

        plugins_dict, _, _ = plugin_analyzer.loadorder_scan_log(segment_plugins=plugins_segment)

        # Validate plugin analysis results
        assert isinstance(plugins_dict, dict), "Plugins should be returned as dict"

        # Should find expected plugins from test data
        expected_plugins = ["Fallout4.esm", "TestPlugin.esp", "AnotherMod.esp"]
        found_plugins = list(plugins_dict.keys())  # Check KEYS (plugin names), not values (indexes)

        for expected_plugin in expected_plugins:
            assert any(expected_plugin in plugin for plugin in found_plugins), (
                f"Expected plugin {expected_plugin} not found in {found_plugins}"
            )

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
            game_root_name=mock_yamldata.game_root_name,
        )

        # Extract call stack segment
        callstack_segment = segments[2] if len(segments) > 2 else []

        # Pass to Record scanner
        record_scanner = get_record_scanner(mock_yamldata)

        _, matches = record_scanner.scan_named_records(callstack_segment)

        # Validate record scanning results
        assert isinstance(matches, list), "Matches should be returned as list"

        # Should find the record types in our test data
        expected_records = ["BGSKeyword", "TESForm"]
        for expected_record in expected_records:
            assert any(expected_record in match for match in matches), f"Expected record {expected_record} not found in {matches}"

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
            _, _, _, segments = parser.find_segments(
                crash_data=sample_crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name,
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
                results["plugins"], _, _ = plugin_analyzer.loadorder_scan_log(plugins_segment)

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
                    assert any(plugin_ref in plugin for plugin in plugin_names), f"FormID references unknown plugin: {plugin_ref}"

        logger.info(f"Complete component chain processing time: {timer.elapsed:.3f}s")


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

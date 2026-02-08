"""
Component error handling tests for Phase 6 Rust migration validation.

This module tests error handling and recovery mechanisms between components,
validating that errors in one component don't cascade and break other
components, and that proper fallback mechanisms are in place.

Key Integration Points Tested:
- Parser error isolation
- FormID analyzer error recovery
- Plugin analyzer error resilience
- Error propagation through component chain
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
    is_rust_accelerated,
)

logger = logging.getLogger(__name__)


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
    def corrupted_crash_data(self) -> list[str]:
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
                game_root_name=mock_yamldata.game_root_name,
            )

            # Should still return structured data even with corruption
            assert isinstance(segments, list), "Should return list even with corrupted data"
            assert game_version is not None, "Should return some game version"
            assert crashgen_version is not None, "Should return some crashgen version"
            assert main_error is not None, "Should return some error info"

        except Exception as e:
            # If parser does fail, it should be a controlled failure, not a crash
            assert "corrupted" in str(e).lower() or "invalid" in str(e).lower(), f"Parser error should indicate data corruption: {e}"

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
            # Rust implementation returns "Form ID: XXXXXXXX" (no 0x prefix in value)
            valid_matches = [fid for fid in formids if "12345678" in fid or "ABCDEF01" in fid]
            assert len(valid_matches) > 0, "Should extract at least some valid FormIDs"

        except Exception as e:
            # If it does fail, should be a controlled failure
            assert "invalid" in str(e).lower() or "malformed" in str(e).lower(), f"FormID analyzer error should indicate data issues: {e}"

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
            # Check KEYS for plugin names
            valid_plugins = [p for p in plugins_dict if p and ".es" in p]
            assert len(valid_plugins) > 0, "Should extract at least some valid plugins"

        except Exception as e:
            # If it does fail, should be controlled
            assert "invalid" in str(e).lower() or "malformed" in str(e).lower(), f"Plugin analyzer error should indicate data issues: {e}"

    def test_component_chain_error_propagation(self, corrupted_crash_data, mock_yamldata):
        """
        Test error propagation through the component chain.

        Validates that an error in one component doesn't prevent
        other components from processing what data they can.
        """
        available_components = [
            comp for comp in ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"] if is_rust_accelerated(comp)
        ]

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
                    game_root_name=mock_yamldata.game_root_name,
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

        if "record_scanner" in available_components and segments:
            try:
                record_scanner = get_record_scanner(mock_yamldata)
                callstack = segments[0] if segments else corrupted_crash_data
                results["record_scanner"] = record_scanner.scan_named_records(callstack)
            except Exception as e:
                errors["record_scanner"] = str(e)

        # At least some components should either succeed or fail gracefully
        total_attempts = len(available_components)
        successful_results = len(results)
        controlled_errors = len([e for e in errors.values() if "invalid" in e.lower() or "malformed" in e.lower()])

        assert (successful_results + controlled_errors) == total_attempts, (
            f"Components should either succeed or fail gracefully. Results: {results}, Errors: {errors}"
        )


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])

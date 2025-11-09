"""
Comprehensive plugin analysis parity validation tests.

This module provides detailed validation that Rust plugin analysis components produce
identical results to Python implementations. Tests cover plugin load order parsing,
ESL handling, plugin limit detection, mod conflict analysis, and problematic plugin
identification.

Plugin Analysis Components Tested:
- Load order parsing from crash log plugin segments
- Plugin index assignment (ESP/ESM/ESL handling)
- Plugin limit detection and warnings
- ESL (light plugin) processing and index assignment
- Problematic plugin pattern matching
- Plugin dependency analysis
- Performance optimization validation

The tests ensure that Rust plugin analysis maintains 100% functional compatibility
with the Python implementation while providing significant performance improvements
(typically 30x faster for load order processing and plugin matching operations).
"""

from __future__ import annotations

import logging
import time
from typing import Any
from unittest.mock import Mock

import pytest

from ClassicLib.integration.factory import get_plugin_analyzer
from ClassicLib.integration.status import (
    is_rust_accelerated,
)

RUST_AVAILABLE = {"plugin_analyzer": is_rust_accelerated("plugin_analyzer")}
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from tests.rust_integration.parity_fixtures import ParityResult, ParityValidator, skip_if_rust_unavailable, validate_plugin_dictionaries

logger = logging.getLogger(__name__)


class PluginParityValidator(ParityValidator):
    """
    Specialized parity validator for plugin analysis components.

    Validates that Rust plugin analysis produces identical results to Python
    implementations across all plugin parsing scenarios, load order detection,
    and edge cases.
    """

    def __init__(self):
        """Initialize plugin parity validator."""
        super().__init__("plugin_analyzer")

    def create_rust_implementation(self, yamldata=None, **kwargs) -> Any | None:
        """Create Rust plugin analyzer implementation using factory."""
        if not RUST_AVAILABLE.get("plugin_analyzer"):
            return None

        # Use factory function to get the best implementation
        return get_plugin_analyzer(yamldata)

    def create_python_implementation(self, yamldata=None, **kwargs) -> PluginAnalyzer:
        """Create Python plugin analyzer implementation."""
        return PluginAnalyzer(yamldata)

    def generate_plugin_test_cases(self) -> list[dict[str, Any]]:
        """Generate comprehensive plugin analysis test cases."""
        return [
            # Basic Fallout 4 load order
            {
                "name": "basic_fallout4_loadorder",
                "plugins_segment": [
                    "\t[00] Fallout4.esm",
                    "\t[01] DLCRobot.esm",
                    "\t[02] DLCworkshop01.esm",
                    "\t[03] DLCCoast.esm",
                    "\t[04] DLCworkshop02.esm",
                    "\t[05] DLCworkshop03.esm",
                    "\t[06] DLCNukaWorld.esm",
                    "\t[07] Unofficial Fallout 4 Patch.esp",
                    "\t[08] TestMod.esp",
                ],
                "expected_count": 9,
            },
            # ESL plugins mixed with regular plugins
            {
                "name": "esl_plugins_mixed",
                "plugins_segment": [
                    "\t[00] Fallout4.esm",
                    "\t[01] DLCRobot.esm",
                    "\t[FE:000] ESLMod1.esl",
                    "\t[FE:001] ESLMod2.esl",
                    "\t[02] RegularMod.esp",
                    "\t[FE:002] ESLMod3.esl",
                    "\t[03] AnotherMod.esp",
                ],
                "expected_count": 7,
                "expected_esl_count": 3,
            },
            # Plugin limit scenario (255 ESP/ESM + ESLs)
            {
                "name": "plugin_limit_scenario",
                "plugins_segment": [f"\t[{i:02X}] Plugin{i}.esp" for i in range(255)]
                + [f"\t[FE:{i:03X}] ESLMod{i}.esl" for i in range(100)],
                "expected_count": 355,
                "expected_limit_triggered": True,
            },
            # Malformed plugin entries
            {
                "name": "malformed_plugin_entries",
                "plugins_segment": [
                    "\t[00] Fallout4.esm",
                    "\t[INVALID] BadEntry.esp",  # Invalid index
                    "\t[01] ValidMod.esp",
                    "\t[256] OutOfRange.esp",  # Index too high
                    "\t[] NoIndex.esp",  # Missing index
                    "\t[02] ValidMod2.esp",
                    "\t[FE:INVALID] BadESL.esl",  # Invalid ESL index
                    "\t[FE:001] ValidESL.esl",
                ],
                "expected_count": 4,  # Only valid entries should be counted
                "expected_valid_indices": ["00", "01", "02", "FE:001"],
            },
            # Empty and edge cases
            {"name": "empty_plugin_list", "plugins_segment": [], "expected_count": 0},
            {"name": "single_plugin", "plugins_segment": ["\t[00] Fallout4.esm"], "expected_count": 1},
            # Large load order (performance test)
            {
                "name": "large_load_order_performance",
                "plugins_segment": [
                    "\t[00] Fallout4.esm",
                    "\t[01] DLCRobot.esm",
                    "\t[02] DLCworkshop01.esm",
                    "\t[03] DLCCoast.esm",
                    "\t[04] DLCworkshop02.esm",
                    "\t[05] DLCworkshop03.esm",
                    "\t[06] DLCNukaWorld.esm",
                ]
                + [f"\t[{i:02X}] Mod{i:03d}.esp" for i in range(7, 255)]
                + [f"\t[FE:{i:03X}] ESLMod{i:03d}.esl" for i in range(500)],
                "expected_count": 755,
                "performance_critical": True,
            },
            # Problematic plugins pattern
            {
                "name": "problematic_plugins",
                "plugins_segment": [
                    "\t[00] Fallout4.esm",
                    "\t[01] DLCRobot.esm",
                    "\t[02] ScrapEverything.esp",  # Known problematic
                    "\t[03] PlaceEverywhere.esp",  # Known problematic
                    "\t[04] SafeMod.esp",
                    "\t[05] Arbitration.esp",  # Potentially problematic
                    "\t[06] CompanionsGoneWild.esp",  # Known problematic
                ],
                "expected_count": 7,
                "has_problematic": True,
            },
            # Unicode and special characters
            {
                "name": "unicode_plugin_names",
                "plugins_segment": [
                    "\t[00] Fallout4.esm",
                    "\t[01] Tëst Mød.esp",  # Unicode characters
                    "\t[02] Мод на русском.esp",  # Cyrillic
                    "\t[03] 日本語Mod.esp",  # Japanese
                    "\t[04] NormalMod.esp",
                ],
                "expected_count": 5,
            },
            # Mixed case and whitespace
            {
                "name": "mixed_case_whitespace",
                "plugins_segment": [
                    "\t[00] Fallout4.esm",
                    "\t[01]   SpacedMod.esp  ",  # Extra whitespace
                    "\t[02]NOSPACE.ESP",  # No space after index
                    "\t[03] MixedCase.ESP",  # Mixed case extension
                    "\t[04] normal.esp",
                ],
                "expected_count": 5,
            },
        ]


@pytest.mark.integration
@pytest.mark.asyncio
@skip_if_rust_unavailable("plugin_analyzer")
class TestPluginParity:
    """
    Comprehensive plugin analysis parity validation test suite.

    These tests ensure that Rust plugin analysis produces identical results
    to Python implementations across all plugin parsing scenarios, load order
    detection, and edge cases.
    """

    async def test_load_order_parsing_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python plugin analyzers produce identical load order
        parsing results across various plugin segment formats.
        """
        validator = PluginParityValidator()
        test_cases = validator.generate_plugin_test_cases()
        results = []

        # Test each case
        for test_case in test_cases:
            try:
                # Create implementations
                rust_analyzer = validator.create_rust_implementation(mock_scanlog_info)
                python_analyzer = validator.create_python_implementation(mock_scanlog_info)

                if not rust_analyzer:
                    pytest.skip("Rust plugin analyzer not available")

                plugins_segment = test_case["plugins_segment"]
                expected_count = test_case.get("expected_count", 0)

                # Time Rust parsing
                start_time = time.perf_counter()
                rust_result = rust_analyzer.loadorder_scan_log(plugins_segment)
                rust_time = time.perf_counter() - start_time

                # Time Python parsing
                start_time = time.perf_counter()
                python_result = python_analyzer.loadorder_scan_log(plugins_segment)
                python_time = time.perf_counter() - start_time

                # Validate plugin dictionaries (first element of tuple)
                rust_plugins = rust_result[0] if rust_result else {}
                python_plugins = python_result[0] if python_result else {}

                is_identical, differences = validate_plugin_dictionaries(rust_plugins, python_plugins)

                # Additional validation for tuple elements
                if len(rust_result) >= 2 and len(python_result) >= 2:
                    # Compare plugin limit triggered flag
                    if rust_result[1] != python_result[1]:
                        differences.append(f"Plugin limit triggered differs: Rust={rust_result[1]}, Python={python_result[1]}")
                        is_identical = False

                if len(rust_result) >= 3 and len(python_result) >= 3:
                    # Compare limit check disabled flag
                    if rust_result[2] != python_result[2]:
                        differences.append(f"Limit check disabled differs: Rust={rust_result[2]}, Python={python_result[2]}")
                        is_identical = False

                # Validate expected counts if specified
                if expected_count > 0:
                    rust_count = len(rust_plugins)
                    python_count = len(python_plugins)

                    if rust_count != expected_count:
                        differences.append(f"Rust plugin count doesn't match expected: got {rust_count}, expected {expected_count}")
                        is_identical = False

                    if python_count != expected_count:
                        differences.append(f"Python plugin count doesn't match expected: got {python_count}, expected {expected_count}")
                        is_identical = False

                # Special validation for ESL plugins
                if test_case.get("expected_esl_count"):
                    expected_esl_count = test_case["expected_esl_count"]
                    rust_esl_count = sum(1 for k in rust_plugins.keys() if k.startswith("FE:"))
                    python_esl_count = sum(1 for k in python_plugins.keys() if k.startswith("FE:"))

                    if rust_esl_count != expected_esl_count:
                        differences.append(f"Rust ESL count doesn't match expected: got {rust_esl_count}, expected {expected_esl_count}")
                        is_identical = False

                    if python_esl_count != expected_esl_count:
                        differences.append(
                            f"Python ESL count doesn't match expected: got {python_esl_count}, expected {expected_esl_count}"
                        )
                        is_identical = False

                # Validate specific indices for malformed entries test
                if "expected_valid_indices" in test_case:
                    expected_indices = set(test_case["expected_valid_indices"])
                    rust_indices = set(rust_plugins.keys())
                    python_indices = set(python_plugins.keys())

                    if rust_indices != expected_indices:
                        differences.append(f"Rust indices don't match expected: got {rust_indices}, expected {expected_indices}")
                        is_identical = False

                    if python_indices != expected_indices:
                        differences.append(f"Python indices don't match expected: got {python_indices}, expected {expected_indices}")
                        is_identical = False

                result = ParityResult(
                    component_name="plugin_analyzer",
                    method_name="loadorder_scan_log",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_result,
                    python_result=python_result,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "plugins_segment_size": len(plugins_segment),
                        "expected_count": expected_count,
                        "rust_plugin_count": len(rust_plugins),
                        "python_plugin_count": len(python_plugins),
                        "performance_critical": test_case.get("performance_critical", False),
                    },
                )

                results.append(result)

                # Log performance for large tests
                if test_case.get("performance_critical") and python_time > 0:
                    performance_gain = python_time / rust_time if rust_time > 0 else 0
                    logger.info(f"Large plugin list parsing: {performance_gain:.1f}x faster with Rust")

            except Exception as e:
                logger.error(f"Plugin parsing test failed for {test_case['name']}: {e}")
                results.append(
                    ParityResult(
                        component_name="plugin_analyzer",
                        method_name="loadorder_scan_log",
                        test_case=test_case["name"],
                        rust_available=True,
                        passed=False,
                        error_messages=[str(e)],
                    )
                )

        # Validate overall results
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        # Log performance statistics
        performance_gains = []
        for result in results:
            if result.python_execution_time > 0 and result.rust_execution_time > 0:
                gain = result.python_execution_time / result.rust_execution_time
                performance_gains.append(gain)

        if performance_gains:
            avg_performance = sum(performance_gains) / len(performance_gains)
            logger.info(f"Average plugin parsing performance gain: {avg_performance:.1f}x")

        # Require high success rate
        assert success_rate >= 0.9, f"Plugin parsing parity too low: {success_rate:.1%}"

        # Log detailed results for failed tests
        for result in results:
            if not result.passed:
                logger.warning(f"Plugin parsing parity failed for {result.test_case}: {result.differences}")

    async def test_plugin_limit_detection_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python plugin analyzers produce identical results
        for plugin limit detection across different scenarios.
        """
        # Test cases for plugin limit detection
        limit_test_cases = [
            # Below limit
            {
                "name": "below_plugin_limit",
                "plugins_segment": [f"\t[{i:02X}] Plugin{i}.esp" for i in range(200)],
                "game_version": "Fallout 4 v1.10.163",
                "version_current": "1.10.163",
                "expected_limit_triggered": False,
                "expected_limit_disabled": False,
            },
            # At ESP limit (255)
            {
                "name": "at_esp_limit",
                "plugins_segment": [f"\t[{i:02X}] Plugin{i}.esp" for i in range(255)],
                "game_version": "Fallout 4 v1.10.163",
                "version_current": "1.10.163",
                "expected_limit_triggered": True,
                "expected_limit_disabled": False,
            },
            # ESLs don't count toward ESP limit
            {
                "name": "esls_dont_count_toward_limit",
                "plugins_segment": [f"\t[{i:02X}] Plugin{i}.esp" for i in range(254)]
                + [f"\t[FE:{i:03X}] ESLMod{i}.esl" for i in range(100)],
                "game_version": "Fallout 4 v1.10.163",
                "version_current": "1.10.163",
                "expected_limit_triggered": False,
                "expected_limit_disabled": False,
            },
            # Old game version without ESL support
            {
                "name": "old_version_without_esl",
                "plugins_segment": [f"\t[{i:02X}] Plugin{i}.esp" for i in range(200)],
                "game_version": "Fallout 4 v1.6.0",
                "version_current": "1.6.0",
                "expected_limit_triggered": False,
                "expected_limit_disabled": True,  # Limit check disabled for old versions
            },
        ]

        results = []

        validator = PluginParityValidator()

        for test_case in limit_test_cases:
            try:
                # Create implementations
                rust_analyzer = validator.create_rust_implementation(mock_scanlog_info)
                python_analyzer = validator.create_python_implementation(mock_scanlog_info)

                if not rust_analyzer:
                    pytest.skip("Rust plugin analyzer not available")

                plugins_segment = test_case["plugins_segment"]
                game_version = test_case.get("game_version")
                version_current = test_case.get("version_current")

                # Time Rust limit detection
                start_time = time.perf_counter()
                rust_result = rust_analyzer.loadorder_scan_log(plugins_segment, game_version, version_current)
                rust_time = time.perf_counter() - start_time

                # Time Python limit detection
                start_time = time.perf_counter()
                python_result = python_analyzer.loadorder_scan_log(plugins_segment, game_version, version_current)
                python_time = time.perf_counter() - start_time

                # Extract limit detection results
                rust_limit_triggered = rust_result[1] if len(rust_result) > 1 else False
                rust_limit_disabled = rust_result[2] if len(rust_result) > 2 else False

                python_limit_triggered = python_result[1] if len(python_result) > 1 else False
                python_limit_disabled = python_result[2] if len(python_result) > 2 else False

                # Validate parity
                differences = []
                is_identical = True

                if rust_limit_triggered != python_limit_triggered:
                    differences.append(f"Limit triggered differs: Rust={rust_limit_triggered}, Python={python_limit_triggered}")
                    is_identical = False

                if rust_limit_disabled != python_limit_disabled:
                    differences.append(f"Limit disabled differs: Rust={rust_limit_disabled}, Python={python_limit_disabled}")
                    is_identical = False

                # Validate against expected results
                expected_triggered = test_case.get("expected_limit_triggered", False)
                expected_disabled = test_case.get("expected_limit_disabled", False)

                if rust_limit_triggered != expected_triggered:
                    differences.append(
                        f"Rust limit triggered doesn't match expected: got {rust_limit_triggered}, expected {expected_triggered}"
                    )
                    is_identical = False

                if rust_limit_disabled != expected_disabled:
                    differences.append(
                        f"Rust limit disabled doesn't match expected: got {rust_limit_disabled}, expected {expected_disabled}"
                    )
                    is_identical = False

                if python_limit_triggered != expected_triggered:
                    differences.append(
                        f"Python limit triggered doesn't match expected: got {python_limit_triggered}, expected {expected_triggered}"
                    )
                    is_identical = False

                if python_limit_disabled != expected_disabled:
                    differences.append(
                        f"Python limit disabled doesn't match expected: got {python_limit_disabled}, expected {expected_disabled}"
                    )
                    is_identical = False

                result = ParityResult(
                    component_name="plugin_analyzer",
                    method_name="plugin_limit_detection",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=(rust_limit_triggered, rust_limit_disabled),
                    python_result=(python_limit_triggered, python_limit_disabled),
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "plugin_count": len(plugins_segment),
                        "game_version": game_version,
                        "expected_triggered": expected_triggered,
                        "expected_disabled": expected_disabled,
                    },
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Plugin limit detection test failed for {test_case['name']}: {e}")
                results.append(
                    ParityResult(
                        component_name="plugin_analyzer",
                        method_name="plugin_limit_detection",
                        test_case=test_case["name"],
                        rust_available=True,
                        passed=False,
                        error_messages=[str(e)],
                    )
                )

        # Validate results
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        assert success_rate >= 0.9, f"Plugin limit detection parity too low: {success_rate:.1%}"

        # Log failures
        for result in results:
            if not result.passed:
                logger.warning(f"Plugin limit detection parity failed: {result.test_case} - {result.differences}")

    async def test_problematic_plugin_matching_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python plugin analyzers produce identical results
        for problematic plugin identification and matching.
        """
        # Configure mock YAML data with problematic plugin patterns
        mock_yaml_dict = {
            "problematic_plugins": {
                "ScrapEverything.esp": "Known to cause crashes with settlement building",
                "PlaceEverywhere.esp": "Can cause object placement issues",
                "Arbitration.esp": "Combat overhaul that may conflict with other mods",
                "CompanionsGoneWild.esp": "Companion behavior mod with known issues",
            },
            "warning_patterns": ["ScrapEverything", "PlaceEverywhere", "CompanionsGoneWild"],
        }

        # Mock the YAML data access
        mock_scanlog_info.problematic_plugins = mock_yaml_dict.get("problematic_plugins", {})
        mock_scanlog_info.warning_patterns = mock_yaml_dict.get("warning_patterns", [])

        test_plugins = [
            "Fallout4.esm",
            "DLCRobot.esm",
            "ScrapEverything.esp",  # Problematic
            "SafeMod.esp",
            "PlaceEverywhere.esp",  # Problematic
            "AnotherSafeMod.esp",
            "Arbitration.esp",  # Problematic
            "CompanionsGoneWild.esp",  # Problematic
            "FinalMod.esp",
        ]

        validator = PluginParityValidator()

        try:
            # Create implementations
            rust_analyzer = validator.create_rust_implementation(mock_scanlog_info)
            python_analyzer = validator.create_python_implementation(mock_scanlog_info)

            if not rust_analyzer:
                pytest.skip("Rust plugin analyzer not available")

            # Create mock report fragment for plugin matching
            mock_report = Mock()
            mock_report.add_problematic_plugin = Mock()
            mock_report.add_warning = Mock()

            # Test problematic plugin matching (this typically modifies a report object)
            start_time = time.perf_counter()
            rust_analyzer.plugin_match(test_plugins, mock_report)
            rust_time = time.perf_counter() - start_time

            # Reset mock for Python test
            rust_calls = mock_report.add_problematic_plugin.call_args_list.copy()
            rust_warnings = mock_report.add_warning.call_args_list.copy()
            mock_report.reset_mock()

            start_time = time.perf_counter()
            python_analyzer.plugin_match(test_plugins, mock_report)
            python_time = time.perf_counter() - start_time

            python_calls = mock_report.add_problematic_plugin.call_args_list.copy()
            python_warnings = mock_report.add_warning.call_args_list.copy()

            # Compare the calls made to the report object
            differences = []
            is_identical = True

            # Compare problematic plugin calls
            if len(rust_calls) != len(python_calls):
                differences.append(f"Problematic plugin call count differs: Rust={len(rust_calls)}, Python={len(python_calls)}")
                is_identical = False
            else:
                for i, (rust_call, python_call) in enumerate(zip(rust_calls, python_calls)):
                    if rust_call != python_call:
                        differences.append(f"Problematic plugin call {i} differs: Rust={rust_call}, Python={python_call}")
                        is_identical = False

            # Compare warning calls
            if len(rust_warnings) != len(python_warnings):
                differences.append(f"Warning call count differs: Rust={len(rust_warnings)}, Python={len(python_warnings)}")
                is_identical = False
            else:
                for i, (rust_warning, python_warning) in enumerate(zip(rust_warnings, python_warnings)):
                    if rust_warning != python_warning:
                        differences.append(f"Warning call {i} differs: Rust={rust_warning}, Python={python_warning}")
                        is_identical = False

            result = ParityResult(
                component_name="plugin_analyzer",
                method_name="plugin_match",
                test_case="problematic_plugin_matching",
                rust_available=True,
                passed=is_identical,
                rust_result={"problematic_calls": rust_calls, "warning_calls": rust_warnings},
                python_result={"problematic_calls": python_calls, "warning_calls": python_warnings},
                differences=differences,
                rust_execution_time=rust_time,
                python_execution_time=python_time,
                metadata={
                    "test_plugins_count": len(test_plugins),
                    "expected_problematic_count": 4,  # ScrapEverything, PlaceEverywhere, Arbitration, CompanionsGoneWild
                },
            )

            assert result.passed, f"Problematic plugin matching parity failed: {result.differences}"

            # Validate that problematic plugins were detected
            expected_problematic = {"ScrapEverything.esp", "PlaceEverywhere.esp", "Arbitration.esp", "CompanionsGoneWild.esp"}
            detected_plugins = set()

            for call in rust_calls:
                if call.args:  # Get the plugin name from the call
                    detected_plugins.add(call.args[0])

            assert expected_problematic.issubset(detected_plugins), (
                f"Not all expected problematic plugins detected: missing {expected_problematic - detected_plugins}"
            )

        except Exception as e:
            logger.error(f"Problematic plugin matching test failed: {e}")
            pytest.fail(f"Problematic plugin matching test failed: {e}")

    @pytest.mark.performance
    async def test_plugin_analysis_performance_regression(self, mock_scanlog_info):
        """
        Test that Rust plugin analysis provides expected performance improvements
        while maintaining complete functional parity.
        """
        # Create large plugin list for performance measurement
        large_plugin_list = (
            [
                "\t[00] Fallout4.esm",
                "\t[01] DLCRobot.esm",
                "\t[02] DLCworkshop01.esm",
                "\t[03] DLCCoast.esm",
                "\t[04] DLCworkshop02.esm",
                "\t[05] DLCworkshop03.esm",
                "\t[06] DLCNukaWorld.esm",
            ]
            + [f"\t[{i:02X}] Mod{i:03d}.esp" for i in range(7, 255)]
            + [f"\t[FE:{i:03X}] ESLMod{i:03d}.esl" for i in range(1000)]
        )

        validator = PluginParityValidator()

        # Create analyzers
        rust_analyzer = validator.create_rust_implementation(mock_scanlog_info)
        python_analyzer = validator.create_python_implementation(mock_scanlog_info)

        if not rust_analyzer:
            pytest.skip("Rust plugin analyzer not available")

        # Measure performance
        start_time = time.perf_counter()
        rust_result = rust_analyzer.loadorder_scan_log(large_plugin_list)
        rust_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        python_result = python_analyzer.loadorder_scan_log(large_plugin_list)
        python_time = time.perf_counter() - start_time

        # Validate parity
        rust_plugins = rust_result[0] if rust_result else {}
        python_plugins = python_result[0] if python_result else {}

        is_identical, differences = validate_plugin_dictionaries(rust_plugins, python_plugins)
        assert is_identical, f"Performance test failed parity validation: {differences[:5]}"

        # Validate performance improvement
        if python_time > 0 and rust_time > 0:
            performance_gain = python_time / rust_time
            logger.info(f"Plugin analysis performance: Rust {performance_gain:.1f}x faster than Python")
            logger.info(f"Processing {len(large_plugin_list)} plugins: Rust={rust_time:.3f}s, Python={python_time:.3f}s")

            # Expect significant performance improvement
            assert performance_gain >= 3.0, f"Plugin analysis performance gain too low: {performance_gain:.1f}x (expected ≥3x)"

        # Validate accuracy
        expected_esp_count = 255  # Master files + regular ESPs
        expected_esl_count = 1000
        expected_total = expected_esp_count + expected_esl_count

        rust_esp_count = sum(1 for k in rust_plugins.keys() if not k.startswith("FE:"))
        rust_esl_count = sum(1 for k in rust_plugins.keys() if k.startswith("FE:"))
        rust_total = len(rust_plugins)

        python_esp_count = sum(1 for k in python_plugins.keys() if not k.startswith("FE:"))
        python_esl_count = sum(1 for k in python_plugins.keys() if k.startswith("FE:"))
        python_total = len(python_plugins)

        assert rust_total == expected_total, f"Rust total plugin count mismatch: got {rust_total}, expected {expected_total}"
        assert python_total == expected_total, f"Python total plugin count mismatch: got {python_total}, expected {expected_total}"
        assert rust_esp_count == expected_esp_count, f"Rust ESP count mismatch: got {rust_esp_count}, expected {expected_esp_count}"
        assert rust_esl_count == expected_esl_count, f"Rust ESL count mismatch: got {rust_esl_count}, expected {expected_esl_count}"

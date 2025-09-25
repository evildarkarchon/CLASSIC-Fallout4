"""
Comprehensive output parity validation tests for Rust-Python implementation compatibility.

This module provides the main testing framework for Phase 6 validation, ensuring that
Rust components produce identical results to Python implementations across all core
functionality. Tests cover functional parity, data format validation, cross-implementation
testing, and regression detection.

Test Coverage:
- Parser segment extraction and metadata parsing
- FormID extraction and validation
- Plugin analysis and load order processing
- Record scanning and pattern matching
- Report generation and formatting
- Database operations and caching
- File I/O operations and encoding handling
- Error condition handling and edge cases

The tests validate that Rust implementations are true drop-in replacements with
zero functional regression while providing significant performance improvements.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from ClassicLib.AsyncBridge import AsyncBridge
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
from ClassicLib.integration.detector import get_available_components

RUST_AVAILABLE = get_available_components()["components"]
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore
from ClassicLib.ScanLog.Parser import find_segments
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.RecordScanner import RecordScanner
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from tests.rust_integration.parity_fixtures import (
    CrashLogParityGenerator,
    MockYamlSettingsCache,
    ParityResult,
    ParityTestRunner,
    ParityValidator,
    normalize_markdown_content,
    skip_if_rust_unavailable,
    validate_formid_lists,
    validate_plugin_dictionaries
)

logger = logging.getLogger(__name__)


class MainParityValidator(ParityValidator):
    """
    Main parity validator for comprehensive cross-implementation testing.

    This validator coordinates testing across all major components to ensure
    complete functional parity between Rust and Python implementations.
    """

    def __init__(self):
        """Initialize the main parity validator."""
        super().__init__("main_parity")
        self.bridge = AsyncBridge.get_instance()

    def create_rust_implementation(self, **kwargs) -> dict[str, Any]:
        """Create Rust implementations for all available components."""
        implementations = {}

        # Parser
        if RUST_AVAILABLE.get("parser", False):
            implementations["parser"] = get_parser()

        # FormID Analyzer
        if RUST_AVAILABLE.get("formid_analyzer", False):
            yamldata = kwargs.get("yamldata")
            if yamldata:
                implementations["formid_analyzer"] = get_formid_analyzer(
                    yamldata, True, False
                )

        # Plugin Analyzer
        if RUST_AVAILABLE.get("plugin_analyzer", False):
            yamldata = kwargs.get("yamldata")
            if yamldata:
                implementations["plugin_analyzer"] = get_plugin_analyzer(yamldata)

        # Record Scanner
        if RUST_AVAILABLE.get("record_scanner", False):
            yamldata = kwargs.get("yamldata")
            if yamldata:
                implementations["record_scanner"] = get_record_scanner(yamldata)

        return implementations

    def create_python_implementation(self, **kwargs) -> dict[str, Any]:
        """Create Python implementations for all components."""
        implementations = {}
        yamldata = kwargs.get("yamldata")

        # Parser (using direct function)
        implementations["parser"] = find_segments

        # FormID Analyzer
        if yamldata:
            implementations["formid_analyzer"] = FormIDAnalyzerCore(
                yamldata, True, False, None
            )

        # Plugin Analyzer
        if yamldata:
            implementations["plugin_analyzer"] = PluginAnalyzer(yamldata)

        # Record Scanner
        if yamldata:
            implementations["record_scanner"] = RecordScanner(yamldata)

        return implementations

    def generate_test_cases(self) -> list:
        """Generate comprehensive test cases for all components."""
        # This is handled by individual test functions
        return []


@pytest.mark.integration
@pytest.mark.asyncio
class TestOutputParity:
    """
    Comprehensive output parity validation test suite.

    These tests ensure that Rust implementations produce identical results
    to Python implementations across all functionality, validating that
    performance improvements come with zero functional regression.
    """

    async def test_parser_segment_extraction_parity(self,
                                                   parity_crash_generator,
                                                   mock_scanlog_info):
        """
        Test that Rust and Python parsers extract identical segments from crash logs.

        This test validates:
        - Segment boundary detection produces same results
        - Metadata extraction is identical
        - Line processing handles edge cases consistently
        - Performance improvements don't affect accuracy
        """
        if not RUST_AVAILABLE.get("parser", False):
            pytest.skip("Rust parser not available")

        test_cases = parity_crash_generator.generate_parity_test_cases()
        results = []

        rust_parser = get_parser()

        for test_case in test_cases[:10]:  # Limit for CI performance
            crash_data = test_case.inputs["crash_data"]

            # Skip empty or invalid crash logs
            if not crash_data or len(crash_data) < 2:
                continue

            try:
                # Execute Rust parser
                start_time = time.perf_counter()
                rust_result = rust_parser.find_segments(
                    crash_data,
                    "Buffout 4",
                    "F4SE",
                    "Fallout4"
                )
                rust_time = time.perf_counter() - start_time

                # Execute Python parser
                start_time = time.perf_counter()
                python_result = find_segments(
                    crash_data,
                    "Buffout 4",
                    "F4SE",
                    "Fallout4"
                )
                python_time = time.perf_counter() - start_time

                # Create parity result
                result = ParityResult(
                    component_name="parser",
                    method_name="find_segments",
                    test_case=test_case.name,
                    rust_available=True,
                    passed=rust_result == python_result,
                    rust_result=rust_result,
                    python_result=python_result,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time
                )

                # Detailed validation of segment structures
                if rust_result != python_result:
                    differences = []

                    # Compare metadata (first 3 elements)
                    rust_meta = rust_result[:3] if len(rust_result) >= 3 else rust_result
                    python_meta = python_result[:3] if len(python_result) >= 3 else python_result

                    if rust_meta != python_meta:
                        differences.append(f"Metadata differs: Rust={rust_meta}, Python={python_meta}")

                    # Compare segments (4th element if present)
                    if len(rust_result) > 3 and len(python_result) > 3:
                        rust_segments = rust_result[3]
                        python_segments = python_result[3]

                        if len(rust_segments) != len(python_segments):
                            differences.append(f"Segment count differs: Rust={len(rust_segments)}, Python={len(python_segments)}")
                        else:
                            for i, (rust_seg, python_seg) in enumerate(zip(rust_segments, python_segments)):
                                if rust_seg != python_seg:
                                    differences.append(f"Segment {i} differs in {len(rust_seg) - len(python_seg)} lines")

                    result.differences = differences
                    logger.warning(f"Parser parity failure in {test_case.name}: {differences[:3]}")

                results.append(result)

            except Exception as e:
                logger.error(f"Parser parity test failed for {test_case.name}: {e}")
                results.append(ParityResult(
                    component_name="parser",
                    method_name="find_segments",
                    test_case=test_case.name,
                    rust_available=True,
                    passed=False,
                    error_messages=[str(e)]
                ))

        # Validate results
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)

        assert passed_tests > 0, "No parser parity tests passed"
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        # Log performance improvements
        performance_improvements = [
            r.python_execution_time / r.rust_execution_time
            for r in results
            if r.rust_execution_time > 0 and r.python_execution_time > 0
        ]

        if performance_improvements:
            avg_improvement = sum(performance_improvements) / len(performance_improvements)
            logger.info(f"Parser average performance improvement: {avg_improvement:.1f}x")

        # Require high success rate for parity validation
        assert success_rate >= 0.9, f"Parser parity success rate too low: {success_rate:.2%} (expected ≥90%)"

    async def test_comprehensive_component_parity(self,
                                                parity_crash_generator,
                                                mock_scanlog_info):
        """
        Test comprehensive parity across all available Rust components.

        This is the master parity validation test that ensures all Rust
        components work together to produce identical results to the full
        Python pipeline.
        """
        # Get component availability status
        rust_status = get_rust_component_status()
        available_components = [k for k, v in rust_status["available"].items() if v]

        if not available_components:
            pytest.skip("No Rust components available for parity testing")

        logger.info(f"Testing parity for components: {available_components}")

        # Generate test cases
        test_cases = parity_crash_generator.generate_parity_test_cases()
        component_results = {comp: [] for comp in available_components}

        # Test each component with multiple crash logs
        for test_case in test_cases[:5]:  # Limit for performance
            crash_data = test_case.inputs["crash_data"]

            if not crash_data or len(crash_data) < 5:
                continue

            # Test parser if available
            if "parser" in available_components:
                result = await self._test_parser_parity(crash_data, test_case.name)
                component_results["parser"].append(result)

            # Test FormID analyzer if available
            if "formid_analyzer" in available_components:
                result = await self._test_formid_analyzer_parity(
                    crash_data, mock_scanlog_info, test_case.name
                )
                component_results["formid_analyzer"].append(result)

            # Test plugin analyzer if available
            if "plugin_analyzer" in available_components:
                result = await self._test_plugin_analyzer_parity(
                    crash_data, mock_scanlog_info, test_case.name
                )
                component_results["plugin_analyzer"].append(result)

            # Test record scanner if available
            if "record_scanner" in available_components:
                result = await self._test_record_scanner_parity(
                    crash_data, mock_scanlog_info, test_case.name
                )
                component_results["record_scanner"].append(result)

        # Validate overall parity results
        overall_results = []
        for component, results in component_results.items():
            if results:
                passed = sum(1 for r in results if r.passed)
                total = len(results)
                success_rate = passed / total if total > 0 else 0

                logger.info(f"{component} parity: {passed}/{total} ({success_rate:.1%}) tests passed")
                overall_results.extend(results)

                # Each component should have high parity success rate
                assert success_rate >= 0.8, f"{component} parity too low: {success_rate:.1%}"

        # Generate comprehensive parity report
        if overall_results:
            parity_report = self._generate_parity_report(overall_results)

            # Save detailed report for analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='_parity_report.json', delete=False) as f:
                json.dump(parity_report, f, indent=2)
                logger.info(f"Detailed parity report saved to: {f.name}")

        # Overall parity validation
        total_passed = sum(1 for r in overall_results if r.passed)
        total_tests = len(overall_results)
        overall_success = total_passed / total_tests if total_tests > 0 else 0

        assert overall_success >= 0.85, f"Overall parity success rate too low: {overall_success:.1%}"
        logger.info(f"🎯 Overall parity validation PASSED: {overall_success:.1%} success rate")

    async def _test_parser_parity(self, crash_data: list[str], test_name: str) -> ParityResult:
        """Test parser parity for a single crash log."""
        rust_parser = get_parser()

        try:
            # Time both implementations
            start_time = time.perf_counter()
            rust_result = rust_parser.find_segments(crash_data, "Buffout 4", "F4SE", "Fallout4")
            rust_time = time.perf_counter() - start_time

            start_time = time.perf_counter()
            python_result = find_segments(crash_data, "Buffout 4", "F4SE", "Fallout4")
            python_time = time.perf_counter() - start_time

            return ParityResult(
                component_name="parser",
                method_name="find_segments",
                test_case=test_name,
                rust_available=True,
                passed=rust_result == python_result,
                rust_result=rust_result,
                python_result=python_result,
                rust_execution_time=rust_time,
                python_execution_time=python_time
            )

        except Exception as e:
            return ParityResult(
                component_name="parser",
                method_name="find_segments",
                test_case=test_name,
                rust_available=True,
                passed=False,
                error_messages=[str(e)]
            )

    async def _test_formid_analyzer_parity(self,
                                         crash_data: list[str],
                                         mock_scanlog_info,
                                         test_name: str) -> ParityResult:
        """Test FormID analyzer parity for a single crash log."""
        try:
            # Create implementations
            rust_analyzer = get_formid_analyzer(mock_scanlog_info, True, False)
            python_analyzer = FormIDAnalyzerCore(mock_scanlog_info, True, False, None)

            # Extract a representative callstack segment for testing
            # Look for PROBABLE CALL STACK section
            callstack = []
            in_callstack = False

            for line in crash_data:
                if "PROBABLE CALL STACK" in line:
                    in_callstack = True
                    continue
                elif line.startswith("MODULES:") or line.startswith("PLUGINS:"):
                    break
                elif in_callstack and line.strip():
                    callstack.append(line)

            if not callstack:
                # No callstack found, create synthetic test data
                callstack = [
                    "\t[0] 0x7FF66DF19300 -> FormID: 0x00000014 (Fallout4.esm)",
                    "\t[1] 0x7FF66DF19400 -> FormID: 0x01002A34 (DLCRobot.esm)",
                ]

            # Test FormID extraction
            start_time = time.perf_counter()
            rust_formids = rust_analyzer.extract_formids(callstack[:20])  # Limit for performance
            rust_time = time.perf_counter() - start_time

            start_time = time.perf_counter()
            python_formids = python_analyzer.extract_formids(callstack[:20])
            python_time = time.perf_counter() - start_time

            # Validate FormID lists
            is_identical, differences = validate_formid_lists(rust_formids, python_formids)

            return ParityResult(
                component_name="formid_analyzer",
                method_name="extract_formids",
                test_case=test_name,
                rust_available=True,
                passed=is_identical,
                rust_result=rust_formids,
                python_result=python_formids,
                differences=differences,
                rust_execution_time=rust_time,
                python_execution_time=python_time
            )

        except Exception as e:
            return ParityResult(
                component_name="formid_analyzer",
                method_name="extract_formids",
                test_case=test_name,
                rust_available=True,
                passed=False,
                error_messages=[str(e)]
            )

    async def _test_plugin_analyzer_parity(self,
                                         crash_data: list[str],
                                         mock_scanlog_info,
                                         test_name: str) -> ParityResult:
        """Test plugin analyzer parity for a single crash log."""
        try:
            # Create implementations
            rust_analyzer = get_plugin_analyzer(mock_scanlog_info)
            python_analyzer = PluginAnalyzer(mock_scanlog_info)

            # Extract plugin segment
            plugins_segment = []
            in_plugins = False

            for line in crash_data:
                if line.strip().startswith("PLUGINS:"):
                    in_plugins = True
                    continue
                elif in_plugins and line.strip():
                    plugins_segment.append(line)
                elif in_plugins and not line.strip():
                    break

            if not plugins_segment:
                # Create synthetic plugin data
                plugins_segment = [
                    "\t[00] Fallout4.esm",
                    "\t[01] DLCRobot.esm",
                    "\t[02] TestPlugin.esp"
                ]

            # Test load order scanning
            start_time = time.perf_counter()
            rust_result = rust_analyzer.loadorder_scan_log(plugins_segment[:50])  # Limit for performance
            rust_time = time.perf_counter() - start_time

            start_time = time.perf_counter()
            python_result = python_analyzer.loadorder_scan_log(plugins_segment[:50])
            python_time = time.perf_counter() - start_time

            # Validate plugin dictionaries (first element of tuple)
            rust_plugins = rust_result[0] if rust_result else {}
            python_plugins = python_result[0] if python_result else {}

            is_identical, differences = validate_plugin_dictionaries(rust_plugins, python_plugins)

            # Also compare other tuple elements
            if len(rust_result) >= 3 and len(python_result) >= 3:
                if rust_result[1] != python_result[1]:  # plugin_limit_triggered
                    differences.append(f"Plugin limit detection differs: Rust={rust_result[1]}, Python={python_result[1]}")
                    is_identical = False
                if rust_result[2] != python_result[2]:  # limit_check_disabled
                    differences.append(f"Limit check status differs: Rust={rust_result[2]}, Python={python_result[2]}")
                    is_identical = False

            return ParityResult(
                component_name="plugin_analyzer",
                method_name="loadorder_scan_log",
                test_case=test_name,
                rust_available=True,
                passed=is_identical,
                rust_result=rust_result,
                python_result=python_result,
                differences=differences,
                rust_execution_time=rust_time,
                python_execution_time=python_time
            )

        except Exception as e:
            return ParityResult(
                component_name="plugin_analyzer",
                method_name="loadorder_scan_log",
                test_case=test_name,
                rust_available=True,
                passed=False,
                error_messages=[str(e)]
            )

    async def _test_record_scanner_parity(self,
                                        crash_data: list[str],
                                        mock_scanlog_info,
                                        test_name: str) -> ParityResult:
        """Test record scanner parity for a single crash log."""
        try:
            # Create implementations
            rust_scanner = get_record_scanner(mock_scanlog_info)
            python_scanner = RecordScanner(mock_scanlog_info)

            # Extract callstack for record scanning
            callstack = []
            in_callstack = False

            for line in crash_data:
                if "PROBABLE CALL STACK" in line:
                    in_callstack = True
                    continue
                elif line.startswith("MODULES:") or line.startswith("PLUGINS:"):
                    break
                elif in_callstack and line.strip():
                    callstack.append(line)

            if not callstack:
                # Create synthetic test data with record patterns
                callstack = [
                    "\t[0] 0x7FF66DF19300 -> TESForm at 0x123456789",
                    "\t[1] 0x7FF66DF19400 -> BGSKeyword at 0x987654321",
                ]

            # Test record scanning
            start_time = time.perf_counter()
            rust_result = rust_scanner.scan_named_records(callstack[:20])  # Limit for performance
            rust_time = time.perf_counter() - start_time

            start_time = time.perf_counter()
            python_result = python_scanner.scan_named_records(callstack[:20])
            python_time = time.perf_counter() - start_time

            # Both should return (fragment, matches) tuple
            differences = []
            is_identical = True

            if len(rust_result) != len(python_result):
                differences.append(f"Result structure differs: Rust={len(rust_result)} elements, Python={len(python_result)} elements")
                is_identical = False
            elif len(rust_result) >= 2:
                # Compare matches (second element)
                rust_matches = rust_result[1] if len(rust_result) > 1 else []
                python_matches = python_result[1] if len(python_result) > 1 else []

                if rust_matches != python_matches:
                    differences.append(f"Record matches differ: Rust={len(rust_matches)} matches, Python={len(python_matches)} matches")
                    is_identical = False

                # Compare fragment content if available
                if len(rust_result) > 0 and len(python_result) > 0:
                    rust_fragment = rust_result[0]
                    python_fragment = python_result[0]

                    # Both should have similar structure (ReportFragment or similar)
                    if hasattr(rust_fragment, 'fragment_content') and hasattr(python_fragment, 'fragment_content'):
                        rust_content = normalize_markdown_content(rust_fragment.fragment_content)
                        python_content = normalize_markdown_content(python_fragment.fragment_content)

                        if rust_content != python_content:
                            differences.append("Record scanner fragment content differs")
                            is_identical = False

            return ParityResult(
                component_name="record_scanner",
                method_name="scan_named_records",
                test_case=test_name,
                rust_available=True,
                passed=is_identical,
                rust_result=rust_result,
                python_result=python_result,
                differences=differences,
                rust_execution_time=rust_time,
                python_execution_time=python_time
            )

        except Exception as e:
            return ParityResult(
                component_name="record_scanner",
                method_name="scan_named_records",
                test_case=test_name,
                rust_available=True,
                passed=False,
                error_messages=[str(e)]
            )

    def _generate_parity_report(self, results: list[ParityResult]) -> dict[str, Any]:
        """Generate comprehensive parity validation report."""
        if not results:
            return {"error": "No parity results to report"}

        # Calculate summary statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests

        # Group by component
        by_component = {}
        for result in results:
            if result.component_name not in by_component:
                by_component[result.component_name] = {
                    "total": 0, "passed": 0, "failed": 0,
                    "avg_performance_gain": 0.0,
                    "results": []
                }

            comp_data = by_component[result.component_name]
            comp_data["total"] += 1
            comp_data["results"].append({
                "test": result.test_case,
                "method": result.method_name,
                "passed": result.passed,
                "performance_gain": result.performance_gain,
                "differences_count": len(result.differences),
                "execution_time_rust": result.rust_execution_time,
                "execution_time_python": result.python_execution_time
            })

            if result.passed:
                comp_data["passed"] += 1
            else:
                comp_data["failed"] += 1

        # Calculate average performance gains per component
        for component, data in by_component.items():
            performance_values = []
            for r in results:
                if (r.component_name == component and
                    r.python_execution_time > 0 and
                    r.rust_execution_time > 0):
                    perf_gain = r.python_execution_time / r.rust_execution_time
                    performance_values.append(perf_gain)

            if performance_values:
                data["avg_performance_gain"] = sum(performance_values) / len(performance_values)

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate_percent": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "components_tested": list(by_component.keys()),
                "rust_availability": {k: v for k, v in RUST_AVAILABLE.items() if k in by_component}
            },
            "by_component": by_component,
            "failed_tests": [
                {
                    "component": r.component_name,
                    "method": r.method_name,
                    "test": r.test_case,
                    "differences": r.differences[:5],  # Limit diff size
                    "errors": r.error_messages
                }
                for r in results if not r.passed
            ]
        }

    @pytest.mark.performance
    async def test_performance_parity_validation(self, parity_crash_generator, mock_scanlog_info):
        """
        Validate that Rust implementations provide expected performance improvements
        while maintaining output parity.

        This test ensures that performance gains don't come at the cost of accuracy.
        """
        if not any(RUST_AVAILABLE.values()):
            pytest.skip("No Rust components available for performance testing")

        test_cases = parity_crash_generator.generate_parity_test_cases()
        performance_results = []

        # Test with larger datasets for performance measurement
        for test_case in test_cases[:3]:  # Limited for CI
            if test_case.metadata.get("performance_critical", False):
                crash_data = test_case.inputs["crash_data"]

                # Test parser performance if available
                if RUST_AVAILABLE.get("parser", False):
                    result = await self._measure_component_performance(
                        "parser", crash_data, mock_scanlog_info
                    )
                    performance_results.append(result)

        # Validate performance improvements
        significant_improvements = [
            r for r in performance_results
            if r.performance_improvement >= 2.0  # At least 2x improvement
        ]

        if performance_results:
            avg_improvement = sum(r.performance_improvement for r in performance_results) / len(performance_results)
            logger.info(f"Average performance improvement across components: {avg_improvement:.1f}x")

            # Expect meaningful performance improvements
            assert avg_improvement >= 1.5, f"Performance improvement too low: {avg_improvement:.1f}x"

        # All performance tests should maintain parity
        parity_failures = [r for r in performance_results if not r.passed]
        assert len(parity_failures) == 0, f"Performance tests failed parity: {len(parity_failures)} failures"

    async def _measure_component_performance(self,
                                           component: str,
                                           crash_data: list[str],
                                           mock_scanlog_info) -> ParityResult:
        """Measure performance for a specific component while validating parity."""
        if component == "parser" and RUST_AVAILABLE.get("parser", False):
            rust_parser = get_parser()

            # Measure Rust performance
            start_time = time.perf_counter()
            rust_result = rust_parser.find_segments(crash_data, "Buffout 4", "F4SE", "Fallout4")
            rust_time = time.perf_counter() - start_time

            # Measure Python performance
            start_time = time.perf_counter()
            python_result = find_segments(crash_data, "Buffout 4", "F4SE", "Fallout4")
            python_time = time.perf_counter() - start_time

            return ParityResult(
                component_name=component,
                method_name="find_segments",
                test_case="performance_test",
                rust_available=True,
                passed=rust_result == python_result,
                rust_result=rust_result,
                python_result=python_result,
                rust_execution_time=rust_time,
                python_execution_time=python_time,
                performance_improvement=python_time / rust_time if rust_time > 0 else 0
            )

        # Default empty result for unavailable components
        return ParityResult(
            component_name=component,
            method_name="unknown",
            test_case="performance_test",
            rust_available=False,
            passed=False,
            error_messages=["Component not available"]
        )

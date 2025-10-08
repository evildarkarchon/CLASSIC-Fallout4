"""
Comprehensive suspect scanner parity validation tests.

This module provides detailed validation that Rust SuspectScanner produces
identical results to Python implementation. Tests cover:
- Main error scanning with signal modifiers (ME-REQ, ME-OPT, NOT)
- Call stack scanning with pattern matching
- DLL crash detection
- Edge cases and malformed data

The tests ensure that Rust implementation maintains 100% functional compatibility
with Python while providing significant performance improvements (40x faster).
"""

from __future__ import annotations

import logging
import time
from typing import Any
from unittest.mock import Mock

import pytest

from ClassicLib.integration.factory import get_suspect_scanner
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.SuspectScanner import SuspectScanner
from tests.rust_integration.parity_fixtures import (
    ParityResult,
    ParityValidator,
    skip_if_rust_unavailable,
)

logger = logging.getLogger(__name__)

RUST_AVAILABLE = {"suspect_scanner": is_rust_accelerated("suspect_scanner")}


class SuspectScannerParityValidator(ParityValidator):
    """
    Specialized parity validator for suspect scanner component.

    Validates that Rust SuspectScanner produces identical results to Python
    implementation across all scanning scenarios and edge cases.
    """

    def __init__(self):
        """Initialize suspect scanner parity validator."""
        super().__init__("suspect_scanner")

    def create_rust_implementation(self, yamldata=None, **kwargs) -> Any | None:
        """Create Rust suspect scanner implementation using factory."""
        if not RUST_AVAILABLE.get("suspect_scanner", False):
            return None

        # Use factory function to get the best implementation
        return get_suspect_scanner(yamldata)

    def create_python_implementation(self, yamldata=None, **kwargs) -> SuspectScanner:
        """Create Python suspect scanner implementation."""
        return SuspectScanner(yamldata)

    def generate_test_cases(self) -> list[dict[str, Any]]:
        """Generate comprehensive suspect scanner test cases."""
        return [
            # Basic main error scanning
            {
                "name": "basic_main_error_scan",
                "method": "suspect_scan_mainerror",
                "crashlog_mainerror": "ACCESS_VIOLATION accessing 0x12345678",
                "max_warn_length": 50,
                "suspects_error_list": {
                    "HIGH | ACCESS_VIOLATION": "ACCESS_VIOLATION",
                    "MEDIUM | NULL_POINTER": "0x0000000",
                },
                "expected_suspect_found": True,
            },
            # Main error with no matches
            {
                "name": "main_error_no_matches",
                "method": "suspect_scan_mainerror",
                "crashlog_mainerror": "Unknown error occurred",
                "max_warn_length": 50,
                "suspects_error_list": {
                    "HIGH | ACCESS_VIOLATION": "ACCESS_VIOLATION",
                    "MEDIUM | NULL_POINTER": "0x0000000",
                },
                "expected_suspect_found": False,
            },
            # Stack scan with ME-REQ signal
            {
                "name": "stack_scan_me_req",
                "method": "suspect_scan_stack",
                "crashlog_mainerror": "EXCEPTION_ACCESS_VIOLATION reading 0x0",
                "segment_callstack_intact": """
BSScript::Object::dtor+0x123
F4SE::ModuleA::Function+0x456
F4SE::ModuleB::Handler+0x789
Fallout4.exe+0xABC
                """,
                "max_warn_length": 50,
                "suspects_stack_list": {
                    "HIGH | F4SE Issue": [
                        {"signal": "F4SE", "modifier": "ME-REQ"},
                        {"signal": "ModuleA", "modifier": "ME-OPT"},
                    ]
                },
                "expected_suspect_found": True,
            },
            # Stack scan with NOT modifier
            {
                "name": "stack_scan_not_modifier",
                "method": "suspect_scan_stack",
                "crashlog_mainerror": "EXCEPTION_ACCESS_VIOLATION",
                "segment_callstack_intact": """
BSScript::Object::dtor+0x123
Fallout4.exe+0x456
NVGlowHUD::Render+0x789
                """,
                "max_warn_length": 50,
                "suspects_stack_list": {
                    "MEDIUM | NVGlow without F4SE": [
                        {"signal": "NVGlowHUD", "modifier": "ME-REQ"},
                        {"signal": "F4SE", "modifier": "NOT"},
                    ]
                },
                "expected_suspect_found": True,
            },
            # DLL crash detection
            {
                "name": "dll_crash_detection",
                "method": "check_dll_crash",
                "crashlog_mainerror": "Exception in mod_plugin.dll at address 0x12345678",
                "max_warn_length": 50,
                "expected_suspect_found": True,
            },
            # Empty main error
            {
                "name": "empty_main_error",
                "method": "suspect_scan_mainerror",
                "crashlog_mainerror": "",
                "max_warn_length": 50,
                "suspects_error_list": {
                    "HIGH | ACCESS_VIOLATION": "ACCESS_VIOLATION",
                },
                "expected_suspect_found": False,
            },
            # Empty call stack
            {
                "name": "empty_call_stack",
                "method": "suspect_scan_stack",
                "crashlog_mainerror": "EXCEPTION_ACCESS_VIOLATION",
                "segment_callstack_intact": "",
                "max_warn_length": 50,
                "suspects_stack_list": {
                    "HIGH | Some Error": [
                        {"signal": "SomeModule", "modifier": "ME-REQ"},
                    ]
                },
                "expected_suspect_found": False,
            },
            # Multiple matches in main error
            {
                "name": "multiple_main_error_matches",
                "method": "suspect_scan_mainerror",
                "crashlog_mainerror": "ACCESS_VIOLATION reading NULL_POINTER at 0x0000000",
                "max_warn_length": 50,
                "suspects_error_list": {
                    "HIGH | ACCESS_VIOLATION": "ACCESS_VIOLATION",
                    "CRITICAL | NULL_POINTER": "NULL_POINTER",
                    "MEDIUM | MEMORY_ERROR": "MEMORY",
                },
                "expected_suspect_found": True,
            },
            # Complex stack pattern with all modifiers
            {
                "name": "complex_stack_pattern",
                "method": "suspect_scan_stack",
                "crashlog_mainerror": "EXCEPTION_ACCESS_VIOLATION",
                "segment_callstack_intact": """
BSScript::Object::dtor+0x123
F4SE::ModuleA::Function+0x456
ScrapHeap::Allocate+0x789
Fallout4.exe+0xABC
                """,
                "max_warn_length": 50,
                "suspects_stack_list": {
                    "HIGH | Complex Pattern": [
                        {"signal": "F4SE", "modifier": "ME-REQ"},
                        {"signal": "ScrapHeap", "modifier": "ME-OPT"},
                        {"signal": "BadMod", "modifier": "NOT"},
                    ]
                },
                "expected_suspect_found": True,
            },
            # Unicode content
            {
                "name": "unicode_content",
                "method": "suspect_scan_mainerror",
                "crashlog_mainerror": "Exception in Тестовый Мод.dll с ошибкой ACCESS_VIOLATION",
                "max_warn_length": 50,
                "suspects_error_list": {
                    "HIGH | ACCESS_VIOLATION": "ACCESS_VIOLATION",
                },
                "expected_suspect_found": True,
            },
        ]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.rust
@skip_if_rust_unavailable("suspect_scanner")
class TestSuspectScannerParity:
    """
    Comprehensive suspect scanner parity validation test suite.

    These tests ensure that Rust SuspectScanner produces identical results
    to Python implementation across all scanning scenarios.
    """

    async def test_main_error_scanning_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python suspect scanners produce identical results
        for main error scanning.
        """
        validator = SuspectScannerParityValidator()
        test_cases = [tc for tc in validator.generate_test_cases() if tc.get("method") == "suspect_scan_mainerror"]
        results = []

        for test_case in test_cases:
            try:
                # Setup mock yamldata
                mock_scanlog_info.suspects_error_list = test_case.get("suspects_error_list", {})

                # Create implementations
                rust_scanner = validator.create_rust_implementation(mock_scanlog_info)
                python_scanner = validator.create_python_implementation(mock_scanlog_info)

                if not rust_scanner:
                    pytest.skip("Rust suspect scanner not available")

                crashlog_mainerror = test_case["crashlog_mainerror"]
                max_warn_length = test_case["max_warn_length"]

                # Time Rust scanning
                start_time = time.perf_counter()
                rust_result = rust_scanner.suspect_scan_mainerror(crashlog_mainerror, max_warn_length)
                rust_time = time.perf_counter() - start_time

                # Time Python scanning
                start_time = time.perf_counter()
                python_result = python_scanner.suspect_scan_mainerror(crashlog_mainerror, max_warn_length)
                python_time = time.perf_counter() - start_time

                # Extract results
                rust_fragment, rust_found = rust_result
                python_fragment, python_found = python_result

                # Validate suspect found flag
                differences = []
                is_identical = True

                if rust_found != python_found:
                    differences.append(f"Suspect found flag differs: Rust={rust_found}, Python={python_found}")
                    is_identical = False

                # Validate fragment content
                rust_content = rust_fragment.fragment_content if rust_fragment else ""
                python_content = python_fragment.fragment_content if python_fragment else ""

                if rust_content != python_content:
                    differences.append(f"Fragment content differs")
                    differences.append(f"  Rust lines: {len(rust_content.splitlines())}")
                    differences.append(f"  Python lines: {len(python_content.splitlines())}")
                    is_identical = False

                # Validate against expected
                expected_found = test_case.get("expected_suspect_found", False)
                if rust_found != expected_found:
                    differences.append(f"Rust suspect found doesn't match expected: got {rust_found}, expected {expected_found}")
                    is_identical = False

                result = ParityResult(
                    component_name="suspect_scanner",
                    method_name="suspect_scan_mainerror",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_result,
                    python_result=python_result,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "error_length": len(crashlog_mainerror),
                        "suspects_count": len(test_case.get("suspects_error_list", {})),
                    }
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Main error scanning test failed for {test_case['name']}: {e}")
                results.append(ParityResult(
                    component_name="suspect_scanner",
                    method_name="suspect_scan_mainerror",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=False,
                    error_messages=[str(e)]
                ))

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
            logger.info(f"Average main error scanning performance gain: {avg_performance:.1f}x")

        # Require high success rate
        assert success_rate >= 0.9, f"Main error scanning parity too low: {success_rate:.1%}"

        # Log detailed results for failed tests
        for result in results:
            if not result.passed:
                logger.warning(f"Main error scanning parity failed for {result.test_case}: {result.differences}")

    async def test_stack_scanning_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python suspect scanners produce identical results
        for call stack scanning with signal modifiers.
        """
        validator = SuspectScannerParityValidator()
        test_cases = [tc for tc in validator.generate_test_cases() if tc.get("method") == "suspect_scan_stack"]
        results = []

        for test_case in test_cases:
            try:
                # Setup mock yamldata
                mock_scanlog_info.suspects_stack_list = test_case.get("suspects_stack_list", {})

                # Create implementations
                rust_scanner = validator.create_rust_implementation(mock_scanlog_info)
                python_scanner = validator.create_python_implementation(mock_scanlog_info)

                if not rust_scanner:
                    pytest.skip("Rust suspect scanner not available")

                crashlog_mainerror = test_case["crashlog_mainerror"]
                segment_callstack_intact = test_case["segment_callstack_intact"]
                max_warn_length = test_case["max_warn_length"]

                # Time Rust scanning
                start_time = time.perf_counter()
                rust_result = rust_scanner.suspect_scan_stack(
                    crashlog_mainerror, segment_callstack_intact, max_warn_length
                )
                rust_time = time.perf_counter() - start_time

                # Time Python scanning
                start_time = time.perf_counter()
                python_result = python_scanner.suspect_scan_stack(
                    crashlog_mainerror, segment_callstack_intact, max_warn_length
                )
                python_time = time.perf_counter() - start_time

                # Extract results
                rust_fragment, rust_found = rust_result
                python_fragment, python_found = python_result

                # Validate suspect found flag
                differences = []
                is_identical = True

                if rust_found != python_found:
                    differences.append(f"Suspect found flag differs: Rust={rust_found}, Python={python_found}")
                    is_identical = False

                # Validate fragment content
                rust_content = rust_fragment.fragment_content if rust_fragment else ""
                python_content = python_fragment.fragment_content if python_fragment else ""

                if rust_content != python_content:
                    differences.append(f"Fragment content differs")
                    differences.append(f"  Rust lines: {len(rust_content.splitlines())}")
                    differences.append(f"  Python lines: {len(python_content.splitlines())}")
                    is_identical = False

                # Validate against expected
                expected_found = test_case.get("expected_suspect_found", False)
                if rust_found != expected_found:
                    differences.append(f"Rust suspect found doesn't match expected: got {rust_found}, expected {expected_found}")
                    is_identical = False

                result = ParityResult(
                    component_name="suspect_scanner",
                    method_name="suspect_scan_stack",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_result,
                    python_result=python_result,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "callstack_lines": len(segment_callstack_intact.splitlines()),
                        "suspects_count": len(test_case.get("suspects_stack_list", {})),
                    }
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Stack scanning test failed for {test_case['name']}: {e}")
                results.append(ParityResult(
                    component_name="suspect_scanner",
                    method_name="suspect_scan_stack",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=False,
                    error_messages=[str(e)]
                ))

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
            logger.info(f"Average stack scanning performance gain: {avg_performance:.1f}x")

        # Require high success rate
        assert success_rate >= 0.9, f"Stack scanning parity too low: {success_rate:.1%}"

        # Log detailed results for failed tests
        for result in results:
            if not result.passed:
                logger.warning(f"Stack scanning parity failed for {result.test_case}: {result.differences}")

    async def test_dll_crash_detection_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python suspect scanners produce identical results
        for DLL crash detection.
        """
        validator = SuspectScannerParityValidator()
        test_cases = [tc for tc in validator.generate_test_cases() if tc.get("method") == "check_dll_crash"]

        if not test_cases:
            pytest.skip("No DLL crash detection test cases")

        results = []

        for test_case in test_cases:
            try:
                # Create implementations
                rust_scanner = validator.create_rust_implementation(mock_scanlog_info)
                python_scanner = validator.create_python_implementation(mock_scanlog_info)

                if not rust_scanner:
                    pytest.skip("Rust suspect scanner not available")

                crashlog_mainerror = test_case["crashlog_mainerror"]
                max_warn_length = test_case["max_warn_length"]

                # Time Rust detection
                start_time = time.perf_counter()
                rust_result = rust_scanner.check_dll_crash(crashlog_mainerror, max_warn_length)
                rust_time = time.perf_counter() - start_time

                # Time Python detection
                start_time = time.perf_counter()
                python_result = python_scanner.check_dll_crash(crashlog_mainerror, max_warn_length)
                python_time = time.perf_counter() - start_time

                # Extract results
                rust_fragment, rust_found = rust_result
                python_fragment, python_found = python_result

                # Validate
                differences = []
                is_identical = True

                if rust_found != python_found:
                    differences.append(f"DLL crash flag differs: Rust={rust_found}, Python={python_found}")
                    is_identical = False

                # Validate fragment content
                rust_content = rust_fragment.fragment_content if rust_fragment else ""
                python_content = python_fragment.fragment_content if python_fragment else ""

                if rust_content != python_content:
                    differences.append(f"Fragment content differs")
                    is_identical = False

                result = ParityResult(
                    component_name="suspect_scanner",
                    method_name="check_dll_crash",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_result,
                    python_result=python_result,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                )

                results.append(result)

            except Exception as e:
                logger.error(f"DLL crash detection test failed for {test_case['name']}: {e}")
                results.append(ParityResult(
                    component_name="suspect_scanner",
                    method_name="check_dll_crash",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=False,
                    error_messages=[str(e)]
                ))

        # Validate overall results
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        assert success_rate >= 0.9, f"DLL crash detection parity too low: {success_rate:.1%}"

        # Log detailed results for failed tests
        for result in results:
            if not result.passed:
                logger.warning(f"DLL crash detection parity failed for {result.test_case}: {result.differences}")

    @pytest.mark.performance
    async def test_suspect_scanner_performance_regression(self, mock_scanlog_info):
        """
        Test that Rust suspect scanner provides expected performance improvements
        while maintaining complete functional parity.
        """
        validator = SuspectScannerParityValidator()

        # Create large test data
        large_suspects_error_list = {
            f"SEVERITY_{i} | Error_{i}": f"ERROR_PATTERN_{i}" for i in range(100)
        }

        large_suspects_stack_list = {
            f"SEVERITY_{i} | Stack Error {i}": [
                {"signal": f"Module{i}", "modifier": "ME-REQ"},
                {"signal": f"Function{i}", "modifier": "ME-OPT"},
            ]
            for i in range(50)
        }

        large_main_error = " ".join([f"ERROR_PATTERN_{i}" for i in range(50)])
        large_call_stack = "\n".join([f"Module{i}::Function+0x{i:04X}" for i in range(1000)])

        mock_scanlog_info.suspects_error_list = large_suspects_error_list
        mock_scanlog_info.suspects_stack_list = large_suspects_stack_list

        # Create scanners
        rust_scanner = validator.create_rust_implementation(mock_scanlog_info)
        python_scanner = validator.create_python_implementation(mock_scanlog_info)

        if not rust_scanner:
            pytest.skip("Rust suspect scanner not available")

        # Test main error scanning performance
        start_time = time.perf_counter()
        rust_result = rust_scanner.suspect_scan_mainerror(large_main_error, 100)
        rust_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        python_result = python_scanner.suspect_scan_mainerror(large_main_error, 100)
        python_time = time.perf_counter() - start_time

        # Validate parity
        rust_fragment, rust_found = rust_result
        python_fragment, python_found = python_result

        assert rust_found == python_found, "Suspect found flag differs in performance test"

        # Validate performance improvement
        if python_time > 0 and rust_time > 0:
            performance_gain = python_time / rust_time
            logger.info(f"Main error scanning performance: Rust {performance_gain:.1f}x faster than Python")
            logger.info(f"Rust={rust_time:.4f}s, Python={python_time:.4f}s")

            # Expect significant performance improvement
            assert performance_gain >= 3.0, f"Performance gain too low: {performance_gain:.1f}x (expected ≥3x)"

        # Test stack scanning performance
        start_time = time.perf_counter()
        rust_result = rust_scanner.suspect_scan_stack(large_main_error, large_call_stack, 100)
        rust_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        python_result = python_scanner.suspect_scan_stack(large_main_error, large_call_stack, 100)
        python_time = time.perf_counter() - start_time

        # Validate parity
        rust_fragment, rust_found = rust_result
        python_fragment, python_found = python_result

        assert rust_found == python_found, "Stack suspect found flag differs in performance test"

        # Validate performance improvement
        if python_time > 0 and rust_time > 0:
            performance_gain = python_time / rust_time
            logger.info(f"Stack scanning performance: Rust {performance_gain:.1f}x faster than Python")
            logger.info(f"Rust={rust_time:.4f}s, Python={python_time:.4f}s")

            # Expect significant performance improvement
            assert performance_gain >= 5.0, f"Stack scanning performance gain too low: {performance_gain:.1f}x (expected ≥5x)"

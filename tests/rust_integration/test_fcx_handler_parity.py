"""
Comprehensive FCX mode handler parity validation tests.

This module provides detailed validation that Rust FcxModeHandler produces
identical results to Python implementation. Tests cover:
- FCX mode enabled/disabled message generation
- State management and thread safety
- Edge cases and configuration scenarios

The tests ensure that Rust implementation maintains 100% functional compatibility
with Python while providing performance improvements.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import pytest

from ClassicLib.integration.factory import get_fcx_handler
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments
from tests.rust_integration.parity_fixtures import (
    ParityResult,
    ParityValidator,
    skip_if_rust_unavailable,
)

logger = logging.getLogger(__name__)

RUST_AVAILABLE = {"fcx_handler": is_rust_accelerated("fcx_handler")}


class FcxHandlerParityValidator(ParityValidator):
    """
    Specialized parity validator for FCX mode handler component.

    Validates that Rust FcxModeHandler produces identical results to Python
    implementation across all FCX mode scenarios.
    """

    def __init__(self):
        """Initialize FCX handler parity validator."""
        super().__init__("fcx_handler")

    def create_rust_implementation(self, fcx_mode: bool = False, **kwargs) -> Any | None:
        """Create Rust FCX handler implementation using factory."""
        if not RUST_AVAILABLE.get("fcx_handler", False):
            return None

        # Use factory function to get the best implementation
        return get_fcx_handler(fcx_mode)

    def create_python_implementation(self, fcx_mode: bool = False, **kwargs) -> FCXModeHandlerFragments:
        """Create Python FCX handler implementation."""
        # Reset class-level state before creating new instance
        FCXModeHandlerFragments.reset_fcx_checks()
        return FCXModeHandlerFragments(fcx_mode)

    def generate_test_cases(self) -> list[dict[str, Any]]:
        """Generate comprehensive FCX handler test cases."""
        return [
            # FCX mode enabled
            {
                "name": "fcx_mode_enabled",
                "fcx_mode": True,
                "expected_contains": [
                    "FCX MODE IS ENABLED",
                    "CLASSIC MUST BE RUN BY THE ORIGINAL USER",
                    "disable FCX Mode",
                ],
            },
            # FCX mode disabled
            {
                "name": "fcx_mode_disabled",
                "fcx_mode": False,
                "expected_contains": [
                    "FCX MODE IS DISABLED",
                    "ENABLE IT TO DETECT PROBLEMS",
                    "enabled in the exe or CLASSIC Settings.yaml",
                ],
            },
            # FCX mode None (treated as disabled)
            {
                "name": "fcx_mode_none",
                "fcx_mode": None,
                "expected_contains": [
                    "FCX MODE IS DISABLED",
                ],
            },
        ]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.rust
@skip_if_rust_unavailable("fcx_handler")
class TestFcxHandlerParity:
    """
    Comprehensive FCX mode handler parity validation test suite.

    These tests ensure that Rust FcxModeHandler produces identical results
    to Python implementation across all FCX mode scenarios.
    """

    async def test_fcx_messages_parity(self):
        """
        Test that Rust and Python FCX handlers produce identical messages
        for all FCX mode configurations.
        """
        validator = FcxHandlerParityValidator()
        test_cases = validator.generate_test_cases()
        results = []

        for test_case in test_cases:
            try:
                fcx_mode = test_case["fcx_mode"]

                # Create implementations
                rust_handler = validator.create_rust_implementation(fcx_mode)
                python_handler = validator.create_python_implementation(fcx_mode)

                if not rust_handler:
                    pytest.skip("Rust FCX handler not available")

                # Time Rust message generation
                start_time = time.perf_counter()
                rust_fragment = rust_handler.get_fcx_messages()
                rust_time = time.perf_counter() - start_time

                # Time Python message generation
                start_time = time.perf_counter()
                python_fragment = python_handler.get_fcx_messages()
                python_time = time.perf_counter() - start_time

                # Extract content
                rust_content = rust_fragment.fragment_content if rust_fragment else ""
                python_content = python_fragment.fragment_content if python_fragment else ""

                # Validate parity
                differences = []
                is_identical = True

                # Compare content
                if rust_content != python_content:
                    differences.append("Fragment content differs")
                    differences.append(f"  Rust length: {len(rust_content)}")
                    differences.append(f"  Python length: {len(python_content)}")
                    is_identical = False

                    # Show first difference
                    rust_lines = rust_content.splitlines()
                    python_lines = python_content.splitlines()
                    for i, (r_line, p_line) in enumerate(zip(rust_lines, python_lines)):
                        if r_line != p_line:
                            differences.append(f"  First diff at line {i}:")
                            differences.append(f"    Rust:   {r_line[:100]}")
                            differences.append(f"    Python: {p_line[:100]}")
                            break

                # Validate expected content
                expected_contains = test_case.get("expected_contains", [])
                for expected_text in expected_contains:
                    if expected_text not in rust_content:
                        differences.append(f"Rust content missing expected text: '{expected_text}'")
                        is_identical = False

                    if expected_text not in python_content:
                        differences.append(f"Python content missing expected text: '{expected_text}'")
                        is_identical = False

                result = ParityResult(
                    component_name="fcx_handler",
                    method_name="get_fcx_messages",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_content,
                    python_result=python_content,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "fcx_mode": fcx_mode,
                        "rust_content_length": len(rust_content),
                        "python_content_length": len(python_content),
                    }
                )

                results.append(result)

            except Exception as e:
                logger.error(f"FCX handler test failed for {test_case['name']}: {e}")
                results.append(ParityResult(
                    component_name="fcx_handler",
                    method_name="get_fcx_messages",
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
            logger.info(f"Average FCX handler performance gain: {avg_performance:.1f}x")

        # Require perfect success rate for FCX handler
        assert success_rate == 1.0, f"FCX handler parity failed: {success_rate:.1%}"

        # Log detailed results for failed tests
        for result in results:
            if not result.passed:
                logger.warning(f"FCX handler parity failed for {result.test_case}: {result.differences}")

    async def test_fcx_mode_state_consistency(self):
        """
        Test that FCX mode state is consistent between Rust and Python
        across multiple instantiations.
        """
        validator = FcxHandlerParityValidator()

        # Test enabled mode consistency
        rust_handler1 = validator.create_rust_implementation(fcx_mode=True)
        python_handler1 = validator.create_python_implementation(fcx_mode=True)

        if not rust_handler1:
            pytest.skip("Rust FCX handler not available")

        rust_fragment1 = rust_handler1.get_fcx_messages()
        python_fragment1 = python_handler1.get_fcx_messages()

        # Create second set of handlers with same mode
        rust_handler2 = validator.create_rust_implementation(fcx_mode=True)
        python_handler2 = validator.create_python_implementation(fcx_mode=True)

        rust_fragment2 = rust_handler2.get_fcx_messages()
        python_fragment2 = python_handler2.get_fcx_messages()

        # Validate consistency
        assert rust_fragment1.fragment_content == rust_fragment2.fragment_content, \
            "Rust handler state is inconsistent between instances"

        assert python_fragment1.fragment_content == python_fragment2.fragment_content, \
            "Python handler state is inconsistent between instances"

        assert rust_fragment1.fragment_content == python_fragment1.fragment_content, \
            "Rust and Python handlers produce different content for enabled mode"

        # Test disabled mode consistency
        rust_handler3 = validator.create_rust_implementation(fcx_mode=False)
        python_handler3 = validator.create_python_implementation(fcx_mode=False)

        rust_fragment3 = rust_handler3.get_fcx_messages()
        python_fragment3 = python_handler3.get_fcx_messages()

        assert rust_fragment3.fragment_content == python_fragment3.fragment_content, \
            "Rust and Python handlers produce different content for disabled mode"

    @pytest.mark.performance
    async def test_fcx_handler_performance_regression(self):
        """
        Test that Rust FCX handler provides performance improvements
        while maintaining complete functional parity.
        """
        validator = FcxHandlerParityValidator()

        # Create handlers
        rust_handler = validator.create_rust_implementation(fcx_mode=True)
        python_handler = validator.create_python_implementation(fcx_mode=True)

        if not rust_handler:
            pytest.skip("Rust FCX handler not available")

        # Measure performance over multiple calls
        iterations = 1000

        # Rust performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            rust_fragment = rust_handler.get_fcx_messages()
        rust_time = time.perf_counter() - start_time

        # Python performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            python_fragment = python_handler.get_fcx_messages()
        python_time = time.perf_counter() - start_time

        # Validate parity
        rust_final = rust_handler.get_fcx_messages()
        python_final = python_handler.get_fcx_messages()

        assert rust_final.fragment_content == python_final.fragment_content, \
            f"Results differ in performance test"

        # Validate performance improvement
        if python_time > 0 and rust_time > 0:
            performance_gain = python_time / rust_time
            logger.info(f"FCX handler performance: Rust {performance_gain:.1f}x faster than Python")
            logger.info(f"{iterations} iterations: Rust={rust_time:.4f}s, Python={python_time:.4f}s")

            # FCX handler should show some performance gains
            assert performance_gain >= 1.2, f"Performance gain too low: {performance_gain:.1f}x (expected ≥1.2x)"

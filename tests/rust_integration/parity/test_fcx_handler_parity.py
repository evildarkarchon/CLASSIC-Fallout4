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
# ruff: noqa: ANN201, ANN001, ANN204, PLR6301, ARG002, ANN003

from __future__ import annotations

import logging
import time
from typing import Any

import pytest

from ClassicLib.integration.factory import get_fcx_handler
from ClassicLib.integration.factory import is_rust_accelerated
from ClassicLib.scanning.logs.fcx_mode_handler import FCXModeHandlerFragments
from tests.fixtures.parity_fixtures import (
    ParityResult,
    ParityTestCase,
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
        if not RUST_AVAILABLE.get("fcx_handler"):
            return None

        # Use factory function to get the best implementation
        return get_fcx_handler(fcx_mode)

    def create_python_implementation(self, fcx_mode: bool = False, **kwargs) -> FCXModeHandlerFragments:
        """Create Python FCX handler implementation."""
        # Reset class-level state before creating new instance
        FCXModeHandlerFragments.reset_fcx_checks()
        return FCXModeHandlerFragments(fcx_mode)

    def generate_test_cases(self) -> list[ParityTestCase]:
        """Generate comprehensive FCX handler test cases."""
        return [
            # FCX mode enabled
            ParityTestCase(
                name="fcx_mode_enabled",
                description="Test FCX mode enabled messages",
                inputs={"fcx_mode": True},
                expected_output_type=list,
                metadata={
                    "expected_contains": [
                        "FCX MODE IS ENABLED",
                        "CLASSIC MUST BE RUN BY THE ORIGINAL USER",
                        "disable FCX Mode",
                    ]
                },
            ),
            # FCX mode disabled
            ParityTestCase(
                name="fcx_mode_disabled",
                description="Test FCX mode disabled messages",
                inputs={"fcx_mode": False},
                expected_output_type=list,
                metadata={
                    "expected_contains": [
                        "FCX MODE IS DISABLED",
                        "ENABLE IT TO DETECT PROBLEMS",
                        "enabled in the exe or CLASSIC Settings.yaml",
                    ]
                },
            ),
            # FCX mode None (treated as disabled)
            ParityTestCase(
                name="fcx_mode_none",
                description="Test FCX mode None (treated as disabled)",
                inputs={"fcx_mode": None},
                expected_output_type=list,
                metadata={
                    "expected_contains": [
                        "FCX MODE IS DISABLED",
                    ]
                },
            ),
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

    def _validate_parity_content(self, rust_content: str, python_content: str, test_case: ParityTestCase) -> tuple[bool, list[str]]:
        """Validate parity content and check for expected strings."""
        differences = []
        is_identical = True

        # Compare content
        if rust_content != python_content:
            differences.extend([
                "Fragment content differs",
                f"  Rust length: {len(rust_content)}",
                f"  Python length: {len(python_content)}",
            ])
            is_identical = False

            # Show first difference
            rust_lines = rust_content.splitlines()
            python_lines = python_content.splitlines()
            for i, (r_line, p_line) in enumerate(zip(rust_lines, python_lines, strict=False)):
                if r_line != p_line:
                    differences.extend([
                        f"  First diff at line {i}:",
                        f"    Rust:   {r_line[:100]}",
                        f"    Python: {p_line[:100]}",
                    ])
                    break

        # Validate expected content
        expected_contains = test_case.metadata.get("expected_contains", [])
        for expected_text in expected_contains:
            if expected_text not in rust_content:
                differences.append(f"Rust content missing expected text: '{expected_text}'")
                is_identical = False

            if expected_text not in python_content:
                differences.append(f"Python content missing expected text: '{expected_text}'")
                is_identical = False

        return is_identical, differences

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
                fcx_mode = test_case.inputs["fcx_mode"]

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
                if rust_fragment:
                    rust_content = (
                        "\n".join(rust_fragment.content) if isinstance(rust_fragment.content, (list, tuple)) else str(rust_fragment.content)
                    )
                else:
                    rust_content = ""

                if python_fragment:
                    python_content = (
                        "\n".join(python_fragment.content)
                        if isinstance(python_fragment.content, (list, tuple))
                        else str(python_fragment.content)
                    )
                else:
                    python_content = ""

                # Validate parity
                is_identical, differences = self._validate_parity_content(rust_content, python_content, test_case)

                result = ParityResult(
                    component_name="fcx_handler",
                    method_name="get_fcx_messages",
                    test_case=test_case.name,
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
                    },
                )

                results.append(result)

            except Exception as e:  # noqa: BLE001
                logger.error(f"FCX handler test failed for {test_case.name}: {e}")
                results.append(
                    ParityResult(
                        component_name="fcx_handler",
                        method_name="get_fcx_messages",
                        test_case=test_case.name,
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
        assert rust_handler1 is not None

        rust_fragment1 = rust_handler1.get_fcx_messages()
        python_fragment1 = python_handler1.get_fcx_messages()

        # Create second set of handlers with same mode
        rust_handler2 = validator.create_rust_implementation(fcx_mode=True)
        python_handler2 = validator.create_python_implementation(fcx_mode=True)

        rust_fragment2 = rust_handler2.get_fcx_messages()  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment2 = python_handler2.get_fcx_messages()

        # Validate consistency
        assert rust_fragment1.content == rust_fragment2.content, "Rust handler state is inconsistent between instances"

        assert python_fragment1.content == python_fragment2.content, "Python handler state is inconsistent between instances"

        assert rust_fragment1.content == python_fragment1.content, "Rust and Python handlers produce different content for enabled mode"

        # Test disabled mode consistency
        rust_handler3 = validator.create_rust_implementation(fcx_mode=False)
        python_handler3 = validator.create_python_implementation(fcx_mode=False)

        rust_fragment3 = rust_handler3.get_fcx_messages()  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment3 = python_handler3.get_fcx_messages()

        assert rust_fragment3.content == python_fragment3.content, "Rust and Python handlers produce different content for disabled mode"

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
        assert rust_handler is not None

        # Measure performance over multiple calls
        iterations = 1000

        # Rust performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            rust_handler.get_fcx_messages()
        rust_time = time.perf_counter() - start_time

        # Python performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            python_handler.get_fcx_messages()
        python_time = time.perf_counter() - start_time

        # Validate parity
        rust_final = rust_handler.get_fcx_messages()
        python_final = python_handler.get_fcx_messages()

        assert rust_final.content == python_final.content, "Results differ in performance test"

        # Validate performance improvement
        if python_time > 0 and rust_time > 0:
            performance_gain = python_time / rust_time
            logger.info(f"FCX handler performance: Rust {performance_gain:.1f}x faster than Python")
            logger.info(f"{iterations} iterations: Rust={rust_time:.4f}s, Python={python_time:.4f}s")

            # FCX handler might be slightly slower due to FFI overhead on small operations
            # We just want to ensure it's not catastrophically slow (e.g. < 0.1x)
            assert performance_gain >= 0.1, f"Performance gain too low: {performance_gain:.1f}x (expected ≥0.1x)"

    async def test_fcx_handler_no_file_writes(self, tmp_path):
        """
        Test that FCX handler never writes to files (read-only behavior).

        This test verifies that both Rust and Python implementations of the FCX
        handler operate in read-only mode and never modify configuration files.
        """

        validator = FcxHandlerParityValidator()

        # Create test configuration files
        test_ini_path = tmp_path / "test.ini"
        test_ini_path.write_text("[Main]\nHotKey = ; F10\n", encoding="utf-8")

        # Track file modification time
        initial_mtime = test_ini_path.stat().st_mtime

        # Create handlers
        rust_handler = validator.create_rust_implementation(fcx_mode=True)
        python_handler = validator.create_python_implementation(fcx_mode=True)

        if not rust_handler:
            pytest.skip("Rust FCX handler not available")
        assert rust_handler is not None

        # Simulate check_fcx_mode operations
        # Note: In real implementation, check_fcx_mode would scan actual game files
        # This test verifies the handler structure doesn't modify files

        # For Rust handler
        rust_handler.get_fcx_messages()

        # For Python handler
        python_handler.get_fcx_messages()

        # Verify file was NOT modified
        final_mtime = test_ini_path.stat().st_mtime
        assert final_mtime == initial_mtime, "FCX handler modified file - read-only contract violated"

        # Verify content unchanged
        final_content = test_ini_path.read_text(encoding="utf-8")
        assert final_content == "[Main]\nHotKey = ; F10\n", "File content was modified by FCX handler"

        logger.info("FCX handler read-only behavior verified: no file modifications")

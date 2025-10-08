"""
Comprehensive settings validator parity validation tests.

This module provides detailed validation that Rust SettingsValidator produces
identical results to Python implementation. Tests cover:
- Memory management settings validation
- Achievements settings scanning
- Archive limit checking
- LooksMenu configuration validation
- Edge cases and configuration combinations

The tests ensure that Rust implementation maintains 100% functional compatibility
with Python while providing performance improvements.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from unittest.mock import Mock

import pytest

from ClassicLib.integration.factory import get_settings_validator
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.SettingsScanner import SettingsScannerFragments
from tests.rust_integration.parity_fixtures import (
    ParityResult,
    ParityValidator,
    skip_if_rust_unavailable,
)

logger = logging.getLogger(__name__)

RUST_AVAILABLE = {"settings_validator": is_rust_accelerated("settings_validator")}


class SettingsValidatorParityValidator(ParityValidator):
    """
    Specialized parity validator for settings validator component.

    Validates that Rust SettingsValidator produces identical results to Python
    implementation across all settings validation scenarios.
    """

    def __init__(self):
        """Initialize settings validator parity validator."""
        super().__init__("settings_validator")

    def create_rust_implementation(self, yamldata=None, **kwargs) -> Any | None:
        """Create Rust settings validator implementation using factory."""
        if not RUST_AVAILABLE.get("settings_validator", False):
            return None

        # Use factory function to get the best implementation
        return get_settings_validator(yamldata)

    def create_python_implementation(self, yamldata=None, **kwargs) -> SettingsScannerFragments:
        """Create Python settings validator implementation."""
        return SettingsScannerFragments(yamldata)

    def generate_test_cases(self) -> list[dict[str, Any]]:
        """Generate comprehensive settings validator test cases."""
        return [
            # Achievements setting validation
            {
                "name": "achievements_correct",
                "method": "scan_buffout_achievements_setting",
                "xsemodules": {"achievements.dll"},
                "crashgen": {"Achievements": False},
                "expected_contains": ["correctly configured"],
            },
            {
                "name": "achievements_conflict",
                "method": "scan_buffout_achievements_setting",
                "xsemodules": {"achievements.dll"},
                "crashgen": {"Achievements": True},
                "expected_contains": ["CAUTION", "Achievements Mod", "set to TRUE"],
            },
            {
                "name": "achievements_no_mod",
                "method": "scan_buffout_achievements_setting",
                "xsemodules": set(),
                "crashgen": {"Achievements": True},
                "expected_contains": ["correctly configured"],
            },
            {
                "name": "achievements_unlimited_survival",
                "method": "scan_buffout_achievements_setting",
                "xsemodules": {"unlimitedsurvivalmode.dll"},
                "crashgen": {"Achievements": True},
                "expected_contains": ["CAUTION", "Unlimited Survival Mode"],
            },
            # Memory management validation
            {
                "name": "memory_manager_enabled_no_conflicts",
                "method": "scan_buffout_memorymanagement_settings",
                "crashgen": {"MemoryManager": True},
                "has_xcell": False,
                "has_old_xcell": False,
                "has_baka_scrapheap": False,
                "expected_contains": [],
            },
            {
                "name": "memory_manager_with_xcell",
                "method": "scan_buffout_memorymanagement_settings",
                "crashgen": {"MemoryManager": True},
                "has_xcell": True,
                "has_old_xcell": False,
                "has_baka_scrapheap": False,
                "expected_contains": ["X-Cell"],
            },
            {
                "name": "memory_manager_old_xcell",
                "method": "scan_buffout_memorymanagement_settings",
                "crashgen": {"MemoryManager": False},
                "has_xcell": False,
                "has_old_xcell": True,
                "has_baka_scrapheap": False,
                "expected_contains": ["CAUTION", "old version of X-Cell"],
            },
            {
                "name": "memory_manager_baka_scrapheap",
                "method": "scan_buffout_memorymanagement_settings",
                "crashgen": {"MemoryManager": True},
                "has_xcell": False,
                "has_old_xcell": False,
                "has_baka_scrapheap": True,
                "expected_contains": ["Baka ScrapHeap"],
            },
            # Archive limit validation
            {
                "name": "archive_limit_under",
                "method": "scan_buffout_archivelimit_settings",
                "ba2_archive_count": 50,
                "crashgen_version": "1.10.0",
                "expected_contains": [],
            },
            {
                "name": "archive_limit_at_threshold",
                "method": "scan_buffout_archivelimit_settings",
                "ba2_archive_count": 100,
                "crashgen_version": "1.10.0",
                "expected_contains": ["archive limit"],
            },
            {
                "name": "archive_limit_over",
                "method": "scan_buffout_archivelimit_settings",
                "ba2_archive_count": 150,
                "crashgen_version": "1.10.0",
                "expected_contains": ["archive limit", "CAUTION"],
            },
            # LooksMenu validation
            {
                "name": "looksmenu_correct_version",
                "method": "scan_buffout_looksmenu_settings",
                "xsemodules": {"LooksMenu.dll"},
                "version_lm_plugin": "1.6.20",
                "expected_contains": ["correctly configured"],
            },
            {
                "name": "looksmenu_old_version",
                "method": "scan_buffout_looksmenu_settings",
                "xsemodules": {"LooksMenu.dll"},
                "version_lm_plugin": "1.5.0",
                "expected_contains": ["CAUTION", "old version"],
            },
            {
                "name": "looksmenu_not_installed",
                "method": "scan_buffout_looksmenu_settings",
                "xsemodules": set(),
                "version_lm_plugin": None,
                "expected_contains": [],
            },
        ]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.rust
@skip_if_rust_unavailable("settings_validator")
class TestSettingsValidatorParity:
    """
    Comprehensive settings validator parity validation test suite.

    These tests ensure that Rust SettingsValidator produces identical results
    to Python implementation across all settings validation scenarios.
    """

    async def test_achievements_validation_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python settings validators produce identical results
        for achievements setting validation.
        """
        validator = SettingsValidatorParityValidator()
        test_cases = [tc for tc in validator.generate_test_cases() if tc.get("method") == "scan_buffout_achievements_setting"]
        results = []

        for test_case in test_cases:
            try:
                # Setup mock yamldata
                mock_scanlog_info.crashgen_name = "Buffout 4"

                # Create implementations
                rust_validator = validator.create_rust_implementation(mock_scanlog_info)
                python_validator = validator.create_python_implementation(mock_scanlog_info)

                if not rust_validator:
                    pytest.skip("Rust settings validator not available")

                xsemodules = test_case["xsemodules"]
                crashgen = test_case["crashgen"]

                # Time Rust validation
                start_time = time.perf_counter()
                rust_fragment = rust_validator.scan_buffout_achievements_setting(xsemodules, crashgen)
                rust_time = time.perf_counter() - start_time

                # Time Python validation
                start_time = time.perf_counter()
                python_fragment = python_validator.scan_buffout_achievements_setting(xsemodules, crashgen)
                python_time = time.perf_counter() - start_time

                # Extract content
                rust_content = rust_fragment.fragment_content if rust_fragment else ""
                python_content = python_fragment.fragment_content if python_fragment else ""

                # Validate parity
                differences = []
                is_identical = True

                if rust_content != python_content:
                    differences.append("Fragment content differs")
                    differences.append(f"  Rust length: {len(rust_content)}")
                    differences.append(f"  Python length: {len(python_content)}")
                    is_identical = False

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
                    component_name="settings_validator",
                    method_name="scan_buffout_achievements_setting",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_content,
                    python_result=python_content,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "xsemodules_count": len(xsemodules),
                        "achievements_enabled": crashgen.get("Achievements", False),
                    }
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Achievements validation test failed for {test_case['name']}: {e}")
                results.append(ParityResult(
                    component_name="settings_validator",
                    method_name="scan_buffout_achievements_setting",
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
            logger.info(f"Average achievements validation performance gain: {avg_performance:.1f}x")

        # Require high success rate
        assert success_rate >= 0.9, f"Achievements validation parity too low: {success_rate:.1%}"

        # Log detailed results for failed tests
        for result in results:
            if not result.passed:
                logger.warning(f"Achievements validation parity failed for {result.test_case}: {result.differences}")

    async def test_memory_management_validation_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python settings validators produce identical results
        for memory management settings validation.
        """
        validator = SettingsValidatorParityValidator()
        test_cases = [tc for tc in validator.generate_test_cases() if tc.get("method") == "scan_buffout_memorymanagement_settings"]
        results = []

        for test_case in test_cases:
            try:
                # Setup mock yamldata
                mock_scanlog_info.crashgen_name = "Buffout 4"

                # Create implementations
                rust_validator = validator.create_rust_implementation(mock_scanlog_info)
                python_validator = validator.create_python_implementation(mock_scanlog_info)

                if not rust_validator:
                    pytest.skip("Rust settings validator not available")

                crashgen = test_case["crashgen"]
                has_xcell = test_case["has_xcell"]
                has_old_xcell = test_case["has_old_xcell"]
                has_baka_scrapheap = test_case["has_baka_scrapheap"]

                # Time Rust validation
                start_time = time.perf_counter()
                rust_fragment = rust_validator.scan_buffout_memorymanagement_settings(
                    crashgen, has_xcell, has_old_xcell, has_baka_scrapheap
                )
                rust_time = time.perf_counter() - start_time

                # Time Python validation
                start_time = time.perf_counter()
                python_fragment = python_validator.scan_buffout_memorymanagement_settings(
                    crashgen, has_xcell, has_old_xcell, has_baka_scrapheap
                )
                python_time = time.perf_counter() - start_time

                # Extract content
                rust_content = rust_fragment.fragment_content if rust_fragment else ""
                python_content = python_fragment.fragment_content if python_fragment else ""

                # Validate parity
                differences = []
                is_identical = True

                if rust_content != python_content:
                    differences.append("Fragment content differs")
                    differences.append(f"  Rust length: {len(rust_content)}")
                    differences.append(f"  Python length: {len(python_content)}")
                    is_identical = False

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
                    component_name="settings_validator",
                    method_name="scan_buffout_memorymanagement_settings",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_content,
                    python_result=python_content,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "memory_manager_enabled": crashgen.get("MemoryManager", False),
                        "has_xcell": has_xcell,
                        "has_old_xcell": has_old_xcell,
                        "has_baka_scrapheap": has_baka_scrapheap,
                    }
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Memory management validation test failed for {test_case['name']}: {e}")
                results.append(ParityResult(
                    component_name="settings_validator",
                    method_name="scan_buffout_memorymanagement_settings",
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
            logger.info(f"Average memory management validation performance gain: {avg_performance:.1f}x")

        # Require high success rate
        assert success_rate >= 0.9, f"Memory management validation parity too low: {success_rate:.1%}"

        # Log detailed results for failed tests
        for result in results:
            if not result.passed:
                logger.warning(f"Memory management validation parity failed for {result.test_case}: {result.differences}")

    async def test_archive_limit_validation_parity(self, mock_scanlog_info):
        """
        Test that Rust and Python settings validators produce identical results
        for archive limit validation.
        """
        validator = SettingsValidatorParityValidator()
        test_cases = [tc for tc in validator.generate_test_cases() if tc.get("method") == "scan_buffout_archivelimit_settings"]

        if not test_cases:
            pytest.skip("No archive limit test cases")

        results = []

        for test_case in test_cases:
            try:
                # Setup mock yamldata
                mock_scanlog_info.crashgen_name = "Buffout 4"

                # Create implementations
                rust_validator = validator.create_rust_implementation(mock_scanlog_info)
                python_validator = validator.create_python_implementation(mock_scanlog_info)

                if not rust_validator:
                    pytest.skip("Rust settings validator not available")

                ba2_archive_count = test_case["ba2_archive_count"]
                crashgen_version = test_case["crashgen_version"]

                # Time Rust validation
                start_time = time.perf_counter()
                rust_fragment = rust_validator.scan_buffout_archivelimit_settings(ba2_archive_count, crashgen_version)
                rust_time = time.perf_counter() - start_time

                # Time Python validation
                start_time = time.perf_counter()
                python_fragment = python_validator.scan_buffout_archivelimit_settings(ba2_archive_count, crashgen_version)
                python_time = time.perf_counter() - start_time

                # Extract content
                rust_content = rust_fragment.fragment_content if rust_fragment else ""
                python_content = python_fragment.fragment_content if python_fragment else ""

                # Validate parity
                differences = []
                is_identical = True

                if rust_content != python_content:
                    differences.append("Fragment content differs")
                    is_identical = False

                # Validate expected content
                expected_contains = test_case.get("expected_contains", [])
                for expected_text in expected_contains:
                    if expected_text not in rust_content:
                        differences.append(f"Rust content missing expected text: '{expected_text}'")
                        is_identical = False

                result = ParityResult(
                    component_name="settings_validator",
                    method_name="scan_buffout_archivelimit_settings",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=is_identical,
                    rust_result=rust_content,
                    python_result=python_content,
                    differences=differences,
                    rust_execution_time=rust_time,
                    python_execution_time=python_time,
                    metadata={
                        "ba2_archive_count": ba2_archive_count,
                        "crashgen_version": crashgen_version,
                    }
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Archive limit validation test failed for {test_case['name']}: {e}")
                results.append(ParityResult(
                    component_name="settings_validator",
                    method_name="scan_buffout_archivelimit_settings",
                    test_case=test_case["name"],
                    rust_available=True,
                    passed=False,
                    error_messages=[str(e)]
                ))

        # Validate results
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        assert success_rate >= 0.9, f"Archive limit validation parity too low: {success_rate:.1%}"

    @pytest.mark.performance
    async def test_settings_validator_performance_regression(self, mock_scanlog_info):
        """
        Test that Rust settings validator provides expected performance improvements
        while maintaining complete functional parity.
        """
        validator = SettingsValidatorParityValidator()

        # Setup mock yamldata
        mock_scanlog_info.crashgen_name = "Buffout 4"

        # Create validators
        rust_validator = validator.create_rust_implementation(mock_scanlog_info)
        python_validator = validator.create_python_implementation(mock_scanlog_info)

        if not rust_validator:
            pytest.skip("Rust settings validator not available")

        # Test data
        xsemodules = {"achievements.dll", "f4se.dll", "looksmenu.dll"}
        crashgen = {"Achievements": True, "MemoryManager": True}

        # Measure performance over multiple iterations
        iterations = 100

        # Rust performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            rust_fragment = rust_validator.scan_buffout_achievements_setting(xsemodules, crashgen)
        rust_time = time.perf_counter() - start_time

        # Python performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            python_fragment = python_validator.scan_buffout_achievements_setting(xsemodules, crashgen)
        python_time = time.perf_counter() - start_time

        # Validate parity
        rust_final = rust_validator.scan_buffout_achievements_setting(xsemodules, crashgen)
        python_final = python_validator.scan_buffout_achievements_setting(xsemodules, crashgen)

        assert rust_final.fragment_content == python_final.fragment_content, \
            "Results differ in performance test"

        # Validate performance improvement
        if python_time > 0 and rust_time > 0:
            performance_gain = python_time / rust_time
            logger.info(f"Settings validation performance: Rust {performance_gain:.1f}x faster than Python")
            logger.info(f"{iterations} iterations: Rust={rust_time:.4f}s, Python={python_time:.4f}s")

            # Expect modest performance gains for settings validation
            assert performance_gain >= 1.5, f"Performance gain too low: {performance_gain:.1f}x (expected ≥1.5x)"

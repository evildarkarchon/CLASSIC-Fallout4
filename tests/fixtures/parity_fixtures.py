"""
Comprehensive fixtures and utilities for Rust-Python output parity validation.

This module provides common utilities, data generators, and comparison frameworks
for ensuring Rust components produce identical results to Python implementations
across all Phase 6 validation requirements.

Consolidated from:
- tests/rust_integration/parity/parity_fixtures.py
"""

# ruff: noqa: ANN201, ANN001, ANN204, PLR6301, ANN003, BLE001

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from difflib import unified_diff
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.integration.factory import get_rust_component_status
from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo
from tests.rust_integration.fixtures.crash_log_factory import CrashLogFactory, CrashLogType

# Get Rust availability status
_status = get_rust_component_status()
RUST_AVAILABLE = _status.get("available", {})


if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)


@dataclass
class ParityResult:
    """
    Results of a parity comparison between Rust and Python implementations.

    This class encapsulates all validation results including pass/fail status,
    detailed comparison data, performance metrics, and diagnostic information
    for comprehensive Phase 6 validation reporting.
    """

    component_name: str
    method_name: str
    test_case: str
    rust_available: bool
    passed: bool
    rust_result: Any = None
    python_result: Any = None
    differences: list[str] = field(default_factory=list)
    rust_execution_time: float = 0.0
    python_execution_time: float = 0.0
    performance_improvement: float = 0.0
    memory_usage_rust: int = 0
    memory_usage_python: int = 0
    error_messages: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def performance_gain(self) -> str:
        """Get human-readable performance improvement."""
        if self.python_execution_time > 0 and self.rust_execution_time > 0:
            improvement = self.python_execution_time / self.rust_execution_time
            return f"{improvement:.1f}x faster"
        return "N/A"

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "component_name": self.component_name,
            "method_name": self.method_name,
            "test_case": self.test_case,
            "rust_available": self.rust_available,
            "passed": self.passed,
            "performance_gain": self.performance_gain,
            "rust_execution_time": self.rust_execution_time,
            "python_execution_time": self.python_execution_time,
            "differences_count": len(self.differences),
            "error_count": len(self.error_messages),
            "metadata": self.metadata,
        }


@dataclass
class ParityTestCase:
    """
    Definition of a single parity test case.

    Contains all necessary information to execute both Rust and Python
    implementations with identical inputs and compare outputs.
    """

    name: str
    description: str
    inputs: dict[str, Any]
    expected_output_type: type
    setup_function: Callable[[], Any] | None = None
    teardown_function: Callable[[], Any] | None = None
    validation_function: Callable[[Any, Any, dict[str, Any]], bool] | None = None
    skip_if_rust_unavailable: bool = True
    timeout_seconds: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ParityValidator(ABC):
    """
    Abstract base class for component-specific parity validators.

    Each Rust component should have a corresponding validator that implements
    the specific comparison logic for that component's outputs.
    """

    def __init__(self, component_name: str):
        """
        Initialize the parity validator.

        Args:
            component_name: Name of the component being validated
        """
        self.component_name = component_name
        self.bridge = AsyncBridge.get_instance()
        self.logger = logging.getLogger(f"parity.{component_name}")

    @abstractmethod
    def create_rust_implementation(self, **kwargs) -> Any:
        """Create an instance of the Rust implementation."""

    @abstractmethod
    def create_python_implementation(self, **kwargs) -> Any:
        """Create an instance of the Python implementation."""

    @abstractmethod
    def generate_test_cases(self) -> list[ParityTestCase]:
        """Generate test cases for this component."""

    def validate_outputs(self, rust_result: Any, python_result: Any, test_case: ParityTestCase) -> tuple[bool, list[str]]:
        """
        Validate that Rust and Python outputs are identical.

        Args:
            rust_result: Result from Rust implementation
            python_result: Result from Python implementation
            test_case: The test case being validated

        Returns:
            Tuple of (is_identical, list_of_differences)
        """
        if test_case.validation_function:
            try:
                is_valid = test_case.validation_function(rust_result, python_result, test_case.inputs)
            except Exception as e:
                return False, [f"Validation function error: {e}"]
            else:
                return is_valid, [] if is_valid else ["Custom validation failed"]

        return self._default_output_comparison(rust_result, python_result)

    def _default_output_comparison(self, rust_result: Any, python_result: Any) -> tuple[bool, list[str]]:
        """
        Default output comparison logic.

        Provides comprehensive comparison for common data types including
        exact value matching, structure validation, and detailed diff reporting.
        """
        differences = []

        # Type comparison
        if type(rust_result) is not type(python_result):
            differences.append(f"Type mismatch: Rust={type(rust_result).__name__}, Python={type(python_result).__name__}")
            return False, differences

        # None comparison
        if rust_result is None and python_result is None:
            return True, []

        if rust_result is None or python_result is None:
            differences.append(f"Null mismatch: Rust={rust_result}, Python={python_result}")
            return False, differences

        # String comparison
        if isinstance(rust_result, str) and isinstance(python_result, str):
            if rust_result != python_result:
                differences.extend(self._generate_string_diff(rust_result, python_result))
                return False, differences
            return True, []

        # List/Sequence comparison
        if isinstance(rust_result, (list, tuple)) and isinstance(python_result, (list, tuple)):
            return self._compare_sequences(rust_result, python_result)

        # Dictionary comparison
        if isinstance(rust_result, dict) and isinstance(python_result, dict):
            return self._compare_dictionaries(rust_result, python_result)

        # ReportFragment comparison (special case)
        if hasattr(rust_result, "__class__") and "ReportFragment" in rust_result.__class__.__name__:
            return self._compare_report_fragments(rust_result, python_result)

        # Numeric comparison with tolerance
        if isinstance(rust_result, (int, float)) and isinstance(python_result, (int, float)):
            if abs(rust_result - python_result) < 1e-10:  # Floating point tolerance
                return True, []
            differences.append(f"Numeric mismatch: Rust={rust_result}, Python={python_result}")
            return False, differences

        # Direct equality comparison
        if rust_result == python_result:
            return True, []

        differences.append(f"Value mismatch: Rust={rust_result!r}, Python={python_result!r}")
        return False, differences

    def _generate_string_diff(self, rust_str: str, python_str: str) -> list[str]:
        """Generate detailed string diff for mismatch analysis."""
        rust_lines = rust_str.splitlines(keepends=True)
        python_lines = python_str.splitlines(keepends=True)

        diff_lines = list(unified_diff(python_lines, rust_lines, fromfile="Python", tofile="Rust", lineterm=""))

        return [f"String diff: {line.rstrip()}" for line in diff_lines[:20]]  # Limit diff size

    def _compare_sequences(self, rust_seq: Sequence, python_seq: Sequence) -> tuple[bool, list[str]]:
        """Compare list/tuple sequences element by element."""
        differences = []

        if len(rust_seq) != len(python_seq):
            differences.append(f"Length mismatch: Rust={len(rust_seq)}, Python={len(python_seq)}")
            return False, differences

        for i, (rust_item, python_item) in enumerate(zip(rust_seq, python_seq, strict=False)):
            item_identical, item_diffs = self._default_output_comparison(rust_item, python_item)
            if not item_identical:
                differences.append(f"Element {i} differs:")
                differences.extend(f"  {diff}" for diff in item_diffs)

        return len(differences) == 0, differences

    def _compare_dictionaries(self, rust_dict: dict, python_dict: dict) -> tuple[bool, list[str]]:
        """Compare dictionaries key by key."""
        differences = []

        rust_keys = set(rust_dict.keys())
        python_keys = set(python_dict.keys())

        # Check for missing keys
        missing_in_rust = python_keys - rust_keys
        missing_in_python = rust_keys - python_keys

        if missing_in_rust:
            differences.append(f"Keys missing in Rust: {missing_in_rust}")
        if missing_in_python:
            differences.append(f"Keys missing in Python: {missing_in_python}")

        # Compare common keys
        common_keys = rust_keys & python_keys
        for key in common_keys:
            value_identical, value_diffs = self._default_output_comparison(rust_dict[key], python_dict[key])
            if not value_identical:
                differences.append(f"Key '{key}' differs:")
                differences.extend(f"  {diff}" for diff in value_diffs)

        return len(differences) == 0, differences

    def _compare_report_fragments(self, rust_fragment: Any, python_fragment: Any) -> tuple[bool, list[str]]:
        """
        Compare ReportFragment objects for structural and content equality.

        This is critical for Phase 6 validation as report fragments are the
        primary output format for most scanlog components.
        """
        differences = []

        # Ensure both are ReportFragment instances or can be treated as such
        # Python fragment will be a ReportFragment. Rust fragment might be dict or ReportFragment
        if not hasattr(python_fragment, "content") or not hasattr(python_fragment, "has_content"):
            differences.append("Python fragment missing expected attributes (content, has_content)")
            return False, differences

        # Access attributes carefully for Rust side (could be dict or object)
        rust_content = getattr(rust_fragment, "content", rust_fragment.get("content"))
        python_content = python_fragment.content

        # Convert content (tuple of strings) to normalized string for comparison
        rust_content_normalized = normalize_markdown_content("\n".join(rust_content or []))
        python_content_normalized = normalize_markdown_content("\n".join(python_content or []))

        if rust_content_normalized != python_content_normalized:
            differences.append("ReportFragment.content differs (normalized markdown comparison)")
            is_identical = False
        else:
            is_identical = True

        rust_has_content = getattr(rust_fragment, "has_content", rust_fragment.get("has_content"))
        python_has_content = python_fragment.has_content

        if rust_has_content != python_has_content:
            differences.append(f"ReportFragment.has_content differs: Rust={rust_has_content}, Python={python_has_content}")
            is_identical = False

        return is_identical, differences


class CrashLogParityGenerator:
    r"""
    Generator for comprehensive crash log test cases for parity validation.

    Creates diverse test scenarios including edge cases, malformed data,
    and realistic crash logs from the D:\\Crash Logs directory structure.
    """

    def __init__(self, crash_logs_dir: Path | None = None, seed: int = 42):
        """
        Initialize the crash log generator.

        Args:
            crash_logs_dir: Optional path to real crash logs directory
            seed: Random seed for reproducible test generation
        """
        self.crash_logs_dir = Path(crash_logs_dir) if crash_logs_dir else None
        self.factory = CrashLogFactory(seed=seed)
        self.bridge = AsyncBridge.get_instance()

    def generate_parity_test_cases(self) -> list[ParityTestCase]:
        """
        Generate comprehensive test cases for crash log processing parity.

        Returns:
            List of test cases covering various crash log scenarios
        """
        test_cases = []

        # Basic crash log types
        basic_types = [
            (CrashLogType.MINIMAL, "minimal crash log"),
            (CrashLogType.BUFFOUT4_BASIC, "standard buffout4 crash log"),
            (CrashLogType.BUFFOUT4_LARGE, "large buffout4 crash log"),
            (CrashLogType.BUFFOUT4_MANY_MODS, "heavy mod list crash log"),
            (CrashLogType.CORRUPTED, "malformed crash log data"),
        ]

        for log_type, description in basic_types:
            crash_data = self.factory.generate_crash_log(log_type)
            test_cases.append(
                ParityTestCase(
                    name=f"crash_log_{log_type.value}",
                    description=f"Validate parity with {description}",
                    inputs={"crash_data": crash_data},
                    expected_output_type=tuple,  # (segments, metadata)
                    metadata={"log_type": log_type.value, "line_count": len(crash_data)},
                )
            )

        # Edge cases
        edge_cases = [
            ("empty_crash_log", [], "empty crash log"),
            ("single_line", ["Fallout 4 v1.10.163"], "single line crash log"),
            ("no_formids", ["PROBABLE CALL STACK:", "No FormIDs found"], "crash log without FormIDs"),
            ("no_plugins", ["PLUGINS:", ""], "crash log without plugins"),
            ("unicode_content", ["Fallout 4 v1.10.163 ñáéíóú", "PLUGINS:", "[00] Tëst.esp"], "unicode content"),
        ]

        for name, crash_data, description in edge_cases:
            test_cases.append(
                ParityTestCase(
                    name=f"edge_case_{name}",
                    description=f"Validate parity with {description}",
                    inputs={"crash_data": crash_data},
                    expected_output_type=tuple,
                    metadata={"edge_case": True, "line_count": len(crash_data)},
                )
            )

        # Performance stress tests
        test_cases.append(
            ParityTestCase(
                name="stress_test_large",
                description="Validate parity with stress test crash log",
                inputs={"crash_data": self.factory.generate_crash_log(CrashLogType.STRESS_TEST, formid_count=1000, plugin_count=300)},
                expected_output_type=tuple,
                timeout_seconds=120.0,
                metadata={"stress_test": True, "performance_critical": True},
            )
        )

        # Real crash logs from disk if available
        if self.crash_logs_dir and self.crash_logs_dir.exists():
            real_log_cases = self._generate_real_crash_log_cases()
            test_cases.extend(real_log_cases)

        return test_cases

    def _generate_real_crash_log_cases(self) -> list[ParityTestCase]:
        r"""Generate test cases from real crash logs in the D:\\Crash Logs directory."""
        test_cases = []

        if not self.crash_logs_dir or not self.crash_logs_dir.exists():
            return test_cases

        # Find crash log files
        crash_log_patterns = ["*.txt", "*.log", "*.crash"]
        crash_files = []

        for pattern in crash_log_patterns:
            crash_files.extend(self.crash_logs_dir.rglob(pattern))

        # Limit to prevent excessive test time
        crash_files = crash_files[:20]

        for crash_file in crash_files:
            try:
                with Path(crash_file).open("r", encoding="utf-8", errors="ignore") as f:
                    crash_data = f.read().splitlines()

                test_cases.append(
                    ParityTestCase(
                        name=f"real_crash_log_{crash_file.stem}",
                        description=f"Validate parity with real crash log: {crash_file.name}",
                        inputs={"crash_data": crash_data},
                        expected_output_type=tuple,
                        timeout_seconds=60.0,
                        metadata={
                            "real_crash_log": True,
                            "file_path": str(crash_file),
                            "file_size": crash_file.stat().st_size,
                            "line_count": len(crash_data),
                        },
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to load crash log {crash_file}: {e}")

        return test_cases


class ParityMockYamlSettingsCache:
    """
    Mock YAML settings cache for consistent testing.

    Provides deterministic settings data for both Rust and Python
    implementations to ensure identical configuration during parity tests.
    """

    def __init__(self):
        """Initialize with default test settings."""
        self._settings = {
            "show_formid_values": True,
            "formid_db_exists": False,
            "enable_advanced_analysis": True,
            "plugin_analysis_enabled": True,
            "record_scanning_enabled": True,
            "report_generation_enabled": True,
            "debug_mode": False,
            "performance_monitoring": True,
        }

    def batch_get_settings(self, setting_requests: list[tuple]) -> list[Any]:
        """
        Batch retrieve settings for testing.

        Args:
            setting_requests: List of (type, section, key) tuples

        Returns:
            List of setting values
        """
        results = []
        for request in setting_requests:
            if len(request) >= 3:
                key = request[2]
                value = self._settings.get(key, None)
                # Apply type conversion if specified
                if len(request) >= 1 and request[0] and value is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        value = request[0](value)
                results.append(value)
            else:
                results.append(None)
        return results

    def set_test_setting(self, key: str, value: Any) -> None:
        """Set a setting for testing purposes."""
        self._settings[key] = value

    def get_test_settings_dict(self) -> dict[str, Any]:
        """Get all settings as dictionary for initialization."""
        return self._settings.copy()


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def parity_crash_generator():
    """Fixture providing crash log generator for parity tests."""
    # Try to use real crash logs if available
    crash_logs_dir = Path("D:/Crash Logs") if Path("D:/Crash Logs").exists() else None
    return CrashLogParityGenerator(crash_logs_dir=crash_logs_dir)


@pytest.fixture
def parity_mock_yaml_cache():
    """Fixture providing mock YAML settings cache."""
    return ParityMockYamlSettingsCache()


@pytest.fixture
def parity_sample_crash_data():
    """Fixture providing sample crash log data for testing."""
    factory = CrashLogFactory(seed=42)
    return factory.generate_crash_log(CrashLogType.BUFFOUT4_BASIC, formid_count=50, plugin_count=100)


@pytest.fixture
def parity_mock_scanlog_info(parity_mock_yaml_cache):
    """Fixture providing mock ClassicScanLogsInfo for testing.

    This fixture provides a comprehensive mock with all attributes required
    by the various analyzers (PluginAnalyzer, FormIDAnalyzer, RecordScanner, etc.).
    """
    mock_info = Mock(spec=ClassicScanLogsInfo)

    # Configure mock attributes that Rust/Python implementations expect
    mock_info.show_formid_values = True
    mock_info.formid_db_exists = False
    mock_info.debug_mode = False
    mock_info.enable_advanced_analysis = True

    # PluginAnalyzer required attributes
    mock_info.game_ignore_plugins = [
        "Fallout4.esm",
        "DLCRobot.esm",
        "DLCworkshop01.esm",
        "DLCCoast.esm",
        "DLCworkshop02.esm",
        "DLCworkshop03.esm",
        "DLCNukaWorld.esm",
    ]
    mock_info.ignore_list = []

    # Plugin limit detection required attributes (str, not Version)
    mock_info.game_version = "1.10.163"
    mock_info.game_version_new = "1.10.984"
    mock_info.game_version_vr = "1.2.72"

    # CrashGen info (required by plugin_match)
    mock_info.crashgen_name = "Buffout 4"
    mock_info.crashgen_name_vr = "Buffout 4 VR"
    mock_info.crashgen_latest_og = "1.32.1"
    mock_info.crashgen_latest_vr = "1.32.1"
    # Note: Rust bindings expect sequences (lists), not sets
    mock_info.crashgen_ignore = []
    mock_info.crashgen_ignore_vr = []

    # Additional attributes for FormIDAnalyzer
    mock_info.classic_game_hints = []
    mock_info.classic_records_list = []
    mock_info.game_ignore_records = []

    # Mod configuration (for Mods analysis)
    mock_info.game_mods_conf = {}
    mock_info.game_mods_core = {}
    mock_info.game_mods_core_folon = {}
    mock_info.game_mods_freq = {}
    mock_info.game_mods_opc2 = {}
    mock_info.game_mods_solu = {}

    # Suspect checking data
    mock_info.suspects_error_list = {}
    mock_info.suspects_stack_list = {}

    # Warning messages
    mock_info.warn_noplugins = "No plugins detected"
    mock_info.warn_outdated = "Outdated version detected"

    # XSE info
    mock_info.xse_acronym = "F4SE"

    # Game root names
    mock_info.game_root_name = "Fallout4"
    mock_info.game_root_name_vr = "Fallout4VR"

    # Helper methods
    mock_info.get_crashgen_name = Mock(side_effect=lambda is_vr: mock_info.crashgen_name_vr if is_vr else mock_info.crashgen_name)
    mock_info.get_crashgen_ignore = Mock(side_effect=lambda is_vr: mock_info.crashgen_ignore_vr if is_vr else mock_info.crashgen_ignore)
    mock_info.get_game_root_name = Mock(side_effect=lambda is_vr: mock_info.game_root_name_vr if is_vr else mock_info.game_root_name)
    # Mock YAML cache integration
    mock_info.yaml_cache = parity_mock_yaml_cache

    return mock_info


@pytest.fixture
def parity_async_bridge():
    """Fixture providing AsyncBridge instance."""
    return AsyncBridge.get_instance()


# ============================================================================
# Utility Functions
# ============================================================================


def skip_if_rust_unavailable(component: str):
    """
    Pytest decorator to skip tests if specific Rust component is unavailable.

    Args:
        component: Name of the Rust component to check

    Returns:
        Pytest skipif marker
    """
    return pytest.mark.skipif(not RUST_AVAILABLE.get(component, False), reason=f"Rust {component} component not available")


def requires_crash_logs_directory():
    """
    Pytest decorator to skip tests that require real crash logs directory.

    Returns:
        Pytest skipif marker
    """
    return pytest.mark.skipif(not Path("D:/Crash Logs").exists(), reason="Real crash logs directory not available")


class ParityTestRunner:
    """
    Comprehensive test runner for executing parity validation tests.

    Manages test execution, result collection, performance monitoring,
    and detailed reporting for Phase 6 validation requirements.
    """

    def __init__(self, output_file: Path | None = None):
        """
        Initialize the parity test runner.

        Args:
            output_file: Optional file path for detailed result output
        """
        self.output_file = output_file
        self.results: list[ParityResult] = []
        self.bridge = AsyncBridge.get_instance()
        self.logger = logging.getLogger("parity_runner")

    async def run_parity_test(self, validator: ParityValidator, test_case: ParityTestCase) -> ParityResult:
        """
        Run a single parity test case.

        Args:
            validator: Component validator to use
            test_case: Test case to execute

        Returns:
            ParityResult with validation outcome
        """
        result = ParityResult(
            component_name=validator.component_name,
            method_name=test_case.name,
            test_case=test_case.description,
            rust_available=RUST_AVAILABLE.get(validator.component_name.lower(), False),
            passed=False,  # Initialize with False, will be updated later
        )

        try:
            # Setup if needed
            if test_case.setup_function:
                test_case.setup_function()

            # Execute both implementations with timing
            rust_impl = validator.create_rust_implementation(**test_case.inputs)
            python_impl = validator.create_python_implementation(**test_case.inputs)

            # Time Rust execution
            import time

            start_time = time.perf_counter()
            rust_result = await self._execute_with_timeout(rust_impl, test_case.inputs, test_case.timeout_seconds)
            result.rust_execution_time = time.perf_counter() - start_time

            # Time Python execution
            start_time = time.perf_counter()
            python_result = await self._execute_with_timeout(python_impl, test_case.inputs, test_case.timeout_seconds)
            result.python_execution_time = time.perf_counter() - start_time

            # Store results
            result.rust_result = rust_result
            result.python_result = python_result

            # Calculate performance improvement
            if result.python_execution_time > 0 and result.rust_execution_time > 0:
                result.performance_improvement = result.python_execution_time / result.rust_execution_time

            # Validate outputs
            is_identical, differences = validator.validate_outputs(rust_result, python_result, test_case)
            result.passed = is_identical
            result.differences = differences

        except Exception as e:
            result.passed = False
            result.error_messages.append(str(e))
            self.logger.error(f"Parity test failed for {test_case.name}: {e}")

        finally:
            # Teardown if needed
            if test_case.teardown_function:
                try:
                    test_case.teardown_function()
                except Exception as e:
                    result.error_messages.append(f"Teardown error: {e}")

        self.results.append(result)
        return result

    async def _execute_with_timeout(self, impl: Any, inputs: dict[str, Any], timeout_duration: float) -> Any:
        """Execute implementation with timeout protection."""
        # This is a placeholder - actual implementation would depend on
        # the specific interface of each component
        if inspect.iscoroutinefunction(getattr(impl, "execute", None)):
            return await asyncio.wait_for(impl.execute(**inputs), timeout=timeout_duration)
        if hasattr(impl, "execute"):
            return impl.execute(**inputs)
        return impl  # If impl is the result itself

    def generate_parity_report(self) -> dict[str, Any]:
        """
        Generate comprehensive parity validation report.

        Returns:
            Dictionary containing detailed validation results and statistics
        """
        if not self.results:
            return {"error": "No test results available"}

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        # Calculate performance statistics
        performance_improvements = [r.performance_improvement for r in self.results if r.performance_improvement > 0]

        avg_improvement = sum(performance_improvements) / len(performance_improvements) if performance_improvements else 0

        # Group results by component
        by_component = {}
        for result in self.results:
            if result.component_name not in by_component:
                by_component[result.component_name] = {"total": 0, "passed": 0, "failed": 0, "results": []}

            by_component[result.component_name]["total"] += 1
            by_component[result.component_name]["results"].append(result.to_dict())

            if result.passed:
                by_component[result.component_name]["passed"] += 1
            else:
                by_component[result.component_name]["failed"] += 1

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "average_performance_improvement": f"{avg_improvement:.1f}x",
                "rust_availability": {component: RUST_AVAILABLE.get(component, False) for component in by_component},
            },
            "by_component": by_component,
            "failed_tests_details": [
                {"component": r.component_name, "test": r.method_name, "differences": r.differences, "errors": r.error_messages}
                for r in self.results
                if not r.passed
            ],
        }

        # Write detailed report to file if specified
        if self.output_file:
            try:
                with Path(self.output_file).open("w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                self.logger.info(f"Detailed parity report written to {self.output_file}")
            except Exception as e:
                self.logger.error(f"Failed to write report file: {e}")

        return report


# ============================================================================
# Utility functions for common parity validations
# ============================================================================


def validate_formid_lists(rust_formids: list[str], python_formids: list[str]) -> tuple[bool, list[str]]:
    """
    Validate that FormID lists are identical.

    Args:
        rust_formids: FormIDs extracted by Rust implementation
        python_formids: FormIDs extracted by Python implementation

    Returns:
        Tuple of (is_identical, list_of_differences)
    """
    differences = []

    if len(rust_formids) != len(python_formids):
        differences.append(f"FormID count mismatch: Rust={len(rust_formids)}, Python={len(python_formids)}")

    # Compare as sets for order-independent comparison
    rust_set = set(rust_formids)
    python_set = set(python_formids)

    missing_in_rust = python_set - rust_set
    missing_in_python = rust_set - python_set

    if missing_in_rust:
        differences.append(f"FormIDs missing in Rust: {missing_in_rust}")
    if missing_in_python:
        differences.append(f"FormIDs missing in Python: {missing_in_python}")

    # For exact parity, also check order
    if rust_formids != python_formids:
        differences.append("FormID order differs between implementations")

    return len(differences) == 0, differences


def validate_plugin_dictionaries(rust_plugins: dict[str, str], python_plugins: dict[str, str]) -> tuple[bool, list[str]]:
    """
    Validate that plugin dictionaries are identical.

    Args:
        rust_plugins: Plugin dictionary from Rust implementation
        python_plugins: Plugin dictionary from Python implementation

    Returns:
        Tuple of (is_identical, list_of_differences)
    """
    differences = []

    rust_keys = set(rust_plugins.keys())
    python_keys = set(python_plugins.keys())

    if rust_keys != python_keys:
        missing_in_rust = python_keys - rust_keys
        missing_in_python = rust_keys - python_keys

        if missing_in_rust:
            differences.append(f"Plugin indices missing in Rust: {missing_in_rust}")
        if missing_in_python:
            differences.append(f"Plugin indices missing in Python: {missing_in_python}")

    # Compare values for common keys
    common_keys = rust_keys & python_keys
    differences.extend(
        f"Plugin mismatch at index {key}: Rust='{rust_plugins[key]}', Python='{python_plugins[key]}'"
        for key in common_keys
        if rust_plugins[key] != python_plugins[key]
    )

    return len(differences) == 0, differences


def normalize_markdown_content(content: str) -> str:
    """
    Normalize markdown content for consistent comparison.

    Args:
        content: Raw markdown content

    Returns:
        Normalized content with consistent line endings and whitespace
    """
    if not content:
        return ""

    # Normalize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Remove trailing whitespace from lines
    lines = []
    lines.extend(line.rstrip() for line in content.split("\n"))

    # Remove empty lines at the end
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines)


# ============================================================================
# Backward compatibility aliases (deprecated - use prefixed names)
# ============================================================================

# Renamed class for clarity
MockYamlSettingsCache = ParityMockYamlSettingsCache

# Fixture aliases
mock_yaml_cache = parity_mock_yaml_cache
sample_crash_data = parity_sample_crash_data
mock_scanlog_info = parity_mock_scanlog_info
async_bridge = parity_async_bridge

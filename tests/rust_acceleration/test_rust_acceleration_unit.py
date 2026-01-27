"""Unit tests for ClassicLib.RustAcceleration module.

This module tests the RustAcceleration coordinator, ComponentMetrics,
ComponentType, WorkloadCharacteristics, and OptimizationLevel components.
Tests are designed to work regardless of whether actual Rust components
are available.
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.acceleration.metrics import ComponentMetrics
from ClassicLib.acceleration.types import ComponentType
from ClassicLib.acceleration.workload import OptimizationLevel, WorkloadCharacteristics

if TYPE_CHECKING:
    from collections.abc import Generator


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_rust_status() -> dict[str, bool]:
    """Create a mock Rust component status dict.

    Returns:
        Dictionary with all components set to False by default.
    """
    return {
        "parser": False,
        "formid_analyzer": False,
        "plugin_analyzer": False,
        "record_scanner": False,
        "report_generation": False,
        "database_pool": False,
        "file_io_core": False,
        "mod_detector": False,
    }


@pytest.fixture
def mock_rust_component_status() -> dict[str, Any]:
    """Create a mock for get_rust_component_status.

    Returns:
        Dictionary simulating component status response.
    """
    return {
        "active_count": 0,
        "total_count": 8,
        "percentage": 0.0,
        "available": {},
    }


@pytest.fixture
def isolated_rust_acceleration() -> Generator[None, None, None]:
    """Provide an isolated RustAcceleration instance for each test.

    Yields:
        None - Resets the singleton after the test.
    """
    # Import here to avoid module-level side effects
    from ClassicLib.acceleration.coordinator import RustAcceleration

    # Ensure clean state before test
    old_instance = RustAcceleration._instance

    # Set PYTEST_CURRENT_TEST if not already set (for reset_instance)
    test_env = os.environ.get("PYTEST_CURRENT_TEST")
    if not test_env:
        os.environ["PYTEST_CURRENT_TEST"] = "test_rust_acceleration"

    try:
        # Reset singleton for clean test
        with RustAcceleration._lock:
            RustAcceleration._instance = None

        yield
    finally:
        # Restore original state
        with RustAcceleration._lock:
            RustAcceleration._instance = old_instance

        # Clean up test env if we set it
        if not test_env:
            os.environ.pop("PYTEST_CURRENT_TEST", None)


# ============================================================================
# ComponentMetrics Tests
# ============================================================================


class TestComponentMetrics:
    """Tests for ComponentMetrics dataclass."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test ComponentMetrics initializes with correct defaults."""
        metrics = ComponentMetrics(name="test_component")

        assert metrics.name == "test_component"
        assert metrics.calls == 0
        assert metrics.total_time == 0.0
        assert metrics.min_time == float("inf")
        assert metrics.max_time == 0.0
        assert metrics.errors == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.last_error is None

    @pytest.mark.unit
    def test_avg_time_with_no_calls(self) -> None:
        """Test avg_time returns 0 when no calls recorded."""
        metrics = ComponentMetrics(name="test")

        assert metrics.avg_time == 0.0

    @pytest.mark.unit
    def test_avg_time_with_calls(self) -> None:
        """Test avg_time calculation with multiple calls."""
        metrics = ComponentMetrics(name="test")

        metrics.record_call(1.0)
        metrics.record_call(2.0)
        metrics.record_call(3.0)

        assert metrics.avg_time == 2.0  # (1 + 2 + 3) / 3

    @pytest.mark.unit
    def test_record_call_updates_statistics(self) -> None:
        """Test record_call properly updates all statistics."""
        metrics = ComponentMetrics(name="test")

        metrics.record_call(0.5)

        assert metrics.calls == 1
        assert metrics.total_time == 0.5
        assert metrics.min_time == 0.5
        assert metrics.max_time == 0.5
        assert metrics.cache_misses == 1
        assert metrics.cache_hits == 0

    @pytest.mark.unit
    def test_record_call_with_cache_hit(self) -> None:
        """Test record_call correctly tracks cache hits."""
        metrics = ComponentMetrics(name="test")

        metrics.record_call(0.1, cache_hit=True)
        metrics.record_call(0.2, cache_hit=False)
        metrics.record_call(0.15, cache_hit=True)

        assert metrics.cache_hits == 2
        assert metrics.cache_misses == 1

    @pytest.mark.unit
    def test_record_call_min_max_tracking(self) -> None:
        """Test record_call properly tracks min and max times."""
        metrics = ComponentMetrics(name="test")

        metrics.record_call(0.5)
        metrics.record_call(0.1)
        metrics.record_call(1.0)
        metrics.record_call(0.3)

        assert metrics.min_time == 0.1
        assert metrics.max_time == 1.0

    @pytest.mark.unit
    def test_cache_hit_rate_with_no_accesses(self) -> None:
        """Test cache_hit_rate returns 0 when no accesses."""
        metrics = ComponentMetrics(name="test")

        assert metrics.cache_hit_rate == 0.0

    @pytest.mark.unit
    def test_cache_hit_rate_calculation(self) -> None:
        """Test cache_hit_rate calculates percentage correctly."""
        metrics = ComponentMetrics(name="test")

        # 3 hits, 7 misses = 30% hit rate
        for _ in range(3):
            metrics.record_call(0.1, cache_hit=True)
        for _ in range(7):
            metrics.record_call(0.1, cache_hit=False)

        assert metrics.cache_hit_rate == 30.0

    @pytest.mark.unit
    def test_record_error_increments_count(self) -> None:
        """Test record_error increments error count."""
        metrics = ComponentMetrics(name="test")

        metrics.record_error("First error")
        assert metrics.errors == 1

        metrics.record_error("Second error")
        assert metrics.errors == 2

    @pytest.mark.unit
    def test_record_error_stores_last_error(self) -> None:
        """Test record_error stores the most recent error message."""
        metrics = ComponentMetrics(name="test")

        metrics.record_error("First error")
        assert metrics.last_error == "First error"

        metrics.record_error("Second error")
        assert metrics.last_error == "Second error"


# ============================================================================
# ComponentType Tests
# ============================================================================


class TestComponentType:
    """Tests for ComponentType enum."""

    @pytest.mark.unit
    def test_all_component_types_defined(self) -> None:
        """Test all expected component types are defined."""
        expected_types = [
            "PARSER",
            "FORMID_ANALYZER",
            "PLUGIN_ANALYZER",
            "RECORD_SCANNER",
            "REPORT_GENERATION",
            "DATABASE_POOL",
            "FILE_IO_CORE",
            "MOD_DETECTOR",
        ]

        for type_name in expected_types:
            assert hasattr(ComponentType, type_name)

    @pytest.mark.unit
    def test_component_type_values(self) -> None:
        """Test component type values are lowercase strings."""
        assert ComponentType.PARSER.value == "parser"
        assert ComponentType.FORMID_ANALYZER.value == "formid_analyzer"
        assert ComponentType.FILE_IO_CORE.value == "file_io_core"
        assert ComponentType.MOD_DETECTOR.value == "mod_detector"

    @pytest.mark.unit
    def test_component_types_are_unique(self) -> None:
        """Test all component type values are unique."""
        values = [ct.value for ct in ComponentType]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    def test_component_types_iterable(self) -> None:
        """Test ComponentType can be iterated."""
        types = list(ComponentType)
        assert len(types) == 8


# ============================================================================
# OptimizationLevel Tests
# ============================================================================


class TestOptimizationLevel:
    """Tests for OptimizationLevel enum."""

    @pytest.mark.unit
    def test_all_levels_defined(self) -> None:
        """Test all optimization levels are defined."""
        expected_levels = ["DISABLED", "MINIMAL", "BALANCED", "AGGRESSIVE", "ADAPTIVE"]

        for level in expected_levels:
            assert hasattr(OptimizationLevel, level)

    @pytest.mark.unit
    def test_level_ordering(self) -> None:
        """Test optimization levels have correct ordering values."""
        assert OptimizationLevel.DISABLED.value == 0
        assert OptimizationLevel.MINIMAL.value == 1
        assert OptimizationLevel.BALANCED.value == 2
        assert OptimizationLevel.AGGRESSIVE.value == 3
        assert OptimizationLevel.ADAPTIVE.value == 4

    @pytest.mark.unit
    def test_level_comparison(self) -> None:
        """Test optimization levels can be compared by value."""
        assert OptimizationLevel.MINIMAL.value < OptimizationLevel.BALANCED.value
        assert OptimizationLevel.BALANCED.value < OptimizationLevel.AGGRESSIVE.value


# ============================================================================
# WorkloadCharacteristics Tests
# ============================================================================


class TestWorkloadCharacteristics:
    """Tests for WorkloadCharacteristics dataclass."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test WorkloadCharacteristics initializes with correct defaults."""
        workload = WorkloadCharacteristics()

        assert workload.file_count == 0
        assert workload.total_file_size == 0
        assert workload.formid_count == 0
        assert workload.plugin_count == 0
        assert workload.database_queries == 0
        assert workload.report_fragments == 0
        assert workload.is_batch_operation is False
        assert workload.is_memory_constrained is False
        assert workload.extended_metrics == {}

    @pytest.mark.unit
    def test_custom_initialization(self) -> None:
        """Test WorkloadCharacteristics with custom values."""
        workload = WorkloadCharacteristics(
            file_count=10,
            formid_count=500,
            plugin_count=100,
            is_batch_operation=True,
        )

        assert workload.file_count == 10
        assert workload.formid_count == 500
        assert workload.plugin_count == 100
        assert workload.is_batch_operation is True

    @pytest.mark.unit
    def test_determine_optimization_level_minimal_on_many_errors(self) -> None:
        """Test returns MINIMAL when many component errors."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {"component_errors": 5}

        assert workload.determine_optimization_level() == OptimizationLevel.MINIMAL

    @pytest.mark.unit
    def test_determine_optimization_level_aggressive_for_large_batch(self) -> None:
        """Test returns AGGRESSIVE for large batch with good acceleration."""
        workload = WorkloadCharacteristics(
            file_count=20,
            is_batch_operation=True,
        )
        workload.extended_metrics = {"acceleration_percentage": 80}

        assert workload.determine_optimization_level() == OptimizationLevel.AGGRESSIVE

    @pytest.mark.unit
    def test_determine_optimization_level_balanced_default(self) -> None:
        """Test returns BALANCED as default."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {}

        assert workload.determine_optimization_level() == OptimizationLevel.BALANCED

    @pytest.mark.unit
    def test_determine_optimization_level_balanced_on_memory_constrained(self) -> None:
        """Test returns BALANCED when memory constrained."""
        workload = WorkloadCharacteristics(is_memory_constrained=True)
        workload.extended_metrics = {"acceleration_percentage": 90}

        assert workload.determine_optimization_level() == OptimizationLevel.BALANCED

    @pytest.mark.unit
    def test_determine_optimization_level_aggressive_on_high_db_queries(self) -> None:
        """Test returns AGGRESSIVE for high database queries."""
        workload = WorkloadCharacteristics(database_queries=150)
        workload.extended_metrics = {"acceleration_percentage": 60}

        assert workload.determine_optimization_level() == OptimizationLevel.AGGRESSIVE

    @pytest.mark.unit
    def test_determine_optimization_level_aggressive_on_many_plugins(self) -> None:
        """Test returns AGGRESSIVE for many plugins with good acceleration."""
        workload = WorkloadCharacteristics(plugin_count=250)
        workload.extended_metrics = {"acceleration_percentage": 70}

        assert workload.determine_optimization_level() == OptimizationLevel.AGGRESSIVE

    @pytest.mark.unit
    def test_determine_optimization_level_aggressive_on_many_formids(self) -> None:
        """Test returns AGGRESSIVE for many FormIDs with good acceleration."""
        workload = WorkloadCharacteristics(formid_count=600)
        workload.extended_metrics = {"acceleration_percentage": 60}

        assert workload.determine_optimization_level() == OptimizationLevel.AGGRESSIVE

    @pytest.mark.unit
    def test_determine_optimization_level_balanced_on_slow_parse_low_accel(self) -> None:
        """Test returns BALANCED when parsing is slow and low acceleration."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {
            "acceleration_percentage": 40,
            "parse_time": 3.0,
        }

        assert workload.determine_optimization_level() == OptimizationLevel.BALANCED

    @pytest.mark.unit
    def test_get_performance_score_base(self) -> None:
        """Test base performance score is 50."""
        workload = WorkloadCharacteristics()
        # No extended metrics = base score only
        workload.extended_metrics = {}

        score = workload.get_performance_score()
        assert score == 50.0

    @pytest.mark.unit
    def test_get_performance_score_full_acceleration(self) -> None:
        """Test performance score with full acceleration bonus."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {"acceleration_percentage": 100}

        score = workload.get_performance_score()
        # 50 (base) + 30 (100% acceleration)
        assert score == 80.0

    @pytest.mark.unit
    def test_get_performance_score_with_cache_bonus(self) -> None:
        """Test performance score includes cache utilization bonus."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {
            "acceleration_percentage": 0,
            "cache_utilization": 100,
        }

        score = workload.get_performance_score()
        # 50 (base) + 0 (no accel) + 15 (full cache)
        assert score == 65.0

    @pytest.mark.unit
    def test_get_performance_score_with_error_penalty(self) -> None:
        """Test performance score applies error penalty."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {"component_errors": 3}

        score = workload.get_performance_score()
        # 50 (base) - 15 (3 errors * 5)
        assert score == 35.0

    @pytest.mark.unit
    def test_get_performance_score_error_penalty_capped(self) -> None:
        """Test error penalty is capped at 20 points."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {"component_errors": 10}

        score = workload.get_performance_score()
        # 50 (base) - 20 (capped penalty)
        assert score == 30.0

    @pytest.mark.unit
    def test_get_performance_score_fast_parse_bonus(self) -> None:
        """Test fast parsing gives bonus."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {"parse_time": 0.05}

        score = workload.get_performance_score()
        # 50 (base) + 5 (fast parse)
        assert score == 55.0

    @pytest.mark.unit
    def test_get_performance_score_slow_parse_penalty(self) -> None:
        """Test slow parsing applies penalty."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {"parse_time": 6.0}

        score = workload.get_performance_score()
        # 50 (base) - 10 (slow parse)
        assert score == 40.0

    @pytest.mark.unit
    def test_get_performance_score_clamped_to_100(self) -> None:
        """Test score is clamped to maximum 100."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {
            "acceleration_percentage": 100,
            "cache_utilization": 100,
            "parse_time": 0.05,
        }

        score = workload.get_performance_score()
        # 50 + 30 + 15 + 5 = 100 (clamped)
        assert score == 100.0

    @pytest.mark.unit
    def test_get_performance_score_clamped_to_0(self) -> None:
        """Test score is clamped to minimum 0."""
        workload = WorkloadCharacteristics()
        workload.extended_metrics = {
            "component_errors": 10,  # -20
            "parse_time": 10.0,  # -10
            "acceleration_percentage": 0,
        }

        score = workload.get_performance_score()
        # 50 - 20 - 10 = 20
        assert score == 20.0


# ============================================================================
# RustAcceleration Coordinator Tests
# ============================================================================


class TestRustAccelerationSingleton:
    """Tests for RustAcceleration singleton pattern."""

    @pytest.mark.unit
    def test_singleton_returns_same_instance(self, isolated_rust_acceleration: None) -> None:
        """Test RustAcceleration returns the same instance."""
        from ClassicLib.acceleration.coordinator import RustAcceleration

        instance1 = RustAcceleration()
        instance2 = RustAcceleration()

        assert instance1 is instance2

    @pytest.mark.unit
    def test_get_instance_returns_same_instance(self, isolated_rust_acceleration: None) -> None:
        """Test get_instance returns the singleton."""
        from ClassicLib.acceleration.coordinator import RustAcceleration

        instance1 = RustAcceleration.get_instance()
        instance2 = RustAcceleration.get_instance()

        assert instance1 is instance2

    @pytest.mark.unit
    def test_reset_instance_requires_test_context(self, isolated_rust_acceleration: None) -> None:
        """Test reset_instance only works in pytest context."""
        from ClassicLib.acceleration.coordinator import RustAcceleration

        # Save and clear the test environment variable
        original = os.environ.pop("PYTEST_CURRENT_TEST", None)

        try:
            with pytest.raises(RuntimeError, match="only allowed in testing contexts"):
                RustAcceleration.reset_instance()
        finally:
            # Restore
            if original:
                os.environ["PYTEST_CURRENT_TEST"] = original

    @pytest.mark.unit
    def test_singleton_thread_safety(self, isolated_rust_acceleration: None) -> None:
        """Test singleton is thread-safe."""
        from ClassicLib.acceleration.coordinator import RustAcceleration

        instances: list[RustAcceleration] = []
        errors: list[Exception] = []

        def get_instance() -> None:
            try:
                instances.append(RustAcceleration.get_instance())
            except Exception as e:
                errors.append(e)

        # Create multiple threads that get the instance
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_instance) for _ in range(20)]
            for future in futures:
                future.result()

        assert not errors
        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)


class TestRustAccelerationInitialization:
    """Tests for RustAcceleration initialization."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_initialization_sets_defaults(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test initialization sets correct default values."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        assert accel.optimization_level == OptimizationLevel.BALANCED
        assert isinstance(accel.metrics, dict)
        assert isinstance(accel.workload, WorkloadCharacteristics)
        assert len(accel.metrics) == len(ComponentType)

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_initialization_creates_metrics_for_all_components(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test initialization creates metrics for all component types."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        for component_type in ComponentType:
            assert component_type in accel.metrics
            assert accel.metrics[component_type].name == component_type.value


class TestRustAccelerationGetComponent:
    """Tests for RustAcceleration.get_component method."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    @patch("ClassicLib.acceleration.coordinator.get_parser")
    def test_get_component_caches_result(
        self,
        mock_get_parser: MagicMock,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test get_component caches components."""
        mock_status.return_value = mock_rust_component_status
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        # First call
        result1 = accel.get_component(ComponentType.PARSER)
        # Second call should use cache
        result2 = accel.get_component(ComponentType.PARSER)

        assert result1 is result2
        # get_parser should only be called once
        mock_get_parser.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    @patch("ClassicLib.acceleration.coordinator.get_parser")
    def test_get_component_records_metrics(
        self,
        mock_get_parser: MagicMock,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test get_component records call metrics."""
        mock_status.return_value = mock_rust_component_status
        mock_get_parser.return_value = MagicMock()

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        accel.get_component(ComponentType.PARSER)

        assert accel.metrics[ComponentType.PARSER].calls == 1

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    @patch("ClassicLib.acceleration.coordinator.get_parser")
    def test_get_component_records_errors(
        self,
        mock_get_parser: MagicMock,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test get_component records errors when component creation fails."""
        mock_status.return_value = mock_rust_component_status
        mock_get_parser.side_effect = RuntimeError("Failed to load parser")

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        accel.get_component(ComponentType.PARSER)

        assert accel.metrics[ComponentType.PARSER].errors == 1
        assert "Failed to load parser" in accel.metrics[ComponentType.PARSER].last_error


class TestRustAccelerationWorkload:
    """Tests for RustAcceleration workload management."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_update_workload_characteristics(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test update_workload_characteristics updates workload."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        accel.update_workload_characteristics(
            file_count=10,
            formid_count=500,
            plugin_count=100,
            is_batch=True,
        )

        assert accel.workload.file_count == 10
        assert accel.workload.formid_count == 500
        assert accel.workload.plugin_count == 100
        assert accel.workload.is_batch_operation is True

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_update_workload_with_extended_metrics(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test update_workload_characteristics with extended metrics."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        accel.update_workload_characteristics(
            file_count=5,
            acceleration_percentage=85.0,
            cache_utilization=70.0,
            parse_time=0.5,
        )

        assert accel.workload.extended_metrics["acceleration_percentage"] == 85.0
        assert accel.workload.extended_metrics["cache_utilization"] == 70.0
        assert accel.workload.extended_metrics["parse_time"] == 0.5


class TestRustAccelerationOptimization:
    """Tests for RustAcceleration optimization level management."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_set_optimization_level(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test set_optimization_level updates the level."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        accel.set_optimization_level(OptimizationLevel.AGGRESSIVE)

        assert accel.optimization_level == OptimizationLevel.AGGRESSIVE

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_set_all_optimization_levels(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test all optimization levels can be set."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        for level in OptimizationLevel:
            accel.set_optimization_level(level)
            assert accel.optimization_level == level


class TestRustAccelerationPerformanceReport:
    """Tests for RustAcceleration performance reporting."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    @patch("ClassicLib.acceleration.coordinator.is_rust_accelerated")
    def test_get_performance_report_structure(
        self,
        mock_is_rust: MagicMock,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test get_performance_report returns correct structure."""
        mock_status.return_value = mock_rust_component_status
        mock_is_rust.return_value = False

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        report = accel.get_performance_report()

        # Check required keys
        assert "uptime_seconds" in report
        assert "total_calls" in report
        assert "total_errors" in report
        assert "error_rate" in report
        assert "optimization_level" in report
        assert "acceleration_factor" in report
        assert "rust_components_active" in report
        assert "total_components" in report
        assert "component_metrics" in report
        assert "workload_characteristics" in report

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    @patch("ClassicLib.acceleration.coordinator.is_rust_accelerated")
    def test_get_performance_report_calculates_error_rate(
        self,
        mock_is_rust: MagicMock,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test get_performance_report calculates error rate correctly."""
        mock_status.return_value = mock_rust_component_status
        mock_is_rust.return_value = False

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        # Record some calls and errors
        accel.metrics[ComponentType.PARSER].calls = 100
        accel.metrics[ComponentType.PARSER].errors = 5

        report = accel.get_performance_report()

        # 5 errors / 100 calls = 5%
        assert report["error_rate"] == 5.0


class TestRustAccelerationHealthCheck:
    """Tests for RustAcceleration health check."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_health_check_healthy_when_no_issues(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
    ) -> None:
        """Test health_check returns healthy when no issues."""
        mock_status.return_value = {
            "active_count": 8,
            "total_count": 8,
        }

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        is_healthy, issues = accel.health_check()

        assert is_healthy is True
        assert issues == []

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {"parser": False})
    def test_health_check_reports_missing_components(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
    ) -> None:
        """Test health_check reports missing components."""
        mock_status.return_value = {
            "active_count": 7,
            "total_count": 8,
        }

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()
        is_healthy, issues = accel.health_check()

        assert is_healthy is False
        assert any("Missing components" in issue for issue in issues)

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_health_check_reports_high_error_rate(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
    ) -> None:
        """Test health_check reports high error rates."""
        mock_status.return_value = {
            "active_count": 8,
            "total_count": 8,
        }

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        # Set high error rate for a component
        accel.metrics[ComponentType.PARSER].calls = 100
        accel.metrics[ComponentType.PARSER].errors = 10  # 10% error rate

        is_healthy, issues = accel.health_check()

        assert is_healthy is False
        assert any("High error rate" in issue for issue in issues)

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_health_check_reports_slow_performance(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
    ) -> None:
        """Test health_check reports slow component performance."""
        mock_status.return_value = {
            "active_count": 8,
            "total_count": 8,
        }

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        # Set slow average time for a component
        accel.metrics[ComponentType.PARSER].calls = 20
        accel.metrics[ComponentType.PARSER].total_time = 30  # 1.5s average

        is_healthy, issues = accel.health_check()

        assert is_healthy is False
        assert any("Slow performance" in issue for issue in issues)


class TestRustAccelerationResetMetrics:
    """Tests for RustAcceleration.reset_metrics method."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_reset_metrics_clears_all_metrics(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test reset_metrics clears all component metrics."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import RustAcceleration

        accel = RustAcceleration()

        # Add some metrics
        accel.metrics[ComponentType.PARSER].calls = 100
        accel.metrics[ComponentType.PARSER].errors = 5

        accel.reset_metrics()

        assert accel.metrics[ComponentType.PARSER].calls == 0
        assert accel.metrics[ComponentType.PARSER].errors == 0


# ============================================================================
# Module-Level Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_get_rust_acceleration_returns_instance(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test get_rust_acceleration returns singleton."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import (
            RustAcceleration,
            get_rust_acceleration,
        )

        accel = get_rust_acceleration()

        assert isinstance(accel, RustAcceleration)

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_configure_for_batch_processing_sets_aggressive(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test configure_for_batch_processing sets aggressive for large batches."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import (
            configure_for_batch_processing,
            get_rust_acceleration,
        )

        configure_for_batch_processing(file_count=20)
        accel = get_rust_acceleration()

        assert accel.optimization_level == OptimizationLevel.AGGRESSIVE
        assert accel.workload.file_count == 20
        assert accel.workload.is_batch_operation is True

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_configure_for_batch_processing_sets_balanced_for_small_batch(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test configure_for_batch_processing sets balanced for small batches."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import (
            configure_for_batch_processing,
            get_rust_acceleration,
        )

        configure_for_batch_processing(file_count=5)
        accel = get_rust_acceleration()

        assert accel.optimization_level == OptimizationLevel.BALANCED

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_configure_for_single_file(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
        mock_rust_component_status: dict[str, Any],
    ) -> None:
        """Test configure_for_single_file sets correct configuration."""
        mock_status.return_value = mock_rust_component_status

        from ClassicLib.acceleration.coordinator import (
            configure_for_single_file,
            get_rust_acceleration,
        )

        configure_for_single_file()
        accel = get_rust_acceleration()

        assert accel.workload.file_count == 1
        assert accel.workload.is_batch_operation is False
        assert accel.optimization_level == OptimizationLevel.BALANCED

    @pytest.mark.unit
    @patch("ClassicLib.acceleration.coordinator.get_rust_component_status")
    @patch("ClassicLib.acceleration.coordinator.RUST_AVAILABLE", {})
    def test_perform_health_check_returns_bool(
        self,
        mock_status: MagicMock,
        isolated_rust_acceleration: None,
    ) -> None:
        """Test perform_health_check returns boolean."""
        mock_status.return_value = {
            "active_count": 8,
            "total_count": 8,
        }

        from ClassicLib.acceleration.coordinator import perform_health_check

        result = perform_health_check()

        assert isinstance(result, bool)

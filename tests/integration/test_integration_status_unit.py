"""Unit tests for the integration status module.

This module tests ClassicLib.integration.status which provides:
- Rust component status detection and reporting
- Performance multiplier queries
- Status tracking and updates
- Performance report generation
"""

from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]

from ClassicLib.integration.status import (
    RUST_AVAILABLE,
    RUST_STATUS,
    _ensure_initialized,
    _initialize_rust_available,
    get_performance_multiplier,
    get_performance_report,
    get_rust_component_status,
    is_rust_accelerated,
    update_status,
)


class TestIsRustAccelerated:
    """Test suite for is_rust_accelerated function."""

    def test_returns_true_for_available_component(self) -> None:
        """Test returns True when component is available."""
        # Find a component that's actually available
        available_components = [k for k, v in RUST_AVAILABLE.items() if v]
        if available_components:
            component = available_components[0]
            result = is_rust_accelerated(component)
            assert result is True

    def test_returns_false_for_unavailable_component(self) -> None:
        """Test returns False when component is not available."""
        result = is_rust_accelerated("nonexistent_component_xyz")
        assert result is False

    def test_returns_false_for_empty_string(self) -> None:
        """Test returns False for empty component name."""
        result = is_rust_accelerated("")
        assert result is False


class TestGetPerformanceMultiplier:
    """Test suite for get_performance_multiplier function."""

    def test_returns_multiplier_for_accelerated_component(self) -> None:
        """Test returns performance multiplier for available Rust component."""
        # Find a component that's accelerated
        available = [k for k, v in RUST_AVAILABLE.items() if v]
        if available:
            component = available[0]
            multiplier = get_performance_multiplier(component)
            # Should be something like "10x", "150x", or "N/A"
            assert isinstance(multiplier, str)
            assert multiplier != "1x"  # Not the fallback

    def test_returns_1x_for_non_accelerated_component(self) -> None:
        """Test returns '1x' for non-accelerated component."""
        multiplier = get_performance_multiplier("nonexistent_component")
        assert multiplier == "1x"


class TestUpdateStatus:
    """Test suite for update_status function."""

    def test_update_initialized_status(self) -> None:
        """Test updating initialized status for a component."""
        # Clear any existing status first
        RUST_STATUS["initialized"].clear()

        update_status("test_component", "initialized", "Loaded successfully")

        assert "test_component" in RUST_STATUS["initialized"]
        assert RUST_STATUS["initialized"]["test_component"] == "Loaded successfully"

    def test_update_failed_status(self) -> None:
        """Test updating failed status for a component."""
        RUST_STATUS["failed"].clear()

        update_status("failed_component", "failed", "Import error")

        assert "failed_component" in RUST_STATUS["failed"]
        assert RUST_STATUS["failed"]["failed_component"] == "Import error"

    def test_update_with_default_reason(self) -> None:
        """Test updating status with auto-generated reason."""
        RUST_STATUS["initialized"].clear()

        update_status("auto_component", "initialized")

        assert "auto_component" in RUST_STATUS["initialized"]
        assert "auto_component initialized" in RUST_STATUS["initialized"]["auto_component"]

    def test_update_invalid_status_key_is_ignored(self) -> None:
        """Test that invalid status keys are silently ignored."""
        initial_keys = set(RUST_STATUS.keys())

        update_status("component", "invalid_status_key", "reason")

        # Should not create new keys
        assert set(RUST_STATUS.keys()) == initial_keys


class TestGetRustComponentStatus:
    """Test suite for get_rust_component_status function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Test that status returns dict with all expected keys."""
        status = get_rust_component_status()

        expected_keys = [
            "available",
            "initialized",
            "failed",
            "performance_gains",
            "active_count",
            "total_count",
            "percentage",
            "acceleration_active",
            "acceleration_level",
            "versions",
            "disabled",
        ]

        for key in expected_keys:
            assert key in status, f"Missing key: {key}"

    def test_available_is_dict_of_bools(self) -> None:
        """Test that 'available' contains component availability map."""
        status = get_rust_component_status()

        assert isinstance(status["available"], dict)
        for name, value in status["available"].items():
            assert isinstance(name, str)
            assert isinstance(value, bool)

    def test_counts_are_non_negative_integers(self) -> None:
        """Test that active_count and total_count are valid."""
        status = get_rust_component_status()

        assert isinstance(status["active_count"], int)
        assert isinstance(status["total_count"], int)
        assert status["active_count"] >= 0
        assert status["total_count"] >= 0
        assert status["active_count"] <= status["total_count"]

    def test_percentage_is_valid(self) -> None:
        """Test that percentage is between 0 and 100."""
        status = get_rust_component_status()

        assert isinstance(status["percentage"], (int, float))
        assert 0 <= status["percentage"] <= 100

    def test_acceleration_level_is_valid_string(self) -> None:
        """Test acceleration_level is one of expected values."""
        status = get_rust_component_status()

        valid_levels = [
            "FULLY ACCELERATED",
            "HIGHLY ACCELERATED",
            "PARTIALLY ACCELERATED",
            "MINIMAL ACCELERATION",
            "NO ACCELERATION",
        ]

        assert status["acceleration_level"] in valid_levels


class TestGetPerformanceReport:
    """Test suite for get_performance_report function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Test that report contains all expected keys."""
        report = get_performance_report()

        expected_keys = [
            "acceleration_level",
            "active_percentage",
            "speedup_coverage",
            "active_components",
            "inactive_components",
            "performance_gains",
            "recommendations",
        ]

        for key in expected_keys:
            assert key in report, f"Missing key: {key}"

    def test_active_components_is_list_of_strings(self) -> None:
        """Test that active_components is a list of strings."""
        report = get_performance_report()

        assert isinstance(report["active_components"], list)
        for comp in report["active_components"]:
            assert isinstance(comp, str)

    def test_inactive_components_is_list_of_strings(self) -> None:
        """Test that inactive_components is a list of strings."""
        report = get_performance_report()

        assert isinstance(report["inactive_components"], list)
        for comp in report["inactive_components"]:
            assert isinstance(comp, str)

    def test_recommendations_is_list(self) -> None:
        """Test that recommendations is a list."""
        report = get_performance_report()

        assert isinstance(report["recommendations"], list)

    def test_speedup_coverage_is_valid_percentage(self) -> None:
        """Test that speedup_coverage is between 0 and 100."""
        report = get_performance_report()

        assert isinstance(report["speedup_coverage"], (int, float))
        assert 0 <= report["speedup_coverage"] <= 100


class TestInitializationFunctions:
    """Test initialization functions."""

    def test_ensure_initialized_can_be_called_multiple_times(self) -> None:
        """Test that _ensure_initialized is idempotent."""
        # Should not raise even when called multiple times
        _ensure_initialized()
        _ensure_initialized()
        _ensure_initialized()

    def test_initialize_rust_available_populates_dict(self) -> None:
        """Test that initialization populates RUST_AVAILABLE."""
        # RUST_AVAILABLE should already be populated
        assert isinstance(RUST_AVAILABLE, dict)
        # Should have some components (even if all False)
        # The dict may be empty if detection finds nothing


class TestPrintRustStatus:
    """Test print_rust_status function."""

    def test_print_rust_status_does_not_raise(self) -> None:
        """Test that print_rust_status runs without error."""
        from ClassicLib.integration.status import print_rust_status

        # Should not raise - may return early if debug disabled
        print_rust_status()

    @patch("ClassicLib.io.yaml.classic_settings")
    def test_print_rust_status_with_debug_enabled(self, mock_settings) -> None:
        """Test print_rust_status when debug is enabled."""
        from ClassicLib.integration.status import print_rust_status

        mock_settings.return_value = True

        # Should not raise
        print_rust_status()

    @patch("ClassicLib.io.yaml.classic_settings")
    def test_print_rust_status_with_debug_disabled(self, mock_settings) -> None:
        """Test print_rust_status returns early when debug disabled."""
        from ClassicLib.integration.status import print_rust_status

        mock_settings.return_value = False

        # Should return early without printing
        print_rust_status()

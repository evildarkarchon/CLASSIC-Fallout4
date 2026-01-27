"""Unit tests for ClassicLib.rust module initialization.

This module tests the rust module's utility functions for checking
component availability and reporting Rust acceleration status.
"""

import io
import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetRustComponentSummary:
    """Tests for get_rust_component_summary function."""

    def test_returns_dict(self) -> None:
        """Test that function returns a dictionary."""
        from ClassicLib.integration.rust import get_rust_component_summary

        result = get_rust_component_summary()

        assert isinstance(result, dict)

    def test_contains_expected_components(self) -> None:
        """Test that summary contains all expected component keys."""
        from ClassicLib.integration.rust import get_rust_component_summary

        result = get_rust_component_summary()

        expected_keys = {
            "parser",
            "formid_analyzer",
            "plugin_analyzer",
            "record_scanner",
            "file_io",
            "database",
            "report_generation",
            "mod_detector",
            "suspect_scanner",
            "fcx_handler",
            "settings_validator",
            "gpu_detector",
        }

        assert expected_keys == set(result.keys())

    def test_all_values_are_boolean(self) -> None:
        """Test that all values in the summary are booleans."""
        from ClassicLib.integration.rust import get_rust_component_summary

        result = get_rust_component_summary()

        for key, value in result.items():
            assert isinstance(value, bool), f"Component {key} has non-boolean value: {value}"

    def test_parser_component_status(self) -> None:
        """Test parser component availability status."""
        from ClassicLib.integration.rust import RustLogParser, get_rust_component_summary

        result = get_rust_component_summary()

        # Parser status should match whether RustLogParser is available
        assert result["parser"] == (RustLogParser is not None)

    def test_file_io_component_status(self) -> None:
        """Test file_io component availability status."""
        from ClassicLib.integration.rust import FileIOCore, get_rust_component_summary

        result = get_rust_component_summary()

        assert result["file_io"] == (FileIOCore is not None)

    def test_database_component_status(self) -> None:
        """Test database component availability status."""
        from ClassicLib.integration.rust import RustAsyncDatabasePool, get_rust_component_summary

        result = get_rust_component_summary()

        assert result["database"] == (RustAsyncDatabasePool is not None)


class TestPrintRustModuleStatus:
    """Tests for print_rust_module_status function."""

    def test_prints_to_stdout(self) -> None:
        """Test that function prints output."""
        from ClassicLib.integration.rust import print_rust_module_status

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            print_rust_module_status()

        output = captured.getvalue()
        assert len(output) > 0

    def test_prints_header(self) -> None:
        """Test that output includes the header."""
        from ClassicLib.integration.rust import print_rust_module_status

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            print_rust_module_status()

        output = captured.getvalue()
        assert "RUST MODULE STATUS" in output

    def test_prints_component_statuses(self) -> None:
        """Test that output includes component status information."""
        from ClassicLib.integration.rust import print_rust_module_status

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            print_rust_module_status()

        output = captured.getvalue()
        # Should include component names
        assert "parser" in output
        assert "file_io" in output

    def test_prints_total_count(self) -> None:
        """Test that output includes total component count."""
        from ClassicLib.integration.rust import print_rust_module_status

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            print_rust_module_status()

        output = captured.getvalue()
        assert "Total:" in output

    def test_prints_percentage(self) -> None:
        """Test that output includes percentage loaded."""
        from ClassicLib.integration.rust import print_rust_module_status

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            print_rust_module_status()

        output = captured.getvalue()
        assert "%" in output

    def test_prints_status_icons(self) -> None:
        """Test that output includes status icons."""
        from ClassicLib.integration.rust import print_rust_module_status

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            print_rust_module_status()

        output = captured.getvalue()
        # Should have either success or failure icons
        assert "✅" in output or "❌" in output


class TestRustModulesAvailable:
    """Tests for RUST_MODULES_AVAILABLE constant."""

    def test_is_boolean(self) -> None:
        """Test that RUST_MODULES_AVAILABLE is a boolean."""
        from ClassicLib.integration.rust import RUST_MODULES_AVAILABLE

        assert isinstance(RUST_MODULES_AVAILABLE, bool)

    def test_consistency_with_components(self) -> None:
        """Test that RUST_MODULES_AVAILABLE is consistent with component availability."""
        from ClassicLib.integration.rust import RUST_MODULES_AVAILABLE, get_rust_component_summary

        summary = get_rust_component_summary()

        # If RUST_MODULES_AVAILABLE is True, at least some components should be loaded
        if RUST_MODULES_AVAILABLE:
            assert any(summary.values()), "RUST_MODULES_AVAILABLE is True but no components are loaded"


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_accessible(self) -> None:
        """Test that all items in __all__ are accessible."""
        from ClassicLib.integration import rust

        for name in rust.__all__:
            assert hasattr(rust, name), f"Export {name} not accessible from rust module"

    def test_key_components_in_all(self) -> None:
        """Test that key components are listed in __all__."""
        from ClassicLib.integration.rust import __all__

        key_components = [
            "RustLogParser",
            "FileIOCore",
            "RUST_MODULES_AVAILABLE",
        ]

        for component in key_components:
            assert component in __all__, f"Key component {component} not in __all__"


class TestFallbackBehavior:
    """Tests for module fallback behavior when imports fail."""

    def test_module_handles_missing_rust(self) -> None:
        """Test that module gracefully handles missing Rust components."""
        # This tests the current state - components may be None if Rust isn't available
        from ClassicLib.integration import rust

        # Module should load without errors
        assert rust is not None

        # get_rust_component_summary should work regardless
        summary = rust.get_rust_component_summary()
        assert isinstance(summary, dict)

    def test_none_components_indicate_unavailable(self) -> None:
        """Test that None components correctly indicate unavailability."""
        from ClassicLib.integration.rust import RustLogParser, get_rust_component_summary

        summary = get_rust_component_summary()

        # If RustLogParser is None, parser should be False
        if RustLogParser is None:
            assert summary["parser"] is False
        else:
            assert summary["parser"] is True

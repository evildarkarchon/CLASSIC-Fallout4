"""Unit tests for ClassicLib.integration.diagnostics module.

This module tests the Rust runtime diagnostics and health monitoring
functions.
"""

import pytest
from unittest.mock import patch, MagicMock
import io

pytestmark = [pytest.mark.unit]


class TestGetRuntimeStats:
    """Tests for get_runtime_stats function."""

    def test_returns_none_when_classic_shared_not_available(self) -> None:
        """Test returns None when classic_shared is not importable."""
        from ClassicLib.integration.diagnostics import get_runtime_stats

        with patch.dict("sys.modules", {"classic_shared": None}):
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "classic_shared":
                    raise ImportError("No module named 'classic_shared'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = get_runtime_stats()

        assert result is None

    def test_returns_none_when_no_diagnostics_attribute(self) -> None:
        """Test returns None when classic_shared lacks get_runtime_stats."""
        from ClassicLib.integration.diagnostics import get_runtime_stats

        mock_module = MagicMock(spec=[])  # No attributes

        with patch.dict("sys.modules", {"classic_shared": mock_module}):
            result = get_runtime_stats()

        assert result is None

    def test_returns_stats_dict_when_available(self) -> None:
        """Test returns stats dictionary when diagnostics available."""
        from ClassicLib.integration.diagnostics import get_runtime_stats

        mock_stats = MagicMock()
        mock_stats.worker_threads = 4
        mock_stats.is_healthy = True

        mock_module = MagicMock()
        mock_module.get_runtime_stats = MagicMock(return_value=mock_stats)

        with patch.dict("sys.modules", {"classic_shared": mock_module}):
            result = get_runtime_stats()

        assert result is not None
        assert result["worker_threads"] == 4
        assert result["is_healthy"] is True
        assert result["has_diagnostics"] is True


class TestIsRuntimeHealthy:
    """Tests for is_runtime_healthy function."""

    def test_returns_true_when_classic_shared_not_available(self) -> None:
        """Test returns True (assumes healthy) when classic_shared not importable."""
        from ClassicLib.integration.diagnostics import is_runtime_healthy

        with patch.dict("sys.modules", {"classic_shared": None}):
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "classic_shared":
                    raise ImportError("No module named 'classic_shared'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = is_runtime_healthy()

        assert result is True

    def test_returns_true_when_no_health_check_attribute(self) -> None:
        """Test returns True when classic_shared lacks is_runtime_healthy."""
        from ClassicLib.integration.diagnostics import is_runtime_healthy

        mock_module = MagicMock(spec=[])  # No attributes

        with patch.dict("sys.modules", {"classic_shared": mock_module}):
            result = is_runtime_healthy()

        assert result is True

    def test_returns_module_health_status_when_available(self) -> None:
        """Test returns actual health status when available."""
        from ClassicLib.integration.diagnostics import is_runtime_healthy

        mock_module = MagicMock()
        mock_module.is_runtime_healthy = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"classic_shared": mock_module}):
            result = is_runtime_healthy()

        assert result is False


class TestPrintRuntimeStatus:
    """Tests for print_runtime_status function."""

    def test_prints_not_available_when_stats_none(self) -> None:
        """Test prints not available message when stats is None."""
        from ClassicLib.integration.diagnostics import print_runtime_status

        with patch("ClassicLib.integration.diagnostics.get_runtime_stats", return_value=None):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                print_runtime_status()

        output = captured.getvalue()
        assert "not available" in output.lower()

    def test_prints_limited_diagnostics_warning(self) -> None:
        """Test prints warning when has_diagnostics is False."""
        from ClassicLib.integration.diagnostics import print_runtime_status

        stats = {"has_diagnostics": False}
        with patch("ClassicLib.integration.diagnostics.get_runtime_stats", return_value=stats):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                print_runtime_status()

        output = captured.getvalue()
        assert "Limited" in output or "limited" in output or "⚠" in output

    def test_prints_full_stats_when_available(self) -> None:
        """Test prints full statistics when diagnostics available."""
        from ClassicLib.integration.diagnostics import print_runtime_status

        stats = {
            "has_diagnostics": True,
            "worker_threads": 4,
            "is_healthy": True,
        }
        with patch("ClassicLib.integration.diagnostics.get_runtime_stats", return_value=stats):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                print_runtime_status()

        output = captured.getvalue()
        assert "Worker" in output or "worker" in output
        assert "4" in output
        assert "Healthy" in output or "healthy" in output

    def test_prints_header(self) -> None:
        """Test prints header line."""
        from ClassicLib.integration.diagnostics import print_runtime_status

        stats = {"has_diagnostics": True, "worker_threads": 4, "is_healthy": True}
        with patch("ClassicLib.integration.diagnostics.get_runtime_stats", return_value=stats):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                print_runtime_status()

        output = captured.getvalue()
        assert "Tokio" in output or "Runtime" in output


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_contains_expected_functions(self) -> None:
        """Test __all__ contains expected function names."""
        from ClassicLib.integration.diagnostics import __all__

        expected = ["get_runtime_stats", "is_runtime_healthy", "print_runtime_status"]
        assert set(expected) == set(__all__)

    def test_all_functions_are_importable(self) -> None:
        """Test all exported functions can be imported."""
        from ClassicLib.integration import diagnostics

        for name in diagnostics.__all__:
            assert hasattr(diagnostics, name)
            assert callable(getattr(diagnostics, name))

"""Unit tests for scanlog factory functions in ClassicLib.integration.factory.

This module tests the scanlog factory functions for report generation,
mod detection, and orchestrator creation.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetReportGenerator:
    """Tests for get_report_generator function."""

    def test_raises_runtime_error_when_rust_unavailable(self) -> None:
        """Test raises RuntimeError when Rust import fails."""
        import builtins

        from ClassicLib.integration.factory import get_report_generator

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "report_rust" in str(args) or name == "ClassicLib.integration.rust.report_rust":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(RuntimeError, match="Required Rust module for ReportGenerator"):
                get_report_generator(None)

    def test_generator_has_generate_header_method(self) -> None:
        """Test returned generator has generate_header method."""
        from ClassicLib.integration.factory import get_report_generator

        generator = get_report_generator(None)

        assert hasattr(generator, "generate_header")
        assert callable(generator.generate_header)

    def test_generator_has_expected_methods(self) -> None:
        """Test returned generator has expected generation methods."""
        from ClassicLib.integration.factory import get_report_generator

        generator = get_report_generator(None)

        # All generators should have generate_header method
        assert hasattr(generator, "generate_header")


class TestGetModDetector:
    """Tests for get_mod_detector function."""

    def test_returns_dict(self) -> None:
        """Test returns dictionary of detection functions."""
        from ClassicLib.integration.factory import get_mod_detector

        result = get_mod_detector()

        assert isinstance(result, dict)
        assert "detect_mods_single" in result
        assert "detect_mods_double" in result
        assert "detect_mods_important" in result

    def test_all_functions_are_callable(self) -> None:
        """Test all returned functions are callable."""
        from ClassicLib.integration.factory import get_mod_detector

        result = get_mod_detector()

        for name, func in result.items():
            assert callable(func), f"{name} should be callable"

    def test_returns_expected_keys(self) -> None:
        """Test returns dictionary with expected keys."""
        from ClassicLib.integration.factory import get_mod_detector

        result = get_mod_detector()

        expected_keys = {"detect_mods_single", "detect_mods_double", "detect_mods_important"}
        assert set(result.keys()) == expected_keys


class TestGetOrchestrator:
    """Tests for get_orchestrator function."""

    @patch("ClassicLib.integration.rust.orchestrator_api.ClassicOrchestrator")
    def test_returns_orchestrator_instance(self, mock_orchestrator_cls: MagicMock) -> None:
        """Test returns orchestrator instance."""
        from ClassicLib.integration.factory import get_orchestrator

        mock_instance = MagicMock()
        mock_orchestrator_cls.return_value = mock_instance

        result = get_orchestrator(
            yamldata=MagicMock(),
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=True,
        )

        assert result is mock_instance
        mock_orchestrator_cls.assert_called_once()

    def test_returns_orchestrator_on_import_error(self) -> None:
        """Test raises ImportError when Rust orchestrator import fails."""
        import builtins

        from ClassicLib.integration.factory import get_orchestrator

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "orchestrator_api" in str(args) or name == "ClassicLib.integration.rust.orchestrator_api":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError):
                get_orchestrator(
                    yamldata=MagicMock(),
                    fcx_mode=False,
                    show_formid_values=True,
                    formid_db_exists=True,
                )

    @patch("ClassicLib.integration.rust.orchestrator_api.ClassicOrchestrator")
    def test_accepts_all_parameters(self, mock_orchestrator_cls: MagicMock) -> None:
        """Test function accepts all expected parameters."""
        from ClassicLib.integration.factory import get_orchestrator

        mock_instance = MagicMock()
        mock_orchestrator_cls.return_value = mock_instance

        # Should not raise any errors
        result = get_orchestrator(
            yamldata=MagicMock(),
            fcx_mode=True,
            show_formid_values=False,
            formid_db_exists=False,
            remove_list=("item1", "item2"),
        )

        assert result is mock_instance

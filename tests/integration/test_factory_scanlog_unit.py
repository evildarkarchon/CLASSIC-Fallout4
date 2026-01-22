"""Unit tests for ClassicLib.integration.factory.scanlog module.

This module tests the scanlog factory functions for report generation,
mod detection, and orchestrator creation.
"""

import pytest
from unittest.mock import patch, MagicMock

pytestmark = [pytest.mark.unit]


class TestGetReportGenerator:
    """Tests for get_report_generator function."""

    def test_returns_python_generator_when_rust_disabled(self) -> None:
        """Test returns Python ReportGenerator when Rust is disabled."""
        from ClassicLib.integration.factory.scanlog import get_report_generator
        from ClassicLib.python.report_py import ReportGenerator

        with patch("ClassicLib.integration.factory.scanlog.is_rust_disabled", return_value=True):
            result = get_report_generator(None)

        assert isinstance(result, ReportGenerator)

    def test_returns_python_generator_when_component_not_available(self) -> None:
        """Test returns Python ReportGenerator when component not available."""
        from ClassicLib.integration.factory.scanlog import get_report_generator
        from ClassicLib.python.report_py import ReportGenerator

        with (
            patch("ClassicLib.integration.factory.scanlog.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.scanlog.get_components", return_value={"report_generation": False}),
        ):
            result = get_report_generator(None)

        assert isinstance(result, ReportGenerator)

    def test_returns_python_generator_on_import_error(self) -> None:
        """Test returns Python ReportGenerator when Rust import fails."""
        from ClassicLib.integration.factory.scanlog import get_report_generator
        from ClassicLib.python.report_py import ReportGenerator

        with (
            patch("ClassicLib.integration.factory.scanlog.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.scanlog.get_components", return_value={"report_generation": True}),
        ):
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "report_rust" in str(args) or name == "ClassicLib.rust.report_rust":
                    raise ImportError("No module")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = get_report_generator(None)

        assert isinstance(result, ReportGenerator)

    def test_generator_has_generate_header_method(self) -> None:
        """Test returned generator has generate_header method."""
        from ClassicLib.integration.factory.scanlog import get_report_generator

        generator = get_report_generator(None)

        assert hasattr(generator, "generate_header")
        assert callable(generator.generate_header)

    def test_generator_has_expected_methods(self) -> None:
        """Test returned generator has expected generation methods."""
        from ClassicLib.integration.factory.scanlog import get_report_generator

        generator = get_report_generator(None)

        # All generators should have generate_header method
        assert hasattr(generator, "generate_header")
        # Generators may have different method sets


class TestGetModDetector:
    """Tests for get_mod_detector function."""

    def test_returns_dict_when_rust_disabled(self) -> None:
        """Test returns dictionary when Rust is disabled."""
        from ClassicLib.integration.factory.scanlog import get_mod_detector

        with patch("ClassicLib.integration.factory.scanlog.is_rust_disabled", return_value=True):
            result = get_mod_detector()

        assert isinstance(result, dict)

    def test_returns_python_functions_when_component_not_available(self) -> None:
        """Test returns Python functions when component not available."""
        from ClassicLib.integration.factory.scanlog import get_mod_detector

        with (
            patch("ClassicLib.integration.factory.scanlog.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.scanlog.get_components", return_value={"mod_detector": False}),
        ):
            result = get_mod_detector()

        assert isinstance(result, dict)
        assert "detect_mods_single" in result
        assert "detect_mods_double" in result
        assert "detect_mods_important" in result

    def test_all_functions_are_callable(self) -> None:
        """Test all returned functions are callable."""
        from ClassicLib.integration.factory.scanlog import get_mod_detector

        result = get_mod_detector()

        for name, func in result.items():
            assert callable(func), f"{name} should be callable"

    def test_returns_expected_keys(self) -> None:
        """Test returns dictionary with expected keys."""
        from ClassicLib.integration.factory.scanlog import get_mod_detector

        result = get_mod_detector()

        expected_keys = {"detect_mods_single", "detect_mods_double", "detect_mods_important"}
        assert set(result.keys()) == expected_keys


class TestGetOrchestrator:
    """Tests for get_orchestrator function."""

    def test_returns_orchestrator_when_rust_disabled(self) -> None:
        """Test returns orchestrator when Rust is disabled."""
        from ClassicLib.integration.factory.scanlog import get_orchestrator

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        mock_yamldata.xse_acronym = "F4SE"
        mock_yamldata.game_root_name = "Fallout4"

        with patch("ClassicLib.integration.factory.scanlog.is_rust_disabled", return_value=True):
            result = get_orchestrator(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            )

        assert result is not None

    def test_returns_orchestrator_when_component_not_available(self) -> None:
        """Test returns orchestrator when component not available."""
        from ClassicLib.integration.factory.scanlog import get_orchestrator

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        mock_yamldata.xse_acronym = "F4SE"
        mock_yamldata.game_root_name = "Fallout4"

        with (
            patch("ClassicLib.integration.factory.scanlog.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.scanlog.get_components", return_value={"orchestrator": False}),
        ):
            result = get_orchestrator(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            )

        assert result is not None

    def test_accepts_all_parameters(self) -> None:
        """Test function accepts all expected parameters."""
        from ClassicLib.integration.factory.scanlog import get_orchestrator

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        mock_yamldata.xse_acronym = "F4SE"
        mock_yamldata.game_root_name = "Fallout4"

        # Should not raise any errors
        result = get_orchestrator(
            yamldata=mock_yamldata,
            fcx_mode=True,
            show_formid_values=False,
            formid_db_exists=False,
            remove_list=("item1", "item2"),
        )

        assert result is not None

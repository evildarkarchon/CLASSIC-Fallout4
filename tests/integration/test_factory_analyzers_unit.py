"""Unit tests for ClassicLib.integration.factory.analyzers module.

This module tests the factory functions for analyzer components.
"""

import pytest
from unittest.mock import patch, MagicMock

pytestmark = [pytest.mark.unit]


class TestGetFormidAnalyzer:
    """Tests for get_formid_analyzer function."""

    def test_returns_analyzer_instance(self) -> None:
        """Test returns an analyzer instance."""
        from ClassicLib.integration.factory.analyzers import get_formid_analyzer

        mock_yamldata = MagicMock()

        result = get_formid_analyzer(mock_yamldata, show_values=True, db_exists=True)

        assert result is not None

    def test_returns_python_analyzer_when_rust_disabled(self) -> None:
        """Test returns Python analyzer when Rust is disabled."""
        from ClassicLib.integration.factory.analyzers import get_formid_analyzer
        from ClassicLib.python.formid_py import FormIDAnalyzer

        mock_yamldata = MagicMock()

        with patch("ClassicLib.integration.factory.analyzers.is_rust_disabled", return_value=True):
            result = get_formid_analyzer(mock_yamldata, show_values=True, db_exists=True)

        assert isinstance(result, FormIDAnalyzer)

    def test_returns_python_analyzer_when_component_not_available(self) -> None:
        """Test returns Python analyzer when component not available."""
        from ClassicLib.integration.factory.analyzers import get_formid_analyzer
        from ClassicLib.python.formid_py import FormIDAnalyzer

        mock_yamldata = MagicMock()

        with (
            patch("ClassicLib.integration.factory.analyzers.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.analyzers.get_components", return_value={"formid_analyzer": False}),
        ):
            result = get_formid_analyzer(mock_yamldata, show_values=True, db_exists=True)

        assert isinstance(result, FormIDAnalyzer)


class TestGetPluginAnalyzer:
    """Tests for get_plugin_analyzer function."""

    def test_returns_analyzer_instance(self) -> None:
        """Test returns an analyzer instance."""
        from ClassicLib.integration.factory.analyzers import get_plugin_analyzer

        mock_yamldata = MagicMock()

        result = get_plugin_analyzer(mock_yamldata)

        assert result is not None

    def test_returns_python_analyzer_when_rust_disabled(self) -> None:
        """Test returns Python analyzer when Rust is disabled."""
        from ClassicLib.integration.factory.analyzers import get_plugin_analyzer
        from ClassicLib.python.plugin_py import PluginAnalyzer

        mock_yamldata = MagicMock()

        with patch("ClassicLib.integration.factory.analyzers.is_rust_disabled", return_value=True):
            result = get_plugin_analyzer(mock_yamldata)

        assert isinstance(result, PluginAnalyzer)


class TestGetRecordScanner:
    """Tests for get_record_scanner function."""

    def test_returns_scanner_instance(self) -> None:
        """Test returns a scanner instance."""
        from ClassicLib.integration.factory.analyzers import get_record_scanner

        mock_yamldata = MagicMock()

        # Force Python implementation to avoid Rust type errors with MagicMock
        with patch("ClassicLib.integration.factory.analyzers.is_rust_disabled", return_value=True):
            result = get_record_scanner(mock_yamldata)

        assert result is not None

    def test_returns_python_scanner_when_rust_disabled(self) -> None:
        """Test returns Python scanner when Rust is disabled."""
        from ClassicLib.integration.factory.analyzers import get_record_scanner
        from ClassicLib.python.record_py import RecordScanner

        mock_yamldata = MagicMock()

        with patch("ClassicLib.integration.factory.analyzers.is_rust_disabled", return_value=True):
            result = get_record_scanner(mock_yamldata)

        assert isinstance(result, RecordScanner)


class TestGetSuspectScanner:
    """Tests for get_suspect_scanner function."""

    def test_returns_scanner_instance(self) -> None:
        """Test returns a scanner instance."""
        from ClassicLib.integration.factory.analyzers import get_suspect_scanner

        mock_yamldata = MagicMock()
        # Provide proper typed attributes that Rust expects
        mock_yamldata.suspects_error_list = {}
        mock_yamldata.suspects_stack_list = {}

        result = get_suspect_scanner(mock_yamldata)

        assert result is not None


class TestGetSettingsValidator:
    """Tests for get_settings_validator function."""

    def test_returns_validator_instance(self) -> None:
        """Test returns a validator instance."""
        from ClassicLib.integration.factory.analyzers import get_settings_validator

        mock_yamldata = MagicMock()
        # Provide proper typed attributes that Rust expects
        mock_yamldata.crashgen_name = "Buffout 4"
        mock_yamldata.crashgen_ignore = []

        result = get_settings_validator(mock_yamldata)

        assert result is not None


class TestGetGpuDetector:
    """Tests for get_gpu_detector function."""

    def test_returns_gpu_rust_module(self) -> None:
        """Test returns gpu_rust module."""
        from ClassicLib.integration.factory.analyzers import get_gpu_detector

        result = get_gpu_detector()

        assert result is not None
        assert hasattr(result, "RUST_AVAILABLE")

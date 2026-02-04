"""Unit tests for factory analyzer functions in ClassicLib.integration.factory.

This module tests the factory functions for analyzer components.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetFormidAnalyzer:
    """Tests for get_formid_analyzer function."""

    def test_returns_analyzer_instance(self) -> None:
        """Test returns an analyzer instance."""
        from ClassicLib.integration.factory import get_formid_analyzer

        # Create mock with proper typed attributes (Rust requires strings, not MagicMock)
        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        mock_yamldata.problematic_plugins = {}
        mock_yamldata.mods_single = {}
        mock_yamldata.mods_double = {}

        result = get_formid_analyzer(mock_yamldata, show_values=True, db_exists=True)

        assert result is not None

    def test_raises_runtime_error_when_rust_unavailable(self) -> None:
        """Test raises RuntimeError when Rust import fails."""
        import builtins

        from ClassicLib.integration.factory import get_formid_analyzer

        # Create mock with proper typed attributes (Rust requires strings, not MagicMock)
        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        mock_yamldata.problematic_plugins = {}
        mock_yamldata.mods_single = {}
        mock_yamldata.mods_double = {}

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "formid_rust" in str(args) or name == "ClassicLib.integration.rust.formid_rust":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(RuntimeError, match="Required Rust module for FormIDAnalyzer"):
                get_formid_analyzer(mock_yamldata, show_values=True, db_exists=True)


class TestGetPluginAnalyzer:
    """Tests for get_plugin_analyzer function."""

    def test_returns_analyzer_instance(self) -> None:
        """Test returns an analyzer instance."""
        from ClassicLib.integration.factory import get_plugin_analyzer

        mock_yamldata = MagicMock()

        result = get_plugin_analyzer(mock_yamldata)

        assert result is not None

    def test_raises_runtime_error_when_rust_unavailable(self) -> None:
        """Test raises RuntimeError when Rust import fails."""
        import builtins

        from ClassicLib.integration.factory import get_plugin_analyzer

        mock_yamldata = MagicMock()
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "plugin_rust" in str(args) or name == "ClassicLib.integration.rust.plugin_rust":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(RuntimeError, match="Required Rust module for plugin analyzer"):
                get_plugin_analyzer(mock_yamldata)


class TestGetRecordScanner:
    """Tests for get_record_scanner function."""

    def test_returns_scanner_instance(self) -> None:
        """Test returns a scanner instance."""
        from ClassicLib.integration.factory import get_record_scanner

        mock_yamldata = MagicMock()
        mock_yamldata.classic_records_list = []
        mock_yamldata.game_ignore_records = []
        mock_yamldata.crashgen_name = "Buffout4"

        result = get_record_scanner(mock_yamldata)

        assert result is not None

    def test_raises_runtime_error_when_rust_unavailable(self) -> None:
        """Test raises RuntimeError when Rust import fails."""
        import builtins

        from ClassicLib.integration.factory import get_record_scanner

        mock_yamldata = MagicMock()
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "record_rust" in str(args) or name == "ClassicLib.integration.rust.record_rust":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(RuntimeError, match="Required Rust module for RecordScanner"):
                get_record_scanner(mock_yamldata)


class TestGetSuspectScanner:
    """Tests for get_suspect_scanner function."""

    def test_returns_scanner_instance(self) -> None:
        """Test returns a scanner instance."""
        from ClassicLib.integration.factory import get_suspect_scanner

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
        from ClassicLib.integration.factory import get_settings_validator

        mock_yamldata = MagicMock()
        # Provide proper typed attributes that Rust expects
        mock_yamldata.crashgen_name = "Buffout 4"
        mock_yamldata.crashgen_ignore = []

        result = get_settings_validator(mock_yamldata)

        assert result is not None


class TestGetGpuDetector:
    """Tests for get_gpu_detector function."""

    def test_returns_gpu_detector_namespace(self) -> None:
        """Test returns namespace with get_gpu_info function."""
        from ClassicLib.integration.factory import get_gpu_detector

        result = get_gpu_detector()

        assert result is not None
        # Factory returns SimpleNamespace with get_gpu_info function
        assert hasattr(result, "get_gpu_info")
        assert callable(result.get_gpu_info)

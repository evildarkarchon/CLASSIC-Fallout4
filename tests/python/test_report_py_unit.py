"""Unit tests for ClassicLib.python.report_py module.

This module tests the PythonReportGenerator class for generating
crash analysis reports as a fallback when Rust is not available.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestPythonReportGeneratorInitialization:
    """Tests for PythonReportGenerator initialization."""

    def test_initializes_with_yamldata(self) -> None:
        """Test initialization stores yamldata."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.classic_version = "CLASSIC v8.0.0"

        generator = PythonReportGenerator(mock_yamldata)

        assert generator.yamldata == mock_yamldata


class TestGenerateHeader:
    """Tests for generate_header method."""

    def test_generates_header_with_filename(self) -> None:
        """Test header includes crash log filename."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.classic_version = "CLASSIC v8.0.0"
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_header("crash-2024-01-15.log")

        content = "".join(result.to_list())
        assert "crash-2024-01-15.log" in content

    def test_generates_header_with_version(self) -> None:
        """Test header includes classic version."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.classic_version = "CLASSIC v8.0.0"
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_header("crash.log")

        content = "".join(result.to_list())
        assert "CLASSIC v8.0.0" in content

    def test_header_uses_default_when_no_yamldata(self) -> None:
        """Test header uses default version when yamldata is None."""
        from ClassicLib.python.report_py import PythonReportGenerator

        generator = PythonReportGenerator(None)

        result = generator.generate_header("crash.log")

        content = "".join(result.to_list())
        assert "CLASSIC" in content

    def test_header_includes_viewing_instructions(self) -> None:
        """Test header includes viewing instructions."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_header("crash.log")

        content = "".join(result.to_list())
        assert "NOTEPAD++" in content or "VIEWING EXPERIENCE" in content

    def test_header_returns_report_fragment(self) -> None:
        """Test that generate_header returns a ReportFragment."""
        from ClassicLib.python.report_py import PythonReportGenerator
        from ClassicLib.ScanLog.fragments import ReportFragment

        mock_yamldata = MagicMock()
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_header("crash.log")

        assert isinstance(result, ReportFragment)


class TestGenerateErrorSection:
    """Tests for generate_error_section method."""

    def test_includes_main_error(self) -> None:
        """Test error section includes main error message."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        generator = PythonReportGenerator(mock_yamldata)

        with patch("ClassicLib.GlobalRegistry.get_vr", return_value=""):
            result = generator.generate_error_section(
                "EXCEPTION_ACCESS_VIOLATION",
                "1.26.2",
                "1.26.2",
                "1.26.2",
                "1.26.2",
            )

        content = "".join(result.to_list())
        assert "EXCEPTION_ACCESS_VIOLATION" in content

    def test_includes_crashgen_version(self) -> None:
        """Test error section includes crashgen version."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        generator = PythonReportGenerator(mock_yamldata)

        with patch("ClassicLib.GlobalRegistry.get_vr", return_value=""):
            result = generator.generate_error_section(
                "ERROR",
                "1.26.2",
                "1.26.2",
                "1.26.2",
                "1.26.2",
            )

        content = "".join(result.to_list())
        assert "1.26.2" in content

    def test_shows_outdated_warning_when_version_old(self) -> None:
        """Test error section shows warning when version is outdated."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        generator = PythonReportGenerator(mock_yamldata)

        with patch("ClassicLib.GlobalRegistry.get_vr", return_value=""):
            result = generator.generate_error_section(
                "ERROR",
                "1.20.0",
                "1.20.0",  # current
                "1.26.2",  # latest
                "1.26.2",  # latest vr
            )

        content = "".join(result.to_list())
        assert "OUTDATED" in content or "❌" in content

    def test_shows_latest_message_when_current(self) -> None:
        """Test error section shows 'latest version' when current."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout4"
        generator = PythonReportGenerator(mock_yamldata)

        with patch("ClassicLib.GlobalRegistry.get_vr", return_value=""):
            result = generator.generate_error_section(
                "ERROR",
                "1.26.2",
                "1.26.2",  # current
                "1.26.2",  # latest
                "1.26.2",  # latest vr
            )

        content = "".join(result.to_list())
        assert "latest version" in content or "✅" in content


class TestGenerateStaticHeaders:
    """Tests for static header generation methods."""

    def test_generate_suspect_section_header(self) -> None:
        """Test suspect section header generation."""
        from ClassicLib.python.report_py import PythonReportGenerator
        from ClassicLib.ScanLog.fragments import ReportFragment

        result = PythonReportGenerator.generate_suspect_section_header()

        assert isinstance(result, ReportFragment)
        content = "".join(result.to_list())
        assert "Crash Messages" in content or "Errors" in content or "Suspects" in content

    def test_generate_settings_section_header(self) -> None:
        """Test settings section header generation."""
        from ClassicLib.python.report_py import PythonReportGenerator
        from ClassicLib.ScanLog.fragments import ReportFragment

        result = PythonReportGenerator.generate_settings_section_header()

        assert isinstance(result, ReportFragment)
        content = "".join(result.to_list())
        assert "Settings" in content

    def test_generate_plugin_suspect_header(self) -> None:
        """Test plugin suspect header generation."""
        from ClassicLib.python.report_py import PythonReportGenerator
        from ClassicLib.ScanLog.fragments import ReportFragment

        result = PythonReportGenerator.generate_plugin_suspect_header()

        assert isinstance(result, ReportFragment)
        content = "".join(result.to_list())
        assert "Plugin" in content

    def test_generate_formid_section_header(self) -> None:
        """Test FormID section header generation."""
        from ClassicLib.python.report_py import PythonReportGenerator
        from ClassicLib.ScanLog.fragments import ReportFragment

        result = PythonReportGenerator.generate_formid_section_header()

        assert isinstance(result, ReportFragment)
        content = "".join(result.to_list())
        assert "FormID" in content

    def test_generate_record_section_header(self) -> None:
        """Test record section header generation."""
        from ClassicLib.python.report_py import PythonReportGenerator
        from ClassicLib.ScanLog.fragments import ReportFragment

        result = PythonReportGenerator.generate_record_section_header()

        assert isinstance(result, ReportFragment)
        content = "".join(result.to_list())
        assert "Record" in content


class TestGenerateSuspectFoundFooter:
    """Tests for generate_suspect_found_footer method."""

    def test_footer_when_suspect_found(self) -> None:
        """Test footer message when suspects were found."""
        from ClassicLib.python.report_py import PythonReportGenerator

        result = PythonReportGenerator.generate_suspect_found_footer(True)

        content = "".join(result.to_list())
        assert "SUSPECTS DETECTED" in content or "ONE OR MORE" in content

    def test_footer_when_no_suspect(self) -> None:
        """Test footer message when no suspects found."""
        from ClassicLib.python.report_py import PythonReportGenerator

        result = PythonReportGenerator.generate_suspect_found_footer(False)

        content = "".join(result.to_list())
        assert "NO SUSPECTS" in content


class TestGenerateModCheckHeader:
    """Tests for generate_mod_check_header method."""

    def test_includes_check_type(self) -> None:
        """Test mod check header includes the check type."""
        from ClassicLib.python.report_py import PythonReportGenerator

        result = PythonReportGenerator.generate_mod_check_header("Cause Crashes")

        content = "".join(result.to_list())
        assert "Cause Crashes" in content

    def test_different_check_types(self) -> None:
        """Test various check types."""
        from ClassicLib.python.report_py import PythonReportGenerator

        check_types = ["Have Issues", "Need Updates", "Are Incompatible"]

        for check_type in check_types:
            result = PythonReportGenerator.generate_mod_check_header(check_type)
            content = "".join(result.to_list())
            assert check_type in content


class TestGenerateFooter:
    """Tests for generate_footer method."""

    def test_footer_includes_version(self) -> None:
        """Test footer includes version information."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        mock_yamldata.classic_version = "CLASSIC v8.0.0"
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_footer()

        content = "".join(result.to_list())
        assert "CLASSIC v8.0.0" in content

    def test_footer_includes_credits(self) -> None:
        """Test footer includes author credits."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_footer()

        content = "".join(result.to_list())
        assert "Poet" in content

    def test_footer_includes_contributors(self) -> None:
        """Test footer includes contributors list."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_footer()

        content = "".join(result.to_list())
        assert "CONTRIBUTORS" in content

    def test_footer_includes_nexusmods_link(self) -> None:
        """Test footer includes NexusMods link."""
        from ClassicLib.python.report_py import PythonReportGenerator

        mock_yamldata = MagicMock()
        generator = PythonReportGenerator(mock_yamldata)

        result = generator.generate_footer()

        content = "".join(result.to_list())
        assert "nexusmods.com" in content

    def test_footer_uses_default_when_no_yamldata(self) -> None:
        """Test footer uses default when yamldata is None."""
        from ClassicLib.python.report_py import PythonReportGenerator

        generator = PythonReportGenerator(None)

        result = generator.generate_footer()

        content = "".join(result.to_list())
        assert "CLASSIC" in content


class TestReportGeneratorAlias:
    """Tests for ReportGenerator compatibility alias."""

    def test_alias_exists(self) -> None:
        """Test ReportGenerator alias exists."""
        from ClassicLib.python.report_py import ReportGenerator

        assert ReportGenerator is not None

    def test_alias_is_same_class(self) -> None:
        """Test ReportGenerator is same as PythonReportGenerator."""
        from ClassicLib.python.report_py import PythonReportGenerator, ReportGenerator

        assert ReportGenerator is PythonReportGenerator

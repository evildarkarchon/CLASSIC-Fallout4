"""Unit tests for ClassicLib.rust.report module.

This module tests the Rust-accelerated report wrappers:
- RustAcceleratedReportFragment
- RustAcceleratedReportComposer
- RustAcceleratedReportGenerator
- ParallelReportProcessor
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
    from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment
    from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator
    from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_lines() -> list[str]:
    """Create sample report lines.

    Returns:
        list[str]: Sample report content lines.
    """
    return [
        "# Crash Report\n",
        "## Summary\n",
        "Error detected in module XYZ\n",
    ]


@pytest.fixture
def mock_yamldata_for_report() -> MagicMock:
    """Create a mock ClassicScanLogsInfo for report generation.

    Returns:
        MagicMock: Mock with report-related attributes.
    """
    mock = MagicMock()
    mock.crashgen_name = "Buffout 4"
    mock.classic_version = "CLASSIC v1.0.0"
    return mock


# ============================================================================
# RustAcceleratedReportFragment Tests
# ============================================================================


class TestRustAcceleratedReportFragment:
    """Tests for RustAcceleratedReportFragment class."""

    @pytest.mark.unit
    def test_init_with_lines(self, sample_lines: list[str]) -> None:
        """Test initialization with lines."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(sample_lines)

        assert fragment.to_list() == sample_lines

    @pytest.mark.unit
    def test_init_with_tuple(self) -> None:
        """Test initialization with tuple of lines."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        lines = ("Line 1\n", "Line 2\n")
        fragment = RustAcceleratedReportFragment(lines)

        result = fragment.to_list()
        assert "Line 1\n" in result
        assert "Line 2\n" in result

    @pytest.mark.unit
    def test_init_with_none(self) -> None:
        """Test initialization with None creates empty fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(None)

        assert len(fragment) == 0

    @pytest.mark.unit
    def test_empty_class_method(self) -> None:
        """Test empty() class method creates empty fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment.empty()

        assert len(fragment) == 0
        assert fragment.has_content is False

    @pytest.mark.unit
    def test_from_lines_class_method(self, sample_lines: list[str]) -> None:
        """Test from_lines() class method."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment.from_lines(sample_lines)

        assert fragment.to_list() == sample_lines

    @pytest.mark.unit
    def test_to_list_returns_list(self, sample_lines: list[str]) -> None:
        """Test to_list() returns list of strings."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(sample_lines)

        result = fragment.to_list()

        assert isinstance(result, list)

    @pytest.mark.unit
    def test_content_property(self, sample_lines: list[str]) -> None:
        """Test content property returns tuple."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(sample_lines)

        content = fragment.content

        assert isinstance(content, tuple)

    @pytest.mark.unit
    def test_has_content_property_true(self, sample_lines: list[str]) -> None:
        """Test has_content is True for non-empty fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(sample_lines)

        assert fragment.has_content is True

    @pytest.mark.unit
    def test_has_content_property_false(self) -> None:
        """Test has_content is False for empty fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment.empty()

        assert fragment.has_content is False

    @pytest.mark.unit
    def test_len_returns_line_count(self, sample_lines: list[str]) -> None:
        """Test __len__ returns number of lines."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(sample_lines)

        assert len(fragment) == len(sample_lines)

    @pytest.mark.unit
    def test_bool_true_for_non_empty(self, sample_lines: list[str]) -> None:
        """Test bool is True for non-empty fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(sample_lines)

        assert bool(fragment) is True

    @pytest.mark.unit
    def test_bool_false_for_empty(self) -> None:
        """Test bool is False for empty fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment.empty()

        assert bool(fragment) is False

    @pytest.mark.unit
    def test_add_combines_fragments(self) -> None:
        """Test __add__ combines two fragments."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        frag1 = RustAcceleratedReportFragment(["Line 1\n"])
        frag2 = RustAcceleratedReportFragment(["Line 2\n"])

        combined = frag1 + frag2

        result = combined.to_list()
        assert "Line 1\n" in result
        assert "Line 2\n" in result

    @pytest.mark.unit
    def test_with_header_prepends_header(self, sample_lines: list[str]) -> None:
        """Test with_header prepends header lines."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        fragment = RustAcceleratedReportFragment(sample_lines)
        header = ["=== HEADER ===\n"]

        with_header = fragment.with_header(header)

        result = with_header.to_list()
        assert result[0] == "=== HEADER ===\n"

    @pytest.mark.unit
    def test_wrap_fragment_class_method(self, sample_lines: list[str]) -> None:
        """Test wrap_fragment wraps existing fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment
        from ClassicLib.scanning.logs.reporting.report_fragment import ReportFragment as PyReportFragment

        py_fragment = PyReportFragment.from_lines(sample_lines)

        rust_fragment = RustAcceleratedReportFragment.from_lines(py_fragment.to_list())
        wrapped = RustAcceleratedReportFragment.wrap_fragment(rust_fragment._fragment, use_rust=True)

        assert wrapped.to_list() == sample_lines


# ============================================================================
# RustAcceleratedReportComposer Tests
# ============================================================================


class TestRustAcceleratedReportComposer:
    """Tests for RustAcceleratedReportComposer class."""

    @pytest.mark.unit
    def test_init_creates_composer(self) -> None:
        """Test initialization creates composer."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer

        composer = RustAcceleratedReportComposer()

        assert composer is not None

    @pytest.mark.unit
    def test_add_returns_self_for_chaining(self, sample_lines: list[str]) -> None:
        """Test add() returns self for method chaining."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        composer = RustAcceleratedReportComposer()
        fragment = RustAcceleratedReportFragment(sample_lines)

        result = composer.add(fragment)

        assert result is composer

    @pytest.mark.unit
    def test_add_multiple_fragments(self) -> None:
        """Test adding multiple fragments."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        composer = RustAcceleratedReportComposer()
        frag1 = RustAcceleratedReportFragment(["Line 1\n"])
        frag2 = RustAcceleratedReportFragment(["Line 2\n"])

        composer.add(frag1).add(frag2)

        result = composer.to_list()
        assert "Line 1\n" in result
        assert "Line 2\n" in result

    @pytest.mark.unit
    def test_compose_returns_fragment(self, sample_lines: list[str]) -> None:
        """Test compose() returns RustAcceleratedReportFragment."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        composer = RustAcceleratedReportComposer()
        fragment = RustAcceleratedReportFragment(sample_lines)
        composer.add(fragment)

        result = composer.compose()

        assert hasattr(result, "to_list")

    @pytest.mark.unit
    def test_build_returns_fragment(self, sample_lines: list[str]) -> None:
        """Test build() is alias for compose()."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        composer = RustAcceleratedReportComposer()
        fragment = RustAcceleratedReportFragment(sample_lines)
        composer.add(fragment)

        result = composer.build()

        assert hasattr(result, "to_list")

    @pytest.mark.unit
    def test_to_list_returns_combined_lines(self) -> None:
        """Test to_list() returns all lines."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        composer = RustAcceleratedReportComposer()
        composer.add(RustAcceleratedReportFragment(["A\n"]))
        composer.add(RustAcceleratedReportFragment(["B\n"]))

        result = composer.to_list()

        assert isinstance(result, list)
        assert "A\n" in result
        assert "B\n" in result

    @pytest.mark.unit
    def test_build_string_returns_str(self, sample_lines: list[str]) -> None:
        """Test build_string() returns string."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        composer = RustAcceleratedReportComposer()
        composer.add(RustAcceleratedReportFragment(sample_lines))

        result = composer.build_string()

        assert isinstance(result, str)

    @pytest.mark.unit
    def test_pool_stats_returns_tuple_or_none(self) -> None:
        """Test pool_stats returns stats or None."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer

        composer = RustAcceleratedReportComposer()

        stats = composer.pool_stats

        # May return tuple of 4 ints or None depending on Rust availability
        assert stats is None or (isinstance(stats, tuple) and len(stats) == 4)


# ============================================================================
# RustAcceleratedReportGenerator Tests
# ============================================================================


class TestRustAcceleratedReportGenerator:
    """Tests for RustAcceleratedReportGenerator class."""

    @pytest.mark.unit
    def test_init_without_yamldata(self) -> None:
        """Test initialization without yamldata."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()

        assert generator.yamldata is None

    @pytest.mark.unit
    def test_init_with_yamldata(self, mock_yamldata_for_report: MagicMock) -> None:
        """Test initialization with yamldata."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator(mock_yamldata_for_report)

        assert generator.yamldata is mock_yamldata_for_report

    @pytest.mark.unit
    def test_generate_header(self) -> None:
        """Test generate_header returns fragment."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()

        result = generator.generate_header("crash-2024.log")

        assert hasattr(result, "to_list")

    @pytest.mark.unit
    def test_generate_suspect_section(self) -> None:
        """Test generate_suspect_section returns fragment."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()

        result = generator.generate_suspect_section(["Suspect1", "Suspect2"])

        assert hasattr(result, "to_list")

    @pytest.mark.unit
    def test_generate_suspect_section_header(self) -> None:
        """Test generate_suspect_section_header method."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_suspect_section_header()

        lines = result.to_list()
        content = "".join(lines)

        assert "Known Crash" in content or "Suspects" in content

    @pytest.mark.unit
    def test_generate_suspect_found_footer_true(self) -> None:
        """Test generate_suspect_found_footer with suspects found."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_suspect_found_footer(True)

        lines = result.to_list()
        content = "".join(lines)

        assert "SUSPECTS DETECTED" in content

    @pytest.mark.unit
    def test_generate_suspect_found_footer_false(self) -> None:
        """Test generate_suspect_found_footer with no suspects."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_suspect_found_footer(False)

        lines = result.to_list()
        content = "".join(lines)

        assert "NO SUSPECTS" in content

    @pytest.mark.unit
    def test_generate_settings_section_header(self) -> None:
        """Test generate_settings_section_header method."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_settings_section_header()

        lines = result.to_list()
        content = "".join(lines)

        assert "Settings" in content

    @pytest.mark.unit
    def test_generate_mod_check_header(self) -> None:
        """Test generate_mod_check_header method."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_mod_check_header("Cause Issues")

        lines = result.to_list()
        content = "".join(lines)

        assert "Cause Issues" in content

    @pytest.mark.unit
    def test_generate_plugin_suspect_header(self) -> None:
        """Test generate_plugin_suspect_header method."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_plugin_suspect_header()

        lines = result.to_list()
        content = "".join(lines)

        assert "Plugin" in content

    @pytest.mark.unit
    def test_generate_formid_section_header(self) -> None:
        """Test generate_formid_section_header method."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_formid_section_header()

        lines = result.to_list()
        content = "".join(lines)

        assert "FormID" in content

    @pytest.mark.unit
    def test_generate_record_section_header(self) -> None:
        """Test generate_record_section_header method."""
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        result = generator.generate_record_section_header()

        lines = result.to_list()
        content = "".join(lines)

        assert "Named Records" in content


# ============================================================================
# ParallelReportProcessor Tests
# ============================================================================


class TestParallelReportProcessor:
    """Tests for ParallelReportProcessor class."""

    @pytest.mark.unit
    def test_init_creates_processor(self) -> None:
        """Test initialization creates processor."""
        from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

        processor = ParallelReportProcessor()

        assert processor is not None

    @pytest.mark.unit
    def test_process_reports_returns_list(self) -> None:
        """Test process_reports returns list of processed reports."""
        from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

        processor = ParallelReportProcessor()
        reports = [["Line 1\n", "Line 2\n"], ["Report 2\n"]]

        result = processor.process_reports(reports)

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.unit
    def test_process_reports_empty_list(self) -> None:
        """Test process_reports with empty list."""
        from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

        processor = ParallelReportProcessor()

        result = processor.process_reports([])

        assert result == []

    @pytest.mark.unit
    def test_combine_fragments_parallel(self, sample_lines: list[str]) -> None:
        """Test combine_fragments_parallel combines fragments."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment
        from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

        processor = ParallelReportProcessor()
        frag1 = RustAcceleratedReportFragment(["A\n"])
        frag2 = RustAcceleratedReportFragment(["B\n"])

        result = processor.combine_fragments_parallel([frag1, frag2])

        assert hasattr(result, "to_list")
        lines = result.to_list()
        assert "A\n" in lines
        assert "B\n" in lines

    @pytest.mark.unit
    def test_combine_fragments_parallel_empty(self) -> None:
        """Test combine_fragments_parallel with empty list."""
        from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

        processor = ParallelReportProcessor()

        result = processor.combine_fragments_parallel([])

        assert len(result) == 0

    @pytest.mark.unit
    def test_combine_fragments_parallel_single(self, sample_lines: list[str]) -> None:
        """Test combine_fragments_parallel with single fragment."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment
        from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

        processor = ParallelReportProcessor()
        frag = RustAcceleratedReportFragment(sample_lines)

        result = processor.combine_fragments_parallel([frag])

        assert result.to_list() == sample_lines


# ============================================================================
# Integration Tests
# ============================================================================


class TestReportIntegration:
    """Integration tests for report components."""

    @pytest.mark.unit
    def test_compose_multiple_section_fragments(self) -> None:
        """Test composing a complete report from multiple sections."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

        generator = RustAcceleratedReportGenerator()
        composer = RustAcceleratedReportComposer()

        # Add various section headers (all methods are now instance methods)
        composer.add(generator.generate_header("test-crash.log"))
        composer.add(generator.generate_suspect_section_header())
        composer.add(generator.generate_suspect_section(["TestSuspect"]))
        composer.add(generator.generate_suspect_found_footer(True))

        result = composer.compose()

        assert len(result) > 0

    @pytest.mark.unit
    def test_fragment_addition_chain(self) -> None:
        """Test chaining fragment additions."""
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

        frag1 = RustAcceleratedReportFragment(["A\n"])
        frag2 = RustAcceleratedReportFragment(["B\n"])
        frag3 = RustAcceleratedReportFragment(["C\n"])

        combined = frag1 + frag2 + frag3

        lines = combined.to_list()
        assert "A\n" in lines
        assert "B\n" in lines
        assert "C\n" in lines

    @pytest.mark.unit
    def test_parallel_processor_with_composer(self) -> None:
        """Test using parallel processor with composer."""
        from ClassicLib.integration.rust.report.composer import RustAcceleratedReportComposer
        from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment
        from ClassicLib.integration.rust.report.parallel import ParallelReportProcessor

        processor = ParallelReportProcessor()

        # Create fragments
        frags = [
            RustAcceleratedReportFragment(["Section 1\n"]),
            RustAcceleratedReportFragment(["Section 2\n"]),
        ]

        # Combine in parallel
        combined = processor.combine_fragments_parallel(frags)

        # Add to composer
        composer = RustAcceleratedReportComposer()
        composer.add(combined)

        result = composer.build_string()
        assert isinstance(result, str)

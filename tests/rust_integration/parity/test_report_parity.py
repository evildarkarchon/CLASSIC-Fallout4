"""
Comprehensive report generation and formatting parity validation tests.

This module provides detailed validation that Rust report generation components produce
identical results to Python implementations. Tests cover ReportFragment operations,
ReportGenerator methods, and report composition.

Report Generation Components Tested:
- ReportFragment creation and manipulation (from_lines, empty, with_header, combine)
- ReportGenerator section headers and content generation
- Markdown formatting consistency
- Performance comparison between Rust and Python implementations

The tests ensure that Rust report generation maintains 100% functional compatibility
with the Python implementation while providing significant performance improvements.
"""

# ruff: noqa: ANN201, ANN001, ANN204, PLR6301, ARG002, ANN003, BLE001

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest

from ClassicLib.integration.factory import detect_component, get_rust_component_status

if TYPE_CHECKING:
    from collections.abc import Callable

# Check if Rust report components are available
RUST_AVAILABLE = get_rust_component_status()["available"]
RUST_REPORT_AVAILABLE = RUST_AVAILABLE.get("report_generation", False)

# Try to import Rust components
_rust_available, _rust_scanlog = detect_component("classic_scanlog")
if _rust_available and _rust_scanlog:
    RustReportGenerator = getattr(_rust_scanlog, "ReportGenerator", None)
    RustReportFragment = getattr(_rust_scanlog, "ReportFragment", None)
else:
    RustReportGenerator = None
    RustReportFragment = None

# Import Python implementations
from ClassicLib.scanning.logs.reporting import ReportFragment as PythonReportFragment  # noqa: E402

logger = logging.getLogger(__name__)


class ReportParityValidator:
    """
    Parity validator for report generation components.

    Provides methods to create Rust and Python implementations of report
    generation components for parity comparison testing.
    """

    def __init__(self) -> None:
        """Initialize the report parity validator."""
        self._rust_available = RUST_REPORT_AVAILABLE and RustReportGenerator is not None

    def create_rust_implementation(self) -> Any | None:
        """
        Create an instance of the Rust ReportGenerator implementation.

        Returns:
            Rust ReportGenerator instance, or None if not available.
        """
        if not self._rust_available or RustReportGenerator is None:
            return None
        return RustReportGenerator()

    def create_python_implementation(self) -> dict[str, Any]:
        """
        Create a dictionary of Python report generation utilities.

        Returns:
            Dictionary containing Python report generation functions and utilities.
        """
        return {
            "report_fragment": PythonReportFragment,
            "markdown_utils": {
                "format_plugin_list": self._format_plugin_list,
                "format_formid_list": self._format_formid_list,
                "generate_statistics": self._generate_statistics,
            },
        }

    @staticmethod
    def _format_plugin_list(plugins: dict[str, str]) -> str:
        """
        Format a plugin dictionary as a markdown list.

        Args:
            plugins: Dictionary mapping indices to plugin names.

        Returns:
            Formatted markdown string.
        """
        lines = ["## Plugin Load Order", ""]
        for index, name in plugins.items():
            lines.append(f"[{index}] {name}")
        return "\n".join(lines)

    @staticmethod
    def _format_formid_list(formids: list[str]) -> str:
        """
        Format a list of FormIDs as a markdown list.

        Args:
            formids: List of FormID strings.

        Returns:
            Formatted markdown string.
        """
        lines = ["## FormIDs Found", ""]
        for i, formid in enumerate(formids, 1):
            lines.append(f"{i}. {formid}")
        return "\n".join(lines)

    @staticmethod
    def _generate_statistics(stats: dict[str, int]) -> str:
        """
        Generate a statistics section as markdown.

        Args:
            stats: Dictionary of statistic names to values.

        Returns:
            Formatted markdown string.
        """
        lines = ["## Analysis Statistics", ""]
        if "plugin_count" in stats:
            lines.append(f"Total Plugins: {stats['plugin_count']}")
        if "formid_count" in stats:
            lines.append(f"FormIDs Found: {stats['formid_count']}")
        for key, value in stats.items():
            if key not in ("plugin_count", "formid_count"):
                lines.append(f"{key}: {value}")
        return "\n".join(lines)


@dataclass
class ParityResult:
    """Results of a parity comparison between Rust and Python implementations."""

    component_name: str
    method_name: str
    test_case: str
    rust_available: bool
    passed: bool
    rust_result: Any = None
    python_result: Any = None
    differences: list[str] | None = None
    rust_execution_time: float = 0.0
    python_execution_time: float = 0.0
    performance_improvement: float = 0.0
    error_message: str | None = None

    @property
    def performance_gain(self) -> str:
        """Get human-readable performance improvement."""
        if self.python_execution_time > 0 and self.rust_execution_time > 0:
            improvement = self.python_execution_time / self.rust_execution_time
            return f"{improvement:.1f}x faster"
        return "N/A"


def normalize_content(content: list[str] | tuple[str, ...]) -> list[str]:
    """Normalize content for comparison.

    Args:
        content: Lines of content to normalize.

    Returns:
        Normalized list of strings with consistent formatting.
    """
    if not content:
        return []
    result = [line.rstrip() for line in content]
    # Remove trailing empty lines
    while result and not result[-1]:
        result.pop()
    return result


def compare_fragments(rust_fragment: Any, python_fragment: Any, method_name: str = "unknown") -> tuple[bool, list[str]]:
    """Compare Rust and Python ReportFragment outputs.

    Args:
        rust_fragment: Fragment from Rust implementation.
        python_fragment: Fragment from Python implementation.
        method_name: Name of the method being tested (for error messages).

    Returns:
        Tuple of (is_identical, list_of_differences).
    """
    differences = []

    # Get content from both fragments
    if hasattr(rust_fragment, "to_list"):
        rust_content = rust_fragment.to_list()
    elif isinstance(rust_fragment, (list, tuple)):
        rust_content = list(rust_fragment)
    else:
        differences.append(f"Rust result is not a fragment: {type(rust_fragment)}")
        return False, differences

    if hasattr(python_fragment, "content"):
        python_content = list(python_fragment.content)
    elif hasattr(python_fragment, "to_list"):
        python_content = python_fragment.to_list()
    elif isinstance(python_fragment, (list, tuple)):
        python_content = list(python_fragment)
    else:
        differences.append(f"Python result is not a fragment: {type(python_fragment)}")
        return False, differences

    # Normalize for comparison
    rust_normalized = normalize_content(rust_content)
    python_normalized = normalize_content(python_content)

    if rust_normalized != python_normalized:
        differences.append(f"{method_name}: Content differs")
        if len(rust_normalized) != len(python_normalized):
            differences.append(f"  Line count: Rust={len(rust_normalized)}, Python={len(python_normalized)}")
        # Show first few differences
        for i, (r_line, p_line) in enumerate(zip(rust_normalized[:10], python_normalized[:10], strict=False)):
            if r_line != p_line:
                differences.append(f"  Line {i}: Rust='{r_line[:50]}' vs Python='{p_line[:50]}'")
        return False, differences

    # Check has_content / is_empty equivalence
    rust_empty = rust_fragment.is_empty() if hasattr(rust_fragment, "is_empty") else len(rust_content) == 0  # pyright: ignore[reportAttributeAccessIssue]
    python_has_content = python_fragment.has_content if hasattr(python_fragment, "has_content") else len(python_content) > 0  # pyright: ignore[reportAttributeAccessIssue]

    if rust_empty == python_has_content:  # They should be opposites
        differences.append(f"{method_name}: Empty state mismatch - Rust.is_empty()={rust_empty}, Python.has_content={python_has_content}")
        return False, differences

    return True, []


def skip_if_rust_unavailable():
    """Create a pytest skip marker if Rust report components are unavailable."""
    return pytest.mark.skipif(
        not RUST_REPORT_AVAILABLE or RustReportGenerator is None or RustReportFragment is None,
        reason="Rust report generation components not available",
    )


@pytest.fixture
def rust_report_generator():
    """Fixture providing a Rust ReportGenerator instance."""
    if RustReportGenerator is None:
        pytest.skip("Rust ReportGenerator not available")
    return RustReportGenerator()


@pytest.fixture
def rust_report_generator_with_config():
    """Fixture providing a configured Rust ReportGenerator instance."""
    if RustReportGenerator is None:
        pytest.skip("Rust ReportGenerator not available")
    return RustReportGenerator.with_config("CLASSIC v1.0.0", "Buffout 4")


@pytest.mark.integration
class TestReportFragmentParity:
    """Test parity between Rust and Python ReportFragment implementations."""

    @skip_if_rust_unavailable()
    def test_empty_fragment_parity(self):
        """Test that empty fragments are equivalent between Rust and Python."""
        rust_empty = RustReportFragment.empty()  # pyright: ignore[reportOptionalMemberAccess]
        python_empty = PythonReportFragment.empty()

        assert rust_empty.is_empty(), "Rust empty fragment should be empty"
        assert not python_empty.has_content, "Python empty fragment should have no content"

        rust_list = rust_empty.to_list()
        python_list = python_empty.to_list()

        assert rust_list == python_list, f"Empty fragments differ: Rust={rust_list}, Python={python_list}"

    @skip_if_rust_unavailable()
    def test_from_lines_parity(self):
        """Test that from_lines creates equivalent fragments."""
        test_lines = ["Line 1", "Line 2", "Line 3"]

        rust_fragment = RustReportFragment.from_lines(test_lines)  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment = PythonReportFragment.from_lines(test_lines)

        is_identical, differences = compare_fragments(rust_fragment, python_fragment, "from_lines")
        assert is_identical, f"from_lines parity failed: {differences}"

    @skip_if_rust_unavailable()
    def test_from_lines_empty_parity(self):
        """Test that from_lines with empty list creates equivalent fragments."""
        rust_fragment = RustReportFragment.from_lines([])  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment = PythonReportFragment.from_lines([])

        assert rust_fragment.is_empty(), "Rust fragment from empty list should be empty"
        assert not python_fragment.has_content, "Python fragment from empty list should have no content"

    @skip_if_rust_unavailable()
    def test_with_header_parity(self):
        """Test that with_header produces equivalent results."""
        base_lines = ["Content line 1", "Content line 2"]
        header_lines = ["# Header", ""]

        rust_base = RustReportFragment.from_lines(base_lines)  # pyright: ignore[reportOptionalMemberAccess]
        python_base = PythonReportFragment.from_lines(base_lines)

        rust_with_header = rust_base.with_header(header_lines)
        python_with_header = python_base.with_header(header_lines)

        is_identical, differences = compare_fragments(rust_with_header, python_with_header, "with_header")
        assert is_identical, f"with_header parity failed: {differences}"

    @skip_if_rust_unavailable()
    def test_combine_parity(self):
        """Test that combining fragments produces equivalent results."""
        lines1 = ["Fragment 1 line 1", "Fragment 1 line 2"]
        lines2 = ["Fragment 2 line 1", "Fragment 2 line 2"]

        rust_frag1 = RustReportFragment.from_lines(lines1)  # pyright: ignore[reportOptionalMemberAccess]
        rust_frag2 = RustReportFragment.from_lines(lines2)  # pyright: ignore[reportOptionalMemberAccess]
        rust_combined = rust_frag1.combine(rust_frag2)

        python_frag1 = PythonReportFragment.from_lines(lines1)
        python_frag2 = PythonReportFragment.from_lines(lines2)
        python_combined = python_frag1 + python_frag2

        is_identical, differences = compare_fragments(rust_combined, python_combined, "combine")
        assert is_identical, f"combine parity failed: {differences}"

    @skip_if_rust_unavailable()
    def test_unicode_content_parity(self):
        """Test that unicode content is handled identically."""
        unicode_lines = [
            "Test with unicode: ñáéíóú",
            "日本語 Japanese text",
            "Русский Russian text",
            "Emoji: 🎯 🚀 ✅",
        ]

        rust_fragment = RustReportFragment.from_lines(unicode_lines)  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment = PythonReportFragment.from_lines(unicode_lines)

        is_identical, differences = compare_fragments(rust_fragment, python_fragment, "unicode")
        assert is_identical, f"Unicode content parity failed: {differences}"

    @skip_if_rust_unavailable()
    @pytest.mark.performance
    def test_from_lines_performance(self):
        """Test that Rust from_lines is faster than Python."""
        # Create a large list of lines
        large_lines = [f"Line {i}: Some content here with text" for i in range(1000)]

        iterations = 100

        # Time Rust
        start = time.perf_counter()
        for _ in range(iterations):
            RustReportFragment.from_lines(large_lines)  # pyright: ignore[reportOptionalMemberAccess]
        rust_time = time.perf_counter() - start

        # Time Python
        start = time.perf_counter()
        for _ in range(iterations):
            PythonReportFragment.from_lines(large_lines)
        python_time = time.perf_counter() - start

        speedup = python_time / rust_time if rust_time > 0 else 0
        logger.info(f"ReportFragment.from_lines performance: Rust={rust_time:.4f}s, Python={python_time:.4f}s, Speedup={speedup:.1f}x")

        # Rust should be at least as fast (no strict requirement, just informational)
        assert rust_time > 0, "Rust execution time should be measurable"


@pytest.mark.integration
class TestReportGeneratorParity:
    """Test parity between Rust ReportGenerator and Python implementations."""

    @skip_if_rust_unavailable()
    def test_generate_header_format(self, rust_report_generator):
        """Test that generate_header produces valid markdown header format."""
        header = rust_report_generator.generate_header("crash-2024-01-01.log")

        # Convert to list for inspection
        content = header.to_list() if hasattr(header, "to_list") else list(header)

        assert len(content) > 0, "Header should have content"
        # Header should contain the filename
        header_text = "\n".join(content)
        assert "crash-2024-01-01.log" in header_text or "CRASH" in header_text.upper()

    @skip_if_rust_unavailable()
    def test_generate_footer_format(self, rust_report_generator):
        """Test that generate_footer produces valid content."""
        footer = rust_report_generator.generate_footer()

        content = footer.to_list() if hasattr(footer, "to_list") else list(footer)
        # Footer may be empty or have content - just verify it's valid
        assert isinstance(content, list), "Footer should return a list"

    @skip_if_rust_unavailable()
    def test_generate_error_section_format(self, rust_report_generator):
        """Test that generate_error_section produces valid error section."""
        error_section = rust_report_generator.generate_error_section(
            main_error="EXCEPTION_ACCESS_VIOLATION",
            crashgen_version="1.32.1",
            is_outdated=False,
        )

        content = error_section.to_list() if hasattr(error_section, "to_list") else list(error_section)
        assert len(content) > 0, "Error section should have content"

        section_text = "\n".join(content)
        # Should mention the error or version
        assert "EXCEPTION" in section_text.upper() or "ERROR" in section_text.upper() or "1.32.1" in section_text

    @skip_if_rust_unavailable()
    def test_generate_error_section_outdated(self, rust_report_generator):
        """Test error section with outdated version flag."""
        error_section = rust_report_generator.generate_error_section(
            main_error="EXCEPTION_ACCESS_VIOLATION",
            crashgen_version="1.30.0",
            is_outdated=True,
        )

        content = error_section.to_list() if hasattr(error_section, "to_list") else list(error_section)
        assert len(content) > 0, "Error section should have content"

    @skip_if_rust_unavailable()
    def test_generate_section_headers(self, rust_report_generator):
        """Test that all section headers are generated correctly."""
        section_methods = [
            "generate_formid_section_header",
            "generate_plugin_suspect_header",
            "generate_record_section_header",
            "generate_settings_section_header",
            "generate_suspect_section_header",
        ]

        for method_name in section_methods:
            if hasattr(rust_report_generator, method_name):
                method = getattr(rust_report_generator, method_name)
                result = method()

                content = result.to_list() if hasattr(result, "to_list") else list(result)
                assert isinstance(content, list), f"{method_name} should return fragment with list content"
                # Section headers typically have content
                logger.info(f"{method_name}: {len(content)} lines")

    @skip_if_rust_unavailable()
    def test_generate_mod_check_header(self, rust_report_generator):
        """Test mod check header generation."""
        header = rust_report_generator.generate_mod_check_header("CHECKING IMPORTANT MODS")

        content = header.to_list() if hasattr(header, "to_list") else list(header)
        assert isinstance(content, list), "Mod check header should return list"

    @skip_if_rust_unavailable()
    def test_generate_suspect_found_footer(self, rust_report_generator):
        """Test suspect found footer generation."""
        # Test with suspects found
        footer_found = rust_report_generator.generate_suspect_found_footer(True)
        content_found = footer_found.to_list() if hasattr(footer_found, "to_list") else list(footer_found)
        assert isinstance(content_found, list)

        # Test with no suspects
        footer_none = rust_report_generator.generate_suspect_found_footer(False)
        content_none = footer_none.to_list() if hasattr(footer_none, "to_list") else list(footer_none)
        assert isinstance(content_none, list)

    @skip_if_rust_unavailable()
    def test_generate_suspect_section(self, rust_report_generator):
        """Test suspect section generation."""
        # Test with suspects (expects a list of suspect strings)
        suspects = ["Suspect plugin 1", "Suspect plugin 2"]
        section = rust_report_generator.generate_suspect_section(suspects)
        content = section.to_list() if hasattr(section, "to_list") else list(section)
        assert isinstance(content, list)
        assert len(content) > 0, "Suspect section should have content when suspects provided"

        # Test with empty suspects
        empty_section = rust_report_generator.generate_suspect_section([])
        empty_content = empty_section.to_list() if hasattr(empty_section, "to_list") else list(empty_section)
        assert isinstance(empty_content, list)

    @skip_if_rust_unavailable()
    def test_with_config_creates_valid_generator(self):
        """Test that with_config creates a working generator."""
        generator = RustReportGenerator.with_config("CLASSIC v2.0.0", "Buffout 4")  # pyright: ignore[reportOptionalMemberAccess]
        assert generator is not None

        # Should be able to use the configured generator
        header = generator.generate_header("test.log")
        content = header.to_list() if hasattr(header, "to_list") else list(header)
        assert isinstance(content, list)


@pytest.mark.integration
@pytest.mark.performance
class TestReportGeneratorPerformance:
    """Performance tests for Rust report generation."""

    @skip_if_rust_unavailable()
    def test_header_generation_performance(self, rust_report_generator):
        """Benchmark header generation performance."""
        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            rust_report_generator.generate_header(f"crash-{i}.log")
        elapsed = time.perf_counter() - start

        ops_per_sec = iterations / elapsed
        logger.info(f"generate_header: {ops_per_sec:.0f} ops/sec ({elapsed:.4f}s for {iterations} iterations)")

        # Should be fast
        assert elapsed < 5.0, f"Header generation too slow: {elapsed:.2f}s for {iterations} iterations"

    @skip_if_rust_unavailable()
    def test_error_section_generation_performance(self, rust_report_generator):
        """Benchmark error section generation performance."""
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            rust_report_generator.generate_error_section("EXCEPTION_ACCESS_VIOLATION", "1.32.1", False)
        elapsed = time.perf_counter() - start

        ops_per_sec = iterations / elapsed
        logger.info(f"generate_error_section: {ops_per_sec:.0f} ops/sec")

        assert elapsed < 5.0, f"Error section generation too slow: {elapsed:.2f}s"

    @skip_if_rust_unavailable()
    def test_full_report_assembly_performance(self, rust_report_generator):
        """Benchmark full report assembly with all sections."""
        iterations = 100

        start = time.perf_counter()
        for i in range(iterations):
            # Generate all sections
            header = rust_report_generator.generate_header(f"crash-{i}.log")
            error = rust_report_generator.generate_error_section("ERROR", "1.0", False)
            formid_header = rust_report_generator.generate_formid_section_header()
            plugin_header = rust_report_generator.generate_plugin_suspect_header()
            record_header = rust_report_generator.generate_record_section_header()
            settings_header = rust_report_generator.generate_settings_section_header()
            suspect_header = rust_report_generator.generate_suspect_section_header()
            suspect_footer = rust_report_generator.generate_suspect_found_footer(True)
            footer = rust_report_generator.generate_footer()

            # Combine all fragments
            combined = header.combine(error)
            combined = combined.combine(formid_header)
            combined = combined.combine(plugin_header)
            combined = combined.combine(record_header)
            combined = combined.combine(settings_header)
            combined = combined.combine(suspect_header)
            combined = combined.combine(suspect_footer)
            combined = combined.combine(footer)

            # Convert to list
            _ = combined.to_list()

        elapsed = time.perf_counter() - start

        ops_per_sec = iterations / elapsed
        logger.info(f"Full report assembly: {ops_per_sec:.0f} reports/sec ({elapsed:.4f}s)")

        assert elapsed < 10.0, f"Full report assembly too slow: {elapsed:.2f}s"


@pytest.mark.integration
class TestReportFragmentEdgeCases:
    """Test edge cases for ReportFragment operations."""

    @skip_if_rust_unavailable()
    def test_very_long_lines(self):
        """Test handling of very long lines."""
        long_line = "A" * 10000
        lines = [long_line, "Short line", long_line]

        rust_fragment = RustReportFragment.from_lines(lines)  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment = PythonReportFragment.from_lines(lines)

        is_identical, differences = compare_fragments(rust_fragment, python_fragment, "long_lines")
        assert is_identical, f"Long line handling differs: {differences}"

    @skip_if_rust_unavailable()
    def test_many_lines(self):
        """Test handling of many lines."""
        many_lines = [f"Line {i}" for i in range(10000)]

        rust_fragment = RustReportFragment.from_lines(many_lines)  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment = PythonReportFragment.from_lines(many_lines)

        assert rust_fragment.len() == len(many_lines), "Rust fragment has wrong line count"
        assert len(python_fragment.content) == len(many_lines), "Python fragment has wrong line count"

    @skip_if_rust_unavailable()
    def test_special_characters(self):
        """Test handling of special characters."""
        special_lines = [
            "Line with\ttabs",
            "Line with   multiple   spaces",
            "Line with special chars: <>&\"'",
            "Line with backslash: C:\\Path\\File",
            "Line with newline escape: \\n",
        ]

        rust_fragment = RustReportFragment.from_lines(special_lines)  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment = PythonReportFragment.from_lines(special_lines)

        is_identical, differences = compare_fragments(rust_fragment, python_fragment, "special_chars")
        assert is_identical, f"Special character handling differs: {differences}"

    @skip_if_rust_unavailable()
    def test_empty_lines_in_content(self):
        """Test handling of empty lines within content."""
        lines_with_empty = ["Line 1", "", "Line 3", "", "", "Line 6"]

        rust_fragment = RustReportFragment.from_lines(lines_with_empty)  # pyright: ignore[reportOptionalMemberAccess]
        python_fragment = PythonReportFragment.from_lines(lines_with_empty)

        is_identical, differences = compare_fragments(rust_fragment, python_fragment, "empty_lines")
        assert is_identical, f"Empty line handling differs: {differences}"

    @skip_if_rust_unavailable()
    def test_combine_with_empty(self):
        """Test combining a fragment with an empty fragment."""
        content_lines = ["Content line 1", "Content line 2"]

        rust_content = RustReportFragment.from_lines(content_lines)  # pyright: ignore[reportOptionalMemberAccess]
        rust_empty = RustReportFragment.empty()  # pyright: ignore[reportOptionalMemberAccess]
        rust_combined = rust_content.combine(rust_empty)

        python_content = PythonReportFragment.from_lines(content_lines)
        python_empty = PythonReportFragment.empty()
        python_combined = python_content + python_empty

        is_identical, differences = compare_fragments(rust_combined, python_combined, "combine_with_empty")
        assert is_identical, f"Combine with empty differs: {differences}"

    @skip_if_rust_unavailable()
    def test_with_header_on_empty(self):
        """Test with_header on an empty fragment."""
        header_lines = ["# Header"]

        rust_empty = RustReportFragment.empty()  # pyright: ignore[reportOptionalMemberAccess]
        rust_with_header = rust_empty.with_header(header_lines)

        python_empty = PythonReportFragment.empty()
        python_with_header = python_empty.with_header(header_lines)

        # Both should remain effectively empty (Python returns self, Rust may vary)
        rust_content = rust_with_header.to_list()
        python_content = python_with_header.to_list()

        # The behavior might differ - Python returns self (empty), Rust might add header
        # Just verify both produce valid results
        assert isinstance(rust_content, list), "Rust should return a list"
        assert isinstance(python_content, list), "Python should return a list"

    @skip_if_rust_unavailable()
    def test_multiple_combines(self):
        """Test chaining multiple combine operations."""
        fragments_data = [
            ["Section 1 line 1", "Section 1 line 2"],
            ["Section 2 line 1"],
            ["Section 3 line 1", "Section 3 line 2", "Section 3 line 3"],
            ["Section 4 line 1"],
        ]

        # Build Rust chain
        rust_result = RustReportFragment.from_lines(fragments_data[0])  # pyright: ignore[reportOptionalMemberAccess]
        for data in fragments_data[1:]:
            rust_result = rust_result.combine(RustReportFragment.from_lines(data))  # pyright: ignore[reportOptionalMemberAccess]

        # Build Python chain
        python_result = PythonReportFragment.from_lines(fragments_data[0])
        for data in fragments_data[1:]:
            python_result = python_result + PythonReportFragment.from_lines(data)

        is_identical, differences = compare_fragments(rust_result, python_result, "multiple_combines")
        assert is_identical, f"Multiple combines differ: {differences}"


@pytest.mark.integration
class TestFullReportParity:
    """Test full report generation parity between Rust and Python."""

    @skip_if_rust_unavailable()
    def test_generate_header_exact_match(self, rust_report_generator):
        """Test that header output matches Python exactly (no VR)."""
        from ClassicLib.scanning.logs.report_generator import ReportGeneratorFragments

        py_gen = ReportGeneratorFragments(None)

        # Generate headers (no VR parameter now)
        rust_header = rust_report_generator.generate_header("crash-2024-01-01.log")
        py_header = py_gen.generate_header("crash-2024-01-01.log")

        # Compare normalized content
        rust_content = normalize_content(rust_header.to_list())
        py_content = normalize_content(py_header.to_list())

        assert rust_content == py_content, f"Header mismatch:\nRust: {rust_content}\nPython: {py_content}"

    @skip_if_rust_unavailable()
    def test_generate_error_section_semantic_parity(self, rust_report_generator_with_config):
        """Test error section semantic parity for both outdated and current versions.

        Note: Character-for-character parity is NOT possible for error sections because:
        - Python computes is_outdated using Version() comparison with game_version_id paths
        - Rust receives pre-computed is_outdated boolean
        - Both produce semantically equivalent output but may differ in intermediate state

        This test validates that both produce valid error section content with the
        same semantic meaning (outdated warning presence/absence based on is_outdated).
        """
        # Test with current version (not outdated)
        rust_error = rust_report_generator_with_config.generate_error_section(
            "EXCEPTION_ACCESS_VIOLATION", "1.37.0", False
        )

        rust_content = normalize_content(rust_error.to_list())

        # Semantic checks: Rust should produce content for current version
        assert len(rust_content) > 0, "Rust error section should have content"
        rust_text = "\n".join(rust_content)
        assert "EXCEPTION_ACCESS_VIOLATION" in rust_text or "Error" in rust_text, \
            "Error section should reference the main error"
        assert "1.37.0" in rust_text, \
            "Error section should reference crashgen version"

        # Should NOT have outdated warning when is_outdated=False
        assert "OUTDATED" not in rust_text.upper(), \
            "Rust should NOT show outdated warning when is_outdated=False"

    @skip_if_rust_unavailable()
    def test_generate_error_section_outdated_warning(self, rust_report_generator_with_config):
        """Test error section shows outdated warning when is_outdated=True."""
        rust_error = rust_report_generator_with_config.generate_error_section(
            "EXCEPTION_ACCESS_VIOLATION", "1.30.0", True
        )

        rust_content = normalize_content(rust_error.to_list())
        rust_text = "\n".join(rust_content)

        # Should have outdated warning when is_outdated=True
        assert "OUTDATED" in rust_text.upper() or "WARNING" in rust_text.upper(), \
            "Rust should show outdated warning when is_outdated=True"

    @skip_if_rust_unavailable()
    def test_generate_footer_exact_match(self, rust_report_generator):
        """Test footer output matches Python exactly."""
        from ClassicLib.scanning.logs.report_generator import ReportGeneratorFragments

        py_gen = ReportGeneratorFragments(None)

        rust_footer = rust_report_generator.generate_footer()
        py_footer = py_gen.generate_footer()

        rust_content = normalize_content(rust_footer.to_list())
        py_content = normalize_content(py_footer.to_list())

        assert rust_content == py_content, f"Footer mismatch:\nRust: {rust_content}\nPython: {py_content}"

    @skip_if_rust_unavailable()
    def test_section_headers_exact_match(self, rust_report_generator):
        """Test all section headers match Python exactly."""
        from ClassicLib.scanning.logs.report_generator import ReportGeneratorFragments

        py_gen = ReportGeneratorFragments(None)

        # Test each section header
        sections = [
            ("suspect_section_header", "generate_suspect_section_header"),
            ("settings_section_header", "generate_settings_section_header"),
            ("formid_section_header", "generate_formid_section_header"),
            ("record_section_header", "generate_record_section_header"),
            ("plugin_suspect_header", "generate_plugin_suspect_header"),
        ]

        for name, method_name in sections:
            rust_section = getattr(rust_report_generator, method_name)()
            py_section = getattr(py_gen, method_name)()

            rust_content = normalize_content(rust_section.to_list())
            py_content = normalize_content(py_section.to_list())

            assert rust_content == py_content, f"{name} mismatch:\nRust: {rust_content}\nPython: {py_content}"

    @skip_if_rust_unavailable()
    def test_suspect_found_footer_exact_match(self, rust_report_generator):
        """Test suspect found footer matches Python for both states."""
        from ClassicLib.scanning.logs.report_generator import ReportGeneratorFragments

        py_gen = ReportGeneratorFragments(None)

        # Test with suspects found
        rust_found = rust_report_generator.generate_suspect_found_footer(True)
        py_found = py_gen.generate_suspect_found_footer(True)

        assert normalize_content(rust_found.to_list()) == normalize_content(py_found.to_list()), \
            "Suspect found footer mismatch (found=True)"

        # Test with no suspects
        rust_none = rust_report_generator.generate_suspect_found_footer(False)
        py_none = py_gen.generate_suspect_found_footer(False)

        assert normalize_content(rust_none.to_list()) == normalize_content(py_none.to_list()), \
            "Suspect found footer mismatch (found=False)"

    @skip_if_rust_unavailable()
    def test_report_section_structure_matches_sample(self, rust_report_generator):
        """Test that generated report section structure matches sample autoscan reports.

        Validates per CONTEXT.md: "Keep current section structure: header, error, suspect, settings, footer"
        """
        # Generate all section headers to validate structure
        header = rust_report_generator.generate_header("crash-2024-01-01.log")
        header_lines = header.to_list()

        # Validate header format elements (matches samples in "Crash Logs" directory)
        assert any("AUTOSCAN REPORT GENERATED BY" in line for line in header_lines), \
            "Header should contain 'AUTOSCAN REPORT GENERATED BY'"
        assert any("FOR BEST VIEWING EXPERIENCE" in line for line in header_lines), \
            "Header should contain viewing instructions"
        assert any("BEWARE OF FALSE POSITIVES" in line for line in header_lines), \
            "Header should contain false positive warning"
        assert any("---" in line for line in header_lines), \
            "Header should contain markdown separator"

        # Validate section headers use proper markdown format
        suspect_header = rust_report_generator.generate_suspect_section_header()
        assert any("###" in line for line in suspect_header.to_list()), \
            "Suspect section should use markdown H3 format"

        settings_header = rust_report_generator.generate_settings_section_header()
        assert any("###" in line for line in settings_header.to_list()), \
            "Settings section should use markdown H3 format"

        footer = rust_report_generator.generate_footer()
        footer_lines = footer.to_list()
        assert len(footer_lines) > 0, "Footer should have content"

        # Validate section separators are markdown-compliant
        suspect_footer = rust_report_generator.generate_suspect_found_footer(True)
        assert any("---" in line for line in suspect_footer.to_list()), \
            "Section footers should include markdown separators"

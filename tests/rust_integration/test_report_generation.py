"""
Tests for Rust-accelerated report generation (Phase 5).

This test suite validates the Rust report generation module's functionality,
performance improvements, and backward compatibility with Python implementation.
"""

from __future__ import annotations

import time

import pytest

# Skip entire module if RustReportGeneration not available yet
pytest.importorskip("ClassicLib.ScanLog.RustReportGeneration", reason="RustReportGeneration module not yet implemented")

from ClassicLib.ScanLog.RustReportGeneration import (
    RUST_AVAILABLE,
    ParallelReportProcessor,
    ReportComposer,
    ReportFragment,
    ReportGenerator,
    StringPool,
)

from ClassicLib.ScanLog.fragments.report_composer import ReportComposer as PyReportComposer

# Also test against Python implementation for comparison
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyReportFragment


@pytest.mark.unit
class TestReportFragment:
    """Test ReportFragment functionality."""

    def test_empty_fragment(self):
        """Test creating an empty fragment."""
        fragment = ReportFragment.empty()
        assert not fragment.has_content
        assert len(fragment) == 0
        assert fragment.to_list() == []

    def test_from_lines(self):
        """Test creating fragment from lines."""
        lines = ["Line 1", "Line 2", "Line 3"]
        fragment = ReportFragment.from_lines(lines)

        assert fragment.has_content
        assert len(fragment) == 3
        assert fragment.to_list() == lines

    def test_with_header(self):
        """Test adding header to fragment."""
        lines = ["Content 1", "Content 2"]
        header = ["Header 1", "Header 2"]

        fragment = ReportFragment.from_lines(lines)
        with_header = fragment.with_header(header)

        expected = header + lines
        assert with_header.to_list() == expected
        assert len(with_header) == 4

    def test_combine_fragments(self):
        """Test combining two fragments."""
        fragment1 = ReportFragment.from_lines(["Line 1", "Line 2"])
        fragment2 = ReportFragment.from_lines(["Line 3", "Line 4"])

        combined = fragment1 + fragment2

        assert len(combined) == 4
        assert combined.to_list() == ["Line 1", "Line 2", "Line 3", "Line 4"]

    def test_empty_combination(self):
        """Test combining with empty fragments."""
        fragment = ReportFragment.from_lines(["Content"])
        empty = ReportFragment.empty()

        # Combining with empty should preserve content
        result1 = fragment + empty
        assert result1.to_list() == ["Content"]

        result2 = empty + fragment
        assert result2.to_list() == ["Content"]

        # Two empty fragments
        result3 = empty + empty
        assert not result3.has_content


@pytest.mark.unit
class TestStringPool:
    """Test string pooling functionality."""

    def test_string_interning(self):
        """Test that string interning works correctly."""
        pool = StringPool()

        # Intern the same string multiple times
        s1 = pool.intern("test_string")
        s2 = pool.intern("test_string")
        s3 = pool.intern("another_string")

        assert s1 == s2  # Same string should be returned
        assert s1 != s3  # Different strings

        # Check statistics
        stats = pool.stats()
        assert stats[0] >= 2  # Pool size (at least 2 unique strings)

    def test_batch_interning(self):
        """Test batch string interning."""
        pool = StringPool()

        strings = ["str1", "str2", "str1", "str3", "str2"]
        interned = pool.intern_batch(strings)

        assert len(interned) == len(strings)
        assert interned[0] == interned[2]  # Same string "str1"
        assert interned[1] == interned[4]  # Same string "str2"

    def test_pool_clear(self):
        """Test clearing the string pool."""
        pool = StringPool()

        # Add some strings
        pool.intern("string1")
        pool.intern("string2")

        stats_before = pool.stats()
        assert stats_before[0] > 0  # Pool has entries

        # Clear the pool
        pool.clear()

        stats_after = pool.stats()
        assert stats_after[0] == 0 or stats_after[0] != stats_before[0]  # Pool cleared or reset


@pytest.mark.unit
class TestReportComposer:
    """Test ReportComposer functionality."""

    def test_compose_single_fragment(self):
        """Test composing a single fragment."""
        composer = ReportComposer()
        fragment = ReportFragment.from_lines(["Line 1", "Line 2"])

        composer.add(fragment)
        result = composer.compose()

        assert result.to_list() == ["Line 1", "Line 2"]

    def test_compose_multiple_fragments(self):
        """Test composing multiple fragments."""
        composer = ReportComposer()

        for i in range(5):
            fragment = ReportFragment.from_lines([f"Fragment {i} - Line 1", f"Fragment {i} - Line 2"])
            composer.add(fragment)

        result = composer.compose()
        lines = result.to_list()

        assert len(lines) == 10  # 5 fragments * 2 lines each
        assert "Fragment 0" in lines[0]
        assert "Fragment 4" in lines[-1]

    def test_build_string(self):
        """Test building complete report as string."""
        composer = ReportComposer()

        composer.add(ReportFragment.from_lines(["# Header"]))
        composer.add(ReportFragment.from_lines(["Content line 1", "Content line 2"]))
        composer.add(ReportFragment.from_lines(["## Footer"]))

        report_string = composer.build_string()

        assert "# Header" in report_string
        assert "Content line 1" in report_string
        assert "## Footer" in report_string
        assert "\n" in report_string  # Should have newlines

    def test_empty_composer(self):
        """Test composing with no fragments."""
        composer = ReportComposer()
        result = composer.compose()

        assert not result.has_content
        assert result.to_list() == []


@pytest.mark.unit
class TestReportGenerator:
    """Test ReportGenerator functionality."""

    def test_generate_header(self):
        """Test header generation."""
        generator = ReportGenerator()
        header = generator.generate_header("test.log", "v1.0.0")

        lines = header.to_list()
        assert any("test.log" in line for line in lines)
        assert any("v1.0.0" in line for line in lines)
        assert any("AUTOSCAN REPORT" in line for line in lines)

    def test_generate_error_section(self):
        """Test error section generation."""
        generator = ReportGenerator()

        # Test with latest version
        section = generator.generate_error_section(
            main_error="Test Error",
            crashgen_version="4.0",
            crashgen_name="Buffout",
            is_latest=True,
            warn_outdated="",
        )

        lines = section.to_list()
        assert any("Test Error" in line for line in lines)
        assert any("✅" in line for line in lines)  # Latest version indicator

        # Test with outdated version
        section_outdated = generator.generate_error_section(
            main_error="Test Error",
            crashgen_version="3.0",
            crashgen_name="Buffout",
            is_latest=False,
            warn_outdated="Please update!",
        )

        lines_outdated = section_outdated.to_list()
        assert any("⚠️" in line for line in lines_outdated)
        assert any("Please update!" in line for line in lines_outdated)

    def test_generate_suspect_section(self):
        """Test suspect section generation."""
        generator = ReportGenerator()

        # Test with no suspects
        no_suspects = generator.generate_suspect_section([])
        lines = no_suspects.to_list()
        assert any("NO CRASH ERRORS" in line for line in lines)

        # Test with suspects
        suspects = ["Suspect 1: Bad mod", "Suspect 2: Memory issue"]
        with_suspects = generator.generate_suspect_section(suspects)
        lines = with_suspects.to_list()

        assert any("Suspect 1" in line for line in lines)
        assert any("Suspect 2" in line for line in lines)
        assert any("SOLUTIONS" in line for line in lines)


@pytest.mark.unit
class TestParallelReportProcessor:
    """Test parallel report processing."""

    def test_process_reports(self):
        """Test processing multiple reports in parallel."""
        processor = ParallelReportProcessor()

        # Create multiple reports
        reports = []
        for i in range(10):
            report_lines = [f"Report {i} - Header", f"Report {i} - Content", f"Report {i} - Footer"]
            reports.append(report_lines)

        # Process in parallel
        results = processor.process_reports(reports)

        assert len(results) == 10
        for i, result in enumerate(results):
            assert f"Report {i}" in result

    def test_combine_fragments_parallel(self):
        """Test combining fragments in parallel."""
        processor = ParallelReportProcessor()

        # Create many fragments
        fragments = []
        for i in range(20):
            fragment = ReportFragment.from_lines([f"Fragment {i}"])
            fragments.append(fragment)

        # Combine in parallel
        combined = processor.combine_fragments_parallel(fragments)

        lines = combined.to_list()
        assert len(lines) == 20
        assert all(f"Fragment {i}" in lines for i in range(20))


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceComparison:
    """Compare performance between Rust and Python implementations."""

    def generate_large_report_data(self, num_fragments: int = 100, lines_per_fragment: int = 50) -> list[list[str]]:
        """Generate large report data for testing."""
        fragments = []
        for i in range(num_fragments):
            lines = [f"Fragment {i} - Line {j}: " + "x" * 100 for j in range(lines_per_fragment)]
            fragments.append(lines)
        return fragments

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
    def test_composition_performance(self):
        """Test that Rust composition is faster than Python."""
        data = self.generate_large_report_data(100, 20)

        # Test Rust implementation
        rust_composer = ReportComposer()
        rust_start = time.perf_counter()
        for lines in data:
            rust_composer.add(ReportFragment.from_lines(lines))
        rust_result = rust_composer.compose()
        rust_time = time.perf_counter() - rust_start

        # Test Python implementation
        py_composer = PyReportComposer()
        py_start = time.perf_counter()
        for lines in data:
            py_composer.add(PyReportFragment.from_lines(lines))
        py_result = py_composer.compose()
        py_time = time.perf_counter() - py_start

        # Verify results are equivalent
        assert len(rust_result.to_list()) == len(py_result.to_list())

        # Performance assertion (should be at least 2x faster)
        speedup = py_time / rust_time
        print(f"Rust speedup: {speedup:.2f}x (Rust: {rust_time:.4f}s, Python: {py_time:.4f}s)")

        # Be conservative in CI environments
        assert speedup > 1.5, f"Expected Rust to be faster, got {speedup:.2f}x"

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
    def test_parallel_processing_performance(self):
        """Test parallel processing performance."""
        processor = ParallelReportProcessor()
        reports = self.generate_large_report_data(50, 30)

        start = time.perf_counter()
        results = processor.process_reports(reports)
        parallel_time = time.perf_counter() - start

        assert len(results) == 50
        print(f"Processed {len(reports)} reports in {parallel_time:.4f}s")

        # Should process multiple reports quickly
        assert parallel_time < 2.0, f"Parallel processing too slow: {parallel_time:.4f}s"


@pytest.mark.integration
class TestBackwardCompatibility:
    """Test backward compatibility with existing Python code."""

    def test_mixed_fragment_types(self):
        """Test mixing Rust and Python fragments."""
        composer = ReportComposer()

        # Add both Rust-accelerated and Python fragments
        rust_fragment = ReportFragment.from_lines(["Rust line 1", "Rust line 2"])
        py_fragment = PyReportFragment.from_lines(["Python line 1", "Python line 2"])

        composer.add(rust_fragment)
        composer.add(py_fragment)  # Should handle Python fragments transparently

        result = composer.compose()
        lines = result.to_list()

        assert "Rust line 1" in lines
        assert "Python line 1" in lines
        assert len(lines) == 4

    def test_api_compatibility(self):
        """Test that the API matches Python implementation."""
        # Both implementations should have the same methods
        rust_fragment = ReportFragment.from_lines(["test"])
        py_fragment = PyReportFragment.from_lines(["test"])

        # Check common methods exist
        assert hasattr(rust_fragment, "to_list")
        assert hasattr(rust_fragment, "with_header")
        assert hasattr(rust_fragment, "has_content")

        # Check properties
        assert rust_fragment.has_content == py_fragment.has_content
        assert len(rust_fragment.to_list()) == len(py_fragment.to_list())


@pytest.mark.unit
class TestMemoryEfficiency:
    """Test memory efficiency features."""

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
    def test_string_pooling_reduces_duplicates(self):
        """Test that string pooling reduces memory for duplicates."""
        pool = StringPool()

        # Create many duplicate strings
        duplicates = ["duplicate"] * 1000
        pool.intern_batch(duplicates)

        # Check pool statistics
        stats = pool.stats()
        pool_size = stats[0]

        # Pool should contain only one unique string despite 1000 inputs
        assert pool_size <= 10  # Allow some overhead

    def test_fragment_immutability(self):
        """Test that fragments are immutable."""
        original_lines = ["Line 1", "Line 2"]
        fragment = ReportFragment.from_lines(original_lines)

        # Modifying original list shouldn't affect fragment
        original_lines.append("Line 3")
        assert len(fragment) == 2

        # Getting content shouldn't allow modification
        content = fragment.to_list()
        content.append("Line 4")
        assert len(fragment) == 2

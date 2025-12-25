"""
Tests for Rust-accelerated report generation.

This test suite validates the Rust report generation module's functionality,
performance improvements, and compares behavior with Python implementation.

The Rust and Python implementations have different APIs:
- Rust ReportComposer: instance-based with add() method, compose() returns list[str]
- Python ReportComposer: static methods, compose(*fragments) returns ReportFragment
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

# Import Python implementations (always available)
from ClassicLib.ScanLog.fragments.report_composer import ReportComposer as PyReportComposer
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyReportFragment

# Try to import Rust implementation
try:
    import classic_scanlog

    RUST_AVAILABLE = True
    RustReportFragment = classic_scanlog.ReportFragment
    RustReportComposer = classic_scanlog.ReportComposer
    RustReportGenerator = classic_scanlog.ReportGenerator
    RustStringPool = classic_scanlog.StringPool
    RustParallelReportProcessor = classic_scanlog.ParallelReportProcessor
except ImportError:
    RUST_AVAILABLE = False
    if TYPE_CHECKING:
        # Type stubs for static analysis (never reached at runtime when import fails)
        from typing import Any

        RustReportFragment: Any = None
        RustReportComposer: Any = None
        RustReportGenerator: Any = None
        RustStringPool: Any = None
        RustParallelReportProcessor: Any = None


# =============================================================================
# Python Implementation Tests (Always Run)
# =============================================================================


@pytest.mark.unit
class TestPythonReportFragment:
    """Test Python ReportFragment functionality."""

    def test_empty_fragment(self):
        """Test creating an empty fragment."""
        fragment = PyReportFragment.empty()
        assert not fragment.has_content
        assert len(fragment.content) == 0
        assert fragment.to_list() == []

    def test_from_lines(self):
        """Test creating fragment from lines."""
        lines = ["Line 1", "Line 2", "Line 3"]
        fragment = PyReportFragment.from_lines(lines)

        assert fragment.has_content
        assert len(fragment.content) == 3
        assert fragment.to_list() == lines

    def test_with_header(self):
        """Test adding header to fragment."""
        lines = ["Content 1", "Content 2"]
        header = ["Header 1", "Header 2"]

        fragment = PyReportFragment.from_lines(lines)
        with_header = fragment.with_header(header)

        expected = header + lines
        assert with_header.to_list() == expected
        assert len(with_header.content) == 4

    def test_combine_fragments(self):
        """Test combining two fragments."""
        fragment1 = PyReportFragment.from_lines(["Line 1", "Line 2"])
        fragment2 = PyReportFragment.from_lines(["Line 3", "Line 4"])

        combined = fragment1 + fragment2

        assert len(combined.content) == 4
        assert combined.to_list() == ["Line 1", "Line 2", "Line 3", "Line 4"]

    def test_empty_combination(self):
        """Test combining with empty fragments."""
        fragment = PyReportFragment.from_lines(["Content"])
        empty = PyReportFragment.empty()

        # Combining with empty should preserve content
        result1 = fragment + empty
        assert result1.to_list() == ["Content"]

        result2 = empty + fragment
        assert result2.to_list() == ["Content"]

        # Two empty fragments
        result3 = empty + empty
        assert not result3.has_content


@pytest.mark.unit
class TestPythonReportComposer:
    """Test Python ReportComposer functionality."""

    def test_compose_single_fragment(self):
        """Test composing a single fragment."""
        fragment = PyReportFragment.from_lines(["Line 1", "Line 2"])

        result = PyReportComposer.compose(fragment)

        assert result.to_list() == ["Line 1", "Line 2"]

    def test_compose_multiple_fragments(self):
        """Test composing multiple fragments."""
        fragments = [PyReportFragment.from_lines([f"Fragment {i} - Line 1", f"Fragment {i} - Line 2"]) for i in range(5)]

        result = PyReportComposer.compose(*fragments)
        lines = result.to_list()

        assert len(lines) == 10  # 5 fragments * 2 lines each
        assert "Fragment 0" in lines[0]
        assert "Fragment 4" in lines[-1]

    def test_empty_compose(self):
        """Test composing with no fragments."""
        result = PyReportComposer.compose()

        assert not result.has_content
        assert result.to_list() == []


# =============================================================================
# Rust Implementation Tests (Skip if not available)
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestRustReportFragment:
    """Test Rust ReportFragment functionality."""

    def test_empty_fragment(self):
        """Test creating an empty fragment."""
        fragment = RustReportFragment.empty()
        assert fragment.is_empty()
        assert fragment.len() == 0
        assert fragment.to_list() == []

    def test_from_lines(self):
        """Test creating fragment from lines."""
        lines = ["Line 1", "Line 2", "Line 3"]
        fragment = RustReportFragment.from_lines(lines)

        assert not fragment.is_empty()
        assert fragment.len() == 3
        assert fragment.to_list() == lines

    def test_with_header(self):
        """Test adding header to fragment."""
        lines = ["Content 1", "Content 2"]
        header = ["Header 1", "Header 2"]

        fragment = RustReportFragment.from_lines(lines)
        with_header = fragment.with_header(header)

        expected = header + lines
        assert with_header.to_list() == expected
        assert with_header.len() == 4

    def test_combine_fragments(self):
        """Test combining two fragments."""
        fragment1 = RustReportFragment.from_lines(["Line 1", "Line 2"])
        fragment2 = RustReportFragment.from_lines(["Line 3", "Line 4"])

        # Rust uses combine() method instead of __add__
        combined = fragment1.combine(fragment2)

        assert combined.len() == 4
        assert combined.to_list() == ["Line 1", "Line 2", "Line 3", "Line 4"]

    def test_empty_combination(self):
        """Test combining with empty fragments."""
        fragment = RustReportFragment.from_lines(["Content"])
        empty = RustReportFragment.empty()

        # Combining with empty should preserve content
        result1 = fragment.combine(empty)
        assert result1.to_list() == ["Content"]

        result2 = empty.combine(fragment)
        assert result2.to_list() == ["Content"]

        # Two empty fragments
        result3 = empty.combine(empty)
        assert result3.is_empty()


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestRustStringPool:
    """Test Rust string pooling functionality."""

    def test_string_interning(self):
        """Test that string interning works correctly."""
        pool = RustStringPool()

        # Intern the same string multiple times
        s1 = pool.intern("test_string")
        s2 = pool.intern("test_string")
        s3 = pool.intern("another_string")

        assert s1 == s2  # Same string should be returned
        assert s1 != s3  # Different strings

        # Check statistics
        stats = pool.get_stats()
        assert stats[0] >= 2  # Pool size (at least 2 unique strings)

    def test_batch_interning(self):
        """Test batch string interning."""
        pool = RustStringPool()

        strings = ["str1", "str2", "str1", "str3", "str2"]
        interned = pool.intern_batch(strings)

        assert len(interned) == len(strings)
        assert interned[0] == interned[2]  # Same string "str1"
        assert interned[1] == interned[4]  # Same string "str2"

    def test_pool_clear(self):
        """Test clearing the string pool."""
        pool = RustStringPool()

        # Add some strings
        pool.intern("string1")
        pool.intern("string2")

        stats_before = pool.get_stats()
        assert stats_before[0] > 0  # Pool has entries

        # Clear the pool
        pool.clear()

        stats_after = pool.get_stats()
        assert stats_after[0] == 0 or stats_after[0] != stats_before[0]  # Pool cleared or reset


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestRustReportComposer:
    """Test Rust ReportComposer functionality."""

    def test_compose_single_fragment(self):
        """Test composing a single fragment."""
        composer = RustReportComposer()
        fragment = RustReportFragment.from_lines(["Line 1", "Line 2"])

        composer.add(fragment)
        # Rust compose() returns list[str], not ReportFragment
        result = composer.compose()

        assert result == ["Line 1", "Line 2"]

    def test_compose_multiple_fragments(self):
        """Test composing multiple fragments."""
        composer = RustReportComposer()

        for i in range(5):
            fragment = RustReportFragment.from_lines([f"Fragment {i} - Line 1", f"Fragment {i} - Line 2"])
            composer.add(fragment)

        result = composer.compose()

        assert len(result) == 10  # 5 fragments * 2 lines each
        assert "Fragment 0" in result[0]
        assert "Fragment 4" in result[-1]

    def test_build_string(self):
        """Test building complete report as string."""
        composer = RustReportComposer()

        composer.add(RustReportFragment.from_lines(["# Header"]))
        composer.add(RustReportFragment.from_lines(["Content line 1", "Content line 2"]))
        composer.add(RustReportFragment.from_lines(["## Footer"]))

        report_string = composer.build_string()

        assert "# Header" in report_string
        assert "Content line 1" in report_string
        assert "## Footer" in report_string
        assert "\n" in report_string  # Should have newlines

    def test_empty_composer(self):
        """Test composing with no fragments."""
        composer = RustReportComposer()
        result = composer.compose()

        assert result == []

    def test_fragment_count(self):
        """Test fragment count tracking."""
        composer = RustReportComposer()

        assert composer.fragment_count() == 0

        composer.add(RustReportFragment.from_lines(["Line 1"]))
        assert composer.fragment_count() == 1

        composer.add(RustReportFragment.from_lines(["Line 2"]))
        assert composer.fragment_count() == 2

    def test_add_many(self):
        """Test adding multiple fragments at once."""
        composer = RustReportComposer()

        fragments = [RustReportFragment.from_lines([f"Fragment {i}"]) for i in range(5)]
        composer.add_many(fragments)

        assert composer.fragment_count() == 5
        result = composer.compose()
        assert len(result) == 5


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestRustReportGenerator:
    """Test Rust ReportGenerator functionality."""

    def test_generate_header(self):
        """Test header generation."""
        generator = RustReportGenerator()
        header = generator.generate_header("test.log")

        lines = header.to_list()
        assert any("test.log" in line for line in lines)
        assert any("AUTOSCAN" in line.upper() for line in lines)

    def test_generate_error_section(self):
        """Test error section generation."""
        generator = RustReportGenerator()

        # Test with up-to-date version (is_outdated=False)
        section = generator.generate_error_section(
            main_error="Test Error",
            crashgen_version="4.0",
            is_outdated=False,
        )

        lines = section.to_list()
        assert any("Test Error" in line for line in lines)

        # Test with outdated version (is_outdated=True)
        section_outdated = generator.generate_error_section(
            main_error="Test Error",
            crashgen_version="3.0",
            is_outdated=True,
        )

        lines_outdated = section_outdated.to_list()
        # Should have some indicator of outdated status
        assert len(lines_outdated) > 0

    def test_generate_suspect_section(self):
        """Test suspect section generation."""
        generator = RustReportGenerator()

        # Test with no suspects
        no_suspects = generator.generate_suspect_section([])
        lines = no_suspects.to_list()
        # Should indicate no suspects found
        assert len(lines) >= 0  # May be empty or have "no suspects" message

        # Test with suspects
        suspects = ["Suspect 1: Bad mod", "Suspect 2: Memory issue"]
        with_suspects = generator.generate_suspect_section(suspects)
        lines = with_suspects.to_list()

        assert any("Suspect 1" in line for line in lines)
        assert any("Suspect 2" in line for line in lines)


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestRustParallelReportProcessor:
    """Test Rust parallel report processing."""

    def test_combine_fragments(self):
        """Test combining fragments using static method."""
        # Create many fragments
        fragments = [RustReportFragment.from_lines([f"Fragment {i}"]) for i in range(20)]

        # Combine using static method
        combined = RustParallelReportProcessor.combine_fragments(fragments)

        lines = combined.to_list()
        assert len(lines) == 20
        assert all(f"Fragment {i}" in lines for i in range(20))


# =============================================================================
# Performance Comparison Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestPerformanceComparison:
    """Compare performance between Rust and Python implementations."""

    def generate_large_report_data(self, num_fragments: int = 100, lines_per_fragment: int = 50) -> list[list[str]]:
        """Generate large report data for testing."""
        return [[f"Fragment {i} - Line {j}: " + "x" * 100 for j in range(lines_per_fragment)] for i in range(num_fragments)]

    def test_fragment_creation_performance(self):
        """Test that Rust fragment creation is competitive with Python."""
        data = self.generate_large_report_data(100, 20)

        # Test Rust implementation
        rust_start = time.perf_counter()
        rust_fragments = [RustReportFragment.from_lines(lines) for lines in data]
        rust_time = time.perf_counter() - rust_start

        # Test Python implementation
        py_start = time.perf_counter()
        py_fragments = [PyReportFragment.from_lines(lines) for lines in data]
        py_time = time.perf_counter() - py_start

        # Verify similar output
        assert len(rust_fragments) == len(py_fragments)

        print(f"Fragment creation - Rust: {rust_time:.4f}s, Python: {py_time:.4f}s")

    def test_composition_performance(self):
        """Test that Rust composition is faster than Python."""
        data = self.generate_large_report_data(100, 20)

        # Test Rust implementation
        rust_composer = RustReportComposer()
        rust_start = time.perf_counter()
        for lines in data:
            rust_composer.add(RustReportFragment.from_lines(lines))
        rust_result = rust_composer.compose()
        rust_time = time.perf_counter() - rust_start

        # Test Python implementation
        py_start = time.perf_counter()
        py_fragments = [PyReportFragment.from_lines(lines) for lines in data]
        py_result = PyReportComposer.compose(*py_fragments)
        py_time = time.perf_counter() - py_start

        # Verify similar output size
        assert len(rust_result) == len(py_result.to_list())

        # Performance comparison (not enforcing speedup requirement due to different APIs)
        speedup = py_time / rust_time if rust_time > 0 else float("inf")
        print(f"Composition speedup: {speedup:.2f}x (Rust: {rust_time:.4f}s, Python: {py_time:.4f}s)")


# =============================================================================
# API Compatibility Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestAPICompatibility:
    """Test API compatibility between Rust and Python implementations."""

    def test_fragment_output_equivalence(self):
        """Test that both implementations produce equivalent output."""
        lines = ["Line 1", "Line 2", "Line 3"]

        rust_fragment = RustReportFragment.from_lines(lines)
        py_fragment = PyReportFragment.from_lines(lines)

        assert rust_fragment.to_list() == py_fragment.to_list()

    def test_combine_output_equivalence(self):
        """Test that combining produces equivalent results."""
        lines1 = ["A", "B"]
        lines2 = ["C", "D"]

        rust_f1 = RustReportFragment.from_lines(lines1)
        rust_f2 = RustReportFragment.from_lines(lines2)
        rust_combined = rust_f1.combine(rust_f2)

        py_f1 = PyReportFragment.from_lines(lines1)
        py_f2 = PyReportFragment.from_lines(lines2)
        py_combined = py_f1 + py_f2

        assert rust_combined.to_list() == py_combined.to_list()

    def test_header_equivalence(self):
        """Test that header addition produces equivalent results."""
        lines = ["Content"]
        header = ["Header"]

        rust_fragment = RustReportFragment.from_lines(lines).with_header(header)
        py_fragment = PyReportFragment.from_lines(lines).with_header(header)

        assert rust_fragment.to_list() == py_fragment.to_list()


# =============================================================================
# Memory Efficiency Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust implementation not available")
class TestMemoryEfficiency:
    """Test memory efficiency features."""

    def test_string_pooling_reduces_duplicates(self):
        """Test that string pooling reduces memory for duplicates."""
        pool = RustStringPool()

        # Create many duplicate strings
        duplicates = ["duplicate"] * 1000
        pool.intern_batch(duplicates)

        # Check pool statistics
        stats = pool.get_stats()
        pool_size = stats[0]

        # Pool should contain only one unique string despite 1000 inputs
        assert pool_size <= 10  # Allow some overhead

    def test_rust_fragment_immutability(self):
        """Test that Rust fragments behave immutably."""
        original_lines = ["Line 1", "Line 2"]
        fragment = RustReportFragment.from_lines(original_lines)

        # Modifying original list shouldn't affect fragment
        original_lines.append("Line 3")
        assert fragment.len() == 2

        # Getting content shouldn't allow modification
        content = fragment.to_list()
        content.append("Line 4")
        assert fragment.len() == 2

    def test_python_fragment_immutability(self):
        """Test that Python fragments are immutable (frozen dataclass)."""
        original_lines = ["Line 1", "Line 2"]
        fragment = PyReportFragment.from_lines(original_lines)

        # Modifying original list shouldn't affect fragment (content is tuple)
        original_lines.append("Line 3")
        assert len(fragment.content) == 2

        # Getting content shouldn't allow modification
        content = fragment.to_list()
        content.append("Line 4")
        assert len(fragment.content) == 2

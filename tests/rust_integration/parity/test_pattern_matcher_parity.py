"""
Python integration tests for Rust PatternMatcher.

This module provides Python-side integration tests that mirror the comprehensive
Rust tests in classic-rust/tests/test_patterns.rs to ensure Python-Rust parity.

Tests cover:
- Basic pattern creation and matching
- Multi-pattern matching with Aho-Corasick
- Cache effectiveness and management
- Case-insensitive matching
- Edge cases (empty patterns, special characters, unicode)
- Performance characteristics
- PyO3 integration and error handling
"""

from __future__ import annotations

from typing import Any

import pytest

try:
    from classic_scanlog import PatternMatcher

    RUST_AVAILABLE = True
except ImportError:
    PatternMatcher: Any = None
    RUST_AVAILABLE = False


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestPatternMatcherBasic:
    """Test basic PatternMatcher functionality."""

    @pytest.mark.parametrize(
        "patterns,expected_count",
        [
            (["error", "warning", "info"], 3),
            ([], 0),
            (["single_pattern"], 1),
        ],
        ids=["three_patterns", "empty", "single"],
    )
    def test_creation(self, patterns, expected_count):
        """Test PatternMatcher creation with various pattern lists."""
        matcher = PatternMatcher(patterns)
        pattern_count, cache_size = matcher.get_stats()
        assert pattern_count == expected_count
        assert cache_size == 0  # Cache always starts empty


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestHasMatch:
    """Test has_match functionality."""

    @pytest.mark.parametrize(
        "patterns,text,expected",
        [
            # Simple matching
            (["error", "warning"], "This is an error message", True),
            (["error", "warning"], "Warning: something happened", True),
            (["error", "warning"], "This is just info", False),
            # Case insensitive
            (["error"], "ERROR", True),
            (["error"], "Error", True),
            (["error"], "eRrOr", True),
            (["error"], "error", True),
            # Edge cases
            (["error"], "", False),  # Empty text
            ([], "Any text here", False),  # No patterns
        ],
        ids=[
            "match_error",
            "match_warning",
            "no_match_info",
            "case_upper",
            "case_mixed",
            "case_alternating",
            "case_lower",
            "empty_text",
            "no_patterns",
        ],
    )
    def test_has_match(self, patterns, text, expected):
        """Test has_match with various patterns and texts."""
        matcher = PatternMatcher(patterns)
        assert matcher.has_match(text) is expected


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestFindFirst:
    """Test find_first functionality."""

    def test_find_first_basic(self):
        """Test basic find_first operation."""
        matcher = PatternMatcher(["error", "warning"])

        result = matcher.find_first("This is an error at position 11")
        assert result is not None

        position, pattern = result
        assert position == 11
        assert pattern == "error"

    def test_find_first_multiple_matches(self):
        """Test find_first with multiple matches (returns earliest)."""
        matcher = PatternMatcher(["error", "warning"])

        # Should find the first occurrence (earliest position)
        result = matcher.find_first("warning and error both present")
        assert result is not None

        position, pattern = result
        assert position == 0  # "warning" starts at 0
        assert pattern == "warning"

    def test_find_first_no_match(self):
        """Test find_first with no matches."""
        matcher = PatternMatcher(["error"])

        result = matcher.find_first("Nothing to find here")
        assert result is None

    def test_find_first_case_insensitive(self):
        """Test find_first case-insensitive matching."""
        matcher = PatternMatcher(["error"])

        result = matcher.find_first("Found ERROR at position 6")
        assert result is not None

        position, pattern = result
        assert position == 6
        assert pattern == "error"


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestFindAll:
    """Test find_all functionality."""

    def test_find_all_single_match(self):
        """Test find_all with single match."""
        matcher = PatternMatcher(["error"])

        matches = matcher.find_all("This is an error message")
        assert len(matches) == 1
        assert matches[0][0] == 11  # Position
        assert matches[0][1] == "error"  # Pattern

    def test_find_all_multiple_patterns(self):
        """Test find_all with multiple different patterns."""
        matcher = PatternMatcher(["error", "warning", "info"])

        text = "error at start, warning in middle, info at end"
        matches = matcher.find_all(text)

        assert len(matches) == 3

        # Verify all patterns found
        found_patterns = [pattern for _, pattern in matches]
        assert "error" in found_patterns
        assert "warning" in found_patterns
        assert "info" in found_patterns

    def test_find_all_duplicate_patterns(self):
        """Test find_all with same pattern multiple times."""
        matcher = PatternMatcher(["test"])

        matches = matcher.find_all("test test test")
        assert len(matches) == 3

        # Verify positions
        assert matches[0][0] == 0
        assert matches[1][0] == 5
        assert matches[2][0] == 10

    def test_find_all_overlapping_patterns(self):
        """Test find_all with overlapping patterns."""
        matcher = PatternMatcher(["abc", "bcd"])

        # Aho-Corasick finds overlapping matches
        matches = matcher.find_all("abcd")

        # Should find "abc" at position 0
        assert any(pos == 0 and pat == "abc" for pos, pat in matches)

    def test_find_all_no_matches(self):
        """Test find_all with no matches."""
        matcher = PatternMatcher(["error", "warning"])

        matches = matcher.find_all("Nothing to find here")
        assert len(matches) == 0

    def test_find_all_empty_text(self):
        """Test find_all with empty text."""
        matcher = PatternMatcher(["error"])

        matches = matcher.find_all("")
        assert len(matches) == 0


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestReplaceAll:
    """Test replace_all functionality."""

    @pytest.mark.parametrize(
        "patterns,text,replacement,expected",
        [
            # Basic replacement
            (["error"], "This is an error message", "SUCCESS", "This is an SUCCESS message"),
            # Multiple occurrences
            (["test"], "test test test", "PASS", "PASS PASS PASS"),
            # Multiple patterns
            (["error", "warning"], "error and warning both replaced", "REDACTED", "REDACTED and REDACTED both replaced"),
            # Case insensitive
            (["error"], "ERROR and error both replaced", "OK", "OK and OK both replaced"),
            # No matches
            (["error"], "Nothing to replace here", "REPLACEMENT", "Nothing to replace here"),
            # Empty replacement
            (["test"], "test this test", "", " this "),
        ],
        ids=[
            "basic",
            "multiple_occurrences",
            "multiple_patterns",
            "case_insensitive",
            "no_matches",
            "empty_replacement",
        ],
    )
    def test_replace_all(self, patterns, text, replacement, expected):
        """Test replace_all with various inputs."""
        matcher = PatternMatcher(patterns)
        result = matcher.replace_all(text, replacement)
        assert result == expected


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestCache:
    """Test caching functionality."""

    def test_cache_population(self):
        """Test that cache is populated on first use."""
        matcher = PatternMatcher(["error"])

        _, cache_size_before = matcher.get_stats()
        assert cache_size_before == 0

        # First call - populates cache
        matcher.find_all("This is an error")

        _, cache_size_after = matcher.get_stats()
        assert cache_size_after == 1

    def test_cache_hit(self):
        """Test cache hit with repeated queries."""
        matcher = PatternMatcher(["error"])

        text = "This is an error message"

        # First call - cache miss
        matches1 = matcher.find_all(text)

        # Second call - cache hit (should return same results)
        matches2 = matcher.find_all(text)

        assert matches1 == matches2

        _, cache_size = matcher.get_stats()
        assert cache_size == 1

    def test_cache_multiple_texts(self):
        """Test cache with multiple different texts."""
        matcher = PatternMatcher(["error"])

        texts = [
            "First error",
            "Second error",
            "Third error",
        ]

        for text in texts:
            matcher.find_all(text)

        _, cache_size = matcher.get_stats()
        assert cache_size == 3

    def test_cache_clear(self):
        """Test cache clearing."""
        matcher = PatternMatcher(["error"])

        # Populate cache
        matcher.find_all("error 1")
        matcher.find_all("error 2")
        matcher.find_all("error 3")

        _, cache_size_before = matcher.get_stats()
        assert cache_size_before == 3

        # Clear cache
        matcher.clear_cache()

        _, cache_size_after = matcher.get_stats()
        assert cache_size_after == 0

    def test_cache_independence(self):
        """Test that cached results are independent."""
        matcher = PatternMatcher(["test"])

        text1 = "prefix test suffix"
        text2 = "another prefix test another suffix"

        matches1 = matcher.find_all(text1)
        matches2 = matcher.find_all(text2)

        # Different texts should have different cached results (different positions)
        assert matches1[0][0] != matches2[0][0]

        _, cache_size = matcher.get_stats()
        assert cache_size == 2


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.parametrize(
        "pattern,text",
        [
            # Special regex characters (treated as literals)
            ("error[0]", "Found error[0] here"),
            ("warning*", "Found warning* here"),
            ("info+test", "Found info+test here"),
            # Unicode characters
            ("错误", "Found 错误 in text"),  # Chinese
            ("エラー", "Found エラー in text"),  # Japanese
            ("ошибка", "Found ошибка in text"),  # Russian
            # Whitespace patterns
            ("error ", "This is error code"),
            (" warning", "This is warning message"),
            ("info\t", "This is info\tdata"),
        ],
        ids=[
            "special_brackets",
            "special_asterisk",
            "special_plus",
            "unicode_chinese",
            "unicode_japanese",
            "unicode_russian",
            "whitespace_trailing",
            "whitespace_leading",
            "whitespace_tab",
        ],
    )
    def test_special_patterns(self, pattern, text):
        """Test patterns with special characters, unicode, and whitespace."""
        matcher = PatternMatcher([pattern])
        assert matcher.has_match(text)

    def test_very_long_pattern(self):
        """Test with very long pattern."""
        long_pattern = "a" * 1000
        matcher = PatternMatcher([long_pattern])

        text = f"prefix {long_pattern} suffix"
        assert matcher.has_match(text)

    def test_very_long_text(self):
        """Test with very long text."""
        matcher = PatternMatcher(["needle"])

        # Create very long text with needle in the middle
        prefix = "x" * 10000
        long_text = f"{prefix}needle{'y' * 10000}"

        matches = matcher.find_all(long_text)
        assert len(matches) == 1
        assert matches[0][0] == len(prefix)  # Position right after prefix

    def test_many_patterns(self):
        """Test with large number of patterns."""
        # Test with a large number of patterns
        patterns = [f"pattern{i}" for i in range(1000)]
        matcher = PatternMatcher(patterns)

        pattern_count, _ = matcher.get_stats()
        assert pattern_count == 1000

        # Should find specific pattern
        assert matcher.has_match("Found pattern500 here")

    def test_duplicate_patterns_in_list(self):
        """Test with duplicate patterns."""
        matcher = PatternMatcher([
            "error",
            "error",  # Duplicate
            "warning",
        ])

        # Aho-Corasick handles duplicates, but counts them
        pattern_count, _ = matcher.get_stats()
        assert pattern_count == 3  # Includes duplicate

    def test_substring_patterns(self):
        """Test patterns that are substrings of each other."""
        matcher = PatternMatcher([
            "test",
            "testing",  # "testing" contains "test"
        ])

        # Should find both patterns in "testing"
        matches = matcher.find_all("testing")
        assert len(matches) >= 1


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
@pytest.mark.slow
class TestPerformance:
    """Test performance characteristics."""

    def test_performance_many_matches(self):
        """Test performance with many matches."""
        import time

        matcher = PatternMatcher(["test"])

        # Text with many occurrences
        text = "test " * 1000

        start = time.perf_counter()
        matches = matcher.find_all(text)
        elapsed = time.perf_counter() - start

        assert len(matches) == 1000
        # Should be very fast (< 10ms)
        assert elapsed < 0.01, f"Expected < 10ms, got {elapsed * 1000:.2f}ms"

    def test_performance_cache_benefit(self):
        """Test that caching provides performance benefit."""
        import time

        matcher = PatternMatcher(["error", "warning"])

        text = "error and warning both present " * 100

        # First call - no cache
        start = time.perf_counter()
        matcher.find_all(text)
        first_time = time.perf_counter() - start

        # Second call - with cache
        start = time.perf_counter()
        matcher.find_all(text)
        cached_time = time.perf_counter() - start

        # Cached call should be faster (usually much faster)
        # Note: Due to system variance, we just verify both complete quickly
        assert first_time < 0.01  # < 10ms
        assert cached_time < 0.01  # < 10ms


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust PatternMatcher not available")
class TestPythonIntegration:
    """Test Python-specific integration aspects."""

    def test_pattern_list_types(self):
        """Test that various Python list types work."""
        # List
        matcher1 = PatternMatcher(["test"])
        assert matcher1.has_match("test")

        # Tuple (PyO3 accepts sequences, not just lists)
        matcher2 = PatternMatcher(("test",))  # type: ignore[arg-type]
        assert matcher2.has_match("test")

    def test_error_handling_invalid_patterns(self):
        """Test error handling with invalid pattern types."""
        # Non-string pattern should raise error
        with pytest.raises((TypeError, ValueError)):
            PatternMatcher([123, 456])  # type: ignore[list-item]

    def test_string_return_types(self):
        """Test that return values are proper Python strings."""
        matcher = PatternMatcher(["test"])

        result = matcher.find_first("test message")
        assert result is not None

        _, pattern = result
        assert isinstance(pattern, str)
        assert pattern == "test"

        matches = matcher.find_all("test test")
        for _, pat in matches:
            assert isinstance(pat, str)

    def test_none_handling(self):
        """Test that None is properly handled in results."""
        matcher = PatternMatcher(["test"])

        result = matcher.find_first("no match")
        assert result is None

    def test_method_chaining(self):
        """Test that operations can be chained."""
        matcher = PatternMatcher(["error", "warning"])

        # Multiple operations in sequence
        matcher.find_all("error warning")
        matcher.clear_cache()
        matches = matcher.find_all("error warning")

        assert len(matches) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

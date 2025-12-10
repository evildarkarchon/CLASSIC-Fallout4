"""
Integration tests for Rust utilities exposed through PyO3.

These tests verify that the Rust extensions work correctly when called from Python,
ensuring proper type conversions, error handling, and performance characteristics.
"""

import time

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

import classic_scanlog

# Skip if classic_shared module not available
try:
    import classic_shared
except ImportError:
    pytest.skip("classic_shared not available", allow_module_level=True)

# Import directly from classic_shared and classic_scanlog
import classic_scanlog
import classic_shared

# Access utility classes from their respective modules
PathHandler = classic_shared.PathHandler
RustPerformanceMonitor = classic_shared.RustPerformanceMonitor
StringProcessor = classic_shared.StringProcessor

# LogProcessor is available in classic_scanlog
LogProcessor = classic_scanlog.LogParser


@pytest.mark.rust
@pytest.mark.integration
class TestRustPathHandler:
    """Test the Rust PathHandler utility from Python."""

    @pytest.fixture
    def path_handler(self):
        """Create a PathHandler instance."""
        return PathHandler()  # No ttl_seconds parameter

    def test_path_normalization(self, path_handler):
        """Test path normalization across platforms."""
        # Test relative path normalization
        result = path_handler.normalize_path("./test/../file.txt")
        assert "file.txt" in result
        assert ".." not in result

        # Test absolute path
        result = path_handler.normalize_path("/absolute/path/to/file")
        # On Windows, normalized paths might start with backslash
        assert result.startswith("/") or result.startswith("\\") or (len(result) > 1 and result[1] == ":")

    def test_path_cache_functionality(self, path_handler):
        """Test that path caching works correctly."""
        test_path = "./test/path/to/cache"

        # First call should add to cache
        path_handler.normalize_path(test_path)
        stats = path_handler.cache_stats()
        # cache_stats might return a single value or tuple
        cache_size = stats if isinstance(stats, int) else stats[0]
        assert cache_size >= 1

        # Clear cache
        path_handler.clear_cache()
        stats = path_handler.cache_stats()
        cache_size = stats if isinstance(stats, int) else stats[0]
        assert cache_size == 0

    @pytest.mark.skip(reason="validate_paths_batch not exposed in current Rust API")
    def test_batch_path_validation(self, path_handler, tmp_path):
        """Test batch validation of paths."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        paths = [
            str(tmp_path),  # Existing directory
            str(test_file),  # Existing file
            "/nonexistent/path/that/should/not/exist",  # Non-existent
        ]

        results = path_handler.validate_paths_batch(paths)
        assert len(results) == 3
        assert results[0][1] is True  # Directory exists
        assert results[1][1] is True  # File exists
        assert results[2][1] is False  # Path doesn't exist

    @pytest.mark.skip(reason="Path operation methods not exposed in current Rust API")
    def test_path_operations(self, path_handler):
        """Test various path operations."""
        # Test join
        joined = path_handler.join_paths("/base", ["sub", "file.txt"])
        assert "sub" in joined
        assert "file.txt" in joined

        # Test split
        components = path_handler.split_path("/base/sub/file.txt")
        assert len(components) >= 3

        # Test filename extraction
        filename = path_handler.get_filename("/path/to/file.txt")
        assert filename == "file.txt"

        # Test extension extraction
        ext = path_handler.get_extension("/path/to/file.txt")
        assert ext == "txt"

        # Test parent extraction
        parent = path_handler.get_parent("/path/to/file.txt")
        assert parent is not None
        assert "to" in parent

    @pytest.mark.skip(reason="common_prefix not exposed in current Rust API")
    def test_common_prefix(self, path_handler):
        """Test finding common prefix of paths."""
        paths = [
            "/home/user/documents/file1.txt",
            "/home/user/documents/file2.txt",
            "/home/user/downloads/file3.txt",
        ]

        prefix = path_handler.common_prefix(paths)
        assert prefix is not None
        assert "home" in prefix
        assert "user" in prefix


@pytest.mark.rust
@pytest.mark.integration
class TestRustStringProcessor:
    """Test the Rust StringProcessor utility from Python."""

    @pytest.fixture
    def processor(self):
        """Create a StringProcessor instance."""
        return StringProcessor()

    def test_string_interning(self, processor):
        """Test string interning for memory efficiency.

        Note: The Rust ThreadedRodeo string interner doesn't support clearing.
        The clear_pool() method will log a warning and not actually clear the pool.
        To reset the pool, create a new StringProcessor instance.
        """
        # Intern the same string multiple times
        processor.intern("test_string")
        processor.intern("test_string")
        processor.intern("test_string")

        # Should only have one entry in the pool
        assert processor.pool_stats() == 1

        # Intern different strings
        processor.intern("another_string")
        processor.intern("third_string")
        assert processor.pool_stats() == 3

        # Attempt to clear pool (ThreadedRodeo doesn't support clearing)
        processor.clear_pool()
        # Pool should still contain the same strings (clearing not supported)
        assert processor.pool_stats() == 3

        # To reset pool, need to create a new instance
        new_processor = StringProcessor()
        assert new_processor.pool_stats() == 0

    def test_batch_processing(self, processor):
        """Test batch string operations."""
        strings = ["Hello", "World", "Python", "Rust"]

        # Test uppercase
        upper = processor.process_batch(strings, "upper")
        assert upper == ["HELLO", "WORLD", "PYTHON", "RUST"]

        # Test lowercase
        lower = processor.process_batch(strings, "lower")
        assert lower == ["hello", "world", "python", "rust"]

        # Test trim (with whitespace strings)
        strings_with_spaces = ["  hello  ", "world  ", "  python", "rust"]
        trimmed = processor.process_batch(strings_with_spaces, "trim")
        assert trimmed == ["hello", "world", "python", "rust"]

    def test_line_operations(self, processor):
        r"""Test line splitting and joining.

        Note: Standard line splitting only recognizes \n and \r\n as line endings,
        not lone \r (which is only used by old Mac OS Classic).
        """
        # Test split lines with standard line endings
        text = "Line 1\nLine 2\r\nLine 3\nLine 4"
        lines = processor.split_lines(text)
        assert len(lines) == 4
        assert lines == ["Line 1", "Line 2", "Line 3", "Line 4"]

        # Test join lines
        joined = processor.join_lines(lines, " | ")
        assert " | " in joined
        assert "Line 1" in joined
        assert "Line 4" in joined
        assert joined == "Line 1 | Line 2 | Line 3 | Line 4"

    def test_common_prefix_strings(self, processor):
        """Test finding common prefix in strings."""
        strings = [
            "prefix_file1.txt",
            "prefix_file2.txt",
            "prefix_file3.txt",
        ]

        prefix = processor.common_prefix(strings)
        assert prefix == "prefix_file"


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.skipif(LogProcessor is None, reason="LogProcessor not yet implemented in Rust")
class TestRustLogProcessor:
    """Test the Rust LogProcessor utility from Python."""

    @pytest.fixture
    def processor(self):
        """Create a LogProcessor instance."""
        return LogProcessor()  # pyright: ignore[reportOptionalCall]

    def test_formid_extraction(self, processor):
        """Test extraction of FormIDs from text."""
        lines = [
            "Found FormIDs in crash log:",
            "- FormID: 0x12345678",
            "- FormID: 0xABCDEF01",
            "- Decimal FormID: 87654321",
            "- Invalid: 0xGGGGGGGG",
        ]

        formids = processor.extract_formids(lines)
        assert len(formids) >= 2
        assert any("12345678" in f for f in formids)
        assert any("ABCDEF01" in f for f in formids)

    def test_plugin_extraction(self, processor):
        """Test extraction of plugin names."""
        lines = [
            "Loading plugins:",
            "[001] Fallout4.esm",
            "[002] DLCRobot.esm",
            "[003] DLCworkshop01.esm",
            "[004] Unofficial Fallout 4 Patch.esp",
            "[005] SomeMode.esp",
            "[006] PatchFile.esl",
        ]

        plugins = processor.extract_plugins(lines)
        assert len(plugins) >= 5
        # extract_plugins returns tuples of (name, index)
        plugin_names = [p[0] for p in plugins]
        assert any("Fallout4.esm" in p for p in plugin_names)
        assert any("PatchFile.esl" in p for p in plugin_names)

    def test_segment_parsing(self, processor):
        """Test parsing log into segments."""
        # Use custom boundaries for this test
        custom_boundaries = [
            ("=== HEADER ===", "=== MODULES ==="),
            ("=== MODULES ===", "=== STACK TRACE ==="),
            ("=== STACK TRACE ===", "EOF"),
        ]
        # Create a new parser with custom boundaries
        custom_parser = LogProcessor(custom_boundaries)

        lines = [
            "=== HEADER ===",
            "Version: 1.0",
            "Date: 2025-01-22",
            "",
            "=== MODULES ===",
            "Module1.dll",
            "Module2.dll",
            "",
            "=== STACK TRACE ===",
            "Frame 1: function_a()",
            "Frame 2: function_b()",
        ]

        segments = custom_parser.parse_segments(lines)
        assert len(segments) >= 2

    def test_pattern_matching_with_pattern_matcher(self):
        """Test pattern matching using PatternMatcher class."""
        patterns = ["ERROR", "WARNING", "INFO"]
        matcher = classic_scanlog.PatternMatcher(patterns)

        text = "ERROR: System failure. WARNING: Low memory. INFO: Started."

        # Test has_match
        assert matcher.has_match(text) is True

        # Test find_all
        results = matcher.find_all(text)
        assert len(results) >= 3

        # Test find_first
        first = matcher.find_first(text)
        assert first is not None
        assert first[1] == "ERROR"

    def test_line_filtering_with_pattern_matcher(self):
        """Test filtering lines by patterns using PatternMatcher."""
        lines = [
            "ERROR: Critical failure",
            "INFO: System started",
            "WARNING: Low resources",
            "ERROR: Another error",
            "DEBUG: Verbose output",
        ]

        # Include only ERROR lines using PatternMatcher
        error_matcher = classic_scanlog.PatternMatcher(["ERROR"])
        filtered = [line for line in lines if error_matcher.has_match(line)]
        assert len(filtered) == 2
        assert all("ERROR" in line for line in filtered)

        # Exclude ERROR lines
        filtered = [line for line in lines if not error_matcher.has_match(line)]
        assert len(filtered) == 3
        assert all("ERROR" not in line for line in filtered)

        # Include WARNING and INFO, exclude DEBUG
        include_matcher = classic_scanlog.PatternMatcher(["WARNING", "INFO"])
        exclude_matcher = classic_scanlog.PatternMatcher(["DEBUG"])
        filtered = [line for line in lines if include_matcher.has_match(line) and not exclude_matcher.has_match(line)]
        assert len(filtered) == 2


@pytest.mark.rust
@pytest.mark.integration
class TestRustPerformanceMonitor:
    """Test the Rust PerformanceMonitor from Python."""

    @pytest.fixture
    def monitor(self):
        """Create a PerformanceMonitor instance."""
        monitor = RustPerformanceMonitor()
        monitor.clear_metrics()
        return monitor

    def test_metric_recording(self, monitor):
        """Test recording performance metrics.

        API: record_metric(operation, duration_ms, bytes_processed=None)
        - operation: str - Name of the operation
        - duration_ms: int - Duration in milliseconds
        - bytes_processed: Optional[int] - Number of bytes processed
        """
        # Record some metrics
        monitor.record_metric("operation1", duration_ms=50, bytes_processed=1024)
        monitor.record_metric("operation1", duration_ms=60, bytes_processed=2048)
        monitor.record_metric("operation2", duration_ms=100, bytes_processed=None)

        # Metrics should be recorded (implementation specific)
        # Since we can't directly query metrics in the current API,
        # we just verify no errors occur

    def test_clear_metrics(self, monitor):
        """Test clearing metrics.

        API: clear_metrics() - Clears all recorded performance metrics
        """
        # Record a metric
        monitor.record_metric("test_op", duration_ms=100, bytes_processed=512)

        # Clear metrics
        monitor.clear_metrics()

        # Should be able to record new metrics after clearing
        monitor.record_metric("new_op", duration_ms=50, bytes_processed=256)


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.performance
class TestRustPerformance:
    """Test performance characteristics of Rust utilities."""

    def test_string_processing_performance(self):
        """Compare Rust string processing performance."""
        processor = StringProcessor()

        # Generate test data
        lines = [f"Line {i} with some text content" for i in range(10000)]

        # Measure batch processing time
        start = time.perf_counter()
        result = processor.process_batch(lines, "upper")
        duration = time.perf_counter() - start

        assert len(result) == 10000
        # Should be very fast (< 100ms for 10k strings)
        assert duration < 0.1, f"Processing took {duration:.3f}s, expected < 0.1s"

    def test_parallel_log_filtering_performance(self):
        """Test parallel filtering performance using PatternMatcher."""
        # Generate test data
        lines = [f"ERROR: Message {i}" if i % 10 == 0 else f"INFO: Message {i}" for i in range(10000)]

        error_matcher = classic_scanlog.PatternMatcher(["ERROR"])

        # Measure filtering time
        start = time.perf_counter()
        filtered = [line for line in lines if error_matcher.has_match(line)]
        duration = time.perf_counter() - start

        assert len(filtered) == 1000  # 10% are ERROR lines
        # Should be reasonably fast
        assert duration < 0.5, f"Filtering took {duration:.3f}s, expected < 0.5s"

    def test_formid_extraction_performance(self):
        """Test FormID extraction performance."""
        processor = LogProcessor()

        # Generate text with many FormIDs
        formid_lines = []
        for i in range(1000):
            formid_lines.append(f"FormID: 0x{i:08X} found in plugin")

        # Measure extraction time
        start = time.perf_counter()
        formids = processor.extract_formids(formid_lines)
        duration = time.perf_counter() - start

        assert len(formids) >= 1000
        # Should be fast even with many FormIDs
        assert duration < 0.1, f"Extraction took {duration:.3f}s, expected < 0.1s"


def is_savefile_formid(formid: int) -> bool:
    """Check if a FormID is from a save file (FF prefix).

    Save file FormIDs in Bethesda games have their highest byte set to 0xFF.

    Args:
        formid: The FormID as an integer

    Returns:
        True if the FormID has an FF prefix (save file item)
    """
    # Check if high byte is 0xFF (save file FormID)
    return (formid >> 24) == 0xFF


@pytest.mark.rust
@pytest.mark.integration
class TestRustCoreClasses:
    """Test the core Rust classes exposed to Python."""

    def test_formid_processor(self):
        """Test the FormIDAnalyzer class.

        FormID Rules for Fallout 4:
        - Valid FormIDs are exactly 8 hex digits (0x00000000 - 0xFFFFFFFF)
        - FormIDs with FF prefix (0xFF000000 - 0xFFFFFFFF) are save file items
        - Anything longer than 8 hex digits is invalid
        - Hex or ignored philosophy: valid hex strings parsed, invalid strings return None
        """
        analyzer = classic_scanlog.FormIDAnalyzer()

        # Test batch processing with validation using parse_formid
        formids = [
            "0x12345678",  # Valid 8 hex digits with prefix
            "0xABCDEF01",  # Valid 8 hex digits with prefix
            "87654321",  # Valid 8 hex digits without prefix
            "0xFF001234",  # Valid save file FormID (FF prefix)
            "FF999999",  # Valid save file FormID without 0x
            "123456789",  # Invalid: 9 hex digits (too long)
            "0x123456789",  # Invalid: 9 hex digits with prefix (too long)
            "FFFFFFFFF",  # Invalid: 9 hex digits (too long)
            "invalid",  # Invalid: non-hex chars
            "GHIJK",  # Invalid: non-hex chars
            "0xZZZZ",  # Invalid: non-hex chars
            "",  # Invalid: empty string
        ]
        results = [analyzer.parse_formid(f) for f in formids]

        assert len(results) == 12

        # Valid FormIDs (8 hex digits or less)
        assert results[0] == 0x12345678, "0x12345678 should parse as hex"
        assert results[1] == 0xABCDEF01, "0xABCDEF01 should parse as hex"
        assert results[2] == 0x87654321, "87654321 should parse as hex"

        # Save file FormIDs (FF prefix)
        assert results[3] == 0xFF001234, "0xFF001234 should parse (save file FormID)"
        assert results[4] == 0xFF999999, "FF999999 should parse (save file FormID)"

        # Invalid: too long (> 8 hex digits)
        assert results[5] is None, "123456789 (9 digits) should be rejected"
        assert results[6] is None, "0x123456789 (9 digits) should be rejected"
        assert results[7] is None, "FFFFFFFFF (9 digits) should be rejected"

        # Invalid: non-hex characters
        assert results[8] is None, "invalid should be ignored (non-hex chars)"
        assert results[9] is None, "GHIJK should be ignored (non-hex chars)"
        assert results[10] is None, "0xZZZZ should be ignored (non-hex chars)"
        assert results[11] is None, "empty string should be ignored"

    def test_formid_save_file_detection(self):
        """Test detection of save file FormIDs (FF prefix).

        Note: The Rust FormIDAnalyzer doesn't expose is_savefile_formid directly,
        so we use a Python helper function that checks if the high byte is 0xFF.
        """
        # Save file FormIDs (FF prefix - highest byte is 0xFF)
        assert is_savefile_formid(0xFF000000) is True, "0xFF000000 is save file"
        assert is_savefile_formid(0xFF001234) is True, "0xFF001234 is save file"
        assert is_savefile_formid(0xFFFFFFFF) is True, "0xFFFFFFFF is save file"
        assert is_savefile_formid(0xFF999999) is True, "0xFF999999 is save file"

        # Regular FormIDs (not FF prefix)
        assert is_savefile_formid(0x00000000) is False, "0x00000000 is not save file"
        assert is_savefile_formid(0x12345678) is False, "0x12345678 is not save file"
        assert is_savefile_formid(0xFE999999) is False, "0xFE999999 is not save file (FE, not FF)"
        assert is_savefile_formid(0x00FF1234) is False, "0x00FF1234 is not save file (FF not in highest byte)"

    def test_formid_batch_with_metadata(self):
        """Test batch processing with save file metadata."""
        analyzer = classic_scanlog.FormIDAnalyzer()

        formids = [
            "0xFF001234",  # Save file FormID
            "0x12345678",  # Regular FormID
            "FF999999",  # Save file FormID without 0x
            "87654321",  # Regular FormID without 0x
            "123456789",  # Invalid: too long
            "invalid",  # Invalid: non-hex
        ]

        # Process batch using parse_formid and the helper is_savefile_formid
        results = []
        for f in formids:
            parsed = analyzer.parse_formid(f)
            is_save = is_savefile_formid(parsed) if parsed is not None else False
            results.append((parsed, is_save))

        assert len(results) == 6

        # Check parsed values and save file flags
        parsed, is_save = results[0]
        assert parsed == 0xFF001234, "0xFF001234 should parse"
        assert is_save is True, "0xFF001234 should be flagged as save file"

        parsed, is_save = results[1]
        assert parsed == 0x12345678, "0x12345678 should parse"
        assert is_save is False, "0x12345678 should NOT be flagged as save file"

        parsed, is_save = results[2]
        assert parsed == 0xFF999999, "FF999999 should parse"
        assert is_save is True, "FF999999 should be flagged as save file"

        parsed, is_save = results[3]
        assert parsed == 0x87654321, "87654321 should parse"
        assert is_save is False, "87654321 should NOT be flagged as save file"

        parsed, is_save = results[4]
        assert parsed is None, "123456789 should be rejected (too long)"
        assert is_save is False, "Invalid FormID should not be flagged as save file"

        parsed, is_save = results[5]
        assert parsed is None, "invalid should be rejected (non-hex)"
        assert is_save is False, "Invalid FormID should not be flagged as save file"

    def test_pattern_counter_with_pattern_matcher(self, tmp_path):
        """Test pattern counting using PatternMatcher.

        Note: classic_scanlog.count_patterns_in_file doesn't exist,
        so we use PatternMatcher.find_all() to count pattern occurrences.
        """
        # Create a test file
        test_file = tmp_path / "test.log"
        test_file.write_text("ERROR ERROR WARNING INFO ERROR")
        content = test_file.read_text()

        # Count ERROR patterns using PatternMatcher
        error_matcher = classic_scanlog.PatternMatcher(["ERROR"])
        error_matches = error_matcher.find_all(content)
        assert len(error_matches) == 3

        # Count WARNING patterns
        warning_matcher = classic_scanlog.PatternMatcher(["WARNING"])
        warning_matches = warning_matcher.find_all(content)
        assert len(warning_matches) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

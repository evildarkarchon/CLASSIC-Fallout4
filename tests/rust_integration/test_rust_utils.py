"""
Integration tests for Rust utilities exposed through PyO3.

These tests verify that the Rust extensions work correctly when called from Python,
ensuring proper type conversions, error handling, and performance characteristics.
"""

import time

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_core", reason="Rust extensions not available")

import classic_core

# Skip if utils module not yet implemented
if not hasattr(classic_core, 'utils'):
    pytest.skip("classic_core.utils not yet implemented", allow_module_level=True)

# Access utils as an attribute, not a submodule
LogProcessor = classic_core.utils.LogProcessor
PathHandler = classic_core.utils.PathHandler
RustPerformanceMonitor = classic_core.utils.RustPerformanceMonitor
StringProcessor = classic_core.utils.StringProcessor


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
        """Test string interning for memory efficiency."""
        # Intern the same string multiple times
        s1 = processor.intern("test_string")
        s2 = processor.intern("test_string")
        s3 = processor.intern("test_string")

        # Should only have one entry in the pool
        assert processor.pool_stats() == 1

        # Intern different strings
        processor.intern("another_string")
        processor.intern("third_string")
        assert processor.pool_stats() == 3

        # Clear pool
        processor.clear_pool()
        assert processor.pool_stats() == 0

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
        """Test line splitting and joining."""
        # Test split lines
        text = "Line 1\\nLine 2\\r\\nLine 3\\rLine 4"
        lines = processor.split_lines(text)
        assert len(lines) == 4

        # Test join lines
        joined = processor.join_lines(lines, " | ")
        assert " | " in joined
        assert "Line 1" in joined
        assert "Line 4" in joined

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
class TestRustLogProcessor:
    """Test the Rust LogProcessor utility from Python."""

    @pytest.fixture
    def processor(self):
        """Create a LogProcessor instance."""
        return LogProcessor()

    def test_pattern_matching(self, processor):
        """Test pattern matching in log text."""
        patterns = ["ERROR", "WARNING", "INFO", "FormID"]

        # Initialize pattern matcher
        processor.init_pattern_matcher(patterns)

        text = "ERROR: System failure. WARNING: Low memory. INFO: Started. FormID: 0x12345678"
        results = processor.find_all_patterns(text, patterns)

        assert len(results) == 4
        # Each pattern should have matches
        for pattern, matches in results:
            if pattern in text:
                assert len(matches) > 0

    def test_formid_extraction(self, processor):
        """Test extraction of FormIDs from text."""
        text = """
        Found FormIDs in crash log:
        - FormID: 0x12345678
        - FormID: 0xABCDEF01
        - Decimal FormID: 87654321
        - Invalid: 0xGGGGGGGG
        """

        formids = processor.extract_formids(text)
        assert len(formids) >= 2
        assert any("12345678" in f for f in formids)
        assert any("ABCDEF01" in f for f in formids)

    def test_plugin_extraction(self, processor):
        """Test extraction of plugin names."""
        text = """
        Loading plugins:
        [001] Fallout4.esm
        [002] DLCRobot.esm
        [003] DLCworkshop01.esm
        [004] Unofficial Fallout 4 Patch.esp
        [005] SomeMode.esp
        [006] PatchFile.esl
        """

        plugins = processor.extract_plugins(text)
        assert len(plugins) >= 5
        assert any("Fallout4.esm" in p for p in plugins)
        assert any("PatchFile.esl" in p for p in plugins)

    def test_line_filtering(self, processor):
        """Test filtering lines by patterns."""
        lines = [
            "ERROR: Critical failure",
            "INFO: System started",
            "WARNING: Low resources",
            "ERROR: Another error",
            "DEBUG: Verbose output",
        ]

        # Include only ERROR lines
        filtered = processor.filter_lines(lines, include=["ERROR"], exclude=None)
        assert len(filtered) == 2
        assert all("ERROR" in line for line in filtered)

        # Exclude ERROR lines
        filtered = processor.filter_lines(lines, include=None, exclude=["ERROR"])
        assert len(filtered) == 3
        assert all("ERROR" not in line for line in filtered)

        # Include WARNING and INFO, exclude DEBUG
        filtered = processor.filter_lines(
            lines,
            include=["WARNING", "INFO"],
            exclude=["DEBUG"]
        )
        assert len(filtered) == 2

    def test_segment_parsing(self, processor):
        """Test parsing log into segments."""
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

        segments = processor.parse_segments(lines)
        assert len(segments) >= 2
        assert any("MODULES" in name for name, _ in segments)
        assert any("STACK" in name for name, _ in segments)

    def test_parallel_processing(self, processor):
        """Test parallel line processing."""
        lines = [f"Line {i}" for i in range(100)]

        # Process to uppercase
        upper = processor.process_lines_parallel(lines, "upper")
        assert all(line.isupper() for line in upper)

        # Process to lowercase
        lower = processor.process_lines_parallel(lines, "lower")
        assert all(line.islower() for line in lower)

    def test_fast_find(self, processor):
        """Test fast string finding with case sensitivity."""
        text = "This is a TEST string with Test and test words"

        # Case sensitive search
        positions = processor.fast_find(text, "test", case_insensitive=False)
        assert len(positions) == 1  # Only lowercase "test"

        # Case insensitive search
        positions = processor.fast_find(text, "test", case_insensitive=True)
        assert len(positions) == 3  # TEST, Test, test


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
        """Test recording performance metrics."""
        # Record some metrics
        monitor.record_metric("operation1", duration_ms=50, memory_bytes=1024)
        monitor.record_metric("operation1", duration_ms=60, memory_bytes=2048)
        monitor.record_metric("operation2", duration_ms=100, memory_bytes=None)

        # Metrics should be recorded (implementation specific)
        # Since we can't directly query metrics in the current API,
        # we just verify no errors occur

    def test_clear_metrics(self, monitor):
        """Test clearing metrics."""
        # Record a metric
        monitor.record_metric("test_op", duration_ms=100, memory_bytes=512)

        # Clear metrics
        monitor.clear_metrics()

        # Should be able to record new metrics after clearing
        monitor.record_metric("new_op", duration_ms=50, memory_bytes=256)


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

    def test_parallel_log_processing_performance(self):
        """Test parallel processing performance."""
        processor = LogProcessor()

        # Generate test data
        lines = [f"ERROR: Message {i}" if i % 10 == 0 else f"INFO: Message {i}"
                 for i in range(10000)]

        # Measure filtering time
        start = time.perf_counter()
        filtered = processor.filter_lines(lines, include=["ERROR"], exclude=None)
        duration = time.perf_counter() - start

        assert len(filtered) == 1000  # 10% are ERROR lines
        # Should be very fast
        assert duration < 0.05, f"Filtering took {duration:.3f}s, expected < 0.05s"

    def test_formid_extraction_performance(self):
        """Test FormID extraction performance."""
        processor = LogProcessor()

        # Generate text with many FormIDs
        formid_lines = []
        for i in range(1000):
            formid_lines.append(f"FormID: 0x{i:08X} found in plugin")
        text = "\\n".join(formid_lines)

        # Measure extraction time
        start = time.perf_counter()
        formids = processor.extract_formids(text)
        duration = time.perf_counter() - start

        assert len(formids) >= 1000
        # Should be fast even with many FormIDs
        assert duration < 0.1, f"Extraction took {duration:.3f}s, expected < 0.1s"


@pytest.mark.rust
@pytest.mark.integration
class TestRustCoreClasses:
    """Test the core Rust classes exposed to Python."""

    def test_file_reader(self, tmp_path):
        """Test the FileReader class."""
        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")

        reader = classic_core.FileReader()

        # Test single file read
        content = reader.read_file(str(file1))
        assert content == "Content 1"

        # Test batch read
        contents = reader.read_files_batch([str(file1), str(file2)])
        assert len(contents) == 2
        assert contents[0] == "Content 1"
        assert contents[1] == "Content 2"

    def test_formid_processor(self):
        """Test the FormIDProcessor class."""
        processor = classic_core.FormIDProcessor()

        # Test batch processing
        formids = ["0x12345678", "0xABCDEF01", "87654321", "invalid"]
        results = processor.process_batch(formids)

        assert len(results) == 4
        assert results[0] == 0x12345678
        assert results[1] == 0xABCDEF01
        assert results[2] is None  # Decimal string not handled
        assert results[3] is None  # Invalid FormID

    def test_pattern_counter(self, tmp_path):
        """Test the count_patterns_in_file function."""
        # Create a test file
        test_file = tmp_path / "test.log"
        test_file.write_text("ERROR ERROR WARNING INFO ERROR")

        # Count patterns
        count = classic_core.count_patterns_in_file(str(test_file), "ERROR")
        assert count == 3

        count = classic_core.count_patterns_in_file(str(test_file), "WARNING")
        assert count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

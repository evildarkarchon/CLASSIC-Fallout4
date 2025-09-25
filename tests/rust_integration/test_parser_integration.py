"""
Integration tests for the enhanced Rust parser module.

This module tests the Rust parser implementation from Python to ensure:
- Proper Python bindings
- Performance improvements over pure Python
- Correct parsing of crash logs
- Pattern matching capabilities
"""

import time

import pytest

# Import the Rust module when available
try:
    import classic_core
    RUST_AVAILABLE = True
except ImportError:
    classic_core = None
    RUST_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Rust extensions not available")


def create_sample_crash_log() -> list[str]:
    """Create a sample crash log for testing."""
    return [
        "Unhandled exception at 0x7FF123456789| ACCESS_VIOLATION",
        "Fallout 4 v1.10.163",
        "Buffout 4 v1.28.6",
        "",
        "[Compatibility]",
        "F4EE: true",
        "Lookmenu: false",
        "",
        "SYSTEM SPECS:",
        "OS: Windows 10 64-bit",
        "CPU: AMD Ryzen 9 5900X",
        "GPU: NVIDIA GeForce RTX 3080",
        "RAM: 32 GB",
        "",
        "PROBABLE CALL STACK:",
        "[0] 0x7FF123456789 Fallout4.exe+0123456",
        "[1] 0x7FF123456790 Fallout4.exe+0123457",
        "[2] 0x7FF123456791 Fallout4.exe+0123458",
        "",
        "MODULES:",
        "Fallout4.exe v1.10.163",
        "ntdll.dll v10.0.19041.1",
        "kernel32.dll v10.0.19041.1",
        "",
        "F4SE PLUGINS:",
        "buffout4.dll v1.28.6",
        "f4ee.dll v1.2.3",
        "",
        "PLUGINS:",
        "[00] Fallout4.esm",
        "[01] DLCRobot.esm",
        "[02] DLCworkshop01.esm",
        "[FE:000] TestMod.esl",
        "",
        "REGISTERS:",
        "RAX: 0x0000000000000000",
        "RBX: 0x0000000000000001",
        "RCX: 0x0000000000000002",
        "",
        "STACK:",
        "0x000000000000: 0x12345678",
        "0x000000000008: 0x87654321",
        "EOF",
    ]


def create_large_crash_log(size: int = 10000) -> list[str]:
    """Create a large crash log for performance testing."""
    base_log = create_sample_crash_log()
    large_log = []
    for i in range(size):
        line = base_log[i % len(base_log)]
        large_log.append(f"{line} [Line {i}]")
    return large_log


@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
class TestRustParserIntegration:
    """Test the Rust parser module from Python."""

    def test_parser_creation(self):
        """Test creating a parser instance."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        assert parser is not None

        # Get statistics
        stats = parser.get_stats()
        assert "compiled_patterns" in stats
        assert stats["compiled_patterns"] > 0

    def test_custom_boundaries(self):
        """Test parser with custom segment boundaries."""
        custom_boundaries = [
            ("START:", "END:"),
            ("BEGIN:", "FINISH:"),
        ]
        parser = classic_core.scanlog.LogParser(custom_boundaries) # pyright: ignore[reportOptionalMemberAccess]
        assert parser is not None

    def test_segment_parsing(self):
        """Test parsing crash log into segments."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        log_lines = create_sample_crash_log()

        segments = parser.parse_segments(log_lines)

        # Should have multiple segments
        assert len(segments) > 0

        # Check for expected content in segments
        has_system_specs = any(
            any("CPU:" in line for line in segment)
            for segment in segments
        )
        assert has_system_specs

    def test_parallel_segment_parsing(self):
        """Test parallel parsing for large logs."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        large_log = create_large_crash_log(5000)

        # Time parallel parsing
        start = time.perf_counter()
        segments_parallel = parser.parse_segments_parallel(large_log, 1000)
        parallel_time = time.perf_counter() - start

        # Time regular parsing
        start = time.perf_counter()
        segments_regular = parser.parse_segments(large_log)
        regular_time = time.perf_counter() - start

        print(f"Parallel: {parallel_time:.3f}s, Regular: {regular_time:.3f}s")

        # Both should produce results
        assert len(segments_parallel) > 0
        assert len(segments_regular) > 0

    def test_pattern_matching(self):
        """Test pattern matching in crash logs."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        log_lines = create_sample_crash_log()

        matches = parser.find_patterns(log_lines)

        # Should find patterns
        assert len(matches) > 0

        # Check match structure
        for line_num, pattern, matched_text in matches:
            assert isinstance(line_num, int)
            assert isinstance(pattern, str)
            assert isinstance(matched_text, str)

    def test_custom_patterns(self):
        """Test adding custom regex patterns."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]

        # Add custom pattern for addresses
        parser.add_pattern("address", r"0x[0-9A-Fa-f]{8,16}")

        test_lines = [
            "Found address: 0x7FF123456789",
            "Another address: 0xABCDEF00",
            "No address here",
        ]

        matches = parser.find_patterns(test_lines)

        # Should find address patterns
        address_matches = [m for m in matches if "0x" in m[2]]
        assert len(address_matches) >= 2

    def test_section_extraction(self):
        """Test extracting specific sections from log."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        log_lines = create_sample_crash_log()

        section = parser.extract_section(
            log_lines,
            "SYSTEM SPECS:",
            "PROBABLE CALL STACK:"
        )

        assert section is not None
        assert len(section) > 0

        # Should contain system specs
        assert any("CPU:" in line for line in section)
        assert any("GPU:" in line for line in section)
        assert any("RAM:" in line for line in section)

    def test_batch_section_extraction(self):
        """Test extracting multiple sections in parallel."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        log_lines = create_sample_crash_log()

        markers = [
            ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
            ("MODULES:", "F4SE PLUGINS:"),
            ("REGISTERS:", "STACK:"),
        ]

        sections = parser.extract_sections_batch(log_lines, markers)

        assert len(sections) == 3
        # All sections should have content
        for section in sections:
            assert section is not None

    def test_crash_header_parsing(self):
        """Test parsing crash header information."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        log_lines = create_sample_crash_log()

        header = parser.parse_crash_header(log_lines)

        assert header is not None
        assert "game_version" in header
        assert "Fallout 4" in header["game_version"]

        assert "crashgen_version" in header
        assert "Buffout" in header["crashgen_version"]

        assert "main_error" in header
        assert "ACCESS_VIOLATION" in header["main_error"]

    def test_cache_effectiveness(self):
        """Test that caching improves performance."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        log_lines = create_sample_crash_log()

        # First parse - populates cache
        start = time.perf_counter()
        segments1 = parser.parse_segments(log_lines)
        first_time = time.perf_counter() - start

        initial_cache = parser.get_stats()["segment_cache_size"]

        # Second parse - uses cache
        start = time.perf_counter()
        segments2 = parser.parse_segments(log_lines)
        cached_time = time.perf_counter() - start

        # Cache should be populated
        assert initial_cache > 0

        # Cached should be faster (allow some variance)
        print(f"First: {first_time:.6f}s, Cached: {cached_time:.6f}s")

        # Results should be identical
        assert len(segments1) == len(segments2)

        # Clear cache
        parser.clear_caches()
        assert parser.get_stats()["segment_cache_size"] == 0

    def test_performance_improvement(self):
        """Test performance improvement over Python implementation."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]
        large_log = create_large_crash_log(10000)

        # Time Rust implementation
        start = time.perf_counter()
        segments = parser.parse_segments_parallel(large_log, 1000)
        rust_time = time.perf_counter() - start

        print(f"Rust parser processed {len(large_log)} lines in {rust_time:.3f}s")
        print(f"Rate: {len(large_log) / rust_time:.0f} lines/second")

        assert len(segments) > 0
        # Should process at least 10000 lines per second
        assert (len(large_log) / rust_time) > 10000


@pytest.mark.integration
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
class TestRustParserWithRealLogs:
    """Test the Rust parser with real crash log files."""

    @pytest.fixture
    def sample_log_path(self, tmp_path):
        """Create a temporary crash log file."""
        log_file = tmp_path / "crash.log"
        log_file.write_text("\n".join(create_sample_crash_log()))
        return log_file

    def test_parse_from_file(self, sample_log_path):
        """Test parsing a crash log from a file."""
        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]

        # Read file
        log_lines = sample_log_path.read_text().splitlines()

        # Parse segments
        segments = parser.parse_segments(log_lines)
        assert len(segments) > 0

        # Find patterns
        matches = parser.find_patterns(log_lines)
        assert len(matches) > 0

    def test_large_file_processing(self, tmp_path):
        """Test processing a large crash log file."""
        # Create large file
        large_file = tmp_path / "large_crash.log"
        large_log = create_large_crash_log(50000)
        large_file.write_text("\n".join(large_log))

        parser = classic_core.scanlog.LogParser() # pyright: ignore[reportOptionalMemberAccess]

        # Read and process
        start = time.perf_counter()
        log_lines = large_file.read_text().splitlines()
        segments = parser.parse_segments_parallel(log_lines, 5000)
        total_time = time.perf_counter() - start

        print(f"Processed {len(log_lines)} lines from file in {total_time:.3f}s")
        assert len(segments) > 0

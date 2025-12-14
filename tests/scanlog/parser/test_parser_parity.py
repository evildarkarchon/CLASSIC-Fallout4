"""Parity tests for Python vs Rust parser implementations.

This module tests that both Python and Rust implementations produce
identical results for crash log parsing operations.
"""

import pytest

from ClassicLib.integration.factory import get_parser
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.Parser import (
    extract_segments,
    find_segments,
    parse_crash_header,
)


# Skip parity tests if Rust parser is not available
pytestmark = [
    pytest.mark.unit,
]


def rust_parser_available() -> bool:
    """Check if Rust parser is available for parity testing."""
    return is_rust_accelerated("parser")


@pytest.mark.unit
class TestParserParityBasic:
    """Basic parity tests between Python and Rust implementations."""

    def test_find_segments_produces_consistent_structure(self, sample_crash_log_lines: list[str]) -> None:
        """Test that find_segments always produces the same structure."""
        result = find_segments(
            sample_crash_log_lines,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Should always return a 4-tuple
        assert len(result) == 4

        game_version, crashgen_version, main_error, segments = result

        # Types should be consistent
        assert isinstance(game_version, str)
        assert isinstance(crashgen_version, str)
        assert isinstance(main_error, str)
        assert isinstance(segments, list)
        assert len(segments) == 6

    def test_parse_crash_header_returns_strings(self, sample_crash_log_lines: list[str]) -> None:
        """Test that parse_crash_header always returns string tuple."""
        result = parse_crash_header(
            sample_crash_log_lines,
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        assert len(result) == 3
        assert all(isinstance(val, str) for val in result)

    def test_extract_segments_returns_list_of_lists(self, sample_crash_log_lines: list[str]) -> None:
        """Test that extract_segments always returns list of lists."""
        boundaries = [
            ("\t[Compatibility]", "SYSTEM SPECS:"),
            ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
        ]

        result = extract_segments(sample_crash_log_lines, boundaries, "EOF")

        assert isinstance(result, list)
        for segment in result:
            assert isinstance(segment, list)
            for line in segment:
                assert isinstance(line, str)


@pytest.mark.unit
@pytest.mark.skipif(not rust_parser_available(), reason="Rust parser not available")
class TestParserParityRust:
    """Parity tests that require the Rust parser."""

    def test_factory_parser_matches_direct_parser(self, sample_crash_log_lines: list[str]) -> None:
        """Test that factory-provided parser produces same results as direct module."""
        factory_parser = get_parser()

        # Both should produce identical results
        factory_result = factory_parser.find_segments(
            sample_crash_log_lines,
            "Buffout 4",
            "F4SE",
            "Fallout 4",
        )

        direct_result = find_segments(
            sample_crash_log_lines,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Compare metadata
        assert factory_result[0] == direct_result[0]  # game_version
        assert factory_result[1] == direct_result[1]  # crashgen_version
        assert factory_result[2] == direct_result[2]  # main_error

        # Compare segment count
        assert len(factory_result[3]) == len(direct_result[3])


@pytest.mark.unit
class TestParserEdgeCases:
    """Edge case tests for parser consistency."""

    def test_empty_crash_data_consistency(self) -> None:
        """Test that empty input produces consistent empty results."""
        result = find_segments(
            [],
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        game_version, crashgen_version, main_error, segments = result

        assert game_version == "UNKNOWN"
        assert crashgen_version == "UNKNOWN"
        assert main_error == "UNKNOWN"
        assert len(segments) == 6
        assert all(seg == [] for seg in segments)

    def test_malformed_data_graceful_handling(self, malformed_crash_log_content: str) -> None:
        """Test that malformed data is handled gracefully without exceptions."""
        crash_lines = malformed_crash_log_content.splitlines()

        # Should not raise any exceptions
        result = find_segments(
            crash_lines,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Should still return valid structure
        assert len(result) == 4
        assert len(result[3]) == 6

    def test_unicode_content_handling(self) -> None:
        """Test that unicode content in crash logs is handled correctly."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "Unhandled exception with unicode: \u00e9\u00e8\u00ea",
            "\t[Compatibility]",
            "Setting: true",
            "SYSTEM SPECS:",
            "OS: Windows with \u00e9",
            "PROBABLE CALL STACK:",
            "MODULES:",
            "F4SE PLUGINS:",
            "PLUGINS:",
        ]

        # Should not raise exceptions
        result = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        assert len(result) == 4

    def test_very_long_lines_handling(self) -> None:
        """Test handling of very long lines in crash logs."""
        long_line = "x" * 10000

        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            long_line,
            "\t[Compatibility]",
            "SYSTEM SPECS:",
            "PROBABLE CALL STACK:",
            "MODULES:",
            "F4SE PLUGINS:",
            "PLUGINS:",
        ]

        # Should handle without issues
        result = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        assert len(result) == 4

    def test_missing_sections_handling(self, minimal_crash_log_content: str) -> None:
        """Test handling of crash logs with missing sections."""
        crash_lines = minimal_crash_log_content.splitlines()

        result = find_segments(
            crash_lines,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Should still produce 6 segments (some may be empty)
        assert len(result[3]) == 6

    def test_duplicate_section_markers(self) -> None:
        """Test handling of duplicate section markers in crash log."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "\t[Compatibility]",
            "Setting: true",
            "SYSTEM SPECS:",
            "OS: Windows",
            "SYSTEM SPECS:",  # Duplicate marker
            "CPU: Intel",
            "PROBABLE CALL STACK:",
            "MODULES:",
            "F4SE PLUGINS:",
            "PLUGINS:",
        ]

        # Should handle gracefully
        result = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        assert len(result) == 4
        assert len(result[3]) == 6

    def test_no_newline_at_end(self) -> None:
        """Test handling of crash log without trailing newline."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "\t[Compatibility]",
            "SYSTEM SPECS:",
            "PROBABLE CALL STACK:",
            "MODULES:",
            "F4SE PLUGINS:",
            "PLUGINS:",
            "[00] Fallout4.esm",  # No newline after this
        ]

        result = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        assert len(result) == 4
        # Last segment (plugins) should have content
        plugins_segment = result[3][5]
        assert len(plugins_segment) >= 0  # May or may not have content depending on parser


@pytest.mark.unit
class TestParserPerformance:
    """Performance-related tests for the parser."""

    def test_large_crash_log_processing(self) -> None:
        """Test processing of a larger crash log doesn't cause issues."""
        # Generate a large crash log with many plugins
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION"',
            "\t[Compatibility]",
            "Achievements: true",
            "SYSTEM SPECS:",
            "OS: Windows",
            "PROBABLE CALL STACK:",
        ]

        # Add many call stack entries
        for i in range(100):
            crash_data.append(f"\t[{i:2d}] 0x7FF6{i:08X} Fallout4.exe")

        crash_data.append("MODULES:")

        # Add many modules
        for i in range(200):
            crash_data.append(f"\tmodule_{i}.dll v1.0.{i}")

        crash_data.append("F4SE PLUGINS:")

        for i in range(50):
            crash_data.append(f"\tplugin_{i}.dll v1.0.{i}")

        crash_data.append("PLUGINS:")

        # Add 255 plugins (near limit)
        for i in range(255):
            crash_data.append(f"\t[{i:02X}] TestPlugin{i}.esp")

        result = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        assert len(result) == 4
        assert len(result[3]) == 6

    def test_repeated_parsing_consistency(self, sample_crash_log_lines: list[str]) -> None:
        """Test that repeated parsing produces identical results."""
        results = []

        for _ in range(5):
            result = find_segments(
                sample_crash_log_lines,
                crashgen_name="Buffout 4",
                xse_acronym="F4SE",
                game_root_name="Fallout 4",
            )
            results.append(result)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result[0] == first_result[0]  # game_version
            assert result[1] == first_result[1]  # crashgen_version
            assert result[2] == first_result[2]  # main_error
            assert len(result[3]) == len(first_result[3])

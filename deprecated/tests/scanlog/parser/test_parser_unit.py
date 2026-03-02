"""Unit tests for the ScanLog Parser module.

This module tests the crash log parsing functionality including:
- parse_crash_header() - version extraction and error handling
- extract_segments() - segment boundary detection
- extract_module_names() - DLL module extraction
- find_segments() - complete segment parsing with metadata
"""

import pytest

pytestmark = [pytest.mark.unit]

from ClassicLib.scanning.logs import parser as parser_module
from ClassicLib.scanning.logs.parser import (
    extract_module_names,
    extract_segments,
    find_segments,
    get_parser_stats,
    is_rust_parser_available,
    parse_crash_header,
)


@pytest.mark.unit
class TestParseCrashHeader:
    """Test suite for parse_crash_header function."""

    def test_parse_valid_header(self, sample_crash_log_lines: list[str]) -> None:
        """Test parsing a valid crash log header extracts all metadata."""
        game_version, crashgen_version, main_error = parse_crash_header(
            sample_crash_log_lines,
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "Buffout 4 v1.28.6"
        assert "EXCEPTION_ACCESS_VIOLATION" in main_error

    def test_parse_header_unknown_game_version(self) -> None:
        """Test parsing returns UNKNOWN when game version not found."""
        crash_data = [
            "Buffout 4 v1.28.6",
            "Some other line",
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data,
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        assert game_version == "UNKNOWN"
        assert crashgen_version == "Buffout 4 v1.28.6"
        assert main_error == "UNKNOWN"

    def test_parse_header_unknown_crashgen_version(self) -> None:
        """Test parsing returns UNKNOWN when crash generator version not found."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Some other line",
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data,
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "UNKNOWN"
        assert main_error == "UNKNOWN"

    def test_parse_header_with_main_error(self) -> None:
        """Test parsing extracts the main error message correctly."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6|More Info',
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data,
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        # The | should be replaced with newline
        assert "EXCEPTION_ACCESS_VIOLATION" in main_error
        assert "\n" in main_error or "|" not in main_error[:50]

    def test_parse_header_empty_data(self) -> None:
        """Test parsing empty crash data returns all UNKNOWN values."""
        game_version, crashgen_version, main_error = parse_crash_header(
            [],
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        assert game_version == "UNKNOWN"
        assert crashgen_version == "UNKNOWN"
        assert main_error == "UNKNOWN"

    def test_parse_header_no_game_root_name(self) -> None:
        """Test parsing with empty game_root_name parameter."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data,
            crashgen_name="Buffout 4",
            game_root_name="",
        )

        # With empty game_root_name, no game version should be found
        assert game_version == "UNKNOWN"
        assert crashgen_version == "Buffout 4 v1.28.6"

    def test_parse_header_tolerates_leading_quote_noise(self) -> None:
        """Test parsing tolerates a leading quote/backtick before version lines."""
        crash_data = [
            "`Fallout 4 v1.10.163",
            '"Buffout 4 v1.28.6',
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6|More Info',
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data,
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "Buffout 4 v1.28.6"
        assert "EXCEPTION_ACCESS_VIOLATION" in main_error


@pytest.mark.unit
class TestExtractSegments:
    """Test suite for extract_segments function."""

    def test_extract_segments_basic(self) -> None:
        """Test extracting segments returns named dict with 8 keys.

        Boundaries parameter is ignored (anchor-first always used).
        Content that doesn't hit a game anchor ends up in 'settings'.
        """
        crash_data = [
            "Header line",
            "START_A",
            "Content A line 1",
            "Content A line 2",
            "END_A",
            "START_B",
            "Content B line 1",
            "END_B",
        ]
        boundaries = [
            ("START_A", "END_A"),
            ("START_B", "END_B"),
        ]

        segments = extract_segments(crash_data, boundaries, "EOF")

        # Result is always a dict with 8 named keys
        assert isinstance(segments, dict)
        assert len(segments) == 8
        # Non-anchor content ends up in settings
        settings = segments["settings"]
        assert any("Content A" in line or "Header" in line for line in settings)

    def test_extract_segments_with_eof_marker(self) -> None:
        """Test segment extraction with content before game anchors."""
        crash_data = [
            "START_A",
            "Content line",
            "EOF",
            "After EOF",
        ]
        # boundaries/eof are ignored — anchor-first always applies
        segments = extract_segments(crash_data, [], "EOF")

        # Result is always a dict with 8 named keys
        assert isinstance(segments, dict)
        assert len(segments) == 8
        # Content with no game anchors lands in settings
        settings = segments["settings"]
        assert any("Content" in line for line in settings)

    def test_extract_segments_empty_data(self) -> None:
        """Test extracting segments from empty crash data returns empty dict."""
        segments = extract_segments([], [], "EOF")

        # Returns a dict with 8 keys, all empty
        assert isinstance(segments, dict)
        assert len(segments) == 8
        assert all(v == [] for v in segments.values())

    def test_extract_segments_no_boundaries_found(self) -> None:
        """Test that content without game anchors lands in settings segment."""
        crash_data = [
            "Line 1",
            "Line 2",
            "Line 3",
        ]
        segments = extract_segments(crash_data, [("NONEXISTENT_START", "NONEXISTENT_END")], "EOF")

        # All content lands in settings when no game anchors present
        assert isinstance(segments, dict)
        assert len(segments) == 8
        assert len(segments["settings"]) == 3
        assert all(v == [] for k, v in segments.items() if k != "settings")

    def test_extract_segments_real_crash_log(self, sample_crash_log_lines: list[str]) -> None:
        """Test segment extraction on realistic crash log data."""
        # Boundaries parameter is ignored — anchor-first always applied
        segments = extract_segments(sample_crash_log_lines, [], "EOF")

        # Result is always a dict with 8 named keys
        assert isinstance(segments, dict)
        assert len(segments) == 8
        # At least some segments should have content
        assert any(v for v in segments.values())


@pytest.mark.unit
class TestExtractModuleNames:
    """Test suite for extract_module_names function."""

    def test_extract_module_names_basic(self) -> None:
        """Test extracting module names from simple DLL entries."""
        module_texts = {
            "test.dll v1.0.0",
            "another.dll v2.3.4",
            "simple.dll",
        }

        result = extract_module_names(module_texts)

        assert "test.dll" in result
        assert "another.dll" in result
        assert "simple.dll" in result

    def test_extract_module_names_with_path(self) -> None:
        """Test extraction handles DLL names with paths."""
        module_texts = {
            "C:\\Windows\\System32\\kernel32.dll v10.0.0",
        }

        # The regex should extract just the filename portion
        result = extract_module_names(module_texts)

        # Check at least one result exists
        assert len(result) > 0

    def test_extract_module_names_empty_set(self) -> None:
        """Test extraction returns empty set for empty input."""
        result = extract_module_names(set())

        assert result == set()

    def test_extract_module_names_no_dll_extension(self) -> None:
        """Test extraction handles entries without .dll extension."""
        module_texts = {
            "SomeFile.exe v1.0",
            "AnotherFile",
        }

        result = extract_module_names(module_texts)

        # Should return the text as-is when no .dll match
        assert len(result) == 2

    def test_extract_module_names_whitespace(self) -> None:
        """Test extraction handles whitespace correctly."""
        module_texts = {
            "  spaced.dll v1.0  ",
            "\ttabbed.dll\t",
        }

        result = extract_module_names(module_texts)

        # Results should have names extracted
        assert len(result) == 2

    def test_extract_module_names_case_insensitive(self) -> None:
        """Test that extraction works case-insensitively for .DLL extensions."""
        module_texts = {
            "test.DLL v1.0",
            "other.Dll v2.0",
        }

        result = extract_module_names(module_texts)

        # Both should be extracted regardless of case
        assert len(result) == 2


@pytest.mark.unit
class TestFindSegments:
    """Test suite for find_segments function (high-level parsing)."""

    def test_find_segments_basic(self, sample_crash_log_lines: list[str]) -> None:
        """Test find_segments extracts metadata and segments."""
        game_version, crashgen_version, main_error, segments = find_segments(
            sample_crash_log_lines,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Check metadata
        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "Buffout 4 v1.28.6"
        assert "EXCEPTION_ACCESS_VIOLATION" in main_error

        # Check segments structure — now a dict with 8 named keys
        assert isinstance(segments, dict)
        assert len(segments) == 8
        expected_keys = {"settings", "system", "callstack", "modules", "xse_modules", "plugins", "registers", "stack_dump"}
        assert set(segments.keys()) == expected_keys
        assert all(isinstance(v, list) for v in segments.values())

    def test_find_segments_empty_data(self) -> None:
        """Test find_segments handles empty crash data."""
        game_version, crashgen_version, main_error, segments = find_segments(
            [],
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        assert game_version == "UNKNOWN"
        assert crashgen_version == "UNKNOWN"
        assert main_error == "UNKNOWN"
        # Should have 8 named keys, all empty
        assert isinstance(segments, dict)
        assert len(segments) == 8
        assert all(v == [] for v in segments.values())

    def test_find_segments_malformed_log(self, malformed_crash_log_content: str) -> None:
        """Test find_segments handles malformed crash logs gracefully."""
        crash_lines = malformed_crash_log_content.splitlines()

        game_version, crashgen_version, main_error, segments = find_segments(
            crash_lines,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Should still return valid structure with 8 named keys
        assert isinstance(segments, dict)
        assert len(segments) == 8
        # Metadata may be partial
        assert "Fallout 4" in game_version or game_version == "UNKNOWN"

    def test_find_segments_strips_whitespace(self, sample_crash_log_lines: list[str]) -> None:
        """Test that segment content is properly stripped of whitespace."""
        _, _, _, segments = find_segments(
            sample_crash_log_lines,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Check that non-empty segments have stripped content
        for segment_lines in segments.values():
            for line in segment_lines:
                # Lines should be stripped (no leading/trailing whitespace)
                assert line == line.strip()

    def test_find_segments_preserves_segment_order(self) -> None:
        """Test that segments are returned in the expected order."""
        # Create minimal test data with clear segment markers
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "\t[Compatibility]",
            "Setting1: true",
            "SYSTEM SPECS:",
            "OS: Windows",
            "PROBABLE CALL STACK:",
            "[ 0] Address",
            "MODULES:",
            "test.dll",
            "F4SE PLUGINS:",
            "plugin.dll",
            "PLUGINS:",
            "[00] Test.esm",
        ]

        game_version, crashgen_version, main_error, segments = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Should have 8 named segments with anchor-first schema
        assert isinstance(segments, dict)
        assert len(segments) == 8
        # Settings section includes [Compatibility] header and Setting1
        assert any("Setting1" in line for line in segments["settings"])
        # System section has OS info
        assert any("OS:" in line for line in segments["system"])
        # Callstack has address
        assert any("Address" in line for line in segments["callstack"])
        # Modules has the DLL
        assert any("test.dll" in line for line in segments["modules"])
        # XSE modules has the plugin
        assert any("plugin.dll" in line for line in segments["xse_modules"])
        # Plugins has the ESM
        assert any("Test.esm" in line for line in segments["plugins"])

    def test_find_segments_propagates_rust_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """find_segments should not silently fall back when Rust parser fails."""

        class _FailingParser:
            def find_segments(self, *_args: object, **_kwargs: object) -> tuple[str, str, str, dict[str, list[str]]]:
                raise RuntimeError("simulated rust failure")

        monkeypatch.setattr(parser_module, "_rust_parser", _FailingParser())

        with pytest.raises(RuntimeError, match="simulated rust failure"):
            find_segments(
                ["Fallout 4 v1.10.163", "Buffout 4 v1.28.6"],
                crashgen_name="Buffout 4",
                xse_acronym="F4SE",
                game_root_name="Fallout 4",
            )


@pytest.mark.unit
class TestParserUtilities:
    """Test suite for parser utility functions."""

    def test_is_rust_parser_available(self) -> None:
        """Test that rust parser availability check returns a boolean."""
        result = is_rust_parser_available()

        assert isinstance(result, bool)

    def test_get_parser_stats(self) -> None:
        """Test that parser stats returns expected structure."""
        stats = get_parser_stats()

        assert isinstance(stats, dict)
        assert "parser_type" in stats
        assert stats["parser_type"] == "rust"
        assert "rust_available" in stats
        assert stats["rust_available"] is True

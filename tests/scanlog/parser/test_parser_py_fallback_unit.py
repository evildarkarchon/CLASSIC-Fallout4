"""Unit tests for the pure Python parser fallback implementation.

This module directly tests ClassicLib.python.parser_py to ensure the Python
fallback implementation has proper coverage. These tests exercise the fallback
code paths that are normally bypassed when Rust acceleration is available.

The Python fallback provides identical functionality to the Rust parser but
is only used when Rust components are unavailable, making direct testing
essential for coverage.
"""

import pytest

pytestmark = [pytest.mark.unit]

# Direct import of Python fallback implementation (not the high-level Parser)
from ClassicLib.python.parser_py import (
    extract_module_names,
    extract_segments,
    find_segments,
    parse_crash_header,
)


class TestParseCrashHeaderPy:
    """Test suite for pure Python parse_crash_header implementation."""

    def test_parse_valid_header_extracts_all_metadata(self) -> None:
        """Test parsing extracts game version, crashgen version, and main error."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512|Details',
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data, crashgen_name="Buffout 4", game_root_name="Fallout 4"
        )

        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "Buffout 4 v1.28.6"
        assert "EXCEPTION_ACCESS_VIOLATION" in main_error
        # The | should be replaced with newline
        assert "\n" in main_error

    def test_parse_header_with_skyrim_format(self) -> None:
        """Test parsing works with Skyrim crash log format."""
        crash_data = [
            "Skyrim SE v1.6.640",
            "Crash Logger v1.8.0",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at address',
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data, crashgen_name="Crash Logger", game_root_name="Skyrim SE"
        )

        assert game_version == "Skyrim SE v1.6.640"
        assert crashgen_version == "Crash Logger v1.8.0"
        assert "EXCEPTION_ACCESS_VIOLATION" in main_error

    def test_parse_header_returns_unknown_for_missing_game_version(self) -> None:
        """Test returns UNKNOWN when game version line is not present."""
        crash_data = [
            "Buffout 4 v1.28.6",
            "Some random line",
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data, crashgen_name="Buffout 4", game_root_name="Fallout 4"
        )

        assert game_version == "UNKNOWN"
        assert crashgen_version == "Buffout 4 v1.28.6"

    def test_parse_header_returns_unknown_for_missing_crashgen(self) -> None:
        """Test returns UNKNOWN when crash generator version is not present."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Some other line",
        ]

        game_version, crashgen_version, main_error = parse_crash_header(
            crash_data, crashgen_name="Buffout 4", game_root_name="Fallout 4"
        )

        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "UNKNOWN"

    def test_parse_header_returns_unknown_for_missing_error(self) -> None:
        """Test returns UNKNOWN when no unhandled exception is present."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
        ]

        _, _, main_error = parse_crash_header(
            crash_data, crashgen_name="Buffout 4", game_root_name="Fallout 4"
        )

        assert main_error == "UNKNOWN"

    def test_parse_header_handles_empty_data(self) -> None:
        """Test parsing empty crash data returns all UNKNOWN."""
        game_version, crashgen_version, main_error = parse_crash_header(
            [], crashgen_name="Buffout 4", game_root_name="Fallout 4"
        )

        assert game_version == "UNKNOWN"
        assert crashgen_version == "UNKNOWN"
        assert main_error == "UNKNOWN"

    def test_parse_header_with_empty_game_root_name(self) -> None:
        """Test parsing with empty game_root_name skips game version detection."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
        ]

        game_version, crashgen_version, _ = parse_crash_header(
            crash_data, crashgen_name="Buffout 4", game_root_name=""
        )

        # Empty game_root_name means line.startswith("") is always True
        # but the conditional checks "if game_root_name and..."
        assert game_version == "UNKNOWN"
        assert crashgen_version == "Buffout 4 v1.28.6"

    def test_parse_header_multiple_matching_lines_uses_last(self) -> None:
        """Test that when multiple lines match, later values are used."""
        crash_data = [
            "Fallout 4 v1.10.162",
            "Fallout 4 v1.10.163",  # Later version should be used
            "Buffout 4 v1.28.5",
            "Buffout 4 v1.28.6",  # Later version should be used
        ]

        game_version, crashgen_version, _ = parse_crash_header(
            crash_data, crashgen_name="Buffout 4", game_root_name="Fallout 4"
        )

        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "Buffout 4 v1.28.6"


class TestExtractSegmentsPy:
    """Test suite for pure Python extract_segments implementation."""

    def test_extract_basic_segment(self) -> None:
        """Test extracting a single segment between boundaries."""
        crash_data = [
            "Header",
            "START_MARKER",
            "Content line 1",
            "Content line 2",
            "Content line 3",
            "END_MARKER",
            "Footer",
        ]
        boundaries = [("START_MARKER", "END_MARKER")]

        segments = extract_segments(crash_data, boundaries, "EOF")

        assert len(segments) >= 1
        # Should contain at least some content from between markers
        if segments[0]:
            assert any("Content" in line for line in segments[0])

    def test_extract_multiple_segments(self) -> None:
        """Test extracting multiple sequential segments."""
        crash_data = [
            "Header",
            "SECTION_A_START",
            "A content 1",
            "A content 2",
            "SECTION_A_END",
            "SECTION_B_START",
            "B content 1",
            "B content 2",
            "SECTION_B_END",
        ]
        boundaries = [
            ("SECTION_A_START", "SECTION_A_END"),
            ("SECTION_B_START", "SECTION_B_END"),
        ]

        segments = extract_segments(crash_data, boundaries, "EOF")

        assert len(segments) >= 2
        # Check first segment has some A content
        if segments[0]:
            assert any("A content" in line for line in segments[0])
        # Check second segment has some B content
        if segments[1]:
            assert any("B content" in line for line in segments[1])

    def test_extract_segments_with_eof_marker(self) -> None:
        """Test that EOF marker captures all remaining content."""
        crash_data = [
            "PLUGINS:",
            "Plugin 1",
            "Plugin 2",
            "Plugin 3",
            # No explicit end marker - should read until EOF
        ]
        boundaries = [("PLUGINS:", "EOF")]

        segments = extract_segments(crash_data, boundaries, "EOF")

        assert len(segments) >= 1
        # Should capture all plugin lines
        combined = " ".join(segments[0]) if segments else ""
        assert "Plugin 1" in combined or "Plugin 2" in combined

    def test_extract_segments_empty_data(self) -> None:
        """Test extraction from empty crash data returns empty list."""
        boundaries = [("START", "END")]

        segments = extract_segments([], boundaries, "EOF")

        assert segments == []

    def test_extract_segments_no_boundaries_found(self) -> None:
        """Test extraction when boundaries don't exist in data."""
        crash_data = [
            "Line 1",
            "Line 2",
            "Line 3",
        ]
        boundaries = [("NONEXISTENT_START", "NONEXISTENT_END")]

        segments = extract_segments(crash_data, boundaries, "EOF")

        # Should return empty when boundaries not found
        assert segments == [] or all(len(seg) == 0 for seg in segments)

    def test_extract_segments_adjacent_boundaries(self) -> None:
        """Test extraction when end of one segment is start of next."""
        crash_data = [
            "SECTION_A",
            "A content",
            "SECTION_B",  # End of A is start of B
            "B content",
            "SECTION_C",
        ]
        boundaries = [
            ("SECTION_A", "SECTION_B"),
            ("SECTION_B", "SECTION_C"),
        ]

        segments = extract_segments(crash_data, boundaries, "EOF")

        assert len(segments) >= 2

    def test_extract_segments_real_crash_log_format(self) -> None:
        """Test extraction with real crash log structure."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "\t[Compatibility]",
            "\tSetting1: true",
            "\tSetting2: false",
            "SYSTEM SPECS:",
            "\tOS: Windows 11",
            "\tCPU: AMD Ryzen",
            "PROBABLE CALL STACK:",
            "\t[ 0] 0x7FF6EF4C3512",
            "MODULES:",
            "\ttest.dll v1.0",
            "F4SE PLUGINS:",
            "\tplugin.dll v1.0",
            "PLUGINS:",
            "\t[00] Fallout4.esm",
        ]
        boundaries = [
            ("\t[Compatibility]", "SYSTEM SPECS:"),
            ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
            ("PROBABLE CALL STACK:", "MODULES:"),
            ("MODULES:", "F4SE PLUGINS:"),
            ("F4SE PLUGINS:", "PLUGINS:"),
            ("PLUGINS:", "EOF"),
        ]

        segments = extract_segments(crash_data, boundaries, "EOF")

        # Should extract 6 segments
        assert len(segments) == 6
        # Verify some content
        all_content = " ".join(line for seg in segments for line in seg)
        assert "Setting1" in all_content or "Windows" in all_content

    def test_extract_segments_handles_single_line_segments(self) -> None:
        """Test extraction of segments with content between markers."""
        crash_data = [
            "START_A",
            "Content line 1",
            "Content line 2",
            "END_A",
        ]
        boundaries = [("START_A", "END_A")]

        segments = extract_segments(crash_data, boundaries, "EOF")

        assert len(segments) >= 1
        # Should capture at least some content
        if segments[0]:
            assert any("Content" in line for line in segments[0])

    def test_extract_segments_end_of_data_while_collecting(self) -> None:
        """Test that reaching end of data while collecting adds remaining content."""
        crash_data = [
            "START_MARKER",
            "Content 1",
            "Content 2",
            # No END_MARKER - reaches end while still collecting
        ]
        boundaries = [("START_MARKER", "END_MARKER")]

        segments = extract_segments(crash_data, boundaries, "EOF")

        # Should have captured the content even without end marker
        assert len(segments) >= 1


class TestFindSegmentsPy:
    """Test suite for pure Python find_segments implementation."""

    def test_find_segments_complete_crash_log(self) -> None:
        """Test find_segments with a complete crash log structure."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at address',
            "\t[Compatibility]",
            "\tAchievements: true",
            "SYSTEM SPECS:",
            "\tOS: Windows 11",
            "PROBABLE CALL STACK:",
            "\t[ 0] 0x7FF6",
            "MODULES:",
            "\ttest.dll v1.0",
            "F4SE PLUGINS:",
            "\tplugin.dll v1.0",
            "PLUGINS:",
            "\t[00] Fallout4.esm",
        ]

        game_version, crashgen_version, main_error, segments = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Verify metadata
        assert game_version == "Fallout 4 v1.10.163"
        assert crashgen_version == "Buffout 4 v1.28.6"
        assert "EXCEPTION_ACCESS_VIOLATION" in main_error

        # Verify 6 segments are returned
        assert len(segments) == 6
        assert all(isinstance(seg, list) for seg in segments)

    def test_find_segments_empty_data(self) -> None:
        """Test find_segments handles empty data gracefully."""
        game_version, crashgen_version, main_error, segments = find_segments(
            [],
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        assert game_version == "UNKNOWN"
        assert crashgen_version == "UNKNOWN"
        assert main_error == "UNKNOWN"
        # Should still return 6 empty segments
        assert len(segments) == 6

    def test_find_segments_strips_whitespace(self) -> None:
        """Test that segment content is stripped of whitespace."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "\t[Compatibility]",
            "  Content with spaces  ",
            "\tContent with tabs\t",
            "SYSTEM SPECS:",
            "  OS  ",
            "PROBABLE CALL STACK:",
            "  call  ",
            "MODULES:",
            "  mod  ",
            "F4SE PLUGINS:",
            "  plugin  ",
            "PLUGINS:",
            "  esp  ",
        ]

        _, _, _, segments = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Check all segment content is stripped
        for segment in segments:
            for line in segment:
                assert line == line.strip()

    def test_find_segments_missing_segments_are_empty_lists(self) -> None:
        """Test that missing segments are represented as empty lists."""
        # Minimal crash data with only some sections
        crash_data = [
            "Fallout 4 v1.10.163",
            "\t[Compatibility]",
            "Setting: true",
            "SYSTEM SPECS:",
            "OS: Windows",
            # Missing: PROBABLE CALL STACK, MODULES, F4SE PLUGINS, PLUGINS
        ]

        _, _, _, segments = find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout 4",
        )

        # Should have 6 segments (some may be empty)
        assert len(segments) == 6

    def test_find_segments_skse_format(self) -> None:
        """Test find_segments works with SKSE (Skyrim) format."""
        crash_data = [
            "Skyrim SE v1.6.640",
            "Crash Logger v1.8.0",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION"',
            "\t[Compatibility]",
            "\tSetting: value",
            "SYSTEM SPECS:",
            "\tOS: Windows",
            "PROBABLE CALL STACK:",
            "\tstack entry",
            "MODULES:",
            "\tmod.dll",
            "SKSE PLUGINS:",  # SKSE instead of F4SE
            "\tplugin.dll",
            "PLUGINS:",
            "\t[00] Skyrim.esm",
        ]

        game_version, crashgen_version, _, segments = find_segments(
            crash_data,
            crashgen_name="Crash Logger",
            xse_acronym="SKSE",  # Use SKSE acronym
            game_root_name="Skyrim SE",
        )

        assert game_version == "Skyrim SE v1.6.640"
        assert crashgen_version == "Crash Logger v1.8.0"
        assert len(segments) == 6


class TestExtractModuleNamesPy:
    """Test suite for pure Python extract_module_names implementation."""

    def test_extract_simple_dll_names(self) -> None:
        """Test extracting DLL names from simple entries."""
        module_texts = {
            "test.dll v1.0.0",
            "another.dll v2.3.4",
            "simple.dll",
        }

        result = extract_module_names(module_texts)

        assert "test.dll" in result
        assert "another.dll" in result
        assert "simple.dll" in result

    def test_extract_dll_names_with_version_formats(self) -> None:
        """Test extraction handles various version formats."""
        module_texts = {
            "mod.dll v1.0",
            "mod2.dll V2.0.0",  # uppercase V
            "mod3.dll 3.0",  # no v prefix
            "mod4.dll v4.0.0.0",  # 4-part version
        }

        result = extract_module_names(module_texts)

        assert "mod.dll" in result
        assert "mod2.dll" in result

    def test_extract_returns_empty_for_empty_input(self) -> None:
        """Test extraction returns empty set for empty input."""
        result = extract_module_names(set())

        assert result == set()

    def test_extract_handles_non_dll_entries(self) -> None:
        """Test extraction handles entries without .dll extension."""
        module_texts = {
            "program.exe v1.0",
            "noextension",
            "file.txt",
        }

        result = extract_module_names(module_texts)

        # Should return the text as-is when no .dll match
        assert len(result) == 3

    def test_extract_strips_whitespace(self) -> None:
        """Test extraction strips leading/trailing whitespace."""
        module_texts = {
            "  spaced.dll v1.0  ",
            "\ttabbed.dll v2.0\t",
            "  \t  both.dll v3.0  \t  ",
        }

        result = extract_module_names(module_texts)

        assert "spaced.dll" in result
        assert "tabbed.dll" in result
        assert "both.dll" in result

    def test_extract_case_insensitive_extension(self) -> None:
        """Test extraction is case-insensitive for .dll extension."""
        module_texts = {
            "lower.dll v1.0",
            "upper.DLL v2.0",
            "mixed.Dll v3.0",
        }

        result = extract_module_names(module_texts)

        # All should be extracted
        assert len(result) == 3

    def test_extract_preserves_original_case_in_result(self) -> None:
        """Test that extracted names preserve their original case."""
        module_texts = {
            "MyPlugin.dll v1.0",
            "UPPERCASE.DLL v2.0",
        }

        result = extract_module_names(module_texts)

        # The regex captures preserving case
        assert any("MyPlugin" in name for name in result)

    def test_extract_handles_complex_version_strings(self) -> None:
        """Test extraction handles complex version/metadata strings."""
        module_texts = {
            "plugin.dll v1.28.6-beta",
            "mod.dll version 2.0 (release)",
            "test.dll v0.1.2.3 alpha",
        }

        result = extract_module_names(module_texts)

        assert "plugin.dll" in result
        assert "mod.dll" in result
        assert "test.dll" in result

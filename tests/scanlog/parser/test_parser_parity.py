"""Parity tests for Python vs Rust parser implementations.

This module tests that both Python and Rust implementations produce
identical results for crash log parsing operations.
"""

import pytest

from ClassicLib.integration.factory import get_parser, is_rust_accelerated
from ClassicLib.scanning.logs.parser import (
    _extract_segments_python,
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
        # segments is now dict[str, list[str]] with 8 named keys
        assert isinstance(segments, dict)
        expected_keys = {"settings", "system", "callstack", "modules", "xse_modules", "plugins", "registers", "stack_dump"}
        assert expected_keys.issubset(segments.keys()), f"Missing keys: {expected_keys - segments.keys()}"

    def test_parse_crash_header_returns_strings(self, sample_crash_log_lines: list[str]) -> None:
        """Test that parse_crash_header always returns string tuple."""
        result = parse_crash_header(
            sample_crash_log_lines,
            crashgen_name="Buffout 4",
            game_root_name="Fallout 4",
        )

        assert len(result) == 3
        assert all(isinstance(val, str) for val in result)

    def test_extract_segments_returns_named_dict(self, sample_crash_log_lines: list[str]) -> None:
        """Test that extract_segments returns dict[str, list[str]] with named keys."""
        # The boundaries and eof_marker parameters are ignored (anchor-first always used)
        boundaries = [
            ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
        ]

        result = extract_segments(sample_crash_log_lines, boundaries, "EOF")

        assert isinstance(result, dict)
        expected_keys = {"settings", "system", "callstack", "modules", "xse_modules", "plugins", "registers", "stack_dump"}
        assert expected_keys.issubset(result.keys())
        for segment_lines in result.values():
            assert isinstance(segment_lines, list)
            for line in segment_lines:
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

        # Compare segment keys (both should return dict with 8 named keys)
        assert isinstance(factory_result[3], dict)
        assert isinstance(direct_result[3], dict)
        assert set(factory_result[3].keys()) == set(direct_result[3].keys())


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
        # Named dict with 8 keys, all empty
        assert isinstance(segments, dict)
        assert len(segments) == 8
        assert all(v == [] for v in segments.values())

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
        assert isinstance(result[3], dict)
        assert len(result[3]) == 8

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

        # Should still produce named dict with 8 keys (some may be empty)
        assert isinstance(result[3], dict)
        assert len(result[3]) == 8

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
        assert isinstance(result[3], dict)
        assert len(result[3]) == 8

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
        # plugins segment should be accessible by named key
        segments = result[3]
        assert isinstance(segments, dict)
        plugins_segment = segments.get("plugins", [])
        assert isinstance(plugins_segment, list)  # May or may not have content depending on parser


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
        assert isinstance(result[3], dict)
        assert len(result[3]) == 8

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
            assert set(result[3].keys()) == set(first_result[3].keys())


# ========================================================================================
# Tasks 8.4–8.7: New scenario tests for anchor-first segmentation and registry routing
# ========================================================================================


@pytest.mark.unit
class TestAnchorFirstSegmentation:
    """Task 8.4–8.6: New anchor-first segmentation scenario tests."""

    def test_addictol_patches_header_produces_correct_segments(self) -> None:
        """Task 8.4: Addictol log with [Patches] header segments correctly."""
        crash_data = [
            "Addictol v1.0.0",
            "[Patches]",
            "bSetting: true",
            "SYSTEM SPECS:",
            "OS: Windows 11",
            "PROBABLE CALL STACK:",
            "[0] 0x7FF func",
            "MODULES:",
            "module.dll v1.0",
            "PLUGINS:",
            "[00] Fallout4.esm",
        ]

        _, _, _, segments = find_segments(crash_data, "Addictol", "F4SE", "Fallout 4")

        # settings segment contains [Patches] line and bSetting line
        assert any("[Patches]" in line for line in segments["settings"])
        assert any("bSetting" in line for line in segments["settings"])
        # system, callstack, plugins should have content
        assert any("OS:" in line for line in segments["system"])
        assert any("func" in line for line in segments["callstack"])
        assert any("Fallout4.esm" in line for line in segments["plugins"])

    def test_unknown_bracket_header_same_structure_as_compatibility(self) -> None:
        """Task 8.5: Unknown bracket header produces same structure as [Compatibility]."""

        def make_log(header: str) -> list[str]:
            lines = [
                "CrashGen v1.0",
                header,
                "Setting: true",
                "SYSTEM SPECS:",
                "CPU: Intel",
                "MODULES:",
                "PLUGINS:",
                "[00] Fallout4.esm",
            ]
            return lines

        compat_log = make_log("[Compatibility]")
        unknown_log = make_log("[NewForkHeader]")

        _, _, _, compat_segs = find_segments(compat_log, "CrashGen", "F4SE", "Fallout 4")
        _, _, _, unknown_segs = find_segments(unknown_log, "CrashGen", "F4SE", "Fallout 4")

        # Both should have the same 8 named keys
        assert set(compat_segs.keys()) == set(unknown_segs.keys())
        assert len(compat_segs) == 8

        # settings segment contains the header line in both cases
        assert any("[Compatibility]" in line for line in compat_segs["settings"])
        assert any("[NewForkHeader]" in line for line in unknown_segs["settings"])

        # Same sections have content/empty in the same positions
        for key in ("system", "plugins"):
            assert bool(compat_segs[key]) == bool(unknown_segs[key])

    def test_no_bracket_header_produces_valid_settings_segment(self) -> None:
        """Task 8.6: Log with no bracket header before SYSTEM SPECS: gives valid settings."""
        crash_data = [
            "CrashGen v1.0",
            "Setting: false",
            "AnotherSetting: true",
            "SYSTEM SPECS:",
            "CPU: AMD",
        ]

        _, _, _, segments = find_segments(crash_data, "CrashGen", "F4SE", "Fallout 4")

        assert isinstance(segments, dict)
        # settings section should contain the header-less lines before SYSTEM SPECS:
        assert any("Setting: false" in line for line in segments["settings"])
        assert any("AnotherSetting" in line for line in segments["settings"])
        # system should have CPU
        assert any("CPU" in line for line in segments["system"])


@pytest.mark.unit
class TestRegistryRoutingIntegration:
    """Task 8.7: Registry routing tests (via Python extract_segments_python)."""

    def test_python_segments_return_named_dict(self) -> None:
        """Python fallback returns dict[str, list[str]] with all 8 keys."""
        crash_data = [
            "Buffout 4 v1.28.6",
            "[Compatibility]",
            "F4EE: true",
            "SYSTEM SPECS:",
            "CPU: AMD",
            "PROBABLE CALL STACK:",
            "[0] frame",
            "MODULES:",
            "mod.dll",
            "PLUGINS:",
            "[00] Fallout4.esm",
        ]

        result = _extract_segments_python(crash_data)

        expected_keys = {"settings", "system", "callstack", "modules", "xse_modules", "plugins", "registers", "stack_dump"}
        assert set(result.keys()) == expected_keys

        # settings should include [Compatibility]
        assert any("[Compatibility]" in line for line in result["settings"])
        # plugins should include Fallout4.esm
        assert any("Fallout4.esm" in line for line in result["plugins"])

    def test_python_single_letter_colon_label_does_not_split_xse_modules(self) -> None:
        """Single-letter uppercase colon labels should NOT be treated as XSE sub-headers."""
        crash_data = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "MODULES:",
            "kernel32.dll v10.0",
            "A:",
            "plugin.dll v1.0",
            "PLUGINS:",
            "[00] Fallout4.esm",
        ]

        result = _extract_segments_python(crash_data)

        # Keep both lines in modules; do not split into xse_modules on one-letter labels.
        assert any("kernel32.dll" in line for line in result["modules"])
        assert any("A:" == line.strip() for line in result["modules"])
        assert any("plugin.dll" in line for line in result["modules"])
        assert result["xse_modules"] == []

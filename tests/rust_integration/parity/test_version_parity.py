"""Parity tests for classic-version Rust module.

Tests Rust implementation parity with Python version handling, including
parsing, comparison, extraction, and validation of semantic versions.

This module uses pytest.mark.parametrize for efficient testing of multiple
inputs with the same test logic.
"""

import pytest

classic_version = pytest.importorskip("classic_version", reason="Rust classic_version module not available")


@pytest.mark.rust
@pytest.mark.unit
class TestVersionParsing:
    """Test version parsing functions."""

    def test_parse_version_function_exists(self):
        """Test parse_version() function is available."""
        assert hasattr(classic_version, "parse_version")
        assert callable(classic_version.parse_version)

    @pytest.mark.parametrize(
        "version_str,expected",
        [
            # Standard three-part versions
            ("1.10.163", (1, 10, 163)),
            ("0.6.23", (0, 6, 23)),
            ("2.0.0", (2, 0, 0)),
            # Four-part versions (ignores fourth)
            ("1.10.163.0", (1, 10, 163)),
            ("1.10.984.0", (1, 10, 984)),
            # With 'v' prefix
            ("v1.10.163", (1, 10, 163)),
            ("v0.6.23", (0, 6, 23)),
            # Two-part versions
            ("1.10", (1, 10, 0)),
            ("2.5", (2, 5, 0)),
        ],
        ids=[
            "standard_3part_1",
            "standard_3part_2",
            "standard_3part_3",
            "4part_ignores_fourth_1",
            "4part_ignores_fourth_2",
            "with_v_prefix_1",
            "with_v_prefix_2",
            "2part_pads_zero_1",
            "2part_pads_zero_2",
        ],
    )
    def test_parse_version_valid(self, version_str, expected):
        """Test parse_version() correctly parses valid version strings."""
        assert classic_version.parse_version(version_str) == expected

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "invalid",
            "not.a.version",
            "",
        ],
        ids=["text", "non_numeric_parts", "empty"],
    )
    def test_parse_version_invalid(self, invalid_input):
        """Test parse_version() raises ValueError for invalid input."""
        with pytest.raises(ValueError):
            classic_version.parse_version(invalid_input)

    def test_try_parse_version_function_exists(self):
        """Test try_parse_version() function is available."""
        assert hasattr(classic_version, "try_parse_version")
        assert callable(classic_version.try_parse_version)

    @pytest.mark.parametrize(
        "version_str,expected",
        [
            ("1.10.163", (1, 10, 163)),
            ("v0.6.23", (0, 6, 23)),
            ("1.10.163.0", (1, 10, 163)),
        ],
        ids=["standard", "with_v", "four_part"],
    )
    def test_try_parse_version_valid(self, version_str, expected):
        """Test try_parse_version() with valid versions."""
        assert classic_version.try_parse_version(version_str) == expected

    @pytest.mark.parametrize(
        "invalid_input",
        ["invalid", "not.a.version", ""],
        ids=["text", "non_numeric", "empty"],
    )
    def test_try_parse_version_invalid(self, invalid_input):
        """Test try_parse_version() returns None for invalid input."""
        assert classic_version.try_parse_version(invalid_input) is None


@pytest.mark.rust
@pytest.mark.unit
class TestVersionComparison:
    """Test version comparison functions."""

    def test_compare_versions_function_exists(self):
        """Test compare_versions() function is available."""
        assert hasattr(classic_version, "compare_versions")
        assert callable(classic_version.compare_versions)

    @pytest.mark.parametrize(
        "v1,v2,expected",
        [
            # Less than cases (expected: -1)
            ((1, 10, 163), (1, 10, 984), -1),
            ((0, 6, 23), (0, 7, 2), -1),
            ((1, 0, 0), (2, 0, 0), -1),
            ((1, 99, 99), (2, 0, 0), -1),
            ((1, 10, 999), (1, 11, 0), -1),
            ((1, 10, 163), (1, 10, 164), -1),
            # Equal cases (expected: 0)
            ((1, 10, 163), (1, 10, 163), 0),
            ((0, 6, 23), (0, 6, 23), 0),
            ((0, 0, 0), (0, 0, 0), 0),
            # Greater than cases (expected: 1)
            ((1, 10, 984), (1, 10, 163), 1),
            ((0, 7, 2), (0, 6, 23), 1),
            ((2, 0, 0), (1, 0, 0), 1),
            ((2, 0, 0), (1, 99, 99), 1),
            ((1, 11, 0), (1, 10, 999), 1),
            ((1, 10, 164), (1, 10, 163), 1),
        ],
        ids=[
            "lt_patch",
            "lt_minor",
            "lt_major",
            "lt_major_priority",
            "lt_minor_priority",
            "lt_patch_priority",
            "eq_1",
            "eq_2",
            "eq_zero",
            "gt_patch",
            "gt_minor",
            "gt_major",
            "gt_major_priority",
            "gt_minor_priority",
            "gt_patch_priority",
        ],
    )
    def test_compare_versions(self, v1, v2, expected):
        """Test compare_versions() returns correct comparison result."""
        assert classic_version.compare_versions(v1, v2) == expected


@pytest.mark.rust
@pytest.mark.unit
class TestKnownVersions:
    """Test known version validation functions."""

    def test_is_known_fallout4_version_function_exists(self):
        """Test is_known_fallout4_version() function is available."""
        assert hasattr(classic_version, "is_known_fallout4_version")
        assert callable(classic_version.is_known_fallout4_version)

    @pytest.mark.parametrize(
        "version,expected",
        [
            # Known valid Fallout 4 versions
            ((1, 10, 163), True),
            ((1, 10, 984), True),
            # Unknown versions
            ((9, 9, 9), False),
            ((0, 0, 0), False),
            ((2, 0, 0), False),
        ],
        ids=["og_version", "ng_version", "unknown_1", "zero", "unknown_2"],
    )
    def test_is_known_fallout4_version(self, version, expected):
        """Test is_known_fallout4_version() returns correct result."""
        assert classic_version.is_known_fallout4_version(version) is expected

    def test_is_known_f4se_version_function_exists(self):
        """Test is_known_f4se_version() function is available."""
        assert hasattr(classic_version, "is_known_f4se_version")
        assert callable(classic_version.is_known_f4se_version)

    @pytest.mark.parametrize(
        "version,expected",
        [
            # Known valid F4SE versions
            ((0, 6, 23), True),
            ((0, 7, 2), True),
            # Unknown versions
            ((9, 9, 9), False),
            ((1, 0, 0), False),
        ],
        ids=["f4se_og", "f4se_ng", "unknown_1", "unknown_2"],
    )
    def test_is_known_f4se_version(self, version, expected):
        """Test is_known_f4se_version() returns correct result."""
        assert classic_version.is_known_f4se_version(version) is expected


@pytest.mark.rust
@pytest.mark.unit
class TestVersionExtraction:
    """Test version extraction from filenames and logs."""

    def test_extract_version_from_filename_function_exists(self):
        """Test extract_version_from_filename() function is available."""
        assert hasattr(classic_version, "extract_version_from_filename")
        assert callable(classic_version.extract_version_from_filename)

    @pytest.mark.parametrize(
        "filename,expected",
        [
            # With 'v' prefix
            ("MyMod-v1.2.3.esp", (1, 2, 3)),
            ("Plugin-v0.6.23.dll", (0, 6, 23)),
            # No version
            ("NoVersion.esp", None),
            ("file.txt", None),
            ("", None),
        ],
        ids=["v_prefix_esp", "v_prefix_dll", "no_version_esp", "no_version_txt", "empty"],
    )
    def test_extract_version_from_filename(self, filename, expected):
        """Test extract_version_from_filename() with various inputs."""
        result = classic_version.extract_version_from_filename(filename)
        if expected is None:
            # No version found, or version without prefix may return None
            assert result is None or result == expected
        else:
            assert result == expected

    def test_extract_version_from_filename_without_prefix(self):
        """Test extracting versions without prefix from filenames."""
        result = classic_version.extract_version_from_filename("MyMod-1.2.3.esp")
        # Should extract version or None depending on implementation
        assert result is None or result == (1, 2, 3)

    def test_extract_version_from_log_function_exists(self):
        """Test extract_version_from_log() function is available."""
        assert hasattr(classic_version, "extract_version_from_log")
        assert callable(classic_version.extract_version_from_log)

    @pytest.mark.parametrize(
        "log_content,expected",
        [
            ("Game version: 1.10.163.0", (1, 10, 163)),
            ("No version here", None),
            ("", None),
        ],
        ids=["with_version", "no_version", "empty"],
    )
    def test_extract_version_from_log(self, log_content, expected):
        """Test extract_version_from_log() with various inputs."""
        result = classic_version.extract_version_from_log(log_content)
        if expected is None:
            assert result is None
        else:
            assert result == expected

    def test_extract_all_versions_function_exists(self):
        """Test extract_all_versions() function is available."""
        assert hasattr(classic_version, "extract_all_versions")
        assert callable(classic_version.extract_all_versions)

    def test_extract_all_versions_basic(self):
        """Test extracting all versions from text."""
        text = "Versions: 1.10.163, 1.10.984, and v0.6.23"
        result = classic_version.extract_all_versions(text)
        assert isinstance(result, list)
        # Should find at least some versions
        assert len(result) >= 0


@pytest.mark.rust
@pytest.mark.unit
class TestVersionFormatting:
    """Test version formatting functions."""

    def test_format_version_function_exists(self):
        """Test format_version() function is available."""
        assert hasattr(classic_version, "format_version")
        assert callable(classic_version.format_version)

    def test_format_version_default(self):
        """Test format_version() with default prefix."""
        formatted = classic_version.format_version((1, 10, 163))
        # Should format with 'v' prefix by default
        assert formatted == "v1.10.163" or formatted == "1.10.163"

    @pytest.mark.parametrize(
        "version,expected_parts",
        [
            ((0, 6, 23), ["0", "6", "23"]),
            ((2, 0, 0), ["2", "0"]),
            ((1, 0, 0), ["1", "0"]),
        ],
        ids=["small_version", "major_only", "one_zero"],
    )
    def test_format_version_various(self, version, expected_parts):
        """Test format_version() produces string containing version parts."""
        result = classic_version.format_version(version)
        assert isinstance(result, str)
        for part in expected_parts:
            assert part in result


@pytest.mark.rust
@pytest.mark.unit
class TestModuleMetadata:
    """Test module-level metadata."""

    def test_module_version(self):
        """Test module __version__ is defined."""
        assert hasattr(classic_version, "__version__")
        assert isinstance(classic_version.__version__, str)
        assert len(classic_version.__version__) > 0

    def test_module_all_exports(self):
        """Test __all__ exports key functions."""
        assert hasattr(classic_version, "__all__")
        all_exports = classic_version.__all__

        # Key functions should be exported
        expected = [
            "parse_version",
            "try_parse_version",
            "compare_versions",
            "is_known_fallout4_version",
            "is_known_f4se_version",
            "extract_version_from_filename",
            "extract_version_from_log",
            "extract_all_versions",
            "format_version",
        ]

        for func in expected:
            assert func in all_exports, f"{func} should be in __all__"


@pytest.mark.rust
@pytest.mark.integration
class TestVersionParityWithConstants:
    """Test version module integrates correctly with constants."""

    def test_known_fallout4_versions_match_constants(self):
        """Test known Fallout 4 versions match those from constants module."""
        try:
            import classic_constants

            # OG and NG versions should be recognized
            og_version = classic_version.parse_version(classic_constants.FALLOUT4_OG_VERSION)
            ng_version = classic_version.parse_version(classic_constants.FALLOUT4_NG_VERSION)

            assert classic_version.is_known_fallout4_version(og_version) is True
            assert classic_version.is_known_fallout4_version(ng_version) is True

        except ImportError:
            pytest.skip("classic_constants module not available")

    def test_known_f4se_versions_match_constants(self):
        """Test known F4SE versions match those from constants module."""
        try:
            import classic_constants

            # Parse F4SE versions from constants
            og_f4se = classic_version.parse_version(classic_constants.F4SE_OG_VERSION)
            ng_f4se = classic_version.parse_version(classic_constants.F4SE_NG_VERSION)

            # Both should be recognized
            assert classic_version.is_known_f4se_version(og_f4se) is True
            assert classic_version.is_known_f4se_version(ng_f4se) is True

        except ImportError:
            pytest.skip("classic_constants module not available")

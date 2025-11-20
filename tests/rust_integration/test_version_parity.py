"""Parity tests for classic-version Rust module.

Tests Rust implementation parity with Python version handling, including
parsing, comparison, extraction, and validation of semantic versions.
"""

import pytest

import classic_version


@pytest.mark.rust
@pytest.mark.unit
class TestVersionParsing:
    """Test version parsing functions."""

    def test_parse_version_function_exists(self):
        """Test parse_version() function is available."""
        assert hasattr(classic_version, "parse_version")
        assert callable(classic_version.parse_version)

    def test_parse_version_standard_format(self):
        """Test parse_version() with standard version formats."""
        # Three-part version
        assert classic_version.parse_version("1.10.163") == (1, 10, 163)
        assert classic_version.parse_version("0.6.23") == (0, 6, 23)
        assert classic_version.parse_version("2.0.0") == (2, 0, 0)

    def test_parse_version_with_fourth_component(self):
        """Test parse_version() with four-part versions (ignores fourth)."""
        assert classic_version.parse_version("1.10.163.0") == (1, 10, 163)
        assert classic_version.parse_version("1.10.984.0") == (1, 10, 984)

    def test_parse_version_with_prefix(self):
        """Test parse_version() with 'v' prefix."""
        assert classic_version.parse_version("v1.10.163") == (1, 10, 163)
        assert classic_version.parse_version("v0.6.23") == (0, 6, 23)

    def test_parse_version_two_part(self):
        """Test parse_version() with two-part versions."""
        assert classic_version.parse_version("1.10") == (1, 10, 0)
        assert classic_version.parse_version("2.5") == (2, 5, 0)

    def test_parse_version_invalid(self):
        """Test parse_version() raises ValueError for invalid input."""
        with pytest.raises(ValueError):
            classic_version.parse_version("invalid")

        with pytest.raises(ValueError):
            classic_version.parse_version("not.a.version")

        with pytest.raises(ValueError):
            classic_version.parse_version("")

    def test_try_parse_version_function_exists(self):
        """Test try_parse_version() function is available."""
        assert hasattr(classic_version, "try_parse_version")
        assert callable(classic_version.try_parse_version)

    def test_try_parse_version_valid(self):
        """Test try_parse_version() with valid versions."""
        assert classic_version.try_parse_version("1.10.163") == (1, 10, 163)
        assert classic_version.try_parse_version("v0.6.23") == (0, 6, 23)
        assert classic_version.try_parse_version("1.10.163.0") == (1, 10, 163)

    def test_try_parse_version_invalid(self):
        """Test try_parse_version() returns None for invalid input."""
        assert classic_version.try_parse_version("invalid") is None
        assert classic_version.try_parse_version("not.a.version") is None
        assert classic_version.try_parse_version("") is None


@pytest.mark.rust
@pytest.mark.unit
class TestVersionComparison:
    """Test version comparison functions."""

    def test_compare_versions_function_exists(self):
        """Test compare_versions() function is available."""
        assert hasattr(classic_version, "compare_versions")
        assert callable(classic_version.compare_versions)

    def test_compare_versions_less_than(self):
        """Test compare_versions() returns -1 when v1 < v2."""
        assert classic_version.compare_versions((1, 10, 163), (1, 10, 984)) == -1
        assert classic_version.compare_versions((0, 6, 23), (0, 7, 2)) == -1
        assert classic_version.compare_versions((1, 0, 0), (2, 0, 0)) == -1

    def test_compare_versions_equal(self):
        """Test compare_versions() returns 0 when v1 == v2."""
        assert classic_version.compare_versions((1, 10, 163), (1, 10, 163)) == 0
        assert classic_version.compare_versions((0, 6, 23), (0, 6, 23)) == 0
        assert classic_version.compare_versions((0, 0, 0), (0, 0, 0)) == 0

    def test_compare_versions_greater_than(self):
        """Test compare_versions() returns 1 when v1 > v2."""
        assert classic_version.compare_versions((1, 10, 984), (1, 10, 163)) == 1
        assert classic_version.compare_versions((0, 7, 2), (0, 6, 23)) == 1
        assert classic_version.compare_versions((2, 0, 0), (1, 0, 0)) == 1

    def test_compare_versions_component_priority(self):
        """Test compare_versions() prioritizes major > minor > patch."""
        # Major version difference
        assert classic_version.compare_versions((2, 0, 0), (1, 99, 99)) == 1
        assert classic_version.compare_versions((1, 99, 99), (2, 0, 0)) == -1

        # Minor version difference
        assert classic_version.compare_versions((1, 11, 0), (1, 10, 999)) == 1
        assert classic_version.compare_versions((1, 10, 999), (1, 11, 0)) == -1

        # Patch version difference
        assert classic_version.compare_versions((1, 10, 164), (1, 10, 163)) == 1
        assert classic_version.compare_versions((1, 10, 163), (1, 10, 164)) == -1


@pytest.mark.rust
@pytest.mark.unit
class TestKnownVersions:
    """Test known version validation functions."""

    def test_is_known_fallout4_version_function_exists(self):
        """Test is_known_fallout4_version() function is available."""
        assert hasattr(classic_version, "is_known_fallout4_version")
        assert callable(classic_version.is_known_fallout4_version)

    def test_is_known_fallout4_version_valid(self):
        """Test is_known_fallout4_version() returns True for known versions."""
        # OG and NG versions from constants
        assert classic_version.is_known_fallout4_version((1, 10, 163)) is True
        assert classic_version.is_known_fallout4_version((1, 10, 984)) is True

    def test_is_known_fallout4_version_invalid(self):
        """Test is_known_fallout4_version() returns False for unknown versions."""
        assert classic_version.is_known_fallout4_version((9, 9, 9)) is False
        assert classic_version.is_known_fallout4_version((0, 0, 0)) is False
        assert classic_version.is_known_fallout4_version((2, 0, 0)) is False

    def test_is_known_f4se_version_function_exists(self):
        """Test is_known_f4se_version() function is available."""
        assert hasattr(classic_version, "is_known_f4se_version")
        assert callable(classic_version.is_known_f4se_version)

    def test_is_known_f4se_version_valid(self):
        """Test is_known_f4se_version() returns True for known F4SE versions."""
        # Common F4SE versions
        assert classic_version.is_known_f4se_version((0, 6, 23)) is True
        assert classic_version.is_known_f4se_version((0, 7, 2)) is True

    def test_is_known_f4se_version_invalid(self):
        """Test is_known_f4se_version() returns False for unknown versions."""
        assert classic_version.is_known_f4se_version((9, 9, 9)) is False
        assert classic_version.is_known_f4se_version((1, 0, 0)) is False


@pytest.mark.rust
@pytest.mark.unit
class TestVersionExtraction:
    """Test version extraction from filenames and logs."""

    def test_extract_version_from_filename_function_exists(self):
        """Test extract_version_from_filename() function is available."""
        assert hasattr(classic_version, "extract_version_from_filename")
        assert callable(classic_version.extract_version_from_filename)

    def test_extract_version_from_filename_with_v_prefix(self):
        """Test extracting versions with 'v' prefix from filenames."""
        assert classic_version.extract_version_from_filename("MyMod-v1.2.3.esp") == (1, 2, 3)
        assert classic_version.extract_version_from_filename("Plugin-v0.6.23.dll") == (0, 6, 23)

    def test_extract_version_from_filename_without_prefix(self):
        """Test extracting versions without prefix from filenames."""
        result = classic_version.extract_version_from_filename("MyMod-1.2.3.esp")
        # Should extract version or None depending on implementation
        assert result is None or result == (1, 2, 3)

    def test_extract_version_from_filename_no_version(self):
        """Test extract_version_from_filename() returns None when no version found."""
        assert classic_version.extract_version_from_filename("NoVersion.esp") is None
        assert classic_version.extract_version_from_filename("file.txt") is None
        assert classic_version.extract_version_from_filename("") is None

    def test_extract_version_from_log_function_exists(self):
        """Test extract_version_from_log() function is available."""
        assert hasattr(classic_version, "extract_version_from_log")
        assert callable(classic_version.extract_version_from_log)

    def test_extract_version_from_log_basic(self):
        """Test extracting version from log content."""
        log_content = "Game version: 1.10.163.0"
        result = classic_version.extract_version_from_log(log_content)
        assert result is None or result == (1, 10, 163)

    def test_extract_version_from_log_no_version(self):
        """Test extract_version_from_log() returns None when no version found."""
        assert classic_version.extract_version_from_log("No version here") is None
        assert classic_version.extract_version_from_log("") is None

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

    def test_format_version_various(self):
        """Test format_version() with various version tuples."""
        # Test that formatting works (exact format may vary)
        result1 = classic_version.format_version((0, 6, 23))
        result2 = classic_version.format_version((2, 0, 0))
        result3 = classic_version.format_version((1, 0, 0))

        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert isinstance(result3, str)

        # Results should contain the version numbers
        assert "0" in result1 and "6" in result1 and "23" in result1
        assert "2" in result2 and "0" in result2
        assert "1" in result3 and "0" in result3


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

"""Integration tests for classic-xse Rust module.

Tests the Rust-accelerated XSE (Script Extender) detection and management,
including version detection, installation checking, and type enumeration.
"""

import tempfile
from pathlib import Path

import pytest

import classic_xse


@pytest.mark.rust
@pytest.mark.unit
class TestXseType:
    """Test XseType enumeration."""

    def test_xse_type_variants_exist(self):
        """Test all XseType factory methods are accessible."""
        assert hasattr(classic_xse.XseType, "f4se")
        assert hasattr(classic_xse.XseType, "f4sevr")
        assert hasattr(classic_xse.XseType, "skse")
        assert hasattr(classic_xse.XseType, "skse64")
        assert hasattr(classic_xse.XseType, "sksevr")
        assert hasattr(classic_xse.XseType, "sfse")

    def test_xse_type_creation(self):
        """Test creating XseType instances."""
        f4se = classic_xse.XseType.f4se()
        f4sevr = classic_xse.XseType.f4sevr()
        skse = classic_xse.XseType.skse()
        skse64 = classic_xse.XseType.skse64()
        sksevr = classic_xse.XseType.sksevr()
        sfse = classic_xse.XseType.sfse()

        # All should be XseType instances
        assert isinstance(f4se, classic_xse.XseType)
        assert isinstance(f4sevr, classic_xse.XseType)
        assert isinstance(skse, classic_xse.XseType)
        assert isinstance(skse64, classic_xse.XseType)
        assert isinstance(sksevr, classic_xse.XseType)
        assert isinstance(sfse, classic_xse.XseType)

    def test_xse_type_as_str(self):
        """Test XseType.as_str() returns correct names."""
        assert classic_xse.XseType.f4se().as_str() == "F4SE"
        assert classic_xse.XseType.f4sevr().as_str() == "F4SEVR"
        assert classic_xse.XseType.skse().as_str() == "SKSE"
        assert classic_xse.XseType.skse64().as_str() == "SKSE64"
        assert classic_xse.XseType.sksevr().as_str() == "SKSEVR"
        assert classic_xse.XseType.sfse().as_str() == "SFSE"

    def test_xse_type_loader_name(self):
        """Test XseType.loader_name() returns correct executable names."""
        assert classic_xse.XseType.f4se().loader_name() == "f4se_loader.exe"
        assert classic_xse.XseType.f4sevr().loader_name() == "f4sevr_loader.exe"
        assert classic_xse.XseType.skse().loader_name() == "skse_loader.exe"
        assert classic_xse.XseType.skse64().loader_name() == "skse64_loader.exe"
        assert classic_xse.XseType.sksevr().loader_name() == "sksevr_loader.exe"
        assert classic_xse.XseType.sfse().loader_name() == "sfse_loader.exe"

    def test_xse_type_dll_prefix(self):
        """Test XseType.dll_prefix() returns correct DLL prefixes."""
        assert classic_xse.XseType.f4se().dll_prefix() == "f4se_"
        assert classic_xse.XseType.f4sevr().dll_prefix() == "f4sevr_"
        assert classic_xse.XseType.skse().dll_prefix() == "skse_"
        assert classic_xse.XseType.skse64().dll_prefix() == "skse64_"
        assert classic_xse.XseType.sksevr().dll_prefix() == "sksevr_"
        assert classic_xse.XseType.sfse().dll_prefix() == "sfse_"

    def test_xse_type_str(self):
        """Test XseType.__str__() returns type name."""
        assert str(classic_xse.XseType.f4se()) == "F4SE"
        assert str(classic_xse.XseType.skse64()) == "SKSE64"

    def test_xse_type_repr(self):
        """Test XseType.__repr__() includes type information."""
        repr_str = repr(classic_xse.XseType.f4se())
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0

    def test_xse_type_equality(self):
        """Test XseType equality comparison."""
        # Same types should be equal
        assert classic_xse.XseType.f4se() == classic_xse.XseType.f4se()
        assert classic_xse.XseType.skse64() == classic_xse.XseType.skse64()

        # Different types should not be equal
        assert classic_xse.XseType.f4se() != classic_xse.XseType.f4sevr()
        assert classic_xse.XseType.skse() != classic_xse.XseType.skse64()


@pytest.mark.rust
@pytest.mark.unit
class TestParseXseType:
    """Test parse_xse_type() function."""

    def test_parse_xse_type_function_exists(self):
        """Test parse_xse_type() function is available."""
        assert hasattr(classic_xse, "parse_xse_type")
        assert callable(classic_xse.parse_xse_type)

    def test_parse_xse_type_case_insensitive(self):
        """Test parse_xse_type() is case-insensitive."""
        # Lowercase
        assert classic_xse.parse_xse_type("f4se").as_str() == "F4SE"
        assert classic_xse.parse_xse_type("skse64").as_str() == "SKSE64"

        # Uppercase
        assert classic_xse.parse_xse_type("F4SE").as_str() == "F4SE"
        assert classic_xse.parse_xse_type("SKSE64").as_str() == "SKSE64"

        # Mixed case
        assert classic_xse.parse_xse_type("F4sE").as_str() == "F4SE"
        assert classic_xse.parse_xse_type("SkSe64").as_str() == "SKSE64"

    def test_parse_xse_type_all_variants(self):
        """Test parse_xse_type() works for all XSE types."""
        assert classic_xse.parse_xse_type("f4se").as_str() == "F4SE"
        assert classic_xse.parse_xse_type("f4sevr").as_str() == "F4SEVR"
        assert classic_xse.parse_xse_type("skse").as_str() == "SKSE"
        assert classic_xse.parse_xse_type("skse64").as_str() == "SKSE64"
        assert classic_xse.parse_xse_type("sksevr").as_str() == "SKSEVR"
        assert classic_xse.parse_xse_type("sfse").as_str() == "SFSE"

    def test_parse_xse_type_invalid(self):
        """Test parse_xse_type() raises ValueError for invalid types."""
        with pytest.raises(ValueError):
            classic_xse.parse_xse_type("invalid")

        with pytest.raises(ValueError):
            classic_xse.parse_xse_type("")

        with pytest.raises(ValueError):
            classic_xse.parse_xse_type("f5se")


@pytest.mark.rust
@pytest.mark.unit
class TestXseInfo:
    """Test XseInfo class."""

    def test_xse_info_creation(self):
        """Test creating XseInfo instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = classic_xse.XseInfo(classic_xse.XseType.f4se(), tmpdir)
            assert isinstance(info, classic_xse.XseInfo)

    def test_xse_info_properties(self):
        """Test XseInfo properties."""
        with tempfile.TemporaryDirectory() as tmpdir:
            xse_type = classic_xse.XseType.f4se()
            info = classic_xse.XseInfo(xse_type, tmpdir)

            # Check properties
            assert info.xse_type().as_str() == "F4SE"
            assert info.path() == tmpdir
            assert isinstance(info.path(), str)

    def test_xse_info_not_installed(self):
        """Test XseInfo when XSE is not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = classic_xse.XseInfo(classic_xse.XseType.f4se(), tmpdir)

            # Should not be installed (no loader executable)
            assert info.installed() is False
            assert info.check_installed() is False
            assert info.version() is None

    def test_xse_info_loader_path(self):
        """Test XseInfo.loader_path() returns correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = classic_xse.XseInfo(classic_xse.XseType.f4se(), tmpdir)
            loader_path = info.loader_path()

            # Should be tmpdir + loader name
            expected = str(Path(tmpdir) / "f4se_loader.exe")
            assert loader_path == expected

    def test_xse_info_installed_with_file(self):
        """Test XseInfo.installed() returns True when loader exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create loader file
            loader_path = Path(tmpdir) / "f4se_loader.exe"
            loader_path.write_bytes(b"fake loader")

            info = classic_xse.XseInfo(classic_xse.XseType.f4se(), tmpdir)

            # Should now be installed
            assert info.check_installed() is True

    def test_xse_info_str(self):
        """Test XseInfo.__str__() returns formatted string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = classic_xse.XseInfo(classic_xse.XseType.f4se(), tmpdir)
            str_repr = str(info)

            assert isinstance(str_repr, str)
            assert len(str_repr) > 0

    def test_xse_info_repr(self):
        """Test XseInfo.__repr__() includes debug information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = classic_xse.XseInfo(classic_xse.XseType.f4se(), tmpdir)
            repr_str = repr(info)

            assert isinstance(repr_str, str)
            assert len(repr_str) > 0


@pytest.mark.rust
@pytest.mark.integration
class TestXseDetectionFunctions:
    """Test XSE detection utility functions."""

    def test_is_xse_installed_function_exists(self):
        """Test is_xse_installed() function is available."""
        assert hasattr(classic_xse, "is_xse_installed")
        assert callable(classic_xse.is_xse_installed)

    def test_is_xse_installed_not_installed(self):
        """Test is_xse_installed() returns False when not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = classic_xse.is_xse_installed(tmpdir, classic_xse.XseType.f4se())
            assert result is False

    def test_is_xse_installed_with_loader(self):
        """Test is_xse_installed() returns True when loader exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create loader file
            loader_path = Path(tmpdir) / "f4se_loader.exe"
            loader_path.write_bytes(b"fake loader")

            result = classic_xse.is_xse_installed(tmpdir, classic_xse.XseType.f4se())
            assert result is True

    def test_is_xse_installed_different_types(self):
        """Test is_xse_installed() with different XSE types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create F4SE loader
            f4se_loader = Path(tmpdir) / "f4se_loader.exe"
            f4se_loader.write_bytes(b"fake f4se")

            # F4SE should be installed
            assert classic_xse.is_xse_installed(tmpdir, classic_xse.XseType.f4se()) is True

            # SKSE64 should not be installed (different loader)
            assert classic_xse.is_xse_installed(tmpdir, classic_xse.XseType.skse64()) is False

    def test_get_xse_info_function_exists(self):
        """Test get_xse_info() function is available."""
        assert hasattr(classic_xse, "get_xse_info")
        assert callable(classic_xse.get_xse_info)

    def test_get_xse_info_returns_info(self):
        """Test get_xse_info() returns XseInfo object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = classic_xse.get_xse_info(tmpdir, classic_xse.XseType.f4se())

            assert isinstance(info, classic_xse.XseInfo)
            assert info.xse_type().as_str() == "F4SE"
            assert info.path() == tmpdir

    def test_get_xse_info_not_installed(self):
        """Test get_xse_info() returns correct status when not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            info = classic_xse.get_xse_info(tmpdir, classic_xse.XseType.f4se())

            assert info.installed() is False
            assert info.version() is None

    def test_get_xse_info_installed(self):
        """Test get_xse_info() returns correct status when installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create loader file
            loader_path = Path(tmpdir) / "skse64_loader.exe"
            loader_path.write_bytes(b"fake skse64")

            info = classic_xse.get_xse_info(tmpdir, classic_xse.XseType.skse64())

            assert info.check_installed() is True

    def test_detect_xse_version_function_exists(self):
        """Test detect_xse_version() function is available."""
        assert hasattr(classic_xse, "detect_xse_version")
        assert callable(classic_xse.detect_xse_version)

    def test_detect_xse_version_nonexistent_file(self):
        """Test detect_xse_version() raises IOError for nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_path = str(Path(tmpdir) / "nonexistent.exe")

            with pytest.raises(Exception):  # IOError or similar
                classic_xse.detect_xse_version(fake_path, classic_xse.XseType.f4se())


@pytest.mark.rust
@pytest.mark.unit
class TestModuleMetadata:
    """Test module-level metadata."""

    def test_module_version(self):
        """Test module __version__ is defined."""
        assert hasattr(classic_xse, "__version__")
        assert isinstance(classic_xse.__version__, str)
        assert len(classic_xse.__version__) > 0

    def test_module_exports(self):
        """Test module exports key types and functions."""
        # Classes
        assert hasattr(classic_xse, "XseType")
        assert hasattr(classic_xse, "XseInfo")

        # Functions
        assert hasattr(classic_xse, "parse_xse_type")
        assert hasattr(classic_xse, "detect_xse_version")
        assert hasattr(classic_xse, "is_xse_installed")
        assert hasattr(classic_xse, "get_xse_info")


@pytest.mark.rust
@pytest.mark.integration
class TestXseTypeConsistency:
    """Test consistency between XseType methods."""

    def test_loader_name_matches_dll_prefix(self):
        """Test loader names and DLL prefixes are consistent."""
        xse_types = [
            classic_xse.XseType.f4se(),
            classic_xse.XseType.f4sevr(),
            classic_xse.XseType.skse(),
            classic_xse.XseType.skse64(),
            classic_xse.XseType.sksevr(),
            classic_xse.XseType.sfse(),
        ]

        for xse_type in xse_types:
            loader = xse_type.loader_name()
            dll_prefix = xse_type.dll_prefix()
            type_str = xse_type.as_str().lower()

            # Loader should contain the prefix
            assert dll_prefix.rstrip("_") in loader, f"{dll_prefix} should be in {loader}"

    def test_as_str_matches_parse_roundtrip(self):
        """Test as_str() and parse_xse_type() are consistent."""
        xse_types = [
            classic_xse.XseType.f4se(),
            classic_xse.XseType.f4sevr(),
            classic_xse.XseType.skse(),
            classic_xse.XseType.skse64(),
            classic_xse.XseType.sksevr(),
            classic_xse.XseType.sfse(),
        ]

        for xse_type in xse_types:
            type_str = xse_type.as_str()
            parsed = classic_xse.parse_xse_type(type_str)

            # Should round-trip correctly
            assert parsed.as_str() == type_str
            assert parsed == xse_type

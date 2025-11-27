"""Tests for enhanced DDS analyzer module."""

import asyncio
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

from ClassicLib.ScanGame.core.dds_analyzer import (
    DDSFlags,
    DDSInfo,
    DDSPixelFlags,
    EnhancedDDSAnalyzer,
    analyze_dds,
    get_analyzer,
)


@pytest.fixture
def analyzer():
    """Create analyzer instance without library dependencies."""
    with patch("ClassicLib.ScanGame.core.dds_analyzer.HAS_PYFFI", False), patch("ClassicLib.ScanGame.core.dds_analyzer.HAS_PIL_DDS", False):
        return EnhancedDDSAnalyzer(use_libraries=False)


@pytest.fixture
def valid_dds_data():
    """Create valid DDS header data for testing."""
    header = bytearray(128)

    # Magic number "DDS "
    header[0:4] = b"DDS "

    # dwSize (124)
    header[4:8] = struct.pack("<I", 124)

    # dwFlags
    flags = DDSFlags.CAPS | DDSFlags.HEIGHT | DDSFlags.WIDTH | DDSFlags.PIXELFORMAT
    header[8:12] = struct.pack("<I", flags)

    # dwHeight
    header[12:16] = struct.pack("<I", 1024)

    # dwWidth
    header[16:20] = struct.pack("<I", 2048)

    # dwPitchOrLinearSize
    header[20:24] = struct.pack("<I", 0)

    # dwDepth
    header[24:28] = struct.pack("<I", 1)

    # dwMipMapCount
    header[28:32] = struct.pack("<I", 1)

    # Pixel format at offset 76
    pf_offset = 76
    header[pf_offset : pf_offset + 4] = struct.pack("<I", 32)  # Size
    header[pf_offset + 4 : pf_offset + 8] = struct.pack("<I", DDSPixelFlags.FOURCC)  # Flags
    header[pf_offset + 8 : pf_offset + 12] = b"DXT5"  # FourCC

    # Caps
    header[108:112] = struct.pack("<I", 0x1000)  # DDSCAPS_TEXTURE
    header[112:116] = struct.pack("<I", 0)  # Caps2

    return bytes(header)


@pytest.fixture
def bc7_dds_data(valid_dds_data):
    """Create DDS with BC7 format."""
    data = bytearray(valid_dds_data)
    # Change FourCC to DX10
    data[84:88] = b"DX10"
    return bytes(data)


@pytest.fixture
def odd_dimension_dds_data(valid_dds_data):
    """Create DDS with odd dimensions."""
    data = bytearray(valid_dds_data)
    # Set odd dimensions
    data[12:16] = struct.pack("<I", 1023)  # Height
    data[16:20] = struct.pack("<I", 2047)  # Width
    return bytes(data)


class TestDDSInfo:
    """Test DDSInfo data class."""

    def test_is_power_of_2(self):
        """Test power of 2 dimension checking."""
        info = DDSInfo(width=1024, height=512)
        assert info.is_power_of_2 is True

        info = DDSInfo(width=1023, height=512)
        assert info.is_power_of_2 is False

        info = DDSInfo(width=2048, height=2048)
        assert info.is_power_of_2 is True

    def test_is_bc_compatible(self):
        """Test BC compression compatibility checking."""
        info = DDSInfo(width=256, height=256)
        assert info.is_bc_compatible is True

        info = DDSInfo(width=255, height=256)
        assert info.is_bc_compatible is False

        info = DDSInfo(width=1024, height=1024)
        assert info.is_bc_compatible is True

    def test_aspect_ratio(self):
        """Test aspect ratio calculation."""
        info = DDSInfo(width=1920, height=1080)
        assert pytest.approx(info.aspect_ratio, 0.01) == 1.78

        info = DDSInfo(width=1024, height=1024)
        assert info.aspect_ratio == 1.0

        info = DDSInfo(width=100, height=0)
        assert info.aspect_ratio == 0

    def test_total_pixels(self):
        """Test total pixel calculation with mipmaps."""
        # No mipmaps
        info = DDSInfo(width=256, height=256, mipmap_count=1)
        assert info.total_pixels == 256 * 256

        # With mipmaps (256x256 + 128x128 + 64x64 + ...)
        info = DDSInfo(width=256, height=256, mipmap_count=9)
        # Calculate expected: sum of 256^2, 128^2, 64^2, 32^2, 16^2, 8^2, 4^2, 2^2, 1^2
        expected = sum([(256 >> i) ** 2 for i in range(9)])
        assert info.total_pixels == expected


class TestEnhancedDDSAnalyzer:
    """Test EnhancedDDSAnalyzer class."""

    def test_analyze_manual_valid_dds(self, analyzer, valid_dds_data, tmp_path):
        """Test manual parsing of valid DDS file."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        info = analyzer.analyze_file(dds_file)

        assert info is not None
        assert info.width == 2048
        assert info.height == 1024
        assert info.format_fourcc == "DXT5"
        assert info.is_compressed is True
        assert info.pixel_format == "BC3/DXT5 (8bpp, interpolated alpha)"

    def test_analyze_manual_dx10_dds(self, analyzer, bc7_dds_data, tmp_path):
        """Test parsing of DX10 extended header DDS."""
        dds_file = tmp_path / "test_bc7.dds"
        dds_file.write_bytes(bc7_dds_data)

        info = analyzer.analyze_file(dds_file)

        assert info is not None
        assert info.is_dx10 is True
        assert info.pixel_format == "DX10 Extended Format"

    def test_analyze_invalid_file(self, analyzer, tmp_path):
        """Test handling of invalid DDS file."""
        # Too small file
        dds_file = tmp_path / "small.dds"
        dds_file.write_bytes(b"INVALID")

        info = analyzer.analyze_file(dds_file)
        assert info is None

        # Wrong magic
        dds_file = tmp_path / "wrong_magic.dds"
        dds_file.write_bytes(b"WRONG" + b"\x00" * 124)

        info = analyzer.analyze_file(dds_file)
        assert info is None

    def test_validate_for_game_fallout4(self, analyzer):
        """Test Fallout 4 specific validation."""
        # Valid texture
        info = DDSInfo(width=2048, height=2048, format_fourcc="DXT5", is_compressed=True)
        issues = analyzer.validate_for_game(info, "Fallout4")
        assert len(issues) == 0

        # Non-power-of-2 with mipmaps
        info = DDSInfo(width=1023, height=1023, mipmap_count=5, is_compressed=True)
        issues = analyzer.validate_for_game(info, "Fallout4")
        assert any("Non-power-of-2" in issue for issue in issues)
        assert any("multiple of 4" in issue for issue in issues)

        # Too large for Fallout 4
        info = DDSInfo(width=8192, height=8192)
        issues = analyzer.validate_for_game(info, "Fallout4")
        assert any("4096" in issue for issue in issues)

        # DXT1 with alpha warning
        info = DDSInfo(width=1024, height=1024, format_fourcc="DXT1", has_alpha=True, is_compressed=True)
        issues = analyzer.validate_for_game(info, "Fallout4")
        assert any("DXT1 with alpha" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_analyze_file_async(self, analyzer, valid_dds_data, tmp_path):
        """Test async file analysis."""
        dds_file = tmp_path / "async_test.dds"
        dds_file.write_bytes(valid_dds_data)

        info = await analyzer.analyze_file_async(dds_file)

        assert info is not None
        assert info.width == 2048
        assert info.height == 1024


class TestIntegration:
    """Test integration with DDSProcessor."""

    @pytest.mark.asyncio
    async def test_processor_with_enhanced_analyzer(self, valid_dds_data, tmp_path):
        """Test DDSProcessor using enhanced analyzer."""
        from ClassicLib.ScanGame.core import DDSProcessor

        # Create test files
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()
        textures_dir = mod_dir / "textures"
        textures_dir.mkdir()

        valid_dds = textures_dir / "valid.dds"
        valid_dds.write_bytes(valid_dds_data)

        # Create DDS with odd dimensions
        odd_dds_data = bytearray(valid_dds_data)
        odd_dds_data[12:16] = struct.pack("<I", 1023)  # Odd height
        odd_dds = textures_dir / "odd.dds"
        odd_dds.write_bytes(bytes(odd_dds_data))

        # Setup processor with enhanced mode
        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore, use_enhanced=False)  # Test basic mode

        # Test batch checking
        dds_files = [(valid_dds, mod_dir), (odd_dds, mod_dir)]
        issue_lists = {"tex_dims": []}
        issue_locks = {"tex_dims": asyncio.Lock()}

        await processor.check_dds_batch_async(dds_files, issue_lists, issue_locks)

        # Should find multiple issues:
        # 1. valid.dds: No mipmaps
        # 2. odd.dds: Non-power-of-2
        # 3. odd.dds: Invalid BC dimensions
        # 4. odd.dds: No mipmaps
        assert len(issue_lists["tex_dims"]) == 4
        assert any("odd.dds" in issue for issue in issue_lists["tex_dims"])
        assert any("valid.dds" in issue for issue in issue_lists["tex_dims"])

    def test_get_analyzer_factory(self):
        """Test analyzer factory function."""
        analyzer = get_analyzer()
        assert isinstance(analyzer, EnhancedDDSAnalyzer)

    def test_analyze_dds_convenience_function(self, valid_dds_data, tmp_path):
        """Test convenience function for single file analysis."""
        dds_file = tmp_path / "convenience.dds"
        dds_file.write_bytes(valid_dds_data)

        info = analyze_dds(dds_file)

        assert info is not None
        assert info.width == 2048
        assert info.height == 1024


@pytest.mark.unit
class TestLibraryFallback:
    """Test behavior when optional libraries are available/unavailable."""

    def test_library_fallback_behavior(self, valid_dds_data, tmp_path):
        """Test that analyzer falls back to manual parsing when libraries unavailable."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        # Test with libraries disabled
        analyzer = EnhancedDDSAnalyzer(use_libraries=False)
        info = analyzer.analyze_file(dds_file)

        # Should still work with manual parsing
        assert info is not None
        assert info.width == 2048
        assert info.height == 1024

    def test_analyzer_with_nonexistent_file(self):
        """Test analyzer handles non-existent files gracefully."""
        analyzer = EnhancedDDSAnalyzer()
        info = analyzer.analyze_file(Path("/nonexistent/file.dds"))
        assert info is None

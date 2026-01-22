"""Unit tests for DDS texture file processor.

This module tests the DDSProcessor class which provides multi-strategy
DDS validation including Rust-accelerated parsing, enhanced analyzer,
and mmap-based fallback.
"""

import asyncio
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.ScanGame.core.dds_processor import DDSProcessor

# Note: DDS fixtures (valid_dds_data, bc7_dds_data, odd_dimension_dds_data)
# are provided by tests/fixtures/scanlog_fixtures.py via the root conftest.py


@pytest.mark.unit
class TestDDSProcessorInit:
    """Test DDSProcessor initialization."""

    def test_init_with_semaphore(self) -> None:
        """Test basic initialization with semaphore."""
        semaphore = asyncio.Semaphore(5)
        processor = DDSProcessor(semaphore)

        assert processor.dds_read_semaphore is semaphore
        assert processor.use_enhanced is False
        assert processor.analyzer is None

    def test_init_with_enhanced_disabled(self) -> None:
        """Test initialization with enhanced mode explicitly disabled."""
        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore, use_enhanced=False)

        assert processor.use_enhanced is False
        assert processor.analyzer is None

    def test_init_with_enhanced_enabled_and_available(self) -> None:
        """Test initialization with enhanced mode when analyzer is available."""
        from ClassicLib.ScanGame.core.dds_analyzer import EnhancedDDSAnalyzer

        semaphore = asyncio.Semaphore(1)
        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_ANALYZER", True):
            with patch(
                "ClassicLib.ScanGame.core.dds_processor._RuntimeEnhancedDDSAnalyzer",
                EnhancedDDSAnalyzer,
            ):
                processor = DDSProcessor(semaphore, use_enhanced=True)

        assert processor.use_enhanced is True
        assert processor.analyzer is not None

    def test_init_with_enhanced_enabled_but_unavailable(self) -> None:
        """Test initialization with enhanced mode when analyzer is unavailable."""
        semaphore = asyncio.Semaphore(1)
        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_ANALYZER", False):
            processor = DDSProcessor(semaphore, use_enhanced=True)

        assert processor.use_enhanced is False
        assert processor.analyzer is None


@pytest.mark.unit
class TestReadDDSHeaderMmap:
    """Test mmap-based DDS header reading."""

    def test_read_valid_dds_header(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test reading a valid DDS header with mmap."""
        dds_file = tmp_path / "valid.dds"
        dds_file.write_bytes(valid_dds_data)

        result = DDSProcessor.read_dds_header_mmap(dds_file)

        assert result is not None
        width, height = result
        # valid_dds_data has 1024x2048 (swapped in header: height first, then width)
        assert width == 1024
        assert height == 2048

    def test_read_file_too_small(self, tmp_path: Path) -> None:
        """Test reading a file that is too small to be a valid DDS."""
        small_file = tmp_path / "small.dds"
        small_file.write_bytes(b"DDS " + b"\x00" * 10)  # Only 14 bytes

        result = DDSProcessor.read_dds_header_mmap(small_file)

        assert result is None

    def test_read_invalid_magic(self, tmp_path: Path) -> None:
        """Test reading a file without DDS magic number."""
        invalid_file = tmp_path / "invalid.dds"
        invalid_file.write_bytes(b"NOTD" + b"\x00" * 20)

        result = DDSProcessor.read_dds_header_mmap(invalid_file)

        assert result is None

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        """Test reading a non-existent file."""
        nonexistent = tmp_path / "nonexistent.dds"

        result = DDSProcessor.read_dds_header_mmap(nonexistent)

        assert result is None

    def test_read_odd_dimensions(self, odd_dimension_dds_data: bytes, tmp_path: Path) -> None:
        """Test reading DDS with odd dimensions."""
        dds_file = tmp_path / "odd.dds"
        dds_file.write_bytes(odd_dimension_dds_data)

        result = DDSProcessor.read_dds_header_mmap(dds_file)

        assert result is not None
        width, height = result
        # The odd_dimension_dds_data fixture sets bytes 12-16 to 1023 and 16-20 to 2047
        # mmap reads 12-16 as width and 16-20 as height
        assert width == 1023
        assert height == 2047


@pytest.mark.unit
class TestReadDDSHeaderRust:
    """Test Rust-based DDS header reading."""

    def test_read_rust_unavailable(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test that method returns None when Rust DDS is unavailable."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            result = DDSProcessor.read_dds_header_rust(dds_file)

        assert result is None

    def test_read_rust_available_valid_file(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test Rust DDS reading with valid file when Rust is available."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        # Create mock DDSHeader
        mock_header = MagicMock()
        mock_header.width = 1024
        mock_header.height = 2048

        mock_dds_header_class = MagicMock()
        mock_dds_header_class.from_bytes.return_value = mock_header

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch(
                "ClassicLib.ScanGame.core.dds_processor._RuntimeRustDDSHeader",
                mock_dds_header_class,
            ):
                result = DDSProcessor.read_dds_header_rust(dds_file)

        assert result is mock_header
        mock_dds_header_class.from_bytes.assert_called_once()

    def test_read_rust_file_error(self, tmp_path: Path) -> None:
        """Test Rust DDS reading when file cannot be read."""
        nonexistent = tmp_path / "nonexistent.dds"

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            result = DDSProcessor.read_dds_header_rust(nonexistent)

        assert result is None

    def test_read_rust_parse_error(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test Rust DDS reading when parsing fails."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_dds_header_class = MagicMock()
        mock_dds_header_class.from_bytes.side_effect = ValueError("Parse error")

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch(
                "ClassicLib.ScanGame.core.dds_processor._RuntimeRustDDSHeader",
                mock_dds_header_class,
            ):
                result = DDSProcessor.read_dds_header_rust(dds_file)

        assert result is None


@pytest.mark.unit
class TestValidateDDSForGame:
    """Test multi-strategy DDS validation."""

    def test_validate_with_rust_valid_texture(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test validation using Rust parser with valid texture."""
        dds_file = tmp_path / "valid.dds"
        dds_file.write_bytes(valid_dds_data)

        # Create mock header with valid texture properties
        mock_header = MagicMock()
        mock_header.width = 1024
        mock_header.height = 1024
        mock_header.is_reasonable_size.return_value = True
        mock_header.is_bc_compressed.return_value = True
        mock_header.has_valid_bc_dimensions.return_value = True
        mock_header.has_power_of_2_dimensions.return_value = True
        mock_header.has_mipmaps.return_value = True

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(DDSProcessor, "read_dds_header_rust", return_value=mock_header):
                issues = processor.validate_dds_for_game(dds_file)

        assert issues == []

    def test_validate_with_rust_unusual_size(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test validation detects unusual texture size."""
        dds_file = tmp_path / "unusual.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_header = MagicMock()
        mock_header.width = 32000
        mock_header.height = 100
        mock_header.is_reasonable_size.return_value = False
        mock_header.is_bc_compressed.return_value = False
        mock_header.has_power_of_2_dimensions.return_value = False
        mock_header.has_mipmaps.return_value = True

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(DDSProcessor, "read_dds_header_rust", return_value=mock_header):
                issues = processor.validate_dds_for_game(dds_file)

        assert any("Unusual texture size" in issue for issue in issues)
        assert any("Non-power-of-2" in issue for issue in issues)

    def test_validate_with_rust_bc_invalid_dimensions(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test validation detects BC compression with invalid dimensions."""
        dds_file = tmp_path / "bc_invalid.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_header = MagicMock()
        mock_header.width = 1023
        mock_header.height = 1023
        mock_header.is_reasonable_size.return_value = True
        mock_header.is_bc_compressed.return_value = True
        mock_header.has_valid_bc_dimensions.return_value = False
        mock_header.has_power_of_2_dimensions.return_value = False
        mock_header.has_mipmaps.return_value = True

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(DDSProcessor, "read_dds_header_rust", return_value=mock_header):
                issues = processor.validate_dds_for_game(dds_file)

        assert any("BC-compressed texture has invalid dimensions" in issue for issue in issues)

    def test_validate_with_rust_no_mipmaps(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test validation detects missing mipmaps."""
        dds_file = tmp_path / "no_mipmaps.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_header = MagicMock()
        mock_header.width = 1024
        mock_header.height = 1024
        mock_header.is_reasonable_size.return_value = True
        mock_header.is_bc_compressed.return_value = False
        mock_header.has_power_of_2_dimensions.return_value = True
        mock_header.has_mipmaps.return_value = False

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(DDSProcessor, "read_dds_header_rust", return_value=mock_header):
                issues = processor.validate_dds_for_game(dds_file)

        assert any("No mipmaps" in issue for issue in issues)

    def test_validate_with_rust_very_large(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test validation detects very large textures."""
        dds_file = tmp_path / "large.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_header = MagicMock()
        mock_header.width = 8192
        mock_header.height = 8192
        mock_header.is_reasonable_size.return_value = True
        mock_header.is_bc_compressed.return_value = False
        mock_header.has_power_of_2_dimensions.return_value = True
        mock_header.has_mipmaps.return_value = True

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(DDSProcessor, "read_dds_header_rust", return_value=mock_header):
                issues = processor.validate_dds_for_game(dds_file)

        assert any("Very large texture" in issue for issue in issues)

    def test_validate_fallback_to_analyzer(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test validation falls back to enhanced analyzer."""
        dds_file = tmp_path / "analyzer.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_analyzer = MagicMock()
        mock_info = MagicMock()
        mock_analyzer.analyze_file.return_value = mock_info
        mock_analyzer.validate_for_game.return_value = ["Test issue from analyzer"]

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)
        processor.analyzer = mock_analyzer

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            issues = processor.validate_dds_for_game(dds_file)

        assert issues == ["Test issue from analyzer"]
        mock_analyzer.analyze_file.assert_called_once_with(dds_file)
        mock_analyzer.validate_for_game.assert_called_once_with(mock_info, "Fallout4")

    def test_validate_fallback_to_mmap(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test validation falls back to mmap-based validation."""
        dds_file = tmp_path / "mmap.dds"
        dds_file.write_bytes(valid_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            issues = processor.validate_dds_for_game(dds_file)

        # valid_dds_data has 1024x2048 which are both even and ≤4096
        assert issues == []

    def test_validate_mmap_odd_dimensions(self, odd_dimension_dds_data: bytes, tmp_path: Path) -> None:
        """Test mmap validation detects odd dimensions."""
        dds_file = tmp_path / "odd.dds"
        dds_file.write_bytes(odd_dimension_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            issues = processor.validate_dds_for_game(dds_file)

        assert any("Non-even dimensions" in issue for issue in issues)

    def test_validate_mmap_large_dimensions(self, tmp_path: Path) -> None:
        """Test mmap validation detects large dimensions."""
        # Create DDS with large dimensions
        header = bytearray(128)
        header[0:4] = b"DDS "
        header[4:8] = struct.pack("<I", 124)  # dwSize
        header[12:16] = struct.pack("<I", 8192)  # height (large)
        header[16:20] = struct.pack("<I", 8192)  # width (large)

        dds_file = tmp_path / "large.dds"
        dds_file.write_bytes(bytes(header))

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            issues = processor.validate_dds_for_game(dds_file)

        assert any("Large texture dimensions" in issue for issue in issues)

    def test_validate_unreadable_header(self, tmp_path: Path) -> None:
        """Test validation when DDS header cannot be read."""
        invalid_file = tmp_path / "invalid.dds"
        invalid_file.write_bytes(b"NOT_A_DDS_FILE")

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            issues = processor.validate_dds_for_game(invalid_file)

        assert issues == ["Unable to read DDS header"]


@pytest.mark.unit
class TestGetDetailedInfo:
    """Test detailed DDS info retrieval."""

    def test_get_detailed_info_with_analyzer(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test getting detailed info when analyzer is available."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_analyzer = MagicMock()
        mock_info = MagicMock()
        mock_analyzer.analyze_file.return_value = mock_info

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)
        processor.analyzer = mock_analyzer

        result = processor.get_detailed_info(dds_file)

        assert result is mock_info
        mock_analyzer.analyze_file.assert_called_once_with(dds_file)

    def test_get_detailed_info_without_analyzer(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test getting detailed info when analyzer is not available."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        result = processor.get_detailed_info(dds_file)

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetDetailedInfoAsync:
    """Test async detailed DDS info retrieval."""

    async def test_get_detailed_info_async_with_analyzer(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test async detailed info retrieval with analyzer."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        mock_analyzer = MagicMock()
        mock_info = MagicMock()

        async def mock_analyze_async(_: Path) -> MagicMock:
            return mock_info

        mock_analyzer.analyze_file_async = mock_analyze_async

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)
        processor.analyzer = mock_analyzer

        result = await processor.get_detailed_info_async(dds_file)

        assert result is mock_info

    async def test_get_detailed_info_async_without_analyzer(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test async detailed info retrieval without analyzer."""
        dds_file = tmp_path / "test.dds"
        dds_file.write_bytes(valid_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        result = await processor.get_detailed_info_async(dds_file)

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestProcessSingleDDSFile:
    """Test single DDS file processing."""

    async def test_process_valid_file_no_issues(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test processing a valid DDS file with no issues."""
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()
        dds_file = mod_dir / "textures" / "test.dds"
        dds_file.parent.mkdir(parents=True)
        dds_file.write_bytes(valid_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        # Mock Rust validation returning no issues
        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(processor, "validate_dds_for_game", return_value=[]):
                issues = await processor._process_single_dds_file(dds_file, mod_dir)

        assert issues == []

    async def test_process_file_with_rust_issues(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test processing a DDS file that has issues detected by Rust."""
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()
        dds_file = mod_dir / "textures" / "test.dds"
        dds_file.parent.mkdir(parents=True)
        dds_file.write_bytes(valid_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(
                processor,
                "validate_dds_for_game",
                return_value=["No mipmaps", "Large texture"],
            ):
                issues = await processor._process_single_dds_file(dds_file, mod_dir)

        assert len(issues) == 2
        assert all("TestMod" in issue for issue in issues)
        assert all("textures\\test.dds" in issue for issue in issues)

    async def test_process_file_with_mmap_fallback(self, odd_dimension_dds_data: bytes, tmp_path: Path) -> None:
        """Test processing falls back to mmap when Rust unavailable."""
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()
        dds_file = mod_dir / "textures" / "odd.dds"
        dds_file.parent.mkdir(parents=True)
        dds_file.write_bytes(odd_dimension_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            issues = await processor._process_single_dds_file(dds_file, mod_dir)

        # Odd dimensions should be detected via mmap fallback
        assert len(issues) == 1
        assert "TestMod" in issues[0]


@pytest.mark.unit
@pytest.mark.asyncio
class TestCheckDDSBatchAsync:
    """Test batch DDS checking."""

    async def test_batch_check_no_issues(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test batch check with valid files produces no issues."""
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()
        dds_file = mod_dir / "texture.dds"
        dds_file.write_bytes(valid_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        dds_files = [(dds_file, mod_dir)]
        issue_lists: dict[str, set[str]] = {"tex_dims": set()}
        issue_locks = {"tex_dims": asyncio.Lock()}

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(processor, "validate_dds_for_game", return_value=[]):
                await processor.check_dds_batch_async(dds_files, issue_lists, issue_locks)

        assert len(issue_lists["tex_dims"]) == 0

    async def test_batch_check_with_issues(self, odd_dimension_dds_data: bytes, tmp_path: Path) -> None:
        """Test batch check collects issues from files."""
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()
        dds_file = mod_dir / "odd_texture.dds"
        dds_file.write_bytes(odd_dimension_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        dds_files = [(dds_file, mod_dir)]
        issue_lists: dict[str, set[str]] = {"tex_dims": set()}
        issue_locks = {"tex_dims": asyncio.Lock()}

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            await processor.check_dds_batch_async(dds_files, issue_lists, issue_locks)

        assert len(issue_lists["tex_dims"]) > 0
        assert any("TestMod" in issue for issue in issue_lists["tex_dims"])

    async def test_batch_check_multiple_files(self, valid_dds_data: bytes, odd_dimension_dds_data: bytes, tmp_path: Path) -> None:
        """Test batch check processes multiple files."""
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()

        valid_file = mod_dir / "valid.dds"
        valid_file.write_bytes(valid_dds_data)

        odd_file = mod_dir / "odd.dds"
        odd_file.write_bytes(odd_dimension_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        dds_files = [(valid_file, mod_dir), (odd_file, mod_dir)]
        issue_lists: dict[str, set[str]] = {"tex_dims": set()}
        issue_locks = {"tex_dims": asyncio.Lock()}

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", False):
            await processor.check_dds_batch_async(dds_files, issue_lists, issue_locks)

        # Only the odd file should have issues
        assert any("odd.dds" in issue for issue in issue_lists["tex_dims"])

    async def test_batch_check_respects_semaphore(self, valid_dds_data: bytes, tmp_path: Path) -> None:
        """Test that batch check respects semaphore for concurrency control."""
        mod_dir = tmp_path / "TestMod"
        mod_dir.mkdir()
        dds_file = mod_dir / "texture.dds"
        dds_file.write_bytes(valid_dds_data)

        semaphore = asyncio.Semaphore(1)
        processor = DDSProcessor(semaphore)

        dds_files = [(dds_file, mod_dir)]
        issue_lists: dict[str, set[str]] = {"tex_dims": set()}
        issue_locks = {"tex_dims": asyncio.Lock()}

        # Acquire semaphore before call - should block if check_dds_batch_async
        # properly acquires the semaphore
        acquired = semaphore.locked()
        assert not acquired  # Semaphore should be free initially

        with patch("ClassicLib.ScanGame.core.dds_processor.HAS_RUST_DDS", True):
            with patch.object(processor, "validate_dds_for_game", return_value=[]):
                await processor.check_dds_batch_async(dds_files, issue_lists, issue_locks)

        # Semaphore should be released after call
        assert not semaphore.locked()

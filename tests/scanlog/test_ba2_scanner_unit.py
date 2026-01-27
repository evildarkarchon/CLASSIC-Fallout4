"""Unit tests for BA2ArchiveScanner component.

This module contains unit tests for the BA2ArchiveScanner class which handles
BA2 archive scanning, header validation, BSArch subprocess execution, and
concurrent archive processing.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, ARG002
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ClassicLib.scanning.game.core.ba2_scanner import BA2ArchiveScanner


@pytest.fixture
def ba2_scanner():
    """Create a BA2ArchiveScanner instance with test fixtures."""
    semaphore = asyncio.Semaphore(4)
    executor = ThreadPoolExecutor(max_workers=2)
    scanner = BA2ArchiveScanner(semaphore, executor)
    yield scanner
    executor.shutdown(wait=False)


@pytest.fixture
def mock_bsarch_path(tmp_path):
    """Create a mock BSArch executable path."""
    bsarch = tmp_path / "BSArch.exe"
    bsarch.touch()
    return bsarch


@pytest.fixture
def sample_ba2_files(tmp_path):
    """Create sample BA2 files for testing."""
    ba2_dir = tmp_path / "mods"
    ba2_dir.mkdir()

    # Create texture BA2
    texture_ba2 = ba2_dir / "textures.ba2"
    texture_ba2.write_bytes(b"BTDX\x00\x00\x00\x00DX10")

    # Create general BA2
    general_ba2 = ba2_dir / "main.ba2"
    general_ba2.write_bytes(b"BTDX\x00\x00\x00\x00GNRL")

    # Create invalid BA2
    invalid_ba2 = ba2_dir / "invalid.ba2"
    invalid_ba2.write_bytes(b"INVALID_HEADER")

    return {
        "dir": ba2_dir,
        "texture": texture_ba2,
        "general": general_ba2,
        "invalid": invalid_ba2,
    }


class TestBA2ArchiveScannerInit:
    """Tests for BA2ArchiveScanner initialization."""

    @pytest.mark.unit
    def test_init_stores_semaphore_and_executor(self):
        """Test that __init__ stores semaphore and executor."""
        semaphore = asyncio.Semaphore(4)
        executor = ThreadPoolExecutor(max_workers=2)

        scanner = BA2ArchiveScanner(semaphore, executor)

        assert scanner.process_semaphore is semaphore
        assert scanner.walk_executor is executor
        executor.shutdown(wait=False)


class TestFindBa2FilesAsync:
    """Tests for find_ba2_files_async method."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_ba2_files_returns_all_ba2s(self, ba2_scanner, sample_ba2_files):
        """Test that find_ba2_files_async returns all BA2 files."""
        result = await ba2_scanner.find_ba2_files_async(sample_ba2_files["dir"])

        # Should find 3 BA2 files
        assert len(result) == 3
        filenames = [f[1] for f in result]
        assert "textures.ba2" in filenames
        assert "main.ba2" in filenames
        assert "invalid.ba2" in filenames

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_ba2_files_excludes_prp_main(self, ba2_scanner, tmp_path):
        """Test that prp - main.ba2 is excluded from results."""
        ba2_dir = tmp_path / "mods"
        ba2_dir.mkdir()

        # Create excluded file
        excluded = ba2_dir / "prp - main.ba2"
        excluded.write_bytes(b"BTDX\x00\x00\x00\x00GNRL")

        # Create regular file
        regular = ba2_dir / "other.ba2"
        regular.write_bytes(b"BTDX\x00\x00\x00\x00GNRL")

        result = await ba2_scanner.find_ba2_files_async(ba2_dir)

        filenames = [f[1] for f in result]
        assert "other.ba2" in filenames
        assert "prp - main.ba2" not in filenames

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_ba2_files_empty_dir(self, ba2_scanner, tmp_path):
        """Test find_ba2_files_async with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = await ba2_scanner.find_ba2_files_async(empty_dir)

        assert result == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_ba2_files_nonexistent_dir(self, ba2_scanner, tmp_path):
        """Test find_ba2_files_async with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        result = await ba2_scanner.find_ba2_files_async(nonexistent)

        assert result == []


class TestReadBa2HeaderAsync:
    """Tests for read_ba2_header_async static method."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_read_header_dx10_format(self, sample_ba2_files):
        """Test reading DX10 format header."""
        header = await BA2ArchiveScanner.read_ba2_header_async(sample_ba2_files["texture"], "textures.ba2")

        assert header is not None
        assert header[:4] == b"BTDX"
        assert header[8:] == b"DX10"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_read_header_gnrl_format(self, sample_ba2_files):
        """Test reading GNRL format header."""
        header = await BA2ArchiveScanner.read_ba2_header_async(sample_ba2_files["general"], "main.ba2")

        assert header is not None
        assert header[:4] == b"BTDX"
        assert header[8:] == b"GNRL"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_read_header_invalid_format(self, sample_ba2_files):
        """Test reading invalid format header."""
        header = await BA2ArchiveScanner.read_ba2_header_async(sample_ba2_files["invalid"], "invalid.ba2")

        assert header is not None
        assert header[:4] != b"BTDX"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_read_header_file_not_found(self, tmp_path):
        """Test reading header from nonexistent file."""
        nonexistent = tmp_path / "nonexistent.ba2"

        with patch("ClassicLib.scanning.game.core.ba2_scanner.msg_warning") as mock_warning:
            header = await BA2ArchiveScanner.read_ba2_header_async(nonexistent, "nonexistent.ba2")

            assert header is None
            mock_warning.assert_called_with("Failed to read file: nonexistent.ba2")


class TestValidateBa2Header:
    """Tests for validate_ba2_header static method."""

    @pytest.mark.unit
    def test_validate_valid_dx10_header(self):
        """Test validation of valid DX10 header."""
        header = b"BTDX\x00\x00\x00\x00DX10"
        issues: dict[str, set[str]] = {"ba2_frmt": set()}

        result = BA2ArchiveScanner.validate_ba2_header(header, "test.ba2", issues)

        assert result is True
        assert len(issues["ba2_frmt"]) == 0

    @pytest.mark.unit
    def test_validate_valid_gnrl_header(self):
        """Test validation of valid GNRL header."""
        header = b"BTDX\x00\x00\x00\x00GNRL"
        issues: dict[str, set[str]] = {"ba2_frmt": set()}

        result = BA2ArchiveScanner.validate_ba2_header(header, "test.ba2", issues)

        assert result is True
        assert len(issues["ba2_frmt"]) == 0

    @pytest.mark.unit
    def test_validate_invalid_signature(self):
        """Test validation fails with invalid signature."""
        header = b"XXXX\x00\x00\x00\x00DX10"
        issues: dict[str, set[str]] = {"ba2_frmt": set()}

        result = BA2ArchiveScanner.validate_ba2_header(header, "bad.ba2", issues)

        assert result is False
        assert len(issues["ba2_frmt"]) == 1
        assert "bad.ba2" in list(issues["ba2_frmt"])[0]

    @pytest.mark.unit
    def test_validate_invalid_format_type(self):
        """Test validation fails with invalid format type."""
        header = b"BTDX\x00\x00\x00\x00XXXX"
        issues: dict[str, set[str]] = {"ba2_frmt": set()}

        result = BA2ArchiveScanner.validate_ba2_header(header, "bad.ba2", issues)

        assert result is False
        assert len(issues["ba2_frmt"]) == 1


class TestProcessTextureBa2Async:
    """Tests for process_texture_ba2_async method."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_texture_success(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test successful texture BA2 processing."""
        # Mock BSArch subprocess output
        # Format: 4 header blocks (separated by \n\n), then file blocks
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        bsarch_output = b"Header1\n\nHeader2\n\nHeader3\n\nHeader4\n\ntest.dds\nExt: dds\nWidth: 1024 Height: 1024 Misc: info\nmore"
        mock_proc.communicate = AsyncMock(return_value=(bsarch_output, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ba2_scanner.process_texture_ba2_async(sample_ba2_files["texture"], "textures.ba2", mock_bsarch_path)

        assert "tex_dims" in result
        assert "tex_frmt" in result
        assert len(result["tex_dims"]) == 0
        assert len(result["tex_frmt"]) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_texture_odd_dimensions(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test detection of odd texture dimensions."""
        # Mock BSArch output with odd dimensions
        # Format: 4 header blocks (separated by \n\n), then file blocks
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        bsarch_output = b"Header1\n\nHeader2\n\nHeader3\n\nHeader4\n\nodd.dds\nExt: dds\nWidth: 1023 Height: 512 Misc: info\nmore"
        mock_proc.communicate = AsyncMock(return_value=(bsarch_output, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ba2_scanner.process_texture_ba2_async(sample_ba2_files["texture"], "textures.ba2", mock_bsarch_path)

        assert len(result["tex_dims"]) == 1
        assert "1023x512" in list(result["tex_dims"])[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_texture_non_dds_format(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test detection of non-DDS texture format."""
        # Mock BSArch output with non-DDS texture
        # Format: 4 header blocks (separated by \n\n), then file blocks
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        bsarch_output = b"Header1\n\nHeader2\n\nHeader3\n\nHeader4\n\ntexture.png\nExt: png\nWidth: 1024 Height: 1024 Misc: info\nmore"
        mock_proc.communicate = AsyncMock(return_value=(bsarch_output, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ba2_scanner.process_texture_ba2_async(sample_ba2_files["texture"], "textures.ba2", mock_bsarch_path)

        assert len(result["tex_frmt"]) == 1
        assert "PNG" in list(result["tex_frmt"])[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_texture_bsarch_failure(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test handling of BSArch failure."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Error occurred"))

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("ClassicLib.scanning.game.core.ba2_scanner.msg_error") as mock_error,
        ):
            result = await ba2_scanner.process_texture_ba2_async(sample_ba2_files["texture"], "textures.ba2", mock_bsarch_path)

            assert len(result["tex_dims"]) == 0
            assert len(result["tex_frmt"]) == 0
            mock_error.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_texture_timeout(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test timeout handling for BSArch subprocess."""
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError())

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("ClassicLib.scanning.game.core.ba2_scanner.msg_error") as mock_error,
        ):
            result = await ba2_scanner.process_texture_ba2_async(sample_ba2_files["texture"], "textures.ba2", mock_bsarch_path)

            mock_error.assert_called_with("BSArch command timed out processing textures.ba2")
            mock_proc.kill.assert_called()
            assert len(result["tex_dims"]) == 0


class TestProcessGeneralBa2Async:
    """Tests for process_general_ba2_async method."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_general_success(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test successful general BA2 processing."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        # 15 lines of header then file list
        header_lines = "\n".join([f"header line {i}" for i in range(15)])
        mock_proc.communicate = AsyncMock(return_value=(f"{header_lines}\nscripts/test.pex\nmeshes/test.nif".encode(), b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ba2_scanner.process_general_ba2_async(sample_ba2_files["general"], "main.ba2", mock_bsarch_path, {})

        assert "snd_frmt" in result
        assert "xse_file" in result
        assert len(result["snd_frmt"]) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_general_detects_mp3(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test detection of MP3 sound files."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        header_lines = "\n".join([f"header line {i}" for i in range(15)])
        mock_proc.communicate = AsyncMock(return_value=(f"{header_lines}\nsounds/music.mp3".encode(), b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ba2_scanner.process_general_ba2_async(sample_ba2_files["general"], "main.ba2", mock_bsarch_path, {})

        assert len(result["snd_frmt"]) == 1
        assert "MP3" in list(result["snd_frmt"])[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_general_detects_xse_files(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test detection of XSE script files."""
        xse_scriptfiles = {"F4SE": {"test_plugin.dll"}}

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        header_lines = "\n".join([f"header line {i}" for i in range(15)])
        mock_proc.communicate = AsyncMock(return_value=(f"{header_lines}\nscripts\\f4se\\test_plugin.pex".encode(), b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ba2_scanner.process_general_ba2_async(sample_ba2_files["general"], "main.ba2", mock_bsarch_path, xse_scriptfiles)

        assert len(result["xse_file"]) == 1
        assert "main.ba2" in list(result["xse_file"])[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_general_timeout(self, ba2_scanner, sample_ba2_files, mock_bsarch_path):
        """Test timeout handling for general BA2 processing."""
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError())

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("ClassicLib.scanning.game.core.ba2_scanner.msg_error") as mock_error,
        ):
            result = await ba2_scanner.process_general_ba2_async(sample_ba2_files["general"], "main.ba2", mock_bsarch_path, {})

            mock_error.assert_called_with("BSArch command timed out processing main.ba2")
            mock_proc.kill.assert_called()


class TestProcessTextureBlock:
    """Tests for process_texture_block static method."""

    @pytest.mark.unit
    def test_process_valid_texture_block(self):
        """Test processing a valid texture block."""
        block = "textures/test.dds\nExt: dds\nWidth: 1024 Height: 1024 Misc: info\nmore data"
        issues: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        BA2ArchiveScanner.process_texture_block(block, "test.ba2", issues)

        assert len(issues["tex_frmt"]) == 0
        assert len(issues["tex_dims"]) == 0

    @pytest.mark.unit
    def test_process_odd_width_dimension(self):
        """Test detection of odd width dimension."""
        block = "textures/odd.dds\nExt: dds\nWidth: 1023 Height: 1024 Misc: info\nmore data"
        issues: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        BA2ArchiveScanner.process_texture_block(block, "test.ba2", issues)

        assert len(issues["tex_dims"]) == 1
        assert "1023x1024" in list(issues["tex_dims"])[0]

    @pytest.mark.unit
    def test_process_odd_height_dimension(self):
        """Test detection of odd height dimension."""
        block = "textures/odd.dds\nExt: dds\nWidth: 1024 Height: 1023 Misc: info\nmore data"
        issues: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        BA2ArchiveScanner.process_texture_block(block, "test.ba2", issues)

        assert len(issues["tex_dims"]) == 1
        assert "1024x1023" in list(issues["tex_dims"])[0]

    @pytest.mark.unit
    def test_process_non_dds_format(self):
        """Test detection of non-DDS texture format."""
        block = "textures/test.png\nExt: png\nWidth: 1024 Height: 1024 Misc: info\nmore data"
        issues: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        BA2ArchiveScanner.process_texture_block(block, "test.ba2", issues)

        assert len(issues["tex_frmt"]) == 1
        assert "PNG" in list(issues["tex_frmt"])[0]


class TestAnalyzeGeneralFiles:
    """Tests for analyze_general_files static method."""

    @pytest.mark.unit
    def test_analyze_detects_mp3(self):
        """Test detection of MP3 files."""
        files = ["sounds/music.mp3", "meshes/test.nif"]
        issues: dict[str, set[str]] = {"snd_frmt": set(), "xse_file": set()}

        BA2ArchiveScanner.analyze_general_files(files, "test.ba2", Path("/mods/test.ba2"), {}, issues)

        assert len(issues["snd_frmt"]) == 1
        assert "MP3" in list(issues["snd_frmt"])[0]

    @pytest.mark.unit
    def test_analyze_detects_m4a(self):
        """Test detection of M4A files."""
        files = ["sounds/voice.m4a"]
        issues: dict[str, set[str]] = {"snd_frmt": set(), "xse_file": set()}

        BA2ArchiveScanner.analyze_general_files(files, "test.ba2", Path("/mods/test.ba2"), {}, issues)

        assert len(issues["snd_frmt"]) == 1
        assert "M4A" in list(issues["snd_frmt"])[0]

    @pytest.mark.unit
    def test_analyze_detects_xse_scripts(self):
        """Test detection of XSE script files."""
        files = ["scripts\\f4se\\plugin.pex"]
        xse_scriptfiles = {"F4SE": set()}
        issues: dict[str, set[str]] = {"snd_frmt": set(), "xse_file": set()}

        BA2ArchiveScanner.analyze_general_files(files, "test.ba2", Path("/mods/test.ba2"), xse_scriptfiles, issues)

        assert len(issues["xse_file"]) == 1
        assert "test.ba2" in list(issues["xse_file"])[0]

    @pytest.mark.unit
    def test_analyze_excludes_workshop_framework(self):
        """Test that Workshop Framework XSE files are excluded."""
        files = ["scripts\\f4se\\plugin.pex"]
        xse_scriptfiles = {"F4SE": set()}
        issues: dict[str, set[str]] = {"snd_frmt": set(), "xse_file": set()}

        BA2ArchiveScanner.analyze_general_files(
            files,
            "test.ba2",
            Path("/mods/Workshop Framework/test.ba2"),
            xse_scriptfiles,
            issues,
        )

        assert len(issues["xse_file"]) == 0


class TestMergeScanResults:
    """Tests for merge_scan_results static method."""

    @pytest.mark.unit
    def test_merge_single_result(self):
        """Test merging a single result."""
        results = [{"tex_frmt": {"issue1"}, "tex_dims": {"dim1"}}]
        target: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        BA2ArchiveScanner.merge_scan_results(results, target)

        assert "issue1" in target["tex_frmt"]
        assert "dim1" in target["tex_dims"]

    @pytest.mark.unit
    def test_merge_multiple_results(self):
        """Test merging multiple results."""
        results = [
            {"tex_frmt": {"issue1"}, "tex_dims": {"dim1"}},
            {"tex_frmt": {"issue2"}, "tex_dims": {"dim2"}},
        ]
        target: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        BA2ArchiveScanner.merge_scan_results(results, target)

        assert len(target["tex_frmt"]) == 2
        assert len(target["tex_dims"]) == 2

    @pytest.mark.unit
    def test_merge_handles_exceptions(self):
        """Test that exceptions in results are handled gracefully."""
        results = [
            {"tex_frmt": {"issue1"}},
            ValueError("Test error"),  # Exception in results
            {"tex_frmt": {"issue2"}},
        ]
        target: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        with patch("ClassicLib.scanning.game.core.ba2_scanner.msg_error") as mock_error:
            BA2ArchiveScanner.merge_scan_results(results, target)  # type: ignore[arg-type]

            mock_error.assert_called()
            assert len(target["tex_frmt"]) == 2

    @pytest.mark.unit
    def test_merge_empty_results(self):
        """Test merging empty results."""
        results: list[dict[str, set[str]]] = []
        target: dict[str, set[str]] = {"tex_frmt": set(), "tex_dims": set()}

        BA2ArchiveScanner.merge_scan_results(results, target)

        assert len(target["tex_frmt"]) == 0
        assert len(target["tex_dims"]) == 0


class TestProcessBa2FilesAsync:
    """Tests for process_ba2_files_async method."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_multiple_files_concurrently(self, ba2_scanner, sample_ba2_files, mock_bsarch_path, message_handler):
        """Test processing multiple BA2 files concurrently."""
        ba2_files = [
            (sample_ba2_files["texture"], "textures.ba2"),
            (sample_ba2_files["general"], "main.ba2"),
        ]

        # Mock subprocess calls
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        header_lines = "\n".join([f"header line {i}" for i in range(15)])
        mock_proc.communicate = AsyncMock(return_value=(f"{header_lines}\nscripts/test.pex".encode(), b""))

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch.object(ba2_scanner, "read_ba2_header_async") as mock_read_header,
            patch.object(ba2_scanner, "validate_ba2_header", return_value=True),
        ):
            # Return appropriate headers based on file
            async def header_side_effect(path, filename):
                if "texture" in filename:
                    return b"BTDX\x00\x00\x00\x00DX10"
                return b"BTDX\x00\x00\x00\x00GNRL"

            mock_read_header.side_effect = header_side_effect

            results = await ba2_scanner.process_ba2_files_async(ba2_files, mock_bsarch_path, {})

        assert len(results) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_handles_task_exceptions(self, ba2_scanner, mock_bsarch_path, message_handler):
        """Test that exceptions during processing are handled."""
        ba2_files = [(Path("/nonexistent/file.ba2"), "file.ba2")]

        with patch.object(ba2_scanner, "read_ba2_header_async", side_effect=OSError("File not found")):
            with patch("ClassicLib.scanning.game.core.ba2_scanner.msg_error"):
                results = await ba2_scanner.process_ba2_files_async(ba2_files, mock_bsarch_path, {})

            # Exception should be caught and logged, empty results returned
            assert len(results) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_returns_empty_for_invalid_header(self, ba2_scanner, sample_ba2_files, mock_bsarch_path, message_handler):
        """Test that invalid headers return empty issues dict."""
        ba2_files = [(sample_ba2_files["invalid"], "invalid.ba2")]

        results = await ba2_scanner.process_ba2_files_async(ba2_files, mock_bsarch_path, {})

        # Should return one result dict with format error
        assert len(results) == 1
        assert len(results[0]["ba2_frmt"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

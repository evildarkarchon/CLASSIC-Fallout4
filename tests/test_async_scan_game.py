"""
Test suite for async implementations in ClassicLib.ScanGame.AsyncScanGame
"""

import asyncio
import sys
from contextlib import nullcontext
from unittest.mock import AsyncMock, patch

import pytest

# Import wrappers from CLASSIC_ScanGame since they're now defined there
import CLASSIC_ScanGame
import ClassicLib.MessageHandler

# Import for MessageHandler initialization
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.ScanGame.AsyncScanGame import (
    MAX_CONCURRENT_DDS_READS,
    MAX_CONCURRENT_LOG_READS,
    check_log_errors_async,
    check_log_errors_async_wrapper,
    scan_mods_archived_async,
    scan_mods_archived_async_wrapper,
    scan_mods_unpacked_async,
    scan_mods_unpacked_async_wrapper,
)


@pytest.fixture(autouse=True)
def init_message_handler_fixture():
    """Initialize MessageHandler for tests."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    # Clean up after test
    ClassicLib.MessageHandler._message_handler = None


@pytest.fixture
def mock_settings():
    """Mock YAML settings for tests."""
    # Patch yaml_settings in both places it might be imported
    with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml_cache:
        with patch("ClassicLib.ScanGame.ScanGameCore.yaml_settings") as mock_yaml_core:
            # Configure return values for different settings
            def yaml_side_effect(type_, yaml_key, setting_path, default=None):
                settings_map = {
                    "catch_log_errors": ["error", "warning", "critical"],
                    "exclude_log_files": ["ignore.log"],
                    "exclude_log_errors": ["ignorable error"],
                    "Mods_Warn.Mods_Path_Missing": "Mods path not configured",
                    "Mods_Warn.Mods_Path_Invalid": "Mods path does not exist",
                    "Mods_Warn.Mods_BSArch_Missing": "BSArch.exe not found",
                }
                return settings_map.get(setting_path, default)

            mock_yaml_cache.side_effect = yaml_side_effect
            mock_yaml_core.side_effect = yaml_side_effect
            yield mock_yaml_cache


@pytest.fixture
def mock_paths(tmp_path):
    """Create mock paths for testing."""
    # Create test directories
    mods_path = tmp_path / "Mods"
    mods_path.mkdir()

    logs_path = tmp_path / "Logs"
    logs_path.mkdir()

    bsarch_path = tmp_path / "CLASSIC Data"
    bsarch_path.mkdir()
    (bsarch_path / "BSArch.exe").touch()

    return {"mods": mods_path, "logs": logs_path, "bsarch": bsarch_path / "BSArch.exe", "tmp": tmp_path}


@pytest.fixture
def mock_scan_settings(mock_paths):
    """Mock get_scan_settings function."""
    with patch("CLASSIC_ScanGame.get_scan_settings") as mock_get:
        with patch("ClassicLib.ScanGame.ScanGameCore.ScanGameCore.get_scan_settings") as mock_core_get:
            return_val = (
                "F4SE",  # xse_acronym
                {"f4se_loader": "hash123"},  # xse_scriptfiles
                mock_paths["mods"],  # mod_path
            )
            mock_get.return_value = return_val
            mock_core_get.return_value = return_val
            yield mock_get


@pytest.fixture
def mock_issue_messages():
    """Mock get_issue_messages function."""
    with patch("CLASSIC_ScanGame.get_issue_messages") as mock_get:
        with patch("ClassicLib.ScanGame.ScanGameCore.ScanGameCore.get_issue_messages") as mock_core_get:
            return_val = {
                "ba2_frmt": ["[!] BA2 FORMAT ERRORS FOUND:\n"],
                "tex_dims": ["[!] TEXTURE DIMENSION ERRORS:\n"],
                "tex_frmt": ["[!] TEXTURE FORMAT ERRORS:\n"],
                "snd_frmt": ["[!] SOUND FORMAT ERRORS:\n"],
                "animdata": ["[!] ANIMATION DATA FOUND:\n"],
                "xse_file": ["[!] F4SE FILES FOUND:\n"],
                "previs": ["[!] PREVIS FILES FOUND:\n"],
                "cleanup": ["[!] CLEANUP FILES:\n"],
            }
            mock_get.return_value = return_val
            mock_core_get.return_value = return_val
            yield mock_get


@pytest.fixture
def mock_global_registry(mock_paths):
    """Mock GlobalRegistry."""
    with patch("ClassicLib.ScanGame.ScanGameCore.GlobalRegistry") as mock_gr_core:
        mock_gr_core.get_local_dir.return_value = mock_paths["tmp"]
        mock_gr_core.get_vr.return_value = ""
        yield mock_gr_core


class TestAsyncScanModsArchived:
    """Test cases for scan_mods_archived_async function."""

    @pytest.mark.asyncio
    async def test_scan_mods_archived_async_with_valid_ba2(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test scanning valid BA2 archives."""
        # Create test BA2 files
        ba2_file1 = mock_paths["mods"] / "test1.ba2"
        ba2_file2 = mock_paths["mods"] / "test2.ba2"

        # Write valid BA2 headers
        with open(ba2_file1, "wb") as f:
            f.write(b"BTDX\x00\x00\x00\x00DX10")  # Texture BA2
        with open(ba2_file2, "wb") as f:
            f.write(b"BTDX\x00\x00\x00\x00GNRL")  # General BA2

        # Mock subprocess for BSArch
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=("Header\n\n\n\n\nFile: test.dds\nExt: dds\nWidth: 1024 Height: 1024", ""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await scan_mods_archived_async()

        assert "RESULTS FROM ARCHIVED / BA2 FILES" in result
        assert mock_proc.communicate.called

    @pytest.mark.asyncio
    async def test_scan_mods_archived_async_with_invalid_ba2(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test scanning invalid BA2 archives."""
        # Create test BA2 file with invalid header
        ba2_file = mock_paths["mods"] / "invalid.ba2"
        with open(ba2_file, "wb") as f:
            f.write(b"INVALID_HEADER")

        result = await scan_mods_archived_async()

        assert "BA2 FORMAT ERRORS FOUND" in result
        assert "invalid.ba2" in result

    @pytest.mark.asyncio
    async def test_scan_mods_archived_async_concurrency_limit(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test that concurrency is limited by semaphore."""
        # Create multiple BA2 files
        ba2_files = []
        for i in range(10):
            ba2_file = mock_paths["mods"] / f"test{i}.ba2"
            with open(ba2_file, "wb") as f:
                f.write(b"BTDX\x00\x00\x00\x00DX10")
            ba2_files.append(ba2_file)

        # Track concurrent processes
        concurrent_count = 0
        max_concurrent = 0

        async def mock_subprocess(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)

            mock_proc = AsyncMock()
            mock_proc.returncode = 0

            async def simulate_communicate():
                await asyncio.sleep(0.1)
                return ("output", "")

            mock_proc.communicate = AsyncMock(side_effect=simulate_communicate)

            # Simulate process completion
            await asyncio.sleep(0.1)
            concurrent_count -= 1

            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess):
            await scan_mods_archived_async()

        # Verify concurrency was limited
        # Import the actual dynamic limit from ScanGameCore
        from ClassicLib.ScanGame.ScanGameCore import MAX_CONCURRENT_SUBPROCESSES as ACTUAL_LIMIT

        assert max_concurrent <= ACTUAL_LIMIT

    @pytest.mark.asyncio
    async def test_scan_mods_archived_async_timeout_handling(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test timeout handling for BSArch subprocess."""
        # Create test BA2 file
        ba2_file = mock_paths["mods"] / "timeout.ba2"
        with open(ba2_file, "wb") as f:
            f.write(b"BTDX\x00\x00\x00\x00DX10")

        # Mock subprocess that times out
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("ClassicLib.ScanGame.ScanGameCore.msg_error") as mock_error:
                result = await scan_mods_archived_async()

                # Verify timeout was handled
                mock_error.assert_called_with("BSArch command timed out processing timeout.ba2")


class TestAsyncCheckLogErrors:
    """Test cases for check_log_errors_async function."""

    @pytest.mark.asyncio
    async def test_check_log_errors_async_with_errors(self, mock_settings, mock_paths):
        """Test checking log files with errors."""
        # Create test log files
        log1 = mock_paths["logs"] / "test1.log"
        log2 = mock_paths["logs"] / "test2.log"
        log3 = mock_paths["logs"] / "crash-test.log"  # Should be ignored

        log1.write_text("Normal line\nERROR: Something went wrong\nAnother line")
        log2.write_text("WARNING: This is a warning\nNormal operation")
        log3.write_text("ERROR: Crash log should be ignored")

        result = await check_log_errors_async(mock_paths["logs"])

        assert "ERROR > ERROR: Something went wrong" in result
        assert "ERROR > WARNING: This is a warning" in result
        assert "Crash log should be ignored" not in result

    @pytest.mark.asyncio
    async def test_check_log_errors_async_concurrency(self, mock_settings, mock_paths):
        """Test concurrent log file processing."""
        # Create many log files
        for i in range(30):
            log_file = mock_paths["logs"] / f"test{i}.log"
            log_file.write_text(f"Log {i}\nERROR: Error in file {i}")

        # Track concurrent reads
        concurrent_reads = 0
        max_concurrent_reads = 0

        original_open = open

        def track_concurrent_open(*args, **kwargs):
            nonlocal concurrent_reads, max_concurrent_reads
            concurrent_reads += 1
            max_concurrent_reads = max(max_concurrent_reads, concurrent_reads)
            result = original_open(*args, **kwargs)
            concurrent_reads -= 1
            return result

        with patch("builtins.open", side_effect=track_concurrent_open):
            result = await check_log_errors_async(mock_paths["logs"])

        # Verify all errors were found
        for i in range(30):
            assert f"Error in file {i}" in result

        # Verify concurrency was limited
        assert max_concurrent_reads <= MAX_CONCURRENT_LOG_READS

    @pytest.mark.asyncio
    async def test_check_log_errors_async_with_unreadable_file(self, mock_settings, mock_paths):
        """Test handling of unreadable log files."""
        # Create a log file
        log_file = mock_paths["logs"] / "unreadable.log"
        log_file.write_text("Some content")

        # Mock both possible file reading methods to raise OSError
        with patch("ClassicLib.ScanGame.ScanGameCore.open_file_with_encoding", side_effect=OSError("Permission denied")):
            # Also mock the async read if it exists
            with patch("aiofiles.open", side_effect=OSError("Permission denied")) if "aiofiles" in str(sys.modules) else nullcontext():
                result = await check_log_errors_async(mock_paths["logs"])

                # Check for the error message (without emoji since test output may vary)
                assert "Unable to scan this log file" in result or "ERROR" in result
                assert "unreadable.log" in result


class TestAsyncScanModsUnpacked:
    """Test cases for scan_mods_unpacked_async function."""

    @pytest.mark.asyncio
    async def test_scan_mods_unpacked_async_basic(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test basic scanning of unpacked mod files."""
        # Create test file structure
        mod1_dir = mock_paths["mods"] / "TestMod1"
        mod1_dir.mkdir()

        # Create various test files
        (mod1_dir / "readme.txt").write_text("Test readme")
        (mod1_dir / "test.dds").write_bytes(
            b"DDS \x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x04\x00\x00"
        )  # Valid DDS header 1024x1024
        (mod1_dir / "test.png").touch()  # Invalid texture format
        (mod1_dir / "test.mp3").touch()  # Invalid sound format

        # Create FOMOD directory
        fomod_dir = mod1_dir / "fomod"
        fomod_dir.mkdir()
        (fomod_dir / "info.xml").touch()

        # Create animation data directory
        anim_dir = mock_paths["mods"] / "TestMod2" / "meshes"
        anim_dir.mkdir(parents=True)
        (anim_dir / "AnimationFileData").mkdir()

        result = await scan_mods_unpacked_async()

        assert "RESULTS FROM UNPACKED / LOOSE FILES" in result
        # Should find various issues
        assert any(keyword in result for keyword in ["CLEANUP", "TEXTURE", "SOUND", "ANIMATION"])

    @pytest.mark.asyncio
    async def test_scan_mods_unpacked_async_dds_dimensions(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test detection of invalid DDS dimensions."""
        # Create DDS files with odd dimensions
        mod_dir = mock_paths["mods"] / "DDSTestMod"
        mod_dir.mkdir()

        # DDS with odd width (1023x1024)
        dds1 = mod_dir / "odd_width.dds"
        dds1.write_bytes(b"DDS \x00\x00\x00\x00\x00\x00\x00\x00\xff\x03\x00\x00\x00\x04\x00\x00")

        # DDS with odd height (1024x1023)
        dds2 = mod_dir / "odd_height.dds"
        dds2.write_bytes(b"DDS \x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\xff\x03\x00\x00")

        result = await scan_mods_unpacked_async()

        assert "odd_width.dds (1023x1024)" in result
        assert "odd_height.dds (1024x1023)" in result

    @pytest.mark.asyncio
    async def test_scan_mods_unpacked_async_concurrent_dds_processing(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test concurrent DDS file processing with semaphore limits."""
        # Create many DDS files
        mod_dir = mock_paths["mods"] / "ManyDDSMod"
        mod_dir.mkdir()

        for i in range(100):
            dds_file = mod_dir / f"texture{i}.dds"
            # Create DDS with valid dimensions
            dds_file.write_bytes(b"DDS \x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x04\x00\x00")

        # Track concurrent reads
        concurrent_reads = 0
        max_concurrent_reads = 0

        original_open = open

        def track_concurrent_open(*args, **kwargs):
            nonlocal concurrent_reads, max_concurrent_reads
            if str(args[0]).endswith(".dds"):
                concurrent_reads += 1
                max_concurrent_reads = max(max_concurrent_reads, concurrent_reads)
            result = original_open(*args, **kwargs)
            if str(args[0]).endswith(".dds"):
                concurrent_reads -= 1
            return result

        with patch("builtins.open", side_effect=track_concurrent_open):
            await scan_mods_unpacked_async()

        # Verify concurrency was limited
        assert max_concurrent_reads <= MAX_CONCURRENT_DDS_READS

    @pytest.mark.asyncio
    async def test_scan_mods_unpacked_async_xse_and_previs_detection(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test detection of XSE files and previs files."""
        # Create mod with XSE scripts (using exact filename from mock)
        xse_mod = mock_paths["mods"] / "XSEMod" / "Scripts"
        xse_mod.mkdir(parents=True)
        (xse_mod / "f4se_loader").touch()  # Exact name matching the mock key

        # Create mod with previs files
        previs_mod = mock_paths["mods"] / "PrevisMod" / "vis"
        previs_mod.mkdir(parents=True)
        (previs_mod / "test.uvd").touch()
        (previs_mod / "test_oc.nif").touch()

        result = await scan_mods_unpacked_async()

        # Check that issues were detected
        assert "F4SE FILES FOUND" in result or "xse_file" in result.lower()
        assert "PREVIS FILES FOUND" in result or "previs" in result.lower()

    @pytest.mark.asyncio
    async def test_scan_mods_unpacked_async_cleanup_operations(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test file cleanup operations (moving files to backup)."""

        # Create files to be cleaned up
        mod_dir = mock_paths["mods"] / "CleanupTestMod"
        mod_dir.mkdir()

        readme_file = mod_dir / "readme.txt"
        readme_file.write_text("Test readme")

        changelog_file = mod_dir / "changes.txt"
        changelog_file.write_text("Test changelog")

        fomod_dir = mod_dir / "fomod"
        fomod_dir.mkdir()

        # Track move operations
        moved_files = []

        def track_move(src, dst):
            moved_files.append((src, dst))
            # Don't actually move in test

        with patch("shutil.move", side_effect=track_move):
            with patch("ClassicLib.ScanGame.Config.TEST_MODE", False):
                result = await scan_mods_unpacked_async()

        # Verify files were marked for cleanup
        assert len(moved_files) >= 3  # readme, changelog, fomod
        assert any("readme.txt" in str(src) for src, dst in moved_files)
        assert any("changes.txt" in str(src) for src, dst in moved_files)
        assert any("fomod" in str(src) for src, dst in moved_files)


class TestAsyncWrappers:
    """Test synchronous wrapper functions."""

    def test_scan_mods_archived_async_wrapper(self, mock_settings):
        """Test synchronous wrapper for scan_mods_archived_async."""
        # Mock the async function to be an AsyncMock
        mock_async_func = AsyncMock(return_value="Test result")

        with patch("ClassicLib.ScanGame.AsyncScanGame.scan_mods_archived_async", mock_async_func):
            result = scan_mods_archived_async_wrapper()
            assert result == "Test result"

    def test_check_log_errors_async_wrapper(self, mock_settings, mock_paths):
        """Test synchronous wrapper for check_log_errors_async."""
        # Mock the async function to be an AsyncMock
        mock_async_func = AsyncMock(return_value="Test log result")

        with patch("ClassicLib.ScanGame.AsyncScanGame.check_log_errors_async", mock_async_func):
            result = check_log_errors_async_wrapper(mock_paths["logs"])
            assert result == "Test log result"

    def test_scan_mods_unpacked_async_wrapper(self, mock_settings):
        """Test synchronous wrapper for scan_mods_unpacked_async."""
        # Mock the async function to be an AsyncMock
        mock_async_func = AsyncMock(return_value="Test unpacked result")

        with patch("ClassicLib.ScanGame.AsyncScanGame.scan_mods_unpacked_async", mock_async_func):
            result = scan_mods_unpacked_async_wrapper()
            assert result == "Test unpacked result"


class TestAsyncIntegration:
    """Integration tests for async functionality."""

    @pytest.mark.asyncio
    async def test_async_performance_improvement(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry
    ):
        """Test that async version is faster than sequential processing."""
        import time

        # Create multiple BA2 files
        for i in range(5):
            ba2_file = mock_paths["mods"] / f"test{i}.ba2"
            with open(ba2_file, "wb") as f:
                f.write(b"BTDX\x00\x00\x00\x00DX10")

        # Mock subprocess with delay
        async def slow_subprocess(*args, **kwargs):
            mock_proc = AsyncMock()
            mock_proc.returncode = 0

            async def simulate_communicate():
                await asyncio.sleep(0.2)
                return ("output", "")

            mock_proc.communicate = AsyncMock(side_effect=simulate_communicate)
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=slow_subprocess):
            start_time = time.time()
            await scan_mods_archived_async()
            async_time = time.time() - start_time

        # With semaphore limit of 4, 5 files should take ~0.4s (2 batches)
        # Sequential would take ~1.0s (5 * 0.2s)
        assert async_time < 0.6  # Allow some overhead

    def test_feature_flag_integration(self, mock_scan_settings, mock_issue_messages):
        """Test that the new async-first implementation works correctly."""
        # Test that sync adapters correctly delegate to async core
        with patch("CLASSIC_ScanGame.ScanGameCore") as mock_core:
            mock_instance = mock_core.return_value
            mock_instance.scan_mods_archived = AsyncMock(return_value="Async result")

            # Call the sync adapter
            result = CLASSIC_ScanGame.scan_mods_archived()

            # Verify core was instantiated and method was called
            mock_core.assert_called_once()
            assert result == "Async result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

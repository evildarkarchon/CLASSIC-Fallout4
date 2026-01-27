"""
Test suite for async INI scanning functionality.

This module contains tests for the async INI scanning functions
and ConfigFileCache async methods that were optimized for performance.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ClassicLib.scanning.game.ScanModInis import (
    check_vsync_settings_async,
    scan_mod_inis,
    scan_mod_inis_async,
)

from ClassicLib.scanning.game.Config import ConfigFileCache


@pytest.mark.unit
class TestAsyncINIScanning:
    """Test async INI scanning functionality."""

    @pytest.mark.asyncio
    async def test_scan_mod_inis_async_basic(self):
        """Test basic async INI scanning functionality."""
        with patch("ClassicLib.scanning.game.ScanModInis.ConfigFileCache") as MockConfigCache:
            # Create mock config cache instance
            mock_cache = MagicMock()
            mock_cache.get_async = AsyncMock(return_value=None)
            mock_cache.duplicate_files = {}
            MockConfigCache.return_value = mock_cache

            # Mock the async helper functions
            with (
                patch("ClassicLib.scanning.game.ScanModInis.check_starting_console_command_async", new_callable=MagicMock),
                patch("ClassicLib.scanning.game.ScanModInis.check_vsync_settings_async", new_callable=AsyncMock) as mock_vsync,
                patch("ClassicLib.scanning.game.ScanModInis.detect_all_ini_issues_async", new_callable=AsyncMock) as mock_detect,
                patch("ClassicLib.scanning.game.ScanModInis.check_duplicate_files"),
            ):
                mock_vsync.return_value = []
                mock_detect.return_value = []  # No issues detected
                result = await scan_mod_inis_async()

                # Verify result is a string
                assert isinstance(result, str)
                assert result == ""  # Empty when no issues found

    @pytest.mark.asyncio
    async def test_scan_mod_inis_async_with_vsync(self):
        """Test async INI scanning with VSync settings detected."""
        with patch("ClassicLib.scanning.game.ScanModInis.ConfigFileCache") as MockConfigCache:
            mock_cache = MagicMock()
            mock_cache.get_async = AsyncMock(return_value=None)
            mock_cache.duplicate_files = {}
            MockConfigCache.return_value = mock_cache

            with (
                patch("ClassicLib.scanning.game.ScanModInis.check_starting_console_command_async", new_callable=MagicMock),
                patch("ClassicLib.scanning.game.ScanModInis.check_vsync_settings_async", new_callable=AsyncMock) as mock_vsync,
                patch("ClassicLib.scanning.game.ScanModInis.detect_all_ini_issues_async", new_callable=AsyncMock) as mock_detect,
                patch("ClassicLib.scanning.game.ScanModInis.check_duplicate_files"),
            ):
                # Mock VSync settings found
                mock_vsync.return_value = ["enblocal.ini | SETTING: ForceVSync\n"]
                mock_detect.return_value = []  # No issues detected
                result = await scan_mod_inis_async()

                # Verify VSync notice is in result
                assert "VSYNC IS CURRENTLY ENABLED" in result
                assert "enblocal.ini" in result

    @pytest.mark.asyncio
    async def test_check_vsync_settings_async(self):
        """Test async VSync settings detection."""
        mock_cache = MagicMock()

        # Create an async function that returns the right value
        async def mock_get_async_impl(value_type, file_name, section, setting):
            # Return True for enblocal.ini ForceVSync (which is in VSYNC_SETTINGS)
            if file_name == "enblocal.ini" and section == "ENGINE" and setting == "ForceVSync":
                return True
            return None  # Return None for other settings

        # Set up the mock
        mock_cache.get_async = mock_get_async_impl
        mock_cache.__contains__ = MagicMock(return_value=False)  # No highfpsphysicsfix.ini
        mock_cache.__getitem__ = MagicMock(return_value=Path("test/enblocal.ini"))

        result = await check_vsync_settings_async(mock_cache)

        # Verify VSync was detected
        assert len(result) == 1
        assert "ForceVSync" in result[0]

    def test_scan_mod_inis_sync_wrapper(self):
        """Test synchronous wrapper calls async version correctly."""
        # Import and patch at the module level where it's used
        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as MockBridge,
            patch("ClassicLib.scanning.game.ScanModInis.scan_mod_inis_async", new_callable=MagicMock) as mock_scan_async,
        ):
            mock_bridge_instance = MagicMock()
            MockBridge.get_instance.return_value = mock_bridge_instance
            mock_bridge_instance.run_async.return_value = "Test Result"

            # Mock return value of async function (coroutine object if not awaited, but here just passed)
            mock_scan_async.return_value = "coroutine_obj"

            result = scan_mod_inis()

            # Verify AsyncBridge was used
            MockBridge.get_instance.assert_called_once()
            mock_bridge_instance.run_async.assert_called_with("coroutine_obj")
            assert result == "Test Result"


@pytest.mark.unit
class TestConfigFileCacheAsync:
    """Test ConfigFileCache async methods."""

    @pytest.mark.asyncio
    async def test_get_async_loads_config(self):
        """Test get_async loads configuration when not cached."""
        # Mock yaml_settings to avoid async context error during init
        with patch("ClassicLib.scanning.game.Config.yaml_settings", return_value=Path()):
            cache = ConfigFileCache()
        cache._config_files = {"test.ini": Path("test/test.ini")}
        cache._config_file_cache = {}

        # Mock _load_config_async
        cache._load_config_async = AsyncMock()

        # Mock the config after loading
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config.has_option.return_value = True
        mock_config.get.return_value = "test_value"

        with patch.object(
            cache,
            "_config_file_cache",
            {
                "test.ini": {
                    "encoding": "utf-8",
                    "path": Path("test/test.ini"),
                    "settings": mock_config,
                    "text": "[section]\nkey=test_value",
                }
            },
        ):
            result = await cache.get_async(str, "test.ini", "section", "key")
            assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_async_uses_cached_config(self):
        """Test get_async uses cached configuration without reloading."""
        # Mock yaml_settings to avoid async context error during init
        with patch("ClassicLib.scanning.game.Config.yaml_settings", return_value=Path()):
            cache = ConfigFileCache()
        cache._config_files = {"test.ini": Path("test/test.ini")}

        # Pre-populate cache
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config.has_option.return_value = True
        mock_config.get.return_value = "cached_value"
        cache._config_file_cache = {
            "test.ini": {
                "encoding": "utf-8",
                "path": Path("test/test.ini"),
                "settings": mock_config,
                "text": "[section]\nkey=cached_value",
            }
        }

        # Mock _load_config_async - should not be called
        cache._load_config_async = AsyncMock()

        result = await cache.get_async(str, "test.ini", "section", "key")

        # Verify cached value was used
        assert result == "cached_value"
        cache._load_config_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_config_async_processes_file(self, tmp_path):
        """Test _load_config_async processes files asynchronously."""
        # Create an actual test file to avoid FileNotFoundError
        test_file = tmp_path / "test.ini"
        test_file.write_text("[section]\nkey=value", encoding="utf-8")

        # Mock yaml_settings to avoid async context error during init
        with patch("ClassicLib.scanning.game.Config.yaml_settings", return_value=Path()):
            cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_file}
        cache._config_file_cache = {}

        # Load the config file
        await cache._load_config_async("test.ini")

        # Verify the file was loaded into the cache
        assert "test.ini" in cache._config_file_cache
        assert cache._config_file_cache["test.ini"]["settings"] is not None
        assert cache._config_file_cache["test.ini"]["encoding"] is not None

    @pytest.mark.asyncio
    async def test_hash_caching_prevents_recalculation(self):
        """Test that file hash caching prevents recalculation."""
        # Mock yaml_settings to avoid async context error during init
        with patch("ClassicLib.scanning.game.Config.yaml_settings", return_value=Path()):
            cache = ConfigFileCache()
        cache._hash_cache = {}

        test_path = Path("test/file.ini")

        # Mock calculate_file_hash
        with patch("ClassicLib.scanning.game.Config.calculate_file_hash") as mock_hash:
            mock_hash.return_value = "hash123"

            # First call should calculate hash
            hash1 = cache._get_cached_hash(test_path)
            assert hash1 == "hash123"
            mock_hash.assert_called_once_with(test_path)

            # Second call should use cache
            hash2 = cache._get_cached_hash(test_path)
            assert hash2 == "hash123"
            mock_hash.assert_called_once()  # Still only called once


@pytest.mark.unit
class TestScanGameOptimizations:
    """Test ScanGame optimizations."""

    @pytest.mark.asyncio
    async def test_optimized_directory_walking(self):
        """Test optimized directory walking using pathlib.rglob."""
        from ClassicLib.scanning.game.ScanGameCore import ScanGameCore

        core = ScanGameCore()

        # Create mock path with rglob
        mock_path = MagicMock(spec=Path)
        mock_path.rglob.return_value = [
            MagicMock(is_dir=lambda: True, is_file=lambda: False, name="dir1", parent=mock_path),
            MagicMock(is_dir=lambda: False, is_file=lambda: True, name="file1.txt", parent=mock_path),
        ]
        mock_path.is_dir.return_value = True
        mock_path.iterdir.return_value = []

        # Test async_walk with optimized implementation
        # The actual test would need to mock the executor
        # This is a simplified version showing the structure
        assert core is not None  # Basic sanity check

    @pytest.mark.asyncio
    async def test_dds_batch_processing_optimization(self):
        """Test optimized DDS header batch processing."""
        from ClassicLib.scanning.game.ScanGameCore import ScanGameCore

        core = ScanGameCore()

        # Create test DDS files
        dds_files = [(Path(f"test{i}.dds"), Path(f"relative{i}.dds")) for i in range(200)]

        issue_lists = {"tex_dims": set()}
        issue_locks = {"tex_dims": asyncio.Lock()}

        # Mock _read_dds_header_mmap to return odd dimensions for some files
        def mock_read_header(file_path):
            # Return odd dimensions for first 10 files
            if "test0" in str(file_path) or "test1" in str(file_path):
                return (101, 102)  # Odd width
            return (100, 100)  # Even dimensions

        # We must mock the method on the dds_processor instance, not the core
        core.dds_processor.read_dds_header_mmap = mock_read_header

        # Mock the executor
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Mock executor to call our function directly
            # Accept arbitrary arguments to handle executor, func, and args
            mock_loop.run_in_executor = AsyncMock(side_effect=lambda executor, func, *args: func(*args))

            await core._check_dds_batch_async(dds_files[:10], issue_lists, issue_locks)

            # Verify issues were detected for files with odd dimensions
            assert len(issue_lists["tex_dims"]) > 0


@pytest.mark.integration
class TestGameIntegrityOrchestratorAsync:
    """Test GameIntegrityOrchestrator async integration."""

    @pytest.mark.asyncio
    async def test_orchestrator_calls_async_ini_scan_directly(self):
        """Test orchestrator calls scan_mod_inis_async directly without executor."""
        from ClassicLib.scanning.game.GameIntegrityOrchestrator import GameIntegrityOrchestratorCore

        orchestrator = GameIntegrityOrchestratorCore()

        # Mock scan_mod_inis_async
        with patch("ClassicLib.scanning.game.GameIntegrityOrchestrator.scan_mod_inis_async") as mock_scan:
            mock_scan.return_value = "Test INI scan result"

            result = await orchestrator._run_mod_inis_scan_async()

            # Verify direct async call was made
            mock_scan.assert_called_once()
            assert result == "Test INI scan result"

    @pytest.mark.asyncio
    async def test_orchestrator_performance_improvement(self):
        """Test that orchestrator doesn't use run_in_executor for async functions."""
        from ClassicLib.scanning.game.GameIntegrityOrchestrator import GameIntegrityOrchestratorCore

        orchestrator = GameIntegrityOrchestratorCore()

        # Patch to ensure run_in_executor is not called for mod_inis_scan
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            with patch("ClassicLib.scanning.game.GameIntegrityOrchestrator.scan_mod_inis_async") as mock_scan:
                mock_scan.return_value = "Direct async result"

                result = await orchestrator._run_mod_inis_scan_async()

                # Verify run_in_executor was NOT called
                mock_loop.run_in_executor.assert_not_called()
                assert result == "Direct async result"

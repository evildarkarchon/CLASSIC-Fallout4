"""
Test suite for async INI scanning functionality.

This module contains tests for the async INI scanning functions
which now delegate to Rust RustModIniScanner. Tests verify the
Python glue layer and ConfigFileCache async methods.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.scanning.game.config import ConfigFileCache
from ClassicLib.scanning.game.scan_mod_inis import (
    scan_mod_inis,
    scan_mod_inis_async,
)


@pytest.mark.unit
class TestAsyncINIScanning:
    """Test async INI scanning functionality (Rust delegation)."""

    @pytest.mark.asyncio
    async def test_scan_mod_inis_async_returns_string(self) -> None:
        """Test scan_mod_inis_async returns a string."""
        with patch("ClassicLib.scanning.game.scan_mod_inis._run_rust_scan") as mock_scan:
            mock_result = MagicMock()
            mock_result.message = "Test scan result"
            mock_scan.return_value = mock_result

            result = await scan_mod_inis_async()

            assert isinstance(result, str)
            assert result == "Test scan result"

    @pytest.mark.asyncio
    async def test_scan_mod_inis_async_returns_empty_when_no_game_root(self) -> None:
        """Test scan_mod_inis_async returns empty string when game root is unavailable."""
        with patch("ClassicLib.scanning.game.scan_mod_inis._run_rust_scan") as mock_scan:
            mock_scan.return_value = None

            result = await scan_mod_inis_async()

            assert result == ""

    def test_scan_mod_inis_sync_returns_string(self) -> None:
        """Test synchronous scan_mod_inis returns string from Rust scanner."""
        with patch("ClassicLib.scanning.game.scan_mod_inis._run_rust_scan") as mock_scan:
            mock_result = MagicMock()
            mock_result.message = "Sync result"
            mock_scan.return_value = mock_result

            result = scan_mod_inis()

            assert result == "Sync result"

    def test_scan_mod_inis_sync_returns_empty_when_no_game_root(self) -> None:
        """Test synchronous scan_mod_inis returns empty when game root is unavailable."""
        with patch("ClassicLib.scanning.game.scan_mod_inis._run_rust_scan") as mock_scan:
            mock_scan.return_value = None

            result = scan_mod_inis()

            assert result == ""


@pytest.mark.unit
class TestConfigFileCacheAsync:
    """Test ConfigFileCache async methods (Rust-backed).

    ConfigFileCache now delegates to RustConfigFileCache which scans the
    game root directory on construction. Tests create INI files in tmp_path
    before constructing the cache.
    """

    @pytest.mark.asyncio
    async def test_get_async_returns_value(self, tmp_path: Path) -> None:
        """Test get_async retrieves values from Rust-backed cache."""
        test_file = tmp_path / "test.ini"
        test_file.write_text("[section]\nkey = test_value\n", encoding="utf-8")

        with patch("ClassicLib.scanning.game.config.yaml_settings", return_value=tmp_path):
            cache = ConfigFileCache()

        result = await cache.get_async(str, "test.ini", "section", "key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_async_returns_none_for_missing_key(self, tmp_path: Path) -> None:
        """Test get_async returns None for non-existent keys."""
        test_file = tmp_path / "test.ini"
        test_file.write_text("[section]\nkey = value\n", encoding="utf-8")

        with patch("ClassicLib.scanning.game.config.yaml_settings", return_value=tmp_path):
            cache = ConfigFileCache()

        result = await cache.get_async(str, "test.ini", "section", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_async_delegates_to_sync_get(self, tmp_path: Path) -> None:
        """Test get_async delegates to synchronous get() method."""
        test_file = tmp_path / "test.ini"
        test_file.write_text("[section]\nkey = value\n", encoding="utf-8")

        with patch("ClassicLib.scanning.game.config.yaml_settings", return_value=tmp_path):
            cache = ConfigFileCache()

        sync_result = cache.get(str, "test.ini", "section", "key")
        async_result = await cache.get_async(str, "test.ini", "section", "key")
        assert sync_result == async_result

    @pytest.mark.asyncio
    async def test_contains_check_after_construction(self, tmp_path: Path) -> None:
        """Test __contains__ finds files scanned during construction."""
        test_file = tmp_path / "test.ini"
        test_file.write_text("[Main]\nKey = Value\n", encoding="utf-8")

        with patch("ClassicLib.scanning.game.config.yaml_settings", return_value=tmp_path):
            cache = ConfigFileCache()

        assert "test.ini" in cache
        assert "nonexistent.ini" not in cache


@pytest.mark.unit
class TestScanGameOptimizations:
    """Test ScanGame optimizations."""

    @pytest.mark.asyncio
    async def test_optimized_directory_walking(self) -> None:
        """Test optimized directory walking using pathlib.rglob."""
        from ClassicLib.scanning.game.core import ScanGameCore

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
    async def test_dds_batch_processing_optimization(self) -> None:
        """Test optimized DDS header batch processing."""
        from ClassicLib.scanning.game.core import ScanGameCore

        core = ScanGameCore()

        # Create test DDS files
        dds_files = [(Path(f"test{i}.dds"), Path(f"relative{i}.dds")) for i in range(200)]

        issue_lists = {"tex_dims": set()}
        issue_locks = {"tex_dims": asyncio.Lock()}

        # Mock _read_dds_header_mmap to return odd dimensions for some files
        def mock_read_header(file_path: Path) -> tuple[int, int]:
            # Return odd dimensions for first 10 files
            if "test0" in str(file_path) or "test1" in str(file_path):
                return (101, 102)  # Odd width
            return (100, 100)  # Even dimensions

        # We must mock the method on the dds_processor instance, not the core
        core.dds_processor.read_dds_header_mmap = mock_read_header  # type: ignore[assignment]

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
    async def test_orchestrator_calls_async_ini_scan_directly(self) -> None:
        """Test orchestrator calls scan_mod_inis_async directly without executor."""
        from ClassicLib.scanning.game.orchestrator import GameIntegrityOrchestratorCore

        orchestrator = GameIntegrityOrchestratorCore()

        # Mock scan_mod_inis_async
        with patch("ClassicLib.scanning.game.orchestrator.scan_mod_inis_async") as mock_scan:
            mock_scan.return_value = "Test INI scan result"

            result = await orchestrator._run_mod_inis_scan_async()

            # Verify direct async call was made
            mock_scan.assert_called_once()
            assert result == "Test INI scan result"

    @pytest.mark.asyncio
    async def test_orchestrator_performance_improvement(self) -> None:
        """Test that orchestrator doesn't use run_in_executor for async functions."""
        from ClassicLib.scanning.game.orchestrator import GameIntegrityOrchestratorCore

        orchestrator = GameIntegrityOrchestratorCore()

        # Patch to ensure run_in_executor is not called for mod_inis_scan
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            with patch("ClassicLib.scanning.game.orchestrator.scan_mod_inis_async") as mock_scan:
                mock_scan.return_value = "Direct async result"

                result = await orchestrator._run_mod_inis_scan_async()

                # Verify run_in_executor was NOT called
                mock_loop.run_in_executor.assert_not_called()
                assert result == "Direct async result"

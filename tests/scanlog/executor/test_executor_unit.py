"""Unit tests for the ScanLogsExecutor module.

This module tests the crash log scanning executor functionality including:
- __init__ - configuration loading
- _load_config_from_settings() - settings extraction
- warm_up() - resource warm-up
- Statistics tracking
"""

import pytest

pytestmark = [pytest.mark.unit]

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ClassicLib.scanning.logs.executor import ScanLogsExecutor
from ClassicLib.scanning.logs.models import ScanConfig


@pytest.mark.unit
class TestScanLogsExecutorInit:
    """Test suite for ScanLogsExecutor initialization."""

    def test_init_with_default_config(self) -> None:
        """Test initialization with default configuration."""
        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            assert executor.config is not None
            assert executor.yamldata is None  # Deferred loading
            assert executor.statistics is not None
            assert executor.statistics.total_files == 0

    def test_init_with_custom_config(self) -> None:
        """Test initialization with custom ScanConfig."""
        config = ScanConfig(
            fcx_mode=True,
            show_formid_values=True,
            move_unsolved_logs=False,
            simplify_logs=True,
        )

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor(config=config)

            assert executor.config.fcx_mode is True
            assert executor.config.show_formid_values is True
            assert executor.config.simplify_logs is True

    def test_init_defers_crash_logs_loading(self) -> None:
        """Test initialization defers crash log file loading (lazy loading).

        Note: crashlog_list is now loaded lazily during execute_scan() via
        _ensure_crashlog_list_async() to avoid calling sync settings functions
        from async context. This test verifies __init__ does NOT load crash logs.
        """
        with (
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            # crashlog_list should be empty after __init__ (lazy loading)
            assert len(executor.crashlog_list) == 0
            assert executor.statistics.total_files == 0

    def test_init_detects_formid_db(self, tmp_path: Path) -> None:
        """Test initialization detects FormID database."""
        db_file = tmp_path / "formid.db"
        db_file.touch()

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[db_file]),
        ):
            executor = ScanLogsExecutor()

            assert executor.config.formid_db_exists is True

    def test_init_with_eager_load_flag(self) -> None:
        """Test initialization with eager_load parameter."""
        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor(eager_load=True)

            assert executor._eager_load is True

    def test_init_defers_remove_list_loading(self) -> None:
        """Test initialization defers remove_list loading (lazy loading).

        Note: remove_list is now loaded lazily during execute_scan() via
        _ensure_crashlog_list_async() to avoid calling sync yaml_settings()
        from async context. This test verifies __init__ does NOT load remove_list.
        """
        with (
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            # remove_list should be empty tuple after __init__ (deferred to execute_scan)
            assert executor.config.remove_list == ()


@pytest.mark.unit
class TestScanLogsExecutorLoadConfig:
    """Test suite for _load_config_from_settings method."""

    def test_load_config_defaults(self) -> None:
        """Test config loading with default values."""
        with patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=None):
            config = ScanLogsExecutor._load_config_from_settings()

            assert isinstance(config, ScanConfig)

    def test_load_config_with_fcx_mode(self) -> None:
        """Test config loading with FCX mode enabled."""

        def mock_settings(type_arg, key: str) -> bool | None:
            if key == "FCX Mode":
                return True
            return None

        with patch("ClassicLib.scanning.logs.executor.classic_settings", side_effect=mock_settings):
            config = ScanLogsExecutor._load_config_from_settings()

            assert config.fcx_mode is True

    def test_load_config_with_all_settings(self) -> None:
        """Test config loading with all settings enabled."""

        def mock_settings(type_arg, key: str) -> bool:
            return True  # All settings enabled

        with patch("ClassicLib.scanning.logs.executor.classic_settings", side_effect=mock_settings):
            config = ScanLogsExecutor._load_config_from_settings()

            assert config.fcx_mode is True
            assert config.show_formid_values is True
            assert config.move_unsolved_logs is True
            assert config.simplify_logs is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestScanLogsExecutorLazyLoading:
    """Test suite for lazy loading via _ensure_crashlog_list_async."""

    async def test_ensure_crashlog_list_loads_files(self, tmp_path: Path) -> None:
        """Test _ensure_crashlog_list_async loads crash log files."""
        crash_files = [tmp_path / f"crash-{i}.log" for i in range(3)]
        for f in crash_files:
            f.touch()

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=crash_files),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            # Before lazy loading
            assert len(executor.crashlog_list) == 0
            assert executor.statistics.total_files == 0

            # Trigger lazy loading
            await executor._ensure_crashlog_list_async()

            # After lazy loading
            assert len(executor.crashlog_list) == 3
            assert executor.statistics.total_files == 3

    async def test_ensure_crashlog_list_loads_remove_list(self) -> None:
        """Test _ensure_crashlog_list_async loads remove_list when not provided."""
        remove_list = ("record1", "record2")

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=remove_list),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            # Before lazy loading
            assert executor.config.remove_list == ()

            # Trigger lazy loading
            await executor._ensure_crashlog_list_async()

            # After lazy loading
            assert executor.config.remove_list == remove_list

    async def test_ensure_crashlog_list_skips_if_already_loaded(self, tmp_path: Path) -> None:
        """Test _ensure_crashlog_list_async skips if already loaded."""
        crash_files = [tmp_path / "crash-1.log"]
        crash_files[0].touch()

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=crash_files) as mock_get_files,
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            # First call loads files
            await executor._ensure_crashlog_list_async()
            assert mock_get_files.call_count == 1

            # Second call should skip (already loaded)
            await executor._ensure_crashlog_list_async()
            assert mock_get_files.call_count == 1  # Still 1, not called again


@pytest.mark.unit
@pytest.mark.asyncio
class TestScanLogsExecutorWarmUp:
    """Test suite for warm_up method."""

    async def test_warm_up_loads_yamldata(self) -> None:
        """Test warm_up loads YAML data."""
        mock_yamldata = MagicMock()

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
            patch(
                "ClassicLib.scanning.logs.executor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ),
        ):
            executor = ScanLogsExecutor()
            assert executor.yamldata is None

            await executor.warm_up()

            assert executor.yamldata is mock_yamldata

    async def test_warm_up_skips_if_already_warmed(self) -> None:
        """Test warm_up skips if already warmed up."""
        mock_yamldata = MagicMock()

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
            patch(
                "ClassicLib.scanning.logs.executor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ) as mock_create,
        ):
            executor = ScanLogsExecutor()
            executor.yamldata = mock_yamldata  # Pre-set

            await executor.warm_up()

            # Should not call create_async again
            mock_create.assert_not_called()

    async def test_warm_up_initializes_db_pool(self, tmp_path: Path) -> None:
        """Test warm_up initializes database pool when DB exists."""
        db_file = tmp_path / "formid.db"
        db_file.touch()
        mock_yamldata = MagicMock()

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[db_file]),
            patch(
                "ClassicLib.scanning.logs.executor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ),
            patch("ClassicLib.io.database.DatabasePoolManager") as mock_pool_manager,
        ):
            mock_pool = MagicMock()
            mock_pool_manager.return_value.get_pool = AsyncMock(return_value=mock_pool)

            executor = ScanLogsExecutor()
            await executor.warm_up()

            # Database pool should be initialized
            mock_pool_manager.return_value.get_pool.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
class TestScanLogsExecutorAsyncDbPaths:
    """Test suite for async-safe database path resolution."""

    async def test_initialize_uses_async_db_paths_in_async_context(self) -> None:
        """Test _initialize_scan_resources uses async DB path helper.

        Regression test for RuntimeError:
        "yaml_settings() called from async context. Use 'await yaml_settings_async()' instead."
        """
        mock_yamldata = MagicMock()
        mock_rust_config = MagicMock()
        mock_yamldata.to_rust_config.return_value = mock_rust_config
        mock_orchestrator = MagicMock()

        sync_call_count = 0

        def sync_db_paths_side_effect() -> list[Path]:
            nonlocal sync_call_count
            sync_call_count += 1
            # First call is allowed during __init__ in sync-safe contexts.
            if sync_call_count == 1:
                return []
            msg = "sync get_all_db_paths() called during async initialization"
            raise RuntimeError(msg)

        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", side_effect=sync_db_paths_side_effect),
            patch(
                "ClassicLib.scanning.logs.executor.get_all_db_paths_async",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_get_all_db_paths_async,
            patch(
                "ClassicLib.scanning.logs.executor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ),
            patch("ClassicLib.support.game_path.game_path_find_async", new_callable=AsyncMock),
            patch("ClassicLib.support.game_path.game_generate_paths_async", new_callable=AsyncMock),
            patch("ClassicLib.scanning.logs.executor.Orchestrator", return_value=mock_orchestrator),
        ):
            executor = ScanLogsExecutor(config=ScanConfig(show_formid_values=True))
            executor.config.formid_db_exists = True

            await executor._initialize_scan_resources()

            # Sync helper should only be used once during __init__ setup.
            assert sync_call_count == 1
            mock_get_all_db_paths_async.assert_awaited_once()


@pytest.mark.unit
class TestScanLogsExecutorStatistics:
    """Test suite for statistics tracking."""

    def test_statistics_initialized(self) -> None:
        """Test statistics are properly initialized."""
        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            assert executor.statistics is not None
            assert executor.statistics.scanned == 0
            assert executor.statistics.incomplete == 0
            assert executor.statistics.failed == 0

    def test_statistics_defers_total_files(self) -> None:
        """Test statistics defer total_files count (lazy loading).

        Note: total_files is now set during _ensure_crashlog_list_async()
        which is called in execute_scan(). This test verifies total_files
        is 0 after __init__ (lazy loading pattern).
        """
        with (
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            # total_files should be 0 after __init__ (set during execute_scan)
            assert executor.statistics.total_files == 0


@pytest.mark.unit
class TestScanLogsExecutorGenerateSummary:
    """Test suite for generate_summary method."""

    def test_generate_summary_no_scans(self) -> None:
        """Test summary generation with no scanned logs."""
        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()

            # Create mock result with zero scans
            from ClassicLib.scanning.logs.models import ScanResult

            result = ScanResult(stats=executor.statistics)
            summary = executor.generate_summary(result)

            assert "no crash logs" in summary.lower() or "no statistics" in summary.lower()

    def test_generate_summary_with_scans(self) -> None:
        """Test summary generation with scanned logs."""
        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
        ):
            executor = ScanLogsExecutor()
            executor.statistics.scanned = 5
            executor.statistics.incomplete = 1
            executor.statistics.failed = 0

            from ClassicLib.scanning.logs.models import ScanResult

            result = ScanResult(stats=executor.statistics)
            result.scan_time = 2.5

            summary = executor.generate_summary(result)

            assert "SCAN COMPLETE" in summary
            assert "5" in summary  # Scanned count
            assert "2.5" in summary or "2.50" in summary  # Scan time


@pytest.mark.unit
class TestScanLogsExecutorSyncWrapper:
    """Test suite for scan_sync method."""

    def test_scan_sync_uses_async_bridge(self) -> None:
        """Test that scan_sync uses AsyncBridge.run_async() directly."""
        with (
            patch("ClassicLib.scanning.logs.executor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.yaml_settings", return_value=None),
            patch("ClassicLib.scanning.logs.executor.classic_settings", return_value=False),
            patch("ClassicLib.scanning.logs.executor.get_all_db_paths", return_value=[]),
            patch("ClassicLib.scanning.logs.executor.AsyncBridge") as mock_bridge_cls,
        ):
            mock_bridge = MagicMock()
            mock_bridge.run_async.return_value = MagicMock()
            mock_bridge_cls.get_instance.return_value = mock_bridge

            executor = ScanLogsExecutor()

            # Mock execute_scan to return a MagicMock instead of a real coroutine,
            # preventing "coroutine was never awaited" warnings when the mock
            # bridge.run_async() silently discards the argument.
            executor.execute_scan = MagicMock(return_value=MagicMock())  # type: ignore[method-assign]

            # Call scan_sync
            try:
                executor.scan_sync()
            except Exception:
                _ = None  # pass  # May fail in test context, that's OK

            # AsyncBridge should have been used
            mock_bridge_cls.get_instance.assert_called()
            mock_bridge.run_async.assert_called()


@pytest.mark.unit
class TestScanLogsExecutorBackwardCompatibility:
    """Test suite for backward compatibility."""

    def test_classiccanlogs_alias_exists(self) -> None:
        """Test that ClassicScanLogs alias exists for backward compatibility."""
        from ClassicLib.scanning.logs.executor import ClassicScanLogs

        assert ClassicScanLogs is ScanLogsExecutor

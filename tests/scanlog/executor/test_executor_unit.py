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

from ClassicLib.ScanLog.models import ScanConfig
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor


@pytest.mark.unit
class TestScanLogsExecutorInit:
    """Test suite for ScanLogsExecutor initialization."""

    def test_init_with_default_config(self) -> None:
        """Test initialization with default configuration."""
        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
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
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor(config=config)

            assert executor.config.fcx_mode is True
            assert executor.config.show_formid_values is True
            assert executor.config.simplify_logs is True

    def test_init_detects_crash_logs(self, tmp_path: Path) -> None:
        """Test initialization detects crash log files."""
        # Create mock crash log files
        crash_files = [
            tmp_path / "crash-1.log",
            tmp_path / "crash-2.log",
        ]
        for f in crash_files:
            f.touch()

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=crash_files),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor()

            assert len(executor.crashlog_list) == 2
            assert executor.statistics.total_files == 2

    def test_init_detects_formid_db(self, tmp_path: Path) -> None:
        """Test initialization detects FormID database."""
        db_file = tmp_path / "formid.db"
        db_file.touch()

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", [db_file]),
        ):
            executor = ScanLogsExecutor()

            assert executor.config.formid_db_exists is True

    def test_init_with_eager_load_flag(self) -> None:
        """Test initialization with eager_load parameter."""
        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor(eager_load=True)

            assert executor._eager_load is True

    def test_init_loads_remove_list(self) -> None:
        """Test initialization loads remove_list from YAML settings."""
        remove_list = ("record1", "record2")

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=remove_list),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor()

            assert executor.config.remove_list == remove_list


@pytest.mark.unit
class TestScanLogsExecutorLoadConfig:
    """Test suite for _load_config_from_settings method."""

    def test_load_config_defaults(self) -> None:
        """Test config loading with default values."""
        with patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=None):
            config = ScanLogsExecutor._load_config_from_settings()

            assert isinstance(config, ScanConfig)

    def test_load_config_with_fcx_mode(self) -> None:
        """Test config loading with FCX mode enabled."""
        def mock_settings(type_arg, key: str) -> bool | None:
            if key == "FCX Mode":
                return True
            return None

        with patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", side_effect=mock_settings):
            config = ScanLogsExecutor._load_config_from_settings()

            assert config.fcx_mode is True

    def test_load_config_with_all_settings(self) -> None:
        """Test config loading with all settings enabled."""
        def mock_settings(type_arg, key: str) -> bool:
            return True  # All settings enabled

        with patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", side_effect=mock_settings):
            config = ScanLogsExecutor._load_config_from_settings()

            assert config.fcx_mode is True
            assert config.show_formid_values is True
            assert config.move_unsolved_logs is True
            assert config.simplify_logs is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestScanLogsExecutorWarmUp:
    """Test suite for warm_up method."""

    async def test_warm_up_loads_yamldata(self) -> None:
        """Test warm_up loads YAML data."""
        mock_yamldata = MagicMock()

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
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
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
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
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", [db_file]),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ),
            patch("ClassicLib.Database.DatabasePoolManager") as mock_pool_manager,
        ):
            mock_pool = MagicMock()
            mock_pool_manager.return_value.get_pool = AsyncMock(return_value=mock_pool)

            executor = ScanLogsExecutor()
            await executor.warm_up()

            # Database pool should be initialized
            mock_pool_manager.return_value.get_pool.assert_called_once()


@pytest.mark.unit
class TestScanLogsExecutorStatistics:
    """Test suite for statistics tracking."""

    def test_statistics_initialized(self) -> None:
        """Test statistics are properly initialized."""
        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor()

            assert executor.statistics is not None
            assert executor.statistics.scanned == 0
            assert executor.statistics.incomplete == 0
            assert executor.statistics.failed == 0

    def test_statistics_tracks_total_files(self, tmp_path: Path) -> None:
        """Test statistics track total files count."""
        crash_files = [tmp_path / f"crash-{i}.log" for i in range(5)]
        for f in crash_files:
            f.touch()

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=crash_files),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor()

            assert executor.statistics.total_files == 5


@pytest.mark.unit
class TestScanLogsExecutorGenerateSummary:
    """Test suite for generate_summary method."""

    def test_generate_summary_no_scans(self) -> None:
        """Test summary generation with no scanned logs."""
        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor()

            # Create mock result with zero scans
            from ClassicLib.ScanLog.models import ScanResult

            result = ScanResult(stats=executor.statistics)
            summary = executor.generate_summary(result)

            assert "no crash logs" in summary.lower() or "no statistics" in summary.lower()

    def test_generate_summary_with_scans(self) -> None:
        """Test summary generation with scanned logs."""
        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
        ):
            executor = ScanLogsExecutor()
            executor.statistics.scanned = 5
            executor.statistics.incomplete = 1
            executor.statistics.failed = 0

            from ClassicLib.ScanLog.models import ScanResult

            result = ScanResult(stats=executor.statistics)
            result.scan_time = 2.5

            summary = executor.generate_summary(result)

            assert "SCAN COMPLETE" in summary
            assert "5" in summary  # Scanned count
            assert "2.5" in summary or "2.50" in summary  # Scan time


@pytest.mark.unit
class TestScanLogsExecutorSyncWrapper:
    """Test suite for scan_sync method."""

    def test_scan_sync_creates_wrapper(self) -> None:
        """Test that scan_sync creates a sync wrapper."""
        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.create_sync_wrapper") as mock_wrapper,
        ):
            mock_wrapper.return_value = MagicMock(return_value=MagicMock())

            executor = ScanLogsExecutor()

            # Call scan_sync
            try:
                executor.scan_sync()
            except Exception:
                pass  # May fail in test context, that's OK

            # Wrapper should have been created
            mock_wrapper.assert_called()


@pytest.mark.unit
class TestScanLogsExecutorBackwardCompatibility:
    """Test suite for backward compatibility."""

    def test_classiccanlogs_alias_exists(self) -> None:
        """Test that ClassicScanLogs alias exists for backward compatibility."""
        from ClassicLib.ScanLog.ScanLogsExecutor import ClassicScanLogs

        assert ClassicScanLogs is ScanLogsExecutor

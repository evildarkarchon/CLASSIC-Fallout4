"""Integration tests for the ScanLogsExecutor module.

This module tests the complete scan execution flow including:
- scan_async() - full async scan flow
- execute_scan() - complete execution pipeline
- Error recovery during scanning
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ClassicLib.ScanLog.models import ScanConfig, ScanResult
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor


def create_rust_compatible_yamldata() -> MagicMock:
    """Create a mock yamldata with all Rust-compatible attributes."""
    mock_yamldata = MagicMock(spec=False)
    mock_yamldata.crashgen_name = "Buffout 4"
    mock_yamldata.xse_acronym = "F4SE"
    mock_yamldata.crashgen_latest_og = "1.28.6"
    mock_yamldata.crashgen_latest_vr = "1.26.2"
    mock_yamldata.game_mods_conf = {}
    mock_yamldata.game_mods_freq = {}
    mock_yamldata.game_mods_solu = {}
    mock_yamldata.game_mods_core = {}
    mock_yamldata.game_mods_core_folon = {}
    mock_yamldata.game_mods_opc2 = {}
    mock_yamldata.crashlog_error_check = {}
    mock_yamldata.crashlog_stack_check = {}
    mock_yamldata.classic_game_hints = []
    mock_yamldata.autoscan_text = ""
    # Required for Rust PluginAnalyzer
    mock_yamldata.game_ignore_plugins = []
    mock_yamldata.ignore_list = []
    mock_yamldata.game_version = "1.10.163"
    mock_yamldata.game_version_vr = "1.2.72"
    mock_yamldata.game_version_new = "1.10.163"
    # Required for report generation
    mock_yamldata.classic_version = "CLASSIC v1.0.0"
    # Required for suspect scanning
    mock_yamldata.suspects_error_list = {}
    mock_yamldata.suspects_stack_list = {}
    return mock_yamldata


@pytest.mark.integration
@pytest.mark.asyncio
class TestScanLogsExecutorExecuteScan:
    """Integration tests for execute_scan method."""

    async def test_execute_scan_returns_result(self, crash_log_file: Path) -> None:
        """Test execute_scan returns a ScanResult."""
        mock_yamldata = create_rust_compatible_yamldata()

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[crash_log_file]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ),
            patch("ClassicLib.GamePath.game_path_find_async", new_callable=AsyncMock),
            patch("ClassicLib.GamePath.game_generate_paths_async", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_info"),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml_async,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic_async,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
            patch("ClassicLib.ScanLog.ScanLogsUtils.write_report_to_file_async", new_callable=AsyncMock),
        ):
            mock_yaml_async.return_value = None
            mock_classic_async.return_value = False

            # Mock progress context
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.was_cancelled = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            # Mock file I/O
            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=crash_log_file.read_text())
            mock_get_io.return_value = mock_io

            # Mock parser
            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(
                return_value=(
                    "Fallout 4 v1.10.163",
                    "Buffout 4 v1.28.6",
                    "Exception",
                    [["Setting"], ["OS"], ["Stack"], ["Module"], ["Plugin"], ["[00] Fallout4.esm"]],
                )
            )
            mock_get_parser.return_value = mock_parser

            executor = ScanLogsExecutor()
            result = await executor.execute_scan()

            assert isinstance(result, ScanResult)
            assert result.stats is not None

    async def test_execute_scan_raises_without_yamldata(self) -> None:
        """Test execute_scan raises if yamldata initialization fails."""
        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=None,  # Fail to create yamldata
            ),
            patch("ClassicLib.GamePath.game_path_find_async", new_callable=AsyncMock),
            patch("ClassicLib.GamePath.game_generate_paths_async", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_info"),
        ):
            executor = ScanLogsExecutor()

            with pytest.raises(RuntimeError, match="YAML data not initialized"):
                await executor.execute_scan()


@pytest.mark.integration
@pytest.mark.asyncio
class TestScanLogsExecutorErrorRecovery:
    """Integration tests for error recovery during scanning."""

    async def test_handles_file_read_error(self, tmp_path: Path) -> None:
        """Test executor handles file read errors gracefully."""
        # Create a crash log file
        crash_file = tmp_path / "crash.log"
        crash_file.write_text("test")

        mock_yamldata = create_rust_compatible_yamldata()

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[crash_file]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ),
            patch("ClassicLib.GamePath.game_path_find_async", new_callable=AsyncMock),
            patch("ClassicLib.GamePath.game_generate_paths_async", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_info"),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml_async,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic_async,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml_async.return_value = None
            mock_classic_async.return_value = False

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.was_cancelled = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            # Mock file I/O to raise error
            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(side_effect=OSError("Read failed"))
            mock_get_io.return_value = mock_io

            mock_parser = MagicMock()
            mock_get_parser.return_value = mock_parser

            executor = ScanLogsExecutor()

            # Should complete without raising (error is logged)
            result = await executor.execute_scan()

            # Should have error in results
            assert result.stats.failed > 0 or len(result.error_messages) > 0


@pytest.mark.integration
@pytest.mark.asyncio
class TestScanLogsExecutorCancellation:
    """Integration tests for scan cancellation handling."""

    async def test_respects_cancellation(self, crash_logs_directory: Path) -> None:
        """Test executor respects cancellation requests."""
        crash_files = list(crash_logs_directory.glob("*.log"))

        mock_yamldata = create_rust_compatible_yamldata()

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=crash_files),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                return_value=mock_yamldata,
            ),
            patch("ClassicLib.GamePath.game_path_find_async", new_callable=AsyncMock),
            patch("ClassicLib.GamePath.game_generate_paths_async", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_info"),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml_async,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic_async,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
            patch("ClassicLib.ScanLog.ScanLogsUtils.write_report_to_file_async", new_callable=AsyncMock),
        ):
            mock_yaml_async.return_value = None
            mock_classic_async.return_value = False

            # Create cancellation-triggering context
            call_count = 0

            def was_cancelled_after_one() -> bool:
                nonlocal call_count
                call_count += 1
                return call_count > 2  # Cancel after first check

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.was_cancelled = MagicMock(side_effect=was_cancelled_after_one)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value="test content")
            mock_get_io.return_value = mock_io

            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(
                return_value=("Game", "Crashgen", "Error", [[], [], [], [], [], []])
            )
            mock_get_parser.return_value = mock_parser

            executor = ScanLogsExecutor()
            result = await executor.execute_scan()

            # Should complete but may not have processed all files
            assert isinstance(result, ScanResult)


@pytest.mark.integration
@pytest.mark.asyncio
class TestScanLogsExecutorResourceManagement:
    """Integration tests for resource management."""

    async def test_initializes_resources_correctly(self) -> None:
        """Test that resources are initialized in correct order."""
        init_order = []
        mock_yamldata = create_rust_compatible_yamldata()

        async def track_yamldata_init() -> MagicMock:
            init_order.append("yamldata")
            return mock_yamldata

        async def track_path_find() -> None:
            init_order.append("path_find")

        async def track_path_generate() -> None:
            init_order.append("path_generate")

        with (
            patch("ClassicLib.ScanLog.ScanLogsExecutor.crashlogs_get_files", return_value=[]),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.yaml_settings", return_value=None),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.classic_settings", return_value=False),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.DB_PATHS", []),
            patch(
                "ClassicLib.ScanLog.ScanLogsExecutor.ClassicScanLogsInfo.create_async",
                new_callable=AsyncMock,
                side_effect=track_yamldata_init,
            ),
            patch(
                "ClassicLib.GamePath.game_path_find_async",
                new_callable=AsyncMock,
                side_effect=track_path_find,
            ),
            patch(
                "ClassicLib.GamePath.game_generate_paths_async",
                new_callable=AsyncMock,
                side_effect=track_path_generate,
            ),
            patch("ClassicLib.ScanLog.ScanLogsExecutor.msg_info"),
        ):
            executor = ScanLogsExecutor()

            # Trigger initialization
            await executor._initialize_scan_resources()

            # Check initialization order
            assert "yamldata" in init_order
            assert "path_find" in init_order
            assert "path_generate" in init_order

            # yamldata should be first
            assert init_order.index("yamldata") < init_order.index("path_find")

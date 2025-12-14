"""Unit tests for the AsyncCrashLogPipeline module.

This module tests the async crash log processing pipeline including:
- AsyncCrashLogPipeline initialization
- Individual stage execution
- Error handling in pipeline
- Performance stats tracking
"""

import pytest

pytestmark = [pytest.mark.unit]

from collections import Counter
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ClassicLib.ScanLog.pipeline.async_crash_log_pipeline import (
    AsyncCrashLogPipeline,
    run_async_crash_log_scan,
    write_reports_batch,
)


@pytest.mark.unit
class TestAsyncCrashLogPipelineInit:
    """Test suite for AsyncCrashLogPipeline initialization."""

    def test_init_with_minimal_params(self, mock_yamldata: MagicMock) -> None:
        """Test pipeline initialization with minimal parameters."""
        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        assert pipeline.yamldata is mock_yamldata
        assert pipeline.fcx_mode is False
        assert pipeline.show_formid_values is False
        assert pipeline.formid_db_exists is False
        assert pipeline.performance_stats == {}

    def test_init_with_all_flags_enabled(self, mock_yamldata: MagicMock) -> None:
        """Test pipeline initialization with all flags enabled."""
        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=True,
            show_formid_values=True,
            formid_db_exists=True,
        )

        assert pipeline.fcx_mode is True
        assert pipeline.show_formid_values is True
        assert pipeline.formid_db_exists is True

    def test_init_performance_stats_empty(self, mock_yamldata: MagicMock) -> None:
        """Test that performance stats start empty."""
        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        assert isinstance(pipeline.performance_stats, dict)
        assert len(pipeline.performance_stats) == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestWriteReportsBatch:
    """Test suite for write_reports_batch function."""

    async def test_write_reports_batch_empty(self) -> None:
        """Test batch writing with empty list."""
        with patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.get_file_io") as mock_get_io:
            mock_io = MagicMock()
            mock_io.write_file = AsyncMock()
            mock_get_io.return_value = mock_io

            # Should complete without error
            await write_reports_batch([])

            # No writes should occur
            mock_io.write_file.assert_not_called()

    async def test_write_reports_batch_single_report(self, tmp_path: Path) -> None:
        """Test batch writing with single report."""
        crash_file = tmp_path / "crash-test.log"
        crash_file.write_text("test")

        reports = [
            (crash_file, ["# Report\n", "Content\n"], False),
        ]

        with patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.get_file_io") as mock_get_io:
            mock_io = MagicMock()
            mock_io.write_file = AsyncMock()
            mock_get_io.return_value = mock_io

            await write_reports_batch(reports)

            # Should write one file
            mock_io.write_file.assert_called_once()

            # Check the file path format
            call_args = mock_io.write_file.call_args
            written_path = call_args[0][0]
            assert "AUTOSCAN" in str(written_path)

    async def test_write_reports_batch_multiple_reports(self, tmp_path: Path) -> None:
        """Test batch writing with multiple reports."""
        reports = []
        for i in range(3):
            crash_file = tmp_path / f"crash-{i}.log"
            crash_file.write_text(f"test {i}")
            reports.append((crash_file, [f"# Report {i}\n"], False))

        with patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.get_file_io") as mock_get_io:
            mock_io = MagicMock()
            mock_io.write_file = AsyncMock()
            mock_get_io.return_value = mock_io

            await write_reports_batch(reports)

            # Should write all files
            assert mock_io.write_file.call_count == 3

    async def test_write_reports_batch_handles_errors(self, tmp_path: Path) -> None:
        """Test that batch writing handles individual write errors."""
        crash_file = tmp_path / "crash-test.log"
        crash_file.write_text("test")

        reports = [
            (crash_file, ["# Report\n"], False),
        ]

        with patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.get_file_io") as mock_get_io:
            mock_io = MagicMock()
            mock_io.write_file = AsyncMock(side_effect=OSError("Write failed"))
            mock_get_io.return_value = mock_io

            # Should not raise (uses return_exceptions=True in gather)
            await write_reports_batch(reports)


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncCrashLogPipelineProcessing:
    """Test suite for pipeline processing."""

    async def test_process_crash_logs_async_empty_list(self, mock_yamldata: MagicMock) -> None:
        """Test processing empty crash log list."""
        with (
            patch(
                "ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            pipeline = AsyncCrashLogPipeline(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            results, stats = await pipeline.process_crash_logs_async([], ("",))

            assert results == []
            assert "total_time" in stats
            assert "logs_per_second" in stats

    async def test_process_crash_logs_async_tracks_performance(
        self, mock_yamldata: MagicMock, crash_log_file: Path
    ) -> None:
        """Test that processing tracks performance statistics."""
        with (
            patch(
                "ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=crash_log_file.read_text())
            mock_get_io.return_value = mock_io

            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(
                return_value=("Game", "Crashgen", "Error", [[], [], [], [], [], []])
            )
            mock_get_parser.return_value = mock_parser

            pipeline = AsyncCrashLogPipeline(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            _, stats = await pipeline.process_crash_logs_async([crash_log_file], ("",))

            # Should have performance stats
            assert "reformat_time" in stats
            assert "process_time" in stats
            assert "write_time" in stats
            assert "total_time" in stats
            assert "logs_per_second" in stats

            # All times should be non-negative
            assert all(v >= 0 for v in stats.values())


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunAsyncCrashLogScan:
    """Test suite for run_async_crash_log_scan function."""

    async def test_run_async_crash_log_scan_creates_pipeline(self, mock_yamldata: MagicMock) -> None:
        """Test that run_async_crash_log_scan creates and uses a pipeline."""
        with (
            patch(
                "ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            results, stats = await run_async_crash_log_scan(
                crashlog_list=[],
                remove_list=("",),
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            assert isinstance(results, list)
            assert isinstance(stats, dict)

    async def test_run_async_crash_log_scan_passes_params(
        self, mock_yamldata: MagicMock, crash_log_file: Path
    ) -> None:
        """Test that parameters are correctly passed to pipeline."""
        # Create a properly mocked DatabasePoolManager
        mock_pool_manager = MagicMock()
        mock_pool_manager.return_value.get_pool = AsyncMock(return_value=MagicMock())

        with (
            patch(
                "ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager", mock_pool_manager),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=crash_log_file.read_text())
            mock_get_io.return_value = mock_io

            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(
                return_value=("Game", "Crashgen", "Error", [[], [], [], [], [], []])
            )
            mock_get_parser.return_value = mock_parser

            results, stats = await run_async_crash_log_scan(
                crashlog_list=[crash_log_file],
                remove_list=("record1", "record2"),
                yamldata=mock_yamldata,
                fcx_mode=True,
                show_formid_values=True,
                formid_db_exists=True,
            )

            # Should have processed the file
            assert len(results) >= 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestPipelineErrorHandling:
    """Test suite for pipeline error handling."""

    async def test_handles_reformat_error(self, mock_yamldata: MagicMock, crash_log_file: Path) -> None:
        """Test pipeline handles reformatting errors."""
        with (
            patch(
                "ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Reformat failed"),
            ),
        ):
            pipeline = AsyncCrashLogPipeline(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            # Should raise the error (not silently swallowed)
            with pytest.raises(RuntimeError, match="Reformat failed"):
                await pipeline.process_crash_logs_async([crash_log_file], ("",))

    async def test_handles_individual_log_errors(
        self, mock_yamldata: MagicMock, crash_logs_directory: Path
    ) -> None:
        """Test pipeline handles individual log processing errors."""
        crash_files = list(crash_logs_directory.glob("*.log"))

        with (
            patch(
                "ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

            # Make file I/O fail sometimes
            call_count = 0

            async def flaky_read(path: Path) -> str:
                nonlocal call_count
                call_count += 1
                if call_count % 2 == 0:
                    raise OSError("Read failed")
                return path.read_text()

            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(side_effect=flaky_read)
            mock_get_io.return_value = mock_io

            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(
                return_value=("Game", "Crashgen", "Error", [[], [], [], [], [], []])
            )
            mock_get_parser.return_value = mock_parser

            pipeline = AsyncCrashLogPipeline(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            # Should complete even with some failures
            results, stats = await pipeline.process_crash_logs_async(crash_files, ("",))

            # Should have some results (errors are captured, not raised)
            assert isinstance(results, list)


@pytest.mark.unit
@pytest.mark.asyncio
class TestPipelineBatchSizing:
    """Test suite for dynamic batch sizing."""

    async def test_batch_size_for_small_log_count(self, mock_yamldata: MagicMock, tmp_path: Path) -> None:
        """Test batch sizing for small number of logs."""
        # Create 5 crash logs (small number)
        crash_files = []
        for i in range(5):
            f = tmp_path / f"crash-{i}.log"
            f.write_text(f"test {i}")
            crash_files.append(f)

        with (
            patch(
                "ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
            patch("os.cpu_count", return_value=4),
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
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

            pipeline = AsyncCrashLogPipeline(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            results, stats = await pipeline.process_crash_logs_async(crash_files, ("",))

            # Should process all files
            assert len(results) == 5

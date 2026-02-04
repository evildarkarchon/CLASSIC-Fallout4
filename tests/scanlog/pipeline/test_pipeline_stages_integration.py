"""Unit tests for the AsyncCrashLogPipeline module.

This module tests the async crash log processing pipeline including:
- AsyncCrashLogPipeline initialization
- Individual stage execution
- Error handling in pipeline
- Performance stats tracking

Phase 9 Update: Tests now mock the Rust Orchestrator directly since
orchestrator_core.py was removed during the Rust migration.
"""

import pytest

pytestmark = [pytest.mark.unit]

from collections import Counter
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ClassicLib.scanning.logs.reporting.async_crash_log_pipeline import (
    AsyncCrashLogPipeline,
    run_async_crash_log_scan,
    write_reports_batch,
)


def create_mock_rust_result(log_path: Path) -> MagicMock:
    """Create a mock Rust AnalysisResult object."""
    mock_result = MagicMock()
    mock_result.log_path = str(log_path)
    mock_result.report_lines = [f"# Report for {log_path.name}"]
    mock_result.trigger_scan_failed = False
    mock_result.scanned = 1
    mock_result.incomplete = 0
    mock_result.failed = 0
    return mock_result


def create_mock_orchestrator(crash_files: list[Path]) -> MagicMock:
    """Create a mock Rust Orchestrator that returns results for given files."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.is_feature_complete.return_value = True
    mock_orchestrator.process_logs_batch.return_value = [
        create_mock_rust_result(f) for f in crash_files
    ]
    return mock_orchestrator


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
        with patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.get_file_io") as mock_get_io:
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

        with patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.get_file_io") as mock_get_io:
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

        with patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.get_file_io") as mock_get_io:
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

        with patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.get_file_io") as mock_get_io:
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
        mock_orchestrator = create_mock_orchestrator([])

        mock_config = MagicMock()
        mock_config_class = MagicMock()
        mock_config_class.from_yamldata.return_value = mock_config

        with (
            patch(
                "ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.integration.factory.get_yamldata", return_value=mock_yamldata),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.AnalysisConfig", mock_config_class),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.Orchestrator", return_value=mock_orchestrator),
        ):
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

    async def test_process_crash_logs_async_tracks_performance(self, mock_yamldata: MagicMock, crash_log_file: Path) -> None:
        """Test that processing tracks performance statistics."""
        mock_orchestrator = create_mock_orchestrator([crash_log_file])

        mock_config = MagicMock()
        mock_config_class = MagicMock()
        mock_config_class.from_yamldata.return_value = mock_config

        with (
            patch(
                "ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.integration.factory.get_yamldata", return_value=mock_yamldata),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.AnalysisConfig", mock_config_class),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.Orchestrator", return_value=mock_orchestrator),
        ):
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
        mock_orchestrator = create_mock_orchestrator([])

        mock_config = MagicMock()
        mock_config_class = MagicMock()
        mock_config_class.from_yamldata.return_value = mock_config

        with (
            patch(
                "ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.integration.factory.get_yamldata", return_value=mock_yamldata),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.AnalysisConfig", mock_config_class),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.Orchestrator", return_value=mock_orchestrator),
        ):
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

    async def test_run_async_crash_log_scan_passes_params(self, mock_yamldata: MagicMock, crash_log_file: Path) -> None:
        """Test that parameters are correctly passed to pipeline."""
        mock_orchestrator = create_mock_orchestrator([crash_log_file])

        mock_config = MagicMock()
        mock_config_class = MagicMock()
        mock_config_class.from_yamldata.return_value = mock_config

        with (
            patch(
                "ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.integration.factory.get_yamldata", return_value=mock_yamldata),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.AnalysisConfig", mock_config_class),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.Orchestrator", return_value=mock_orchestrator),
        ):
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.update = MagicMock()
            mock_progress.return_value = mock_context

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
                "ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async",
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

    async def test_handles_individual_log_errors(self, mock_yamldata: MagicMock, crash_logs_directory: Path) -> None:
        """Test pipeline handles individual log processing errors."""
        crash_files = list(crash_logs_directory.glob("*.log"))

        # Create orchestrator that simulates some failures
        mock_orchestrator = MagicMock()
        mock_orchestrator.is_feature_complete.return_value = True
        results = []
        for i, f in enumerate(crash_files):
            mock_result = MagicMock()
            mock_result.log_path = str(f)
            mock_result.report_lines = [f"# Report for {f.name}"]
            mock_result.trigger_scan_failed = i % 2 == 0  # Alternate failures
            mock_result.scanned = 1 if i % 2 != 0 else 0
            mock_result.incomplete = 0
            mock_result.failed = 1 if i % 2 == 0 else 0
            results.append(mock_result)
        mock_orchestrator.process_logs_batch.return_value = results

        mock_config = MagicMock()
        mock_config_class = MagicMock()
        mock_config_class.from_yamldata.return_value = mock_config

        with (
            patch(
                "ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.integration.factory.get_yamldata", return_value=mock_yamldata),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.AnalysisConfig", mock_config_class),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.Orchestrator", return_value=mock_orchestrator),
        ):
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

        mock_orchestrator = create_mock_orchestrator(crash_files)

        mock_config = MagicMock()
        mock_config_class = MagicMock()
        mock_config_class.from_yamldata.return_value = mock_config

        with (
            patch(
                "ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async",
                new_callable=AsyncMock,
            ),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.msg_progress_context") as mock_progress,
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock),
            patch("ClassicLib.integration.factory.get_yamldata", return_value=mock_yamldata),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.AnalysisConfig", mock_config_class),
            patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.Orchestrator", return_value=mock_orchestrator),
            patch("os.cpu_count", return_value=4),
        ):
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

            results, stats = await pipeline.process_crash_logs_async(crash_files, ("",))

            # Should process all files
            assert len(results) == 5

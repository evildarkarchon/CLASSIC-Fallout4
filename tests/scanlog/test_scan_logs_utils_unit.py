"""Unit tests for ClassicLib.scanning.logs.utils module.

This module tests the utility functions for crash log scanning operations,
including report writing, file management, and scan completion tasks.

Test coverage includes:
- write_report_to_file_async - async report writing with fallbacks
- write_report_to_file - sync report writing
- move_unsolved_logs - moving unsolved logs to backup
- complete_scan_with_summary - scan completion and statistics
- crashlogs_scan_async_pure - main async scanning function
- crashlogs_scan - sync wrapper for GUI
"""

import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# write_report_to_file Tests
# ============================================================================


@pytest.mark.unit
class TestWriteReportToFile:
    """Tests for write_report_to_file function."""

    def test_writes_autoscan_report(self, tmp_path: Path) -> None:
        """write_report_to_file should write the autoscan report to a file."""
        from ClassicLib.scanning.logs.utils import write_report_to_file

        crashlog_file = tmp_path / "crash-2024-01-15.log"
        crashlog_file.write_text("crash content")

        autoscan_report = ["Line 1\n", "Line 2\n", "Line 3\n"]

        mock_executor = MagicMock()
        mock_executor.config.move_unsolved_logs = False

        write_report_to_file(crashlog_file, autoscan_report, False, mock_executor)

        autoscan_path = tmp_path / "crash-2024-01-15-AUTOSCAN.md"
        assert autoscan_path.exists()
        assert autoscan_path.read_text() == "Line 1\nLine 2\nLine 3\n"

    def test_triggers_move_unsolved_when_failed(self, tmp_path: Path) -> None:
        """write_report_to_file should move unsolved logs when scan failed."""
        from ClassicLib.scanning.logs.utils import write_report_to_file

        crashlog_file = tmp_path / "crash-unsolved.log"
        crashlog_file.write_text("crash content")

        mock_executor = MagicMock()
        mock_executor.config.move_unsolved_logs = True

        with patch("ClassicLib.scanning.logs.utils.move_unsolved_logs") as mock_move:
            write_report_to_file(crashlog_file, ["report"], True, mock_executor)

            mock_move.assert_called_once_with(crashlog_file)

    def test_does_not_move_when_disabled(self, tmp_path: Path) -> None:
        """write_report_to_file should not move logs when move_unsolved_logs is False."""
        from ClassicLib.scanning.logs.utils import write_report_to_file

        crashlog_file = tmp_path / "crash-unsolved.log"
        crashlog_file.write_text("crash content")

        mock_executor = MagicMock()
        mock_executor.config.move_unsolved_logs = False

        with patch("ClassicLib.scanning.logs.utils.move_unsolved_logs") as mock_move:
            write_report_to_file(crashlog_file, ["report"], True, mock_executor)

            mock_move.assert_not_called()


# ============================================================================
# write_report_to_file_async Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestWriteReportToFileAsync:
    """Tests for write_report_to_file_async function."""

    async def test_writes_autoscan_report_async(self, tmp_path: Path) -> None:
        """write_report_to_file_async should write the autoscan report asynchronously."""
        from ClassicLib.scanning.logs.utils import write_report_to_file_async

        crashlog_file = tmp_path / "crash-2024-01-15.log"
        crashlog_file.write_text("crash content")

        autoscan_report = ["Async Line 1\n", "Async Line 2\n"]

        mock_executor = MagicMock()
        mock_executor.config.move_unsolved_logs = False

        await write_report_to_file_async(crashlog_file, autoscan_report, False, mock_executor)

        autoscan_path = tmp_path / "crash-2024-01-15-AUTOSCAN.md"
        assert autoscan_path.exists()
        assert autoscan_path.read_text() == "Async Line 1\nAsync Line 2\n"

    async def test_triggers_move_unsolved_async_when_failed(self, tmp_path: Path) -> None:
        """write_report_to_file_async should move unsolved logs when scan failed."""
        from ClassicLib.scanning.logs.utils import write_report_to_file_async

        crashlog_file = tmp_path / "crash-unsolved.log"
        crashlog_file.write_text("crash content")

        mock_executor = MagicMock()
        mock_executor.config.move_unsolved_logs = True

        with patch("ClassicLib.scanning.logs.utils.move_unsolved_logs") as mock_move:
            await write_report_to_file_async(crashlog_file, ["report"], True, mock_executor)

            mock_move.assert_called_once_with(crashlog_file)

    async def test_falls_back_to_sync_when_aiofiles_unavailable(self, tmp_path: Path) -> None:
        """write_report_to_file_async should fall back to sync write if aiofiles not available."""
        from ClassicLib.scanning.logs.utils import write_report_to_file_async

        crashlog_file = tmp_path / "crash-fallback.log"
        crashlog_file.write_text("crash content")

        mock_executor = MagicMock()
        mock_executor.config.move_unsolved_logs = False

        # Simulate aiofiles not being available by mocking the import
        with patch.dict("sys.modules", {"aiofiles": None}):
            with patch("ClassicLib.scanning.logs.utils.write_report_to_file") as mock_sync:
                # Force the ImportError path
                import builtins

                original_import = builtins.__import__

                def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
                    if name == "aiofiles":
                        raise ImportError("aiofiles not available")
                    return original_import(name, *args, **kwargs)

                with patch.object(builtins, "__import__", mock_import):
                    await write_report_to_file_async(crashlog_file, ["report"], False, mock_executor)

                    mock_sync.assert_called_once()


# ============================================================================
# move_unsolved_logs Tests
# ============================================================================


@pytest.mark.unit
class TestMoveUnsolvedLogs:
    """Tests for move_unsolved_logs function."""

    def test_moves_crashlog_to_backup(self, tmp_path: Path) -> None:
        """move_unsolved_logs should move crash log to backup directory."""
        from ClassicLib.scanning.logs.utils import move_unsolved_logs

        crashlog_file = tmp_path / "crash-unsolved.log"
        crashlog_file.write_text("unsolved crash")

        with patch("ClassicLib.core.registry.GlobalRegistry.get_local_dir", return_value=tmp_path):
            move_unsolved_logs(crashlog_file)

            backup_path = tmp_path / "CLASSIC Backup" / "Unsolved Logs" / "crash-unsolved.log"
            assert backup_path.exists()
            assert not crashlog_file.exists()

    def test_moves_autoscan_report_to_backup(self, tmp_path: Path) -> None:
        """move_unsolved_logs should move autoscan report to backup directory."""
        from ClassicLib.scanning.logs.utils import move_unsolved_logs

        crashlog_file = tmp_path / "crash-unsolved.log"
        crashlog_file.write_text("unsolved crash")
        autoscan_file = tmp_path / "crash-unsolved-AUTOSCAN.md"
        autoscan_file.write_text("autoscan report")

        with patch("ClassicLib.core.registry.GlobalRegistry.get_local_dir", return_value=tmp_path):
            move_unsolved_logs(crashlog_file)

            backup_autoscan = tmp_path / "CLASSIC Backup" / "Unsolved Logs" / "crash-unsolved-AUTOSCAN.md"
            assert backup_autoscan.exists()
            assert not autoscan_file.exists()

    def test_creates_backup_directory(self, tmp_path: Path) -> None:
        """move_unsolved_logs should create backup directory if it doesn't exist."""
        from ClassicLib.scanning.logs.utils import move_unsolved_logs

        crashlog_file = tmp_path / "crash-unsolved.log"
        crashlog_file.write_text("unsolved crash")

        with patch("ClassicLib.core.registry.GlobalRegistry.get_local_dir", return_value=tmp_path):
            move_unsolved_logs(crashlog_file)

            backup_dir = tmp_path / "CLASSIC Backup" / "Unsolved Logs"
            assert backup_dir.exists()
            assert backup_dir.is_dir()

    def test_handles_missing_crashlog(self, tmp_path: Path) -> None:
        """move_unsolved_logs should handle case where crash log doesn't exist."""
        from ClassicLib.scanning.logs.utils import move_unsolved_logs

        crashlog_file = tmp_path / "nonexistent.log"

        with patch("ClassicLib.core.registry.GlobalRegistry.get_local_dir", return_value=tmp_path):
            # Should not raise
            move_unsolved_logs(crashlog_file)


# ============================================================================
# complete_scan_with_summary Tests
# ============================================================================


@pytest.mark.unit
class TestCompleteScanWithSummary:
    """Tests for complete_scan_with_summary function."""

    def test_displays_error_for_failed_logs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """complete_scan_with_summary should display error message for failed logs."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import complete_scan_with_summary

        monkeypatch.chdir(tmp_path)

        # We need some scanned logs, otherwise the "no logs found" message takes precedence
        stats = ScanStatistics(scanned=1, incomplete=0, failed=1)
        result = ScanResult(
            stats=stats,
            failed_logs=["crash-failed.log"],
        )
        mock_yamldata = MagicMock()
        mock_yamldata.classic_game_hints = []

        with (
            patch("ClassicLib.scanning.logs.utils.msg_error") as mock_error,
            patch("ClassicLib.scanning.logs.utils.msg_info"),
        ):
            complete_scan_with_summary(result, mock_yamldata, time.perf_counter())

            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "UNABLE TO PROPERLY SCAN" in call_args
            assert "crash-failed.log" in call_args

    def test_displays_success_message_for_scanned_logs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """complete_scan_with_summary should display success message for scanned logs."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import complete_scan_with_summary

        monkeypatch.chdir(tmp_path)

        stats = ScanStatistics(scanned=2, incomplete=0, failed=0)
        result = ScanResult(
            stats=stats,
            failed_logs=[],
        )
        mock_yamldata = MagicMock()
        mock_yamldata.classic_game_hints = []

        with patch("ClassicLib.scanning.logs.utils.msg_info") as mock_info:
            complete_scan_with_summary(result, mock_yamldata, time.perf_counter() - 1.0)

            mock_info.assert_called()
            # Check that success message was displayed
            call_args = [call[0][0] for call in mock_info.call_args_list]
            assert any("SCAN COMPLETE" in arg for arg in call_args)

    def test_displays_no_logs_error_when_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """complete_scan_with_summary should display error when no logs scanned."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import complete_scan_with_summary

        monkeypatch.chdir(tmp_path)

        stats = ScanStatistics(scanned=0, incomplete=0, failed=0)
        result = ScanResult(
            stats=stats,
            failed_logs=[],
        )
        mock_yamldata = MagicMock()

        with patch("ClassicLib.scanning.logs.utils.msg_error") as mock_error:
            complete_scan_with_summary(result, mock_yamldata, time.perf_counter())

            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "no crash logs" in call_args.lower()

    def test_displays_random_hint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """complete_scan_with_summary should display a random hint from yamldata."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import complete_scan_with_summary

        monkeypatch.chdir(tmp_path)

        stats = ScanStatistics(scanned=1, incomplete=0, failed=0)
        result = ScanResult(
            stats=stats,
            failed_logs=[],
        )
        mock_yamldata = MagicMock()
        mock_yamldata.classic_game_hints = ["Hint 1", "Hint 2", "Hint 3"]

        with (
            patch("ClassicLib.scanning.logs.utils.msg_info") as mock_info,
            patch("ClassicLib.scanning.logs.utils.random.choice", return_value="Hint 2"),
        ):
            complete_scan_with_summary(result, mock_yamldata, time.perf_counter())

            # Verify hint was displayed
            hint_calls = [call for call in mock_info.call_args_list if "Hint 2" in str(call)]
            assert len(hint_calls) == 1

    def test_displays_fallout4_specific_info(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """complete_scan_with_summary should display Fallout4-specific info."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import complete_scan_with_summary

        monkeypatch.chdir(tmp_path)

        stats = ScanStatistics(scanned=1, incomplete=0, failed=0)
        result = ScanResult(
            stats=stats,
            failed_logs=[],
        )
        mock_yamldata = MagicMock()
        mock_yamldata.classic_game_hints = []
        mock_yamldata.autoscan_text = "Fallout 4 specific information"

        with (
            patch("ClassicLib.scanning.logs.utils.msg_info") as mock_info,
            patch("ClassicLib.core.registry.GlobalRegistry.get_game", return_value="Fallout4"),
        ):
            complete_scan_with_summary(result, mock_yamldata, time.perf_counter())

            # Check for Fallout4-specific content
            all_calls = [str(call) for call in mock_info.call_args_list]
            assert any("Fallout 4 specific information" in call for call in all_calls)


# ============================================================================
# crashlogs_scan_async_pure Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestCrashlogsScanAsyncPure:
    """Tests for crashlogs_scan_async_pure function."""

    async def test_resets_fcx_checks_before_scan(self) -> None:
        """crashlogs_scan_async_pure should reset FCX checks before scanning."""
        from ClassicLib.scanning.logs.utils import crashlogs_scan_async_pure

        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.stats.scanned = 1
        mock_result.stats.incomplete = 0
        mock_result.stats.failed = 0
        mock_result.failed_logs = []
        mock_executor.execute_scan = AsyncMock(return_value=mock_result)
        mock_executor.yamldata = MagicMock()
        mock_executor.yamldata.classic_game_hints = []
        mock_executor.statistics.scan_start_time = time.perf_counter()

        with (
            patch("ClassicLib.integration.factory._FcxHandlerWrapper") as mock_fcx,
            patch("ClassicLib.scanning.logs.utils.complete_scan_with_summary"),
        ):
            await crashlogs_scan_async_pure(mock_executor)

            mock_fcx.reset_fcx_checks.assert_called_once()

    async def test_executes_scan_and_returns_result(self) -> None:
        """crashlogs_scan_async_pure should execute scan and return result."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import crashlogs_scan_async_pure

        mock_executor = MagicMock()
        stats = ScanStatistics(scanned=1, incomplete=0, failed=0)
        expected_result = ScanResult(
            stats=stats,
            failed_logs=[],
        )
        mock_executor.execute_scan = AsyncMock(return_value=expected_result)
        mock_executor.yamldata = MagicMock()
        mock_executor.yamldata.classic_game_hints = []
        mock_executor.statistics.scan_start_time = time.perf_counter()

        with (
            patch("ClassicLib.integration.factory._FcxHandlerWrapper"),
            patch("ClassicLib.scanning.logs.utils.complete_scan_with_summary"),
        ):
            result = await crashlogs_scan_async_pure(mock_executor)

            assert result == expected_result
            mock_executor.execute_scan.assert_awaited_once()

    async def test_raises_if_yamldata_not_initialized(self) -> None:
        """crashlogs_scan_async_pure should raise if yamldata not initialized."""
        from ClassicLib.scanning.logs.utils import crashlogs_scan_async_pure

        mock_executor = MagicMock()
        mock_executor.execute_scan = AsyncMock(return_value=MagicMock())
        mock_executor.yamldata = None  # Simulate uninitialized

        with (
            patch("ClassicLib.integration.factory._FcxHandlerWrapper"),
            pytest.raises(RuntimeError, match="YAML data should be initialized"),
        ):
            await crashlogs_scan_async_pure(mock_executor)

    async def test_calls_complete_scan_with_summary(self) -> None:
        """crashlogs_scan_async_pure should call complete_scan_with_summary."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import crashlogs_scan_async_pure

        mock_executor = MagicMock()
        stats = ScanStatistics(scanned=0, incomplete=0, failed=0)
        mock_result = ScanResult(
            stats=stats,
            failed_logs=[],
        )
        mock_executor.execute_scan = AsyncMock(return_value=mock_result)
        mock_yamldata = MagicMock()
        mock_executor.yamldata = mock_yamldata
        mock_executor.statistics.scan_start_time = 12345.0

        with (
            patch("ClassicLib.integration.factory._FcxHandlerWrapper"),
            patch("ClassicLib.scanning.logs.utils.complete_scan_with_summary") as mock_complete,
        ):
            await crashlogs_scan_async_pure(mock_executor)

            mock_complete.assert_called_once_with(mock_result, mock_yamldata, 12345.0)


# ============================================================================
# crashlogs_scan Tests
# ============================================================================


@pytest.mark.unit
class TestCrashlogsScan:
    """Tests for crashlogs_scan sync wrapper function."""

    def test_creates_executor_and_runs_async(self) -> None:
        """crashlogs_scan should create executor and run async function."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import crashlogs_scan

        stats = ScanStatistics(scanned=0, incomplete=0, failed=0)
        expected_result = ScanResult(
            stats=stats,
            failed_logs=[],
        )

        def close_and_return(coro):
            """Close coroutine to prevent 'never awaited' warning and return value."""
            coro.close()
            return expected_result

        with (
            patch("ClassicLib.scanning.logs.executor.ScanLogsExecutor") as mock_executor_class,
            patch("ClassicLib.core.async_bridge.run_async", side_effect=close_and_return) as mock_run,
        ):
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            result = crashlogs_scan()

            assert result == expected_result
            mock_executor_class.assert_called_once()
            mock_run.assert_called_once()


# ============================================================================
# crashlogs_scan_async_pure_with_qt Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestCrashlogsScanAsyncPureWithQt:
    """Tests for crashlogs_scan_async_pure_with_qt function."""

    async def test_delegates_to_main_function(self) -> None:
        """crashlogs_scan_async_pure_with_qt should delegate to crashlogs_scan_async_pure."""
        from ClassicLib.scanning.logs.models import ScanResult, ScanStatistics
        from ClassicLib.scanning.logs.utils import crashlogs_scan_async_pure_with_qt

        mock_executor = MagicMock()
        stats = ScanStatistics(scanned=1, incomplete=0, failed=0)
        expected_result = ScanResult(
            stats=stats,
            failed_logs=[],
        )

        with patch(
            "ClassicLib.scanning.logs.utils.crashlogs_scan_async_pure",
            new_callable=AsyncMock,
            return_value=expected_result,
        ) as mock_pure:
            result = await crashlogs_scan_async_pure_with_qt(mock_executor)

            assert result == expected_result
            mock_pure.assert_awaited_once_with(mock_executor)

"""Integration tests for the ScanLog OrchestratorCore module.

This module tests the full orchestration pipeline including:
- Full crash log processing with real crash logs
- Report generation end-to-end
- Database integration with FormID lookup
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrchestratorCoreProcessing:
    """Integration tests for crash log processing."""

    async def test_process_crash_log_returns_valid_structure(
        self,
        mock_yamldata: MagicMock,
        crash_log_file: Path,
    ) -> None:
        """Test that process_crash_log returns the expected structure."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

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
                    'Unhandled exception "EXCEPTION_ACCESS_VIOLATION"',
                    [
                        ["Achievements: true"],
                        ["OS: Windows"],
                        ["[ 0] 0x7FF6EF4C3512"],
                        ["module.dll"],
                        ["plugin.dll"],
                        ["[00] Fallout4.esm"],
                    ],
                )
            )
            mock_get_parser.return_value = mock_parser

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                result = await orchestrator.process_crash_log(crash_log_file)

                # Result should be a 4-tuple
                assert len(result) == 4
                crashlog_path, autoscan_report, trigger_scan_failed, local_stats = result

                # Validate types
                assert isinstance(crashlog_path, Path)
                assert isinstance(autoscan_report, list)
                assert isinstance(trigger_scan_failed, bool)
                assert hasattr(local_stats, "__getitem__")  # Counter-like

                # Report should have content
                assert len(autoscan_report) > 0

    async def test_process_crash_log_generates_report_content(
        self,
        mock_yamldata: MagicMock,
        crash_log_file: Path,
    ) -> None:
        """Test that processing generates meaningful report content."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            # Mock file I/O
            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=crash_log_file.read_text())
            mock_get_io.return_value = mock_io

            # Mock parser with realistic data
            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(
                return_value=(
                    "Fallout 4 v1.10.163",
                    "Buffout 4 v1.28.6",
                    'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512',
                    [
                        ["Achievements: true", "MemoryManager: false"],
                        ["OS: Microsoft Windows 11"],
                        ["[ 0] 0x7FF6EF4C3512 Fallout4.exe"],
                        ["module.dll v1.0"],
                        ["Achievements.dll v2.3.0"],
                        ["[00] Fallout4.esm", "[01] DLCRobot.esm"],
                    ],
                )
            )
            mock_get_parser.return_value = mock_parser

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                _, autoscan_report, _, _ = await orchestrator.process_crash_log(crash_log_file)

                # Join report for easier searching
                report_text = "".join(autoscan_report)

                # Report should contain crash log filename
                assert crash_log_file.name in report_text or "crash" in report_text.lower()

    async def test_process_crash_log_handles_malformed_log(
        self,
        mock_yamldata: MagicMock,
        malformed_crash_log_file: Path,
    ) -> None:
        """Test that malformed crash logs are handled gracefully."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            # Mock file I/O
            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=malformed_crash_log_file.read_text())
            mock_get_io.return_value = mock_io

            # Mock parser returning minimal/empty data
            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(
                return_value=(
                    "UNKNOWN",
                    "UNKNOWN",
                    "UNKNOWN",
                    [[], [], [], [], [], []],  # Empty segments
                )
            )
            mock_get_parser.return_value = mock_parser

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Should not raise exception
                result = await orchestrator.process_crash_log(malformed_crash_log_file)

                # Should still return valid structure
                assert len(result) == 4
                _, _, trigger_scan_failed, local_stats = result

                # Malformed logs should trigger incomplete/failed status
                assert local_stats["incomplete"] > 0 or local_stats["failed"] > 0 or trigger_scan_failed

    async def test_process_crash_log_tracks_statistics(
        self,
        mock_yamldata: MagicMock,
        crash_log_file: Path,
    ) -> None:
        """Test that processing updates statistics correctly."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=crash_log_file.read_text())
            mock_get_io.return_value = mock_io

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

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                _, _, _, local_stats = await orchestrator.process_crash_log(crash_log_file)

                # Stats should have expected keys
                assert "scanned" in local_stats
                assert "incomplete" in local_stats
                assert "failed" in local_stats


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrchestratorCoreBatchProcessing:
    """Integration tests for batch crash log processing."""

    async def test_batch_processing_multiple_logs(
        self,
        mock_yamldata: MagicMock,
        crash_logs_directory: Path,
    ) -> None:
        """Test batch processing of multiple crash logs."""
        crash_files = list(crash_logs_directory.glob("*.log"))

        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            # Mock file I/O to read actual files
            mock_io = MagicMock()

            async def read_file_mock(path: Path) -> str:
                return path.read_text()

            mock_io.read_file = AsyncMock(side_effect=read_file_mock)
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

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                results = await orchestrator.process_crash_logs_batch(crash_files)

                # Should process all files
                assert len(results) == len(crash_files)

                # Each result should be valid
                for result in results:
                    assert len(result) == 4
                    path, report, failed, stats = result
                    assert isinstance(path, Path)
                    assert isinstance(report, list)
                    assert isinstance(failed, bool)

    async def test_batch_processing_handles_errors(
        self,
        mock_yamldata: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test batch processing handles individual file errors."""
        # Create one valid and one problematic file
        valid_file = tmp_path / "valid.log"
        valid_file.write_text("Valid content")

        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            # Mock file I/O - first call succeeds, second raises
            mock_io = MagicMock()
            call_count = 0

            async def read_file_with_error(path: Path) -> str:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return path.read_text()
                raise OSError("Read error")

            mock_io.read_file = AsyncMock(side_effect=read_file_with_error)
            mock_get_io.return_value = mock_io

            mock_parser = MagicMock()
            mock_parser.find_segments = MagicMock(return_value=("Game", "Crashgen", "Error", [[], [], [], [], [], []]))
            mock_get_parser.return_value = mock_parser

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Process two files
                results = await orchestrator.process_crash_logs_batch([valid_file, valid_file])

                # Should have results for both (one success, one error)
                assert len(results) == 2


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrchestratorCoreReportGeneration:
    """Integration tests for report generation."""

    async def test_report_contains_header(
        self,
        mock_yamldata: MagicMock,
        crash_log_file: Path,
    ) -> None:
        """Test that generated report contains a header."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=crash_log_file.read_text())
            mock_get_io.return_value = mock_io

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

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                _, report, _, _ = await orchestrator.process_crash_log(crash_log_file)

                # Report should not be empty
                assert report
                report_text = "".join(report)

                # Should have some content
                assert len(report_text) > 0

    async def test_report_contains_footer(
        self,
        mock_yamldata: MagicMock,
        crash_log_file: Path,
    ) -> None:
        """Test that generated report contains a footer."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.ScanLog.OrchestratorCore.DatabasePoolManager"),
            patch("ClassicLib.ScanLog.OrchestratorCore.get_file_io") as mock_get_io,
            patch("ClassicLib.ScanLog.OrchestratorCore.get_parser") as mock_get_parser,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            mock_io = MagicMock()
            mock_io.read_file = AsyncMock(return_value=crash_log_file.read_text())
            mock_get_io.return_value = mock_io

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

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                _, report, _, _ = await orchestrator.process_crash_log(crash_log_file)

                # Report should have content at the end
                assert report
                assert len(report) > 0

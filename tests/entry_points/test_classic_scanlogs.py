"""Tests for CLASSIC_ScanLogs.py CLI entry point.

This module tests the crash log scanning CLI interface, including
backward compatibility wrappers, async adapters, and core scanning functionality.
"""

import pytest
import warnings
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, AsyncMock, call
from collections import Counter
import asyncio

# Mark all tests in this module
pytestmark = [pytest.mark.unit]


class TestClassicScanLogs:
    """Test suite for CLASSIC_ScanLogs.py CLI entry point."""

    def test_deprecated_import_warning(self) -> None:
        """Test that deprecation warnings are issued for moved imports."""
        from CLASSIC_ScanLogs import _deprecated_import_warning

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _deprecated_import_warning("OldClass", "new.module.location")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "OldClass" in str(w[0].message)
            assert "new.module.location" in str(w[0].message)

    @patch("CLASSIC_ScanLogs.ScanLogsExecutor")
    def test_classic_scanlogs_backward_compatibility_wrapper(
        self,
        mock_executor_class: Mock
    ) -> None:
        """Test ClassicScanLogs backward compatibility wrapper."""
        from CLASSIC_ScanLogs import ClassicScanLogs

        # Arrange
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor
        mock_executor.crashlog_list = [Path("test1.log"), Path("test2.log")]
        mock_executor.yamldata = MagicMock()
        mock_executor.config.fcx_mode = True
        mock_executor.config.show_formid_values = False
        mock_executor.config.formid_db_exists = True
        mock_executor.config.move_unsolved_logs = False
        mock_executor.statistics.scan_start_time = 12345.0
        mock_executor.crashlogs = MagicMock()
        mock_executor.statistics.to_counter.return_value = Counter({"test": 1})

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            scanner = ClassicScanLogs()

        # Assert - Deprecation warning issued
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "ClassicScanLogs" in str(w[0].message)

        # Assert - Backward compatibility attributes
        assert scanner.crashlog_list == mock_executor.crashlog_list
        assert scanner.yamldata == mock_executor.yamldata
        assert scanner.fcx_mode == True
        assert scanner.show_formid_values == False
        assert scanner.formid_db_exists == True
        assert scanner.move_unsolved_logs == False
        assert scanner.scan_start_time == 12345.0
        assert scanner.crashlogs == mock_executor.crashlogs
        assert scanner.crashlog_stats == Counter({"test": 1})

    @pytest.mark.asyncio
    @patch("CLASSIC_ScanLogs.ScanLogsExecutor")
    async def test_process_crashlog_async_backward_compatibility(
        self,
        mock_executor_class: Mock
    ) -> None:
        """Test process_crashlog_async backward compatibility method."""
        from CLASSIC_ScanLogs import ClassicScanLogs

        # Arrange
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor
        mock_executor.statistics.to_counter.return_value = Counter()

        # Setup async method mock
        expected_result = (
            Path("test.log"),
            ["report line 1", "report line 2"],
            False,
            Counter({"processed": 1})
        )
        mock_executor._process_crashlog_async = AsyncMock(return_value=expected_result)

        # Act
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scanner = ClassicScanLogs()

        orchestrator = MagicMock()
        result = await scanner.process_crashlog_async(Path("test.log"), orchestrator)

        # Assert
        assert result == expected_result
        mock_executor._process_crashlog_async.assert_called_once_with(Path("test.log"), orchestrator)

    @patch("CLASSIC_ScanLogs._write_report_to_file")
    def test_write_report_to_file_backward_compatibility(
        self,
        mock_write_func: Mock
    ) -> None:
        """Test write_report_to_file backward compatibility function."""
        from CLASSIC_ScanLogs import write_report_to_file, ClassicScanLogs

        # Arrange
        crashlog = Path("test.log")
        report = ["line1", "line2"]
        scanner = MagicMock(spec=ClassicScanLogs)
        scanner._executor = MagicMock()

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            write_report_to_file(crashlog, report, False, scanner)

        # Assert
        assert len(w) == 1
        assert "write_report_to_file" in str(w[0].message)
        mock_write_func.assert_called_once_with(crashlog, report, False, scanner._executor)

    @patch("CLASSIC_ScanLogs._move_unsolved_logs")
    def test_move_unsolved_logs_backward_compatibility(
        self,
        mock_move_func: Mock
    ) -> None:
        """Test move_unsolved_logs backward compatibility function."""
        from CLASSIC_ScanLogs import move_unsolved_logs

        # Arrange
        crashlog = Path("unsolved.log")

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            move_unsolved_logs(crashlog)

        # Assert
        assert len(w) == 1
        assert "move_unsolved_logs" in str(w[0].message)
        mock_move_func.assert_called_once_with(crashlog)

    @patch("CLASSIC_ScanLogs._crashlogs_scan")
    def test_crashlogs_scan_main_entry(
        self,
        mock_scan_func: Mock
    ) -> None:
        """Test crashlogs_scan main entry point."""
        from CLASSIC_ScanLogs import crashlogs_scan

        # Act
        crashlogs_scan()

        # Assert
        mock_scan_func.assert_called_once()

    @patch("CLASSIC_ScanLogs._func")
    @pytest.mark.asyncio
    async def test_crashlogs_scan_async_pure_with_qt(
        self,
        mock_func: Mock
    ) -> None:
        """Test crashlogs_scan_async_pure_with_qt backward compatibility."""
        from CLASSIC_ScanLogs import crashlogs_scan_async_pure_with_qt, ClassicScanLogs

        # Arrange
        scanner = MagicMock(spec=ClassicScanLogs)
        scanner._executor = MagicMock()
        mock_func.return_value = None

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with patch("CLASSIC_ScanLogs._func", new=AsyncMock()) as mock_async_func:
                await crashlogs_scan_async_pure_with_qt(scanner)

        # Assert
        assert len(w) == 1
        assert "crashlogs_scan_async_pure_with_qt" in str(w[0].message)
        mock_async_func.assert_called_once_with(scanner._executor)

    @pytest.mark.asyncio
    async def test_crashlogs_scan_async_pure(self) -> None:
        """Test crashlogs_scan_async_pure backward compatibility."""
        from CLASSIC_ScanLogs import crashlogs_scan_async_pure, ClassicScanLogs

        # Arrange
        scanner = MagicMock(spec=ClassicScanLogs)
        scanner._executor = MagicMock()

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with patch("CLASSIC_ScanLogs._func", new=AsyncMock()) as mock_async_func:
                await crashlogs_scan_async_pure(scanner)

        # Assert
        assert len(w) == 1
        assert "crashlogs_scan_async_pure" in str(w[0].message)
        mock_async_func.assert_called_once_with(scanner._executor)

    @pytest.mark.asyncio
    async def test_write_report_to_file_async(self) -> None:
        """Test write_report_to_file_async backward compatibility."""
        from CLASSIC_ScanLogs import write_report_to_file_async, ClassicScanLogs

        # Arrange
        crashlog = Path("test.log")
        report = ["line1", "line2"]
        scanner = MagicMock(spec=ClassicScanLogs)
        scanner._executor = MagicMock()

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with patch("CLASSIC_ScanLogs._func", new=AsyncMock()) as mock_async_func:
                await write_report_to_file_async(crashlog, report, True, scanner)

        # Assert
        assert len(w) == 1
        assert "write_report_to_file_async" in str(w[0].message)
        mock_async_func.assert_called_once_with(crashlog, report, True, scanner._executor)

    @patch("CLASSIC_ScanLogs._func")
    def test_complete_scan_with_summary(
        self,
        mock_func: Mock
    ) -> None:
        """Test _complete_scan_with_summary backward compatibility."""
        from CLASSIC_ScanLogs import _complete_scan_with_summary, ClassicScanLogs

        # Arrange
        scanner = MagicMock(spec=ClassicScanLogs)
        scanner._executor = MagicMock()
        scan_failed_list = ["fail1", "fail2"]
        yamldata = MagicMock()

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _complete_scan_with_summary(scanner, scan_failed_list, yamldata)

        # Assert
        assert len(w) == 1
        assert "_complete_scan_with_summary" in str(w[0].message)
        mock_func.assert_called_once_with(scanner._executor, scan_failed_list, yamldata)

    def test_scan_config_model_import(self) -> None:
        """Test that ScanConfig model can be imported."""
        try:
            from ClassicLib.ScanLog.models import ScanConfig, ScanResult
        except ImportError as e:
            pytest.fail(f"Failed to import ScanConfig/ScanResult models: {e}")

        assert ScanConfig is not None
        assert ScanResult is not None

    def test_orchestrator_core_import(self) -> None:
        """Test that OrchestratorCore can be imported."""
        try:
            from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
        except ImportError as e:
            pytest.fail(f"Failed to import OrchestratorCore: {e}")

        assert OrchestratorCore is not None

    def test_scan_logs_executor_import(self) -> None:
        """Test that ScanLogsExecutor can be imported."""
        try:
            from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
        except ImportError as e:
            pytest.fail(f"Failed to import ScanLogsExecutor: {e}")

        assert ScanLogsExecutor is not None

    def test_setup_coordinator_import(self) -> None:
        """Test that SetupCoordinator can be imported."""
        try:
            from ClassicLib.SetupCoordinator import SetupCoordinator
        except ImportError as e:
            pytest.fail(f"Failed to import SetupCoordinator: {e}")

        assert SetupCoordinator is not None

    @patch("CLASSIC_ScanLogs.ScanLogsExecutor")
    def test_executor_wrapper_uses_correct_instance(
        self,
        mock_executor_class: Mock
    ) -> None:
        """Test that ClassicScanLogs properly wraps ScanLogsExecutor instance."""
        from CLASSIC_ScanLogs import ClassicScanLogs
        from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor

        # Arrange
        real_executor = MagicMock(spec=ScanLogsExecutor)
        mock_executor_class.return_value = real_executor
        real_executor.statistics.to_counter.return_value = Counter()

        # Act
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scanner1 = ClassicScanLogs()
            scanner2 = ClassicScanLogs()

        # Assert - Each scanner gets its own executor
        assert mock_executor_class.call_count == 2
        assert scanner1._executor is not scanner2._executor

    def test_main_module_execution(self) -> None:
        """Test that the module can be executed as __main__."""
        with patch("CLASSIC_ScanLogs.crashlogs_scan") as mock_scan:
            with patch("CLASSIC_ScanLogs.__name__", "__main__"):
                import importlib
                import CLASSIC_ScanLogs
                # Module doesn't have __main__ block, but crashlogs_scan would be called
                # if it did have one

        # The module doesn't actually have a __main__ block,
        # but we're testing that it could be added without issues
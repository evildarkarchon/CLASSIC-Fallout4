"""
Integration tests for crash_log_processing - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

import pytest

from CLASSIC_ScanLogs import ClassicScanLogs
from ClassicLib import GlobalRegistry

pytestmark = pytest.mark.integration


@pytest.fixture
def sample_crashlog() -> str:
    """Return text content of a sample crash log."""
    return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

PROBABLE CALL STACK:
  [0] 0x7FF6EF4C3512 Fallout4.exe+0733512
  [1] 0x7FF6EF4C3513 Fallout4.exe+0733513
"""

@pytest.mark.integration
@pytest.mark.asyncio
class TestCrashLogProcessingIntegration:
    """Integration tests for crash log processing."""

    async def test_end_to_end_scan_logs(self, tmp_path: Path, sample_crashlog: str, message_handler) -> None:
        """Test the entire crash log scanning process - Phase 5: Native async."""
        crash_dir: Path = tmp_path / 'Crash Logs'
        crash_dir.mkdir(exist_ok=True)
        crash_log_files: list[Any] = []
        for i in range(3):
            crash_file: Path = crash_dir / f'crash-2023-01-0{i + 1}-00-00-00.log'
            crash_file.write_text(sample_crashlog)
            crash_log_files.append(crash_file)
        with patch('ClassicLib.YamlSettingsCache.yaml_settings') as mock_yaml, patch('ClassicLib.YamlSettingsCache.classic_settings') as mock_classic, patch('ClassicLib.ScanLog.Util.crashlogs_get_files') as mock_get_files, patch('ClassicLib.ScanLog.Util.crashlogs_reformat'), patch('ClassicLib.ScanLog.ScanLogsUtils.write_report_to_file'):

            def yaml_side_effect(_type_arg: str, _yaml_store: str, key_path: str, _new_value: Any=None) -> dict[str, str] | None | Literal['Buffout 4'] | Literal['F4SE'] | tuple[str, ...]:
                if key_path == 'Game_Info.CRASHGEN_LogName':
                    return 'Buffout 4'
                if key_path == 'Game_Info.XSE_Acronym':
                    return 'F4SE'
                if key_path == 'Mods_Alert_Single':
                    return {'problemplugin': 'This plugin causes crashes.'}
                if key_path == 'Crashlog_Error_Check':
                    return {'HIGH | Access violation': 'EXCEPTION_ACCESS_VIOLATION'}
                if key_path == 'exclude_log_records':
                    return ('unwanted_record',)
                return None
            mock_yaml.side_effect = yaml_side_effect
            mock_classic.return_value = False
            mock_get_files.return_value = crash_log_files
            original_game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
            GlobalRegistry.register(GlobalRegistry.Keys.GAME, 'Fallout4')
            # Ensure YAML cache is registered
            if not GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
                from unittest.mock import MagicMock
                mock_cache = MagicMock()
                GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, mock_cache)
            # Note: ThreadSafeLogCache was removed for performance reasons
            # OrchestratorCore no longer requires crashlogs parameter
            try:
                scanner: ClassicScanLogs = ClassicScanLogs()
                # The scanner's crashlog_list should use our mocked files
                scanner.crashlog_list = crash_log_files
                results: list[Any] = []

                # Phase 5: Use native async instead of AsyncBridge
                from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
                for crash_file in scanner.crashlog_list:
                    async with OrchestratorCore(scanner.yamldata, scanner.fcx_mode, scanner.show_formid_values, scanner.formid_db_exists) as orchestrator:
                        crashlog_file, autoscan_report, trigger_scan_failed, local_stats = await scanner.process_crashlog_async(crash_file, orchestrator)
                        results.append(autoscan_report)

                assert scanner.crashlog_list is not None
                assert len(scanner.crashlog_list) == 3
                assert len(results) == 3
                # Note: mock_get_files is not called because we manually set crashlog_list
            finally:
                if original_game is not None:
                    GlobalRegistry.register(GlobalRegistry.Keys.GAME, original_game)

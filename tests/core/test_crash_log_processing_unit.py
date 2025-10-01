"""
Unit tests for crash_log_processing - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

import pytest

from CLASSIC_ScanLogs import ClassicScanLogs
from ClassicLib import GlobalRegistry

pytestmark = pytest.mark.unit


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


@pytest.fixture
def create_crashlog_file(tmp_path: Path, sample_crashlog: str) -> Path:
    """Create a temporary crash log file for testing."""
    crash_dir: Path = tmp_path / "Crash Logs"
    crash_dir.mkdir(exist_ok=True)

    crash_file: Path = crash_dir / "crash-2023-01-01-00-00-00.log"
    crash_file.write_text(sample_crashlog, encoding="utf-8")
    return crash_file


@pytest.mark.unit
class TestCrashLogProcessingUnit:
    """Unit tests for crash log processing."""

    def test_process_crashlog_unit(self, create_crashlog_file: Path, message_handler, async_bridge) -> None:
        """Test the full process_crashlog function with minimal mocking."""
        crash_file: Path = create_crashlog_file
        with patch('ClassicLib.YamlSettingsCache.yaml_settings') as mock_yaml, patch('ClassicLib.YamlSettingsCache.classic_settings') as mock_classic, patch('ClassicLib.ScanLog.Util.crashlogs_get_files') as mock_get_files, patch('ClassicLib.ScanLog.Util.crashlogs_reformat'):

            def yaml_side_effect(_type_arg: str, _yaml_store: str, key_path: str, _new_value: Any=None) -> dict[str, str] | dict[str, list[str]] | None | Literal['Buffout 4'] | Literal['F4SE']:
                if key_path == 'Game_Info.CRASHGEN_LogName':
                    return 'Buffout 4'
                if key_path == 'Game_Info.XSE_Acronym':
                    return 'F4SE'
                if key_path == 'Mods_Alert_Single':
                    return {'problemplugin': 'This plugin causes crashes.'}
                if key_path == 'Crashlog_Error_Check':
                    return {'HIGH | Access violation': 'EXCEPTION_ACCESS_VIOLATION'}
                if key_path == 'Crashlog_Stack_Check':
                    return {'MEDIUM | Problematic stack': ['Fallout4.exe+0733512']}
                return None
            mock_yaml.side_effect = yaml_side_effect
            mock_get_files.return_value = [crash_file]
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
                from ClassicLib.AsyncBridge import AsyncBridge
                from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore

                async def process_with_orchestrator():
                    async with OrchestratorCore(scanner.yamldata, scanner.fcx_mode, scanner.show_formid_values, scanner.formid_db_exists) as orchestrator:
                        return await scanner.process_crashlog_async(crash_file, orchestrator)

                bridge = AsyncBridge.get_instance()
                result: tuple[Path, list[str], bool, Any] = bridge.run_async(process_with_orchestrator())
                assert result is not None
                assert len(result) == 4
                assert result[0] == crash_file
                assert isinstance(result[1], list)
                assert isinstance(result[2], bool)
            finally:
                if original_game is not None:
                    GlobalRegistry.register(GlobalRegistry.Keys.GAME, original_game)

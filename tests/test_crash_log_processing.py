"""
Integration tests for crash log processing.

This module contains tests that focus on the end-to-end processing
of crash logs, verifying that the full pipeline works correctly.
"""


from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import patch

import pytest

from CLASSIC_ScanLogs import ClassicScanLogs, process_crashlog
from ClassicLib import GlobalRegistry
from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

if TYPE_CHECKING:
    from collections import Counter


@pytest.fixture
def sample_crashlog() -> str:
    """Return text content of a sample crash log."""
    return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

\t[Compatibility]
\t\tF4EE: true
\t[Crashlog]
\t\tPromptUpload: false

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]

PROBABLE CALL STACK:
\t[0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72
\t[1] 0x7FF6EF4C145E Fallout4.exe+073145E -> 825090+0x67E

MODULES:
\tproblematic_module.dll
\ttest_module.dll

F4SE PLUGINS:
\tf4se_plugin1.dll
\tcrash_plugin.dll

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] ProblemPlugin.esp
\t[03] AnotherMod.esp
"""


@pytest.fixture
def create_crashlog_file(tmp_path: Path, sample_crashlog: str) -> Path:
    """Create a temporary crash log file for testing."""
    crash_dir = tmp_path / "Crash Logs"
    crash_dir.mkdir(exist_ok=True)

    crash_file = crash_dir / "crash-2023-01-01-00-00-00.log"
    crash_file.write_text(sample_crashlog)

    return crash_file


@pytest.mark.integration
class TestCrashLogProcessingIntegration:
    """Integration tests for crash log processing."""

    def test_process_crashlog_integration(self, create_crashlog_file: Path) -> None:
        """Test the full process_crashlog function with minimal mocking."""
        crash_file = create_crashlog_file

        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
            # Setup the mock to return values needed for crash processing
            def yaml_side_effect(
                _type_arg: str, _yaml_store: str, key_path: str, _new_value: Any = None
            ) -> dict[str, str] | dict[str, list[str]] | None | Literal["Buffout 4"] | Literal["F4SE"]:
                if key_path == "Game_Info.CRASHGEN_LogName":
                    return "Buffout 4"
                if key_path == "Game_Info.XSE_Acronym":
                    return "F4SE"
                if key_path == "Mods_Alert_Single":
                    return {"problemplugin": "This plugin causes crashes."}
                if key_path == "Crashlog_Error_Check":
                    return {"HIGH | Access violation": "EXCEPTION_ACCESS_VIOLATION"}
                if key_path == "Crashlog_Stack_Check":
                    return {"MEDIUM | Problematic stack": ["Fallout4.exe+0733512"]}
                return None

            mock_yaml.side_effect = yaml_side_effect

            # Register necessary global values
            original_game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
            GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")

            try:
                # Create log cache
                log_cache = ThreadSafeLogCache([crash_file])

                # Process the crash log
                result_data: tuple[Path, list[str], bool, Counter[str]] = process_crashlog(log_cache, crash_file)

                # Verify results
                assert result_data is not None
                assert "crash-2023-01-01-00-00-00" in result_data

                # Check for expected content based on the sample crash log
                assert "EXCEPTION_ACCESS_VIOLATION" in result_data
                assert "ProblemPlugin.esp" in result_data

            finally:
                # Restore original global registry value
                if original_game is not None:
                    GlobalRegistry.register(GlobalRegistry.Keys.GAME, original_game)

    def test_end_to_end_scan_logs(self, tmp_path: Path, sample_crashlog: str) -> None:
        """Test the entire crash log scanning process."""
        # Create crash logs directory with multiple logs
        crash_dir = tmp_path / "Crash Logs"
        crash_dir.mkdir(exist_ok=True)

        # Create multiple crash log files
        for i in range(3):
            crash_file = crash_dir / f"crash-2023-01-0{i + 1}-00-00-00.log"
            crash_file.write_text(sample_crashlog)

        with (
            patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml,
            patch("ClassicLib.YamlSettingsCache.classic_settings") as mock_classic,
            patch("CLASSIC_ScanLogs.crashlogs_get_files") as mock_get_files,
            patch("CLASSIC_ScanLogs.main_combined_result") as mock_main_result,
            patch("CLASSIC_ScanLogs.game_combined_result") as mock_game_result,
            patch("CLASSIC_ScanLogs.write_report_to_file"),  # Mock the write function to prevent actual file writing
        ):
            # Configure mocks
            def yaml_side_effect(
                _type_arg: str, _yaml_store: str, key_path: str, _new_value: Any = None
            ) -> dict[str, str] | None | Literal["Buffout 4"] | Literal["F4SE"]:
                if key_path == "Game_Info.CRASHGEN_LogName":
                    return "Buffout 4"
                if key_path == "Game_Info.XSE_Acronym":
                    return "F4SE"
                if key_path == "Mods_Alert_Single":
                    return {"problemplugin": "This plugin causes crashes."}
                if key_path == "Crashlog_Error_Check":
                    return {"HIGH | Access violation": "EXCEPTION_ACCESS_VIOLATION"}
                return None

            mock_yaml.side_effect = yaml_side_effect
            mock_classic.return_value = False  # Default value for most settings
            mock_get_files.return_value = [crash_dir / f"crash-2023-01-0{i + 1}-00-00-00.log" for i in range(3)]
            mock_main_result.return_value = "Main files result"
            mock_game_result.return_value = "Game files result"

            # Register necessary global values
            original_game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
            GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")

            try:
                # Run the scanner
                scanner = ClassicScanLogs()

                # Process each crash log and collect results
                results = []
                for crash_file in scanner.crashlog_list:
                    crashlog_file, autoscan_report, trigger_scan_failed, local_stats = process_crashlog(scanner, crash_file)
                    results.append(autoscan_report)

                # Verify results
                assert scanner.crashlog_list is not None
                assert len(scanner.crashlog_list) == 3
                assert len(results) == 3

                # Check that expected methods were called
                mock_get_files.assert_called_once()

            finally:
                # Restore original global registry value
                if original_game is not None:
                    GlobalRegistry.register(GlobalRegistry.Keys.GAME, original_game)

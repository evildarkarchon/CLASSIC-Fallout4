"""
Integration tests for crash log processing.

This module contains tests that focus on the end-to-end processing
of crash logs, verifying that the full pipeline works correctly.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import patch

import pytest

from CLASSIC_ScanLogs import ClassicScanLogs
from ClassicLib import GlobalRegistry

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
    crash_dir: Path = tmp_path / "Crash Logs"
    crash_dir.mkdir(exist_ok=True)

    crash_file: Path = crash_dir / "crash-2023-01-01-00-00-00.log"
    crash_file.write_text(sample_crashlog)

    return crash_file


@pytest.mark.integration
class TestCrashLogProcessingIntegration:
    """Integration tests for crash log processing."""

    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_process_crashlog_integration(self, create_crashlog_file: Path) -> None:
        """Test the full process_crashlog function with minimal mocking."""
        crash_file: Path = create_crashlog_file

        with (
            patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml,
            patch("ClassicLib.YamlSettingsCache.classic_settings") as mock_classic,  # noqa: F841
            patch("CLASSIC_ScanLogs.crashlogs_get_files") as mock_get_files,
            patch("CLASSIC_ScanLogs.crashlogs_reformat"),
        ):
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
            mock_get_files.return_value = [crash_file]

            # Register necessary global values
            original_game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
            GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")

            try:
                # Create scanner instance with proper mocking
                scanner: ClassicScanLogs = ClassicScanLogs()

                # Process the crash log using the instance method
                result: tuple[Path, list[str], bool, Counter[str]] = scanner.process_crashlog(crash_file)

                # Verify results
                assert result is not None
                assert len(result) == 4  # Should return a tuple with 4 elements
                assert result[0] == crash_file  # First element should be the crash file path
                assert isinstance(result[1], list)  # Second element should be autoscan_report
                assert isinstance(result[2], bool)  # Third element should be trigger_scan_failed

            finally:
                # Restore original global registry value
                if original_game is not None:
                    GlobalRegistry.register(GlobalRegistry.Keys.GAME, original_game)

    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_end_to_end_scan_logs(self, tmp_path: Path, sample_crashlog: str) -> None:
        """Test the entire crash log scanning process."""
        # Create crash logs directory with multiple logs
        crash_dir: Path = tmp_path / "Crash Logs"
        crash_dir.mkdir(exist_ok=True)

        # Create multiple crash log files
        crash_log_files: list[Any] = []
        for i in range(3):
            crash_file: Path = crash_dir / f"crash-2023-01-0{i + 1}-00-00-00.log"
            crash_file.write_text(sample_crashlog)
            crash_log_files.append(crash_file)

        with (
            patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml,
            patch("ClassicLib.YamlSettingsCache.classic_settings") as mock_classic,
            patch("CLASSIC_ScanLogs.crashlogs_get_files") as mock_get_files,
            patch("CLASSIC_ScanLogs.crashlogs_reformat"),
            patch("CLASSIC_ScanLogs.write_report_to_file"),  # Mock the write function to prevent actual file writing
        ):
            # Configure mocks
            def yaml_side_effect(
                _type_arg: str, _yaml_store: str, key_path: str, _new_value: Any = None
            ) -> dict[str, str] | None | Literal["Buffout 4"] | Literal["F4SE"] | tuple[str, ...]:
                if key_path == "Game_Info.CRASHGEN_LogName":
                    return "Buffout 4"
                if key_path == "Game_Info.XSE_Acronym":
                    return "F4SE"
                if key_path == "Mods_Alert_Single":
                    return {"problemplugin": "This plugin causes crashes."}
                if key_path == "Crashlog_Error_Check":
                    return {"HIGH | Access violation": "EXCEPTION_ACCESS_VIOLATION"}
                if key_path == "exclude_log_records":
                    return ("unwanted_record",)
                return None

            mock_yaml.side_effect = yaml_side_effect
            mock_classic.return_value = False  # Default value for most settings
            mock_get_files.return_value = crash_log_files  # Use our created files

            # Register necessary global values
            original_game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
            GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")

            try:
                # Run the scanner
                scanner: ClassicScanLogs = ClassicScanLogs()

                # Process each crash log and collect results
                results: list[Any] = []
                for crash_file in scanner.crashlog_list:
                    crashlog_file, autoscan_report, trigger_scan_failed, local_stats = scanner.process_crashlog(crash_file)
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

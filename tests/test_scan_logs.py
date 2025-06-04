"""
Test suite for CLASSIC_ScanLogs.py and related functionality.

This module contains tests for the crash log scanning functionality,
including segment extraction, plugin detection, and suspect identification.
"""

import os
import threading
from collections import Counter
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from CLASSIC_ScanLogs import ClassicScanLogs
from ClassicLib import GlobalRegistry
from ClassicLib.Constants import NULL_VERSION, YAML
from ClassicLib.ScanLog.DetectMods import detect_mods_single, detect_mods_double, detect_mods_important
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.Util import get_entry
from ClassicLib.YamlSettingsCache import yaml_settings


@pytest.fixture
def setup_global_registry() -> Generator:
    """Set up test values in the global registry."""
    # Save original values to restore them after tests
    original_game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
    original_vr = GlobalRegistry.get(GlobalRegistry.Keys.VR)

    # Register test values
    GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
    GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

    yield

    # Restore original values
    if original_game is not None:
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, original_game)
    if original_vr is not None:
        GlobalRegistry.register(GlobalRegistry.Keys.VR, original_vr)


@pytest.fixture
def mock_yaml_settings() -> Generator:
    """Mock the yaml_settings function to return test values."""
    with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
        # Configure the mock to return appropriate values for different calls
        def side_effect(type_arg, yaml_store, key_path, new_value=None):
            # Handle special cases based on arguments
            if key_path == "catch_log_records":
                return ["Record1", "Record2"]
            if key_path == "Game_Info.CRASHGEN_LogName":
                return "Buffout 4"
            if key_path == "Game_Info.XSE_Acronym":
                return "F4SE"
            if isinstance(yaml_store, YAML) and yaml_store == YAML.Game and "Mods_" in key_path:
                return {"test_mod": "Test mod warning message"}
            if key_path == "Crashlog_Error_Check":
                return {"HIGH | Test Error": "error_signal"}
            if key_path == "Crashlog_Stack_Check":
                return {"MEDIUM | Stack Error": ["required:signal1", "optional:signal2"]}
            # Default return
            return None

        mock_yaml.side_effect = side_effect
        yield mock_yaml


@pytest.fixture
def mock_crash_data() -> list[str]:
    """Create mock crash log data for testing."""
    return [
        "Fallout 4 v1.10.163",
        "Buffout 4 v1.28.6",
        "",
        'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512',
        "",
        "\t[Compatibility]",
        "\t\tF4EE: true",
        "\t[Crashlog]",
        "\t\tPromptUpload: false",
        "SYSTEM SPECS:",
        "\tOS: Microsoft Windows 11 Pro v10.0.22621",
        "\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor",
        "\tGPU #1: Nvidia AD104 [GeForce RTX 4070]",
        "PROBABLE CALL STACK:",
        "\t[0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72",
        "\t[1] 0x7FF6EF4C145E Fallout4.exe+073145E -> 825090+0x67E",
        "MODULES:",
        "\tmodule1.dll",
        "\tmodule2.dll",
        "F4SE PLUGINS:",
        "\tf4se_plugin1.dll",
        "\tf4se_plugin2.dll",
        "PLUGINS:",
        "\t[00] Fallout4.esm",
        "\t[01] DLCRobot.esm",
        "\t[FE:123] TestMod.esp",
    ]


@pytest.fixture
def mock_scanner(setup_global_registry, mock_yaml_settings) -> ClassicScanLogs:
    """Create a mock ClassicScanLogs instance with basic functionality."""
    with (
        patch("ClassicLib.ScanLog.Util.crashlogs_get_files", return_value=[Path("crash-test.log")]),
        patch("ClassicLib.ScanLog.Util.crashlogs_reformat"),
        patch("CLASSIC_ScanLogs.ThreadSafeLogCache"),
    ):
        scanner = ClassicScanLogs()
        scanner.yamldata = ClassicScanLogsInfo()
        scanner.lower_records = {"record1", "record2"}
        scanner.lower_ignore = {"ignored_record"}
        scanner.lower_plugins_ignore = {"ignored_plugin"}
        scanner.formid_db_exists = True
        scanner.show_formid_values = True
        return scanner


class TestClassicScanLogs:
    """Tests for the ClassicScanLogs class."""

    def test_init(self, setup_global_registry, mock_yaml_settings):
        """Test initialization of the ClassicScanLogs class."""
        with (
            patch("ClassicLib.ScanLog.Util.crashlogs_get_files", return_value=[Path("crash-test.log")]),
            patch("ClassicLib.ScanLog.Util.crashlogs_reformat"),
            patch("CLASSIC_ScanLogs.ThreadSafeLogCache"),
        ):
            scanner = ClassicScanLogs()

            assert hasattr(scanner, "pluginsearch")
            assert hasattr(scanner, "crashlog_list")
            assert hasattr(scanner, "yamldata")
            assert hasattr(scanner, "crashlog_stats")
            assert scanner.crashlog_stats["scanned"] == 0
            assert scanner.crashlog_stats["incomplete"] == 0
            assert scanner.crashlog_stats["failed"] == 0

    def test_find_segments(self, mock_scanner, mock_crash_data):
        """Test extraction of segments from crash log data."""
        game_ver, crashgen_ver, main_error, segments = mock_scanner.find_segments(mock_crash_data, "Buffout 4")

        assert game_ver == "Fallout 4 v1.10.163"
        assert crashgen_ver == "Buffout 4 v1.28.6"
        assert main_error == 'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512'
        assert len(segments) == 6  # crashgen, system, callstack, allmodules, xsemodules, plugins

        # Verify content of segments
        assert "F4EE: true" in segments[0]  # crashgen
        assert "OS: Microsoft Windows 11 Pro" in segments[1]  # system
        assert "0x7FF6EF4C3512 Fallout4.exe" in segments[2][0]  # callstack
        assert "module1.dll" in segments[3]  # allmodules
        assert "f4se_plugin1.dll" in segments[4]  # xsemodules
        assert "Fallout4.esm" in segments[5][0]  # plugins

    def test_extract_segments(self, mock_scanner, mock_crash_data):
        """Test the _extract_segments method."""
        segment_boundaries = [
            ("\t[Compatibility]", "SYSTEM SPECS:"),  # segment_crashgen
            ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),  # segment_system
            ("PROBABLE CALL STACK:", "MODULES:"),  # segment_callstack
        ]

        segments = mock_scanner._extract_segments(mock_crash_data, segment_boundaries, "EOF")

        assert len(segments) == 3
        assert "F4EE: true" in segments[0]  # crashgen
        assert "OS: Microsoft Windows 11 Pro" in segments[1]  # system
        assert "0x7FF6EF4C3512 Fallout4.exe" in segments[2][0]  # callstack

    def test_loadorder_scan_log(self, mock_scanner):
        """Test the loadorder_scan_log method."""
        segment_plugins = ["[00] Fallout4.esm", "[01] DLCRobot.esm", "[FE:123] TestMod.esp", "[FF] LimitTestMod.esp"]

        # Create ClassicScanLogsInfo with test versions
        mock_scanner.yamldata.game_version = Version("1.10.163")
        mock_scanner.yamldata.game_version_new = Version("1.10.984")
        mock_scanner.yamldata.game_version_vr = Version("1.2.72")

        plugin_map, limit_triggered, limit_disabled = mock_scanner.loadorder_scan_log(
            segment_plugins, mock_scanner.yamldata.game_version, Version("1.28.6")
        )

        assert "Fallout4.esm" in plugin_map
        assert plugin_map["Fallout4.esm"] == "00"
        assert "TestMod.esp" in plugin_map
        assert plugin_map["TestMod.esp"] == "FE123"
        assert limit_triggered is True
        assert limit_disabled is False

    def test_suspect_scan_mainerror(self, mock_scanner):
        """Test the suspect_scan_mainerror method."""
        autoscan_report = []

        # Mock suspects_error_list
        mock_scanner.yamldata.suspects_error_list = {"HIGH | Test Error": "test_signal"}

        # Test with matching error
        result = mock_scanner.suspect_scan_mainerror(autoscan_report, "Critical error with test_signal in it", 30)

        assert result is True
        assert len(autoscan_report) == 1
        assert "Test Error" in autoscan_report[0]
        assert "HIGH" in autoscan_report[0]

        # Test with non-matching error
        autoscan_report.clear()
        result = mock_scanner.suspect_scan_mainerror(autoscan_report, "No matching signal here", 30)

        assert result is False
        assert len(autoscan_report) == 0

    def test_suspect_scan_stack(self, mock_scanner):
        """Test the suspect_scan_stack method."""
        # Mock suspects_stack_list
        mock_scanner.yamldata.suspects_stack_list = {"MEDIUM | Stack Error": ["required:test_signal", "optional:another_signal"]}

        autoscan_report = []

        # Test with matching stack
        result = mock_scanner.suspect_scan_stack("Main error", "Stack with test_signal in it", autoscan_report, 30)

        assert result is True
        assert len(autoscan_report) == 1
        assert "Stack Error" in autoscan_report[0]
        assert "MEDIUM" in autoscan_report[0]

        # Test with non-matching stack
        autoscan_report.clear()
        result = mock_scanner.suspect_scan_stack("Main error", "No matching signal here", autoscan_report, 30)

        assert result is False
        assert len(autoscan_report) == 0

    def test_process_signal(self):
        """Test the _process_signal method."""
        match_status = {"has_required_item": True, "error_req_found": False, "error_opt_found": False, "stack_found": False}

        # Test required signal
        result = ClassicScanLogs._process_signal("required:test_signal", "Error with test_signal", "Stack without signal", match_status)

        assert result is False
        assert match_status["error_req_found"] is True

        # Test optional signal
        match_status["error_req_found"] = False
        result = ClassicScanLogs._process_signal("optional:test_signal", "Error with test_signal", "Stack without signal", match_status)

        assert result is False
        assert match_status["error_opt_found"] is True

        # Test negative signal
        match_status["error_opt_found"] = False
        result = ClassicScanLogs._process_signal("not:test_signal", "Error without signal", "Stack with test_signal", match_status)

        assert result is True  # Should break out of loop

        # Test occurrence count signal
        match_status["stack_found"] = False
        result = ClassicScanLogs._process_signal(
            "2:test_signal", "Error without signal", "Stack with test_signal and more test_signal instances", match_status
        )

        assert result is False
        assert match_status["stack_found"] is True

    def test_is_suspect_match(self):
        """Test the _is_suspect_match method."""
        # Case 1: Required item with matching error
        match_status = {"has_required_item": True, "error_req_found": True, "error_opt_found": False, "stack_found": False}
        assert ClassicScanLogs._is_suspect_match(match_status) is True

        # Case 2: Required item without matching error
        match_status["error_req_found"] = False
        assert ClassicScanLogs._is_suspect_match(match_status) is False

        # Case 3: Optional item with matching error
        match_status["has_required_item"] = False
        match_status["error_opt_found"] = True
        assert ClassicScanLogs._is_suspect_match(match_status) is True

        # Case 4: Optional item with matching stack
        match_status["error_opt_found"] = False
        match_status["stack_found"] = True
        assert ClassicScanLogs._is_suspect_match(match_status) is True

        # Case 5: No matches at all
        match_status["stack_found"] = False
        assert ClassicScanLogs._is_suspect_match(match_status) is False

    def test_plugin_match(self, mock_scanner):
        """Test the plugin_match method."""
        segment_callstack_lower = [
            "line with test_plugin1 in it",
            "another line with test_plugin2 in it",
            "line with ignored_plugin that should be skipped",
        ]

        crashlog_plugins_lower = {"test_plugin1", "test_plugin2", "ignored_plugin", "unmentioned_plugin"}

        autoscan_report = []

        mock_scanner.plugin_match(segment_callstack_lower, crashlog_plugins_lower, autoscan_report)

        assert len(autoscan_report) > 0
        assert any("test_plugin1" in line for line in autoscan_report)
        assert any("test_plugin2" in line for line in autoscan_report)
        assert not any("ignored_plugin" in line for line in autoscan_report)
        assert not any("unmentioned_plugin" in line for line in autoscan_report)

    def test_formid_match(self, mock_scanner):
        """Test the formid_match method."""
        formids_matches = ["Form ID: 123456", "Form ID: 789ABC"]
        crashlog_plugins = {"Plugin1.esp": "00", "Plugin2.esp": "01"}
        autoscan_report = []

        with patch("ClassicLib.ScanLog.Util.get_entry", return_value="Test Record"):
            mock_scanner.formid_match(formids_matches, crashlog_plugins, autoscan_report)

            assert len(autoscan_report) > 0
            assert any("123456" in line for line in autoscan_report)
            assert any("789ABC" in line for line in autoscan_report)
            assert any("Plugin1.esp" in line for line in autoscan_report) or any("Plugin2.esp" in line for line in autoscan_report)

    @patch("ClassicLib.ScanLog.Util.get_entry")
    def test_scan_named_records(self, mock_get_entry, mock_scanner):
        """Test the scan_named_records method."""
        segment_callstack = [
            "[RSP+10] 0x123 (Record1)",
            "[RSP+20] 0x456 (Some other text)",
            "[RSP+30] 0x789 (Record2)",
            "[RSP+40] 0xABC (ignored_record)",
        ]

        records_matches = []
        autoscan_report = []

        mock_scanner.scan_named_records(segment_callstack, records_matches, autoscan_report)

        assert "Record1" in records_matches
        assert "Record2" in records_matches
        assert "ignored_record" not in records_matches
        assert len(autoscan_report) > 0

    def test_scan_log_gpu(self, mock_scanner):
        """Test the scan_log_gpu method."""
        # Test with NVIDIA GPU
        segment_system = ["GPU #1: Nvidia RTX 3080", "GPU #2: Other GPU"]

        gpu_name, gpu_rival = mock_scanner.scan_log_gpu(segment_system)

        assert gpu_name == "Nvidia RTX 3080"
        assert gpu_rival == "amd"

        # Test with AMD GPU
        segment_system = ["GPU #1: AMD Radeon RX 6800", "GPU #2: Other GPU"]

        gpu_name, gpu_rival = mock_scanner.scan_log_gpu(segment_system)

        assert gpu_name == "AMD Radeon RX 6800"
        assert gpu_rival == "nvidia"

        # Test with unknown GPU
        segment_system = ["GPU #1: Unknown Graphics Card", "GPU #2: Other GPU"]

        gpu_name, gpu_rival = mock_scanner.scan_log_gpu(segment_system)

        assert gpu_name == "Unknown Graphics Card"
        assert gpu_rival is None


class TestDetectMods:
    """Tests for the DetectMods functions."""

    def test_detect_mods_single(self):
        """Test the detect_mods_single function."""
        yaml_dict = {"test_mod": "Test mod warning message", "another_mod": "Another warning message"}

        crashlog_plugins = {"test_mod_plugin.esp": "00", "unrelated_plugin.esp": "01"}

        autoscan_report = []

        result = detect_mods_single(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) == 2  # [!] FOUND and the warning message
        assert "FOUND" in autoscan_report[0]
        assert "Test mod warning message" in autoscan_report[1]

        # Test with no matches
        autoscan_report.clear()
        result = detect_mods_single({"no_match_mod": "Warning"}, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0

    def test_detect_mods_double(self):
        """Test the detect_mods_double function."""
        yaml_dict = {"mod1 | mod2": "These mods conflict with each other", "mod3 | mod4": "Another conflict pair"}

        crashlog_plugins = {"plugin_with_mod1.esp": "00", "plugin_with_mod2.esp": "01", "unrelated_plugin.esp": "02"}

        autoscan_report = []

        result = detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) == 2  # [!] CAUTION and the warning message
        assert "CAUTION" in autoscan_report[0]
        assert "These mods conflict with each other" in autoscan_report[1]

        # Test with no conflicts
        autoscan_report.clear()
        result = detect_mods_double({"mod1 | mod5": "No conflict here"}, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0

    def test_detect_mods_important(self):
        """Test the detect_mods_important function."""
        yaml_dict = {"mod1 | Important Mod": "You should install this mod", "nvidia_mod | NVIDIA Mod": "nvidia warning"}

        crashlog_plugins = {"plugin_with_mod1.esp": "00", "unrelated_plugin.esp": "01"}

        autoscan_report = []

        # Test with installed mod and no GPU rivalry
        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, None)

        assert any("✔️ Important Mod is installed" in line for line in autoscan_report)
        assert not any("NVIDIA Mod" in line for line in autoscan_report)

        # Test with installed mod and GPU rivalry
        autoscan_report.clear()
        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, "amd")

        assert any("✔️ Important Mod is installed" in line for line in autoscan_report)

        # Test with NVIDIA mod on AMD GPU
        yaml_dict = {"nvidia_mod | NVIDIA Mod": "nvidia warning"}
        crashlog_plugins = {"plugin_with_nvidia_mod.esp": "00"}

        autoscan_report.clear()
        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, "amd")

        assert any("❓ NVIDIA Mod is installed" in line for line in autoscan_report)
        assert any("AMD" in line for line in autoscan_report)


class TestThreadSafeLogCache:
    """Tests for the ThreadSafeLogCache class."""

    def test_init(self):
        """Test initialization of ThreadSafeLogCache."""
        with patch("builtins.open", MagicMock()), patch("pathlib.Path.read_bytes", return_value=b"Test log content"):
            log_files = [Path("crash-test1.log"), Path("crash-test2.log")]
            cache = ThreadSafeLogCache(log_files)

            assert hasattr(cache, "lock")
            assert hasattr(cache, "cache")
            assert len(cache.cache) == 2
            assert "crash-test1.log" in cache.cache
            assert "crash-test2.log" in cache.cache

    def test_read_log(self):
        """Test reading logs from the cache."""
        # Create a cache with mock data
        cache = ThreadSafeLogCache([])
        cache.cache = {"test.log": b"Line 1\nLine 2\nLine 3"}

        lines = cache.read_log("test.log")

        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

        # Test with non-existent log
        with pytest.raises(KeyError):
            cache.read_log("nonexistent.log")

    def test_get_log_names(self):
        """Test getting log names from the cache."""
        cache = ThreadSafeLogCache([])
        cache.cache = {"log1.log": b"content1", "log2.log": b"content2"}

        names = cache.get_log_names()

        assert len(names) == 2
        assert "log1.log" in names
        assert "log2.log" in names

    def test_add_log(self):
        """Test adding a new log to the cache."""
        with patch("pathlib.Path.read_bytes", return_value=b"New log content"):
            cache = ThreadSafeLogCache([])

            result = cache.add_log(Path("new.log"))

            assert result is True
            assert "new.log" in cache.cache
            assert cache.cache["new.log"] == b"New log content"

            # Test with file that causes exception
            with patch("pathlib.Path.read_bytes", side_effect=OSError("Test error")):
                result = cache.add_log(Path("error.log"))

                assert result is False
                assert "error.log" not in cache.cache

    def test_close(self):
        """Test closing and clearing the cache."""
        cache = ThreadSafeLogCache([])
        cache.cache = {"test.log": b"content"}

        cache.close()

        assert len(cache.cache) == 0


class TestIntegration:
    """Integration tests for the crash log scanning system."""

    @patch("CLASSIC_ScanLogs.ThreadSafeLogCache")
    def test_process_crashlog(self, mock_cache, mock_scanner, mock_crash_data):
        """Test the process_crashlog function."""
        # This is a simplified test for the process_crashlog function
        from CLASSIC_ScanLogs import process_crashlog

        # Setup mock cache to return crash data
        mock_cache_instance = MagicMock()
        mock_cache_instance.read_log.return_value = mock_crash_data
        mock_scanner.crashlogs = mock_cache_instance

        # Setup yamldata with necessary attributes
        mock_scanner.yamldata.crashgen_name = "Buffout 4"
        mock_scanner.yamldata.crashgen_latest_og = "v1.28.6"
        mock_scanner.yamldata.crashgen_latest_vr = "v1.28.6"
        mock_scanner.yamldata.warn_outdated = "Warning: outdated"
        mock_scanner.yamldata.classic_version = "1.0"
        mock_scanner.yamldata.classic_version_date = "2023-01-01"
        mock_scanner.yamldata.autoscan_text = "Auto scan text"

        # Add mocks for required methods
        mock_scanner.scan_log_gpu = MagicMock(return_value=("NVIDIA GPU", "amd"))
        mock_scanner.loadorder_scan_log = MagicMock(return_value=({}, False, False))
        mock_scanner.formid_match = MagicMock()
        mock_scanner.plugin_match = MagicMock()
        mock_scanner.scan_named_records = MagicMock()
        mock_scanner.scan_buffout_achievements_setting = MagicMock()
        mock_scanner.scan_buffout_memorymanagement_settings = MagicMock()
        mock_scanner.scan_buffout_looksmenu_setting = MagicMock()
        mock_scanner.suspect_scan_mainerror = MagicMock(return_value=False)
        mock_scanner.suspect_scan_stack = MagicMock(return_value=False)

        with (
            patch("ClassicLib.ScanLog.DetectMods.detect_mods_single", return_value=False),
            patch("ClassicLib.ScanLog.DetectMods.detect_mods_double", return_value=False),
            patch("ClassicLib.ScanLog.DetectMods.detect_mods_important"),
        ):
            crash_file = Path("crash-test.log")
            result = process_crashlog(mock_scanner, crash_file)

            assert len(result) == 4
            assert result[0] == crash_file  # crash log file path
            assert isinstance(result[1], list)  # autoscan report
            assert isinstance(result[2], bool)  # trigger_scan_failed
            assert isinstance(result[3], Counter)  # local_stats


if __name__ == "__main__":
    pytest.main()

"""Unit tests for ClassicLib.python.plugin_py module.

This module tests the PythonPluginAnalyzer class, which provides the pure Python
fallback implementation for plugin analysis operations when Rust acceleration
is not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.python.plugin_py import PythonPluginAnalyzer

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_yamldata_for_plugin() -> MagicMock:
    """Create a mock ClassicScanLogsInfo for plugin testing.

    Returns:
        MagicMock: Mock with plugin-related attributes.
    """
    mock = MagicMock()
    mock.game_ignore_plugins = ["fallout4.esm", "dlccoast.esm", "dlcrobot.esm"]
    mock.ignore_list = ["ignored_mod.esp"]
    mock.crashgen_name = "Buffout 4"

    # Version objects for plugin limit checking
    mock.game_version = MagicMock()
    mock.game_version.__eq__ = lambda self, other: str(other) == "1.10.163"
    mock.game_version.__str__ = lambda self: "1.10.163"

    mock.game_version_vr = MagicMock()
    mock.game_version_vr.__eq__ = lambda self, other: str(other) == "1.2.72"
    mock.game_version_vr.__str__ = lambda self: "1.2.72"

    mock.game_version_new = MagicMock()
    mock.game_version_new.__le__ = lambda self, other: False
    mock.game_version_new.__ge__ = lambda self, other: True
    mock.game_version_new.__str__ = lambda self: "1.10.980"

    return mock


@pytest.fixture
def plugin_analyzer(mock_yamldata_for_plugin: MagicMock) -> "PythonPluginAnalyzer":
    """Create a PythonPluginAnalyzer instance for testing.

    Args:
        mock_yamldata_for_plugin: Mock YAML data fixture.

    Returns:
        PythonPluginAnalyzer instance.
    """
    from ClassicLib.python.plugin_py import PythonPluginAnalyzer

    return PythonPluginAnalyzer(mock_yamldata_for_plugin)


@pytest.fixture
def sample_segment_plugins() -> list[str]:
    """Create sample plugin segment data.

    Returns:
        list[str]: Sample plugin entries as they appear in crash logs.
    """
    return [
        "  [00] Fallout4.esm",
        "  [01] DLCRobot.esm",
        "  [02] DLCworkshop01.esm",
        "  [0A] TestMod.esp",
        "  [FE:001] LightMod.esl",
        "  [FE:002] AnotherLight.esl",
    ]


@pytest.fixture
def sample_callstack_lower() -> list[str]:
    """Create sample lowercase callstack lines.

    Returns:
        list[str]: Sample callstack lines in lowercase.
    """
    return [
        "fallout4.exe+0x12345",
        "testmod.esp+0x00001234",
        "somefunction from testmod.esp",
        "another line without plugin",
        "lightmod.esl causes crash",
        "modified by: dlcrobot.esm",  # Should be filtered out
    ]


# ============================================================================
# PythonPluginAnalyzer Initialization Tests
# ============================================================================


class TestPythonPluginAnalyzerInit:
    """Tests for PythonPluginAnalyzer initialization."""

    @pytest.mark.unit
    def test_init_stores_yamldata(self, mock_yamldata_for_plugin: MagicMock) -> None:
        """Test that yamldata is stored on initialization."""
        from ClassicLib.python.plugin_py import PythonPluginAnalyzer

        analyzer = PythonPluginAnalyzer(mock_yamldata_for_plugin)

        assert analyzer.yamldata is mock_yamldata_for_plugin

    @pytest.mark.unit
    def test_init_creates_pluginsearch_regex(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that pluginsearch regex is compiled."""
        assert plugin_analyzer.pluginsearch is not None
        assert hasattr(plugin_analyzer.pluginsearch, "match")

    @pytest.mark.unit
    def test_init_creates_lowercase_ignore_plugins(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that ignore plugins are converted to lowercase set."""
        assert "fallout4.esm" in plugin_analyzer.lower_plugins_ignore
        assert "dlccoast.esm" in plugin_analyzer.lower_plugins_ignore
        assert "dlcrobot.esm" in plugin_analyzer.lower_plugins_ignore

    @pytest.mark.unit
    def test_init_creates_lowercase_ignore_list(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that ignore list is converted to lowercase set."""
        assert "ignored_mod.esp" in plugin_analyzer.ignore_plugins_list

    @pytest.mark.unit
    def test_init_handles_none_ignore_list(self, mock_yamldata_for_plugin: MagicMock) -> None:
        """Test that None ignore_list is handled gracefully."""
        from ClassicLib.python.plugin_py import PythonPluginAnalyzer

        mock_yamldata_for_plugin.ignore_list = None
        analyzer = PythonPluginAnalyzer(mock_yamldata_for_plugin)

        assert analyzer.ignore_plugins_list == set()


# ============================================================================
# loadorder_scan_loadorder_txt Tests
# ============================================================================


class TestLoadorderScanLoadorderTxt:
    """Tests for PythonPluginAnalyzer.loadorder_scan_loadorder_txt method."""

    @pytest.mark.unit
    def test_loadorder_scan_loadorder_txt_with_file(
        self, plugin_analyzer: "PythonPluginAnalyzer", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test parsing loadorder.txt when file exists."""
        # Create a loadorder.txt file in the current directory
        loadorder_content = "# Header line\nMod1.esp\nMod2.esp\nMod3.esp\n"
        loadorder_file = tmp_path / "loadorder.txt"
        loadorder_file.write_text(loadorder_content)

        # Change to tmp_path so the method finds the file
        monkeypatch.chdir(tmp_path)

        plugins, loaded, fragment = plugin_analyzer.loadorder_scan_loadorder_txt()

        assert loaded is True
        assert "Mod1.esp" in plugins
        assert "Mod2.esp" in plugins
        assert "Mod3.esp" in plugins
        assert plugins["Mod1.esp"] == "LO"

    @pytest.mark.unit
    def test_loadorder_scan_loadorder_txt_skips_header(
        self, plugin_analyzer: "PythonPluginAnalyzer", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that first line (header) is skipped."""
        loadorder_content = "HeaderToSkip\nActualMod.esp\n"
        loadorder_file = tmp_path / "loadorder.txt"
        loadorder_file.write_text(loadorder_content)

        monkeypatch.chdir(tmp_path)

        plugins, loaded, fragment = plugin_analyzer.loadorder_scan_loadorder_txt()

        assert "HeaderToSkip" not in plugins
        assert "ActualMod.esp" in plugins

    @pytest.mark.unit
    def test_loadorder_scan_loadorder_txt_removes_duplicates(
        self, plugin_analyzer: "PythonPluginAnalyzer", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that duplicate plugins are not added."""
        loadorder_content = "Header\nMod1.esp\nMod1.esp\nMod2.esp\n"
        loadorder_file = tmp_path / "loadorder.txt"
        loadorder_file.write_text(loadorder_content)

        monkeypatch.chdir(tmp_path)

        plugins, loaded, fragment = plugin_analyzer.loadorder_scan_loadorder_txt()

        # Only one entry per plugin
        assert len([k for k in plugins if k == "Mod1.esp"]) == 1

    @pytest.mark.unit
    def test_loadorder_scan_loadorder_txt_returns_fragment(
        self, plugin_analyzer: "PythonPluginAnalyzer", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that method returns a ReportFragment."""
        loadorder_content = "Header\nMod.esp\n"
        loadorder_file = tmp_path / "loadorder.txt"
        loadorder_file.write_text(loadorder_content)

        monkeypatch.chdir(tmp_path)

        _, _, fragment = plugin_analyzer.loadorder_scan_loadorder_txt()

        assert hasattr(fragment, "to_list") or hasattr(fragment, "content")


# ============================================================================
# check_plugin_limit Tests
# ============================================================================


class TestCheckPluginLimit:
    """Tests for PythonPluginAnalyzer.check_plugin_limit method."""

    @pytest.mark.unit
    def test_check_plugin_limit_returns_false_without_versions(
        self, plugin_analyzer: "PythonPluginAnalyzer", sample_segment_plugins: list[str]
    ) -> None:
        """Test returns (False, False) when version info missing."""
        triggered, disabled = plugin_analyzer.check_plugin_limit(sample_segment_plugins)

        assert triggered is False
        assert disabled is False

    @pytest.mark.unit
    def test_check_plugin_limit_returns_false_no_ff_marker(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test returns False when no [FF] marker present."""
        from packaging.version import Version

        plugins = ["  [00] Mod.esp", "  [01] Another.esp"]
        game_version = Version("1.10.163")
        version_current = Version("1.37.0")

        triggered, disabled = plugin_analyzer.check_plugin_limit(plugins, game_version, version_current)

        assert triggered is False
        assert disabled is False

    @pytest.mark.unit
    def test_check_plugin_limit_triggered_original_game(self, mock_yamldata_for_plugin: MagicMock) -> None:
        """Test plugin limit triggered for original game version."""
        from packaging.version import Version

        from ClassicLib.python.plugin_py import PythonPluginAnalyzer

        # Set up yamldata with proper Version objects for comparison
        mock_yamldata_for_plugin.game_version = Version("1.10.163")
        mock_yamldata_for_plugin.game_version_vr = Version("1.2.72")
        mock_yamldata_for_plugin.game_version_new = Version("1.10.980")

        analyzer = PythonPluginAnalyzer(mock_yamldata_for_plugin)

        plugins = ["  [FE] Mod.esp", "  [FF] OverLimit.esp"]
        game_version = Version("1.10.163")  # Matches yamldata.game_version
        version_current = Version("1.37.0")

        triggered, disabled = analyzer.check_plugin_limit(plugins, game_version, version_current)

        assert triggered is True
        assert disabled is False


# ============================================================================
# loadorder_scan_log Tests
# ============================================================================


class TestLoadorderScanLog:
    """Tests for PythonPluginAnalyzer.loadorder_scan_log method."""

    @pytest.mark.unit
    def test_loadorder_scan_log_returns_empty_for_empty_input(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test returns empty dict for empty segment."""
        plugins, triggered, disabled = plugin_analyzer.loadorder_scan_log([])

        assert plugins == {}
        assert triggered is False
        assert disabled is False

    @pytest.mark.unit
    def test_loadorder_scan_log_extracts_hex_indices(
        self, plugin_analyzer: "PythonPluginAnalyzer", sample_segment_plugins: list[str]
    ) -> None:
        """Test extraction of hex indices from plugin lines."""
        plugins, _, _ = plugin_analyzer.loadorder_scan_log(sample_segment_plugins)

        assert "Fallout4.esm" in plugins
        assert plugins["Fallout4.esm"] == "00"
        assert "TestMod.esp" in plugins
        assert plugins["TestMod.esp"] == "0A"

    @pytest.mark.unit
    def test_loadorder_scan_log_handles_light_plugins(
        self, plugin_analyzer: "PythonPluginAnalyzer", sample_segment_plugins: list[str]
    ) -> None:
        """Test extraction of FE: prefix light plugin indices."""
        plugins, _, _ = plugin_analyzer.loadorder_scan_log(sample_segment_plugins)

        assert "LightMod.esl" in plugins
        assert plugins["LightMod.esl"] == "FE001"

    @pytest.mark.unit
    def test_loadorder_scan_log_skips_duplicates(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that duplicate plugin names are skipped."""
        plugins_segment = [
            "  [00] Mod.esp",
            "  [01] Mod.esp",  # Duplicate - should be skipped
        ]

        plugins, _, _ = plugin_analyzer.loadorder_scan_log(plugins_segment)

        assert plugins["Mod.esp"] == "00"  # First occurrence

    @pytest.mark.unit
    def test_loadorder_scan_log_skips_empty_names(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that entries with empty plugin names are skipped."""
        plugins_segment = [
            "  [00] Valid.esp",
            "  [01] ",  # Empty name
        ]

        plugins, _, _ = plugin_analyzer.loadorder_scan_log(plugins_segment)

        assert len(plugins) == 1
        assert "Valid.esp" in plugins


# ============================================================================
# plugin_match Tests
# ============================================================================


class TestPluginMatch:
    """Tests for PythonPluginAnalyzer.plugin_match method."""

    @pytest.mark.unit
    def test_plugin_match_finds_plugins_in_callstack(
        self, plugin_analyzer: "PythonPluginAnalyzer", sample_callstack_lower: list[str]
    ) -> None:
        """Test that plugins are found in callstack."""
        crashlog_plugins = {"testmod.esp", "lightmod.esl", "fallout4.esm"}

        fragment = plugin_analyzer.plugin_match(sample_callstack_lower, crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        # testmod.esp should be found (not in ignore list)
        assert "testmod.esp" in content

    @pytest.mark.unit
    def test_plugin_match_filters_modified_by_lines(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that 'modified by:' lines are filtered out."""
        callstack = [
            "normal line with testmod.esp",
            "modified by: testmod.esp",  # Should be filtered
        ]
        crashlog_plugins = {"testmod.esp"}

        fragment = plugin_analyzer.plugin_match(callstack, crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        # Should find testmod.esp but count should be 1 (filtered line excluded)
        assert "testmod.esp" in content
        assert "| 1" in content

    @pytest.mark.unit
    def test_plugin_match_skips_ignored_plugins(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that plugins in ignore list are skipped."""
        callstack = [
            "line with fallout4.esm",
            "line with testmod.esp",
        ]
        crashlog_plugins = {"fallout4.esm", "testmod.esp"}

        fragment = plugin_analyzer.plugin_match(callstack, crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        # fallout4.esm should be ignored, testmod.esp should be found
        assert "fallout4.esm" not in content
        assert "testmod.esp" in content

    @pytest.mark.unit
    def test_plugin_match_counts_occurrences(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that plugin occurrences are counted."""
        callstack = [
            "testmod.esp first occurrence",
            "testmod.esp second occurrence",
            "testmod.esp third occurrence",
        ]
        crashlog_plugins = {"testmod.esp"}

        fragment = plugin_analyzer.plugin_match(callstack, crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "testmod.esp | 3" in content

    @pytest.mark.unit
    def test_plugin_match_no_matches_message(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test message when no plugins found."""
        callstack = ["no plugins here"]
        crashlog_plugins = {"testmod.esp"}

        fragment = plugin_analyzer.plugin_match(callstack, crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "COULDN'T FIND ANY PLUGIN SUSPECTS" in content


# ============================================================================
# filter_ignored_plugins Tests
# ============================================================================


class TestFilterIgnoredPlugins:
    """Tests for PythonPluginAnalyzer.filter_ignored_plugins method."""

    @pytest.mark.unit
    def test_filter_ignored_plugins_removes_ignored(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that ignored plugins are removed."""
        crashlog_plugins = {
            "TestMod.esp": "0A",
            "Ignored_Mod.esp": "0B",  # Should be removed (case-insensitive)
            "AnotherMod.esp": "0C",
        }

        result = plugin_analyzer.filter_ignored_plugins(crashlog_plugins)

        assert "TestMod.esp" in result
        assert "Ignored_Mod.esp" not in result
        assert "AnotherMod.esp" in result

    @pytest.mark.unit
    def test_filter_ignored_plugins_case_insensitive(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that filtering is case-insensitive."""
        crashlog_plugins = {
            "IGNORED_MOD.ESP": "0A",  # Uppercase version
        }

        result = plugin_analyzer.filter_ignored_plugins(crashlog_plugins)

        assert "IGNORED_MOD.ESP" not in result

    @pytest.mark.unit
    def test_filter_ignored_plugins_empty_ignore_list(self, mock_yamldata_for_plugin: MagicMock) -> None:
        """Test that empty ignore list returns plugins unchanged."""
        from ClassicLib.python.plugin_py import PythonPluginAnalyzer

        mock_yamldata_for_plugin.ignore_list = []
        analyzer = PythonPluginAnalyzer(mock_yamldata_for_plugin)

        crashlog_plugins = {"Mod1.esp": "0A", "Mod2.esp": "0B"}

        result = analyzer.filter_ignored_plugins(crashlog_plugins)

        assert result == crashlog_plugins

    @pytest.mark.unit
    def test_filter_ignored_plugins_preserves_original_case(self, plugin_analyzer: "PythonPluginAnalyzer") -> None:
        """Test that original key casing is preserved."""
        crashlog_plugins = {
            "TestMod.ESP": "0A",
            "AnotherMod.Esp": "0B",
        }

        result = plugin_analyzer.filter_ignored_plugins(crashlog_plugins)

        # Keys should maintain original case
        assert "TestMod.ESP" in result
        assert "AnotherMod.Esp" in result


# ============================================================================
# Alias Tests
# ============================================================================


class TestPluginAnalyzerAlias:
    """Tests for PluginAnalyzer alias."""

    @pytest.mark.unit
    def test_plugin_analyzer_alias_exists(self) -> None:
        """Test PluginAnalyzer is an alias for PythonPluginAnalyzer."""
        from ClassicLib.python.plugin_py import PluginAnalyzer, PythonPluginAnalyzer

        assert PluginAnalyzer is PythonPluginAnalyzer

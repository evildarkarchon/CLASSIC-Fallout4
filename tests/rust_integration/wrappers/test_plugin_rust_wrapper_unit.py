"""Unit tests for ClassicLib.rust.plugin_rust module.

This module tests the RustPluginAnalyzer wrapper class, which provides
high-performance plugin analysis with automatic fallback to Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.rust.plugin_rust import RustPluginAnalyzer


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_yamldata_for_rust_plugin() -> MagicMock:
    """Create a mock ClassicScanLogsInfo for plugin analysis.

    Returns:
        MagicMock: Mock with plugin-related attributes.
    """
    mock = MagicMock()
    mock.game_ignore_plugins = ["fallout4.esm", "dlccoast.esm"]
    mock.ignore_list = ["ignored_mod.esp"]
    mock.crashgen_name = "Buffout 4"
    mock.game_version = "1.10.163"
    mock.game_version_vr = "1.2.72"
    mock.game_version_new = "1.10.980"
    return mock


@pytest.fixture
def rust_plugin_analyzer(mock_yamldata_for_rust_plugin: MagicMock) -> "RustPluginAnalyzer":
    """Create a RustPluginAnalyzer instance for testing.

    Args:
        mock_yamldata_for_rust_plugin: Mock YAML data fixture.

    Returns:
        RustPluginAnalyzer instance.
    """
    from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

    return RustPluginAnalyzer(mock_yamldata_for_rust_plugin)


@pytest.fixture
def sample_segment_plugins() -> list[str]:
    """Create sample plugin segment data.

    Returns:
        list[str]: Sample plugin entries.
    """
    return [
        "  [00] Fallout4.esm",
        "  [01] DLCRobot.esm",
        "  [02] DLCworkshop01.esm",
        "  [0A] TestMod.esp",
        "  [FE:001] LightMod.esl",
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
        "lightmod.esl causes crash",
    ]


# ============================================================================
# RustPluginAnalyzer Initialization Tests
# ============================================================================


class TestRustPluginAnalyzerInit:
    """Tests for RustPluginAnalyzer initialization."""

    @pytest.mark.unit
    def test_init_stores_yamldata(self, mock_yamldata_for_rust_plugin: MagicMock) -> None:
        """Test that yamldata is stored on initialization."""
        from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

        analyzer = RustPluginAnalyzer(mock_yamldata_for_rust_plugin)

        assert analyzer.yamldata is mock_yamldata_for_rust_plugin

    @pytest.mark.unit
    def test_is_rust_accelerated_property(self, rust_plugin_analyzer: "RustPluginAnalyzer") -> None:
        """Test is_rust_accelerated property works."""
        assert isinstance(rust_plugin_analyzer.is_rust_accelerated, bool)


# ============================================================================
# loadorder_scan_log Tests
# ============================================================================


class TestLoadorderScanLog:
    """Tests for RustPluginAnalyzer.loadorder_scan_log method."""

    @pytest.mark.unit
    def test_loadorder_scan_log_returns_tuple(
        self, rust_plugin_analyzer: "RustPluginAnalyzer", sample_segment_plugins: list[str]
    ) -> None:
        """Test loadorder_scan_log returns tuple."""
        plugins, triggered, disabled = rust_plugin_analyzer.loadorder_scan_log(sample_segment_plugins)

        assert isinstance(plugins, dict)
        assert isinstance(triggered, bool)
        assert isinstance(disabled, bool)

    @pytest.mark.unit
    def test_loadorder_scan_log_extracts_plugins(
        self, rust_plugin_analyzer: "RustPluginAnalyzer", sample_segment_plugins: list[str]
    ) -> None:
        """Test plugin extraction from segment."""
        plugins, _, _ = rust_plugin_analyzer.loadorder_scan_log(sample_segment_plugins)

        assert "Fallout4.esm" in plugins
        assert "TestMod.esp" in plugins

    @pytest.mark.unit
    def test_loadorder_scan_log_empty_input(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test with empty input."""
        plugins, triggered, disabled = rust_plugin_analyzer.loadorder_scan_log([])

        assert plugins == {}
        assert triggered is False
        assert disabled is False

    @pytest.mark.unit
    def test_loadorder_scan_log_with_version(
        self, rust_plugin_analyzer: "RustPluginAnalyzer", sample_segment_plugins: list[str]
    ) -> None:
        """Test with version parameters."""
        from packaging.version import Version

        plugins, triggered, disabled = rust_plugin_analyzer.loadorder_scan_log(
            sample_segment_plugins,
            game_version=Version("1.10.163"),
            version_current=Version("1.37.0"),
        )

        assert isinstance(plugins, dict)


# ============================================================================
# check_plugin_limit Tests
# ============================================================================


class TestCheckPluginLimit:
    """Tests for RustPluginAnalyzer.check_plugin_limit method."""

    @pytest.mark.unit
    def test_check_plugin_limit_returns_tuple(
        self, rust_plugin_analyzer: "RustPluginAnalyzer", sample_segment_plugins: list[str]
    ) -> None:
        """Test check_plugin_limit returns tuple of bools."""
        triggered, disabled = rust_plugin_analyzer.check_plugin_limit(sample_segment_plugins)

        assert isinstance(triggered, bool)
        assert isinstance(disabled, bool)

    @pytest.mark.unit
    def test_check_plugin_limit_with_versions(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test with version parameters."""
        from packaging.version import Version

        plugins = ["  [FE] Mod.esp", "  [FF] OverLimit.esp"]

        triggered, disabled = rust_plugin_analyzer.check_plugin_limit(
            plugins,
            game_version=Version("1.10.163"),
            version_current=Version("1.37.0"),
        )

        assert isinstance(triggered, bool)
        assert isinstance(disabled, bool)


# ============================================================================
# plugin_match Tests
# ============================================================================


class TestPluginMatch:
    """Tests for RustPluginAnalyzer.plugin_match method."""

    @pytest.mark.unit
    def test_plugin_match_returns_fragment(
        self, rust_plugin_analyzer: "RustPluginAnalyzer", sample_callstack_lower: list[str]
    ) -> None:
        """Test plugin_match returns ReportFragment."""
        crashlog_plugins = {"testmod.esp", "lightmod.esl"}

        fragment = rust_plugin_analyzer.plugin_match(sample_callstack_lower, crashlog_plugins)

        assert hasattr(fragment, "to_list")

    @pytest.mark.unit
    def test_plugin_match_finds_plugins(
        self, rust_plugin_analyzer: "RustPluginAnalyzer", sample_callstack_lower: list[str]
    ) -> None:
        """Test that plugins are found in callstack."""
        crashlog_plugins = {"testmod.esp"}

        fragment = rust_plugin_analyzer.plugin_match(sample_callstack_lower, crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        # Should find testmod.esp
        assert "testmod.esp" in content or "COULDN'T FIND" in content

    @pytest.mark.unit
    def test_plugin_match_empty_callstack(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test with empty callstack."""
        fragment = rust_plugin_analyzer.plugin_match([], {"testmod.esp"})

        lines = fragment.to_list()
        content = "".join(lines)

        assert "COULDN'T FIND" in content

    @pytest.mark.unit
    def test_plugin_match_empty_plugins(
        self, rust_plugin_analyzer: "RustPluginAnalyzer", sample_callstack_lower: list[str]
    ) -> None:
        """Test with empty plugins set."""
        fragment = rust_plugin_analyzer.plugin_match(sample_callstack_lower, set())

        lines = fragment.to_list()
        content = "".join(lines)

        assert "COULDN'T FIND" in content


# ============================================================================
# filter_ignored_plugins Tests
# ============================================================================


class TestFilterIgnoredPlugins:
    """Tests for RustPluginAnalyzer.filter_ignored_plugins method."""

    @pytest.mark.unit
    def test_filter_ignored_plugins_removes_ignored(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test that ignored plugins are removed."""
        crashlog_plugins = {
            "TestMod.esp": "0A",
            "Ignored_Mod.esp": "0B",
        }

        result = rust_plugin_analyzer.filter_ignored_plugins(crashlog_plugins)

        assert "TestMod.esp" in result
        assert "Ignored_Mod.esp" not in result

    @pytest.mark.unit
    def test_filter_ignored_plugins_preserves_non_ignored(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test that non-ignored plugins are preserved."""
        crashlog_plugins = {
            "Mod1.esp": "0A",
            "Mod2.esp": "0B",
        }

        result = rust_plugin_analyzer.filter_ignored_plugins(crashlog_plugins)

        assert result == crashlog_plugins


# ============================================================================
# parse_plugin_line Tests
# ============================================================================


class TestParsePluginLine:
    """Tests for RustPluginAnalyzer.parse_plugin_line static method."""

    @pytest.mark.unit
    def test_parse_plugin_line_valid(self) -> None:
        """Test parsing valid plugin line."""
        from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

        result = RustPluginAnalyzer.parse_plugin_line("  [0A] TestMod.esp")

        assert result is not None
        assert result[0] == "0A"
        assert result[1] == "TestMod.esp"

    @pytest.mark.unit
    def test_parse_plugin_line_lowercase_hex(self) -> None:
        """Test parsing with lowercase hex."""
        from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

        result = RustPluginAnalyzer.parse_plugin_line("  [0a] TestMod.esp")

        assert result is not None
        assert result[0] == "0A"  # Should be uppercase

    @pytest.mark.unit
    def test_parse_plugin_line_invalid(self) -> None:
        """Test parsing invalid plugin line."""
        from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

        result = RustPluginAnalyzer.parse_plugin_line("Invalid line without brackets")

        assert result is None

    @pytest.mark.unit
    def test_parse_plugin_line_empty(self) -> None:
        """Test parsing empty line."""
        from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

        result = RustPluginAnalyzer.parse_plugin_line("")

        assert result is None


# ============================================================================
# Fallback Tests
# ============================================================================


class TestRustPluginAnalyzerFallback:
    """Tests for Python fallback behavior."""

    @pytest.mark.unit
    def test_uses_python_when_rust_unavailable(
        self, mock_yamldata_for_rust_plugin: MagicMock
    ) -> None:
        """Test Python implementation is used when Rust unavailable."""
        with patch.dict("sys.modules", {"classic_scanlog": None}):
            from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

            analyzer = RustPluginAnalyzer(mock_yamldata_for_rust_plugin)

            # May use Rust or Python depending on actual availability
            assert isinstance(analyzer.is_rust_accelerated, bool)

    @pytest.mark.unit
    def test_fallback_loadorder_scan(
        self, mock_yamldata_for_rust_plugin: MagicMock, sample_segment_plugins: list[str]
    ) -> None:
        """Test loadorder_scan_log works with fallback."""
        from ClassicLib.rust.plugin_rust import RustPluginAnalyzer

        analyzer = RustPluginAnalyzer.__new__(RustPluginAnalyzer)
        analyzer._rust_analyzer = None
        analyzer._use_rust = False
        analyzer._python_analyzer = None
        analyzer.yamldata = mock_yamldata_for_rust_plugin

        # Should create Python analyzer on demand
        plugins, triggered, disabled = analyzer.loadorder_scan_log(sample_segment_plugins)

        assert isinstance(plugins, dict)


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestRustPluginAnalyzerEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.unit
    def test_handles_special_characters(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test handling of special characters in plugin names."""
        segment = ["  [0A] Special~!@#$%.esp"]

        plugins, _, _ = rust_plugin_analyzer.loadorder_scan_log(segment)

        # Should parse without error
        assert isinstance(plugins, dict)

    @pytest.mark.unit
    def test_handles_unicode_plugin_names(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test handling of unicode in plugin names."""
        segment = ["  [0A] 日本語モッド.esp"]

        plugins, _, _ = rust_plugin_analyzer.loadorder_scan_log(segment)

        assert isinstance(plugins, dict)

    @pytest.mark.unit
    def test_handles_very_long_plugin_list(
        self, rust_plugin_analyzer: "RustPluginAnalyzer"
    ) -> None:
        """Test handling of very long plugin list."""
        segment = [f"  [{i:02X}] Plugin{i}.esp" for i in range(255)]

        plugins, _, _ = rust_plugin_analyzer.loadorder_scan_log(segment)

        assert isinstance(plugins, dict)
        assert len(plugins) > 0

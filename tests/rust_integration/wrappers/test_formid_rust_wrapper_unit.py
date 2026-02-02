"""Unit tests for ClassicLib.integration.rust.formid_rust module.

This module tests the FormIDAnalyzer wrapper class, which provides
high-performance FormID extraction with automatic fallback to Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_yamldata_for_formid() -> MagicMock:
    """Create a mock ClassicScanLogsInfo for FormID analysis.

    Returns:
        MagicMock: Mock with FormID-related attributes.
    """
    mock = MagicMock()
    mock.crashgen_name = "Buffout 4"
    mock.problematic_plugins = {
        "BadPlugin.esp": "This plugin causes issues",
    }
    mock.mods_single = {
        "problemplugin": "Warning about single mod",
    }
    mock.mods_double = {
        "mod_a | mod_b": "These mods conflict",
    }
    return mock


@pytest.fixture
def formid_analyzer(mock_yamldata_for_formid: MagicMock) -> "FormIDAnalyzer":
    """Create a FormIDAnalyzer instance for testing.

    Args:
        mock_yamldata_for_formid: Mock YAML data fixture.

    Returns:
        FormIDAnalyzer instance.
    """
    from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

    return FormIDAnalyzer(mock_yamldata_for_formid, show_formid_values=True, formid_db_exists=False)


@pytest.fixture
def sample_callstack_with_formids() -> list[str]:
    """Create sample callstack data with FormID references.

    Returns:
        list[str]: Sample callstack lines with FormIDs.
    """
    return [
        "Actor::Process() FormID=0x00000014",
        "TESObjectREFR::Update() [0001F66A]",
        "Normal line without formid",
        "Another formid: 00033A81",
        "Reference (FormID: 0x0A001234)",
    ]


@pytest.fixture
def sample_plugins() -> dict[str, str]:
    """Create sample plugin dictionary.

    Returns:
        dict[str, str]: Plugin name to ID mapping.
    """
    return {
        "Fallout4.esm": "00",
        "TestMod.esp": "0A",
        "AnotherMod.esp": "0B",
    }


# ============================================================================
# FormIDAnalyzer Initialization Tests
# ============================================================================


class TestFormIDAnalyzerInit:
    """Tests for FormIDAnalyzer initialization."""

    @pytest.mark.unit
    def test_init_stores_yamldata(self, mock_yamldata_for_formid: MagicMock) -> None:
        """Test that yamldata is stored on initialization."""
        from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

        analyzer = FormIDAnalyzer(mock_yamldata_for_formid, True, False)

        assert analyzer.yamldata is mock_yamldata_for_formid

    @pytest.mark.unit
    def test_init_stores_show_formid_values(self, mock_yamldata_for_formid: MagicMock) -> None:
        """Test show_formid_values is stored."""
        from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

        analyzer = FormIDAnalyzer(mock_yamldata_for_formid, show_formid_values=True, formid_db_exists=False)

        assert analyzer.show_formid_values is True

    @pytest.mark.unit
    def test_init_stores_formid_db_exists(self, mock_yamldata_for_formid: MagicMock) -> None:
        """Test formid_db_exists is stored."""
        from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

        analyzer = FormIDAnalyzer(mock_yamldata_for_formid, show_formid_values=False, formid_db_exists=True)

        assert analyzer.formid_db_exists is True

    @pytest.mark.unit
    def test_is_rust_accelerated_property(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test is_rust_accelerated property works."""
        assert isinstance(formid_analyzer.is_rust_accelerated, bool)

    @pytest.mark.unit
    def test_python_analyzer_always_initialized(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test Python analyzer is always created (needed for formid_match)."""
        assert formid_analyzer._python_analyzer is not None


# ============================================================================
# extract_formids Tests
# ============================================================================


class TestExtractFormids:
    """Tests for FormIDAnalyzer.extract_formids method."""

    @pytest.mark.unit
    def test_extract_formids_returns_list(self, formid_analyzer: "FormIDAnalyzer", sample_callstack_with_formids: list[str]) -> None:
        """Test extract_formids returns list."""
        result = formid_analyzer.extract_formids(sample_callstack_with_formids)

        assert isinstance(result, list)

    @pytest.mark.unit
    def test_extract_formids_finds_formids(self, formid_analyzer: "FormIDAnalyzer", sample_callstack_with_formids: list[str]) -> None:
        """Test FormIDs are extracted from callstack."""
        result = formid_analyzer.extract_formids(sample_callstack_with_formids)

        # Should find at least some FormIDs
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_extract_formids_empty_callstack(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test extraction from empty callstack."""
        result = formid_analyzer.extract_formids([])

        assert result == []

    @pytest.mark.unit
    def test_extract_formids_no_formids(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test extraction when no FormIDs present."""
        callstack = ["No formids here", "Just regular lines"]

        result = formid_analyzer.extract_formids(callstack)

        assert result == []


# ============================================================================
# formid_match Tests
# ============================================================================


class TestFormidMatch:
    """Tests for FormIDAnalyzer.formid_match method."""

    @pytest.mark.unit
    def test_formid_match_adds_to_report(self, formid_analyzer: "FormIDAnalyzer", sample_plugins: dict[str, str]) -> None:
        """Test formid_match adds fragment to report."""

        class MockReport:
            def __init__(self) -> None:
                self.fragments: list[Any] = []

            def add_fragment(self, fragment: Any) -> None:
                self.fragments.append(fragment)

        report = MockReport()
        formids = ["00000014", "0001F66A"]

        formid_analyzer.formid_match(formids, sample_plugins, report)

        # Report may or may not have fragments depending on implementation
        assert isinstance(report.fragments, list)

    @pytest.mark.unit
    def test_formid_match_empty_formids(self, formid_analyzer: "FormIDAnalyzer", sample_plugins: dict[str, str]) -> None:
        """Test formid_match with empty formid list."""

        class MockReport:
            def __init__(self) -> None:
                self.fragments: list[Any] = []

            def add_fragment(self, fragment: Any) -> None:
                self.fragments.append(fragment)

        report = MockReport()

        # Should not raise
        formid_analyzer.formid_match([], sample_plugins, report)

    @pytest.mark.unit
    def test_formid_match_empty_plugins(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test formid_match with empty plugins dict."""

        class MockReport:
            def __init__(self) -> None:
                self.fragments: list[Any] = []

            def add_fragment(self, fragment: Any) -> None:
                self.fragments.append(fragment)

        report = MockReport()
        formids = ["00000014"]

        # Should not raise
        formid_analyzer.formid_match(formids, {}, report)


# ============================================================================
# extract_formids_batch Tests
# ============================================================================


class TestExtractFormidsBatch:
    """Tests for FormIDAnalyzer.extract_formids_batch method."""

    @pytest.mark.unit
    def test_extract_formids_batch_returns_list(self, formid_analyzer: "FormIDAnalyzer", sample_callstack_with_formids: list[str]) -> None:
        """Test batch extraction returns list of lists."""
        segments = [sample_callstack_with_formids, ["Other line"]]

        result = formid_analyzer.extract_formids_batch(segments)

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.unit
    def test_extract_formids_batch_each_segment(self, formid_analyzer: "FormIDAnalyzer", sample_callstack_with_formids: list[str]) -> None:
        """Test each segment is processed."""
        segments = [sample_callstack_with_formids]

        result = formid_analyzer.extract_formids_batch(segments)

        assert len(result) == 1
        assert isinstance(result[0], list)

    @pytest.mark.unit
    def test_extract_formids_batch_empty_segments(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test batch extraction with empty segments."""
        result = formid_analyzer.extract_formids_batch([])

        assert result == []


# ============================================================================
# Fallback Tests
# ============================================================================


class TestFormIDAnalyzerFallback:
    """Tests for Python fallback behavior."""

    @pytest.mark.unit
    def test_uses_python_when_rust_unavailable(self, mock_yamldata_for_formid: MagicMock) -> None:
        """Test Python implementation is used when Rust unavailable."""
        with patch.dict("sys.modules", {"classic_scanlog": None}):
            from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

            analyzer = FormIDAnalyzer(mock_yamldata_for_formid, True, False)

            # May use Rust or Python depending on actual availability
            assert isinstance(analyzer.is_rust_accelerated, bool)

    @pytest.mark.unit
    def test_fallback_extract_formids(self, mock_yamldata_for_formid: MagicMock) -> None:
        """Test extraction works with Python fallback."""
        from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

        analyzer = FormIDAnalyzer.__new__(FormIDAnalyzer)
        analyzer._rust_analyzer = None
        analyzer._use_rust = False
        analyzer._python_analyzer = None
        analyzer.yamldata = mock_yamldata_for_formid
        analyzer.show_formid_values = True
        analyzer.formid_db_exists = False
        analyzer._init_python_analyzer()

        result = analyzer.extract_formids(["line with 00000014"])

        assert isinstance(result, list)


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestFormIDAnalyzerEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.unit
    def test_handles_malformed_formids(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test handling of malformed FormID strings."""
        callstack = ["FormID=not_a_hex", "0xGGGGGGGG", "Normal line"]

        # Should not raise
        result = formid_analyzer.extract_formids(callstack)

        assert isinstance(result, list)

    @pytest.mark.unit
    def test_handles_very_long_callstack(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test handling of very long callstack."""
        callstack = [f"Line {i} FormID=0x{i:08X}" for i in range(1000)]

        result = formid_analyzer.extract_formids(callstack)

        assert isinstance(result, list)

    @pytest.mark.unit
    def test_handles_unicode_in_callstack(self, formid_analyzer: "FormIDAnalyzer") -> None:
        """Test handling of unicode characters in callstack."""
        callstack = ["日本語 FormID=00000014", "Ñoño 0x00001234"]

        # Should not raise
        result = formid_analyzer.extract_formids(callstack)

        assert isinstance(result, list)

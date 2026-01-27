"""Unit tests for ClassicLib.python.formid_py module.

This module tests the PythonFormIDAnalyzer class, which provides the pure Python
fallback implementation for FormID extraction and analysis when Rust acceleration
is not available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_yamldata_formid() -> MagicMock:
    """Create mock yamldata for FormID analyzer tests.

    Returns:
        MagicMock with required attributes for FormID analysis.
    """
    mock = MagicMock()
    mock.crashgen_name = "Buffout 4"
    return mock


@pytest.fixture
def mock_db_pool() -> AsyncMock:
    """Create mock async database pool.

    Returns:
        AsyncMock with database pool methods.
    """
    pool = AsyncMock()
    pool.get_entry = AsyncMock(return_value=None)
    pool.get_entries_batch = AsyncMock(return_value={})
    return pool


@pytest.fixture
def formid_analyzer(mock_yamldata_formid: MagicMock) -> "PythonFormIDAnalyzer":
    """Create a FormID analyzer instance for testing.

    Args:
        mock_yamldata_formid: Mock yamldata fixture.

    Returns:
        PythonFormIDAnalyzer instance configured for testing.
    """
    from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

    return PythonFormIDAnalyzer(
        yamldata=mock_yamldata_formid,
        show_formid_values=True,
        formid_db_exists=True,
        db_pool=None,
    )


@pytest.fixture
def formid_analyzer_with_pool(
    mock_yamldata_formid: MagicMock,
    mock_db_pool: AsyncMock,
) -> "PythonFormIDAnalyzer":
    """Create a FormID analyzer with database pool.

    Args:
        mock_yamldata_formid: Mock yamldata fixture.
        mock_db_pool: Mock database pool fixture.

    Returns:
        PythonFormIDAnalyzer instance with database pool.
    """
    from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

    return PythonFormIDAnalyzer(
        yamldata=mock_yamldata_formid,
        show_formid_values=True,
        formid_db_exists=True,
        db_pool=mock_db_pool,
    )


# ============================================================================
# PythonFormIDAnalyzer Initialization Tests
# ============================================================================


class TestPythonFormIDAnalyzerInit:
    """Tests for PythonFormIDAnalyzer initialization."""

    @pytest.mark.unit
    def test_init_with_all_parameters(self, mock_yamldata_formid: MagicMock) -> None:
        """Test analyzer initializes with all required parameters."""
        from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

        analyzer = PythonFormIDAnalyzer(
            yamldata=mock_yamldata_formid,
            show_formid_values=True,
            formid_db_exists=True,
            db_pool=None,
        )

        assert analyzer.yamldata == mock_yamldata_formid
        assert analyzer.show_formid_values is True
        assert analyzer.formid_db_exists is True
        assert analyzer.db_pool is None

    @pytest.mark.unit
    def test_init_with_disabled_formid_values(self, mock_yamldata_formid: MagicMock) -> None:
        """Test analyzer initializes with FormID values disabled."""
        from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

        analyzer = PythonFormIDAnalyzer(
            yamldata=mock_yamldata_formid,
            show_formid_values=False,
            formid_db_exists=False,
            db_pool=None,
        )

        assert analyzer.show_formid_values is False
        assert analyzer.formid_db_exists is False

    @pytest.mark.unit
    def test_init_creates_formid_pattern(self, mock_yamldata_formid: MagicMock) -> None:
        """Test analyzer creates regex pattern for FormID matching."""
        from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

        analyzer = PythonFormIDAnalyzer(
            yamldata=mock_yamldata_formid,
            show_formid_values=True,
            formid_db_exists=True,
            db_pool=None,
        )

        assert analyzer.formid_pattern is not None
        # Test pattern matches expected format
        match = analyzer.formid_pattern.search("  Form ID: 0x0A001234")
        assert match is not None
        assert match.group(1).upper() == "0A001234"


# ============================================================================
# extract_formids Tests
# ============================================================================


class TestExtractFormids:
    """Tests for PythonFormIDAnalyzer.extract_formids method."""

    @pytest.mark.unit
    def test_extract_formids_from_empty_callstack(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test extracting FormIDs from empty callstack returns empty list."""
        result = formid_analyzer.extract_formids([])

        assert result == []

    @pytest.mark.unit
    def test_extract_formids_from_valid_line(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test extracting FormID from valid line."""
        callstack = ["  Form ID: 0x0A001234"]

        result = formid_analyzer.extract_formids(callstack)

        assert len(result) == 1
        assert result[0] == "Form ID: 0A001234"

    @pytest.mark.unit
    def test_extract_formids_skips_ff_prefix(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test extracting FormIDs skips those starting with FF."""
        callstack = [
            "  Form ID: 0xFF001234",  # Should be skipped
            "  Form ID: 0x0A001234",  # Should be included
        ]

        result = formid_analyzer.extract_formids(callstack)

        assert len(result) == 1
        assert result[0] == "Form ID: 0A001234"

    @pytest.mark.unit
    def test_extract_formids_keeps_null_formid(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test extracting FormIDs keeps NULL FormID (00000000)."""
        callstack = ["  Form ID: 0x00000000"]

        result = formid_analyzer.extract_formids(callstack)

        assert len(result) == 1
        assert result[0] == "Form ID: 00000000"

    @pytest.mark.unit
    def test_extract_formids_case_insensitive(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test FormID extraction is case insensitive."""
        callstack = [
            "  Form ID: 0x0a001234",  # lowercase
            "  Form ID: 0x0B005678",  # uppercase
        ]

        result = formid_analyzer.extract_formids(callstack)

        assert len(result) == 2
        # Results should be normalized to uppercase
        assert "Form ID: 0A001234" in result
        assert "Form ID: 0B005678" in result

    @pytest.mark.unit
    def test_extract_formids_multiple_lines(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test extracting FormIDs from multiple lines."""
        callstack = [
            "Some random line",
            "  Form ID: 0x0A001234",
            "Another line without FormID",
            "  Form ID: 0x0B005678",
            "  Form ID: 0x0A001234",  # Duplicate
        ]

        result = formid_analyzer.extract_formids(callstack)

        assert len(result) == 3
        assert result.count("Form ID: 0A001234") == 2

    @pytest.mark.unit
    def test_extract_formids_no_matches(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test extracting FormIDs when no matches found."""
        callstack = [
            "Random line 1",
            "Random line 2",
            "No FormID here",
        ]

        result = formid_analyzer.extract_formids(callstack)

        assert result == []


# ============================================================================
# formid_match Tests
# ============================================================================


class TestFormidMatch:
    """Tests for PythonFormIDAnalyzer.formid_match method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_formid_match_empty_matches(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test formid_match with empty matches returns appropriate message."""
        result = await formid_analyzer.formid_match([], {})

        assert result.has_content
        content = "".join(result.content)
        assert "COULDN'T FIND ANY FORM ID SUSPECTS" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_formid_match_with_matching_plugin(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test formid_match with FormID matching a plugin."""
        formids = ["Form ID: 0A001234"]
        plugins = {"TestPlugin.esp": "0A"}

        result = await formid_analyzer.formid_match(formids, plugins)

        assert result.has_content
        content = "".join(result.content)
        assert "0A001234" in content
        assert "TestPlugin.esp" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_formid_match_counts_duplicates(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test formid_match correctly counts duplicate FormIDs."""
        formids = ["Form ID: 0A001234", "Form ID: 0A001234", "Form ID: 0A001234"]
        plugins = {"TestPlugin.esp": "0A"}

        result = await formid_analyzer.formid_match(formids, plugins)

        assert result.has_content
        content = "".join(result.content)
        # Should show count of 3
        assert "| 3\n" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_formid_match_no_matching_plugin(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test formid_match when no plugin matches FormID prefix."""
        formids = ["Form ID: 0A001234"]
        plugins = {"OtherPlugin.esp": "0B"}  # Different prefix

        result = await formid_analyzer.formid_match(formids, plugins)

        assert result.has_content
        content = "".join(result.content)
        # Should have footer but no specific FormID line (no matching plugin)
        assert "These Form IDs were caught by" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_formid_match_includes_footer_text(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test formid_match includes explanatory footer."""
        formids = ["Form ID: 0A001234"]
        plugins = {"TestPlugin.esp": "0A"}

        result = await formid_analyzer.formid_match(formids, plugins)

        content = "".join(result.content)
        assert "Buffout 4" in content  # crashgen_name
        assert "xEdit" in content


class TestFormidMatchWithDatabase:
    """Tests for formid_match with database lookups."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_formid_match_with_db_pool_lookup(
        self,
        formid_analyzer_with_pool: "PythonFormIDAnalyzer",
        mock_db_pool: AsyncMock,
    ) -> None:
        """Test formid_match performs database lookup with pool."""
        mock_db_pool.get_entries_batch.return_value = {("001234", "TestPlugin.esp"): "Test Description"}

        formids = ["Form ID: 0A001234"]
        plugins = {"TestPlugin.esp": "0A"}

        result = await formid_analyzer_with_pool.formid_match(formids, plugins)

        content = "".join(result.content)
        assert "Test Description" in content
        mock_db_pool.get_entries_batch.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_formid_match_with_db_pool_no_result(
        self,
        formid_analyzer_with_pool: "PythonFormIDAnalyzer",
        mock_db_pool: AsyncMock,
    ) -> None:
        """Test formid_match handles no database result gracefully."""
        mock_db_pool.get_entries_batch.return_value = {}

        formids = ["Form ID: 0A001234"]
        plugins = {"TestPlugin.esp": "0A"}

        result = await formid_analyzer_with_pool.formid_match(formids, plugins)

        content = "".join(result.content)
        # Should still show FormID without description
        assert "0A001234" in content
        assert "TestPlugin.esp" in content


# ============================================================================
# lookup_formid_value Tests
# ============================================================================


class TestLookupFormidValue:
    """Tests for PythonFormIDAnalyzer.lookup_formid_value method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lookup_formid_value_no_db(self, mock_yamldata_formid: MagicMock) -> None:
        """Test lookup returns None when database doesn't exist."""
        from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

        analyzer = PythonFormIDAnalyzer(
            yamldata=mock_yamldata_formid,
            show_formid_values=True,
            formid_db_exists=False,  # No database
            db_pool=None,
        )

        result = await analyzer.lookup_formid_value("001234", "Test.esp")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lookup_formid_value_with_pool(
        self,
        formid_analyzer_with_pool: "PythonFormIDAnalyzer",
        mock_db_pool: AsyncMock,
    ) -> None:
        """Test lookup uses database pool when available."""
        mock_db_pool.get_entry.return_value = "Test Description"

        result = await formid_analyzer_with_pool.lookup_formid_value("001234", "Test.esp")

        assert result == "Test Description"
        mock_db_pool.get_entry.assert_called_once_with("001234", "Test.esp")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lookup_formid_value_fallback_to_sync(self, mock_yamldata_formid: MagicMock) -> None:
        """Test lookup falls back to sync lookup when no pool."""
        from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer

        analyzer = PythonFormIDAnalyzer(
            yamldata=mock_yamldata_formid,
            show_formid_values=True,
            formid_db_exists=True,
            db_pool=None,
        )

        with patch("ClassicLib.integration.python.formid_py._cached_formid_lookup") as mock_lookup:
            mock_lookup.return_value = "Cached Result"

            result = await analyzer.lookup_formid_value("001234", "Test.esp")

            # Should have called the cached lookup via asyncio.to_thread
            assert result == "Cached Result"


# ============================================================================
# _perform_async_lookups Tests
# ============================================================================


class TestPerformAsyncLookups:
    """Tests for PythonFormIDAnalyzer._perform_async_lookups method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_perform_async_lookups_no_pool(self, formid_analyzer: "PythonFormIDAnalyzer") -> None:
        """Test async lookups fallback when no pool available."""
        lines: list[str] = []
        tasks = [("Form ID: 0A001234", "001234", "Test.esp", 1)]

        await formid_analyzer._perform_async_lookups(tasks, lines)

        assert len(lines) == 1
        assert "0A001234" in lines[0]
        assert "Test.esp" in lines[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_perform_async_lookups_with_pool(
        self,
        formid_analyzer_with_pool: "PythonFormIDAnalyzer",
        mock_db_pool: AsyncMock,
    ) -> None:
        """Test async lookups with database pool."""
        mock_db_pool.get_entries_batch.return_value = {("001234", "Test.esp"): "Description"}

        lines: list[str] = []
        tasks = [("Form ID: 0A001234", "001234", "Test.esp", 2)]

        await formid_analyzer_with_pool._perform_async_lookups(tasks, lines)

        assert len(lines) == 1
        assert "Description" in lines[0]
        assert "| 2\n" in lines[0]


# ============================================================================
# Alias Tests
# ============================================================================


class TestFormIDAnalyzerAlias:
    """Tests for FormIDAnalyzer alias."""

    @pytest.mark.unit
    def test_formid_analyzer_alias_exists(self) -> None:
        """Test FormIDAnalyzer is an alias for PythonFormIDAnalyzer."""
        from ClassicLib.integration.python.formid_py import FormIDAnalyzer, PythonFormIDAnalyzer

        assert FormIDAnalyzer is PythonFormIDAnalyzer


# ============================================================================
# Pattern Cache Tests
# ============================================================================


class TestPatternCache:
    """Tests for regex pattern caching."""

    @pytest.mark.unit
    def test_pattern_cache_reused(self, mock_yamldata_formid: MagicMock) -> None:
        """Test that pattern cache is reused across instances."""
        from ClassicLib.integration.python.formid_py import _PATTERN_CACHE, PythonFormIDAnalyzer

        # Create first analyzer
        analyzer1 = PythonFormIDAnalyzer(
            yamldata=mock_yamldata_formid,
            show_formid_values=True,
            formid_db_exists=True,
            db_pool=None,
        )

        # Create second analyzer
        analyzer2 = PythonFormIDAnalyzer(
            yamldata=mock_yamldata_formid,
            show_formid_values=True,
            formid_db_exists=True,
            db_pool=None,
        )

        # Both should use the same cached pattern
        assert analyzer1.formid_pattern is analyzer2.formid_pattern

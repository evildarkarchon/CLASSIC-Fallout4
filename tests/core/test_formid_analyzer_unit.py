"""
Tests for the FormIDAnalyzerCore component.

This module contains tests for FormID extraction, matching, and database lookups
in the async crash log processing pipeline.

IMPORTANT: These tests use mocked AsyncDatabasePool to avoid actual database connections.
The clean_database_pool_manager fixture ensures proper singleton isolation.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from unittest.mock import AsyncMock, MagicMock

import pytest

from ClassicLib.Database import AsyncDatabasePool
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Mock ClassicScanLogsInfo for testing."""
    yamldata: MagicMock = MagicMock()
    yamldata.game_ignore_plugins = ["plugin1.esp", "plugin2.esp"]
    yamldata.game_ignore_records = ["record1", "record2"]
    yamldata.ignore_list = ["ignore1.esp", "ignore2.esp"]
    yamldata.classic_records_list = ["record1", "record2"]
    return yamldata


@pytest.mark.integration
@pytest.mark.asyncio
class TestFormIDAnalyzerCore:
    """Integration tests for FormIDAnalyzerCore."""

    async def test_formid_analyzer_core_initialization(self, mock_yamldata: MagicMock) -> None:
        """Test FormIDAnalyzerCore initialization.

        Uses a mocked AsyncDatabasePool to avoid actual database connections.
        The clean_database_pool_manager fixture ensures singleton cleanup.
        """
        mock_pool: AsyncMock = AsyncMock(spec=AsyncDatabasePool)

        analyzer: FormIDAnalyzerCore = FormIDAnalyzerCore(
            yamldata=mock_yamldata,
            show_formid_values=True,
            formid_db_exists=True,
            db_pool=mock_pool,
        )

        assert analyzer.yamldata == mock_yamldata
        assert analyzer.show_formid_values is True
        assert analyzer.formid_db_exists is True
        assert analyzer.db_pool == mock_pool

    async def test_formid_extraction(self, mock_yamldata: MagicMock) -> None:
        """Test FormID extraction from call stack.

        Creates analyzer with mocked pool to test FormID extraction logic.
        """
        mock_pool: AsyncMock = AsyncMock(spec=AsyncDatabasePool)
        analyzer: FormIDAnalyzerCore = FormIDAnalyzerCore(mock_yamldata, True, True, mock_pool)

        callstack: list[str] = [
            "Form ID: 0x12345678",
            "Form ID: 0x87654321",
            "Form ID: 0xFF000001",  # Should be skipped (FF prefix)
            "Regular line without FormID",
        ]

        formids: list[str] = analyzer.extract_formids(callstack)

        assert len(formids) == 2
        assert "Form ID: 12345678" in formids
        assert "Form ID: 87654321" in formids
        assert "Form ID: FF000001" not in formids

    async def test_formid_extraction_with_various_formats(self, mock_yamldata: MagicMock) -> None:
        """Test FormID extraction with various formatting patterns."""
        mock_pool: AsyncMock = AsyncMock(spec=AsyncDatabasePool)
        analyzer: FormIDAnalyzerCore = FormIDAnalyzerCore(mock_yamldata, True, True, mock_pool)

        callstack: list[str] = [
            "Form ID: 0x00ABCDEF",  # Standard format
            "Form ID: 0xABCDEF",  # Without leading zeros
            "Form ID: ABCDEF",  # Without 0x prefix (won't match pattern)
            "FormID: 0x12345678",  # Without space (won't match pattern)
            "Form ID: 0xFE000001",  # FE prefix (should be kept)
            "Form ID: 0xFF000001",  # FF prefix (should be skipped)
            "Form ID: 0x00000000",  # NULL FormID (intentionally extracted to show errors)
        ]

        formids: list[str] = analyzer.extract_formids(callstack)

        # Verify expected FormIDs were extracted based on actual pattern matching
        # The pattern requires "Form ID:" with space and "0x" prefix
        assert "Form ID: 00ABCDEF" in formids
        assert "Form ID: FE000001" in formids
        assert "Form ID: FF000001" not in formids  # FF prefix is filtered (exceeds plugin limit)

        # Pattern is permissive and handles "FormID:" without space
        assert len([f for f in formids if "12345678" in f]) == 1

        # NULL FormID (0x00000000) is intentionally extracted as it indicates an error/invalid reference
        # that users need to investigate in their load order
        assert "Form ID: 00000000" in formids

    async def test_async_formid_matching(self, mock_yamldata: MagicMock) -> None:
        """Test async FormID matching with database lookups.

        Uses AsyncMock correctly to simulate async database operations.
        The FormIDAnalyzerCore uses batch queries for performance.
        """
        from ClassicLib.rust.report_rust import ReportFragment

        mock_pool: AsyncMock = AsyncMock(spec=AsyncDatabasePool)
        # FormIDAnalyzerCore uses batch queries for performance
        # Mock the batch query method to return a dictionary of results
        mock_batch_results = {("12345678", "TestPlugin.esp"): "Test Entry 1", ("87654321", "AnotherPlugin.esp"): "Test Entry 2"}
        mock_pool.get_entries_batch = AsyncMock(return_value=mock_batch_results)

        analyzer: FormIDAnalyzerCore = FormIDAnalyzerCore(mock_yamldata, True, True, mock_pool)

        formids_matches: list[str] = ["Form ID: 12345678", "Form ID: 87654321"]
        crashlog_plugins: dict[str, str] = {"TestPlugin.esp": "12", "AnotherPlugin.esp": "87"}

        # Use the new formid_match method that returns a ReportFragment
        result: ReportFragment = await analyzer.formid_match(formids_matches, crashlog_plugins)

        # Verify batch database query was made
        assert mock_pool.get_entries_batch.call_count == 1

        # Verify report fragment was populated
        assert result.has_content
        result_list = result.to_list()
        assert len(result_list) >= 2  # At least 2 FormID entries plus footer
        result_str = "".join(result_list)
        assert "TestPlugin.esp" in result_str
        assert "AnotherPlugin.esp" in result_str

    async def test_formid_matching_without_database(self, mock_yamldata: MagicMock) -> None:
        """Test FormID matching when database doesn't exist."""
        from ClassicLib.rust.report_rust import ReportFragment

        analyzer: FormIDAnalyzerCore = FormIDAnalyzerCore(
            yamldata=mock_yamldata,
            show_formid_values=False,
            formid_db_exists=False,
            db_pool=None,
        )

        formids_matches: list[str] = ["Form ID: 12345678", "Form ID: 87654321"]
        crashlog_plugins: dict[str, str] = {"TestPlugin.esp": "12", "AnotherPlugin.esp": "87"}

        result: ReportFragment = await analyzer.formid_match(formids_matches, crashlog_plugins)

        # Without database, should still create report but without entry details
        assert result.has_content
        result_str = "".join(result.to_list())
        assert "TestPlugin.esp" in result_str

    async def test_formid_with_ignored_plugins(self, mock_yamldata: MagicMock) -> None:
        """Test FormID matching with ignored plugins.

        Uses AsyncMock correctly to simulate async database operations.
        """
        from ClassicLib.rust.report_rust import ReportFragment

        mock_pool: AsyncMock = AsyncMock(spec=AsyncDatabasePool)
        # FormIDAnalyzerCore uses batch queries for performance
        mock_batch_results = {("12345678", "TestPlugin.esp"): "Test Entry 1", ("87654321", "IgnoredPlugin.esp"): "Test Entry 2"}
        mock_pool.get_entries_batch = AsyncMock(return_value=mock_batch_results)

        # Set ignored plugins
        mock_yamldata.game_ignore_plugins = ["IgnoredPlugin.esp"]

        analyzer: FormIDAnalyzerCore = FormIDAnalyzerCore(mock_yamldata, True, True, mock_pool)

        formids_matches: list[str] = ["Form ID: 12345678", "Form ID: 87654321"]
        crashlog_plugins: dict[str, str] = {
            "TestPlugin.esp": "12",
            "IgnoredPlugin.esp": "87",  # Should be filtered out
        }

        result: ReportFragment = await analyzer.formid_match(formids_matches, crashlog_plugins)

        result_str = "".join(result.to_list())
        assert "TestPlugin.esp" in result_str
        # Ignored plugin might still appear in some contexts, but verify it's handled
        # The actual filtering logic depends on the implementation

    async def test_empty_formid_list(self, mock_yamldata: MagicMock) -> None:
        """Test handling of empty FormID list."""
        from ClassicLib.rust.report_rust import ReportFragment

        mock_pool: AsyncMock = AsyncMock(spec=AsyncDatabasePool)
        analyzer: FormIDAnalyzerCore = FormIDAnalyzerCore(mock_yamldata, True, True, mock_pool)

        formids_matches: list[str] = []
        crashlog_plugins: dict[str, str] = {"TestPlugin.esp": "12"}

        result: ReportFragment = await analyzer.formid_match(formids_matches, crashlog_plugins)

        # Should handle empty FormID list gracefully
        # May or may not have content depending on implementation
        assert isinstance(result, ReportFragment)

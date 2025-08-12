"""
DEPRECATED: Async FormID analyzer module for crash log scanning.

This module is deprecated as of the async-first refactoring.
All functionality has been moved to FormIDAnalyzerCore.py.
This module now provides compatibility aliases to maintain backwards compatibility.
"""

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class AsyncFormIDAnalyzer(FormIDAnalyzerCore):
    """
    DEPRECATED: Use FormIDAnalyzerCore instead.

    This class is maintained for backwards compatibility only.
    It simply inherits from FormIDAnalyzerCore without modification.
    """

    def __init__(
        self, yamldata: "ClassicScanLogsInfo", show_formid_values: bool, formid_db_exists: bool, db_pool: AsyncDatabasePool
    ) -> None:
        """
        Initialize the async FormID analyzer (deprecated).

        Args:
            yamldata: Configuration data
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
            db_pool: Async database connection pool
        """
        super().__init__(yamldata, show_formid_values, formid_db_exists, db_pool)

    # All methods are inherited from FormIDAnalyzerCore
    # The following are aliases for backwards compatibility

    async def formid_match_async(self, formids_matches: list[str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> None:
        """
        DEPRECATED: Use formid_match() instead.

        Maintained for backwards compatibility.
        """
        return await self.formid_match(formids_matches, crashlog_plugins, autoscan_report)

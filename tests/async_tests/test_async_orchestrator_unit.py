"""
Unit tests for async_orchestrator - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

pytestmark = pytest.mark.unit

@pytest.mark.integration
@pytest.mark.asyncio
class TestOrchestratorCore:
    """Integration tests for OrchestratorCore."""

    async def test_orchestrator_core_context_manager(self, mock_yamldata: MagicMock) -> None:
        """Test OrchestratorCore as async context manager."""
        crashlogs: MagicMock = MagicMock(spec=ThreadSafeLogCache)
        with patch('ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool') as mock_pool_class:
            mock_pool: AsyncMock = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool
            async with OrchestratorCore(yamldata=mock_yamldata, crashlogs=crashlogs, fcx_mode=False, show_formid_values=True, formid_db_exists=True) as orchestrator:
                assert orchestrator is not None
                assert orchestrator._db_pool == mock_pool
                mock_pool.initialize.assert_called_once()
            mock_pool.close.assert_called_once()

    async def test_orchestrator_initialization_without_db(self, mock_yamldata: MagicMock) -> None:
        """Test orchestrator initialization without FormID database."""
        crashlogs: MagicMock = MagicMock(spec=ThreadSafeLogCache)
        with patch('ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool') as mock_pool_class:
            mock_pool: AsyncMock = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool
            async with OrchestratorCore(yamldata=mock_yamldata, crashlogs=crashlogs, fcx_mode=True, show_formid_values=False, formid_db_exists=False) as orchestrator:
                assert orchestrator is not None
                assert orchestrator.fcx_handler is not None  # FCX handler created with fcx_mode=True
                assert orchestrator.show_formid_values is False
                assert orchestrator.formid_db_exists is False
                # Pool is created but not used when formid_db_exists is False
                mock_pool_class.assert_called_once()

    async def test_orchestrator_with_multiple_analyzers(self, mock_yamldata: MagicMock) -> None:
        """Test orchestrator with multiple analyzer components enabled."""
        crashlogs: MagicMock = MagicMock(spec=ThreadSafeLogCache)
        mock_yamldata.formid_analyzer_enabled = True
        mock_yamldata.record_scanner_enabled = True
        mock_yamldata.plugin_analyzer_enabled = True
        with patch('ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool') as mock_pool_class:
            mock_pool: AsyncMock = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool
            async with OrchestratorCore(yamldata=mock_yamldata, crashlogs=crashlogs, fcx_mode=False, show_formid_values=True, formid_db_exists=True) as orchestrator:
                assert orchestrator.formid_analyzer is not None
                assert orchestrator.record_scanner is not None
                assert orchestrator.plugin_analyzer is not None

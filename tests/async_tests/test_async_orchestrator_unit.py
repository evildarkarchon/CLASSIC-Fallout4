"""
Unit tests for async_orchestrator - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.

IMPORTANT: These tests use the DatabasePoolManager singleton pattern.
The clean_database_pool_manager fixture ensures proper test isolation.
Mock fixtures are used to avoid actual database connections during unit tests.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns

from unittest.mock import MagicMock

import pytest

from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore

pytestmark = pytest.mark.unit


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrchestratorCore:
    """Integration tests for OrchestratorCore."""

    async def test_orchestrator_core_context_manager(self, mock_yamldata: MagicMock, mock_database_pool_manager) -> None:
        """Test OrchestratorCore as async context manager.

        Uses mock_database_pool_manager fixture to ensure singleton isolation.
        The fixture mocks DatabasePoolManager to prevent actual database connections.

        Note: ThreadSafeLogCache was removed for performance reasons.
        OrchestratorCore no longer requires crashlogs parameter and reads files directly.
        """
        # OrchestratorCore now uses DatabasePoolManager singleton internally
        async with OrchestratorCore(yamldata=mock_yamldata, fcx_mode=False, show_formid_values=True, formid_db_exists=True) as orchestrator:
            assert orchestrator is not None
            # The mock_database_pool_manager ensures the pool is properly mocked
            assert orchestrator._db_pool is not None

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_without_db(self, mock_yamldata: MagicMock, mock_database_pool_manager) -> None:
        """Test orchestrator initialization without FormID database.

        Uses mock_database_pool_manager fixture for singleton isolation.
        Tests that orchestrator works correctly when FormID database is not available.

        Note: ThreadSafeLogCache was removed for performance reasons.
        OrchestratorCore no longer requires crashlogs parameter and reads files directly.
        """
        # Test with FormID database disabled
        async with OrchestratorCore(
            yamldata=mock_yamldata, fcx_mode=True, show_formid_values=False, formid_db_exists=False
        ) as orchestrator:
            assert orchestrator is not None
            assert orchestrator.fcx_handler is not None  # FCX handler created with fcx_mode=True
            assert orchestrator.show_formid_values is False
            assert orchestrator.formid_db_exists is False
            # Pool is None when database doesn't exist (lazy initialization)
            assert orchestrator._db_pool is None

    @pytest.mark.asyncio
    async def test_orchestrator_with_multiple_analyzers(self, mock_yamldata: MagicMock, mock_database_pool_manager) -> None:
        """Test orchestrator with multiple analyzer components enabled.

        Uses mock_database_pool_manager to ensure proper singleton isolation.
        Verifies all analyzer components are initialized correctly.

        Note: ThreadSafeLogCache was removed for performance reasons.
        OrchestratorCore no longer requires crashlogs parameter and reads files directly.
        """
        mock_yamldata.formid_analyzer_enabled = True
        mock_yamldata.record_scanner_enabled = True
        mock_yamldata.plugin_analyzer_enabled = True

        # Test with all analyzers enabled
        async with OrchestratorCore(yamldata=mock_yamldata, fcx_mode=False, show_formid_values=True, formid_db_exists=True) as orchestrator:
            assert orchestrator.formid_analyzer is not None
            assert orchestrator.record_scanner is not None
            assert orchestrator.plugin_analyzer is not None
            # Pool should be available for FormID lookups
            assert orchestrator._db_pool is not None

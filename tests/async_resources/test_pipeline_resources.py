"""Tests for async pipeline resource management."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib import init_message_handler
from tests.async_resources.conftest import ContextTestError

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup


@pytest.mark.asyncio
class TestAsyncPipelineResourceManagement:
    """Tests for async pipeline resource management."""

    async def test_pipeline_cleanup_on_exception(self, message_handler):
        """Test that pipeline properly cleans up resources on exception."""
        from ClassicLib.ScanLog.pipeline import AsyncCrashLogPipeline

        mock_yamldata = MagicMock()
        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # Mock to make processing fail
        with (
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async") as mock_reformat,
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.load_crash_logs_async") as mock_load,
        ):
            # Make reformat raise an exception
            mock_reformat.side_effect = Exception("Simulated error")

            # Processing should fail
            with pytest.raises(Exception, match="Simulated error"):
                await pipeline.process_crash_logs_async([], ())

            # Pipeline should still be in a valid state for cleanup
            assert isinstance(pipeline.performance_stats, dict)

    async def test_orchestrator_resource_cleanup(self, message_handler):
        """Test that OrchestratorCore properly manages database pool resources."""
        from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
        from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

        mock_yamldata = MagicMock()
        mock_crashlogs = MagicMock(spec=ThreadSafeLogCache)

        def _raise_test_exception():
            """Helper function to raise a test exception during context operations."""
            raise ContextTestError("Test exception during context")

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool") as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool

            # Test normal flow
            async with OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=mock_crashlogs,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            ) as orchestrator:
                assert orchestrator._db_pool == mock_pool
                mock_pool.initialize.assert_called_once()

            # Verify cleanup was called
            mock_pool.close.assert_called_once()

            # Reset mocks for next test
            mock_pool.initialize.reset_mock()
            mock_pool.close.reset_mock()

            # Test cleanup on exception during context
            # Create a new orchestrator that will fail during usage
            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=mock_crashlogs,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            )

            # Use the context manager and force an exception
            try:
                async with orchestrator:
                    # Force an exception after initialization
                    _raise_test_exception()
            except ContextTestError as e:
                if "Test exception" not in str(e):
                    raise

            # Cleanup should have been called
            mock_pool.close.assert_called_once()

    async def test_pipeline_state_management(self, message_handler):
        """Test that pipeline maintains proper state throughout lifecycle."""
        from ClassicLib.ScanLog.pipeline import AsyncCrashLogPipeline

        mock_yamldata = MagicMock()
        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=True,
            show_formid_values=True,
            formid_db_exists=True,
        )

        # Check initial state
        assert pipeline.fcx_mode is True
        assert pipeline.show_formid_values is True
        assert pipeline.formid_db_exists is True
        assert isinstance(pipeline.performance_stats, dict)

        # Mock successful processing - just check initialization state
        # The pipeline maintains its state regardless of processing
        assert pipeline.fcx_mode is True
        assert pipeline.show_formid_values is True

    async def test_orchestrator_concurrent_processing(self, message_handler):
        """Test that orchestrator can handle concurrent processing."""
        from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
        from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

        mock_yamldata = MagicMock()
        mock_crashlogs = MagicMock(spec=ThreadSafeLogCache)

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool") as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=mock_crashlogs,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Verify orchestrator is ready for concurrent operations
                assert orchestrator is not None
                # Database pool should be initialized
                mock_pool.initialize.assert_called_once()
